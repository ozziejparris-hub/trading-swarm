# State of play — 2026-07-24 shutdown, ~2 weeks offline

**SUPERSEDED 2026-08-07 — B5 is now FINAL, not "SHIPPED, NOT FINAL" as stated throughout this doc.** O-46 (the external audit gap this doc calls out below) was cleared 2026-08-07 — see `brain/decisions/2026-06-29-overhang-ledger.md` O-46 entry ("EXTERNAL AUDIT RESULT 2026-08-07") and `brain/decisions/2026-08-07-session-summary.md` Part 3 for the full result. Zero false splits found; B5 is the frozen input to B3. Everything else in this doc (harness state, ledger snapshot, PIT components) reflects 2026-07-24 and should be read as historical context, not current status.

**Read this first on return.** Server goes offline tonight (2026-07-24) for ~2 weeks. This captures exactly where the project stands so you don't have to reconstruct it from commit archaeology.

---

## 1. Where we are

**All 3 PIT (point-in-time) components are done:**
- **B1a** — `geo_elo` (frozen area; do not lift the freeze or force a recompute)
- **B1b-positions** — PIT reconstruction of open positions as-of-T (first-repo `924fed4`), validated: 0 unexplained vs. live table across 3,234 traders
- **B1b-prices** — `price_at()` point-in-time price lookup (first-repo `5a8c680`), validated at all tested edges. CLOB downgraded strong-primary → primary-with-fallback (73.1% cross-check vs. 90% pre-registered bar, specifically weak on old/thin markets) — recorded honestly, not smoothed over.

**Backtest population is canonical and pinned:**
- `monitoring/column_definitions.py` Section 6 (`backtest_window_sql()`) is the single source of truth for "did this market conclude within window [start,end)" — tape_end-anchored, never resolution_date (O-45: resolution_date has two bulk-backfill contamination events).
- **Frozen snapshot `bt_pop_2025-11-01_v1`** exists in `backtest_population_snapshots` (first-repo `cfbc1cd`) — 4,712 markets, window_start=2025-11-01, open-ended, generated 2026-07-24T18:54Z, sql_version=1. This is the population B5 labelled against and B3 should build its splits against (re-pin a new snapshot_id if B3 needs a larger population later — the *holdout* boundary is the load-bearing pin, not this one).
- `tests/test_backtest_window_population.py` was rewritten to separate live invariants (always true regardless of population size) from snapshot facts (frozen, checked against the pinned table) — the original version hardcoded an exact count against a query that's legitimately time-varying (4,690 → 4,712 within one day) and was failing daily maintenance until fixed. Full suite green: 15/15 files, 339,700/339,700 tests.

**B5 event clustering: SHIPPED, NOT FINAL.**
- `event_cluster_labels` table built against snapshot `bt_pop_2025-11-01_v1` (first-repo `387e772`, `scripts/build_event_cluster_labels.py`): 1,891 native negRisk (522 groups) + 143 hand-standalone + 2,678 trivial-standalone = 4,712. 0 hand_sibling, 0 unsure.
- 3 mechanical structural checks run (see `brain/agent-outputs/b5-event-clustering/2026-07-24-structural-checks.md`): Check 1 (merge errors) clean, 0 found. Check 2 (date coherence) and Check 3 (price-sum) each flagged a handful, all inspected and explained as benign.
- **Gap:** the mechanical checks can't catch a false split (a real sibling-set wrongly labeled standalone) — the direction that inflates B3's bet count. See O-46 below — **this is the first task on return.**

---

## 2. What's NEXT (in order)

1. **Finish the B5 external audit (O-46).** Verify these against real-world facts the way Singapore/California were verified in the 2026-07-24 calibration:
   - `ca_ltgov_advance` (2 members, both NO, zero resolution-data confirmation)
   - `bg_seat` (4 members, all NO, zero confirmation)
   - `tx_senate_flip` (2 members, both NO — murkiest reasoning in the batch, unclear what "flip" resolves on)
   - The 15 raw singletons (candidate-shaped, no matched family) — eyeball for a missed sibling
   - Lower-priority: `ca_gov_advance` (21 members, restates the calibration-confirmed CA top-two fact, not new inference)

   If any of these is actually a sibling-set, treat it as a false-split finding: check how many others share its shape before re-running B5.

