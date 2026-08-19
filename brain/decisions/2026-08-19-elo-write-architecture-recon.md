# 2026-08-19 — ELO write architecture reconnaissance

Read-only. Nothing changed. Every claim tagged **[V]** (verified this
session — command/file:line given) or **[I]** (inferred, explicitly
marked). This is reconnaissance for the pending decision on wiring
`backfill_trade_results_geo.py` into `daily_maintenance.py`
(`2026-08-19-geo-backfill-wiring-prereg.md`, `9610f99`) — not itself a
decision or a fix.

**Several claims in this task's own framing were checked and found wrong
or imprecise — corrected below rather than propagated**, per the standing
"verify, don't propagate" rule that has now triggered on three consecutive
tasks in this arc.

---

## 1. The canonical formula

**[V] Exists, and is genuinely pure.** `analysis/comprehensive_elo_formula.py:65`,
`compute_comprehensive_elo(base, beh_mult, bonus, pnl_raw, closed, resolved,
w_beh, apply_soft_cap, apply_floor) -> EloResult`. Read the entire 145-line
file: no `import sqlite3`, no `conn`/`cursor` reference, no global mutation,
no I/O of any kind — it is a closed-form function over its scalar arguments,
returning a frozen `@dataclass EloResult`. `W_BEH = 0.0` is a module
constant (line 26), set 2026-07-12 per a cited behavioral-validation study
finding a well-powered null (R²=0.00018, n=21,218) — not hardcoded at call
sites, per its own docstring instruction.

This is specifically the **comprehensive_elo** formula. `geo_elo` (a
different column, different metric, different formula —
`scripts/update_geo_elo.py:139`, `_compute_geo_elo`) is **not** part of
this arc or this formula and should not be conflated with it — flagged
here since the two are easy to blur under "the ELO system."

---

## 2. The atomic write helper

**[V] Exists: `monitoring/database.py:30`, `write_elo_result(conn, address,
result, *, base_category_elo, behavioral_modifier, advanced_modifier,
kelly_alignment_score, patience_score, timing_score, elo_last_updated=None)`.**
Read the code, not the docstring, to establish what it actually does:

- It issues **one `UPDATE traders SET ... WHERE address = ?` statement**
  (lines 72-95) covering all 9 columns: `comprehensive_elo`,
  `base_category_elo`, `behavioral_modifier`, `advanced_modifier`,
  `pnl_modifier`, `kelly_alignment_score`, `patience_score`,
  `timing_score`, `elo_last_updated`.
- **What this guarantees:** for one trader, one call, all 9 columns come
  from the same computation, in the same statement — this is what makes
  a split write (some columns from Sunday, others from Monday — the
  RQ-CONTESTED-001 artifact class) impossible **for callers that use this
  helper**.
- **What this does NOT guarantee:**
  - **No transaction wrapping.** The function calls `conn.execute()` only
    — it does not `BEGIN`/`COMMIT`. The caller controls commit timing
    (both `apply_full_elo_modifiers.py` and `elo_bridge.py`'s canonical
    path batch-commit every N traders, not per-call).
  - **No cross-row atomicity.** Each trader gets a separate `execute()`
    call; a crash mid-loop updates some traders and not others — there is
    no all-or-nothing guarantee across a batch.
  - **No cross-table consistency.** Only `traders` is touched. Nothing
    ties this write to the state of `positions`, `trades`, or `pnl_cache`
    at the same instant.
  - **No enforcement that this is the only write path.** It is a
    convenience function, not a trigger, constraint, or gate. Nothing in
    SQLite or in the codebase prevents a different piece of code from
    issuing its own `UPDATE traders SET comprehensive_elo = ...` — see §4.
  - Decorated with `@retry_on_locked(max_retries=15, delay=2)` (line 29) —
    this is lock-contention handling, not a correctness guarantee.

---

## 3. Writers today

