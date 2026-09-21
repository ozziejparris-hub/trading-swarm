"""
test_corpus_content_extractor.py
Tests for scripts/corpus_content_extractor.py's 2026-09-21 additions:
deterministic post-extraction dedup, the length-scaled per-call timeout,
and the daily_maintenance overlap guard. No Ollama/model involvement --
all three are pure/deterministic and testable offline.
Run from repo root: python3 -m pytest tests/test_corpus_content_extractor.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from scripts.corpus_content_extractor import (
    dedup_field,
    dedup_record,
    timeout_for_lines,
    maintenance_in_progress,
    MIN_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    ALL_CLAIM_FIELDS,
    MAINTENANCE_START_MARKER,
    MAINTENANCE_FINISH_MARKER,
)
import scripts.corpus_content_extractor as cce


def _item(claim, quote):
    return {"claim": claim, "quote": quote}


class TestDedupField:
    """dedup_field(items) -> (kept, removed)."""

    def test_no_duplicates_passes_through_unchanged(self):
        items = [_item("a", "quote one"), _item("b", "quote two")]
        kept, removed = dedup_field(items)
        assert kept == items
        assert removed == []

    def test_exact_repeat_is_removed_keeping_first(self):
        first = _item("a", "the exact same quote text")
        second = _item("a again", "the exact same quote text")
        kept, removed = dedup_field([first, second])
        assert kept == [first]
        assert removed == [second]

    def test_whitespace_only_difference_is_still_a_duplicate(self):
        # This is the point of reusing _normalize_ws: a hard-wrapped/
        # re-indented copy of the same source span must still collapse.
        first = _item("a", "line one\nline two   continues")
        second = _item("a", "line one line two continues")
        kept, removed = dedup_field([first, second])
        assert kept == [first]
        assert len(removed) == 1

    def test_three_way_duplicate_keeps_only_first(self):
        a = _item("a", "repeated text")
        b = _item("b", "repeated text")
        c = _item("c", "repeated text")
        kept, removed = dedup_field([a, b, c])
        assert kept == [a]
        assert removed == [b, c]

    def test_order_preserved_among_survivors(self):
        a = _item("a", "alpha")
        b = _item("b", "beta")
        c = _item("c", "alpha")  # dup of a
        d = _item("d", "gamma")
        kept, removed = dedup_field([a, b, c, d])
        assert kept == [a, b, d]
        assert removed == [c]

    def test_malformed_items_never_treated_as_duplicates(self):
        # Missing/non-string quote: can't confidently normalize, so never
        # collapsed with anything -- conservative failure direction.
        weird1 = {"claim": "a", "quote": None}
        weird2 = {"claim": "b", "quote": None}
        weird3 = {"claim": "c"}  # no quote key at all
        kept, removed = dedup_field([weird1, weird2, weird3])
        assert kept == [weird1, weird2, weird3]
        assert removed == []

    def test_empty_list(self):
        kept, removed = dedup_field([])
        assert kept == []
        assert removed == []

    def test_negative_control_shared_wording_different_passages_both_survive(self):
        """
        THE CRITICAL CASE the task calls out: two items that share
        wording but cite genuinely different passages of the source must
        both survive. Constructed so the two quotes are similar (same
        leading words, same topic) but NOT identical after normalization
        -- e.g. two list entries from the same enumerated block that share
        a common stem but diverge partway through, the exact shape of the
        real explicitly_open duplicates found in the fourth pilot's OTHER
        items that were genuinely distinct.
        """
        distinct_a = _item(
            "first requirement",
            "The implementing task must establish, and record having "
            "established: 1. A sample of the 15,427 genuinely lacks "
            "usable identifiers",
        )
        distinct_b = _item(
            "second requirement",
            "The implementing task must establish, and record having "
            "established: 2. No legitimate, resolvable market is caught "
            "by the exclusion predicate",
        )
        kept, removed = dedup_field([distinct_a, distinct_b])
        assert kept == [distinct_a, distinct_b]
        assert removed == []


class TestDedupRecord:
    """dedup_record(record) -- the full-record wrapper used by process_one()."""

    def _bare_record(self, **fields):
        record = {f: [] for f in ALL_CLAIM_FIELDS}
        record.update(fields)
        return record

    def test_raw_fields_never_mutated(self):
        raw_findings = [_item("a", "dup text"), _item("b", "dup text")]
        record = self._bare_record(findings=list(raw_findings))
        before = [dict(item) for item in record["findings"]]
        dedup_record(record)
        assert record["findings"] == before  # untouched: still has both

    def test_deduped_key_has_the_reduced_list(self):
        record = self._bare_record(
            findings=[_item("a", "dup text"), _item("b", "dup text")]
        )
        dedup_record(record)
        assert len(record["deduped"]["findings"]) == 1

    def test_padding_removed_counts_are_per_field(self):
        record = self._bare_record(
            findings=[_item("a", "x"), _item("b", "x"), _item("c", "y")],
            explicitly_open=[_item("a", "z")],
        )
        dedup_record(record)
        assert record["padding_removed"]["findings"] == 1
        assert record["padding_removed"]["explicitly_open"] == 0

    def test_padding_removed_items_are_the_actual_removed_dicts(self):
        second = _item("b", "x")
        record = self._bare_record(findings=[_item("a", "x"), second])
        dedup_record(record)
        assert record["padding_removed_items"]["findings"] == [second]

    def test_all_fields_present_in_output_even_when_empty(self):
        record = self._bare_record()
        dedup_record(record)
        for field in ALL_CLAIM_FIELDS:
            assert field in record["deduped"]
            assert record["padding_removed"][field] == 0


class TestTimeoutForLines:
    def test_floor_applies_to_small_documents(self):
        assert timeout_for_lines(1) == MIN_TIMEOUT_SECONDS
        assert timeout_for_lines(167) == MIN_TIMEOUT_SECONDS

    def test_ceiling_applies_to_huge_documents(self):
        assert timeout_for_lines(50_000) == MAX_TIMEOUT_SECONDS

    def test_monotonically_nondecreasing(self):
        prev = timeout_for_lines(0)
        for lines in range(0, 3000, 50):
            cur = timeout_for_lines(lines)
            assert cur >= prev
            prev = cur

    def test_largest_corpus_document_exceeds_the_observed_2400s_need(self):
        # 2026-08-21-discovery-gap-closure-prereg.md, 1,884 lines, the
        # corpus's largest document and the one the flat 1200s ceiling
        # (and even a 2400s supplementary retry margin) was breached by.
        assert timeout_for_lines(1884) >= 2400

    def test_covers_every_returned_call_in_pilot_history(self):
        """
        Every (line_count, observed_call_seconds) pair reconstructed from
        the pilot, re-pilot, and fourth-pilot artifacts' indexed_at
        timestamps (successful/returned calls only) must fit under the
        timeout this formula would assign. This is the same 24-point
        dataset the fit itself was derived from -- see
        brain/decisions/2026-09-21-dedup-and-length-scaled-timeout.md for
        provenance and the reconstruction method.
        """
        observed = [
            (167, 229.6), (268, 262.1), (268, 298.2), (268, 350.9),
            (301, 90.5), (301, 164.6), (301, 191.2), (315, 140.5),
            (412, 120.4), (412, 177.9), (436, 91.3), (436, 109.1),
            (436, 148.3), (498, 206.0), (498, 290.3), (521, 188.4),
            (527, 319.1), (666, 217.3), (1066, 271.0), (1066, 284.5),
            (1066, 574.5), (1884, 814.7), (1884, 1009.2), (1884, 1680.3),
        ]
        for lines, seconds in observed:
            assigned = timeout_for_lines(lines)
            assert assigned >= seconds, (
                f"lines={lines} observed={seconds}s but formula assigned "
                f"only {assigned}s"
            )


class TestMaintenanceInProgress:
    def test_no_log_file_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cce, "MAINTENANCE_LOG_FILE", tmp_path / "does_not_exist.log")
        assert maintenance_in_progress() is False

    def test_started_not_finished_is_in_progress(self, tmp_path, monkeypatch):
        log = tmp_path / "daily_maintenance.log"
        log.write_text(f"[2026-09-21T06:00:00Z] {MAINTENANCE_START_MARKER}\n")
        monkeypatch.setattr(cce, "MAINTENANCE_LOG_FILE", log)
        assert maintenance_in_progress() is True

    def test_started_then_finished_is_not_in_progress(self, tmp_path, monkeypatch):
        log = tmp_path / "daily_maintenance.log"
        log.write_text(
            f"[2026-09-21T06:00:00Z] {MAINTENANCE_START_MARKER}\n"
            "... maintenance output ...\n"
            f"[2026-09-21T10:37:00Z] {MAINTENANCE_FINISH_MARKER} (exit: 0)\n"
        )
        monkeypatch.setattr(cce, "MAINTENANCE_LOG_FILE", log)
        assert maintenance_in_progress() is False

    def test_prior_days_cycle_does_not_leak_into_todays_check(self, tmp_path, monkeypatch):
        log = tmp_path / "daily_maintenance.log"
        log.write_text(
            f"[2026-09-20T06:00:00Z] {MAINTENANCE_START_MARKER}\n"
            f"[2026-09-20T13:12:00Z] {MAINTENANCE_FINISH_MARKER} (exit: 0)\n"
            f"[2026-09-21T06:00:00Z] {MAINTENANCE_START_MARKER}\n"
        )
        monkeypatch.setattr(cce, "MAINTENANCE_LOG_FILE", log)
        assert maintenance_in_progress() is True

    def test_wide_tail_scan_finds_a_start_line_beyond_the_first_chunk(self, tmp_path, monkeypatch):
        # Marker at the START of the file, followed by >64KB of padding
        # with no Finished line -- the initial 64KB-from-the-end tail read
        # misses the marker entirely, so this only passes if the
        # widen-and-retry path actually runs.
        log = tmp_path / "daily_maintenance.log"
        padding = "padding line, not a marker\n" * 5000  # well over 64KB
        log.write_text(f"[2026-09-21T06:00:00Z] {MAINTENANCE_START_MARKER}\n" + padding)
        monkeypatch.setattr(cce, "MAINTENANCE_LOG_FILE", log)
        assert maintenance_in_progress() is True


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
