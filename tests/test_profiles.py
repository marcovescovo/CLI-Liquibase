import pytest
from pydantic import ValidationError

from lqb.config.schema import Config, Profile


def make_profile(**kwargs) -> Profile:
    defaults = dict(
        name="test",
        jdbc_url="jdbc:postgresql://localhost:5432/db",
        username="user",
        changelog_file="db/changelog.xml",
    )
    defaults.update(kwargs)
    return Profile(**defaults)


def test_profile_valid():
    p = make_profile()
    assert p.name == "test"
    assert p.driver_class == "org.postgresql.Driver"


def test_profile_mysql_driver():
    p = make_profile(jdbc_url="jdbc:mysql://host:3306/db")
    assert "mysql" in p.driver_class.lower()


def test_profile_invalid_jdbc():
    with pytest.raises(ValidationError):
        make_profile(jdbc_url="postgresql://localhost/db")


def test_config_get():
    cfg = Config(profiles=[make_profile(name="a"), make_profile(name="b")])
    assert cfg.get("a") is not None
    assert cfg.get("missing") is None


def test_config_active_profile():
    cfg = Config(active="a", profiles=[make_profile(name="a")])
    assert cfg.active_profile().name == "a"


def test_config_active_none():
    cfg = Config()
    assert cfg.active_profile() is None