| # | Path | Canonical formula? | Atomic helper? | Currently invoked? |
|---|---|---|---|---|
| 1 | **Writer A** — `scripts/recalculate_comprehensive_elo.py` → `monitoring/elo_bridge.py:469` `full_elo_recalculation()` | **Yes** — `compute_comprehensive_elo` imported and called (`elo_bridge.py:589-632`) | **Yes** — `write_elo_result` (`elo_bridge.py:590,643`) | **Yes** — `polymarket-sunday-elo.timer` (systemd), weekly, `Sun *-*-* 03:00:00 UTC`, **enabled and active** [V]. Last run 2026-08-16 03:00→05:12:49, **31,232 updated, 0 failed** [V, `logs/sunday_elo.log`]. |
| 2 | **Writer B** — `scripts/apply_full_elo_modifiers.py` | **Yes** — imported directly (`apply_full_elo_modifiers.py:70`) | **Yes** — imported directly (line 71), used at line 276 | **Yes** — `daily_maintenance.py` step 24 (`"Apply full ELO modifiers"`, no `non_blocking` flag → **default False, BLOCKING**), runs every day [V]. |
| 3 | **Writer C** — `scripts/integrate_behavioral_elo.py` | n/a | n/a | **Deleted.** File does not exist [V, `ls` fails]. Confirmed via `git log`: commit `61adaf5`, "fix: Stage 0c — delete dead Writer C". Remaining hits for the name are comments/docs in other files, not live imports. |
| 4 | **Writer D** — `monitoring/elo_bridge.py:208` `_batch_store_elo_results` (reached via `_process_trader_chunk`, line 259, called from `quick_elo_update_for_traders`, line 330) | **No** — raw inline `UPDATE traders SET comprehensive_elo=?, base_category_elo=?, behavioral_modifier=?, advanced_modifier=?, pnl_modifier=?, elo_last_updated=?` (lines 242-249); does not call `compute_comprehensive_elo` | **No** — does not call `write_elo_result`; also **writes only 6 of the 9 columns** — `kelly_alignment_score`, `patience_score`, `timing_score` are never touched by this path | **No live call site found.** Its original entry point per `2026-06-29-comprehensive-elo-writer-map.md:140` (`monitoring/trader_analyzer.py:303`, fired every 15-min monitoring cycle) no longer exists — `monitoring/trader_analyzer.py` currently contains **zero** ELO-related code [V, full file read]. `quick_elo_update_for_traders` is now reachable only via `elo_bridge.py`'s own `--quick-update` CLI flag (nothing schedules that flag — absent from `crontab -l`, `daily_maintenance.py`, and every systemd unit checked) and from 5 files under `scripts/archive/` (test scripts, not live). **Code remains, live invocation does not** — see §5. |
| 5 | `scripts/update_geo_elo.py` | **N/A — different column, different formula** (`geo_elo`/`geo_elo_active`, not `comprehensive_elo`; own pure function `_compute_geo_elo`, line 139) | **No** — raw `UPDATE traders SET geo_elo=...` (line 291) and `UPDATE traders SET geo_elo_active=...` (line 326); correctly so, since `write_elo_result` has no parameter for these columns | **Yes** — `daily_maintenance.py` step 9, non-blocking, daily [V]. |
| 6 | `scripts/quarantine_o37_synthetic_markets.py` | No (writes `geo_elo`, lines 209/226, as a data-quality correction, not a regular recompute) | No | **Manual only** — absent from `daily_maintenance.py` and `crontab -l` [V]. |
| 7 | `scripts/archive/backfill_elo_ratings.py`, `scripts/simulation/calculate_elo_simple.py`, `scripts/archive/update_database_from_csvs.py` | No | No | **Dead/manual-only** — under `archive/` or `simulation/`; none appear in `daily_maintenance.py` or `crontab -l` [V]. |

**Corrections to project history made in building this table:**
- CLAUDE.md states *"Full 6-dimensional recalculation now runs automatically
  every Sunday via `daily_maintenance.py`."* **This is inaccurate as
  written.** `daily_maintenance.py`'s own code says otherwise, explicitly:
  `build_steps()`'s Sunday branch (`daily_maintenance.py:205-207`) comment
  reads *"Full ELO recalculation runs at 03:00 UTC via
  `polymarket-sunday-elo.timer` — `daily_maintenance` does NOT run
  `--full-recalc` — the timer owns it exclusively."* — confirmed by
  `main()` printing `"[WEEKLY] Sunday — full ELO recalculation handled by
  polymarket-sunday-elo.timer (03:00 UTC)"` (line 254) and running nothing
  else for it. Writer A runs via a **separate systemd timer**, before
  `daily_maintenance.py` even starts (03:00 vs. 06:00 UTC) — not "via"
  `daily_maintenance.py` in any sense.
