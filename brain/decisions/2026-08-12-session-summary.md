# 2026-08-12 Session Summary

## Theme

Three parts: an overnight/system-health check (order-book capture had stalled ~2 days — recovered on its own before this session started), a full-window run of Definition A (the frozen-spec cohort-consensus backtest) that produced a stop-the-project-as-conceived finding by mid-morning, and a same-day hardening retest that retracted it. The retraction has its own record — `2026-08-12-rung-a-retraction.md` — this summary covers the system-health findings and the methodology critique, and points at that record rather than repeating it.

---

## Part 1 — Overnight/system-health check

**Manual maintenance re-run** (PID 6699, launched ~22:10 on 08-11 to recover from the order-book stall): completed cleanly, `MAINTENANCE COMPLETE — FAILURES: 32/33 OK — FAILED: Run test suite`, 13694.1s (~3h48m), finished 2026-08-12T01:58:49Z. Only the test-suite step failed (see below — pre-existing, not new).

**Order-book capture — the item that mattered:** `snapshot_order_books.py` fired during the manual re-run (~01:3x–01:5x UTC, 268 rows) and again during the regular 06:00 run (~09:0x–09:29, 257 rows). Most recent row at check time: 2026-08-12T09:29:46Z. The 08-11 gap is real (zero rows all day, confirming the ~2-day stall) but resolved itself via the manual re-run — no further manual trigger was needed by the time this session ran.

**Today's 06:00 scheduled maintenance did not collide with the manual re-run** — the manual run had already finished over 4 hours before 06:00:01Z started. (The log briefly reads as if two runs overlapped; that's a stdout-buffering artifact — `daily_maintenance.py`'s own step-header prints get flushed as one block at process exit while subprocess output streams in real time — not an actual concurrent invocation. Confirmed via wall-clock cross-check, not assumed.)

**New reboot found:** 2026-08-11 18:26:58 UTC, same kernel version — consistent with an unattended-upgrades package update, not a crash. Both services (`polymarket-monitoring`, `polymarket-observer`) auto-restarted cleanly 6 seconds after boot. Predates the manual maintenance re-run by ~3.5h; not the cause of the order-book stall, which started over a day earlier.

**`audit_invariants`:** 0 CRITICAL on both runs. 3 REGRESSIONS each, composition shifted: a new one appeared — `580 data_source not in canonical set`. Traced to exactly 402 `trades` + 178 `markets` rows carrying `data_source='gap_recovery_20260811'` (402+178=580) — our own gap-recovery write from 08-11, not corruption. `canonical_definitions.py`'s allowlist just hasn't been updated to include that label. One-line fix, not urgent, carried to next session's open items.

**`run_tests.py`:** 15 files, 1 failure — `test_backtest_window_population.py` (19/24 passed), small population drift (±2–6 markets) between the frozen snapshot and a live re-derivation. Pre-existing — same file has been the sole failure in every maintenance run back through 07-24, not a new regression.

**Gap-recovery trades confirmed intact:** all 402 `gap_recovery_20260811` trade rows present and unmodified, verified directly against the live table. (Also what's driving the new audit regression above — itself confirmation nothing was silently reverted by dedup/sync/reconcile steps overnight.)

---

## Part 2 — Morning Definition A run, and the retraction

Ran Definition A (§4.2 of the FABLE design) against the full 353-market holdout with filters on and off, and reconciled against the `2026-08-09` B3-scoping "9 signals/8 clusters" headline. Findings, in brief (full detail not repeated here):

- Filters-on (band + liquidity + gap enforced daily, strict): **4 signals / 4 clusters** on the full window — lower than 9, not flat as hypothesized going in.
- Filters-off: **20 signals / 19 clusters**.
- **The 9/8 figure could not be reproduced.** Checked the source decision record directly: 9/8 was explicitly *not* filtered (band/liquidity applied), so it should compare against the 20-signal filters-off count, and it doesn't match that either. The generating script no longer exists — it was a background-agent run, never committed to either repo. **A number that can't be reproduced isn't a measurement.** Whatever 9/8 was counting, it wasn't a spec-compliant signal count, and it should stop anchoring planning discussions as if it were a settled figure.
- The filters-off run then fed a check of *where* in the market's price history consensus first forms — the rung-A thesis test. That produced the "consensus forms late" finding, reported mid-morning, **retracted same evening**. Full writeup, root cause, corrected numbers (18/28 = 64.3% form in-band, median 58 days to resolution), and the two implementation bugs caught during the retest: **see `2026-08-12-rung-a-retraction.md`.**

---

## Methodology critique (from this session, worth carrying forward as process, not just content)

**(a) We validated the plumbing exhaustively and the premise barely at all.** PIT geo_elo, PIT positions, price_at, the frozen population snapshot, B5 clustering — all built, tested, and cross-validated at scale before today. Rung A — does the cohort's consensus even lead the market, the cheapest test on the whole list, requiring no new infrastructure — got sequenced last, after months of build work on everything else. If it had come first, either the underpowered-9/8 framing or today's whole detour might have looked different from the start.

**(b) The 9/8 baseline anchored weeks of framing and turned out not to be measuring what everyone assumed.** It drove the 2026-08-09 strategic reframe (Phase 2 promoted to primary) and every conversation since. It cannot be reproduced because the generating script was a background-agent run committed nowhere. Going forward: any number that's going to anchor a decision this size needs its generating code committed, not just its output quoted.

**(c) When signal was scarce, we kept resizing the test instead of asking whether scarcity itself was the finding.** LEGENDARY-only fell short → widen to NEAR_LEGENDARY → still short → Pool-C-top-N proposed and correctly rejected on 08-09 for changing the hypothesis. What didn't get asked directly until today: is the LEGENDARY cohort's consensus rare because our filters are too strict, or because genuine multi-trader agreement on a contested market is just an intrinsically rare event? Today's retest suggests the latter isn't the failure mode — 64% of the (still small) set of formations that do occur happen in-band — but the instinct to widen the cohort before checking the cohort's timing was itself worth naming.

---

## State for next session — Oscar's framing: get everything in order before paper trading commences, no rush

Open items, roughly in order:

1. **The volume/power question** (~9–25 vs. 60–120 clusters) — now the sole blocker on whether Phase 2 is worth starting, and for how long. This is the reopened question from `2026-08-09-phase2-primary-and-paper-trading-preparation.md`, now sitting on corrected footing rather than the retracted rung-A framing.
2. **Re-run the detection-latency analysis against the 28 corrected timestamps** from today's retest — expected to defuse entirely given the 58-day median, but not yet confirmed against the actual latency-decay methodology.
3. **The low-side clustering asymmetry** — all 10 outside-band formations from today's corrected run sit below 0.10, none above 0.90. Unexplained, not investigated (out of scope once the verdict came back BREAKS). Worth a look.
4. **Ingestion detection** — no alert exists today for "our DB is missing trades the API has." The 08-11 order-book stall was found by luck (this session's overnight check), not by monitoring. Mandatory before a months-long passive Phase 2 run.
5. **B7 build items** — `paper_trades` table + scorer, `tx_hash` idempotency, per-signal capture (fee fields, timing chain, exits via `detect_counter_signals.py`), group-sequential pre-registration, spec freeze + config hash.
6. **Carried from prior sessions:** O-49 gap-flagging (still awaiting backfill convergence), the canonical-allowlist fix for `gap_recovery_20260811` (see Part 1), elections fee-classification calibration re-run, O-38, O-18.
