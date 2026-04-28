import subprocess
from unittest.mock import MagicMock, patch

import pytest

from lqb.config.schema import Profile
from lqb.runner.liquibase import RunResult, _resolve_password, run


def make_profile():
    return Profile(
        name="test",
        jdbc_url="jdbc:postgresql://localhost:5432/db",
        username="user",
        changelog_file="db/changelog.xml",
    )


@patch("lqb.runner.liquibase.get_password", return_value="secret")
@patch("lqb.runner.liquibase._find_binary", return_value="liquibase")
@patch("lqb.runner.liquibase.subprocess.run")
def test_run_success(mock_subprocess, mock_binary, mock_pwd):
    mock_subprocess.return_value = MagicMock(returncode=0, stdout="Liquibase command 'update' was executed successfully.", stderr="")
    result = run(make_profile(), "update")
    assert result.ok is True
    assert "update" in result.stdout


@patch("lqb.runner.liquibase.get_password", return_value="secret")
@patch("lqb.runner.liquibase._find_binary", return_value="liquibase")
@patch("lqb.runner.liquibase.subprocess.run")
def test_run_failure(mock_subprocess, mock_binary, mock_pwd):
    mock_subprocess.return_value = MagicMock(returncode=1, stdout="", stderr="Connection refused")
    result = run(make_profile(), "update")
    assert result.ok is False
    assert "Connection refused" in result.stderr


@patch("lqb.runner.liquibase.get_password", return_value="secret")
@patch("lqb.runner.liquibase._find_binary", return_value="liquibase")
@patch("lqb.runner.liquibase.subprocess.run")
def test_password_not_in_args(mock_subprocess, mock_binary, mock_pwd):
    mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")
    run(make_profile(), "status")
    call_args = mock_subprocess.call_args
    cmd = call_args[0][0]
    assert not any("secret" in str(a) for a in cmd), "Password must not appear in CLI args"
    env = call_args[1]["env"]
    assert env["LIQUIBASE_COMMAND_PASSWORD"] == "secret"


# --- _resolve_password ---

@patch("lqb.runner.liquibase.get_password", return_value=None)
def test_resolve_password_profile_env_var(mock_pwd, monkeypatch):
    monkeypatch.setenv("LQB_PASSWORD_MY_DB", "env-secret")
    monkeypatch.delenv("LQB_PASSWORD", raising=False)
    assert _resolve_password("my-db", None) == "env-secret"


@patch("lqb.runner.liquibase.get_password", return_value=None)
def test_resolve_password_generic_env_var(mock_pwd, monkeypatch):
    monkeypatch.delenv("LQB_PASSWORD_PRODUCTION", raising=False)
    monkeypatch.setenv("LQB_PASSWORD", "generic-secret")
    assert _resolve_password("production", None) == "generic-secret"


@patch("lqb.runner.liquibase.get_password", return_value=None)
def test_resolve_password_profile_var_takes_priority(mock_pwd, monkeypatch):
    monkeypatch.setenv("LQB_PASSWORD_PRODUCTION", "specific")
    monkeypatch.setenv("LQB_PASSWORD", "generic")
    assert _resolve_password("production", None) == "specific"


@patch("lqb.runner.liquibase.get_password", return_value=None)
def test_resolve_password_override_takes_priority(mock_pwd, monkeypatch):
    monkeypatch.setenv("LQB_PASSWORD", "generic")
    assert _resolve_password("production", "explicit") == "explicit"


@patch("lqb.runner.liquibase.sys.stdin")
@patch("lqb.runner.liquibase.get_password", return_value=None)
def test_resolve_password_non_interactive_exits(mock_pwd, mock_stdin, monkeypatch):
    mock_stdin.isatty.return_value = False
    monkeypatch.delenv("LQB_PASSWORD", raising=False)
    monkeypatch.delenv("LQB_PASSWORD_PRODUCTION", raising=False)
    monkeypatch.delenv("LQB_NON_INTERACTIVE", raising=False)
    with pytest.raises(SystemExit):
        _resolve_password("production", None)


@patch("lqb.runner.liquibase.sys.stdin")
@patch("lqb.runner.liquibase.get_password", return_value=None)
def test_resolve_password_non_interactive_flag_exits(mock_pwd, mock_stdin, monkeypatch):
    mock_stdin.isatty.return_value = True
    monkeypatch.setenv("LQB_NON_INTERACTIVE", "1")
    monkeypatch.delenv("LQB_PASSWORD", raising=False)
    monkeypatch.delenv("LQB_PASSWORD_PRODUCTION", raising=False)
    with pytest.raises(SystemExit):
        _resolve_password("production", None)
