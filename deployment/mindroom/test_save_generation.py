"""Exercise the installed MindRoom save/reload path without production state."""

import asyncio
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi import FastAPI, HTTPException, Request
import yaml

from mindroom import constants
from mindroom.agent_reply_membership import AgentReplyMembershipIndex
from mindroom.api import config_lifecycle as lifecycle, main
from mindroom.orchestration.external_trigger_runtime import ExternalTriggerRuntimeCoordinator


class SaveGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.paths = constants.RuntimePaths(
            config_path=root / "config.yaml",
            config_dir=root,
            env_path=root / ".env",
            storage_root=root / "storage",
        )
        self.app = FastAPI()
        main.initialize_api_app(self.app, self.paths)
        self.save({
            "agents": {"probe": {
                "display_name": "Probe", "role": "Initial role", "tools": [], "rooms": [],
            }},
            "models": {"default": {"provider": "openai", "id": "gpt-4o-mini"}},
        })

    @property
    def snapshot(self):
        return lifecycle.require_api_state(self.app).snapshot

    def request(self):
        return Request({"type": "http", "app": self.app, "headers": []})

    def save(self, payload, generation=None, request=None):
        return lifecycle.replace_committed_config(
            request or self.request(), payload,
            error_prefix="test save", expected_generation=generation,
        )

    def reload(self):
        coordinator = ExternalTriggerRuntimeCoordinator(
            self.paths, AgentReplyMembershipIndex(),
        )
        runtime_config = self.snapshot.runtime_config
        with patch.object(main, "app", self.app):
            asyncio.run(coordinator.sync_api_config_snapshot(runtime_config))

    def test_consecutive_edits_survive_hot_reload(self):
        generation = self.snapshot.generation
        for role in ("First saved edit", "Second saved edit", "Third saved edit"):
            payload = deepcopy(self.snapshot.config_data)
            payload["agents"]["probe"]["role"] = role
            generation = self.save(payload, generation)
            saved_payload = deepcopy(self.snapshot.config_data)
            revision = self.snapshot.revision
            self.reload()
            self.assertEqual(self.snapshot.generation, generation)
            self.assertEqual(self.snapshot.config_data, saved_payload)
            self.assertGreater(self.snapshot.revision, revision)

    def test_competing_editor_still_gets_conflict(self):
        stale_generation = self.snapshot.generation
        stale_payload = deepcopy(self.snapshot.config_data)
        newer_payload = deepcopy(stale_payload)
        newer_payload["agents"]["probe"]["role"] = "Other editor's change"
        self.save(newer_payload, stale_generation)
        self.reload()
        with self.assertRaises(HTTPException) as caught:
            self.save(stale_payload, stale_generation)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.snapshot.config_data["agents"]["probe"]["role"],
                         "Other editor's change")

    def test_external_file_edit_still_invalidates_draft(self):
        generation = self.snapshot.generation
        payload = deepcopy(self.snapshot.config_data)
        external = deepcopy(payload)
        external["agents"]["probe"]["role"] = "External file edit"
        self.paths.config_path.write_text(yaml.safe_dump(external))
        self.assertTrue(lifecycle.load_config_into_app(self.paths, self.app))
        self.assertGreater(self.snapshot.generation, generation)
        with self.assertRaises(HTTPException) as caught:
            self.save(payload, generation)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.snapshot.config_data["agents"]["probe"]["role"],
                         "External file edit")

    def test_runtime_swap_still_invalidates_draft_and_auth(self):
        before = self.snapshot
        before.auth_state = object()
        main.initialize_api_app(
            self.app, replace(self.paths, config_path=self.paths.config_dir / "other.yaml"),
        )
        self.assertGreater(self.snapshot.generation, before.generation)
        self.assertGreater(self.snapshot.revision, before.revision)
        self.assertEqual(self.snapshot.config_data, {})
        self.assertIsNone(self.snapshot.auth_state)

    def test_same_runtime_preserves_generation_auth_and_revision_guard(self):
        before = self.snapshot
        before.auth_state = object()
        pinned_request = self.request()
        pinned_request.scope["api_snapshot"] = before
        main.initialize_api_app(self.app, self.paths)
        self.assertEqual(self.snapshot.generation, before.generation)
        self.assertIs(self.snapshot.auth_state, before.auth_state)
        self.assertGreater(self.snapshot.revision, before.revision)
        with self.assertRaises(HTTPException) as caught:
            self.save(before.config_data, before.generation, pinned_request)
        self.assertEqual(caught.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main(verbosity=2)
