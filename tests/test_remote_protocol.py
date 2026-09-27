from __future__ import annotations

import base64
import hashlib
import json
import unittest
from pathlib import Path

from ordax_dev_agent.models import ActionResult
from ordax_dev_agent.remote_protocol import (
    canonical_result,
    decode_job_payload,
    dispatch_job,
)


class ProviderNeutralRemoteProtocolTests(unittest.TestCase):
    def test_cloudflare_transport_does_not_import_development_v2(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / "ordax_dev_agent" / "cloudflare_control_plane.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("development_control_plane", source)
        self.assertNotIn("DevelopmentControlPlane", source)
        self.assertIn("from .remote_protocol import", source)

    def test_digest_dispatch_and_result_are_provider_neutral(self) -> None:
        payload = {"project": "scene", "limit": 12}
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        row = {
            "capability": "blender.live_inspect",
            "payload_canonical_b64": base64.b64encode(raw).decode("ascii"),
            "payload_sha256": hashlib.sha256(raw).hexdigest(),
        }

        decoded = decode_job_payload(row)
        action, action_payload, project = dispatch_job(row, decoded)
        body, digest = canonical_result(
            ActionResult(True, "ok", {"transport": "provider-neutral"})
        )

        self.assertEqual(decoded, payload)
        self.assertEqual(action, "blender.live_inspect")
        self.assertEqual(action_payload, payload)
        self.assertEqual(project, "scene")
        self.assertEqual(body["data"]["transport"], "provider-neutral")
        self.assertEqual(len(digest), 64)

    def test_digest_mismatch_fails_before_dispatch(self) -> None:
        raw = b"{}"
        row = {
            "capability": "agent.status",
            "payload_canonical_b64": base64.b64encode(raw).decode("ascii"),
            "payload_sha256": "0" * 64,
        }
        with self.assertRaisesRegex(RuntimeError, "digest mismatch"):
            decode_job_payload(row)


if __name__ == "__main__":
    unittest.main()