2. **Once B5 is confirmed final → B3 (the backtest harness).** Last piece before the actual experiment (FABLE §4.3 lag-sweep, §4.5 train/validate/holdout) runs.

---

## 3. Full open-ledger state (overhang ledger, `brain/decisions/2026-06-29-overhang-ledger.md`)

Active items as of shutdown:

- **O-46 (new, this session)** — B5 audit gap, see above. Not frozen-area.
- **O-45** — backtest-window population contamination. **FIXED for B5** (canonical + snapshot pinned). **OPEN for RQ1.1**: `rq1_1_elo_persistence.py`'s Period-1/Period-2 split still filters on the contaminated `resolution_date` boundary at 4 call sites (not a one-line fix — the boundary is duplicated as string literals, not referencing the file's own named constants). Report-only annotation applied 2026-07-23 (first-repo `281ee19`); the original April-2026 RQ1.1 run (trading-swarm copy, superseded, last touched 2026-05-01) carries the same class of risk via its own dynamic resolution_date-based NTILE split — noted (trading-swarm `454c9fc`), not fixed. Neither re-run yet.
- **O-40** — 2026-07-13 elections calibration, worse-than-naive result confound-checked and confirmed real (not an O-37 synthetic-data artifact). REPORT ONLY, no code/DB change. Elections-calibration current-state re-run still needs the original performance-analyst methodology or a fresh instrumented run — open/parallel item, unchanged for several sessions.
- **O-38** — `order_book_snapshots`: 62 pre-existing (+1) signal-linked rows carry a bid/ask sort-order bug. OPEN, deliberately left in place (tied to real STR-003 signal history, needs its own scoped delete-vs-flag decision, not a same-night sweep). Anything reading historical `mid_price`/`spread` from before the fix must filter these 63 rows out.
- **O-18** — pre-bug NULL `resolution_date` rows, historical/static (55 rows, drift-verified benign). OPEN, quantified only. Do NOT blanket-backfill — needs a per-row Gamma re-fetch if picked up.
- **O-37** — synthetic-market quarantine (84 markets, 926 sub-floor traders). CLOSED/stable — 5+ cycles deep, invariant reconfirmed (0 traders with a qualifying geo_elo dependent on a flagged market). §8 correction: the 926 all show `geo_resolved_trades_count=0` post-correction, the earlier "17 fully-synthetic / 909 partial" split was pre-exclusion and is stale language if you see it referenced elsewhere.
- **B4 capture** — 3 persistent thin-market `failed_no_book` cases (the same handful of thin geo markets each day, most recently ~2/day). Not investigated further; low-priority/expected given thin liquidity.

Resolved this window, for context (don't re-open): O-39 (B1a validated), O-41–O-44 (B1b-positions ledgered), O-15/O-16/O-17 (resolution_date/pnl_worker bugs, all fixed with commits cited in memory), O-14 (offsite backup, 2nd root cause fixed via automount), O-13 (monitoring stall, closed clean).

---

## 4. Harness state at shutdown

- `daily_maintenance.py`: **ALL OK: 33/33** expected on next run (test-suite failure that blocked 2026-07-24's run is fixed).
- `audit_invariants.py`: 25 checks, 0 CRITICAL, 3 REGRESSION (T2 pending-on-resolved x2 — normal day-to-day fluctuation, not a spike; total_invested mismatch flat at 10,055 — longstanding, not new).
- Services: `polymarket-monitoring`, `polymarket-observer`, `trading-swarm` all active as of shutdown prep.

See §3 of `brain/decisions/2026-07-24-shutdown-safety.md` (this session, part 3) for the actual shutdown sequence and pre-shutdown checklist.
