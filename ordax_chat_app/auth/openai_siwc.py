"""Official Sign in with ChatGPT flow for the ORDAX open-source desktop app."""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

import httpx
import jwt

from .local_state import HostIdentityStore, ProtectedJsonStore


ISSUER = "https://auth.openai.com"
DISCOVERY_URL = f"{ISSUER}/.well-known/openid-configuration"
RESOURCE = "https://api.openai.com/v1"
DYNAMIC_CLIENT_ID = "dynamic_agent_client"
DEFAULT_SCOPES = (
    "openid",
    "profile",
    "email",
    "offline_access",
    "resource.invoke",
    "chatgpt.tokens.use.direct",
)
CALLBACK_PATH = "/auth/callback"


class SignInError(RuntimeError):
    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class OidcDiscovery:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    revocation_endpoint: str | None = None


@dataclass(frozen=True)
class AuthorizationAttempt:
    state: str
    nonce: str
    code_verifier: str
    redirect_uri: str
    requested_client_id: str
    ext_agent_host_id: str
    authorization_url: str
    expected_subject: str | None = None


@dataclass
class ChatGPTAccount:
    subject: str
    email: str | None
    name: str | None
    issuer: str
    client_id: str
    ext_agent_host_id: str
    id_token: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    earliest_refresh_at: int | None
    scopes: list[str]
    saved_at_unix: int

    @property
    def key(self) -> str:
        digest = hashlib.sha256(f"{self.issuer}\0{self.subject}\0{self.client_id}".encode("utf-8")).hexdigest()
        return digest[:32]

    @property
    def expires_at_unix(self) -> int:
        return self.saved_at_unix + self.expires_in

    def access_token_valid_for(self, seconds: int = 120) -> bool:
        return self.expires_at_unix - int(time.time()) > seconds


class ChatGPTAccountStore:
    def __init__(self, protected_store: ProtectedJsonStore | None = None):
        self.store = protected_store or ProtectedJsonStore()
        self._refresh_locks: dict[str, threading.Lock] = {}
        self._lock = threading.Lock()

    def list_accounts(self) -> list[ChatGPTAccount]:
        payload = self.store.load()
        return [ChatGPTAccount(**item) for item in payload.get("accounts", [])]

    def selected(self) -> ChatGPTAccount | None:
        payload = self.store.load()
        selected = payload.get("selected_account")
        for item in payload.get("accounts", []):
            account = ChatGPTAccount(**item)
            if account.key == selected:
                return account
        return None

    def get(self, account_key: str) -> ChatGPTAccount | None:
        return next((item for item in self.list_accounts() if item.key == account_key), None)

    def save(self, account: ChatGPTAccount, *, select: bool = True) -> ChatGPTAccount:
        payload = self.store.load()
        accounts = []
        replaced = False
        for item in payload.get("accounts", []):
            current = ChatGPTAccount(**item)
            if current.key == account.key:
                accounts.append(asdict(account))
                replaced = True
            else:
                accounts.append(item)
        if not replaced:
            accounts.append(asdict(account))
        payload["accounts"] = accounts
        if select:
            payload["selected_account"] = account.key
        self.store.save(payload)
        return account

    def clear_tokens(self, account_key: str) -> None:
        payload = self.store.load()
        updated = []
        for item in payload.get("accounts", []):
            account = ChatGPTAccount(**item)
            if account.key == account_key:
                item = dict(item)
                item.update({"access_token": "", "refresh_token": "", "id_token": "", "expires_in": 0})
            updated.append(item)
        payload["accounts"] = updated
        self.store.save(payload)

    def refresh_lock(self, account_key: str) -> threading.Lock:
        with self._lock:
            return self._refresh_locks.setdefault(account_key, threading.Lock())


class _CallbackState:
    def __init__(self):
        self.event = threading.Event()
        self.result: dict[str, str] | None = None


