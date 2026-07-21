# 2026-07-21 Session Summary

## Theme

Session opened to start B1 (edge-experiment PIT engine) but a foundation check surfaced that ~966K geo/elec trades under the experiment were synthetic. Became a full detect→prove→verify→remediate cycle on the O-37 contamination, THEN built and validated B1a (the PIT geo_elo reconstruction core). Through-line: validate against something proven-clean, never against something merely hoped-clean — which recurred at every major step.

---

## What Shipped

### O-37 synthetic-market quarantine — CLOSED (first-repo `5777e45`; trading-swarm `9e05c81`, `83cbe7b`)

- **Detection:** dual-signal convergence (stats heuristic + last session's token-backfill failures) on synthetic geo/elec markets.
- **Proof phase — CRITICAL:** the naive detector flagged 1,614 markets but had false positives in BOTH directions (low-volume real markets with coincidental txhash gaps flagged; 4 real recurring-format markets caught in the naive core). Live-API verification refined 1,614 → 84, every one individually verified absent from Polymarket. Root cause: a single bulk import on 2026-01-12/13 plus 2026-04-01, `api_id` NULL, masquerading as `live_monitoring`.
- **Verified blast radius:** 84 markets / 965,542 trades, 0 cohort / 0 Pool-C exposure — the prior session's "34%" estimate was false-positive noise, verified down to ~0.
- **Remediation:** quarantine-not-delete (`trade_gap_flag=1`, `flag_reason='synthetic_quarantine_2026-07-19'`), bounded recompute of 953 affected traders, 926 sub-floor corrected (17 fully un-qualified — their entire scoring history was synthetic, `resolved_count=0`). Success invariant proven on live data: 0 traders carry a qualifying `geo_elo` depending on a flagged market.
- **Three near-misses caught by prove→design→execute, not shipped blind:**
  1. The blanket-1,614 quarantine, which would have deleted ~1,526 REAL markets.
  2. Committing before handling the 926, which would have left 17 fabricated LEGENDARY scores in the ranking.
  3. The beat-5 flawed comparison (time-decay drift contaminating the diff) — caught and re-run with a same-instant control.

### B1a PIT geo_elo reconstruction — BUILT + VALIDATED (first-repo `dde13a4`; trading-swarm `252a328`)

- `reconstruct_geo_elo_at(T)`: wraps the production formula functions (`_compute_geo_elo` etc.) with a T-bound. Three correctness guards:
  - T = the step-9 write-time from the maintenance log (NOT the date-only `snapshot_date`).
  - Tape-end computed unbounded, compared `<= T` (the O-36 resolution bound).
  - Flag-aware exclusion of the 84 quarantined markets.
- **Validation reframed mid-build:** the `elo_snapshots` stored `geo_elo` turned out to be FROZEN-stale (06-18, for ~70% of sampled traders) — not a clean oracle. Validated against production-at-now instead (a stronger oracle, requiring no stored ground truth): 3,229/3,229 exact match (2 `geo_elo_active` diffs, both explained as a per-trader `datetime.now()` truncation-edge artifact, not a bug). The one reimplemented predicate — the pool gate — matched production table-wide: 164,303 rows, 0 mismatch.
- **Two deferrals surfaced + named for B1b:**
  1. `trade_result`-availability-as-of-T bounding — an evaluation-lag finding, same event-time/write-time class as O-33, one column over.
  2. Since-deleted-duplicate-rows limit — some past states are unrecoverable from the current trade tape; an inherent bound on PIT-from-current-data, not a bug.

---

## Ledgered This Session

- **O-39** — `elo_snapshots.geo_elo` frozen-stale (06-18) while `geo_resolved_trades_count` in the same row live-updated — internally-inconsistent rows, rooted in the standing ELO freeze. Report-only, cross-referenced to the Layer-2/unfreeze workstream. This is *why* the snapshots couldn't serve as B1a's oracle.
- **O-40** — the elections-calibration/O-37 link tested and REJECTED: the 07-13 worse-than-naive elections calibration finding is real/structural, not a synthetic-data artifact (the synthetics weren't in the calibration sample; same-sample before/after Brier was identical, 0.0608 both ways). Opens the next-session item to re-run elections calibration with the original methodology to get a current, comparable number.

---

## Also

- Writer A's Sunday 07-19 canonical run reconfirmed clean — no formula divergence; the day-over-day change is the normal Sunday recompute.
- Sunday DB-lock contention: maintenance write-contention, self-limiting, recurs weekly on the long Sunday run — known pattern, ledger item, not actioned.
- B4 healthy, capturing forward. One open item: `failed_no_book=3` on a recent run — worth a glance next session, not urgent.

---

## State For Next Session

- B1a done + validated. B1b (positions/prices PIT) is next — its scope is sharply defined by the two named deferrals above; best started fresh-session with its own scoping read.
- Open/parallel: elections-calibration current-state re-run (new item, from O-40), O-36 (`resolution_date` generator), O-18 (import investigation — O-37 handed it the 2026-01-12/13 import signature to check against), O-38, O-39, B4's `failed_no_book` glance.
- Deferred unchanged: `is_taker` retire-or-wire, ELO unfreeze/Layer-2, swarm items behind the experiment.

---

## Methodology Thread

Every major step this session refused to build on unverified ground, and was right to:

- The quarantine we didn't run blind (would have deleted 1,526 real markets).
- The commit we didn't rush (would have left 17 fabricated scores in the ranking).
- The B1a validation we didn't run against frozen snapshots (would have been a match-the-stale-target illusion — validated against production-at-now instead, and ledgered *why* as O-39).
- The elections finding we didn't "resolve" via the appealing-but-false synthetic explanation.

Prove the target is clean before validating against it; if it isn't, find out why rather than force the match.
