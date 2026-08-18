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

=== SECTION: THE HYPOTHESIS, PLAINLY ===
Strip away every layer of infrastructure and the question has always been one sentence: do skilled traders on Polymarket predict outcomes better than the market price, in a way that's identifiable in advance and tradeable after costs?
That's it. Everything else — geo_elo, PIT reconstruction, event clustering, the cost model, the whole v2 metric rebuild — exists only to answer that one question honestly. When any of it stops serving that question, or when we can't tell whether it does, that's a signal to stop and re-anchor, not to keep building. This session's realignment happened because we lost sight of this for a period and let the instrument (the spec) become more complex than the question ever required.

=== SECTION: HOW WE WORK ===
A new instance should understand the working relationship, not just the findings, because the METHOD is as load-bearing as the results.

Division of labour: Oscar sets direction, priorities, and makes final calls on anything ambiguous or consequential (thresholds, scope changes, cutover decisions). Claude reasons about design, spots risk, proposes and critiques methodology, and writes the precise instructions Claude Code executes. Claude Code is the hands — it runs queries, writes code, and reports findings, but it does not make judgment calls about what a finding MEANS or what to do next; that comes back to this conversation.

The core discipline, in order of how often it's saved us:

1. PRE-REGISTER BEFORE COMPUTING. Hypothesis, metric, and success criterion are written down and committed BEFORE any result exists. This is not bureaucracy — it is what makes a null result trustworthy and prevents unconsciously searching for a specification that produces a preferred answer. Every "vX" pass this session (Layer 0 through v2f) followed this pattern, and it is why the final null-but-underpowered result can be believed rather than second-guessed.

2. TEST THE PREMISE BEFORE BUILDING THE INSTRUMENT. The single biggest mistake of the project's first month: we validated the plumbing (PIT reconstruction, positions, prices, clustering) to an exhaustive standard, and never directly asked "does the base skill metric predict anything at all" until forced to. That question was always the cheapest one available and should always be asked first on any new thesis or sub-question.

3. IF A GATE FAILS, STOP AND REPORT — DO NOT RE-SPECIFY TO PASS IT. This happened repeatedly and explicitly this session (v2's calibration gate failing and staying failed until properly diagnosed; v2e's coverage simulation catching a real bug in the correction itself before it was reported). The instruction to Claude Code is always: if the pre-registered criterion isn't met, say so and stop, don't quietly adjust the method until it is.

4. ESTABLISH FIELD SEMANTICS EMPIRICALLY, NEVER FROM NAMES OR DOCSTRINGS. The entire geo_elo sign-error saga traced back to inferring what a price field meant from its name and the surrounding code's apparent intent, rather than checking what the data actually contained. The fix, now standard practice: for any price/probability field, take paired opposite-side trades on the same market at the same moment and check whether they sum to ~1.0. That single test would have caught the bug on day one.

5. CHECK WHETHER A STRIKING RESULT SITS AT A BOUNDARY WE CHOSE. Any time a reconstruction or measurement produces a dramatic finding, ask first whether it's a property of the world or an artifact of where WE decided to start looking (a lookback window, a data-availability cutoff, an outage boundary). This has fired twice this session alone — a stop-the-project "consensus only forms after certainty" conclusion that was entirely a lookback-window artifact, and a "trades are gone forever" conclusion (O-49) that turned out to be current-absence mistaken for permanent-absence.

6. REPRODUCIBILITY IS NOT OPTIONAL. Any number that carries a project decision must come from a committed, parameterised, re-runnable script writing to a durable artifact with its generating parameters recorded — not a one-off background-agent run, not a number quoted from memory of a prior chat. We have been burned by this three separate times (the original B3 scoping's 9/8, a 28-formation retest, v2's first raw count) — each anchored real project decisions and none could be regenerated when questioned.

