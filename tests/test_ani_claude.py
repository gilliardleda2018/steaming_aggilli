import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    import anthropic
except ImportError:  # CI installs only the base test dependencies
    anthropic = None

from commercial.ani_dj import INTENT_SCHEMA, claude_intent, resolve_intent


def reply(stop_reason="end_turn", text=None):
    content = [] if text is None else [SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(stop_reason=stop_reason, content=content)


class FakeClaude:
    """Stands in for anthropic.Anthropic(): records the request, returns a canned reply."""

    def __init__(self, response=None, error=None):
        self.requests = []
        self.response, self.error = response, error
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.response


CLAUDE_ENV = {"AGGILLI_ANI_PROVIDER": "anthropic", "AGGILLI_ANI_MODEL": "claude-opus-5-5"}


class ClaudeIntentTests(unittest.TestCase):
    def test_request_uses_structured_output_fallbacks_and_only_the_prompt(self):
        client = FakeClaude(reply(text=json.dumps({"mood": "energia", "title": "Treino a mil"})))
        intent = claude_intent("energia para treinar", model="claude-opus-5-5", client=client)
        self.assertEqual(intent, {"mood": "energia", "title": "Treino a mil", "genre": None,
                                  "minutes": None, "avoid_repeats": False, "query": ""})
        request = client.requests[0]
        self.assertEqual(request["model"], "claude-opus-5-5")
        self.assertEqual(request["fallbacks"], "default")
        self.assertEqual(request["betas"], ["server-side-fallback-2026-07-01"])
        self.assertEqual(request["output_config"]["format"], {"type": "json_schema", "schema": INTENT_SCHEMA})
        self.assertEqual(request["messages"], [{"role": "user", "content": "energia para treinar"}])
        self.assertNotIn("temperature", request)

    def test_schema_only_allows_player_moods(self):
        self.assertEqual(INTENT_SCHEMA["properties"]["mood"]["enum"],
                         ["descoberta", "energia", "foco", "relaxar", "romantico"])
        self.assertEqual(INTENT_SCHEMA["properties"]["genre"]["enum"][-1], "qualquer")
        self.assertEqual(set(INTENT_SCHEMA["required"]), {"mood", "title", "genre", "minutes", "avoid_repeats", "query"})
        self.assertFalse(INTENT_SCHEMA["additionalProperties"])

    def test_engine_is_ani_when_claude_answers(self):
        client = FakeClaude(reply(text='{"mood": "relaxar", "title": "Noite calma"}'))
        with patch.dict(os.environ, CLAUDE_ENV):
            result = resolve_intent("algo calmo", model_enabled=True, model_client=client)
        self.assertEqual(result, {"mood": "relaxar", "title": "Noite calma", "genre": None,
                                  "minutes": None, "avoid_repeats": False, "query": "", "engine": "ani"})

    def test_refusal_falls_back_to_local_selection(self):
        client = FakeClaude(reply(stop_reason="refusal"))
        with patch.dict(os.environ, CLAUDE_ENV):
            result = resolve_intent("algo calmo para relaxar", model_enabled=True, model_client=client)
        self.assertEqual(result["engine"], "offline")
        self.assertEqual(result["mood"], "relaxar")

    @unittest.skipIf(anthropic is None, "anthropic SDK not installed")
    def test_api_errors_fall_back_to_local_selection(self):
        error = anthropic.APIConnectionError(request=None)
        with patch.dict(os.environ, CLAUDE_ENV):
            result = resolve_intent("foco para estudar", model_enabled=True,
                                    model_client=FakeClaude(error=error))
        self.assertEqual(result["engine"], "offline")

    def test_unexpected_mood_is_rejected(self):
        client = FakeClaude(reply(text='{"mood": "festa", "title": "x"}'))
        with patch.dict(os.environ, CLAUDE_ENV):
            result = resolve_intent("festa", model_enabled=True, model_client=client)
        self.assertEqual(result["engine"], "offline")

    def test_missing_model_never_calls_the_api(self):
        client = FakeClaude(reply(text='{"mood": "foco", "title": "x"}'))
        with patch.dict(os.environ, {"AGGILLI_ANI_PROVIDER": "anthropic", "AGGILLI_ANI_MODEL": ""}):
            result = resolve_intent("foco", model_enabled=True, model_client=client)
        self.assertEqual(result["engine"], "offline")
        self.assertEqual(client.requests, [])


if __name__ == "__main__":
    unittest.main()
