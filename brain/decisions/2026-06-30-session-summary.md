# Session Summary — 2026-06-30

## THEME: "Verify the thing we depend on"

Today's two surface tasks (score June 30 STR-002/STR-003 signals, measure STR-002 revalidation) were both blocked or routine on their face — but *interrogating why* surfaced more value than the tasks themselves would have:
- STR-003 scoring looked blocked → checking the oracle (not just assuming it was down) confirmed Iran/Ukraine markets are genuinely still OPEN on-chain (healthy waiting, not a bug).
- Verifying the resolution-collection pipeline (rather than trusting it worked) surfaced 3 silent gaps, one of which (cap-latency) was actively dropping same-day quarter-end clusters.
- The STR-002 revalidation measurement (routine, gate-due) turned into the first concrete evidence that an existing data-integrity overhang (O-7) has a live strategy-performance cost.

**Methodology lesson:** when a task looks blocked or routine, verify the dependency itself before moving on — that's where today's actual findings came from, not from the nominal task.

---

## WHAT SHIPPED (commit hashes, both repos)

### first-repo `6c08afc` — resolution-collection round-robin fix
June 30 STR-002/003 signal-scoring was blocked because Pass 2 of resolution collection (`run_recent_overdue_pass`) wasn't keeping up. Root-caused to **3 silent gaps** in the collection pipeline (only one fixed today, see O-12 below for the other):

- **Cap-latency gap (fixed):** Pass 2 used `ORDER BY resolution_date ASC LIMIT 100`, which always sorted same-day resolutions to the bottom and silently dropped markets once the queue exceeded the cap. June 30 itself was the trigger case: 173/186 markets resolved same day, overflowing the 100-row cap. `last_checked` was also only updated on resolution (not on every check), so checked-but-still-open markets kept stale timestamps and re-rose to the top every run — no rotation at all.
- **Fix (3 coupled parts):** `ORDER BY last_checked ASC NULLS FIRST` (true priority queue) + update `last_checked` on every CLOB check, not just resolution (the keystone — without this the ORDER BY change is a no-op) + raise `LIMIT` 100→200 (buffer for calendar-cluster spikes). Added cap-hit observability (`[WARN]` log + "N of TOTAL in window" on every run — previously silent).
- **Verdict:** latency, not loss — Pass 3 is a 7-day safety net that still catches everything. But it was a real ~7-day delay for end-of-month/quarter signal markets; now resolves within ~2 runs and is logged.
- **Tested:** `tests/test_recent_overdue_rotation.py` (7 new rotation tests), full suite 53/53 green.

### trading-swarm `89347ad` — O-12 added to overhang ledger
The **other** collection gap surfaced during the same investigation, distinct from the cap-latency fix: some `market_id`s are **unroutable** through any path — CLOB returns empty, Gamma doesn't recognize the hex ID, no `api_id`/`condition_id` fallback exists. Example: Putin market `0x657195fda8...`, 90 days stale. This is a **permanent-loss class**, not a latency class — Pass 3's safety net doesn't help because the ID never resolves through any path. Needs its own investigation (characterize scope, find root cause — likely V1/V2 ID format mismatch). Gamma-null observability (warn on markets with no `api_id`/`condition_id`) folded into O-12's scope rather than tracked separately.

### trading-swarm `d7f2ba5` (tightened in `ce80597`) — STR-002 thesis-cell analysis
The June 30 scheduled revalidation measurement (`brain/strategy-registry.md` gate: "Next revalidation due: 2026-07-01"). 40 signals scored, **22.5% accuracy, -7.7% avg edge** — well below the 60% gate (Wilson 95% CI [12.3%, 37.5%], upper bound below gate).

**Verdict: (b) signal-quality/filtering problem — NOT FALSIFIED, NOT YET VALIDATED.** Failures cluster mechanistically, not randomly:
- Gap ≥60pt (divergence magnitude): 0/24 correct. Gap <60pt: 9/16 (56.2%).
- 77.5% of signals fire in NEAR_RESOLVED regime (price ≤0.10 or ≥0.90) — thin-pool share-weighting artifacts, not conviction.
- The clean test cell (`has_proven_trader=1 AND regime='CONTESTED'`) — the one that actually tests the premise — is **n=2**. Too small to confirm or rule out an edge.
- STR-003 (structurally similar thesis, different filters) is tracking toward its own gate on overlapping data, not failing — evidence against the premise being dead, not evidence it's confirmed.

