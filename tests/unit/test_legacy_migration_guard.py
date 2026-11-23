"""Verify that a CommercePilot migration cannot discard populated legacy tables."""

import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "b7c2130a60fa_retire_legacy_tenants.py"
)


class FakeResult:
    def __init__(self, populated: bool) -> None:
        self.populated = populated

    def scalar_one(self) -> bool:
        return self.populated


class FakeConnection:
    def __init__(self, populated_table: str | None) -> None:
        self.populated_table = populated_table
        self.checked_tables: list[str] = []

    def execute(self, statement: object) -> FakeResult:
        query = str(statement)
        table = query.split('FROM "')[1].split('"')[0]
        self.checked_tables.append(table)
        return FakeResult(table == self.populated_table)


def test_populated_legacy_table_blocks_all_drops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upgrade = runpy.run_path(str(MIGRATION))["upgrade"]
    connection = FakeConnection(populated_table="organizations")
    deleted: list[str] = []
    monkeypatch.setitem(
        upgrade.__globals__,
        "op",
        SimpleNamespace(get_bind=lambda: connection, drop_table=deleted.append),
    )

    with pytest.raises(RuntimeError, match="Refusing to drop populated legacy table"):
        upgrade()

    assert deleted == []
    assert connection.checked_tables[-1] == "organizations"


def test_empty_legacy_tables_drop_in_fk_safe_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upgrade = runpy.run_path(str(MIGRATION))["upgrade"]
    connection = FakeConnection(populated_table=None)
    deleted: list[str] = []
    monkeypatch.setitem(
        upgrade.__globals__,
        "op",
        SimpleNamespace(get_bind=lambda: connection, drop_table=deleted.append),
    )

    upgrade()

    assert deleted == [
        "project_memberships",
        "projects",
        "organization_memberships",
        "organizations",
    ]
    assert connection.checked_tables == deleted