class LoopbackCallback:
    def __init__(self):
        self.state = _CallbackState()
        callback_state = self.state

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path != CALLBACK_PATH:
                    self.send_response(404)
                    self.end_headers()
                    return
                query = urllib.parse.parse_qs(parsed.query)
                callback_state.result = {key: values[-1] for key, values in query.items() if values}
                callback_state.event.set()
                self.send_response(200)
                self.send_header("content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<!doctype html><meta charset='utf-8'><title>ORDAX</title>"
                    b"<h1>ORDAX connected to ChatGPT</h1><p>You can return to ORDAX.</p>"
                )

            def log_message(self, _format, *_args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def redirect_uri(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}{CALLBACK_PATH}"

    def start(self) -> None:
        self.thread.start()

    def wait(self, timeout_seconds: float = 300.0) -> dict[str, str]:
        if not self.state.event.wait(timeout_seconds):
            raise SignInError("ChatGPT sign-in timed out", code="callback_timeout")
        return dict(self.state.result or {})

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        if self.thread.is_alive():
            self.thread.join(timeout=2)


class OpenAISignInClient:
    def __init__(
        self,
        *,
        app_name: str = "ORDAX Dev",
        host_store: HostIdentityStore | None = None,
        account_store: ChatGPTAccountStore | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 30.0,
    ):
        self.app_name = app_name
        self.host_store = host_store or HostIdentityStore()
        self.account_store = account_store or ChatGPTAccountStore()
        self.transport = transport
        self.timeout_seconds = timeout_seconds
        self._discovery: OidcDiscovery | None = None

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout_seconds, transport=self.transport, follow_redirects=False)

    def discovery(self, *, force: bool = False) -> OidcDiscovery:
        if self._discovery is not None and not force:
            return self._discovery
        with self._client() as client:
            response = client.get(DISCOVERY_URL)
        if not response.is_success:
            raise SignInError(f"OpenAI OIDC discovery failed: HTTP {response.status_code}", code="discovery_failed")
        payload = response.json()
        required = ["issuer", "authorization_endpoint", "token_endpoint", "jwks_uri"]
        if any(not isinstance(payload.get(key), str) or not payload[key] for key in required):
            raise SignInError("OpenAI OIDC discovery document is incomplete", code="invalid_discovery")
        if payload["issuer"] != ISSUER:
            raise SignInError("Unexpected OpenAI OIDC issuer", code="invalid_issuer")
        self._discovery = OidcDiscovery(
            issuer=payload["issuer"],
            authorization_endpoint=payload["authorization_endpoint"],
            token_endpoint=payload["token_endpoint"],
            jwks_uri=payload["jwks_uri"],
            revocation_endpoint=payload.get("revocation_endpoint"),
        )
        return self._discovery

    @staticmethod
    def _pkce() -> tuple[str, str]:
        verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return verifier, challenge

    def prepare_authorization(
        self,
        redirect_uri: str,
        *,
        account: ChatGPTAccount | None = None,
    ) -> AuthorizationAttempt:
        discovery = self.discovery()
        verifier, challenge = self._pkce()
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        host_id = self.host_store.get_or_create()
        requested_client_id = account.client_id if account else DYNAMIC_CLIENT_ID
        params: dict[str, str] = {
            "client_id": requested_client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(DEFAULT_SCOPES),
            "resource": RESOURCE,
            "state": state,
            "nonce": nonce,
            "code_challenge_method": "S256",
            "code_challenge": challenge,
            "ext_agent_host_id": host_id,
        }
        expected_subject = None
        if account is None:
            params["agent_name_hint"] = self.app_name
        else:
            expected_subject = account.subject
            if account.id_token:
                params["id_token_hint"] = account.id_token
            if account.email:
                params["login_hint"] = account.email
        url = discovery.authorization_endpoint + "?" + urllib.parse.urlencode(params)
        return AuthorizationAttempt(
            state=state,
            nonce=nonce,
            code_verifier=verifier,
            redirect_uri=redirect_uri,
            requested_client_id=requested_client_id,
            ext_agent_host_id=host_id,
            authorization_url=url,
            expected_subject=expected_subject,
        )

    def exchange_callback(
        self,
        attempt: AuthorizationAttempt,
        callback: dict[str, str],
    ) -> ChatGPTAccount:
        if callback.get("state") != attempt.state:
            raise SignInError("ChatGPT callback state mismatch", code="state_mismatch")
        if callback.get("error"):
            raise SignInError(
                callback.get("error_description") or callback["error"],
                code=callback["error"],
            )
        code = str(callback.get("code") or "")
        if not code:
            raise SignInError("ChatGPT callback did not include an authorization code", code="missing_code")

        if attempt.requested_client_id == DYNAMIC_CLIENT_ID:
            issued_client_id = str(callback.get("client_id") or "")
            if not issued_client_id or issued_client_id == DYNAMIC_CLIENT_ID:
                raise SignInError("Dynamic ChatGPT registration did not return an issued client_id", code="missing_client_id")
        else:
            issued_client_id = attempt.requested_client_id
            returned = callback.get("client_id")
            if returned and returned != issued_client_id:
                raise SignInError("Returning ChatGPT client_id mismatch", code="client_id_mismatch")

        discovery = self.discovery()
        form = {
            "grant_type": "authorization_code",
            "client_id": issued_client_id,
            "code": code,
            "code_verifier": attempt.code_verifier,
            "redirect_uri": attempt.redirect_uri,
            "resource": RESOURCE,
        }
        with self._client() as client:
            response = client.post(discovery.token_endpoint, data=form)
        if not response.is_success:
            raise self._token_error(response, "ChatGPT code exchange failed")
        token = response.json()
        return self._account_from_token(
            token,
            client_id=issued_client_id,
            host_id=attempt.ext_agent_host_id,
            nonce=attempt.nonce,
            expected_subject=attempt.expected_subject,
        )

    def _account_from_token(
        self,
        token: dict[str, Any],
        *,
        client_id: str,
        host_id: str,
        nonce: str | None,
        expected_subject: str | None,
    ) -> ChatGPTAccount:
        access_token = str(token.get("access_token") or "")
        refresh_token = str(token.get("refresh_token") or "")
        id_token = str(token.get("id_token") or "")
        if not access_token or not refresh_token or not id_token:
            raise SignInError("ChatGPT token response is missing required credentials", code="invalid_token_response")

        scopes = sorted({item for item in str(token.get("scope") or "").split() if item})
        if "chatgpt.tokens.use.direct" not in scopes:
            raise SignInError("ChatGPT plan usage permission was not granted", code="plan_scope_missing")

        claims = self.validate_id_token(
            id_token,
            client_id=client_id,
            nonce=nonce,
        )
        subject = str(claims.get("sub") or "")
        if not subject:
            raise SignInError("Validated ChatGPT ID token has no subject", code="id_token_subject_missing")
        if expected_subject is not None and subject != expected_subject:
            raise SignInError("ChatGPT account changed during reauthorization", code="account_mismatch")

        return ChatGPTAccount(
            subject=subject,
            email=str(claims.get("email") or "") or None,
            name=str(claims.get("name") or "") or None,
            issuer=str(claims["iss"]),
            client_id=client_id,
            ext_agent_host_id=host_id,
            id_token=id_token,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=str(token.get("token_type") or "Bearer"),
            expires_in=int(token.get("expires_in") or 3600),
            earliest_refresh_at=int(token["earliest_refresh_at"]) if token.get("earliest_refresh_at") is not None else None,
            scopes=scopes,
            saved_at_unix=int(time.time()),
        )

    def validate_id_token(self, id_token: str, *, client_id: str, nonce: str | None) -> dict[str, Any]:
        discovery = self.discovery()
        try:
            header = jwt.get_unverified_header(id_token)
        except jwt.PyJWTError as error:
            raise SignInError(f"ChatGPT ID token header is invalid: {error}", code="invalid_id_token") from error
        kid = str(header.get("kid") or "")
        algorithm = str(header.get("alg") or "")
        if not kid or algorithm not in {"RS256", "ES256"}:
            raise SignInError("ChatGPT ID token uses an unsupported signing key", code="unsupported_id_token_key")

        with self._client() as client:
            response = client.get(discovery.jwks_uri)
        if not response.is_success:
            raise SignInError("Could not load OpenAI JWKS", code="jwks_unavailable")
        jwks = response.json()
        keys = jwks.get("keys") if isinstance(jwks, dict) else None
        key_data = next((item for item in keys or [] if isinstance(item, dict) and item.get("kid") == kid), None)
        if key_data is None:
            raise SignInError("OpenAI JWKS does not contain the ID-token key", code="jwks_key_missing")
        try:
            key = jwt.PyJWK.from_dict(key_data, algorithm=algorithm).key
            claims = jwt.decode(
                id_token,
                key=key,
                algorithms=[algorithm],
                audience=client_id,
                issuer=discovery.issuer,
                options={"require": ["exp", "iat", "iss", "sub", "aud"]},
            )
        except jwt.PyJWTError as error:
            raise SignInError(f"ChatGPT ID token validation failed: {error}", code="invalid_id_token") from error
        if nonce is not None and claims.get("nonce") != nonce:
            raise SignInError("ChatGPT ID-token nonce mismatch", code="nonce_mismatch")
        return dict(claims)

    def refresh(self, account: ChatGPTAccount) -> ChatGPTAccount:
        if not account.refresh_token:
            raise SignInError("ChatGPT refresh token is unavailable", code="refresh_token_missing")
        with self.account_store.refresh_lock(account.key):
            latest = self.account_store.get(account.key) or account
            if latest.access_token_valid_for(180):
                return latest
            if latest.earliest_refresh_at is not None and int(time.time()) < latest.earliest_refresh_at:
                return latest

            discovery = self.discovery()
            with self._client() as client:
                response = client.post(
                    discovery.token_endpoint,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": latest.client_id,
                        "refresh_token": latest.refresh_token,
                        "resource": RESOURCE,
                    },
                )
            if not response.is_success:
                error = self._token_error(response, "ChatGPT token refresh failed")
                if error.code in {
                    "invalid_grant",
                    "invalid_refresh_token",
                    "token_expired",
                    "refresh_token_expired",
                    "refresh_token_invalidated",
                    "refresh_token_reused",
                }:
                    self.account_store.clear_tokens(latest.key)
                raise error

            token = response.json()
            access_token = str(token.get("access_token") or "")
            replacement_refresh = str(token.get("refresh_token") or "")
            if not access_token or not replacement_refresh:
                raise SignInError(
                    "ChatGPT refresh response is missing replacement credentials",
                    code="invalid_refresh_response",
                )
            raw_scope = str(token.get("scope") or "").strip()
            scopes = sorted({item for item in raw_scope.split() if item}) if raw_scope else list(latest.scopes)
            if "chatgpt.tokens.use.direct" not in scopes:
                raise SignInError(
                    "ChatGPT plan usage permission is no longer granted",
                    code="plan_scope_missing",
                )

            replacement_id_token = str(token.get("id_token") or "")
            if replacement_id_token:
                claims = self.validate_id_token(
                    replacement_id_token,
                    client_id=latest.client_id,
                    nonce=None,
                )
                if str(claims.get("sub") or "") != latest.subject:
                    raise SignInError(
                        "ChatGPT account changed during token refresh",
                        code="account_mismatch",
                    )
                id_token = replacement_id_token
                email = str(claims.get("email") or "") or latest.email
                name = str(claims.get("name") or "") or latest.name
                issuer = str(claims.get("iss") or latest.issuer)
            else:
                id_token = latest.id_token
                email = latest.email
                name = latest.name
                issuer = latest.issuer

            refreshed = ChatGPTAccount(
                subject=latest.subject,
                email=email,
                name=name,
                issuer=issuer,
                client_id=latest.client_id,
                ext_agent_host_id=latest.ext_agent_host_id,
                id_token=id_token,
                access_token=access_token,
                refresh_token=replacement_refresh,
                token_type=str(token.get("token_type") or latest.token_type or "Bearer"),
                expires_in=int(token.get("expires_in") or 3600),
                earliest_refresh_at=int(token["earliest_refresh_at"]) if token.get("earliest_refresh_at") is not None else None,
                scopes=scopes,
                saved_at_unix=int(time.time()),
            )
            return self.account_store.save(refreshed, select=True)

    def access_token(self, account_key: str | None = None) -> str:
        account = self.account_store.get(account_key) if account_key else self.account_store.selected()
        if account is None:
            raise SignInError("No ChatGPT account is connected", code="account_missing")
        if not account.access_token_valid_for(180):
            account = self.refresh(account)
        if not account.access_token:
            raise SignInError("ChatGPT access token is unavailable", code="access_token_missing")
        return account.access_token

    def sign_in_interactive(
        self,
        *,
        account: ChatGPTAccount | None = None,
        timeout_seconds: float = 300,
        browser_open: Callable[[str], Any] = webbrowser.open,
    ) -> ChatGPTAccount:
        callback = LoopbackCallback()
        callback.start()
        try:
            attempt = self.prepare_authorization(callback.redirect_uri, account=account)
            opened = browser_open(attempt.authorization_url)
            if opened is False:
                raise SignInError("Could not open the system browser", code="browser_open_failed")
            params = callback.wait(timeout_seconds)
            connected = self.exchange_callback(attempt, params)
            return self.account_store.save(connected, select=True)
        finally:
            callback.close()

    def revoke(self, account: ChatGPTAccount) -> bool:
        discovery = self.discovery()
        if not discovery.revocation_endpoint or not account.refresh_token:
            self.account_store.clear_tokens(account.key)
            return False
        confirmed = False
        try:
            with self._client() as client:
                response = client.post(
                    discovery.revocation_endpoint,
                    data={
                        "token": account.refresh_token,
                        "token_type_hint": "refresh_token",
                        "client_id": account.client_id,
                    },
                )
            confirmed = response.status_code == 200
        except httpx.HTTPError:
            confirmed = False
        finally:
            self.account_store.clear_tokens(account.key)
        return confirmed

    @staticmethod
    def _token_error(response: httpx.Response, prefix: str) -> SignInError:
        code = None
        description = ""
        try:
            payload = response.json()
            if isinstance(payload, dict):
                code = str(payload.get("error") or "") or None
                description = str(payload.get("error_description") or "")
                if isinstance(payload.get("error"), dict):
                    error = payload["error"]
                    code = str(error.get("code") or "") or code
                    description = str(error.get("message") or "") or description
        except ValueError:
            description = response.text[-1000:]
        message = prefix + (f": {description}" if description else "")
        return SignInError(message, code=code)
