"""Unit tests never reach the network: live search is off unless a test turns it on."""
import pytest


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("REFERENCES_LIVE_SEARCH", "false")
