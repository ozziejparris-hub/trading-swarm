# 2026-07-22 Session Summary

## Theme

Read-only morning snapshot (services/maintenance/O-37/harness/B4/git all clean, one anomaly flagged), then a bounded root-cause dig on that anomaly, then B1b-positions: scoped, designed, built, single-trader-proved, full-population-validated, and shipped — the first of B1b's two halves (positions done; prices scoped separately, not started).

---

## What Shipped

### T2 harness spike — root-caused, benign, already drained (no code change)

Morning snapshot flagged a 746x overnight spike in `audit_invariants`' "pending on resolved non-gap markets (flagged traders)" check (269 → 200,669). Traced to `background_backfill_worker.py`'s known Unknown-category/pending insert pattern (O-30-adjacent) accumulating an unusually large batch (202,285 vs. the normal ~40,000) that `evaluate_new_trader_results.py` (daily_maintenance step 21) cleared **within the same maintenance run**, before the audit numbers were even pulled. Live re-run of `audit_invariants.py` confirmed drained to 1,535 (near the 269 baseline). Correction of an earlier misreport in-session: an initial "still growing" claim compared an unfiltered live count against the audit's `is_flagged=1`-filtered metric — apples to oranges; the filtered comparison shows drainage, not growth. No ledger item — not a new defect, a bigger-than-usual instance of a known, self-healing mechanism.

### B1b-positions — BUILT + VALIDATED + SHIPPED (first-repo `924fed4`)

