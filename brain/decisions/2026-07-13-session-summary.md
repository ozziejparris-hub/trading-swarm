# Session Summary — 2026-07-13

**ELO Arc Stage 2 SHIPPED — the canonical formula and the atomic write helper are both live in the daily production path, proven output-neutral four independent ways. Plus Stage 0d and Stage 1 completed, and the O-20 gate fixed for real this time (third instance of the event-time/write-time trap).**

---

## 1. Overnight/health — first clean 24h since the outage

- Maintenance: **33/33 ALL OK** (new O-26 honest banner working as intended).
- Tests green: first-repo 116, swarm 124.
- **O-14's automount passed its first real test**: last night's 02:00 offsite backup succeeded, no alert fired.
- signals.json safe-write running clean: no `CorruptSignalsFileError`, `.bak` rolling correctly.

All of yesterday's fixes held under real overnight load.

---

## 2. O-33 — the O-20 gate fixed properly (third event-time/write-time trap)

The gate redefined on 07-12 filtered on trade **execution** timestamp, not local write-time. Consequence: a freshly-backfilled flagged trader's multi-year history instantly counted as "stale orphans" — the gate read **528**, driven entirely by 3 traders (2 backfilled that same day).

**Fix:** gate on `MAX(trade.timestamp, COALESCE(trader.backfill_attempted, trade.timestamp))` — age from when *we* received the data, not when the trade executed.

**Verified** it kept the real signal: the 2 same-day backfills correctly excluded; 1 genuine hit remains (a trade from 06-22 on a trader backfilled 05-19 — a real 3-week-old unmatched trade). Resampled 1,1,1 — gate **passing** (threshold 20).

**LESSON (O-33):** this is the third time (O-21 → the 07-12 O-20 redefinition → today). We wrote the rule down after O-21 — "gate on write-time, never event-time, because backfills legitimately write old event-times" — and violated it anyway, because the new context didn't *look* like a queue trigger. A principle in a ledger entry doesn't fire automatically; it must be a **checklist question at gate-design time**.

---

## 3. ELO arc — Stage 0d + Stage 1 complete

**0d:** 5 `comprehensive_elo` harness invariants added in OBSERVE mode (first-repo `434a6dd`). Baselines recorded: range 475–3,324 (passes), 16 traders exceed soft cap, 270 write-atomicity violations (non-NULL comp with NULL components), behavioral-materialization fails by design at W_beh=0.

**Stage 1:** `analysis/comprehensive_elo_formula.py` built as a pure function. 339,663 assertions green: golden tests (all 5 worked examples exact), property tests, and the **zero-diff equivalence test** — grid of 61,248 inputs, diff count **0** against an independent verbatim port of production Writer B. Live-data validation: 99.87% byte-identical across 25,635 real traders, all 33 mismatches traced (32 = write-timestamp drift, 2 explained).

Shadow table (`elo_shadow`) + delta report, both ways:
- At **Stage-2 settings** → 99.88% ~zero delta, tier counts move <1%, top-100 100% retained (empirical output-neutrality).
- At **Stage-3 settings** → tier counts −15.74%/−4.44%/0%, 11/100 leaderboard turnover, exactly 16 soft-cap traders (matching 0d's baseline — two independent measurements agreeing).

Both cutovers now previewed before either happens.

**O-34:** design doc's §2.2 was stale — the 07-06 correction pass updated §2.1/2.4/2.5/4.1/5 but missed §2.2, which still had pre-correction numbers in all 3 sub-points. Fixed + changelogged.

**LESSON:** a correction pass is itself a claim that can go stale — grep for **every** place a corrected number appears, not just the sections you remember.

---

## 4. Stage 2 SHIPPED (first-repo `3371a1a`, ledger `1ca061b`)

`apply_full_elo_modifiers.py` now uses `compute_comprehensive_elo(w_beh=0, apply_soft_cap=False, apply_floor=False)` + `write_elo_result()` (the atomic full-column-set write).

**Proven output-neutral four independent ways:** algebra → 61K-input zero-diff grid → 99.88% live match → byte-identical full-snapshot dry-run (all 157,527 traders, 0 diffs on every column; the only changes are the 2 intentional ones — `elo_last_updated` format + atomic component refresh).

**The dry-run caught a real bug:** `base_category_elo` differed on 27,597 rows — `write_elo_result()` was unconditionally rounding to 6dp, but the old code only rounds on the backfill branch. It was silently truncating precision on every preserve-path write. A looser epsilon check (diffs under ~1e-6) would likely have passed this silently — the zero-tolerance assertion is why it was caught.

**What this lands:** the canonical formula is in production (daily path); the atomic write helper makes the RQ-CONTESTED-001 bug class ("columns from different writers at different times") **structurally impossible**, not just fixed; and O-3's generator is fixed as a side effect (`elo_last_updated` now canonical — the timestamp debt stops growing).

Backup taken first (`markets_20260713_203618.db`, WAL-safe + integrity-verified per O-19).

---

## Next session — Stage-2 post-run checklist (run after the 06:00 cycle)

1. `comprehensive_elo` unchanged vs. the backup for a sample of addresses.
2. `elo_last_updated` now canonical (space-separated) for newly-written rows.
3. The 270 write-atomicity violations (0d baseline) dropping toward 0 as traders get rewritten.
4. Re-run `audit_invariants.py` — no unexplained OBSERVE-mode drift.

**Then:** Stage 3 (Writer A onto canonical + turn the bounds ON). This is where values actually move — but we already know exactly who and by how much (16 soft-cap traders, 11/100 leaderboard turnover) from Stage 1's delta report. No surprises expected.

---

## Also still open (Oscar's calls + consolidation backlog)

- **Tier-3 governance decision** — full-shell agents undercut every code guard we build; the biggest standing swarm risk.
- **`is_taker`/`transaction_hash` decision** — 2–3h of every maintenance run building a filter nothing reads; wire it in or reclaim the time.
- The swarm's respawn/verification build ("make the swarm real").
- **O-29** — the shared write/co-write keystone.
- **O-28** — remaining harness invariants.
- **research-scout dedup** — prerequisite to Oscar's research-content review.

---

*Session closed 2026-07-13. Both repos committed and pushed.*
