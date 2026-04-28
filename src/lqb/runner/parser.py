from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


@dataclass
class Changeset:
    id: str
    author: str
    filepath: str
    date_executed: str = ""
    order_executed: int = 0
    tag: str = ""


@dataclass
class LockInfo:
    locked: bool
    locked_by: str = ""
    lock_granted: str = ""


@dataclass
class StatusResult:
    pending_count: int = 0
    pending_changesets: list[str] = field(default_factory=list)


def parse_history(output: str) -> list[Changeset]:
    changesets: list[Changeset] = []

    # Liquibase 5.x tabular format:
    # | Deployment ID | Update Date | Changelog Path | Changeset Author | Changeset ID | Tag |
    table_pattern = re.compile(
        r"^\|\s*(\S+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|",
        re.MULTILINE,
    )
    order = 0
    for m in table_pattern.finditer(output):
        deployment_id = m.group(1)
        if deployment_id in ("Deployment ID", "-" * len(deployment_id)):
            continue
        order += 1
        changesets.append(
            Changeset(
                order_executed=order,
                id=m.group(5).strip(),
                author=m.group(4).strip(),
                filepath=m.group(3).strip(),
                date_executed=m.group(2).strip(),
                tag=m.group(6).strip(),
            )
        )

    # fallback: legacy line-based format
    if not changesets:
        pattern = re.compile(
            r"(\d+)\s+(\S+)::\S+::(\S+)\s+(\S+T\S+|\d{4}-\d{2}-\d{2}[^\n]+?)\s+EXECUTED",
            re.MULTILINE,
        )
        for m in pattern.finditer(output):
            changesets.append(
                Changeset(
                    order_executed=int(m.group(1)),
                    id=m.group(2).split("::")[-1] if "::" in m.group(2) else m.group(2),
                    author=m.group(3),
                    filepath=m.group(2),
                    date_executed=m.group(4).strip(),
                )
            )

    return changesets


def parse_status(output: str) -> StatusResult:
    result = StatusResult()
    pending: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if re.match(r"\d+ changesets? have not been applied", stripped, re.IGNORECASE):
            m = re.match(r"(\d+)", stripped)
            if m:
                result.pending_count = int(m.group(1))
        elif stripped.startswith("changeSet") or ("::" in stripped and "EXECUTED" not in stripped):
            pending.append(stripped)
    if not result.pending_count and pending:
        result.pending_count = len(pending)
    result.pending_changesets = pending
    return result


def parse_locks(output: str) -> list[LockInfo]:
    locks: list[LockInfo] = []
    if re.search(r"no locks|not locked", output, re.IGNORECASE):
        return [LockInfo(locked=False)]
    pattern = re.compile(r"([\w.]+) at (.+?) \(", re.IGNORECASE)
    for m in pattern.finditer(output):
        locks.append(LockInfo(locked=True, locked_by=m.group(1), lock_granted=m.group(2)))
    if not locks and output.strip():
        locks.append(LockInfo(locked=True))
    return locks


def parse_validate(output: str) -> tuple[bool, list[str]]:
    issues: list[str] = []
    ok = bool(re.search(r"No validation errors found", output, re.IGNORECASE))
    for line in output.splitlines():
        s = line.strip()
        if s and not ok and s not in ("", "Liquibase command 'validate' was executed successfully."):
            issues.append(s)
    return ok, issues
