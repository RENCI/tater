"""Tests for CLI argument parsing (tater/ui/cli.py)."""
import sys
import pytest
from unittest.mock import patch

from tater.ui.cli import parse_args


def _parse(*args):
    """Call parse_args() with the given argv (no browser, no file I/O)."""
    with patch.object(sys, "argv", ["tater", *args]):
        return parse_args()


def _parse_raises(*args):
    """Assert that parse_args() exits with a validation error."""
    with patch.object(sys, "argv", ["tater", *args]):
        with pytest.raises(SystemExit):
            parse_args()


# ---------------------------------------------------------------------------
# Hosted mode
# ---------------------------------------------------------------------------

class TestHostedMode:
    def test_hosted_alone_is_valid(self):
        args = _parse("--hosted")
        assert args.hosted is True

    def test_hosted_with_no_restore_raises(self):
        _parse_raises("--hosted", "--no-restore")

    def test_hosted_with_documents_is_allowed(self):
        # --documents is not required but not rejected in hosted mode
        args = _parse("--hosted", "--documents", "docs.json")
        assert args.hosted is True
        assert args.documents == "docs.json"

    def test_hosted_with_config_is_allowed(self):
        args = _parse("--hosted", "--config", "config.py")
        assert args.hosted is True


# ---------------------------------------------------------------------------
# Non-hosted mode
# ---------------------------------------------------------------------------

class TestNonHostedMode:
    def test_config_with_documents_is_valid(self):
        args = _parse("--config", "config.py", "--documents", "docs.json")
        assert args.config == "config.py"
        assert args.documents == "docs.json"
        assert args.hosted is False

    def test_schema_with_documents_is_valid(self):
        args = _parse("--schema", "schema.json", "--documents", "docs.json")
        assert args.schema == "schema.json"

    def test_missing_mode_flag_raises(self):
        _parse_raises("--documents", "docs.json")

    def test_non_hosted_missing_documents_raises(self):
        _parse_raises("--config", "config.py")

    def test_config_and_schema_are_mutually_exclusive(self):
        _parse_raises("--config", "config.py", "--schema", "schema.json", "--documents", "docs.json")

    def test_no_restore_is_valid_in_non_hosted(self):
        args = _parse("--config", "config.py", "--documents", "docs.json", "--no-restore")
        assert args.no_restore is True

    def test_no_restore_defaults_false(self):
        args = _parse("--config", "config.py", "--documents", "docs.json")
        assert args.no_restore is False

    def test_annotations_path_is_optional(self):
        args = _parse("--config", "config.py", "--documents", "docs.json", "--annotations", "ann.json")
        assert args.annotations == "ann.json"

    def test_debug_flag(self):
        args = _parse("--config", "config.py", "--documents", "docs.json", "--debug")
        assert args.debug is True


# ---------------------------------------------------------------------------
# Port and host defaults and flags
# ---------------------------------------------------------------------------

class TestPortAndHost:
    def test_default_port(self, monkeypatch):
        monkeypatch.delenv("TATER_PORT", raising=False)
        args = _parse("--hosted")
        assert args.port == 8050

    def test_default_host(self, monkeypatch):
        monkeypatch.delenv("TATER_HOST", raising=False)
        args = _parse("--hosted")
        assert args.host == "127.0.0.1"

    def test_port_flag(self, monkeypatch):
        monkeypatch.delenv("TATER_PORT", raising=False)
        args = _parse("--hosted", "--port", "9090")
        assert args.port == 9090

    def test_host_flag(self, monkeypatch):
        monkeypatch.delenv("TATER_HOST", raising=False)
        args = _parse("--hosted", "--host", "0.0.0.0")
        assert args.host == "0.0.0.0"


# ---------------------------------------------------------------------------
# Environment variable fallbacks
# ---------------------------------------------------------------------------

class TestEnvVars:
    def test_port_env_var(self, monkeypatch):
        monkeypatch.setenv("TATER_PORT", "9090")
        args = _parse("--hosted")
        assert args.port == 9090

    def test_host_env_var(self, monkeypatch):
        monkeypatch.setenv("TATER_HOST", "0.0.0.0")
        args = _parse("--hosted")
        assert args.host == "0.0.0.0"

    def test_debug_env_var_true(self, monkeypatch):
        monkeypatch.setenv("TATER_DEBUG", "true")
        args = _parse("--hosted")
        assert args.debug is True

    def test_debug_env_var_1(self, monkeypatch):
        monkeypatch.setenv("TATER_DEBUG", "1")
        args = _parse("--hosted")
        assert args.debug is True

    def test_debug_env_var_yes(self, monkeypatch):
        monkeypatch.setenv("TATER_DEBUG", "yes")
        args = _parse("--hosted")
        assert args.debug is True

    def test_debug_env_var_false(self, monkeypatch):
        monkeypatch.setenv("TATER_DEBUG", "false")
        args = _parse("--hosted")
        assert args.debug is False

    def test_debug_env_var_absent(self, monkeypatch):
        monkeypatch.delenv("TATER_DEBUG", raising=False)
        args = _parse("--hosted")
        assert args.debug is False

    def test_port_env_var_overridden_by_flag(self, monkeypatch):
        monkeypatch.setenv("TATER_PORT", "9090")
        args = _parse("--hosted", "--port", "7777")
        assert args.port == 7777
