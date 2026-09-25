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
        self.device = str(uuid.uuid4())
        self.binding = 'a' * 64
        self.credential_hash = None
        self.enrollments = 0
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
        if body['operation'] == 'enroll':
            self.assertEqual('Bearer github-private', req.headers['Authorization'])
            self.assertNotIn('token', body)
            self.credential_hash = body['token_sha256']
            self.enrollments += 1
            if self.lost_ack:
                self.lost_ack = False
                raise httpx.ReadTimeout('ack lost after commit')
        elif self.mismatch:
            return httpx.Response(403, json={'ok': False})
        elif hashlib.sha256(req.headers['X-Ordax-Device-Token'].encode()).hexdigest() != self.credential_hash:
            return httpx.Response(401, json={'ok': False})
        return httpx.Response(200, json={'ok': True, 'protocol': 'development-v2', 'device_id': self.device})

    def run_setup(self):
        return configure(self.state, client=self.client, binding=self.binding, home=self.home)

    def test_new_machine_and_ten_idempotent_runs(self):
        self.run_setup()
        token = (self.state / 'device-token.txt').read_text()
        for _ in range(10):
            self.assertEqual(self.device, self.run_setup()['device_id'])
        self.assertEqual(1, self.enrollments)
        self.assertEqual(token, (self.state / 'device-token.txt').read_text())
        self.assertEqual(1, self.auth_mock.call_count)
        settings = json.loads((self.state / 'agent-settings.json').read_text())
        self.assertEqual(CONTROL_PLANE, settings['supabase_url'])
        self.assertIn('cerco-no-interior-mvp', settings['projects'])

    def test_lost_response_reuses_committed_pending_token(self):
        self.lost_ack = True
        with self.assertRaises(SetupError):
            self.run_setup()
        pending = (self.state / 'device-token.txt.pending-setup').read_text()
        self.run_setup()
        self.assertEqual(pending, (self.state / 'device-token.txt').read_text())
        self.assertEqual(1, self.enrollments)

    def test_revoked_token_reenrolls_and_preserves_device(self):
        self.run_setup()
        old = (self.state / 'device-token.txt').read_text()
        self.credential_hash = None
        self.assertEqual(self.device, self.run_setup()['device_id'])
        self.assertNotEqual(old, (self.state / 'device-token.txt').read_text())

    def test_missing_token_recovers_same_machine(self):
        self.run_setup()
        (self.state / 'device-token.txt').unlink()
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
