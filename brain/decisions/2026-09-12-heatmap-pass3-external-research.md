# Heatmap Pass 3 of 5 — External Research

**Date:** 2026-09-12
**Depends on:** Pass 1 (asset inventory, trading-swarm `1bb36e1`), Pass 2 (ruled-out
register, trading-swarm `5e94eef`). Asset IDs (`data_d1`, `instr_v8`, ...) and register
entry IDs (`A1`-`A11`, `B1`-`B6`, `C1`-`C8`, `D1`-`D10`) refer to those documents.

**Scope:** what the outside world already knows, bearing on this project's questions,
findings, and blind spots. Three jobs, run in parallel by three research sweeps, each
using live WebSearch/WebFetch against primary sources (arXiv, SSRN, exchange
documentation) where reachable. This pass does not propose what to do about any of it —
that is pass 4/5.

---

## Headline finding — flagged prominently, per instruction

**The project's own-market calibration result (`instr_v8`, 2026-09-10) and the closest
external primary source (arXiv:2602.19520) genuinely conflict on calibration SHAPE, and
the conflict is only partially explained.** Both agree on direction (underconfidence,
slope > 1 almost everywhere). They disagree on shape: the project finds slope falling
from ~1.29 near resolution to ~1.14 weeks out; the external paper finds slope rising
from 0.99 at 0-1h to 1.32 beyond a month (pooled), and a noisy but still net-rising
Politics-specific pattern (1.34 → 1.73, non-monotonic). Full detail in Job B §1 below.
**This does not trigger the formal stop condition** — pass 2's register has no entry for
this specific test (`instr_v8` produced a live, non-closed finding, not a ruling), so
there is no CLOSED-STRONG ruling being contradicted. It is flagged here with the same
seriousness the task assigns it regardless.

---

## Search scope and transparency

**Job A** (25 unasked questions): searched arXiv, SSRN for 7 priority RQs plus 3
lower-priority items. Primary sources reached directly where possible; two PDF fetches
degraded to compression-encoded, unreadable content (arXiv:2602.19520's PDF,
arXiv:2604.27041 partial) — flagged per-item below, with HTML-rendering fallback used
where available.

**Job B** (agreement/conflict): 5 specific checks. arXiv:2602.19520 and arXiv:2606.07811
fetched and read directly (primary-source-confirmed). SSRN 6617059 and SSRN 6191618
(the project's own two foundational citations) both returned **HTTP 403** on their
abstract pages — could not be read directly; figures for both come from search-result
excerpts and secondary summaries (SSRN Blog, Yale Insights), **flagged explicitly as
secondary**, not the primary PDF/abstract. A Medium technical deep-dive on Polymarket's
CLOB mechanics also 403'd.

**Job C** (unconsidered inefficiencies): all 6 required categories searched. Two PDF
fetches (arXiv:2601.01706, arXiv:2606.16852) returned compressed/unparseable content —
findings rely on abstract/search-snippet level for those two, flagged. Several
cross-platform-arbitrage findings are **blog/secondary-source only** (no academic
primary source located, despite targeted search) — flagged explicitly throughout that
section rather than presented as verified.

**What came back empty, reported as information:** a quantified "copyable window" with
an edge magnitude for prediction-market copy-trading (Job B §3); a validated
market-maker/LP-exclusion methodology specific to prediction-market aggregate-positioning
strategies (Job C); independent replication of the specific pattern "a matched control
group matches or beats a naively-selected skilled group" outside this project (Job B
§4); trader-level (not market-level) correlated-position skill signals (Job A,
RQ-CORRELATION-001); prediction-market-specific momentum/serial-correlation literature
with a reportable effect size (Job C §4).

---

## JOB A — the 25 unasked questions

