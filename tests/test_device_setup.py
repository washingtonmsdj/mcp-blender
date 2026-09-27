import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import httpx

from ordax_dev_agent.device_setup import CONTROL_PLANE, SetupError, configure, setup_lock


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / 'state'
        self.home = Path(self.temp.name) / 'home'
        self.state.mkdir()
        (self.home / 'Documents/github/cerco-no-interior-mvp').mkdir(parents=True)
        self.devices = {
            'development-v2': str(uuid.uuid4()),
            'cloudflare-v3': str(uuid.uuid4()),
        }
        self.device = self.devices['development-v2']
        self.binding = 'a' * 64
        self.credential_hashes = {
            'development-v2': None,
            'cloudflare-v3': None,
        }
        self.enrollments = 0
        self.protocol = 'development-v2'
        self.calls = []
        self.offline = False
        self.lost_ack = False
        self.mismatch = False
        self.auth = patch('ordax_dev_agent.device_setup.github_token', return_value='github-private')
        self.auth_mock = self.auth.start()
        self.addCleanup(self.auth.stop)
        self.acl = patch('ordax_dev_agent.device_setup.private_directory', side_effect=lambda p: p.mkdir(exist_ok=True))
        self.acl.start()
        self.addCleanup(self.acl.stop)
        self.client = httpx.Client(transport=httpx.MockTransport(self.server))
        self.addCleanup(self.client.close)

    def server(self, req):
        if self.offline:
            raise httpx.ConnectError('offline')
        body = json.loads(req.content)
        self.calls.append(body)
        self.last_request_path = req.url.path
        request_protocol = (
            'cloudflare-v3'
            if req.url.path == '/v3/device/setup'
            else 'development-v2'
        )
        if body['operation'] == 'enroll':
            self.assertEqual('Bearer github-private', req.headers['Authorization'])
            self.assertNotIn('token', body)
            self.credential_hashes[request_protocol] = body['token_sha256']
            self.enrollments += 1
            if self.lost_ack:
                self.lost_ack = False
                raise httpx.ReadTimeout('ack lost after commit')
        elif self.mismatch:
            return httpx.Response(403, json={'ok': False})
        elif (
            hashlib.sha256(
                req.headers['X-Ordax-Device-Token'].encode()
            ).hexdigest()
            != self.credential_hashes[request_protocol]
        ):
            return httpx.Response(401, json={'ok': False})
        return httpx.Response(
            200,
            json={
                'ok': True,
                'protocol': request_protocol,
                'device_id': self.devices[request_protocol],
            },
        )

    def run_setup(self, **kwargs):
        return configure(
            self.state,
            client=self.client,
            binding=self.binding,
            home=self.home,
            **kwargs,
        )

    def test_new_machine_and_ten_idempotent_runs(self):
        self.run_setup()
        token_path = self.state / 'device-token.development-v2.txt'
        token = token_path.read_text()
        for _ in range(10):
            self.assertEqual(self.device, self.run_setup()['device_id'])
        self.assertEqual(1, self.enrollments)
        self.assertEqual(token, token_path.read_text())
        self.assertEqual(1, self.auth_mock.call_count)
        settings = json.loads((self.state / 'agent-settings.json').read_text())
        self.assertEqual(CONTROL_PLANE, settings['supabase_url'])
        self.assertIn('cerco-no-interior-mvp', settings['projects'])

    def test_lost_response_reuses_committed_pending_token(self):
        self.lost_ack = True
        with self.assertRaises(SetupError):
            self.run_setup()
        pending = (
            self.state / 'device-token.development-v2.txt.pending-setup'
        ).read_text()
        self.run_setup()
        self.assertEqual(
            pending,
            (self.state / 'device-token.development-v2.txt').read_text(),
        )
        self.assertEqual(1, self.enrollments)

    def test_revoked_token_reenrolls_and_preserves_device(self):
        self.run_setup()
        token_path = self.state / 'device-token.development-v2.txt'
        old = token_path.read_text()
        self.credential_hashes['development-v2'] = None
        self.assertEqual(self.device, self.run_setup()['device_id'])
        self.assertNotEqual(old, token_path.read_text())

    def test_missing_token_recovers_same_machine(self):
        self.run_setup()
        (self.state / 'device-token.development-v2.txt').unlink()
        self.assertEqual(self.device, self.run_setup()['device_id'])
        self.assertEqual(2, self.enrollments)

    def test_offline_never_rotates_or_changes_settings(self):
        self.run_setup()
        before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        self.offline = True
        with self.assertRaisesRegex(SetupError, 'UNAVAILABLE'):
            self.run_setup()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.state.iterdir()})
        self.assertEqual(1, self.enrollments)

    def test_other_machine_token_is_refused(self):
        self.run_setup()
        self.mismatch = True
        with self.assertRaisesRegex(SetupError, 'MACHINE_BINDING_MISMATCH'):
            self.run_setup()
        self.assertEqual(1, self.enrollments)

    def test_legacy_settings_and_existing_project_customization_preserved(self):
        custom = {'path': 'D:/custom', 'apps': ['blender']}
        (self.state / 'agent-settings.json').write_text(json.dumps({
            'publishable_key': 'public-key', 'custom': 123,
            'projects': {'cerco-no-interior-mvp': custom}}))
        self.run_setup()
        settings = json.loads((self.state / 'agent-settings.json').read_text())
        self.assertEqual(custom, settings['projects']['cerco-no-interior-mvp'])
        self.assertEqual(123, settings['custom'])
        self.assertEqual('development-v2', settings['control_plane_protocol'])


    def test_cloudflare_v3_enrollment_preserves_projects_and_uses_provider_url(self):
        self.protocol = 'cloudflare-v3'
        result = self.run_setup(
            protocol='cloudflare-v3',
            control_plane_url='https://control.example',
        )
        self.assertEqual('cloudflare-v3', result['protocol'])
        settings = json.loads((self.state / 'agent-settings.json').read_text())
        self.assertEqual('cloudflare-v3', settings['control_plane_protocol'])
        self.assertEqual('https://control.example', settings['control_plane_url'])
        self.assertEqual(
            self.devices['cloudflare-v3'],
            settings['development_device_id'],
        )
        self.assertIn('cerco-no-interior-mvp', settings['projects'])
        self.assertEqual('/v3/device/setup', self.last_request_path)
        self.assertEqual(
            self.devices['cloudflare-v3'],
            settings['control_plane_identities']['cloudflare-v3']['device_id'],
        )

    def test_provider_switch_preserves_both_credentials_and_identities(self):
        v2 = self.run_setup()
        v2_token = (
            self.state / 'device-token.development-v2.txt'
        ).read_text()

        v3 = self.run_setup(
            protocol='cloudflare-v3',
            control_plane_url='https://control.example',
        )
        v3_token = (
            self.state / 'device-token.cloudflare-v3.txt'
        ).read_text()

        self.assertEqual(self.devices['development-v2'], v2['device_id'])
        self.assertEqual(self.devices['cloudflare-v3'], v3['device_id'])
        self.assertNotEqual(v2_token, v3_token)
        self.assertEqual(
            v2_token,
            (self.state / 'device-token.development-v2.txt').read_text(),
        )

        settings = json.loads((self.state / 'agent-settings.json').read_text())
        identities = settings['control_plane_identities']
        self.assertEqual(
            self.devices['development-v2'],
            identities['development-v2']['device_id'],
        )
        self.assertEqual(
            self.devices['cloudflare-v3'],
            identities['cloudflare-v3']['device_id'],
        )

        back = self.run_setup(protocol='development-v2')
        self.assertEqual(self.devices['development-v2'], back['device_id'])
        self.assertEqual(
            v3_token,
            (self.state / 'device-token.cloudflare-v3.txt').read_text(),
        )

    def test_legacy_v2_token_is_migrated_once(self):
        legacy = self.state / 'device-token.txt'
        legacy.write_text('a' * 64)
        self.credential_hashes['development-v2'] = hashlib.sha256(
            ('a' * 64).encode()
        ).hexdigest()

        result = self.run_setup()

        self.assertEqual(self.devices['development-v2'], result['device_id'])
        self.assertFalse(legacy.exists())
        self.assertEqual(
            'a' * 64,
            (self.state / 'device-token.development-v2.txt').read_text(),
        )
        self.assertEqual(0, self.auth_mock.call_count)

    def test_cloudflare_v3_requires_https_outside_loopback(self):
        with self.assertRaisesRegex(SetupError, 'CONTROL_PLANE_URL_INVALID'):
            self.run_setup(
                protocol='cloudflare-v3',
                control_plane_url='http://control.example',
            )
        self.assertEqual([], self.calls)

    def test_cloudflare_v3_allows_loopback_http_for_local_verification(self):
        self.protocol = 'cloudflare-v3'
        result = self.run_setup(
            protocol='cloudflare-v3',
            control_plane_url='http://127.0.0.1:8787',
        )
        self.assertEqual('cloudflare-v3', result['protocol'])

    def test_corrupt_settings_are_not_overwritten(self):
        (self.state / 'agent-settings.json').write_text('{broken')
        with self.assertRaisesRegex(SetupError, 'SETTINGS_INVALID_PRESERVED'):
            self.run_setup()
        self.assertEqual([], self.calls)

    def test_failed_acl_prevents_network_and_secret_creation(self):
        with patch('ordax_dev_agent.device_setup.private_directory', side_effect=SetupError('PRIVATE_ACL_FAILED')):
            with self.assertRaisesRegex(SetupError, 'ACL'):
                self.run_setup()
        self.assertEqual([], self.calls)
        self.assertEqual([], list(self.state.iterdir()))

    def test_concurrent_supervisor_and_setup_cannot_rotate_twice(self):
        with setup_lock(self.state):
            with self.assertRaisesRegex(SetupError, 'SETUP_ALREADY_RUNNING'):
                self.run_setup()
        self.assertEqual([], self.calls)
        self.run_setup()
        self.assertEqual(1, self.enrollments)


if __name__ == '__main__':
    unittest.main()