- The task's own background claim ("TradeEvaluator's two callers in
  neither crontab nor maintenance") — checked in the prior task
  (`2026-08-19-geo-backfill-wiring-prereg.md`) — is also relevant here:
  `evaluate_new_trader_results.py` **is** wired (step 21); only
  `scripts/backfill_trade_results.py` is genuinely unwired.

---

## 4. Is adherence enforced or conventional — THE CENTRAL QUESTION

**[V] Convention-only. Not structurally enforced. Same shape of gap as
`backtest_window_sql` (`2026-08-16-canonical-infrastructure-recon.md`).**

The design doc that specified this arc
(`2026-07-06-elo-arc-design-FABLE.md`, §6, "DECISION 5 — Harness coverage")
names **9 invariants** to add to `audit_invariants.py`, and is explicit
that invariant #3 is the load-bearing one:

> *"#3 [T1] **Formula reproducibility**: for every flagged trader with
> complete components, `|comp − compute_comprehensive_elo(stored
> components)| < ε` — **The single-writer enforcement invariant.** Only
> possible because §4.1 writes all inputs atomically with the output. Any
> rogue writer, manual UPDATE, or formula drift trips it within one audit
> cycle. Gating from end of Stage 3."*

**This invariant was never implemented.** Read `scripts/audit_invariants.py`
in full: it has exactly 5 `comp_elo`-related checks (`check_comp_elo_range`,
`check_comp_elo_soft_cap`, `check_comp_elo_write_atomicity`,
`check_comp_elo_behavioral_materialization`, `check_comp_elo_population_drift`
— lines 570-772, all registered in `CHECKS` at the same 5 lines, 768-772).
None of them calls `compute_comprehensive_elo`; there is no `grep` hit for
that import or that function name anywhere in `audit_invariants.py`. The
specific check the design doc calls "the single-writer enforcement
invariant" does not exist.

The 5 checks that **were** implemented are all pinned at **tier 0**
(`"[0d/OBSERVE]"` in each check's returned name), and `determine_status()`
(`audit_invariants.py:779-786`) hardcodes: `if tier == 0: return "OBSERVE"`
— **unconditionally, regardless of count.** The design doc itself
describes this as deliberate: *"They gate NOTHING yet (status is always
OBSERVE regardless of count) ... Each is promoted to its target tier at
the migration stage named in its docstring"* (`audit_invariants.py:96-99`).
Invariant #3's target promotion point was "end of Stage 3." Stage 3
shipped (commit `4fc4523`) — the promotion did not happen, because the
check that would need promoting was never written.