### A1. RQ-VPIN-001 (volume-synchronized probability of informed trading)
**Verdict: PARTIALLY ANSWERED.**
VPIN has been directly applied to Polymarket: Nechepurenko, *"Per-Market Information
Leakage and Order-Flow Skill"* (arXiv:2605.02287, May 2026). Key finding: **inferred
VPIN (from public order-flow classification) diverges substantially from ground-truth
VPIN**, and order-flow-imbalance estimates are directionally biased — but **ground-truth
VPIN positively predicts Brier scores** (forecast accuracy) while Gibbs spread
negatively predicts them. Classical critique literature (Andersen & Bondarenko, SSRN
1881731) finds VPIN's predictive power for volatility is a mechanical artifact of
trade-classification error under Bulk Volume Classification, not fundamentals-based —
a pre-existing methodological warning for anyone building on *inferred* (not
ground-truth) VPIN.
**Cheap win?** Partially — the ground-truth-vs-inferred distinction is the load-bearing
finding and would need to be designed around, not simply replicated. Not a full
drop-in answer.

### A2. RQ-ILS-001 (information leakage score)
**Verdict: ANSWERED — strong cheap win.**
A dedicated paper exists with the same name and concept: Nechepurenko, *"ForesightFlow:
An Information Leakage Score Framework for Prediction Markets"* (arXiv:2605.00493, May
2026) — an ILS quantifying how much of a market's terminal move was priced in before
the corresponding public-news event, applied to Polymarket, with public code/data
(github.com/ForesightFlow). Companion papers from the same research program:
*"Information Leakage at Population Scale: An Evaluation of the Polymarket
Insider-Relevant Subpopulation, 2020-2026"* (arXiv:2605.00459) and *"Empirical
Evaluation of Deadline-Resolved Information Leakage on Documented Polymarket Insider
Cases"* (arXiv:2605.02286). Effect sizes (from the companion paper, 2605.02287): skilled
accounts + market makers (<3.5% of accounts) capture >30% of platform gains.
**Cheap win: yes, unambiguously.** This project never needed to build RQ-ILS-001 from
scratch — a maintained framework with public code already exists, under the same name.

### A3. RQ-POSSIZE-001 / RQ4.1 (position size / Kelly alignment as skill signal)
**Verdict: PARTIALLY ANSWERED.**
Academic: Meister, *"Application of the Kelly Criterion to Prediction Markets"*
(arXiv:2412.14144, 2024) shows theoretically that misjudged position sizing degrades
portfolio growth rate via KL-divergence between belief and true distribution — position
size *quality*, not raw size, is the relevant signal. This is **consistent with the
project's own null finding** on `kelly_alignment_score` (pass-1 `built_b5`, found
null/negligible under Stage 0b). Secondary (blog, flagged as such): bet size functions
as a wallet-relative, track-record-filtered confidence signal — large tickets against
prevailing price from high-scoring wallets are informative, small/generic-sized bets are
not. Mitts & Ofir 2026 (SSRN 6426778, "From Iran to Taylor Swift") use bet size jointly
with timing/profitability/directional concentration as one of five criteria in a
composite insider-detection score across 93,000 markets/50,000 wallets, flagging ~$143M
in suspicious profits — **position size alone is not used as an isolated signal
anywhere found; it's always conditioned on trader history.**

### A4. RQ-SECTOR-001 (category specialization)
**Verdict: PARTIALLY ANSWERED — literature conflicts with itself.**
General forecasting research (Tetlock, foundational) finds domain expertise is *not* a
reliable predictor of forecasting skill — cognitive style ("fox" vs. "hedgehog")
dominates. Prediction-market-specific secondary sources (trading-strategy blogs, not
peer-reviewed) claim the opposite for Polymarket specifically: category specialization
is load-bearing, with distinct non-transferable skill profiles by category. A relevant
academic paper, Le, arXiv:2602.19520 (the same paper as the calibration-shape check,
Job B §1), directly studies domain-specific calibration dynamics but its category-specific
slope numbers could not be fully extracted (PDF compression-encoded; HTML rendering
partially recovered political-market numbers only, see Job B §1).
**Verdict: genuinely contested, not cleanly answered either way.**