7. WHEN SOMETHING SURPRISES YOU, DIAGNOSE IT RATHER THAN JUST REPORTING IT OR SUPPRESSING IT. A gate failure or a degenerate statistic is not just "the answer" — it's information about why the method broke, and that diagnosis is usually the most valuable output of the pass (see: the market-concentration diagnosis behind v2's gate failure, the t-vs-z coverage bug behind v2e's correction). But diagnosing is not license to then quietly fix and re-run without disclosing what happened — every self-caught error this session was reported explicitly, including the ones that were embarrassing.

8. HONEST NULL RESULTS ARE THE GOAL, NOT A FAILURE MODE. The project's most valuable outputs this month were negative or ambiguous findings, arrived at rigorously: geo_elo doesn't measure what we thought; the backtest can't reach the required power; the corrected thesis test is null but underpowered rather than confirmed. Each of these closes off a wrong path cheaply instead of expensively. A confident wrong answer is a worse outcome than an honest "we don't know yet," and the entire methodology above exists to make the honest answer the only one the process can produce.

A new chat instance inheriting this project should hold this posture from the first message: skepticism toward our own prior conclusions, insistence on empirical verification over inference from names/docs/intent, and comfort reporting "this doesn't work" or "we don't know" as a complete and valuable answer.

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

**LEGENDARY overlap with the new metric's equivalent tier — CORRECTED 2026-08-18.**
Originally reported here as **15/81 (18.5%)**, measured against a hardcoded
`geo_elo >= 2175` predicate used across all six `trader_skill_metric_v2*.py` sites. That
predicate is **not** the canonical gate (`cd.LEGENDARY_GATE_WHERE`: `geo_elo_active >=
2175 AND geo_accuracy_pool=1 AND research_excluded=0 AND bot_type IS NULL`), so the
reference set of 81 was inflated. The 15/81 figure itself reproduces exactly as of
2026-08-18 — it is not data drift, it is the wrong denominator. **15/81 is superseded;
do not quote it going forward.**

**Corrected overlap: 3/10 (30.0%), as-of 2026-08-18T19:25:10Z.** This figure MUST NOT be
quoted without that timestamp: `geo_elo_active` carries continuous time decay, so the
canonical LEGENDARY set moves as time passes even with no code changes. It is also
structurally unstable at this sample size — n=10 means each trader is worth 10
percentage points and each overlap trader ~33 points; small changes here carry no
information.

Why the number changed: the original was measured against a non-canonical gate, not
against different underlying data — a future reader must not mistake this for
population drift. Decomposition of the 81 inflated traders against the four canonical
conditions: the `geo_elo_active` time-decay condition alone disqualifies 69/81 (85.2%) —
the dominant driver by far; `geo_accuracy_pool=1` removes 21; `research_excluded=0`
removes 4; `bot_type IS NULL` removes 1; 20 traders fail more than one condition. The
inflated reference set was inflated almost entirely by including traders whose ELO has
since decayed below the bar, not by pool/exclusion/bot-type differences.

The claim survives, restated at the corrected strength: **70% of the canonical
LEGENDARY tier is still absent from the new metric's cohort** — substantially
different, on a small and unstable sample — rather than "little in common," which
overstated the original 18.5% figure by roughly 1.6x.

