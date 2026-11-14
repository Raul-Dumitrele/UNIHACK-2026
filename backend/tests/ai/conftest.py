"""Unit tests never reach the network: live search is off, and the LLM chain is replaced by fake_chain()."""
import pytest

from backend.ai.llm import LLMUnavailable
from backend.ai.llm.chain import parse_json


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("REFERENCES_LIVE_SEARCH", "false")
    monkeypatch.setenv("LLM_ENABLED", "false")


def fake_chain(monkeypatch, target: str, *answers, tries: int = 2):
    """Replace `<target>.generate_json` with a scripted model: each call consumes the next answer (JSON text,
    dict or exception); like the real chain, an invalid or rejected answer is retried once, then
    LLMUnavailable. Returns the list of prompts sent."""
    import json

    prompts: list[str] = []
    queue = list(answers)

    def fake(prompt, schema, system=None, task="generic", validator=None):
        for _ in range(tries):
            if not queue:
                break
            prompts.append(prompt)
            answer = queue.pop(0) if len(queue) > 1 else queue[0]
            if isinstance(answer, BaseException):
                continue
            text = answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)
            try:
                obj = parse_json(text, schema)
                if validator is not None:
                    validator(obj)
                return obj
            except ValueError:
                continue
        raise LLMUnavailable("scripted failure")

    monkeypatch.setattr(f"{target}.generate_json", fake)
    return prompts
