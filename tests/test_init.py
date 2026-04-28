from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lqb.commands.init import (
    _MASTER_BROWNFIELD,
    _MASTER_GREENFIELD,
    _finalize_profile,
    _greenfield,
    _brownfield,
)
from lqb.config.schema import Config, Profile
from lqb.runner.liquibase import RunResult


def make_profile(changelog_file: str = "db/changelog/db.changelog-master.xml") -> Profile:
    return Profile(
        name="test",
        jdbc_url="jdbc:postgresql://localhost:5432/db",
        username="user",
        changelog_file=changelog_file,
    )


# --- Template XML validity ---

def test_greenfield_template_is_valid_xml():
    ET.fromstring(_MASTER_GREENFIELD)


def test_brownfield_template_is_valid_xml():
    ET.fromstring(_MASTER_BROWNFIELD)


def test_brownfield_template_includes_baseline():
    root = ET.fromstring(_MASTER_BROWNFIELD)
    ns = {"lb": "http://www.liquibase.org/xml/ns/dbchangelog"}
    includes = [el for el in root if el.tag.endswith("include")]
    assert any(el.get("file") == "baseline.xml" for el in includes)


# --- _finalize_profile ---

def test_finalize_profile_updates_existing(tmp_path):
    profile = make_profile()
    cfg = Config(active="test", profiles=[profile])
    new_path = str(tmp_path / "db.changelog-master.xml")

    with patch("lqb.commands.init.cfg_mod.save") as mock_save:
        _finalize_profile(cfg, profile, None, new_path)

    mock_save.assert_called_once()
    assert cfg.profiles[0].changelog_file == new_path


def test_finalize_profile_registers_new(tmp_path):
    profile = make_profile()
    cfg = Config()
    new_path = str(tmp_path / "db.changelog-master.xml")

    with patch("lqb.commands.init.register_profile") as mock_reg:
        _finalize_profile(cfg, profile, "secret", new_path)

    mock_reg.assert_called_once()
    call_args = mock_reg.call_args
    saved_profile = call_args[0][1]
    assert saved_profile.changelog_file == new_path


# --- _greenfield ---

def test_greenfield_creates_files(tmp_path):
    root = tmp_path / "db" / "changelog"
    profile = make_profile()
    cfg = Config(active="test", profiles=[profile])

    with patch("lqb.commands.init.cfg_mod.save"):
        _greenfield(root, profile, cfg, None, yes=True)

    assert (root / "db.changelog-master.xml").exists()
    assert (root / "changes").is_dir()
    assert (root / "changes" / ".gitkeep").exists()
    content = (root / "db.changelog-master.xml").read_text()
    assert "databaseChangeLog" in content


def test_greenfield_master_contains_valid_xml(tmp_path):
    root = tmp_path / "db" / "changelog"
    profile = make_profile()
    cfg = Config(active="test", profiles=[profile])

    with patch("lqb.commands.init.cfg_mod.save"):
        _greenfield(root, profile, cfg, None, yes=True)

    ET.parse(root / "db.changelog-master.xml")


# --- _brownfield ---

@patch("lqb.commands.init.get_password", return_value="secret")
@patch("lqb.commands.init.lqb_runner.run_no_changelog")
@patch("lqb.commands.init.prompts.confirm", return_value=True)
def test_brownfield_success(mock_confirm, mock_runner, mock_pwd, tmp_path):
    root = tmp_path / "db" / "changelog"
    root.mkdir(parents=True)
    profile = make_profile()
    cfg = Config(active="test", profiles=[profile])

    baseline_content = '<?xml version="1.0"?><databaseChangeLog/>'

    def fake_run(p, subcommand, extra_args=None, password=None):
        if subcommand == "generate-changelog":
            baseline = root / "baseline.xml"
            baseline.write_text(baseline_content, encoding="utf-8")
        return RunResult(returncode=0, stdout="OK", stderr="")

    mock_runner.side_effect = fake_run

    with patch("lqb.commands.init.cfg_mod.save"):
        _brownfield(root, profile, cfg, None, yes=False)

    assert (root / "baseline.xml").exists()
    assert (root / "db.changelog-master.xml").exists()
    assert mock_runner.call_count == 2


@patch("lqb.commands.init.get_password", return_value="secret")
@patch("lqb.commands.init.lqb_runner.run_no_changelog")
@patch("lqb.commands.init.prompts.confirm", return_value=True)
def test_brownfield_generate_changelog_failure(mock_confirm, mock_runner, mock_pwd, tmp_path):
    import click

    root = tmp_path / "db" / "changelog"
    root.mkdir(parents=True)
    profile = make_profile()
    cfg = Config(active="test", profiles=[profile])

    mock_runner.return_value = RunResult(returncode=1, stdout="", stderr="Connection refused")

    with pytest.raises((SystemExit, click.exceptions.Exit)):
        _brownfield(root, profile, cfg, None, yes=True)

    assert not (root / "baseline.xml").exists()
