"""Verify MiMo dispatch, credential isolation, and tool replay without network I/O."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from agno.exceptions import ModelAuthenticationError
from agno.models.message import Message
from agno.models.xiaomi import MiMo

from mindroom.config.main import Config
from mindroom.constants import RuntimePaths
from mindroom.credentials import get_runtime_shared_credentials_manager
from mindroom.model_loading import get_model_instance


class MiMoIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.paths = RuntimePaths(
            config_path=root / "config.yaml", config_dir=root,
            env_path=root / ".env", storage_root=root / "storage",
        )
        self.config = Config.model_validate({"models": {
            "default": {"provider": "openai", "id": "existing-model"},
            **{f"mimo-{tier}": {
                "provider": "xiaomi", "id": f"mimo-v2.6-{tier}",
                "extra_kwargs": {"use_thinking": True, "max_tokens": 16384},
            } for tier in ("flash", "pro")},
        }})
        self.credentials = get_runtime_shared_credentials_manager(self.paths)

    def model(self, name="mimo-flash"):
        return get_model_instance(self.config, self.paths, name)

    def test_model_keys_override_provider_without_affecting_openai(self):
        self.credentials.save_credentials("openai", {"api_key": "meta-test-key"})
        self.credentials.save_credentials("xiaomi", {"api_key": "xiaomi-shared"})
        for tier in ("flash", "pro"):
            name = f"mimo-{tier}"
            self.credentials.save_credentials(f"model:{name}", {"api_key": name})
            model = self.model(name)
            self.assertIsInstance(model, MiMo)
            self.assertEqual(model.id, f"mimo-v2.6-{tier}")
            self.assertEqual(model.base_url, "https://api.xiaomimimo.com/v1")
            self.assertEqual(model.get_client().api_key, name)
        self.assertEqual(self.model("default").api_key, "meta-test-key")

    def test_shared_xiaomi_key_is_supported(self):
        self.credentials.save_credentials("xiaomi", {"api_key": "xiaomi-shared"})
        self.assertEqual(self.model().get_client().api_key, "xiaomi-shared")

    def test_missing_xiaomi_key_never_uses_openai_key(self):
        self.credentials.save_credentials("openai", {"api_key": "meta-test-key"})
        with patch.dict(os.environ, {"OPENAI_API_KEY": "another-provider"}, clear=True):
            with self.assertRaises(ModelAuthenticationError):
                self.model().get_client()

    def test_reasoning_and_legacy_tool_replay_are_both_preserved(self):
        message = Message(
            role="assistant", content=None, reasoning_content="Need the tool result.",
            tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "probe"}}],
        )
        formatted = self.model()._format_all_messages([
            message, Message(role="tool", tool_call_id="call_1", content="result"),
        ])
        self.assertEqual(formatted[0]["reasoning_content"], message.reasoning_content)
        self.assertEqual(formatted[0]["tool_calls"][0]["function"]["arguments"], "{}")
        self.assertEqual(formatted[1]["tool_call_id"], "call_1")
        self.assertNotIn("arguments", message.tool_calls[0]["function"])

    def test_thinking_and_output_limit_reach_provider(self):
        params = self.model().get_request_params()
        self.assertEqual(params["extra_body"]["thinking"], {"type": "enabled"})
        self.assertEqual(params["max_tokens"], 16384)


if __name__ == "__main__":
    unittest.main(verbosity=2)
