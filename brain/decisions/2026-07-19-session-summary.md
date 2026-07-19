# 2026-07-19 Session Summary — O-37 Synthetic-Market Quarantine: Detect, Prove, Verify, Remediate, Close

## Theme

Session opened to start the edge-experiment build (B4 done last session, B1 next) — but
confirming the foundation first surfaced that ~966K geo/elec trades under the experiment were
fabricated. The session became a full detect→prove→verify→remediate cycle on the
synthetic-market contamination (O-37), ending with B1's ELO baseline **proven** clean rather
than assumed clean. Two experiment-relevant gates — the Writer A Sunday canonical run and
O-37 — both resolved this session.

---

## Writer A Sunday canonical run — confirmed clean (gate closed)

First real production run of the Stage 3 canonical ELO path. Completed via systemd timer
(not manual): **26,942 updated, 0 failed, exit 0, 110.9 min.**

- No formula divergence: zero sign-flips/negatives/new-NULLs; range/soft-cap/population-drift
  invariants all 0.
- The large day-over-day change fraction (58%) is normal Sunday full-recompute behavior (prior
  Sunday showed 90%+), **not** divergence — the dry-run's 98.95% figure measured formula
  reproducibility against frozen inputs, a different thing from day-over-day movement. Recording
  this distinction for the record since it's easy to conflate.
- Downstream Writer B saw fully-populated base ELO. Test suite green (339,663).

---

## O-37 synthetic-market quarantine — detected, proven, verified, remediated, closed

This is the session's main work. Full arc, as the durable record.

### Detection — dual-signal convergence

The O-37 stats heuristic (duplicate-title / implausible per-market stats) and last session's
token-backfill failures (54 open geo/elec markets with trade history but no live CLOB/Gamma
listing) independently fingered the same population. Anchor case: `0x08e61703`
("USA ceasefire agreement..."), ~15K trades, distinct trade_ids, NULL tx_hashes.

### Proof phase — the detector had false positives in both directions (the critical finding)

The naive detector flagged **1,614** markets. Live-API verification proved:

- "No token + zero txhash" is legitimate noise at low volume — 148 confirmed-REAL markets had
  zero txhash, none with >100 trades.
- The low-volume flagged tail was 10/10 REAL on live API (un-backfilled real markets, e.g.
  "Finnish Presidential Election").
- Running the fingerprint check **backward** against the 88-market core caught 4 REAL
  recurring-format markets ("Will Trump say 'Peanut'").

Target refined **1,614 → 84**, every one individually live-verified absent from Polymarket —
not sampled.

### Verified blast radius

**84 markets / 965,542 trades.** 0 cohort, 0 Pool-C, no tier-gate risk. The prior session's
"14/41 cohort, 34% exposure" figure was almost entirely false-positive noise — verified down to
effectively 0 experiment-relevant exposure. Single import root cause: 2026-01-12/13 (50 markets)
+ 2026-04-01 (34 markets), `api_id` NULL throughout, `data_source` masqueraded as
`'live_monitoring'`. No second generator found.

### Remediation — quarantine, not delete (first-repo commit `5777e45`, in-session recompute)

- Flagged 84 markets (`trade_gap_flag=1`, new `flag_reason='synthetic_quarantine_2026-07-19'`).
- Bounded recompute of the 953 affected traders. Handled the skipped-thin gap (see methodology
  below): 926 traders dropped below the 5-trade qualifying floor once synthetics were excluded —
  corrected to the system's existing sub-floor/NULL convention, so no stored `geo_elo` depends
  on flagged data.
- 17 high-ELO traders (up to 2,541 `geo_elo_active`, some above the 2175 LEGENDARY gate) fully
  un-qualified because their **entire** scoring history was synthetic
  (`resolved_count=0` post-correction — not partial).

### Success invariant — proven on live data

Stored `geo_elo` matches an independent flag-aware recompute, **0/953 mismatch**.

Note the invariant-wording catch: a literal "no qualifying trade in a flagged market" check
can't return 0 under quarantine-not-delete, since the rows still exist. The correct invariant is
**stored-value-matches-flag-aware-recompute**. Recording this as a methodology note for anyone
re-running this class of check.

---

## Methodology thread (the session's real lesson — three near-misses caught by prove→design→execute)

