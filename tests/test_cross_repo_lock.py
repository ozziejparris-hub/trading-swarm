"""
test_cross_repo_lock.py

THE test that proves (or would have disproved) the central claim of the
atomicity-siblings fix: a write to trading-swarm/brain/signals.json from
this repo and a write from first-repo (register_signal.py,
detect_counter_signals.py, score_str003_signals.py) genuinely serialize
against each other — not just against other writers in the same repo.

Both repos load an IDENTICAL absolute lock-path from a shared JSON target:
<resolved target>.lock. Neither repo can import the other's Python module
(separate repos, no dependency between them by design — see both
json_safety.py docstrings for why that's the right call), so this test
dynamically loads first-repo's scripts/json_safety.py by file path. That is
NOT something production code does anywhere — it's this test harness
verifying, from the outside, that two independently-maintained
implementations actually agree on the one thing that matters: the lock
path. If a future edit changes _lock_path() in one repo and not the other,
this test is what catches it.

Section (a) is the non-tautological anchor: it proves the OLD scheme was
NOT a real cross-repo lock at all — register_signal.py used to flock
signals.json itself, while orchestrator.py has always flocked a
signals.json.lock sidecar. Those are two different inodes, so the two
locks never contended with each other, at all, ever — proven here by
showing both can be held AT THE SAME TIME with zero wait, which is
impossible for a single real mutex.

Section (b) proves the NEW scheme is real: the identical lock derivation
on both sides means one side's holder blocks the other side's acquirer.

Section (c) is the full proof requested: real OS processes running the
ACTUAL code from both repos (not simulated), hammering the same
signals.json concurrently, asserting no lost updates and a clean parse at
the end — this must currently PASS (post-fix) where it would have been
capable of losing updates pre-fix (per section a's proof that the old
locks didn't exclude each other at all).

Run: python3 -m pytest tests/test_cross_repo_lock.py -v
"""

import fcntl
import importlib.util
import json
import multiprocessing
import sys
import time
from pathlib import Path

import pytest

import orchestrator.json_safety as swarm_js

FIRST_REPO_JSON_SAFETY = Path("/home/parison/projects/first-repo/scripts/json_safety.py")


