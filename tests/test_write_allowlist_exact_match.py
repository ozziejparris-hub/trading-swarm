"""
test_write_allowlist_exact_match.py
Tests for orchestrator/ollama_agent_loop.py's _match_write_allowlist() /
_assigned_columns() — the SQL write-allowlist used by tool_run_sql_write().

O-24 (Fable finding 6.1): the old allowlist matched only the START of the query
(re.match on a prefix regex with no end-anchor or column-exclusivity check), so
"UPDATE traders SET geo_elo=1500, comprehensive_elo=9999 WHERE ..." passed straight
through — comprehensive_elo (the frozen ELO-arc column) was writable by smuggling it
behind ANY allowed column, via ANY of the allowed prefixes.

These tests exercise the matching logic directly (pure functions, no sqlite3.connect,
no PROD_DB_PATH touched) — deliberately, since tool_run_sql_write() would execute a
real write against the production DB if called.

Run: python3 -m pytest tests/test_write_allowlist_exact_match.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.ollama_agent_loop import (
    _WRITE_ALLOWLIST,
    _assigned_columns,
    _match_write_allowlist,
)


class TestLegitimateWritesStillAllowed:
    """Every currently-supported single-column write must still pass."""

    def test_geo_elo(self):
        q = "UPDATE traders SET geo_elo = 1420.5 WHERE address = '0xTEST'"
        assert _match_write_allowlist(q) == "UPDATE traders SET geo_elo"

    def test_geo_directionality_score(self):
        q = "UPDATE traders SET geo_directionality_score = 0.72 WHERE address = '0xTEST'"
        assert _match_write_allowlist(q) == "UPDATE traders SET geo_directionality_score"

    def test_geo_resolved_trades_count(self):
        q = "UPDATE traders SET geo_resolved_trades_count = 12 WHERE address = '0xTEST'"
        assert _match_write_allowlist(q) == "UPDATE traders SET geo_resolved_trades_count"

    def test_bot_type(self):
        q = "UPDATE traders SET bot_type = 'LP_ARTIFACT' WHERE address = '0xTEST'"
        assert _match_write_allowlist(q) == "UPDATE traders SET bot_type"

    def test_research_excluded(self):
        q = "UPDATE traders SET research_excluded = 1 WHERE address = '0xTEST'"
        assert _match_write_allowlist(q) == "UPDATE traders SET research_excluded"

    def test_no_where_clause_still_allowed(self):
        # WHERE is optional in the grammar we match — a bare single-column SET with
        # no WHERE is still exactly-one-column and should still be permitted (the
        # existing MAX_WRITE_ROWS guard handles the "too broad" risk separately).
        q = "UPDATE traders SET geo_elo = 1500"
        assert _match_write_allowlist(q) == "UPDATE traders SET geo_elo"

    def test_case_insensitive(self):
        q = "update TRADERS set Geo_Elo = 1500 where address='0xTEST'"
        assert _match_write_allowlist(q) == "UPDATE traders SET geo_elo"


class TestFrozenColumnCannotBeSmuggled:
    """The exact attack Fable's audit (finding 6.1) described must now be rejected."""

    def test_the_reported_attack(self):
        q = "UPDATE traders SET geo_elo=1500, comprehensive_elo=9999 WHERE address='0xTEST'"
        assert _match_write_allowlist(q) == ""

    def test_smuggle_behind_bot_type(self):
        q = "UPDATE traders SET bot_type='LP_ARTIFACT', comprehensive_elo=1 WHERE address='0xTEST'"
        assert _match_write_allowlist(q) == ""

    def test_smuggle_behind_research_excluded(self):
        q = "UPDATE traders SET research_excluded=0, comprehensive_elo=9999 WHERE 1=1"
        assert _match_write_allowlist(q) == ""

    def test_smuggle_multiple_frozen_columns(self):
        q = ("UPDATE traders SET geo_elo=1500, comprehensive_elo=9999, "
             "behavioral_modifier=1.0, geo_elo_active=1 WHERE address='0xTEST'")
        assert _match_write_allowlist(q) == ""

    def test_direct_write_to_comprehensive_elo_alone(self):
        # Never matched any prefix, before or after the fix — included for completeness.
        q = "UPDATE traders SET comprehensive_elo = 9999 WHERE address = '0xTEST'"
        assert _match_write_allowlist(q) == ""

    def test_smuggle_via_geo_directionality_score(self):
        q = ("UPDATE traders SET geo_directionality_score=0.9, comprehensive_elo=1 "
             "WHERE address='0xTEST'")
        assert _match_write_allowlist(q) == ""

    def test_smuggle_via_geo_resolved_trades_count(self):
        q = ("UPDATE traders SET geo_resolved_trades_count=5, comprehensive_elo=1 "
             "WHERE address='0xTEST'")
        assert _match_write_allowlist(q) == ""


class TestDeadEntriesRemoved:
    """accuracy_pool / trader_notes / ALTER TABLE must no longer be in the allowlist."""

    def test_accuracy_pool_entry_removed(self):
        names = [name for name, _, _ in _WRITE_ALLOWLIST]
        assert not any("accuracy_pool" in n for n in names)

    def test_trader_notes_entry_removed(self):
        names = [name for name, _, _ in _WRITE_ALLOWLIST]
        assert not any("trader_notes" in n for n in names)

    def test_alter_table_entry_removed(self):
        names = [name for name, _, _ in _WRITE_ALLOWLIST]
        assert not any("ALTER" in n for n in names)

    def test_accuracy_pool_query_now_rejected_outright(self):
        # Even a "clean" single-column write to the dropped column is rejected —
        # there's no rule left that names it.
        q = "UPDATE traders SET accuracy_pool = 1 WHERE address = '0xTEST'"
        assert _match_write_allowlist(q) == ""

    def test_alter_table_query_now_rejected_outright(self):
        q = "ALTER TABLE traders ADD COLUMN new_col TEXT"
        assert _match_write_allowlist(q) == ""


class TestAssignedColumnsHelper:
    """Direct unit coverage of the extraction helper backing the exact-match check."""

    def test_single_column(self):
        assert _assigned_columns("UPDATE traders SET geo_elo=1500 WHERE x=1") == ["geo_elo"]

    def test_multiple_columns(self):
        cols = _assigned_columns("UPDATE traders SET geo_elo=1500, comprehensive_elo=9999")
        assert cols == ["geo_elo", "comprehensive_elo"]

    def test_non_update_query_returns_none(self):
        assert _assigned_columns("SELECT * FROM traders") is None

    def test_strips_where_clause(self):
        cols = _assigned_columns("UPDATE traders SET geo_elo=1500 WHERE address='0x1,0x2'")
        # Only the SET clause is inspected — a comma inside the WHERE clause's value
        # must not be misread as an extra assignment.
        assert cols == ["geo_elo"]
