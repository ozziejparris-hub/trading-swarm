# MASTER HANDOVER — 2026-08-15

**Read this first.** This document supersedes `2026-07-18-MASTER-HANDOVER.md` and all
session summaries in between as the single entry point for a new Claude chat instance
picking up this project. It covers roughly a month of work and contains a finding that
**changes the project's north star.** It is a snapshot, not a living doc — if it's more
than a couple weeks old when you're reading it, cross-check `brain/decisions/` for
anything newer before trusting it blindly.

---

## 0. HOW TO START A NEW SESSION

1. Read this document, in full.
2. Read `brain/decisions/2026-08-15-skill-metric-rebuild.md` **before touching anything
   that consumes `geo_elo`.** This is not optional — see §1 below for why.
3. Read the most recent session summary (`brain/decisions/2026-08-*-session-summary.md`,
   sorted by date).
4. Check the three services: `polymarket-monitoring`, `polymarket-observer`,
   `trading-swarm.service` — `systemctl is-active` all three.
5. Check today's maintenance banner / daily_maintenance.py output for anything red.
6. Both repos are public: `ozziejparris-hub/first-repo` (data/execution layer) and
   `ozziejparris-hub/trading-swarm` (orchestration + brain, this repo).

---

## 1. NORTH STAR — REVISED (read this before anything else)

**The 07-18 handover's north star is NO LONGER VALID as stated.** It read: "track
skilled geopolitics traders via `geo_elo`, surface signals when LEGENDARY traders
(`geo_elo >= 2175`) express conviction." `geo_elo` has since been established as unfit
for purpose. If you are a fresh chat instance and only read one section of this
document, read this one — building anything on the old framing now means building on a
foundation that's been confirmed broken.

**The thesis itself is unchanged:** do skilled Polymarket traders predict outcomes
better than the market price? **What changed is the instrument** used to measure
"skilled."

### geo_elo's confirmed defects

1. **SIGN ERROR.** `_compute_geo_elo` computes `expected = 1.0 − price`, but `price`
   already equals P(the traded outcome wins) for **both** sides — empirically confirmed
   by pairing Yes/No trades within 60 seconds of each other on the same market and
   finding they sum to 1.000 ± 0.001. For No-side trades, the formula scores the trader
   against the probability of the outcome they bet *against*. The module's docstring
   embeds the *same* error the code has, which is why every prior code-vs-spec
   validation passed — the spec was wrong from the birth commit, not just the
   implementation.
2. **IMPROPER AS A SCORING RULE.** A zero-skill trader buying favoured No positions
   earns expected `2·price − 1 > 0` per trade — free rating for zero edge. Not exotic:
   ~71% of these markets resolve No and volume clusters on favourites, so LEGENDARY may
   have substantially selected for favourite-betting No traders rather than skill.
3. **SELL CONTAMINATION.** 35.7% of the qualifying population (88,927 rows) folded in
   under `trade_evaluator.py`'s inverted win-condition. There is no side filter anywhere
   in `_fetch_qualifying_trades`.
4. **DOUBLE-COUNTING.** 52.3% of (trader, market) pairs have more than one qualifying
   trade, accounting for 86.3% of all qualifying trades (median 2, max 642). The
   K-schedule was counting decision *fragments*, not decisions.
5. **UNCALIBRATED PARAMETERS.** K-schedule (32/24/16), start rating 1500, ratchet
   150/step, `MIN_TRADES=5`, decay half-life 180 days, and the tier ladder
   1000/1400/1800/2175 all have no calibration record. 2175/1800 were copied from a
   discredited `comprehensive_elo` system; 1000/1400 don't appear anywhere before the
   June 22 consolidation commit that claimed to lift values "exactly from source
   scripts" — verified inaccurate.

**Important:** the sign bug is NOT the dominant driver of rank disagreement
(corr(rank disagreement, No-fraction) = 0.088 position-weighted, 0.112 cap5). `geo_elo`
is several broken things, not one broken thing. No single fix restores it — this is why
the response was a rebuild, not a patch.

### The replacement (built this session, NOT yet in production)

**Mean market-relative edge per independent decision.**
`edge = (won ? 1 : 0) − entry_price_of_side_held`, with no conditional flip. One
observation per (trader, market, side) *position* from the positions FIFO aggregation —
not raw trades. Empirical-Bayes shrinkage toward the population mean. **cap5 weighting**
(each (trader, market) pair weighted `min(n_positions, 5)`) — the clean knee:
`sigma2_between` is exactly zero for market/log/sqrt/cap3 weighting and only turns on at
cap5. Two-way trader×market clustered bootstrap CIs, verified nominal coverage (5.56%
vs nominal 5%).

**Cohort definition (decided, not yet cut over):** significance-95 + M≥10 distinct
markets as the *definitional* rule; effect-size ≥0.02 as a *required secondary filter*
for "tradeable" vs merely "provably nonzero." Percentile explicitly **rejected** as
primary — a percentile cut always has a top 1% even under zero true skill variance, so
it can't distinguish skill from luck by construction.