def _load_first_repo_json_safety():
    """Dynamically load first-repo's json_safety.py by absolute path — the
    one place in either repo this cross-import happens, and only because
    this test's entire purpose is verifying the two independently-written
    modules actually agree, from the outside, without coupling either repo
    to the other at runtime."""
    spec = importlib.util.spec_from_file_location(
        "firstrepo_json_safety", FIRST_REPO_JSON_SAFETY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pytestmark = pytest.mark.skipif(
    not FIRST_REPO_JSON_SAFETY.exists(),
    reason="first-repo checkout not present on this machine",
)


def test_both_repos_derive_the_identical_lock_path(tmp_path):
    firstrepo_js = _load_first_repo_json_safety()
    target = tmp_path / "signals.json"
    target.write_text("{}")

    swarm_lock = swarm_js._lock_path(target)
    firstrepo_lock = firstrepo_js._lock_path(target)

    assert swarm_lock == firstrepo_lock
    assert swarm_lock == target.with_name("signals.json.lock")


# ─────────────────────────────────────────────
# (a) non-tautological anchor: the OLD scheme was not a real lock at all
# ─────────────────────────────────────────────

def _old_register_signal_flock_holder(target_str, hold_seconds, started_evt):
    """Replicates register_signal.py's PRE-FIX lock: flock the target file
    ITSELF (r+), not a sidecar."""
    with open(target_str, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        started_evt.set()
        time.sleep(hold_seconds)
        fcntl.flock(f, fcntl.LOCK_UN)


def test_old_cross_repo_locks_did_not_exclude_each_other(tmp_path):
    """Start a process holding the OLD register_signal.py-style lock
    (flock on signals.json itself) for a while. Meanwhile, try to acquire
    the swarm's ACTUAL lock (json_lock on signals.json.lock, the sidecar).
    If the two schemes were really the same mutex, this would block for
    ~hold_seconds. It doesn't — it returns near-instantly, proving the
    pre-fix cross-repo lock was fake: two different inodes, zero mutual
    exclusion, the whole time detect_counter_signals.py and
    score_str003_signals.py (which had NO lock at all) or
    register_signal.py (locking the wrong file) could write concurrently
    with the swarm orchestrator with no serialization whatsoever."""
    target = tmp_path / "signals.json"
    target.write_text(json.dumps({"str003_signals": []}))

    ctx = multiprocessing.get_context("fork")
    started = ctx.Event()
    hold_seconds = 2.0
    holder = ctx.Process(
        target=_old_register_signal_flock_holder,
        args=(str(target), hold_seconds, started),
    )
    holder.start()
    assert started.wait(timeout=5), "holder never acquired its lock"

    t0 = time.monotonic()
    with swarm_js.json_lock(target):
        elapsed = time.monotonic() - t0

    holder.join(timeout=10)
    assert elapsed < 0.5, (
        f"acquiring the swarm's sidecar lock took {elapsed:.2f}s while the "
        f"old-style target-file lock was held — if this ever blocks, the "
        f"pre-fix schemes were somehow compatible after all (they were not)"
    )


# ─────────────────────────────────────────────
# (b) the NEW scheme is a real, shared mutex
# ─────────────────────────────────────────────

def _new_style_holder(target_str, hold_seconds, started_evt, use_first_repo):
    if use_first_repo:
        js = _load_first_repo_json_safety()
    else:
        import orchestrator.json_safety as js
    with js.json_lock(Path(target_str)):
        started_evt.set()
        time.sleep(hold_seconds)


def test_new_cross_repo_locks_genuinely_exclude_each_other(tmp_path):
    """First-repo's json_lock() holds the lock; the swarm's json_lock()
    must wait for it — proving the two are the SAME mutex now, not two
    that happen to share a name."""
    target = tmp_path / "signals.json"
    target.write_text(json.dumps({"str003_signals": []}))

    ctx = multiprocessing.get_context("fork")
    started = ctx.Event()
    hold_seconds = 1.5
    holder = ctx.Process(
        target=_new_style_holder,
        args=(str(target), hold_seconds, started, True),  # first-repo holds
    )
    t_launch = time.monotonic()
    holder.start()
    assert started.wait(timeout=5)

    with swarm_js.json_lock(target):  # swarm-side acquirer
        elapsed_since_launch = time.monotonic() - t_launch

    holder.join(timeout=10)
    assert elapsed_since_launch >= hold_seconds * 0.8, (
        f"swarm's json_lock() acquired after only {elapsed_since_launch:.2f}s, "
        f"before first-repo's {hold_seconds}s hold ended — the two repos' "
        f"locks are not the same mutex"
    )


# ─────────────────────────────────────────────
# (c) the full proof: real processes, real code, both repos, no lost updates
# ─────────────────────────────────────────────

def _swarm_writer(target_str, idx, n_iters):
    import orchestrator.json_safety as js
    path = Path(target_str)
    for _ in range(n_iters):
        with js.json_lock(path):
            data = js.load_json_or_raise(path, default=lambda: {"str003_signals": []})
            data["str003_signals"].append({"writer": "swarm", "idx": idx})
            js.atomic_write_json(path, data)


def _first_repo_writer(target_str, idx, n_iters):
    js = _load_first_repo_json_safety()
    path = Path(target_str)
    for _ in range(n_iters):
        with js.json_lock(path):
            data = js.load_json_or_raise(path, default=lambda: {"str003_signals": []})
            data["str003_signals"].append({"writer": "first-repo", "idx": idx})
            js.atomic_write_json(path, data)


def test_real_concurrent_writers_from_both_repos_never_lose_an_update(tmp_path):
    """The actual proof requested: real OS processes, some running the
    swarm's json_safety.py, some running first-repo's json_safety.py,
    hammering the same signals.json concurrently. Every one of their
    appends must survive, and the file must always parse — this is only
    possible because both sides contend on the identical lock path proven
    in test_both_repos_derive_the_identical_lock_path above."""
    target = tmp_path / "signals.json"
    swarm_js.atomic_write_json(target, {"str003_signals": []})

    ctx = multiprocessing.get_context("fork")
    n_each = 6
    n_iters = 8
    procs = []
    for i in range(n_each):
        procs.append(ctx.Process(target=_swarm_writer, args=(str(target), i, n_iters)))
        procs.append(ctx.Process(target=_first_repo_writer, args=(str(target), i, n_iters)))

    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)
        assert p.exitcode == 0

    data = json.loads(target.read_text())  # must parse cleanly — no torn writes
    entries = data["str003_signals"]
    assert len(entries) == n_each * n_iters * 2, (
        "a lost update means a swarm write and a first-repo write "
        "interleaved instead of genuinely serializing"
    )
    swarm_entries = [e for e in entries if e["writer"] == "swarm"]
    firstrepo_entries = [e for e in entries if e["writer"] == "first-repo"]
    assert len(swarm_entries) == n_each * n_iters
    assert len(firstrepo_entries) == n_each * n_iters
    assert sorted(e["idx"] for e in swarm_entries) == sorted(list(range(n_each)) * n_iters)
    assert sorted(e["idx"] for e in firstrepo_entries) == sorted(list(range(n_each)) * n_iters)