### A5. RQ-CORRELATION-001 (correlated positions across markets)
**Verdict: OPEN, mostly.**
Substantial literature exists on *market-level* correlation/arbitrage (neg_risk-adjacent:
"Executable Arbitrage and Market Efficiency in Prediction Markets," arXiv:2608.00666;
cross-market no-arbitrage relationships beyond neg_risk, arXiv:2605.11640) — but this is
about price-consistency arbitrage between linked markets, not a *trader's* correlated
position-taking as a skill signal, which is what the internal RQ asked. **No paper found**
treating trader-level cross-market position correlation as an informedness signal.

### A6. RQ4-MULTI (multivariate Kelly for correlated positions)
**Verdict: ANSWERED on the math, not on application.**
Tepelyan & Lam, *"Efficient Multivariate Kelly Optimization Reveals Sigmoidal Scaling
Laws"* (arXiv:2604.24723, April 2026) solves exactly this: naive multivariate Kelly is
O(2^N) for N simultaneous correlated bets; their integral-transform method reduces it to
O(N), tractable for hundreds of bets. General portfolio-optimization result, **not
validated as a prediction-market trader-skill-detection tool** — answers "how would an
optimal bettor size correlated positions," not "does observed sizing reveal skill."

### A7. RQ3.2 (crowd vs. elite divergence)
**Verdict: ANSWERED — and the project already has this paper.**
Gómez-Cram, Guo, Jensen & Kung (SSRN 6617059) — already cited in the project's own
directional-skill persistence work (pass-2 entries A2-A4, the source of the 44%/3%
benchmark figures) — directly answers RQ3.2: **~3.14% of accounts** (a sign-randomization
test on 1.72M accounts, 210,322 markets, $13.76B volume) are a persistently-skilled
informed minority; "the crowd generates most of the volume but little of the information,
and its losses fund the minority's profits."
**This is the single clearest case in Job A**: the project's own RQ3.2 sat
ABANDONED-UNTESTED (pass-2 `D3`) while the exact paper needed to answer it was already
being used elsewhere in the project for a different purpose, and nobody closed the loop
back to RQ3.2 itself.

### A8. RQ-SCI-001 (signal credibility index validation) — lower priority
**Verdict: ANSWERED — strong cheap win.**
Nechepurenko, *"The Signal Credibility Index for Prediction Markets: A
Microstructure-Grounded Diagnostic with Weighted and Time-Varying Extensions"*
(arXiv:2604.27041) — same name, same concept as the project's own `signal_credibility.py`
(pass-1 corrected: it is live, not dead, but annotation-only, gated on ≥20 resolved
markets never reached — pass-2 `D4`). Published version has: a persistence-ratio
component on logit prices, weighted Cobb-Douglas form with flow-concentration HHI, a
time-varying real-time specification, and **Monte Carlo validation including
out-of-distribution stress tests and coordinated multi-wallet manipulation scenarios** —
validation depth the project's own version doesn't have. Paper cautions its τ*=0.27
threshold is calibrated to its own simulation universe, not universal — "empirical
applications should recalibrate by domain, platform, and response horizon." Not a
drop-in replacement, but a validated starting framework.

### A9. Discovery-gap-closure's relevance-classifier recall (general NLP angle) — lower priority
**Verdict: PARTIALLY ANSWERED.**
Comparable relevance/frame-classification benchmarks report LLM/fine-tuned-model F1 in
the 0.94-0.98 range (DeBERTa 0.98, Claude zero-shot 0.96, Llama3-70B 94.4% on
fake-news F1) in adjacent domains — meaningfully above the project's own 90.35% recall
(pass-2 `C1`). But a media-bias relevance-classification benchmark reports F1 as low as
0.381 — the task-difficulty range is enormous and domain-dependent; the general
literature does not establish whether this project's specific political/geopolitics
market-title classification task is closer to the easy or hard end. **Does not
contradict** the project's own diagnosed conclusion (diffuse, 18-subtype failure,
matching its own §3.11(a) "abandon" criterion) — none of these benchmarks studied this
exact task.