v2 filters (cap gap <60pt, fix ELO- vs share-weighting mismatch, stop gating on `comprehensive_elo` until O-7 lands, suppress NEAR_RESOLVED, dedupe correlated multi-candidate clusters) are specified as a **pre-registered forward test** — explicitly NOT retrofit to the existing 40 (that would be circular/overfit). Full detail: `brain/decisions/2026-06-30-str002-thesis-cell-analysis.md`.

---

## THE CONNECTIVE THREAD (raises O-7's priority)

Today produced the first **concrete, measured** evidence that O-7 (the `comprehensive_elo` Layer-2 reconciler, currently blocked behind O-5→O-6) has a live downstream cost, not just an abstract data-integrity smell:

STR-002's ELITE/QUALIFIED tiers (39 of 40 signals in today's batch) gate on `comprehensive_elo`. Per O-6's investigation (`brain/decisions/2026-06-29-comprehensive-elo-writer-map.md`), that column is currently `base × pnl` only — the daily writer (`apply_full_elo_modifiers.py`) strips the behavioral dimension every day after Sunday's full recalc (intentional, pending the O-7 redesign — RQ-CONTESTED-001). So STR-002's trader-quality filter is, right now, a P&L-momentum proxy instead of the 6-dimensional skill score its own premise assumes.

This doesn't change O-7's position in the dependency chain (still gated behind O-5/O-6 for unrelated reasons) — but it adds a second, *measured* motivating example beyond the diagnostic itself. O-7 is no longer "internal cleanup with no named external cost." Cross-referenced in the ledger (`brain/decisions/2026-06-29-overhang-ledger.md`, O-7 entry, "DOWNSTREAM IMPACT CONFIRMED" line).

---

## STATE FOR NEXT SESSION

**System health:** clean. Services up, daily maintenance completing, O-1 (`run_tests.py` wired into maintenance) live in production, harness shows 0 critical.

**STR-003 scoring: STAGED, not done.** Iran/Ukraine markets confirmed still OPEN on-chain (checked, not assumed) — this is healthy waiting on the oracle, not a bug:
- `STR003-007` — "Will the Iranian regime fall by June 30?" — condition_id `0x9352c559e9648ab4cab236087b64ca85c5b7123a4c7d9d7d4efde4a39c18056f`
- `STR003-008` — "European country agrees to give Ukraine security guarantee by June 30?" — condition_id `0x2a6d2cb5250e55c9c910e2ce005cc67d956973fbffe9b69539fb4ab58383cc59`
- Both tracked in `brain/signals.json` under `str003_signals`.
- Scoring steps live in `scripts/score_str003_signals.py` (first-repo); the trigger query it runs per-market is `SELECT resolved, winning_outcome, resolution_date FROM markets WHERE market_id = ?` — once that flips to `resolved=1` for these two IDs, re-run the script.
- Thanks to the `6c08afc` rotation fix, once the oracle does fire, collection picks these up within ~2 resolution-collection runs instead of the old ~7-day latency.

**Ledger status** (`brain/decisions/2026-06-29-overhang-ledger.md`):
- O-0 (Pool C decline) — open, hot, blocks July 1 RQ wave.
- O-1 (run_tests.py wiring) — **done**.
- O-2 (category cache), O-3 (timestamp normalization) — still open, both **regressing** (worsening since #39), independent of ELO arc.
- O-6 (comprehensive_elo daily-path) — investigated-complete, intentional, no code change needed.
- O-7 (Layer 2 reconciler) — open, blocked behind O-5/O-6, **priority raised** today via the STR-002 link above.
- O-12 (resolution-collection ID-routing gap) — **new today**, permanent-loss class, uninvestigated.
- Critical path to Layer 2 unfreeze unchanged: O-5 → O-6/O-7 → unfreeze `recalculate_comprehensive_elo.py`.

**Both repos clean as of:**
- first-repo: `6c08afc`
- trading-swarm: `ce80597`
