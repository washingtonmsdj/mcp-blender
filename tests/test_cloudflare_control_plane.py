from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import unittest
from unittest.mock import call, patch
from pathlib import Path

from ordax_dev_agent.cloudflare_control_plane import CloudflareControlPlane
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.control_plane import build_control_plane
from ordax_dev_agent.models import ActionResult, AgentJob
from ordax_dev_agent.remote_protocol import TransientDeliveryError


DEVICE_ID = "22222222-2222-4222-8222-222222222222"


def make_config(root: Path, *, url: str = "https://control.example") -> AgentConfig:
    return AgentConfig(
        agent_name="test-agent",
        supabase_url=None,
        poll_seconds=1.0,
        state_dir=root / "state",
        agent_repo_path=root / "agent",
        hordax_path=root / "hordax",
        bridge_path=root / "bridge",
        control_plane_protocol="cloudflare-v3",
        development_device_id=DEVICE_ID,
        control_plane_url=url,
    )


def write_token(root: Path) -> None:
    state = root / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "device-token.cloudflare-v3.txt").write_text(
        "c" * 64 + "\n", encoding="utf-8"
    )


class CloudflareControlPlaneTests(unittest.TestCase):
    def test_builder_requires_no_supabase_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_token(root)

            control = build_control_plane(make_config(root))

            self.assertIsInstance(control, CloudflareControlPlane)
            self.assertEqual(control.device_id, DEVICE_ID)
            self.assertEqual(
                control.ws_url,
                f"wss://control.example/v3/device/ws?device_id={DEVICE_ID}",
            )

    def test_ws_url_preserves_control_plane_path_prefix(self) -> None:
        url = CloudflareControlPlane._make_ws_url(
            "https://example.workers.dev/ordax",
            DEVICE_ID,
        )
        self.assertEqual(
            url,
            f"wss://example.workers.dev/ordax/v3/device/ws?device_id={DEVICE_ID}",
        )

    def test_invalid_control_plane_url_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_token(root)
            with self.assertRaisesRegex(RuntimeError, "absolute HTTP"):
                CloudflareControlPlane(make_config(root, url="file:///tmp/control"))

    def test_complete_retries_identical_terminal_report_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_token(root)
            control = CloudflareControlPlane(make_config(root))
            job = AgentJob(
                id="33333333-3333-4333-8333-333333333333",
                action="agent.status",
                payload={},
                lease_token="66666666-6666-4666-8666-666666666666",
                effect_id="44444444-4444-4444-8444-444444444444",
                attempt_id="55555555-5555-4555-8555-555555555555",
                execution_epoch=1,
                agent_instance_id=control.agent_instance_id,
                boot_id=control.boot_id,
            )
            control._jobs[job.id] = job
            reports: list[dict] = []

            def flaky_rpc(operation, payload=None, **_kwargs):
                self.assertEqual(operation, "report")
                reports.append(json.loads(json.dumps(payload)))
                if len(reports) < 3:
                    raise TransientDeliveryError("simulated lost ACK")
                return {"type": "ack", "ok": True}

            control._rpc = flaky_rpc  # type: ignore[method-assign]

            with patch("ordax_dev_agent.cloudflare_control_plane.time.sleep") as sleep:
                control.complete(
                    job,
                    ActionResult(True, "ok", {"transport": "cloudflare-v3"}),
                )

            self.assertEqual(len(reports), 3)
            self.assertEqual(reports[0], reports[1])
            self.assertEqual(reports[1], reports[2])
            self.assertEqual(
                {report["report_id"] for report in reports},
                {reports[0]["report_id"]},
            )
            sleep.assert_has_calls([call(1), call(2)])
            self.assertNotIn(job.id, control._jobs)

    def test_failed_terminal_delivery_survives_process_and_recovers_before_claim(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_token(root)
            control = CloudflareControlPlane(make_config(root))
            job = AgentJob(
                id="33333333-3333-4333-8333-333333333333",
                action="agent.status",
                payload={},
                lease_token="66666666-6666-4666-8666-666666666666",
                effect_id="44444444-4444-4444-8444-444444444444",
                attempt_id="55555555-5555-4555-8555-555555555555",
                execution_epoch=1,
                agent_instance_id=control.agent_instance_id,
                boot_id=control.boot_id,
            )
            control._jobs[job.id] = job

            def offline_rpc(*_args, **_kwargs):
                raise TransientDeliveryError("offline")

            control._rpc = offline_rpc  # type: ignore[method-assign]
            with patch("ordax_dev_agent.cloudflare_control_plane.time.sleep"):
                with self.assertRaises(TransientDeliveryError):
                    control.complete(job, ActionResult(True, "executed", {}))

            pending = control._terminal_outbox.pending()
            self.assertEqual(len(pending), 1)
            persisted_report = pending[0][1]
            self.assertEqual(persisted_report["job_id"], job.id)
            self.assertIn(job.id, control._jobs)

            restarted = CloudflareControlPlane(make_config(root))
            recovered: list[dict] = []
            restarted._recover_terminal_report = (  # type: ignore[method-assign]
                lambda report: recovered.append(json.loads(json.dumps(report)))
                or {"ok": True, "recovered": True}
            )

            self.assertEqual(restarted.recover_pending_reports(), 1)
            self.assertEqual(recovered, [persisted_report])
            self.assertEqual(restarted._terminal_outbox.pending(), [])

    def test_claim_recovers_outbox_before_opening_websocket(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_token(root)
            control = CloudflareControlPlane(make_config(root))
            calls: list[str] = []
            control.recover_pending_reports = (  # type: ignore[method-assign]
                lambda: calls.append("recover") or 0
            )

            def socket_should_follow_recovery():
                calls.append("socket")
                raise TimeoutError

            control._ensure_socket = socket_should_follow_recovery  # type: ignore[method-assign]

            with self.assertRaises(TimeoutError):
                control.claim_next_job()

            self.assertEqual(calls, ["recover", "socket"])

    def test_worker_never_releases_expired_running_job_automatically(self) -> None:
        root = Path(__file__).resolve().parents[1]
        worker = (
            root / "control-plane" / "cloudflare" / "src" / "index.ts"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "status = 'queued' OR (status = 'leased' AND lease_expires_at < ?2)",
            worker,
        )
        self.assertNotIn(
            "status IN ('leased','running') AND lease_expires_at < ?2",
            worker,
        )
        self.assertIn("/v3/device/recover-report", worker)
        self.assertIn("execution_context_superseded", worker)

    def test_job_envelope_reuses_v2_digest_and_action_contract(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write_token(root)
            control = CloudflareControlPlane(make_config(root))
            control._rpc = lambda *_args, **_kwargs: {"ok": True}  # type: ignore[method-assign]

            payload = {"project": "scene", "limit": 20}
            encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            message = {
                "type": "job",
                "job": {
                    "job_id": "33333333-3333-4333-8333-333333333333",
                    "capability": "blender.live_inspect",
                    "payload_canonical_b64": base64.b64encode(encoded).decode("ascii"),
                    "payload_sha256": hashlib.sha256(encoded).hexdigest(),
                    "effect_id": "44444444-4444-4444-8444-444444444444",
                    "attempt_id": "55555555-5555-4555-8555-555555555555",
                    "lease_id": "66666666-6666-4666-8666-666666666666",
                    "execution_epoch": 1,
                },
            }

            job = control._job_from_message(message)

            self.assertEqual(job.action, "blender.live_inspect")
            self.assertEqual(job.project_slug, "scene")
            self.assertEqual(job.payload, payload)
            self.assertEqual(job.lease_token, "66666666-6666-4666-8666-666666666666")


if __name__ == "__main__":
    unittest.main()
