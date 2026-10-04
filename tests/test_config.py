"""Tests for configuration loading and validation."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from app.config import Settings


def test_valid_config(monkeypatch):
    monkeypatch.setenv("WOOCOMMERCE_STORE_URL", "https://shop.example.test/")
    monkeypatch.setenv("WOOCOMMERCE_CONSUMER_KEY", "ck_abc")
    monkeypatch.setenv("WOOCOMMERCE_CONSUMER_SECRET", "cs_xyz")
    s = Settings()  # type: ignore[call-arg]
    # Trailing slash stripped
    assert s.woocommerce_store_url == "https://shop.example.test"
    assert isinstance(s.woocommerce_consumer_key, SecretStr)
    assert s.woocommerce_consumer_key.get_secret_value() == "ck_abc"


def test_missing_required_vars(monkeypatch):
    monkeypatch.delenv("WOOCOMMERCE_STORE_URL", raising=False)
    monkeypatch.delenv("WOOCOMMERCE_CONSUMER_KEY", raising=False)
    monkeypatch.delenv("WOOCOMMERCE_CONSUMER_SECRET", raising=False)
    with pytest.raises(Exception):
        Settings()  # type: ignore[call-arg]


def test_secrets_not_in_repr(monkeypatch):
    monkeypatch.setenv("WOOCOMMERCE_STORE_URL", "https://shop.example.test")
    monkeypatch.setenv("WOOCOMMERCE_CONSUMER_KEY", "ck_supersecret")
    monkeypatch.setenv("WOOCOMMERCE_CONSUMER_SECRET", "cs_supersecret")
    s = Settings()  # type: ignore[call-arg]
    r = repr(s)
    assert "ck_supersecret" not in r
    assert "cs_supersecret" not in r


def test_invalid_max_per_page(monkeypatch):
    monkeypatch.setenv("WOOCOMMERCE_STORE_URL", "https://shop.example.test")
    monkeypatch.setenv("WOOCOMMERCE_CONSUMER_KEY", "ck_abc")
    monkeypatch.setenv("WOOCOMMERCE_CONSUMER_SECRET", "cs_xyz")
    monkeypatch.setenv("MAX_PER_PAGE", "200")
    with pytest.raises(Exception, match="max_per_page"):
        Settings()  # type: ignore[call-arg]


def test_defaults(monkeypatch):
    monkeypatch.setenv("WOOCOMMERCE_STORE_URL", "https://shop.example.test")
    monkeypatch.setenv("WOOCOMMERCE_CONSUMER_KEY", "ck_abc")
    monkeypatch.setenv("WOOCOMMERCE_CONSUMER_SECRET", "cs_xyz")
    s = Settings()  # type: ignore[call-arg]
    assert s.request_timeout_seconds == 15
    assert s.max_retries == 3
    assert s.max_per_page == 100