**Direct answer: there is no test, assertion, or structural mechanism
that would fail if someone wrote an ELO column outside the canonical
path.** `write_elo_result` is a discipline tool that correct callers use
voluntarily. Writer D (§3, #4) is a live demonstration that a
non-canonical write path can exist in the same codebase, indefinitely,
with nothing flagging it — it simply isn't *currently invoked*, which is
a fact about scheduling, not about any enforcement mechanism.

---

## 5. Writer D — do remnants remain

**[V] Yes, the code remains; only the live trigger is gone.** Per §3 row 4:
`_batch_store_elo_results`, `_process_trader_chunk`, and
`quick_elo_update_for_traders` all still exist, unchanged, in
`monitoring/elo_bridge.py` (lines 208-467) — none were deleted, despite
Stage 5's explicit item: *"Retire Writer D remnants
(`quick_elo_update_for_traders`, `_process_trader_chunk`,
`_batch_store_elo_results`, `--quick-update` CLI)."* The `--quick-update`
CLI flag also still exists (`elo_bridge.py:812-826`). **None of the four
named items were retired.**

What has changed since the 2026-06-29 writer-map doc: the live call site
that used to fire Writer D every 15-minute monitoring cycle
(`monitoring/trader_analyzer.py:303` per that doc) is gone —
`trader_analyzer.py` today is a 115-line file with no ELO code at all
(full file read, confirmed). **No commit in git history is labeled as
this removal** (`git log --grep="Writer D"` across all branches: zero
hits) — the most recent touch to `trader_analyzer.py` is commit `ca30c07`,
"remove dead check_market_resolutions from monitor loop, offload
scan_for_successful_traders (O-13)," which is about a different,
already-closed issue (O-13, monitoring stall), not a documented ELO
cleanup. **[I]** This reads as Writer D's live trigger having been cut
incidentally, as a side effect of unrelated monitor-loop refactoring,
rather than as a deliberate Stage-5 action — inferred from the absence of
any commit or doc naming this removal, not proven.

---

## 6. Stage 5 status, per item

Per `2026-07-06-elo-arc-design-FABLE.md`, "Stage 5 — Cleanup and unfreeze"
names exactly three items:

| Item | Status | Evidence |
|---|---|---|
| Retire Writer D remnants | **NOT DONE** | §5 above — all 4 named artifacts still present in code. |
| One-time `elo_last_updated` backfill (23.5K non-canonical T-separated rows) | **NOT DONE** | **[V]** Live query: `SELECT COUNT(*) FROM traders WHERE elo_last_updated LIKE '%T%'` → **22,558** today. `audit_invariants.py`'s `FLOOR_TS_TRADER_ELO = 22560` was set 2026-07-14 as *"today's actual T-sep debt"*, with the comment predicting it would *"drop toward 0 as write_elo_result rewrites rows, hitting ~0 after Stage 5 backfill."* Over more than a month (07-14 → 08-19), the count has moved from 22,560 to 22,558 — a drop of **2**. No dedicated backfill script or step exists; the only mechanism is incidental natural rewrite (a trader happens to get touched by Writer A/B, which writes the canonical space-separated format going forward) — and at this rate it is not converging in any practically observable time. |
| Unfreeze `recalculate_comprehensive_elo.py` | **Functionally moot — it is running, and has been for some time** | §7 below. |

**Overall: 1 of 3 Stage 5 items resolved (by circumstance, not by an
executed Stage-5 pass); 2 of 3 empirically not done.** No commit or doc
anywhere in either repo's history claims Stage 5 was executed — consistent
with the task's framing that "Stage 5 was never confirmed complete," now
confirmed **empirically**, not just as an absence of confirmation.

---

## 7. Is the ELO recalc frozen

**[V] No — not in the sense of anything currently blocking execution.**
`recalculate_comprehensive_elo.py` (Writer A) is running successfully on
its systemd timer weekly (§3, row 1; last run 08-16, 31,232 traders
updated, 0 failed). There is no code-level freeze flag: `grep` for
"freeze"/"frozen"/"ELO_FROZEN" across all `.py` files found zero hits;
`config/elo_update_settings.json` has no freeze-related key (`auto_updates_enabled: true`
is the only relevant flag, and it governs the daily monitor's own
update-trigger thresholds, not this arc).

**What "frozen" meant, per the design doc that used the word:** the ELO
write path was, at design time (2026-07-06), a "frozen area" in the
project-management sense — a live production write path the design
doc's own author committed not to touch structurally except through the
staged Stage 0-5 process (*"Design constraints: live system, frozen area,
every step individually reversible, every step verified before the next,"*
line 245). Stage 5's *"Unfreeze `recalculate_comprehensive_elo.py`"* item
refers to lifting that **process-level caution**, not a runtime gate — its
own stated exit condition was *"Layer 2 done + harness clean."* Stage 2
and Stage 3 (both migrating writers onto the canonical formula + atomic
helper) **did ship** (commits `3371a1a`, `4fc4523`), and Writer A has been
running on the canonical path via the timer ever since — so in practical
terms the script was never runtime-blocked by this freeze; the freeze was
advisory ("don't restructure this without the staged process"), and the
restructuring that mattered (Stage 2/3) already happened.

**Nothing currently depends on it staying frozen** — there is no flag to
flip, and Writer A already runs unimpeded. The unresolved piece is
narrower than "unfreezing": Stage 4 (enabling `W_BEH > 0`, the one actual
formula change) was never flipped, and Stage 5's cleanup items (§6) were
never executed. Framing this as "still frozen" would overstate what
remains; framing it as "fully resolved" would understate it — reported as
both, precisely, rather than rounded either way.

---

## 8. The daily ELO path — actual current sequence

Confirmed directly against `scripts/daily_maintenance.py:32-81` (`STEPS`)
and today's `logs/daily_maintenance.log` (`[N/29]` labels matched 1:1) —
**not** from any doc, since the task correctly flags documented step lists
as stale.

**Before `daily_maintenance.py` even starts, on Sundays only:** 03:00 UTC,
`polymarket-sunday-elo.timer` → `run_sunday_elo.sh` → Writer A
(`recalculate_comprehensive_elo.py --skip-correlation --skip-contrarian
--skip-advanced-metrics`), typically finishing ~05:00-05:15 (last run:
2h12m). This is fully external to `daily_maintenance.py`.

**Within `daily_maintenance.py` (every day, 06:00 UTC start), ELO-relevant
steps in order:**

| step | label | reads/computes/writes | relative to gate/step 21 |
|---|---|---|---|
| 7 | Integrity audit (pre-ELO gate) | `audit_invariants.py --alert` — **reads** `comprehensive_elo`, `geo_elo`, and their component columns for the 5 OBSERVE checks (§4) plus the T1 `geo_elo` range/pool-sanity checks (which **do** gate); writes only its own report/alert, no `traders` columns | **THE GATE.** Everything ELO-writing below happens after this read. |
| 8 | Canonical definitions drift | `check_canonical_definitions.py` — checks for hardcoded ELO thresholds outside `column_definitions.py`; non-blocking; **currently failing daily** (confirmed in this session's earlier Task-A read, unrelated root cause not re-investigated here) | after gate |
| 9 | Update geo ELO scores | `update_geo_elo.py` — separate `geo_elo`/`geo_elo_active` writer (§3, row 5); non-blocking | after gate |
| 21 | Evaluate new trader results | `evaluate_new_trader_results.py` — writes `trades.trade_result` (won/lost) and recomputes `traders.resolved_trades_count` for `is_flagged=1` traders; **does not write any of the 9 canonical ELO columns itself**, but its output (`resolved_trades_count`) is a direct **input** to `compute_comprehensive_elo` | reference point named in the task |
| 22 | Reconcile geo resolved counts [post-eval] | settles `geo_resolved_trades_count` after step 21 | after step 21 |
| 24 | **Apply full ELO modifiers** | **Writer B** (§3, row 2) — reads `pnl_cache`/`positions`, `base_category_elo`, behavioral/advanced modifiers; computes via `compute_comprehensive_elo`; writes all 9 columns via `write_elo_result`. **BLOCKING** (no `non_blocking` flag) | 3 steps after step 21, 17 steps after the gate |
| 27 | Snapshot ELO scores | `snapshot_elo_scores.py` — reads current `comprehensive_elo` into a history/snapshot table; non-blocking, does not write `traders` | after Writer B |

**Net sequence relative to the two named reference points:** gate (7) →
… → evaluate_new_trader_results (21) → reconcile (22) → … → **Writer B
(24)** → … → snapshot (27). Writer B is the **last** writer of
`comprehensive_elo` on every weekday, and — per the writer-map doc's own
finding, still architecturally true today since neither Writer A nor
Writer B's formula-call sites have changed since Stage 3 — **also the last
writer on Sundays**, for any flagged trader with a closed position that
day: Writer A runs at 03:00, Writer B runs again at step 24 (~08:xx) and
overwrites `comprehensive_elo` for that population using the same
canonical formula but a different `resolved`/`pnl_raw` snapshot than
Writer A used 5 hours earlier.

---

## 9. Exposure to the proposed change

**[V] The new step (per the pre-registration, inserted as new step 22,
between "Evaluate new trader results" and "Reconcile geo resolved counts
[post-eval]") writes `trades.trade_result` and `traders.geo_resolved_trades_count`
— neither is one of the 9 canonical `comprehensive_elo` columns, and
neither goes through `compute_comprehensive_elo` or `write_elo_result`
(confirmed by reading `backfill_trade_results_geo.py` in full — it has its
own `evaluate_trade()`, structurally identical logic to `TradeEvaluator`
but not the same function, and its own raw `UPDATE trades`/`UPDATE
traders` statements).** No new direct ELO-column writer is being added.

**Indirect exposure, traced and measured rather than assumed:**

1. **`resolved_trades_count` (a real, if narrow, exposure).**
   `evaluate_new_trader_results.py` recomputes this column from scratch
   each run (`COUNT(DISTINCT market_id) WHERE trade_result IN ('won',
   'lost')`) for `is_flagged=1` traders — a full recompute, not
   incremental, so it will correctly pick up any trade the new step
   evaluates, **regardless of which script did the evaluating**, on its
   *next* run (the following day's step 21). This column feeds
   `compute_comprehensive_elo`'s `resolved` parameter directly — the soft
   cap (`1500 + resolved*150`) and the thin-sample gate (`resolved < 10`)
   both key off it. Clearing the stuck backlog will raise
   `resolved_trades_count` for some flagged traders, which can raise their
   soft cap and/or clear their thin-sample gate on Writer B's/Writer A's
   next run.

2. **`pnl_raw`/`closed` inputs (checked empirically — smaller exposure
   than assumed at first pass).** `compute_comprehensive_elo`'s P&L inputs
   come from `UnifiedELOSystem._load_pnl_data()`, which reads
   `positions WHERE status = 'closed'` (`unified_elo_system.py:3685-3697`)
   — **not** from `trades.trade_result` directly. Positions close via
   either a real SELL match or `position_tracker.py`'s
   `apply_synthetic_closes()` (line 366), which determines win/loss by
   comparing `position.outcome` against `market.winning_outcome`
   **directly** — it does not reference `trades.trade_result` at all.
   **Queried the actual overlap**: of the positions tied to the
   stuck-pending entry trades in the geo/elections invariant population,
   **11,644 (99.3%) already have `status='closed'`**; only 56 are `open`
   and 24 `partially_closed`. **This means the `pnl_cache`/`compute_comprehensive_elo`
   pathway is already counting the large majority of these positions
   today, independent of whether the stuck `trade_result='pending'` ever
   gets cleared** — the exposure here is much smaller than a naive read of
   "24,707 stuck trades" would suggest, confined in practice to the 56+24
   not-yet-closed positions, and even those close via a mechanism
   (`apply_synthetic_closes`) that does not depend on the new step running
   at all.

3. **`geo_resolved_trades_count`** feeds `geo_elo` eligibility — a
   different formula, different column, not part of `compute_comprehensive_elo`'s
   input set (§1). Real effect on `geo_elo`, not on `comprehensive_elo`.

**Given §4's finding:** none of this exposure is *newly risky* in the
sense of introducing a fresh gap — the lack of structural enforcement on
the canonical ELO write path is pre-existing and applies identically
whether or not this change ships. What this change does is make
`resolved_trades_count` (a genuine, unenforced input to an unenforced
formula) move for a population of traders whose closed-position count was
previously frozen mid-backlog. **No judgment offered on whether this
argues for or against proceeding** — that is out of scope for this
reconnaissance, per the task's instruction.

---

## Summary table for quick reference

| Question | Answer |
|---|---|
| Canonical formula exists & pure? | Yes — `analysis/comprehensive_elo_formula.py:65`, verified pure by full read |
| Atomic helper exists? | Yes — `monitoring/database.py:30`; guarantees single-statement 9-column write per trader, nothing more |
| Enforced or convention? | **Convention-only** — the one designed enforcement invariant (#3) was never implemented; the 5 that were are hardcoded to never gate |
| Writer C | Deleted (commit `61adaf5`), confirmed gone |
| Writer D | Code remains, live trigger gone (untracked in git history), none of Stage 5's 4 named retirement items done |
| Stage 5 | 1 of 3 items resolved (by circumstance), 2 of 3 empirically not done |
| Frozen? | No runtime block found; "freeze" was process-level caution, already superseded by Stage 2/3 shipping |
| Daily sequence | gate(7) → …→ eval(21) → reconcile(22) → … → Writer B(24, blocking) → … → snapshot(27); Writer A is external (systemd timer, 03:00 Sunday, before daily_maintenance starts) |
| Exposure to proposed change | No new direct ELO-column writer; narrow real exposure via `resolved_trades_count`; `pnl_raw`/`closed` exposure much smaller than assumed — 99.3% of affected positions already closed independent of `trade_result` |

---

*Generated 2026-08-19. Sources: `analysis/comprehensive_elo_formula.py`,
`monitoring/database.py`, `monitoring/elo_bridge.py`,
`scripts/apply_full_elo_modifiers.py`, `scripts/update_geo_elo.py`,
`scripts/daily_maintenance.py`, `scripts/audit_invariants.py`,
`monitoring/trader_analyzer.py`, `monitoring/position_tracker.py`,
`analysis/unified_elo_system.py`, `config/elo_update_settings.json`,
`crontab -l`, `systemctl list-timers`/`systemctl cat
polymarket-sunday-elo.timer`/`.service`, `logs/sunday_elo.log`, `git log`
(all branches, both repos), `2026-06-29-comprehensive-elo-writer-map.md`,
`2026-07-06-elo-arc-design-FABLE.md`, live DB queries against
`data/polymarket_tracker.db` (T-separated `elo_last_updated` count,
`positions.status` breakdown for the stuck-pending population). No code
changed, no script executed beyond read-only queries.*
