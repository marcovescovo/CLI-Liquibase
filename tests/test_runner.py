import subprocess
from unittest.mock import MagicMock, patch

import pytest

from lqb.config.schema import Profile
from lqb.runner.liquibase import RunResult, run


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
