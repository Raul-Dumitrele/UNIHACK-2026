"""Seed tests never reach the network: live search and the LLM chain are off."""
import pytest


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("REFERENCES_LIVE_SEARCH", "false")
    monkeypatch.setenv("LLM_ENABLED", "false")
