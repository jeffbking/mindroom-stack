from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from bootstrap_runtime import bootstrap_runtime
import quickstart
import stack_smoke_test as smoke


class PrivateDeploymentTest(unittest.TestCase):
    def test_missing_env_uses_private_template_and_stops_before_startup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deployment").mkdir()
            template = root / "deployment/deployment.env.example"
            template.write_text("META_API_KEY=\nMATRIX_REGISTRATION_TOKEN=\n")
            env_file = root / ".env"
            with patch.object(quickstart, "STACK_ROOT", root), patch.object(quickstart, "ENV_FILE", env_file):
                with self.assertRaisesRegex(quickstart.QuickstartError, "META_API_KEY and MATRIX_REGISTRATION_TOKEN"):
                    quickstart._ensure_env_file()
            self.assertEqual(env_file.read_text(), template.read_text())
            self.assertEqual(env_file.stat().st_mode & 0o777, 0o600)

    def test_bootstrap_seeds_missing_files_and_preserves_live_edits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "deployment").mkdir()
            (root / "deployment/config.yaml").write_text("initial config")
            (root / "mind_data/memory").mkdir(parents=True)
            (root / "mind_data/SOUL.md").write_text("initial identity")
            (root / "mind_data/memory/seed.md").write_text("seed memory")
            bootstrap_runtime(root)
            config = root / "runtime/config/config.yaml"
            identity = root / "runtime/workspace/SOUL.md"
            self.assertEqual(config.read_text(), "initial config")
            self.assertEqual(identity.read_text(), "initial identity")
            config.write_text("dashboard changes")
            identity.write_text("agent changes")
            (root / "runtime/workspace/memory/seed.md").unlink()
            bootstrap_runtime(root)
            self.assertEqual(config.read_text(), "dashboard changes")
            self.assertEqual(identity.read_text(), "agent changes")
            self.assertEqual((root / "runtime/workspace/memory/seed.md").read_text(), "seed memory")

    def test_owner_session_logs_out_on_success_and_failures(self) -> None:
        for failure in (None, "join", "reply", "restart"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
                credentials = Path(directory) / "credentials.json"
                credentials.write_text(json.dumps({"user_id": "@owner:test", "password": "test-password"}))
                args = argparse.Namespace(
                    homeserver="https://matrix.test", client_url="https://chat.test",
                    dashboard_url="https://admin.test", client_homeserver_url="https://matrix.test",
                    timeout_seconds=1, credentials_file=str(credentials),
                    assistant_room_alias="#lobby:test", mind_room_alias="#personal:test",
                    assistant_user_id="@assistant:test", mind_user_id="@mind:test", restart_check=True,
                )
                requests = []

                def request(method, url, **kwargs):
                    requests.append((url, kwargs.get("token")))
                    if url.endswith("/login"):
                        return {"user_id": "@owner:test", "access_token": "temporary-session"}
                    if failure == "join" and "/join/" in url:
                        raise smoke.SmokeTestError("join failed")
                    return {}

                stack.enter_context(patch.object(smoke, "_request_json", side_effect=request))
                for name in ("_wait_for_stack_health", "_wait_for_room_aliases"):
                    stack.enter_context(patch.object(smoke, name))
                stack.enter_context(patch.object(smoke, "_resolve_and_wait_for_autojoin", return_value="!room:test"))
                stack.enter_context(patch.object(smoke, "_sync", return_value={"next_batch": "cursor"}))
                stack.enter_context(patch.object(smoke, "_joined_rooms", return_value=["!room:test"]))
                for name, stage in (("_exercise_agent_reply", "reply"), ("_restart_stack", "restart")):
                    stack.enter_context(patch.object(
                        smoke, name,
                        side_effect=smoke.SmokeTestError(stage + " failed") if failure == stage else None,
                    ))
                if failure:
                    with self.assertRaises(smoke.SmokeTestError):
                        smoke.run(args)
                else:
                    smoke.run(args)
                self.assertEqual(requests[-1], ("https://matrix.test/_matrix/client/v3/logout", "temporary-session"))
                self.assertEqual(sum(url.endswith("/logout") for url, _ in requests), 1)


if __name__ == "__main__":
    unittest.main()
