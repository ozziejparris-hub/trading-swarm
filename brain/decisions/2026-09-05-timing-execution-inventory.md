# Timing, Speed & Execution-Quality Inventory

**READ-ONLY.** Nothing built, changed, or proposed here. This inventories
what exists against the Gómez-Cram, Guo, Jensen & Kung (SSRN 6617059) and
Della Vedova (SSRN 6191618) findings, and traces the history of every
timing/execution mechanism found. Tags: **[V]** verified this session
(query/code/doc cited), **[I]** inferred or a judgment call.

Corrections to this task's own framing, checked before reporting: the
prompt's "3,509 OOS positions" figure is **stale** — the verified count
from this session's own committed Track 2 diagnostic
(`data/characterizations/track2_ci_power_20260905T104945Z.json`, first-repo
`7aaf8d9`) is **3,795** cohort positions / 141 surviving traders (169
presplit-qualifying before the OOS-survival filter). The prompt's "three
known readers" of `is_taker`/`transaction_hash` also does not hold —
see §1.2. Both are used below, corrected.

---

## PART 1 — INVENTORY

### 1.1 `timing_score`, `patience_score`, `kelly_alignment_score` (traders columns)

**What they compute, from what inputs** (`analysis/trading_behavior_analysis.py`):

- **`kelly_alignment_score`** (lines 275-368): per trade, `actual_size = shares*price/1000` (assumes a flat **$1000 bankroll**, not the trader's real one) vs. a Kelly-optimal fraction derived from the trader's **single, static, whole-history `win_rate`** (not per-trade edge). Score = `1/(1+|avg_kelly_ratio − 1|)`.
- **`patience_score`** (~line 422): `min(avg_gap_hours_between_trades / 168, 1.0)` — a trading-frequency-discipline proxy, nothing to do with entry timing within a market.
- **`timing_score`** / cache key `optimal_timing_score` (lines 443-605, `calculate_timing_quality`): **relative entry percentile** among all traders who ever entered the same market — earliest entrant scores 1.0, latest 0.0, `0.5` fallback when fewer than 3 total entrants exist in that market. Docstring calls this a "PERMANENT ENHANCEMENT... works without `created_at` column."

**What reads them / write path**: cached 24h in-process (`UnifiedEloSystem._load_behavioral_data`, `analysis/unified_elo_system.py:682`), written every Sunday full-recalc (Writer A, `monitoring/elo_bridge.py:618-651`) and by `scripts/apply_full_elo_modifiers.py:281-283`, via `monitoring/database.py`'s atomic `write_elo_result`. They feed `calculate_behavioral_elo_bonus` (`unified_elo_system.py:822-929`, adaptive-weighted kelly=40/patience=30/timing=30, ±100-point bonus) — **but neither current writer calls that function**: both pass `bonus=0.0` directly (`elo_bridge.py:627`, `apply_full_elo_modifiers.py:20-25`), because the bonus (and the separate `behavioral_modifier` composite — `consistency×diversification×trading_style×activity`, which does **not** include kelly/patience/timing at all) are both gated by `W_BEH` (`analysis/comprehensive_elo_formula.py:26`), fixed at **`W_BEH = 0.0`** since 2026-07-12 (Stage 0b — §2 below).

**Verdict: LIVE (write path) / DORMANT (scoring effect).** Recomputed and written to `traders` every week; contributes **zero** to `comprehensive_elo` today.

**A live stale-instructions finding**: CLAUDE.md's "Important Warnings" §3 states "Timing quality is intentionally disabled — the `created_at` column doesn't exist... all traders receive a neutral timing score." The underlying fact is still true — [V] the `markets` schema has no `created_at`/`start_date`/`listed_at` column, only `end_date`, `resolution_date`, `resolution_recorded_at`, `last_checked` — but the **conclusion is stale**: the relative-percentile method (live since 2026-01-16, commit `5b6efcd`) was built specifically to route around that absence and does **not** give all traders a neutral score — only those in markets with <3 total entrants fall back to 0.5. Zero effect on ELO today is real, but for a different, later reason (`W_BEH=0`, unrelated to `created_at`).

### 1.2 `is_taker` and `transaction_hash` (trades columns)

**Four writers, not the task's implied structure:**
- `monitoring/monitor.py:873,927` — captures `transaction_hash` free, at live ingestion (commit `95934bd`, "enables dedup and future maker/taker detection").
- `scripts/backfill_transaction_hashes.py` — retroactive `transaction_hash` backfill, **only** `--tier legendary` (`geo_elo_active>=2175`) or `--tier pool_c` (`geo_accuracy_pool=1`); `daily_maintenance.py` only ever runs `--tier pool_c`.
- `scripts/polygon_maker_taker.py:235` — writes `is_taker` by decoding Polygon RPC `OrderFilled` event-log topic position; requires `transaction_hash` already set. This is the step currently mid-run in today's `daily_maintenance.py` (RPC timeouts observed live).
- `scripts/polygon_event_scanner.py:381,425-427` — a fourth, independent writer of **both** columns via a different (event-scanner) code path; not in `daily_maintenance.py`'s STEPS list, invocation cadence undetermined.

**Coverage** [V, live queries]:

| population | trades | `is_taker` covered | `transaction_hash` covered |
|---|---|---|---|
| all trades | 13,607,590 | 621,350 (4.57%) | 2,506,957 (18.42%) |
| Geopolitics+Elections | 2,390,924 | 113,009 (4.73%) | 486,205 (20.34%) |
| Track 2 true cohort (169 traders) | 133,418 | 23,020 (17.25%) | 90,246 (67.64%) |

Cohort coverage is elevated only because 158/169 Track2 cohort traders happen to also sit in Pool C — an incidental overlap of two independently-defined populations, not designed.

**A critical distributional finding, not just a coverage gap** [V, database-wide]: `SELECT is_taker, COUNT(*) FROM trades GROUP BY is_taker` returns **only two rows: NULL (12,986,240) and 1/True (621,350). Zero rows anywhere in the database have `is_taker = 0`.** The column has never recorded a single maker-side trade. See §4.

**"Three known readers" — does not hold.** [V] Exhaustive grep of both repos for non-write references found **zero downstream consumers**. Every read is a self-diagnostic print inside the writer script itself (`polygon_maker_taker.py:254-280`, `backfill_transaction_hashes.py:252-285`, `polygon_event_scanner.py:561-610` — each prints its own tier's maker/taker counts as a QA check on its own progress). No ELO module, no bot-detection script, no research script reads either column today.

**Verdict: LIVE (writers actively running) / DORMANT (as a research signal)** — nothing outside the writers themselves consumes it.

### 1.3 `tape_end` / `tape_start` / market temporal anchors

`tape_end` — **LIVE, reusable, persisted-pattern**: `build_tape_end_map` (`scripts/trader_skill_metric_v2d.py:268-273`), `MAX(timestamp)` per market from `trades`, used across the v2d/v2f metric scripts (Track 2's own diagnostic reused it via `build_presplit_cohort`).

`tape_start` — **does not exist** as a reusable concept [V, full schema + repo search]. The only occurrence anywhere is a locally-scoped ad hoc helper, `scripts/discovery_gap_sizing.py:74-78` (`MIN(t.timestamp)` per market), part of the unrelated discovery-gap-sizing lineage — not persisted, not reused by the ELO/metric pipeline.

**No market-open/listing timestamp exists anywhere** [V, full `markets` schema]. Only `end_date`, `resolution_date`, `resolution_recorded_at`, `last_checked`. Consequence: a position's entry can only be timed against (a) other traders' entries in the same market (what `timing_score` uses) or (b) `resolution_date`/`end_date` — entry-to-resolution lag, the Della Vedova framing directly. **Nothing in the ELO/edge pipeline computes (b)** — it exists only as `detect_insider_activity.py:259`'s `s4_days_before_resolution` signal, entirely outside the ELO/edge pipeline (§1.6).

### 1.4 B4 order-book snapshots (`scripts/snapshot_order_books.py`, table `order_book_snapshots`)

**Purpose, per its own docstring**: captures CLOB depth for **STR-002/STR-003 signal markets** specifically — "Phase 6 paper trading fill simulator needs real historical book data." Not a general market-population capture, and not connected to the ELO/Track2 research cohort except by incidental overlap.

**Schema**: `market_id, snapshot_ts, signal_id, snapshot_type, direction, token_id, bids_json, asks_json, mid_price, spread, bid_depth_10, ask_depth_10, clob_market_price_yes`, PK `(market_id, snapshot_ts, direction)`.

**Coverage** [V]: 5,000 rows, 432 distinct markets — **3.57% of the 12,097 Geopolitics+Elections markets**, ~0% of all 838,006 markets. Range 2026-06-12 → 2026-09-05, 63/85 elapsed calendar days with ≥1 snapshot. Only 4 distinct `signal_id` values across all 5,000 rows (98.5% `signal_id IS NULL`).

**Gaps — the documented one is real but not the one the task implies, and it is not the only one** [V]: the ~14-day gap (07-24→08-08, ~15 days measured) is a **server-shutdown event** (`~/trading-swarm/brain/decisions/2026-07-24-shutdown-state-of-play.md` / `shutdown-safety.md`, "~14 days of forward order-book calibration data permanently lost") — **not** the April 2026 monitoring-outage `trade_gap_flag` window. Additional, previously-unnamed gaps found: 5-day (06-18→06-23) and three 2-day gaps (06-27→06-29, 06-30→07-02, 07-11→07-13, 08-10→08-12, 08-21→08-23). Also a known bug (O-38, same doc): 62-63 signal-linked rows carry a bid/ask sort-order defect, deliberately left unpatched — any read of historical `mid_price`/`spread` must filter these rows.

**B4 has been used at least once already**: `trader_skill_metric_v2f.py`'s cost-floor spread assumption (`SPREAD_LO, SPREAD_HI = 0.001, 0.02`) cites "per B4's captured range" as its source — so B4 informed one assumed constant, though not as a per-position benchmark.

**Verdict: LIVE** (still capturing as of 2026-09-05) but **narrow-scope and disjoint from the research cohort** — unusable as a general fair-price benchmark at current coverage (3.57% of the relevant category).

### 1.5 `detect_insider_activity.py`

**LIVE**: called from `monitoring/system_observer.py._insider_detection_loop` (lines 3221-3401), launched as an asyncio task at observer startup (line 147), 15-min cycle (`CHECK_INTERVAL=900`), 2-hour lookback. Detects (a) **individual**: fresh wallet (<90d) + position >$2,000 + Geopolitics market + ≤2 markets total + low-odds (<0.35) OR high-conviction late-stage (≥0.75, ≥$10-50K); (b) **cluster**: 3+ fresh wallets, same outcome/market, within 6h, combined ≥$50K. Both scored by a five-signal "Mitts/Ofir composite" (lines 155-277): cross-sectional bet size, within-trader bet-size anomaly, price contrarianism, **pre-resolution timing** (signal 4 — `days_before ≤1 → 1.0` suspicion, `>30 → 0.0`), market concentration.

**A polarity note for the Della Vedova comparison**: this signal treats *late* entry (close to resolution) as the insider marker — the **opposite** polarity from Della Vedova's finding that bot/systematic execution advantage comes from *early* entry (>8 days out). Not a contradiction — different populations (single-event insiders vs. systematic bots) — but worth flagging as a tension if this is ever cited as a project "timing mechanism" in the same breath as Della Vedova.

**History**: only **7** `insider_signals` rows ever existed (2026-03-04 → 2026-05-02), 1 cluster ever (the "Feb 28 Iran strike" pattern the code repeatedly names). Of the 7, 4 have been scored against actual resolution outcomes — all 4 correct (n=4, thin). Nothing recorded in the last 4 months. Built via `ac82eb8` "Comprehensive insider detection" plus 8 iteration commits (threshold relaxation, noise filters, the Mitts/Ofir composite `14b9b8b`, outcome scoring `677f677`, cluster tightening `14ea5aa`, calibration `836a0ef`, wallet-age fix `eb06281`) — active, documented development.

**Runtime-firing verification: COULD NOT DETERMINE this session** [I — access gap, not a finding]. `sudo journalctl -u polymarket-observer` requires an interactive password in this environment; every attempt failed silently (grep then reports "0" against empty/failed input, which is **not** the same as a confirmed-zero log search — this was checked and the distinction matters, per §2c's M6 lesson). The call site exists and the observer process is alive (PID 1222, since Sep 02), but whether the loop is still actually firing and finding nothing (consistent with the 4-month signal drought) vs. silently broken could not be confirmed here. Flagged explicitly rather than asserted either way.

### 1.6 `resolution_sweep.py` / Channel 2 "single-event insider"

**LIVE**, in `daily_maintenance.py`'s STEPS (non-blocking). **Not itself a timing/execution metric** — a **population-discovery** mechanism: sweeps any trader with ≥$500 position volume in a just-resolved Geopolitics/Elections/Politics/Ukraine-Russia market into the monitored pool, with no minimum trade count and no minimum market count, specifically to catch single-event insiders who would never qualify via leaderboard discovery (which requires 3+ markets) — the "Magamyman archetype." It feeds population into the ELO/insider-detection systems; it does not score timing itself. Origin: `brain/agent-outputs/backtest-agent/2026-05-21-LH-001-lifecycle-heuristic.json` — this **is** Oscar's earlier finding (§2b).

### 1.7 Other timing-adjacent mechanisms found

- **`analysis/copy_trade_detector.py`** — `avg_reaction_time` (lines 438, 658): lag between a "leader" trade and a "follower" copying it, for **copy-bot/leader-follower exclusion** from ELO, not skill/execution scoring. LIVE (`unified_elo_system.py:41,1573`, `analysis_scheduler.py:534-536`).
- **`scripts/archive/bot_detection.py:20`** — one-line comment, "Edge is latency-based. Excluded from signals." **ARCHIVED/DEAD** — documents that a latency-based edge concept was recognized and deliberately excluded at some point; no further detail survives in that file.
- **`scripts/simulation/seed_production_data.py`**'s `reaction_time_hours` — synthetic-trader generation for simulations only, not a production signal.

---

## PART 2 — HISTORY

### 2a. What prompted the timing/patience/kelly mechanisms?

Born **2026-01-14** (`a13da71`, "Simulation informed improvements") — i.e. out of a **synthetic-trader simulation project**, not real-outcome analysis. The relative-percentile timing method followed two days later, **2026-01-16** (`5b6efcd`, "Behavior finishing touches"), which added `TIMING_QUALITY_ENHANCEMENT.md`. That doc's own stated premise — quoting its actual claim — is **asserted, not empirically tested at build time**: "Absolute market age doesn't predict trader skill. Relative entry timing DOES (early adopters have information edge)." No outcome-correlation check accompanies this; the doc only reports coverage/distribution stats (976 traders, 98.8% coverage, avg score 0.511). **This directly answers Part 2d: `timing_score` was built on an assumption never tested against outcomes at build time**, and — per the Stage 0b study below — was only tested once, five months later, and never re-tested since despite that test flagging exactly the kind of data-quality problem that would need fixing first.

The schema migration that formally added these columns (`scripts/archive/update_database_schema.py`) was itself archived in `1e4d96b` (2026-06-05, "audit cleanup — archive orphaned scripts, drop vestigial columns, disable unused behavioral modifier") — a **documented** cleanup, separate from and predating the Stage 0b decision.

### 2b. Oscar's prior similar finding — confirmed

`brain/agent-outputs/backtest-agent/2026-05-21-LH-001-lifecycle-heuristic.json`, "LH-001 Lifecycle Heuristic — Single-Event Geopolitics Insider Detection." Tested whether entering at the right moment around a specific real-world event (the Nikki Haley VP-candidate market; an Iran-strike market) predicted anomalous PnL vs. matched controls. **Verdict: `conditional_pass`.** Pooled signal significant (p=0.016, rank-biserial r=0.208; candidate median PnL $606K vs. control $220K, n=59 clean candidates vs. 90 controls after bot exclusion) — **but neither event was independently significant** (Haley p=0.109, Iran p=0.482), and an earlier v1 result claiming p=0.0000 was traced to a market-scale confound, not reproducible. Power analysis: only 2 events studied, 7 needed minimum for cross-event generalization — verdict explicitly **"INSUFFICIENT."**

What got built as a result, per the doc's own recommendation, quoted: **"Deploy as watchlist trigger only via existing `insider_signals` infrastructure. Do NOT build parallel system."** This is why `detect_insider_activity.py`/`resolution_sweep.py` exist in their current form rather than as a separate "lifecycle heuristic" system — the finding was folded into the existing channel, not spun out into something new.

### 2c. The M6 precedent — full story

`brain/decisions/2026-08-31-geo-scoping-inventory.md` catalogued `monitor.py._ai_categorization_check` (a local-Mistral market-categorization check) as **"M6 — LIVE (hybrid mode)"**, inferred from the module constant `AI_FILTER_MODE = "hybrid"`. `2026-08-31-local-llm-consolidation-assessment.md` (commit `7099743`) corrected this: production runs `start_monitoring.py → main_telegram_safe`, which constructs the monitor with **`ai_agent=None` hardcoded** — the guard on `self.ai_agent` always fails, so `_ai_categorization_check` is **never called**, verified by zero `[AI PATH]` log lines across three months of journald and every restart banner reading `TELEGRAM-SAFE`, never "AI Agent: Enabled."

**The exact lesson, applied throughout this inventory**: a config constant matching a code branch's guard condition is not evidence the branch executes — only runtime log/counter evidence proves invocation. This standard is why `detect_insider_activity.py`'s LIVE verdict above is qualified rather than asserted outright (§1.5) — its call site and process-alive status are confirmed, but its actual recent firing could not be journal-verified this session, and that gap is reported honestly rather than resolved by assumption in either direction.

### 2d. Documented abandonment vs. silent drift

Everything found in this inventory that is DORMANT or DEAD was **documented**, not silent: M6 (corrected in a dated decision doc), the pre-Stage-0b `integrate_behavioral_elo.py`/Writer C (disabled 2026-06-05 per `1e4d96b`, deleted entirely in "Stage 0c" per commit `61adaf5`), the LH-001 heuristic (explicitly marked `conditional_pass`/`INSUFFICIENT`, folded into existing infrastructure per its own recommendation, not silently dropped), and the archived `bot_detection.py` latency-exclusion comment (a one-line documented exclusion, not drift). No case was found in this scope of a mechanism that simply stopped being called with zero record of why. The one open exception is `detect_insider_activity.py`'s current firing status (§1.5/§2c) — not documented drift, but a genuine access-limited unknown in this session.

### 2e. Was any timing signal ever validated against outcomes?

**Yes, once**: the Stage 0b behavioral validation study (`brain/decisions/2026-07-12-behavioral-validation-study-STAGE-0B.md`, n=21,218, well-powered — detects effects as small as R²=0.00018). Decomposition test (§3.2 of that doc): `kelly_alignment_score` tiny-positive (β=0.0164, p=0.015), `patience_score` null (β=−0.0035, p=0.613), **`timing_score` the largest and most significant of the three** (β=0.0210, p<0.001) — but the study's own authors explicitly distrusted this result: ~1,541 traders (7%) sat at exactly 0.5 (a neutral-default signature mixed with pre-disablement computation as of that date), and the study recommended re-deriving `timing_score` "from scratch on a repaired `created_at`-equivalent input" before treating the coefficient as evidence. **That re-derivation has never happened.** Net: the one internal timing signal that empirically looked most like it might carry real information has never been cleanly re-tested on clean data — a genuinely open question, not a closed null.

---

## PART 3 — FITNESS FOR THE TWO METHODS

### 3a. The Della Vedova decomposition

**Needs, per position**: side, entry price, outcome, and an independent fair-price benchmark at entry (not the trader's own achieved price, and not conventional VWAP, which the paper itself says conflates the two things it separates).

**What exists, for the verified 3,795 true-cohort OOS positions** (correcting the task's stale "3,509" figure):
- **Side**: `positions.outcome` / `trades.side` — 100% coverage [V, 0 nulls across 2,390,924 Geo/Elec trades].
- **Entry price**: `entry_avg_price` — 100% (NOT NULL column).
- **Outcome**: via `trade_result` join — 100% for resolved positions (definitionally, since the cohort query requires `trade_result IN ('won','lost')`).
- **Independent fair-price benchmark distinct from the trader's own achieved price**: **does not exist at usable coverage.** `entry_avg_price` is what the trader paid, not an independent mid-price/fair-value at that instant. The only candidate that could supply one — B4 order-book mid-price/spread — covers 3.57% of Geopolitics+Elections markets, is scoped to STR-002/STR-003 signal markets, and has essentially zero overlap with the Track2/ELO research cohort.

**Verdict: partially computable.** The directional-outcome half (side/price/outcome) is fully available; the execution-quality half — which specifically requires a fair-price benchmark independent of what the trader paid — is not, for lack of any such benchmark at meaningful coverage.

### 3b. The Gómez-Cram randomized-direction benchmark

**Needs**: each trader's actual trade sequence — market, timing, price, size — held fixed, direction randomized.

**What exists**: `trades` table has `side`, `price`, `shares`, `timestamp` at **100% coverage** [V, verified 0 nulls across 2,390,924 Geo/Elec rows] — full trade-level granularity is present. Bet size is not just schema-present but already actively used elsewhere: `kelly_alignment_score`'s `actual_size = shares*price/1000` computation (§1.1) confirms `shares`/`price` are a real, exercised field, not a dead column.

**Verdict: fully computable**, at ~100% coverage for the cohort's trade population — the mechanical requirement (hold trade attributes fixed, permute direction) is a straightforward extension of exactly the kind of resampling Track 2's own bootstrap already does at the pair level.

### 3c. Plainly

- **Gómez-Cram: FULLY COMPUTABLE** — all four required fields present at ~100% coverage at trade level.
- **Della Vedova: PARTIALLY COMPUTABLE** — side/entry-price/outcome at 100%; the one distinguishing requirement (an independent fair-price benchmark at entry, distinct from achieved price) is missing at any usable coverage. The specific missing field: a trade-time bid/ask mid-price or equivalent fair-value series, which only B4 supplies, at 3.57% coverage of the relevant market population and disjoint from the research cohort.
- Nothing is uncomputable in the strict sense; Della Vedova's core distinguishing input is the one genuinely missing piece.

---

## PART 4 — WHAT THE MAKER/TAKER SIGNAL COULD DO

### 4a. Actual coverage across the cohort's positions

17.25% of the Track 2 true cohort's 133,418 trades carry an `is_taker` label (155/169 cohort traders have at least one labeled trade; 14/169 have zero). Database-wide, 4.57% of all trades and 4.73% of Geopolitics+Elections trades are labeled.

### 4b. Per-trade or per-position?

**Per-trade only.** `is_taker` lives on the `trades` table, keyed to individual `trade_id`. A `position` can aggregate multiple BUY trades (`entry_trade_ids` is a JSON array); no position-level aggregation of maker/taker mix exists anywhere in either repo.

### 4c. Could it split the cohort today? — No, and coverage is not the binding constraint

**A distributional finding, verified database-wide, that supersedes the coverage question**: `SELECT is_taker, COUNT(*) FROM trades GROUP BY is_taker` returns exactly two groups — `NULL` (12,986,240 rows) and **`1`/True (621,350 rows). Zero rows anywhere in the entire database have `is_taker = 0`.** This holds within the Track 2 cohort's labeled trades too (23,020 labeled, all 23,020 are `is_taker=1`, none are `0`).

**The column currently functions as "confirmed-taker-or-unknown," not a true binary maker/taker split.** No liquidity-providing (maker) trade has ever been recorded by either writer (`polygon_maker_taker.py`, `polygon_event_scanner.py`) across the entire trade history. Whether this reflects a genuine population fact (this project's tracked traders never get filled as maker — implausible at this scale) or a methodological artifact in the extraction logic (e.g. only writing a value when the `OrderFilled` log topic positively identifies a taker match, leaving everything else `NULL` rather than explicitly `False`) is not determined here — no root-cause investigation was performed, per the read-only scope of this task. **Reported as a fact requiring attention before any liquidity-providing-vs-liquidity-taking split is attempted, not as something fixed or explained here.**

Given this, no maker/taker split of the cohort can be reported — there is no maker group to split against.

---

## What remains / could not be fully determined

- `polygon_event_scanner.py`'s invocation cadence/schedule (not in `daily_maintenance.py`'s STEPS list; unclear if cron'd elsewhere or run ad hoc).
- `order_book_snapshots`' `snapshot_type='registration'` rows' reliability vs. daily-cadence rows — not broken out separately.
- Whether `insider_signals`' 4-month silence (last row 2026-05-02) reflects the underlying pattern genuinely not recurring vs. a possible detection regression — could not confirm via journald (sudo access unavailable non-interactively in this session); the call site and process-alive status are the only evidence available here.
- Root cause of `is_taker`'s zero-maker-rows distribution (§4c) — not investigated, flagged for whoever picks this up next.