1. **The blanket-1,614 quarantine we didn't run** would have deleted ~1,526 real markets (false
   positives). Caught by live-API verification before any write.
2. **The commit-before-handling-the-926 we didn't make** would have left 17 fully-synthetic
   LEGENDARY-range scores sitting in the ranking table. Caught by the
   dry-run-before-persist discipline.
3. **The beat-5 flawed comparison** (fresh recompute vs. frozen stored values mixed time-decay
   drift into the quarantine effect) — caught and re-run with an isolated same-instant
   flagged-vs-unflagged control. Same class of trap as event-time-vs-write-time confusion.

The write we almost made, and the write we almost rushed, were both prevented by
proving-then-designing-then-executing rather than acting on strong-but-unverified evidence.
Detector precision cut both ways — false positives AND false negatives — which is why
individual ground-truth verification (not the heuristic) defined the final target, not the
initial 1,614 or even the refined-but-unverified 88.

---

## Resequencing record

- O-37 remediation was briefly sequenced ahead of B1 (on the unverified 34%-exposure number),
  then moved back to parallel-not-gating once verification proved 0 cohort/Pool-C exposure.
  Recording both the initial call and the evidence-driven reversal honestly — the first number
  drove a real (if temporary) resequencing decision before it was checked.
- B1 remains next; its ELO baseline is now proven synthetic-free.

---

## Also this session

- **O-38 updated + resolved-in-place.** The one `order_book_snapshots` row touching a flagged
  O-37 market traced to O-38's already-documented sort-order-bug rows (same signal family / date
  range) — folded into O-38, not treated as new contamination.
- **Live DB-lock contention (this morning).** `background_pnl_worker.py` hit "database is
  locked" during the 6h42m `daily_maintenance` run (finished 12:42 UTC, ALL OK 36/36). Diagnosed
  as maintenance write-contention, not the ELO run. Confirmed self-limiting: locks stopped
  post-12:42, worker recovered at full cadence, `pnl_skip=0` (nothing permanently dropped). The
  stale-P&L count was a rolling-24h-window artifact (throttled cohort aging past 24h) — crested
  and turned over as predicted. Noting the maintenance-runtime/contention pattern for the ledger
  (connects to the hung-RPC-no-timeout robustness item) — not actioned, worth watching if
  maintenance runtime keeps growing.
- **B4 healthy on day-2.** Liveness summary fired again (selected/captured, 0 skipped/failed),
  corrected mid/spread values still sane. Anti-rot guard working.

---

## State for next session

- O-37 closed. B1 clear to proceed on a proven-clean ELO baseline.
- B4 capturing forward, no attention needed.
- Deferred/parallel: O-36 (`resolution_date` generator, still daily, workaround insulates the
  experiment), O-18 (import investigation — O-37 just handed it fresh evidence: the
  2026-01-12/13 + 04-01 import signature), elections calibration (worse-than-naive finding —
  worth re-checking now that synthetic ELECTION markets are quarantined; the before/after may
  partly resolve it), O-38.
- Consider: does removing the synthetic election markets shift the 2026-07-13 elections
  calibration? Flagged for next session, not actioned.

---

## Repo state

- **first-repo**: commit `5777e45` ("feat: O-37 synthetic-market quarantine — 84 markets /
  965,542 trades") pushed to `origin/main` per standing authorization, confirmed up to date.
  Working tree carries unstaged routine state files (`data/.last_requeue_run`,
  `data/category_backfill_state.json`, `logs/focus_ratio_review.json`) — cron-generated, not
  session work product, left uncommitted (no authorization given this session to commit in
  first-repo beyond confirming `5777e45`'s push state).
- **trading-swarm**: this summary committed alongside `brain/findings.json` (routine
  `score_str003_signals` cron output), `brain/integration-health.json` (routine daily
  maintenance stamp), and `logs/backup.log` / `logs/backup_offsite.log` / `logs/orchestrator.log`
  (routine log growth). Untracked routine agent-output files
  (`brain/agent-outputs/data-audit/2026-07-19-audit.json`,
  `brain/agent-outputs/pre-resolution/2026-07-19-pre-res-scan.json`,
  `brain/agent-outputs/str002-scoring/2026-07-19-str002-scoring.json`) committed as
  cron-generated artifacts, not session work product — consistent with the 2026-07-18 session's
  convention.
