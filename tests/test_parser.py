from lqb.runner.parser import parse_history, parse_locks, parse_status, parse_validate


def test_parse_status_pending():
    out = "3 changesets have not been applied to mydb"
    result = parse_status(out)
    assert result.pending_count == 3


def test_parse_status_up_to_date():
    out = "mydb is up to date"
    result = parse_status(out)
    assert result.pending_count == 0


def test_parse_history():
    out = (
        "1\tmyfile.xml::001::alice\t2024-01-10T10:00:00\tEXECUTED\n"
        "2\tmyfile.xml::002::bob\t2024-01-11T11:00:00\tEXECUTED\n"
    )
    changesets = parse_history(out)
    assert len(changesets) == 2
    assert changesets[0].author == "alice"
    assert changesets[1].author == "bob"


def test_parse_locks_no_locks():
    out = "Database change log is not locked."
    locks = parse_locks(out)
    assert len(locks) == 1
    assert locks[0].locked is False


def test_parse_validate_ok():
    out = "No validation errors found."
    ok, issues = parse_validate(out)
    assert ok is True
    assert issues == []


def test_parse_validate_fail():
    out = "Validation failed\nMissing required attribute 'author' for changeset '001'"
    ok, issues = parse_validate(out)
    assert ok is False
    assert len(issues) > 0
