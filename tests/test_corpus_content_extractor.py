"""
test_corpus_content_extractor.py
Tests for scripts/corpus_content_extractor.py's 2026-09-21 additions
(deterministic post-extraction dedup, the length-scaled per-call timeout)
and its 2026-09-22 additions (the run-level pre-launch projection
assertion, the flock-probe maintenance guard replacing the log-tail
heuristic, and the failed-document retry-on-resume fix). No Ollama/model
involvement -- all of this is pure/deterministic and testable offline.
Run from repo root: python3 -m pytest tests/test_corpus_content_extractor.py -v
"""

import json
import os
import signal
import subprocess
import sys
import time as _time
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


def _start_flock_holder(lockfile: Path) -> subprocess.Popen:
    """
    Spawns a detached process that opens `lockfile` and holds an exclusive
    flock on it indefinitely -- the identical stand-in pattern as
    bfdf9d6's tests/test_daily_maintenance_overlap_guard.sh start_holder(),
    reused here (not reinvented) so the Python probe is exercised against
    the same kind of lock holder that shell guard's own 33/33 suite
    already proved correct against.
    """
    proc = subprocess.Popen(
        ["setsid", "bash", "-c",
         'exec 9<>"$0"; flock -x 9; while :; do sleep 0.2; done', str(lockfile)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        result = subprocess.run(["flock", "-n", str(lockfile), "-c", "true"])
        if result.returncode != 0:
            return proc  # lock is now held -- holder acquired it
        _time.sleep(0.1)
    proc.kill()
    raise RuntimeError(f"holder never acquired {lockfile}")


def _kill_holder(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


class TestMaintenanceInProgressFlockProbe:
    """
    maintenance_in_progress() (2026-09-22: switched from a log-tail
    heuristic to a kernel-advisory flock probe against the exact lockfile
    run_daily_maintenance.sh's overlap guard holds -- bfdf9d6, Part 7's
    documented migration path). PROBE, NEVER HOLD is the property that
    matters most: if this ever held the lock instead of only checking it,
    the next real 06:00 daily_maintenance run would be wrongly REFUSED
    (exit 75 + Telegram alert) by a corpus job that has nothing to do with
    it -- test_probe_is_probe_only_* below is the direct proof it doesn't.
    """

    def test_no_holder_is_not_in_progress(self, tmp_path, monkeypatch):
        lockfile = tmp_path / "run_daily_maintenance.sh.lock"
        monkeypatch.setattr(cce, "MAINTENANCE_LOCKFILE", lockfile)
        assert maintenance_in_progress() is False

    def test_held_lock_is_in_progress_no_false_negative(self, tmp_path, monkeypatch):
        lockfile = tmp_path / "run_daily_maintenance.sh.lock"
        monkeypatch.setattr(cce, "MAINTENANCE_LOCKFILE", lockfile)
        holder = _start_flock_holder(lockfile)
        try:
            assert maintenance_in_progress() is True
        finally:
            _kill_holder(holder)

    def test_released_lock_is_not_in_progress_no_false_positive(self, tmp_path, monkeypatch):
        lockfile = tmp_path / "run_daily_maintenance.sh.lock"
        monkeypatch.setattr(cce, "MAINTENANCE_LOCKFILE", lockfile)
        holder = _start_flock_holder(lockfile)
        assert maintenance_in_progress() is True
        _kill_holder(holder)
        for _ in range(50):
            if maintenance_in_progress() is False:
                break
            _time.sleep(0.05)
        assert maintenance_in_progress() is False

    def test_probe_returns_quickly_while_blocked(self, tmp_path, monkeypatch):
        lockfile = tmp_path / "run_daily_maintenance.sh.lock"
        monkeypatch.setattr(cce, "MAINTENANCE_LOCKFILE", lockfile)
        holder = _start_flock_holder(lockfile)
        try:
            t0 = _time.monotonic()
            result = maintenance_in_progress()
            elapsed = _time.monotonic() - t0
            assert result is True
            assert elapsed < 1.0, f"probe took {elapsed:.2f}s -- LOCK_NB must never block"
        finally:
            _kill_holder(holder)

    def test_probe_is_probe_only_maintenance_can_still_acquire_afterward(self, tmp_path, monkeypatch):
        """
        THE CRITICAL PROOF: after maintenance_in_progress() runs against a
        free lock, a real maintenance-side `flock -n` acquire attempt
        against the SAME lockfile must still succeed. If the probe had
        acquired-and-kept the lock instead of acquiring-and-releasing it,
        this second acquire would fail.
        """
        lockfile = tmp_path / "run_daily_maintenance.sh.lock"
        monkeypatch.setattr(cce, "MAINTENANCE_LOCKFILE", lockfile)
        assert maintenance_in_progress() is False
        result = subprocess.run(["flock", "-n", str(lockfile), "-c", "true"])
        assert result.returncode == 0, (
            "maintenance's own flock -n acquire was blocked after the probe ran -- "
            "the probe held the lock instead of only checking it"
        )

    def test_repeated_probing_never_starves_a_concurrent_acquire(self, tmp_path, monkeypatch):
        """
        Probes ~200 times in a tight loop (mimicking this job checking
        before every one of ~280 documents) and confirms a maintenance-
        side acquire attempt right after still succeeds -- the probe holds
        the lock for zero net time, so no amount of probing can starve a
        real acquire.
        """
        lockfile = tmp_path / "run_daily_maintenance.sh.lock"
        monkeypatch.setattr(cce, "MAINTENANCE_LOCKFILE", lockfile)
        for _ in range(200):
            assert maintenance_in_progress() is False
        result = subprocess.run(["flock", "-n", str(lockfile), "-c", "true"])
        assert result.returncode == 0


class TestProjectRunWallSeconds:
    """project_run_wall_seconds() -- the pre-launch projection's estimator."""

    def test_projection_scales_with_total_lines(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cce, "REPO_ROOT", tmp_path)
        (tmp_path / "doc.md").write_text("\n".join(f"line {i}" for i in range(100)))
        projected, total_lines = cce.project_run_wall_seconds(["doc.md"])
        assert total_lines == 100
        expected = cce.TIMEOUT_SECONDS_PER_LINE * 100 * cce.RUN_PROJECTION_SAFETY_MULTIPLIER
        assert projected == pytest.approx(expected)

    def test_multiple_paths_sum(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cce, "REPO_ROOT", tmp_path)
        (tmp_path / "a.md").write_text("\n".join(["x"] * 50))
        (tmp_path / "b.md").write_text("\n".join(["y"] * 70))
        _, total_lines = cce.project_run_wall_seconds(["a.md", "b.md"])
        assert total_lines == 120

    def test_unreadable_path_is_skipped_not_fatal(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cce, "REPO_ROOT", tmp_path)
        projected, total_lines = cce.project_run_wall_seconds(["does_not_exist.md"])
        assert total_lines == 0
        assert projected == 0

    def test_empty_path_list(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cce, "REPO_ROOT", tmp_path)
        projected, total_lines = cce.project_run_wall_seconds([])
        assert (projected, total_lines) == (0, 0)


class TestPreLaunchAssertion:
    """
    main() must refuse to launch (exit 1, printing both the projected wall
    time and the launch ceiling) when the pending set's projected wall time
    exceeds PRE_LAUNCH_CEILING_FRACTION of MAX_RUN_WALL_SECONDS, and must
    proceed otherwise. This is the exact check that would have caught the
    2026-09-21 failure: a 10.8-20.5h pre-launch projection was never
    compared against the inherited 6h ceiling before launch.
    """

    def _argv(self, tmp_path, paths_file):
        return [
            "corpus_content_extractor.py",
            "--paths-file", str(paths_file),
            "--out", str(tmp_path / "index.jsonl"),
            "--state-file", str(tmp_path / "state.json"),
            "--failures-file", str(tmp_path / "failures.jsonl"),
            "--telemetry-file", str(tmp_path / "telemetry.jsonl"),
            "--log-file", str(tmp_path / "log.log"),
            "--limit", "0",  # breaks the loop before any real call is ever made
        ]

    def test_refuses_to_launch_above_ceiling_and_prints_both_numbers(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(cce, "REPO_ROOT", tmp_path)
        (tmp_path / "doc.md").write_text("\n".join(f"line {i}" for i in range(1000)))
        paths_file = tmp_path / "paths.txt"
        paths_file.write_text("doc.md\n")
        monkeypatch.setattr(cce, "MAX_RUN_WALL_SECONDS", 10)
        monkeypatch.setattr(sys, "argv", self._argv(tmp_path, paths_file))

        with pytest.raises(SystemExit) as exc_info:
            cce.main()
        assert exc_info.value.code == 1

        err = capsys.readouterr().err
        assert "REFUSING TO LAUNCH" in err
        expected_projected = cce.TIMEOUT_SECONDS_PER_LINE * 1000 * cce.RUN_PROJECTION_SAFETY_MULTIPLIER
        assert f"{expected_projected:.0f}s" in err, "the projected-seconds number must be printed"
        assert "MAX_RUN_WALL_SECONDS=10s" in err, "the ceiling number must be printed"

    def test_proceeds_below_ceiling(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(cce, "REPO_ROOT", tmp_path)
        (tmp_path / "doc.md").write_text("\n".join(f"line {i}" for i in range(10)))
        paths_file = tmp_path / "paths.txt"
        paths_file.write_text("doc.md\n")
        monkeypatch.setattr(cce, "MAX_RUN_WALL_SECONDS", 86400)
        monkeypatch.setattr(sys, "argv", self._argv(tmp_path, paths_file))

        cce.main()  # must not raise/exit -- --limit 0 breaks the loop before any real call

        err = capsys.readouterr().err
        assert "REFUSING TO LAUNCH" not in err


class TestResumeRetriesFailuresNotSuccesses:
    """
    2026-09-22 fix: a failed document must be retried on the next normal
    (non --paths-file) resume; a successfully-processed document must
    never be reprocessed. Before the fix, the failure branch advanced
    state["last_seen_path"] exactly like the success branch, which
    permanently placed a failed document's path before the cursor and
    excluded it from every future `pending` computation -- silently
    dropping it forever. call_ollama is stubbed (deterministic, no
    network/model) so this is a pure orchestration test.
    """

    def _setup_repo(self, tmp_path, monkeypatch):
        decisions_dir = tmp_path / "brain" / "decisions"
        decisions_dir.mkdir(parents=True)
        for name in ("a.md", "b.md", "c.md"):
            (decisions_dir / name).write_text("line1\nline2\n")
        monkeypatch.setattr(cce, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(cce, "DECISIONS_DIR", decisions_dir)
        monkeypatch.setattr(cce, "MAINTENANCE_LOCKFILE", tmp_path / "maint.lock")
        monkeypatch.setattr(cce, "MAX_RUN_WALL_SECONDS", 3600)

    def _run(self, tmp_path, monkeypatch, index_file, state_file, failures_file,
             telemetry_name, log_name, call_ollama_stub):
        monkeypatch.setattr(cce, "call_ollama", call_ollama_stub)
        monkeypatch.setattr(sys, "argv", [
            "corpus_content_extractor.py",
            "--out", str(index_file), "--state-file", str(state_file),
            "--failures-file", str(failures_file),
            "--telemetry-file", str(tmp_path / telemetry_name),
            "--log-file", str(tmp_path / log_name),
        ])
        cce.main()

    def test_failed_doc_retried_success_not_rerun(self, tmp_path, monkeypatch):
        self._setup_repo(tmp_path, monkeypatch)
        index_file = tmp_path / "index.jsonl"
        state_file = tmp_path / "state.json"
        failures_file = tmp_path / "failures.jsonl"

        def fake_call_ollama_run1(path_rel, text, logger, line_count):
            if path_rel == "brain/decisions/b.md":
                return None, {"path": path_rel, "call_seconds": 1.0,
                              "error": "request_failed: simulated timeout"}
            return {f: [] for f in cce.ALL_CLAIM_FIELDS}, {"path": path_rel, "call_seconds": 1.0}

        self._run(tmp_path, monkeypatch, index_file, state_file, failures_file,
                   "telemetry1.jsonl", "log1.log", fake_call_ollama_run1)

        indexed_after_run1 = {json.loads(l)["path"] for l in index_file.read_text().splitlines() if l.strip()}
        assert indexed_after_run1 == {"brain/decisions/a.md", "brain/decisions/c.md"}
        state_after_run1 = json.loads(state_file.read_text())
        assert state_after_run1["failed"] == 1

        call_log = []

        def fake_call_ollama_run2(path_rel, text, logger, line_count):
            call_log.append(path_rel)
            return {f: [] for f in cce.ALL_CLAIM_FIELDS}, {"path": path_rel, "call_seconds": 1.0}

        self._run(tmp_path, monkeypatch, index_file, state_file, failures_file,
                   "telemetry2.jsonl", "log2.log", fake_call_ollama_run2)

        assert call_log == ["brain/decisions/b.md"], (
            f"resume must retry exactly the previously-failed document, not re-call "
            f"the already-succeeded ones or skip the failure: got {call_log}"
        )
        indexed_after_run2 = {json.loads(l)["path"] for l in index_file.read_text().splitlines() if l.strip()}
        assert indexed_after_run2 == {
            "brain/decisions/a.md", "brain/decisions/b.md", "brain/decisions/c.md",
        }


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
