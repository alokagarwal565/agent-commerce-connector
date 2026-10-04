"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx

from app.client.woo_client import WooCommerceClient
from app.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"
STORE_URL = "https://example-store.test"
BASE_API = f"{STORE_URL}/wp-json/wc/v3"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture()
def settings(monkeypatch):
    monkeypatch.setenv("WOOCOMMERCE_STORE_URL", STORE_URL)
    monkeypatch.setenv("WOOCOMMERCE_CONSUMER_KEY", "ck_test_key")
    monkeypatch.setenv("WOOCOMMERCE_CONSUMER_SECRET", "cs_test_secret")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("MAX_RETRIES", "2")
    return Settings()  # type: ignore[call-arg]


@pytest.fixture()
def client(settings):
    return WooCommerceClient(settings)


@pytest.fixture()
def mock_api():
    """Activate respx mocking for the duration of a test."""
    with respx.mock(assert_all_called=False) as rsps:
        yield rsps