- **Scoping first** (Parts A–D, read-only): confirmed positions are cleanly time-boundable (`entry_timestamp <= T AND (exit_timestamp IS NULL OR exit_timestamp > T)`), corrected a "~40% NULL exit_timestamp" misreading from a prior session to what it actually is (~40% `is_synthetic_close=1`, inheriting O-36's resolution_date unreliability — quantified: 4.0% of synthetic closes in-window have exit *before* tape-end, an impossible ordering; 5.6% sit >14 days late). Confirmed CLOB `prices-history` mechanics for the B1b-prices half (separate, unscoped this session) and reused `scripts/b2_price_history_probe.py`'s existing token-resolution/chunked-fetch logic rather than re-deriving it.
- **Design confirmed before building:** `analysis/pit_positions.py::reconstruct_positions_at(conn, T, addresses)` — trade-tape replay bounded to `trades.timestamp <= T`, not a filter over the stored `positions` table (whose synthetic-close timestamps are the unreliable part). Reuses `PositionTracker._match_group`/`_match_group_simplified`/`Position.close_position` (unchanged) and `_ensure_tape_end_temp_table` (imported directly from B1a's `analysis/pit_geo_elo.py`, not rebuilt). Synthetic-close exit is tape-end, explicitly documented as a BOUND ("market had stopped trading by here"), not a precise close instant. Deliberately preserves production's existing gap (only `status=='open'` positions get synthetically closed, never `partially_closed`) so a T=now reconstruction stays a clean twin of the live table for validation — ledgered separately (O-41) rather than silently fixed.
- **Stage 2 (single-trader proof) surfaced two real, unrelated production bugs** while root-causing why T=now didn't initially match the live table: **O-42** (`is_synthetic_close` flag freezes at its first-insert value — `store_positions()`'s upsert never updates it on re-upsert; true synthetic-close population is ≥63.6% of closed positions table-wide, not the 39.7% the flag alone suggests) and **O-43** (`position_id` collisions — same trader/market/outcome/entry_timestamp — silently collapse distinct positions in the same upsert; on one trader, 235 true positions collapsed to 107 stored, including one case where a real $10.52-P&L closed position was overwritten by a $0.0000659 floating-point dust remainder). Both real, both pre-existing, both out of B1b's scope to fix (B1b never reads the stored flag and never persists through the collision-prone upsert, so is unaffected by either).
- **Stage 3 (full-population validation, 3,234 Pool-C traders) found a third: O-44** (any FIFO/simplified-matching boundary shift from new trades — not only the 50-trade dispatch threshold, any trade at all — strands the pre-shift rows as permanent orphans; store_positions() has no deletion path). After accounting for all three: **T=now reconstruction vs. the live table reconciles to ZERO unexplained divergence** across 1,246,606 compared items (1,231,158 reconstructed + 15,448 live-only orphans). `partially_closed`: 947/947 exact, no divergence of any kind. `open`: 356,522 exact / 5,274 O-43 / 10,311 O-44 / 0 unexplained — touched by the same defects as closed positions, just fully explained (corrected an over-generalization from the single-trader stage that opens were untouched).
- **The flip count** (O-36 correction's measured value): at T=2026-05-22, **16,981/396,231 (4.29%)** of still-open-after-real-trades positions in resolved markets would get a DIFFERENT open/closed verdict under a naive resolution_date-gated reconstruction vs. tape-end-gated. Concrete, population-scale sizing of what the O-36 correction buys the backtest.

---

## Ledgered This Session

- **O-41** — `PositionTracker.apply_synthetic_closes` skips `partially_closed` positions (only `status=='open'` gets synthetically closed) — stale `remaining_shares` in resolved markets, never resolved. Report-only; B1b preserves this behavior deliberately (fixing it would break the T=now validation anchor).
- **O-42** — `store_positions()`'s upsert never updates `is_synthetic_close` on re-upsert — flag freezes at first-insert value. True synthetic-close population ≥63.6% of closed positions vs. 39.7% the flag suggests (893,394 mislabeled table-wide). Report-only.
- **O-43** — `position_id` collisions (same trader/market/outcome/entry_timestamp) silently collapse distinct positions via the same upsert; real closed positions can be overwritten by unrelated dust remainders. Report-only.
- **O-44** — any trade-driven FIFO/simplified-matching boundary shift strands pre-shift position rows as permanent orphans (15,448 across the Pool-C population, 1.5% of live positions, 392/3,234 traders affected); store_positions() has no deletion path for superseded rows. Report-only.

None of O-41–O-44 are fixed this session. All four are independent of each other and of B1b's own logic — found *by* B1b's validation work, not caused by it.

---

## Also

- Morning snapshot (services, daily_maintenance 33/33 ALL OK, O-37 quarantine holding at 84 markets / 0 cohort exposure, harness 3 pre-existing REGRESSIONs / 0 CRITICAL, B4 capture, git) — full detail not duplicated here, see session transcript. One B4 finding: of the (small, since-drained) `failed_no_book` set, 3 markets fail persistently across multiple days (thin/longshot geo-election markets) alongside transient new ones each run.

---

## State For Next Session

- **B1b-positions DONE + validated + shipped.** Carry forward three documented limits into any B3-adjacent work that consumes it:
  1. **`trade_result`-availability-as-of-T is unrecoverable** — no `evaluated_at`/`updated_at` column exists on `trades`. B1b reconstructs trade *existence* as of T (via `timestamp <= T`), not evaluation *state* as of T. A trade whose result was written after some historical T but whose event-timestamp precedes T is indistinguishable, from current data, from one evaluated promptly. Same event-time/write-time class as O-33.
  2. **Deleted-duplicate-row windows are unreconstructable** — the weekly full-sync dedup (Sundays, gated, itself unreliable — only fired 3 of 8 Sundays in the log's ~7-week coverage) removes ~7,400 rows/week when it runs, with no record of which rows or which time window. No T-bound over the *current* trades table can recover what's been physically deleted. Bounds how far back exact reconstruction can go.
  3. **Synthetic-close `exit_timestamp` is a BOUND, not a precise close instant** — tape-end only certifies "this market had stopped trading by here." Sufficient for open/closed determination at any T (B1b's job); must not be used for holding-period/timing math that assumes an exact instant.
- **B1b-prices is next** — scope it fresh, not a roll-in from this session. B2's probe work (`scripts/b2_price_history_probe.py`, 98% token resolution / 100% CLOB retention / 30min granularity on resolved geo/elec) is the starting point, not yet wired into a `reconstruct_prices_at`-equivalent.
- Open/parallel, unchanged from 07-21: elections-calibration current-state re-run (O-40), O-36 (`resolution_date` generator investigation), O-18 (import investigation), O-38, O-39, B4 `failed_no_book` persistent-3 (now characterized, not yet acted on).
- Deferred unchanged: `is_taker` retire-or-wire, ELO unfreeze/Layer-2, O-41/O-42/O-43/O-44 (all report-only, none fixed), swarm items behind the experiment.

---

## Methodology Thread

Continues 07-21's through-line: validate against something proven-clean, not merely hoped-clean.

- T=now didn't match the live table on the first pass. Debugged to root rather than tuning the comparison to pass or assuming B1b was wrong — found three independent, real, pre-existing defects (O-42, O-43, O-44), none of them B1b's.
- The open/partial "sanity check" was itself wrong on the first pass (didn't account for collisions), understating how much divergence actually existed — caught before reporting a false "clean" result, generalized O-44's detection from a narrow threshold-crossing signature to the actual root mechanism once a second, differently-shaped example surfaced.
- Declined to generalize from one trader's clean open-position match to "opens are untouched by these bugs" — population-scale validation showed they aren't (just fully explained).
