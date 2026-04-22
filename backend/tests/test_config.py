"""Tests for config module."""

from __future__ import annotations

import os
from unittest.mock import patch

from backend.config import Settings, load_settings


def test_settings_defaults():
    s = Settings()
    assert s.neo4j_uri == "bolt://localhost:7687"
    assert s.neo4j_user == "neo4j"
    assert s.neo4j_password == "cuedrop_dev"
    assert s.vdj_host == "http://127.0.0.1:80"
    assert s.port == 8000
    assert s.cors_origins == ["*"]


def test_settings_frozen():
    s = Settings()
    try:
        s.port = 9000  # type: ignore[misc]
        assert False, "Should have raised"
    except AttributeError:
        pass


def test_load_settings_from_env():
    env = {
        "NEO4J_URI": "bolt://remote:7687",
        "NEO4J_USER": "admin",
        "NEO4J_PASSWORD": "secret",
        "VDJ_HOST": "http://192.168.1.100:80",
        "PORT": "9000",
    }
    with patch.dict(os.environ, env, clear=False):
        with patch("backend.config.load_dotenv"):
            s = load_settings()
    assert s.neo4j_uri == "bolt://remote:7687"
    assert s.neo4j_user == "admin"
    assert s.neo4j_password == "secret"
    assert s.vdj_host == "http://192.168.1.100:80"
    assert s.port == 9000


def test_load_settings_defaults_when_env_empty():
    with patch.dict(os.environ, {}, clear=True):
        with patch("backend.config.load_dotenv"):
            s = load_settings()
    assert s.neo4j_uri == "bolt://localhost:7687"
    assert s.port == 8000
