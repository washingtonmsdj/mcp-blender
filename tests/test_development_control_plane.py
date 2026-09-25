from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import unittest
import httpx
from pathlib import Path

from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.control_plane import build_control_plane
from ordax_dev_agent.development_control_plane import DevelopmentControlPlane, DeviceAuthorizationError


DEVICE_ID = "11111111-1111-4111-8111-111111111111"


def make_config(root: Path) -> AgentConfig:
    return AgentConfig(
        agent_name="test-agent",
        supabase_url="https://example.supabase.co",
        publishable_key=None,
        poll_seconds=1.0,
        state_dir=root / "state",
        agent_repo_path=root / "agent",
        hordax_path=root / "hordax",
        bridge_path=root / "bridge",
        control_plane_protocol="development-v2",
        development_device_id=DEVICE_ID,
    )


class DevelopmentControlPlaneTests(unittest.TestCase):
    def test_revoked_token_requests_supervisor_recovery(self):
        control = object.__new__(DevelopmentControlPlane)
        control.device_id = DEVICE_ID
        control.endpoint = 'https://example.supabase.co/functions/v1/device'
        with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(401, json={'error':'invalid_device_token'}))) as client:
            control.http = client
            with self.assertRaises(DeviceAuthorizationError):
                control._call('heartbeat')

    def test_v2_builder_uses_device_scoped_local_credential(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = root / "state"
            state.mkdir()
            (state / "device-token.txt").write_text("a" * 64 + "\n", encoding="utf-8")

            control = build_control_plane(make_config(root))

            self.assertIsInstance(control, DevelopmentControlPlane)
            self.assertEqual(control.device_id, DEVICE_ID)
            self.assertEqual(control.device_token, "a" * 64)
            self.assertTrue(control.endpoint.endswith("/functions/v1/ordax-development-device"))

    def test_payload_digest_is_verified_before_json_dispatch(self) -> None:
        payload = {"action": "blender.live_status", "payload": {}, "project": "scene"}
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        row = {
            "payload_canonical_b64": base64.b64encode(raw).decode("ascii"),
            "payload_sha256": hashlib.sha256(raw).hexdigest(),
        }

        self.assertEqual(DevelopmentControlPlane._decode_payload(row), payload)

        row["payload_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "digest mismatch"):
            DevelopmentControlPlane._decode_payload(row)

    def test_adapter_envelope_maps_only_typed_device_agent_action(self) -> None:
        action, payload, project = DevelopmentControlPlane._dispatch(
            {"capability": "ordax.dev.adapter.invoke"},
            {
                "adapter": "blender",
                "action": "blender.live_inspect",
                "payload": {"limit": 25},
                "project": "cerco-no-interior-mvp",
            },
        )
        self.assertEqual(action, "blender.live_inspect")
        self.assertEqual(payload, {"limit": 25})
        self.assertEqual(project, "cerco-no-interior-mvp")

    def test_system_capability_is_not_owned_by_windows_device_agent(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not owned by Device Agent"):
            DevelopmentControlPlane._dispatch(
                {"capability": "ordax.dev.system.exec"},
                {"script_b64": "AAAA"},
            )

    def test_adapter_envelope_rejects_unknown_fields(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "unsupported fields"):
            DevelopmentControlPlane._dispatch(
                {"capability": "ordax.dev.adapter.invoke"},
                {
                    "adapter": "blender",
                    "action": "blender.live_status",
                    "payload": {},
                    "project": "scene",
                    "shell": "powershell",
                },
            )


if __name__ == "__main__":
    unittest.main()