### A10. STR-004 archetype/market-maker filtering — lower priority
**Verdict: OPEN.**
No paper found validating a specific methodology for excluding liquidity-providers/
market-makers from a capital-weighted aggregate skill signal in prediction markets
specifically (relevant to pass-2 `C7`, STR-004's stalled required re-specification);
only generic "smart money concept" trading-blog material (not academic) and general
market-microstructure literature on LP/taker clustering by order-flow pattern (not
skill).

---

## JOB B — agreement and conflict with the project's own findings

### B1. Own-market calibration shape — GENUINE, PARTIALLY-EXPLAINED CONFLICT
See Headline finding above for the summary. Full detail:

**Project finding** (`instr_v8`, 2026-09-10): logistic recalibration slope >1 at every
lead time, FALLING from ~1.29 near resolution to ~1.14 at weeks out. Geo/Elections only,
price-weighted, `tape_end`-anchored, 9,739 canonical markets.

**External source** (primary, fetched directly): Nam Anh Le, *"Decomposing Crowd Wisdom:
Domain-Specific Calibration Dynamics in Prediction Markets,"* arXiv:2602.19520. 353M
trades, 429,000 binary contracts, Kalshi (64.7M trades/210,608 contracts) + Polymarket
(288.7M trades/218,000 resolved), all six categories.

- **Universal (pooled) horizon effect:** slope RISES 0.99 (0-1h) → 1.32 (beyond 1
  month) — confirms the numbers cited in the task exactly.
- **Politics-specific (Kalshi, Table 4), 9 horizon buckets:** 1.34 (0-1h) → 0.93 (1-3h,
  attributed to Trump-administration-contract composition effects) → 1.32 (3-6h) → 1.55
  (6-12h) → 1.48 (12-24h) → 1.52 (24-48h) → 1.83 (2d-1w) → 1.83 (1w-1mo) → 1.73 (1mo+).
  Net direction 0-1h→1mo+ is still a **rise** (1.34→1.73), not monotonic, not a clean
  fall either.
- **Polymarket-specific:** the paper states the pattern "is also visible on Polymarket
  across the three comparable domains" and reports a single blended mean slope 1.45
  across reliable bins for political markets (excluding the two shortest horizons for
  timestamp noise) — a full Polymarket-only horizon breakdown was not extractable from
  the available rendering.
- **Weighting:** the external paper is contract/position-size-weighted ("larger
  positions are associated with prices further from truth") — **differs from the
  project's price-weighting**.
- **Time anchor:** τ = close_time − trade_time, calendar duration — conceptually
  similar to, but not identical to, the project's `tape_end` anchor.

**Verdict: CONFLICT, not fully explained.** Even narrowing to Politics-only and
Polymarket-only, the external paper finds slopes flat-to-rising with horizon (or at
minimum a noisy non-monotonic pattern with an overall rise), while the project finds a
clean monotonic fall. Two of three candidate explanations are present but neither is
confirmed sufficient from the primary source alone:
- **(a) Population breadth** — project is Geo/Elections narrowly; external Politics
  domain is broader and pools Kalshi+Polymarket.
- **(b) Weighting scheme** — position-size-weighted vs. price-weighted is a genuine
  methodological difference; the paper's own note that "larger positions are associated
  with prices further from truth" suggests weighting choice could materially affect the
  measured slope-by-horizon shape.
- **(c) Anchoring** — plausibly *not* the driver, since both use an actual-trade/close-based
  anchor rather than a raw `resolution_date` field.
**This is a real, unresolved shape conflict.** Per pass 2, no register entry exists for
this specific test (it produced a live, non-closed finding from `instr_v8`), so this
does not trigger the formal stop condition — flagged with equivalent seriousness
regardless, per instruction.

### B2. Directional persistence 37.0%/18.6% vs. Gómez-Cram's 44%/3% — NOT DIRECTLY COMPARABLE
**External source** (methodology confirmed via SSRN Blog + Yale Insights secondary
summaries; SSRN abstract page itself returned HTTP 403 — **flagged, secondary**):
Gómez-Cram, Guo, Jensen & Kung, *"Prediction Market Accuracy: Crowd Wisdom or Informed
Minority?"* SSRN 6617059, April 2026. Population: all of Polymarket, $13.76B volume,
1.72M accounts, 98,906 events, 2023-2025. Skill classification: 10,000-simulation
coin-toss benchmark per trader, ~3% classified skilled. Persistence test: **split-half
by randomly dividing each trader's own events in half** — "44% of traders classified
skilled based on the first set are also classified that way in the second" (vs. ~10%
for mutual fund managers, cited as context).

**Project's own test:** temporal split at `T_split`, **not** split-half — the project's
own handover already explicitly names this "the project's own first direct test of
Gómez-Cram's persistence methodology, temporally rather than by split-half." Population:
Geo/Elections-only, PIT-legal classifiable traders (5,732), 146-trader
pre-split-BH-skilled cohort (pass-2 `A2`-`A4`).

**Verdict: NOT DIRECTLY COMPARABLE** — confirmed methodological difference (temporal
vs. random split-half) plus population difference (narrow Geo/Elections vs.
all-category). No numerical conflict: the project's CI [29.45%, 45.21%] contains 44%, so
nothing contradicts Gómez-Cram's figure, but the comparison cannot be read as a
replication given the split-methodology difference. Confirms what pass 2 already
flagged (CI straddles the external benchmark, "expected at N=146, not a failure") — now
against the actual primary methodology rather than assumed.

### B3. Copy-trade decay vs. published price-discovery speed — ADJACENT, NOT DIRECTLY COMPARABLE, ROUGHLY CONSISTENT
**Project finding** (`A6`): edge COLLAPSES-BEFORE-CADENCE — no CI-excludes-zero edge at
or beyond N=15min on any population/construction (+0.01233, CI [−0.00186, +0.02410] at
N=15min).

**External source** (primary, fetched directly): Angelini & De Angelis, *"When Do
Markets Fully Process Public Information? Evidence from Real-Time Prediction Markets,"*
arXiv:2606.07811, June 2026. Finds a one-minute change in a benchmark probability model
is associated with only a **0.64-for-one contemporaneous** price change; the missing
0.36 predicts price drift over "the following several minutes," with underreaction
larger in low-liquidity markets. No exact minute-count for full adjustment, no explicit
profitability figure.

**Verdict: NOT DIRECTLY COMPARABLE** (this paper measures market-wide reaction to
*public news signals*; the project's question is about copying one *individual informed
trader's own position* — a different mechanism) but **roughly consistent, not
contradictory** — a "several minutes" underreaction/drift window at the market level is
not inconsistent with the project finding that nothing capturable remains by 15 minutes.
**No paper found** (searched explicitly) reporting a quantified "copyable window" with
an edge magnitude comparable against the project's own cost floors (geo 0.0005-0.010,
elections 0.0056-0.020) — reported as an empty search, not stretched to fit.

### B4. The falsified-selectors pattern — INDEPENDENT SUPPORT FOR THE EXPLANATION, NOT FOR THE PATTERN ITSELF
**Della Vedova, SSRN 6191618** (methodology confirmed via search-result excerpt; SSRN
page itself 403'd — **flagged, secondary**), *"Who Profits from Prediction Markets?
Execution, not Information,"* Feb 2026. 222M trades with observable terminal payoffs.
Retail traders pick winners **51.3%** of the time (barely above coinflip) yet **lose
money**; automated traders are only coinflip-accurate (50%) yet earn **$133M**.
Directional and execution skill are **nearly orthogonal, shared variance <1%** for
humans (replicates in CBOE equity options; the accuracy-profitability *inversion* itself
does not replicate there, "bounding it to single-margin markets"). The paper additionally
argues negative cross-skill correlations reported elsewhere in equity-decomposition
literature are a *measurement artifact* of shared-benchmark construction.

**Verdict:** strong independent support for the project's working explanation of *why*
naive skill-selection keeps failing to beat matched/placebo comparison groups (pass-2
`A8`-`A11`, `A4`) — because profitability is driven by execution, nearly orthogonal to
directional accuracy. **No other paper found** reporting the specific empirical pattern
itself ("a matched/activity-controlled comparison group matches or beats a
naively-selected 'skilled' group") in prediction markets or sports betting — two
targeted searches came back empty, reported as empty rather than papered over.
Independent support for the *mechanism*, no independent replication found of the
*pattern* in a different dataset.

### B5. `is_taker` structural explanation — NOT CONFIRMED, a plausible partial complication surfaced
Could not reach Polymarket's own primary technical documentation on this specific point
(the official docs page for order creation does not cover settlement-transaction
attribution; a Medium deep-dive on CLOB V2 mechanics 403'd). From secondary/aggregator
sources only (**explicitly flagged as such**): Polymarket's matching is off-chain
(operator), settlement on-chain via Polygon, and — importantly — "you do not pay gas per
fill — the protocol's relayer infrastructure batches and pays the on-chain cost... without
you submitting a transaction per trade." **This is not a clean confirmation** of the
project's specific hypothesis (`built_b7`: "the taker's wallet sends the settling
transaction; a resting maker order may never generate one of its own") — if a relayer
batches and submits on behalf of both sides, the simple taker-sends-it story is at least
incomplete, and the real explanation for why the project's per-trade-hash detection
method sees zero makers may lie in how transaction hashes get attributed in the
relayer's batched submissions, not in a maker/taker on-chain asymmetry per se.
**Verdict: UNCONFIRMED / possible partial complication** — flagged, not resolved, given
no primary source was reachable.

---

## JOB C — what the project has never considered

### C1. UMA optimistic-oracle vote concentration
WSJ investigation (May 2026, **secondary source** — no academic primary found): top 10
wallets cast >50% of dispute votes; ~60% of active UMA voters linkable to Polymarket
trading accounts; ~1 in 5 disputes had a voter with an open position in the market being
judged; 1,150+ disputed markets in 2026 (already exceeding full-year 2025), ~$5B at
stake across ~2,000 contracts. Baseline dispute rate ~1.5% of all proposals (general UMA
mechanism docs). Relatedly, *"Prediction Laundering: The Illusion of Neutrality,
Transparency, and Governance in Polymarket"* (arXiv:2602.05181) argues decentralization
is partly illusory — $750 dispute bonds gate participation to a narrow actor class.
**Measurability:** **not measurable with current assets** — no UMA voter/wallet
identity data in the project's DB; `infra_o2` (canonical resolution write path)
captures resolution provenance for only 3/13 migrated writers and has no vote-level
detail.

### C2. Mitts & Ofir wallet-level informed-trading screen
Found via search, primary paper (Columbia Law, cited, not independently fetched —
**flagged**): composite of cross-sectional bet size, within-trader bet size,
profitability, pre-event timing, and directional concentration, applied to 210,000+
wallet-market pairs, 93,000+ markets, 2023-early 2026. **69.9% win rate on flagged
trades, >60 SD above null under permutation test, ~$143M aggregate anomalous profit.**
Iran-strike case study: 6 new wallets, Yes shares at $0.10, ~$1.2M profit within hours.
**Measurability: measurable with current assets** — every input feature (bet size,
profitability, pre-event timing, directional concentration) is derivable from `data_d1`
(trades) + `data_d2` (positions); this is a direct, larger-scale generalization of the
project's own LH-001 (pass-2 `C8`, currently stalled at n=2 events).

### C3. "Ghosts of Polymarket" — off-chain/on-chain settlement mismatch
arXiv:2606.16852: off-chain matching engine confirms a fill that then reverts
on-chain — a settlement-layer inefficiency, not a pricing one. Effect size not
extractable from the fetch (PDF compression, **flagged**). **Measurability: not
measurable with current assets** — the project's `trades` table (`data_d1`) presumably
records only settled trades; no evidence of revert/failed-match data being captured
anywhere in pass 1's inventory.

### C4. Optimal market making in binary-settlement markets
arXiv:2607.17991, July 2026: stochastic-control framework for binary-settlement market
making, distinct from classical continuous-asset market making. No prediction-market-specific
numerical edge reported in the available summary. **Measurability: partially
measurable** — would need `data_d4` (order_book_snapshots, 3.57% coverage — already
known-limited per pass 1) to apply; effectively not measurable at any useful coverage.

### C5. Polymarket CLOB v2 upgrade and maker-rebate program (April 28 2026)
**A mid-project structural change the corpus (pass 1/2) never mentions.** $1M
maker-rebate program funded by taker fees. **Measurability: measurable with current
assets, and cheaply** — `data_d1` (trades) has timestamps, so a simple before/after
split at 2026-04-28 against `is_taker` (`built_b7`, pass 1: zero maker rows
database-wide) would test whether the rebate program produced any maker-side rows
post-upgrade — a concrete, low-cost check the project's own assets can already run,
bearing directly on `built_b7`'s known-limits and Job B §5's unresolved structural
question.

### C6. Fee-figure discrepancy — flagged, not resolved
External sources describe Polymarket fees generically as "~2% on winning positions"
(one blog) and Kalshi as "up to 3% taker." The project's own cost floors (`instr_v8`,
per pass-1 citing `MASTER_HANDOVER_2026-08-15.md` §5) state Geopolitics is fee-free
(spread-only 0.0005-0.010) and Elections carries a 4% feeRate (~0.0097 at median price
0.59). **Not obviously reconcilable** from what this search surfaced — could be
category-specific fee schedules, a fee-structure change coincident with CLOB v2, or an
imprecise external source. Flagged, not resolved.

### C7. Cross-platform price relationships (Kalshi/Polymarket)
**Only blog/secondary sources found** (predictionmarketspicks.com, PredTerminal,
ClawArbs, launchpoly.com) — **explicitly flagged**, no academic primary source located.
Reported gaps of ~13 cents gross, persisting minutes to hours, closing to ~7-8 cents net
after Kalshi's ~2¢/contract/side fee; execution window compressed from "~5 minutes in
2024" to "~30 seconds in 2026" as bot competition increased (unverified, blog-sourced
claim). A genuine academic primary source exists on a related question — *"Semantic
Non-Fungibility and Violations of the Law of One Price in Prediction Markets"*
(arXiv:2601.01706, Gebele & Matthes) — but the fetch returned unparseable compressed
content; only the abstract-level topic is confirmed, no effect size obtained.
**Measurability: not measurable at all** — the project has zero cross-platform data
(confirmed absent from pass 1's entire asset inventory); would require wholly new data
acquisition from Kalshi/PredictIt/Manifold.

### C8. Time-series/momentum effects — largely empty
**Largely empty for prediction-market-specific work.** General financial-market
momentum/mean-reversion/order-flow literature exists in depth but nothing
prediction-market-specific with a reportable effect size was found. This is itself
information: no one has published a "volume precedes price" or momentum-decay finding
for Polymarket/prediction markets specifically that this search could locate. If it
were measurable, `data_d1` (trades, full tape) would support it — but there is no
external claim to test against.

### C9. Wash-trading network-detection study (Columbia)
Sirolly, Ma, Kanoria, Sethi — SSRN 5714122, Nov 2025, network-based detection: **~25%
of all Polymarket trades 2022-2025 estimated as wash trades**; 14% of 1.26M wallets
exhibit wash-trading-consistent behavior; wash-trading share peaked near **60% of
weekly volume in December 2024** (43,000-wallet coordinated network), largely
incentive-farming-motivated (no real profit), not fee-evasion.
**Measurability: measurable with current assets** — `data_d1` (trades) has the
counterparty/wallet-pair structure needed for network-clustering detection; the
project's existing bot detection (Pattern A/B/C in `daily_maintenance.py`'s ARB_BOT
step, per pass 1) is a **methodologically distinct, non-network-based method** — a
different approach the project could in principle benchmark against, using data it
already has.

### C10. "Fill-Side Non-Retail Trading on Polymarket"
arXiv:2605.11640: behavioral-tier classification of market-makers/arbitrageurs/
non-retail liquidity providers via microstructure signatures, using the external PMXT
v2 archive (April 21-27 2026 window). Full text not extractable (fetch failed, **flagged**),
no effect size confirmed. **Measurability: partially measurable** — the classification
concept could in principle be attempted on `data_d1`/`data_d2`, but the project has no
existing instrument that does this (its `bot_type` tagging — ARB_BOT/LP_ARTIFACT — is a
coarser, different classification) — new method-building, not applying an existing
validated instrument.

### C11. ILS papers (cross-reference with Job A)
arXiv:2605.02287 and arXiv:2605.00493 (see Job A §A2/A1) substantively answer the
project's own never-run RQ-ILS-001 — surfaced independently by this Job C sweep too,
confirming the finding rather than being a duplicate coincidence. Effect sizes: skilled
accounts + market makers (<3.5% of accounts) capture >30% of platform gains; a related
lifecycle-and-conviction heuristic flags 1,950 accounts, mean profit $15,012.92.
**Measurability: measurable with current assets** — `data_d1` + `instr_v3` (`price_at()`)
are sufficient to construct a per-market ILS on this project's own population.

### C12. Della Vedova follow-up — flagged, unverified
*"Detecting Informed Trading in Prediction Markets: One Event at a Time"* (SSRN
6567238), found as a listed follow-on to the project's already-foundational SSRN
6191618, but the fetch returned HTTP 403 — could not confirm method or effect size
independently this pass. Flagged as existing but unverified.

---

## Contradictions / notable cross-references

- **B1 (calibration shape) is the pass's headline conflict** — see top of document.
- **A4 (RQ-SECTOR-001) and B1 share the same source paper** (arXiv:2602.19520) —
  the category-specific calibration-dynamics question and the domain-specialization
  question are two facets of the same external work, not independently verified twice.
- **A2/A8 (RQ-ILS-001, RQ-SCI-001) and C11 converge**: three separate sweeps (Job A
  twice, Job C once) independently located the same Nechepurenko research program,
  strengthening confidence these are real, substantive external answers rather than a
  single fork's search artifact.
- **B4 and C9/C2** together suggest a pattern: where the project's own naive-selection
  approach failed (falsified selectors, pass-2 `A8`-`A11`), published work using
  *composite, conditioned* signals (bet size + timing + profitability + concentration,
  jointly) succeeds at finding informed trading (C2, C9-adjacent). This is reported as
  an observation connecting existing findings, not a proposal — pass 4's territory.

---

## What this pass did NOT cover

- Full-text extraction of arXiv:2602.19520's complete Polymarket-only horizon table
  (PDF compression-blocked; only partial HTML-rendered figures recovered for Politics/
  Kalshi).
- Independent primary-source verification of SSRN 6617059 and SSRN 6191618 (both
  403'd) — all figures for these two foundational papers come from secondary summaries,
  flagged throughout.
- Full text of arXiv:2601.01706, arXiv:2606.16852, arXiv:2605.11640, and the Della
  Vedova follow-up (SSRN 6567238) — all fetch-blocked or compression-encoded.
- Confirmation of the Polymarket fee-schedule discrepancy (C6).
- Any search beyond arXiv/SSRN/exchange docs and a small number of secondary
  aggregators — no attempt to survey conference proceedings, working-paper archives
  outside these venues, or non-English-language literature.

---

## What this pass did NOT do (by design, per scope)

No ranking, scoring, or proposal of next steps (pass 4/5). No measurement was re-run
against project data. Nothing was modified or written to any production table. The
project corpus itself was not re-read beyond what was needed to cross-reference against
passes 1 and 2, which remain the project-side record.