Source: `2026-08-18-legendary-overlap-recompute.md` (commit `dd2261a`), generating
script `scripts/characterize_legendary_overlap_recompute.py` (first-repo, commit
`fd9e329`).

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
   **Added 2026-08-18:** the "before" state for that before/after must anchor on the
   corrected canonical n=10 LEGENDARY set (see §1), not the inflated n=81. With n=10
   and continuous decay, a noise threshold must be fixed in the pre-registration
   BEFORE computing, or the comparison will not be decidable. This is a decision for
   Oscar, not yet made.
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
6. **O-49 gap-flagging — CORRECTED 2026-08-16.** The prior framing here ("still
   diverging, not converging, tape_end-in-window 0 → 4,979 → 20,211 across Aug
   07/09/14") was wrong and had propagated across handovers. The 2026-08-16
   reproducibility audit established that 20,211 and `trade_gap_flag` were never the
   same measurement: 20,211 is an ad-hoc readiness count ("tape_end in outage
   window"), never applied as a write; today's `markets.trade_gap_flag = 1` count is
   250, comprising the SAME April-gap (166) + O-37-quarantine (84) components that
   predate 08-15. The "do not flag until two consecutive readings are materially
   unchanged" deferral applies to the readiness count, not to the flag — the flag
   itself has not been touched by O-49 at all.
   (`2026-08-16-result-of-record-reproducibility-audit.md`)
7. **Carried:** elections calibration re-run (O-40), RQ1.1 repoint, O-38, O-18,
   canonical allowlist fix for `gap_recovery_20260811`, maintenance lock-file
   hardening.
8. **v2f population bypass (found 2026-08-16).** The v2f pipeline does not call the
   canonical `backtest_window_sql()` — it computes `tape_end` independently
   (`build_tape_end_map`) and anchors its query on the `positions` table rather than
   `markets`/`trades`. At the T_split boundary: canonical population = 6,842 markets;
   v2f's implicit population = 6,588 — a 254-market symmetric difference, entirely
   one-directional (v2f is a strict subset of canonical). Root cause: 166 markets have
   trades but no FIFO-closed position; 88 have positions but `trade_result='pending'`
   on a market flagged `resolved=1`. Because `edge = won − entry_price` requires a
   closed position, the metric is structurally conditioned on clean closure — the
   cohort's edge is measured on a non-random subset of the population, of unknown
   direction and magnitude. The 88 `resolved=1`/`trade_result='pending'` markets are a
   separate, open data-consistency item (`markets.resolved` and the entry trade's
   `trade_result` can disagree).
   (`2026-08-16-canonical-infrastructure-recon.md`, commit `f6cbbf0`)
9. **Objective 2 cohort persistence gap (found 2026-08-16).** Objective 1 persists its
   membership (`metric_v2f_intersection_cohort`, 295 trader addresses); Objective 2 —
   the pipeline stage that actually produces the headline result — persisted only
   aggregate counts, never the 148 qualifying / 120 surviving / 148 matched-control
   trader addresses. This is the specific mechanism behind the 2026-08-16
   UNREPRODUCIBLE verdict (see §6a): when cohort membership shifts, there is nothing
   to diff against. The schema pattern needed already exists — Objective 1 uses it —
   and was simply not applied to Objective 2.
   (`2026-08-16-result-of-record-reproducibility-audit.md`, commit `5195b01`)

---

## 6a. REPRODUCIBILITY AUDIT — 2026-08-16

**Verdict: UNREPRODUCIBLE.** Not because the finding changed character — the re-run is
still null, still directionally positive, still ~2.3x the placebo's point estimate. It
is UNREPRODUCIBLE because the audit's fixed criteria required row-level attribution for
every discrepancy, and the audit could only rule causes *out*, not name the ones
actually responsible.

- **Code drift: ruled out entirely.** Current HEAD *is* `eaeabbc`, the
  `generator_commit` persisted on every result-of-record row. Zero commits have landed
  in first-repo since the result of record.
- **Prior-state record: exists, and reconciles exactly.** The persisted
  `metric_v2f_oos_result` / `metric_v2f_findings` tables match the stated figures
  precisely — `generated_at = 2026-08-15T19:36:56.85Z`. The number of record is
  genuinely the number persisted.
- **Re-run deltas (same seed, same code, different data):**
  - Objective 1 intersection cohort: 295 → 298.
  - Objective 2 cohort: 3,032 → 3,033 positions, point estimate +0.03160 → +0.03184.
  - Objective 2 placebo: 2,569/110 → 2,518/106 positions/traders, point estimate
    +0.01271 → +0.01392.
- **Mechanism confirmed active, but not resolved to specific rows.** Background
  backfill is actively inserting pre-T_split-timestamped trades into the DB: 162,648
  such rows among the most recent 553,800 inserted (by rowid). This plausibly explains
  the shape of the drift but was not traced to the individual rows behind each figure —
  see §6.9 for why (Objective 2's membership was never persisted to diff against).
- **Pin-mechanism finding.** Nothing in the schema currently pins dataset state to a
  decision-carrying number — only code (`generator_commit`) and time (`generated_at`).

**New baseline fingerprint, 2026-08-16:** traders=170,430; trades=11,350,510;
positions=7,476,972; markets=722,851; max trade timestamp=2026-08-16 14:12:03;
resolved markets=224,828; Geopolitics/Elections resolved+gap-clean=10,448;
`trade_gap_flag=1` count=250.

Full detail: `2026-08-16-result-of-record-reproducibility-audit.md` (commit `5195b01`).

---

## 6b. CANONICAL INFRASTRUCTURE — ENFORCEMENT IS CONVENTION-ONLY (2026-08-16)

Canonical adherence across this project is convention-only, not structural, with one
exception. `check_canonical_definitions.py` (the drift guard wired into daily
maintenance) covers geo_elo thresholds and Pool-C SQL shapes — it has **zero coverage
of Section 6** (`backtest_window_sql`), confirmed by reading its AST rules directly.
Nothing in the codebase would have flagged the v2f bypass (§6.8). More broadly,
`run_tests.py` has no automatic trigger anywhere — no pre-commit hook, no CI — so even
the tests that exist (including ones that would catch this class of drift) only fire on
manual invocation.

The one structurally-enforced counter-example: `json_safety.py` /
`test_cross_repo_lock.py` — a test that imports both repos' independently-maintained
copies of the lock-path logic and asserts they agree, plus runs real concurrent
multiprocess writers across both. Even this runs only on manual invocation
(`python3 -m pytest`), not automatically.

Separately: the two repos' `brain/integration-contract.md` files are entirely different
documents (v1.4, 275 lines vs. v2.13, 1,413 lines), not cross-linked, and both stale.
The larger copy's documented daily-maintenance step list (19–20 steps) is missing 10+
steps present in the actual current `daily_maintenance.py` (29 steps), including a
blocking pre-ELO integrity gate that the "authoritative" contract does not mention.

Full detail: `2026-08-16-canonical-infrastructure-recon.md` (commit `f6cbbf0`).

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

*Amended 2026-08-16 (same day, later pass): §6 item 6 (O-49) corrected — the prior
0 → 4,979 → 20,211 framing conflated an ad-hoc readiness count with the actual
`trade_gap_flag` column, which the reproducibility audit found were never the same
measurement. §6 items 8–9 and §6a–§6b added, covering the v2f `backtest_window_sql`
population bypass, the Objective 2 cohort-persistence gap, the 2026-08-16
reproducibility audit (verdict: UNREPRODUCIBLE) and its new baseline fingerprint, and
the canonical-infrastructure enforcement finding (convention-only, one structurally-
enforced exception). Sources: `2026-08-16-canonical-infrastructure-recon.md`
(commit `f6cbbf0`) and `2026-08-16-result-of-record-reproducibility-audit.md`
(commit `5195b01`). §1 and §2 (the metric teardown and the thesis result) are
unchanged by this amendment.*

*Amended 2026-08-18 (later pass): §1's LEGENDARY overlap figure corrected — 15/81
(18.5%), measured against a hardcoded non-canonical gate across all six
`trader_skill_metric_v2*.py` sites, replaced with 3/10 (30.0%, as-of
2026-08-18T19:25:10Z) against the canonical `cd.LEGENDARY_GATE_WHERE`, with the
time-decay decomposition and an explicit instability/as-of warning. §6.1 (cutover
decision) updated to anchor any before/after on the corrected n=10 set. §2 (the thesis
result) is unaffected by this amendment. Sources: `2026-08-18-legendary-overlap-
recompute.md` (commit `dd2261a`) and its generating script
`scripts/characterize_legendary_overlap_recompute.py` (first-repo, commit `fd9e329`).*