**LEGENDARY overlap with the new metric's equivalent tier: 15/81 (18.5%).** The current
production tier has little in common with what a defensible metric calls the top tier.

Full derivation, all eight pre-registered passes (Layer 0 → v2f), and the audit trail:
`brain/decisions/2026-08-15-skill-metric-rebuild.md`.

---

## 2. THE THESIS RESULT — the headline for a new instance

**First trustworthy out-of-sample test of the thesis.**

`T_split = 2026-04-01`, chosen on volume/power grounds alone, before computing any
outcome (independently matches FABLE's own original train/validation boundary, set
months before this metric existed). Cohort defined PIT-correctly — only positions whose
markets had already *resolved* by `T_split` (via `tape_end`, not merely entered, which
would leak resolution information): **148 traders qualify** on information available at
the split; **120 survive** into the out-of-sample window.

**Result:** cohort mean edge **+0.0316**, CI **[−0.0088, +0.0710]**, n=3,032 positions.
Placebo (matched on position count / market breadth / activity period, NOT edge-selected):
**+0.0127**, CI [−0.0210, +0.0461].

**Verdict: NULL — the CI does not exclude zero.**

**But not flat-null.** Point estimate +3.2pp vs placebo +1.3pp — directionally larger,
in the direction the thesis predicts. With ~8pp of CI width, a genuine 2–4pt edge
(economically meaningful against the cost floors in §5) cannot be distinguished from
noise at this sample size. **Underpowered, in the direction the thesis predicts — not
evidence against it.** The placebo's own null confirms no structural artifact is
contaminating the comparison.

**What NOT to do next:** raising the effect-size bar, trying another weighting, or
re-cutting the split are all ways of searching the same data for a specification that
clears significance — exactly the garden-of-forking-paths failure this arc was built to
avoid. The honest resolution to "suggestive but underpowered" is **more out-of-sample
observations**, not more analyses of these ones.

---

## 3. PHASE 2 REFRAME

Phase 2 (forward paper trading) is now the **primary experiment**, not a follow-on. Its
purpose has changed: no longer "test a thesis we have no evidence for" but "accumulate
the out-of-sample observations needed to resolve a directionally-positive but
underpowered signal." It now has a validated measurement instrument to do that with.

**Backtest is not viable as the primary test.** Full-population, spec-compliant volume
measured at 2–3 signals / 1–3 clusters over 37.3 weeks — roughly **14–43 years** to the
design's 60-bet / 40-cluster target, ~5–6 years even with the NEAR_LEGENDARY fallback.
Note: this was measured on the **broken** `geo_elo` and should be re-derived on the new
metric before being treated as final — it may look different once the qualifying
population is redefined.

---

## 4. SYSTEM ARCHITECTURE (unchanged since 07-18, restated for completeness)

### Two repos, one server

- **`~/projects/first-repo`** — the data/execution layer. Monitoring services, the
  Polymarket trade/trader database, the ELO scoring system.
- **`~/trading-swarm`** — the multi-agent orchestration layer. `brain/` (findings,
  signals, decisions, strategy registry), the orchestrator, agent templates.
- **Server:** Minisforum UM890 Pro, Ubuntu 24.04. SSH alias `trading-swarm`
  (`192.168.1.54`, user `parison`). Both repos live on this one box, under the same
  user.
- **Live services — all three confirmed active as of this writing:**
  `polymarket-monitoring`, `polymarket-observer`, `trading-swarm.service`.

### Workflow

- **Chat-Claude** (you) — plans, architects, reviews.
- **CC (Claude Code)** — implements over SSH on the actual server; file edits, script
  runs, commits.
- **Fable** — brought in for big design/audit tasks. Look for `-FABLE.md` suffix on
  decision docs.

### Environment quirks — still true, unchanged

- `run_tests.py` is the canonical test runner (first-repo root) — bare `pytest`
  wrongly collects legacy files.
- Swarm tests need `PYTHONPATH` set.
- Detach long jobs (`nohup ... & disown`) — power and internet on this box are flaky
  independently.
- Commit as soon as tests pass; don't let verified work sit uncommitted.
- WAL-safe backup discipline before bulk writes to the production DB.

---

## 5. INFRASTRUCTURE BUILT AND VALIDATED (still sound, reusable regardless of cutover)

- **PIT reconstruction:** `analysis/pit_geo_elo.py` (validated 3,229/3,229 vs
  production-at-now; NOTE it faithfully reproduces `geo_elo`'s bug by design — it's a
  point-in-time replay tool, not a fix), `analysis/pit_positions.py` (validated 1.2M
  items, zero unexplained divergence), `monitoring/price_history.py` `price_at()` (CLOB,
  all 5 edge cases proven, cross-source 73.1% stratified — characterised as
  primary-with-fallback, age/liquidity-dependent).
- **Canonical backtest population:** `column_definitions.py` Section 6,
  `backtest_window_sql()`, `tape_end`-anchored (not `resolution_date` — see O-45/O-36),
  half-open intervals, INNER JOIN so zero-trade markets drop structurally. Frozen
  snapshot `bt_pop_2025-11-01_v1` (4,712 markets) in `backtest_population_snapshots`.
