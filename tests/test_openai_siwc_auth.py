from __future__ import annotations

import json
import tempfile
import time
import unittest
import urllib.parse
from pathlib import Path

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from ordax_chat_app.auth import (
    ChatGPTAccount,
    ChatGPTAccountStore,
    HostIdentityStore,
    OpenAISignInClient,
    ProtectedJsonStore,
)
from ordax_chat_app.auth.openai_siwc import DYNAMIC_CLIENT_ID, RESOURCE


class OpenAISignInClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.private_key.public_key()))
        public_jwk.update({"kid": "test-key", "alg": "RS256", "use": "sig"})
        self.jwks = {"keys": [public_jwk]}
        self.discovery = {
            "issuer": "https://auth.openai.com",
            "authorization_endpoint": "https://auth.openai.com/api/accounts/authorize",
            "token_endpoint": "https://auth.openai.com/api/accounts/oauth/token",
            "jwks_uri": "https://auth.openai.com/.well-known/jwks.json",
            "revocation_endpoint": "https://auth.openai.com/api/accounts/oauth/revoke",
        }
        protected = ProtectedJsonStore(
            self.root / "accounts.dat",
            protect=lambda data: b"x" + data[::-1],
            unprotect=lambda data: data[1:][::-1],
        )
        self.account_store = ChatGPTAccountStore(protected)
        self.host_store = HostIdentityStore(self.root / "state")

    def _id_token(
        self,
        *,
        client_id: str,
        nonce: str | None,
        subject: str = "user-123",
        email: str = "user@example.com",
    ) -> str:
        now = int(time.time())
        claims = {
            "iss": "https://auth.openai.com",
            "aud": client_id,
            "sub": subject,
            "email": email,
            "name": "Example User",
            "iat": now,
            "exp": now + 3600,
        }
        if nonce is not None:
            claims["nonce"] = nonce
        return jwt.encode(
            claims,
            self.private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

    def test_prepare_authorization_uses_dynamic_client_pkce_and_stable_host(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/.well-known/openid-configuration")
            return httpx.Response(200, json=self.discovery)

        client = OpenAISignInClient(
            host_store=self.host_store,
            account_store=self.account_store,
            transport=httpx.MockTransport(handler),
        )
        first = client.prepare_authorization("http://127.0.0.1:1455/auth/callback")
        second = client.prepare_authorization("http://127.0.0.1:1456/auth/callback")

        query = urllib.parse.parse_qs(urllib.parse.urlparse(first.authorization_url).query)
        self.assertEqual(query["client_id"], [DYNAMIC_CLIENT_ID])
        self.assertEqual(query["resource"], [RESOURCE])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["agent_name_hint"], ["ORDAX Dev"])
        self.assertIn("chatgpt.tokens.use.direct", query["scope"][0].split())
        self.assertTrue(first.ext_agent_host_id.startswith("urn:uuid:"))
        self.assertEqual(first.ext_agent_host_id, second.ext_agent_host_id)
        self.assertNotEqual(first.state, second.state)
        self.assertNotEqual(first.nonce, second.nonce)
        self.assertNotEqual(first.code_verifier, second.code_verifier)

    def test_dynamic_callback_exchanges_code_validates_identity_and_saves_account(self) -> None:
        issued_client_id = "oaiapp_test"
        observed_form = {}

        client_ref = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/.well-known/openid-configuration":
                return httpx.Response(200, json=self.discovery)
            if request.url.path == "/.well-known/jwks.json":
                return httpx.Response(200, json=self.jwks)
            if request.url.path == "/api/accounts/oauth/token":
                form = urllib.parse.parse_qs(request.content.decode("utf-8"))
                observed_form.update({key: values[-1] for key, values in form.items()})
                attempt = client_ref["attempt"]
                return httpx.Response(
                    200,
                    json={
                        "access_token": "access-1",
                        "refresh_token": "refresh-1",
                        "id_token": self._id_token(
                            client_id=issued_client_id,
                            nonce=attempt.nonce,
                        ),
                        "token_type": "Bearer",
                        "expires_in": 3600,
                        "scope": "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct",
                        "earliest_refresh_at": int(time.time()) + 10,
                    },
                )
            raise AssertionError(f"unexpected request {request.method} {request.url}")

        client = OpenAISignInClient(
            host_store=self.host_store,
            account_store=self.account_store,
            transport=httpx.MockTransport(handler),
        )
        attempt = client.prepare_authorization("http://127.0.0.1:1455/auth/callback")
        client_ref["attempt"] = attempt
        account = client.exchange_callback(
            attempt,
            {
                "state": attempt.state,
                "code": "code-123",
                "client_id": issued_client_id,
            },
        )
        self.assertEqual(account.subject, "user-123")
        self.assertEqual(account.email, "user@example.com")
        self.assertEqual(account.client_id, issued_client_id)
        self.assertIn("chatgpt.tokens.use.direct", account.scopes)
        self.assertEqual(observed_form["client_id"], issued_client_id)
        self.assertEqual(observed_form["code_verifier"], attempt.code_verifier)
        self.assertEqual(observed_form["redirect_uri"], attempt.redirect_uri)

        self.account_store.save(account)
        selected = self.account_store.selected()
        self.assertIsNotNone(selected)
        self.assertEqual(selected.subject, "user-123")
        self.assertNotIn(b"access-1", (self.root / "accounts.dat").read_bytes())

    def test_returning_authorization_uses_saved_client_and_identity_hints(self) -> None:
        account = ChatGPTAccount(
            subject="user-123",
            email="user@example.com",
            name="Example",
            issuer="https://auth.openai.com",
            client_id="oaiapp_saved",
            ext_agent_host_id=self.host_store.get_or_create(),
            id_token="retained-id-token",
            access_token="access",
            refresh_token="refresh",
            token_type="Bearer",
            expires_in=3600,
            earliest_refresh_at=None,
            scopes=["chatgpt.tokens.use.direct"],
            saved_at_unix=int(time.time()),
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=self.discovery)

        client = OpenAISignInClient(
            host_store=self.host_store,
            account_store=self.account_store,
            transport=httpx.MockTransport(handler),
        )
        attempt = client.prepare_authorization(
            "http://127.0.0.1:2222/auth/callback",
            account=account,
        )
        query = urllib.parse.parse_qs(urllib.parse.urlparse(attempt.authorization_url).query)
        self.assertEqual(query["client_id"], ["oaiapp_saved"])
        self.assertEqual(query["id_token_hint"], ["retained-id-token"])
        self.assertEqual(query["login_hint"], ["user@example.com"])
        self.assertNotIn("agent_name_hint", query)
        self.assertEqual(attempt.expected_subject, "user-123")

    def test_refresh_rotates_refresh_token_without_requiring_new_id_token(self) -> None:
        original = ChatGPTAccount(
            subject="user-123",
            email="user@example.com",
            name="Example",
            issuer="https://auth.openai.com",
            client_id="oaiapp_saved",
            ext_agent_host_id=self.host_store.get_or_create(),
            id_token="retained-id-token",
            access_token="expired-access",
            refresh_token="refresh-old",
            token_type="Bearer",
            expires_in=1,
            earliest_refresh_at=None,
            scopes=["openid", "offline_access", "resource.invoke", "chatgpt.tokens.use.direct"],
            saved_at_unix=int(time.time()) - 3600,
        )
        self.account_store.save(original)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/.well-known/openid-configuration":
                return httpx.Response(200, json=self.discovery)
            if request.url.path == "/api/accounts/oauth/token":
                form = urllib.parse.parse_qs(request.content.decode("utf-8"))
                self.assertEqual(form["grant_type"], ["refresh_token"])
                self.assertEqual(form["refresh_token"], ["refresh-old"])
                return httpx.Response(
                    200,
                    json={
                        "access_token": "access-new",
                        "refresh_token": "refresh-new",
                        "token_type": "Bearer",
                        "expires_in": 3600,
                    },
                )
            raise AssertionError(f"unexpected request {request.url}")

        client = OpenAISignInClient(
            host_store=self.host_store,
            account_store=self.account_store,
            transport=httpx.MockTransport(handler),
        )
        refreshed = client.refresh(original)
        self.assertEqual(refreshed.access_token, "access-new")
        self.assertEqual(refreshed.refresh_token, "refresh-new")
        self.assertEqual(refreshed.id_token, "retained-id-token")
        self.assertEqual(refreshed.subject, "user-123")
        selected = self.account_store.selected()
        self.assertEqual(selected.refresh_token, "refresh-new")

    def test_invalid_grant_clears_unusable_credentials(self) -> None:
        original = ChatGPTAccount(
            subject="user-123",
            email=None,
            name=None,
            issuer="https://auth.openai.com",
            client_id="oaiapp_saved",
            ext_agent_host_id=self.host_store.get_or_create(),
            id_token="id",
            access_token="expired",
            refresh_token="bad-refresh",
            token_type="Bearer",
            expires_in=1,
            earliest_refresh_at=None,
            scopes=["chatgpt.tokens.use.direct"],
            saved_at_unix=int(time.time()) - 3600,
        )
        self.account_store.save(original)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/.well-known/openid-configuration":
                return httpx.Response(200, json=self.discovery)
            if request.url.path == "/api/accounts/oauth/token":
                return httpx.Response(400, json={"error": "invalid_grant"})
            raise AssertionError(f"unexpected request {request.url}")

        client = OpenAISignInClient(
            host_store=self.host_store,
            account_store=self.account_store,
            transport=httpx.MockTransport(handler),
        )
        with self.assertRaisesRegex(Exception, "refresh failed"):
            client.refresh(original)
        cleared = self.account_store.get(original.key)
        self.assertEqual(cleared.access_token, "")
        self.assertEqual(cleared.refresh_token, "")


if __name__ == "__main__":
    unittest.main()