- **B5 event clustering:** `event_cluster_labels`, 4,712/4,712 rows. `neg_risk` native
  grouping covers 40.1% (1,891 markets / 522 groups); 143 ambiguous hand-labelled, all
  standalone; 3 structural checks passed (0 merge errors across 3,343 clusters);
  external audit found 0 false splits (O-46 cleared).
- **B4 order-book capture:** live, daily, ~2,691 rows / 366 markets, liveness summary
  guards against silent-empty.
- **Layer 0/v2 metric scripts:** `layer0c_corrected_metric.py`,
  `trader_skill_metric_v2*.py` — all committed, parameterised, `--selfcheck`.

**Cost floors (category-specific, at the cohort's own empirical entry prices):**
Geopolitics is fee-free, floor 0.0005–0.010 (spread only); Elections carries a 4%
feeRate, fee 0.0097 at the cohort's median price of 0.59, floor 0.0056–0.020. The
blended 0.02 effect-size bar is comfortable for geopolitics (up to 2× headroom) but sits
at the *top* of elections' range — defensible, not generous.

---

## 6. OPEN ITEMS

1. **Cutover decision** — does the new metric replace `geo_elo` in production? **Not
   made.** Requires its own pre-registration and a before/after on cohort membership.
2. **Category-split cost floor** — the blended 0.02 bar works for geopolitics but is
   tight for elections (see §5). Not fully resolved.
3. **Ingestion detection** — still mandatory before any months-long passive run. No
   alert exists when the DB is missing trades the API has; the 08-11 13-hour cohort gap
   was found by luck. Note O-49's correction: trades do NOT self-heal for already-known
   traders (`monitor.py` is recency-only; `background_backfill_worker` only targets
   brand-new traders). Targeted cohort re-fetch required after any outage.
4. **The consensus question** (does ≥2-member agreement beat individual positioning) —
   untested, correctly not run on a broken foundation, now testable.
5. **`comprehensive_elo` / `calibration_analysis.py`** — analogous sign-error pattern
   flagged, out of scope all session, **still open and live-affecting.**
6. **O-49 gap-flagging** — still diverging, not converging (tape_end-in-window
   0 → 4,979 → 20,211 across Aug 07/09/14). Do not flag until two consecutive readings
   are materially unchanged.
7. **Carried:** elections calibration re-run (O-40), RQ1.1 repoint, O-38, O-18,
   canonical allowlist fix for `gap_recovery_20260811`, maintenance lock-file
   hardening.

---

## 7. STANDING METHODOLOGY RULES (carry these — they were earned)

- **Reproducibility.** Any number carrying a project decision must come from a
  committed script writing to a durable artifact with generating parameters recorded.
  Three decision-carrying numbers have proved unreproducible to date (the 9/8 B3
  scoping, the 08-12 retest's 28 formations, v2's first 10 raw formations).
- **Pre-registration.** Hypothesis, metric, and success criterion fixed and written
  before computing. Do not re-specify to obtain a preferred result. If a gate fails,
  stop and report.
- **Boundary check.** When a reconstruction produces a striking result, check whether
  it sits at a boundary *we* chose before concluding it's a property of the world.
  Twice bitten — O-49 (current absence ≠ permanent absence) and the 06-01
  roster-lookback artifact that produced a false stop-the-project conclusion.
- **Field semantics established empirically, never from field names or docstrings.**
  The `geo_elo` sign error came from inferring meaning from a name.
- **Calibration plot as precondition.** Plot mean edge vs price, split by side, before
  trusting any edge metric. Both metrics built this arc had normalisation errors that
  only surfaced this way.
- **Test the premise before building the instrument.** Rung A was the cheapest test
  available on the diagnostic ladder and got sequenced last — the lesson this whole
  arc exists to institutionalise.

---

## 8. IMMEDIATE NEXT STEPS

1. Do not consume `geo_elo` for any new skill-ranking work without reading
   `2026-08-15-skill-metric-rebuild.md` first.
2. Decide (with Oscar) whether to pre-register the cutover (§6.1) or continue running
   the new metric in parallel a while longer.
3. Re-derive the backtest volume estimate (§3) on the new metric before treating the
   14–43-year figure as final — it was measured on the broken instrument.
4. Build the ingestion-detection alert (§6.3) before any extended passive paper-trading
   run — this is now load-bearing since Phase 2 is the primary experiment.
5. Everything else in §6 is real but secondary — don't let it derail the two items
   above unless it turns out to actively block them.

---

*This document was generated by Claude (chat instance) on 2026-08-16 at Oscar's request,
to replace `2026-07-18-MASTER-HANDOVER.md` as the entry point for new-chat handoff. It
draws on `2026-08-15-skill-metric-rebuild.md`, `2026-08-15-session-summary.md`, and
direct verification of repo state (git log, systemctl status) at time of writing. Treat
it as a snapshot — verify anything load-bearing against current repo state before
relying on it if significant time has passed.*
