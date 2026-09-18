# Methodology Extraction — the Three Foundational Papers, Read Properly

**Date:** 2026-09-18
**Depends on:** Pass 1 (asset inventory, `1bb36e1`), Pass 3 (external research, `9efc118`), Pass 5
(shortlist, part of the same 2026-09-12 sequence). Asset IDs (`data_d1`, `instr_v7`, ...) refer to
Pass 1. This is a different kind of pass from Pass 3: Pass 3 gathered findings (effect sizes,
verdicts). This pass reads three specific papers deeply and produces **implementation
requirements** — what this project would need to actually replicate or adapt each method, not a
restatement of headline numbers.

**Scope discipline:** no measurement was run against project data, nothing was implemented, the
2026-09-12 shortlist was not reordered and no shortlist item was started, nothing was written to
any production table.

---

## Flagged prominently, per instruction — a real contradiction with the project's prior citations

**Paper 2 (Gómez-Cram et al.) was reached in PRIMARY form for the first time, and three figures
this project has been citing secondhand are measurably wrong against the current primary text:**

| Figure this project cited (secondhand, via SSRN Blog / Yale Insights) | Primary-text value (78-page PDF, "This version: June 25, 2026") |
|---|---|
| "10,000-simulation coin-toss benchmark per trader" | **B = 1,000** simulations. "10,000" does not occur anywhere in the paper's full text. |
| "44% of traders classified skilled ... also classified that way in the second [half]" | **46%** (same quantity, same table). Likely version drift — the secondary sources summarized the original April 20, 2026 SSRN posting; the PDF obtained here is a June 25, 2026 revision. |
| "~3.14% of accounts ... persistently-skilled" | **3.16%** (Table 1, benchmark specification, consistent throughout the paper). Small, plausibly also version drift or press rounding. |

None of these are large enough to overturn any conclusion this project has drawn (the CI
comparisons in Pass 3 §B2 were already framed as "not directly comparable" for independent
reasons, which still holds and is now sharper — see Paper 2 below). But per the task's own stop
condition, a paper's actual method differing from how the project has been citing it reaches
committed findings, and both the 10,000→1,000 and 44%→46% deltas do exactly that. **Any
downstream document that repeats "10,000 simulations" or "44%" for this paper is now citing a
superseded or incorrect figure and should be corrected against the June 25, 2026 PDF.**

The other two papers produced no comparable contradiction — see per-paper sections. Mitts &
Ofir's previously-cited headline figures (69.9% win rate, >60 SD, ~$143M, 210,000+ wallet-market
pairs) were independently corroborated by four additional academic sources in this pass, not
contradicted.

---

## Access summary

| Paper | SSRN ID | Access status | Route |
|---|---|---|---|
| Mitts & Ofir, "From Iran to Taylor Swift" | 6426778 | **SECONDARY ONLY** | SSRN itself confirmed Cloudflare-blocked (403 via both WebFetch and raw `curl -I`, ruling out a tool-specific block). Best sources reached: four independent arXiv papers (2605.02286, 2605.02287, 2605.00459, 2605.00493) that read and cite the working paper closely enough to quote its methods; Harvard Law School Forum on Corporate Governance repost; Columbia Law School news article. The actual PDF/HTML was never obtained. |
| Gómez-Cram, Guo, Jensen & Kung, "Prediction Market Accuracy" | 6617059 | **PRIMARY** | SSRN itself still 403'd. Reached via co-author Howard Kung's personal working-papers page (Google-hosted PDF link), which is not blocked. Full 78-page PDF obtained and text-extracted. |
| Della Vedova, "Who Profits from Prediction Markets?" | 6191618 | **SECONDARY ONLY** (author-authoritative for method mechanics, ordinary secondhand for magnitude figures) | SSRN 403'd on every route tried, including the follow-up paper SSRN 6567238. Best source reached: the author's own public GitHub reproduction repo (`github.com/jdellavedova/polymarket-index`), which contains code and a companion methodology.tex that mirror and cite the paper's own analysis by exact script/line number. This is author-authored, code-level material — closer to primary than a blog summary, but not the paper's own prose/tables/robustness section, so labeled secondary throughout with that distinction preserved. |

**All three SSRN abstract pages remain individually inaccessible to automated fetching**
(Cloudflare-gated, confirmed via both the tool and raw `curl`), consistent with Pass 3's finding.
The improvement this pass made was in finding better routes AROUND SSRN, not through it — a human
with an SSRN login, or a different network path, would likely succeed where this pass's automated
routes did not for two of the three.

---

## PAPER 1 — Mitts & Ofir, composite informed-trading screen

**Access: SECONDARY ONLY.** Never reached the paper's own text. All figures below sourced from
four independent academic papers that engaged with it directly (cited inline), plus the Harvard
Law Forum repost and Columbia's own news coverage. Authors confirmed: Joshua Mitts (Columbia Law
School) and Moran Ofir (University of Haifa), released ~2026-03-16.

### 1. The permutation test — UNRESOLVED, the decisive open question

No source reached — including four papers by people who read the actual working paper closely
enough to critique its design — specifies what is permuted, what is held fixed, or the
permutation count. The most specific available language (arXiv 2605.00459) says only that flagged
wallet-market pairs show "joint anomalies in size, timing, profitability, and directional
concentration relative to a permutation null" — confirms a permutation null exists, gives no
mechanics.

**Important disambiguation, stated because it would be an easy mistake to make:** Gómez-Cram et
al. (Paper 2, below) uses a well-documented, genuinely activity-matched sign-randomization null
(event-level Rademacher flips, holding fixed which events/markets each account traded). Because
both papers are permutation-based and appeared close together, it would be easy to assume Mitts &
Ofir's null works the same way. **No source states that it does.** These are two different papers
with two different, independently-designed null constructions, and only one of the two (Gómez-Cram)
is confirmed activity-matched.

**Answer to the project's own question:** cannot determine, from any source reached, whether
Mitts & Ofir's permutation null controls for a wallet's baseline trading-activity level. Genuinely
unknown, not "probably yes by analogy."

### 2. Composite construction — named, not specified

Consistently described as combining the five inputs "into a single statistic" / "single anomaly
score" (arXiv 2605.02286, 2605.00459). No source specifies whether it's a weighted sum, a rank
aggregation, or a fitted model, nor whether any weights are estimated or assigned. **One
unsourced numeric weighting (25%/20% split) surfaced during this pass's own search process and is
explicitly flagged as unreliable** — it appeared with no corresponding snippet or source link
anywhere in the result set, and none of the four academic papers that engaged with the actual
working paper mention any specific weight. Do not treat that figure as real.

### 3. Component definitions

- Cross-sectional bet size, within-trader bet size, directional concentration: named consistently,
  never mathematically defined in anything reached. A Herfindahl-style (HHI) concentration measure
  appears in two of the citing papers, but explicitly as **those papers' own** feature, not
  attributed to Mitts & Ofir — do not assume Mitts & Ofir's "directional concentration" is
  HHI-based.
- Pre-event timing: named only, no window length or anchor point found anywhere.
- **Profitability — the one component with a clear, repeated characterization across three
  independent sources: it is computed retrospectively, using the market's actual resolved
  outcome, not out-of-sample.** Direct language: "computed retrospectively on resolved markets...
  by construction prevents real-time application" (2605.02286); "profitability is only known at
  resolution... does not separate skill from luck explicitly" (2605.00459); "rely on... features
  (such as profitability) that are observable only after resolution" (2605.00493). This is the
  same structural shape as the circularity concern this project's own selection work has run
  into — not confirmed identical, but structurally adjacent, and worth treating as a real caution
  rather than dismissing.

### 4. Within-trader vs. cross-trader

A wallet/trader-flagging tool: it identifies specific (wallet, market) pairs as anomalous based on
that wallet's own multi-factor profile, explicitly contrasted (in the same sources) against
market-level tools like the ILS family that flag markets rather than wallets. Because it is
retrospective and resolution-dependent, no source positions it as a "copy this trader going
forward" tool either — it is explicitly described as unsuited to any real-time use.

### 5. Sample, period, population

Reasonably consistent across 4+ sources: >210,000 flagged wallet-market pairs (one source gives
210,718 exactly), >93,000 distinct markets, ~50,000 unique wallet addresses. One unresolved
discrepancy: start date is given as "February 2024" by two sources (Harvard blog, Columbia news)
and as "2023" by implication in another — not resolved from any source reached, flagged rather
than picked.

### 6. What they control for / acknowledge

Best single source (Harvard blog, itself a summary, not the paper): "we cannot observe the full
portfolio of any given trader" and "cannot rule out the possibility that we are identifying
unlikely coincidental patterns rather than genuine exploitation of material nonpublic
information." Independently, two academic papers characterize the profitability-dependence
described in §3 as a design limitation (not real-time-deployable), though not necessarily
self-described that way by the authors themselves.

### Implementation requirements

- **What this project would need:** the exact permutation mechanics and the exact composite
  construction/weighting rule — **neither is recoverable from any source reached in this pass.**
  Everything else (which raw features feed the score) is already known and buildable.
- **Pass-1 assets supplying each input:** `data_d1` (trades — bet size, pre-event timing,
  directional concentration all derivable), `data_d2` (positions — profitability). `instr_v6`
  (`match_control()`) would be required regardless of what Mitts & Ofir's own null does, per the
  point below. `instr_v5` (clustered bootstrap) for any CI construction.
- **What is missing:** the actual scoring algorithm. Because it cannot be reconstructed, any
  project version of this screen would not be a *replication* — it would be an independently
  *designed* composite inspired by the same five named inputs, which is a materially weaker and
  different claim than "applying Mitts & Ofir's method."
- **Implementable status: PARTIALLY IMPLEMENTABLE.** The input features are fully constructable
  (as Pass 3 already found); the actual selection algorithm is not reconstructable and would have
  to be built from scratch.

---

## PAPER 2 — Gómez-Cram, Guo, Jensen & Kung, persistent skill

**Access: PRIMARY.** Full 78-page PDF obtained (June 25, 2026 revision — later than the April 20,
2026 date press coverage was written against). Authors: Gómez-Cram, Guo, and Kung at London
Business School; Jensen at Yale University (corrects this pass's initial guess of Boston College
for Gómez-Cram — not a contradiction of any prior project citation, just a correction to this
pass's own working assumption).

### 1. The randomized-direction null

Randomizes **trade direction (buy/sell sign) at the EVENT level** — one Rademacher ±1 draw per
event, applied to *all* of that trader's trades within that event simultaneously. Explicitly
**not** trade-level (would overstate independent bets by splitting one position into many) and
**not** market-level (would split correlated same-event positions, e.g. "Trump wins"/"Harris
loses," into separate bets that are actually the same bet). Held fixed: trade sizes, prices paid,
market outcomes. Statistic: realized PnL vs. a **mid-p** estimator of the simulated-PnL
distribution (Lancaster 1961; Routledge 1994), chosen specifically to handle ties from
discreteness. **B = 1,000** simulations per account (Monte Carlo draws, not exhaustive
enumeration) — see the contradiction flagged at the top of this document.

**On the pinning/floor problem this project hit (0.00067 floor, 12.5% of traders pinned at 1,500
reps):** the paper addresses a version of this, but not via a pinning-incidence diagnostic. They
note the true p-value is combinatorially bounded to `[2^-(E+1), 1−2^-(E+1)]` given E events, and
**truncate at that trader-specific bound** rather than reporting values outside it. They chose the
10-event minimum specifically so `2^10 = 1,024 > B = 1,000` — i.e., so the event count, not the
simulation count, is no longer the binding resolution constraint (footnote 4). **The paper does
not report what fraction of traders are pinned at the empirical p-value floor** — this project's
own 12.5%-pinned diagnostic has no analogue in the source paper to compare against.

### 2. Minimum event counts

**≥10 EVENTS** per trader (their unit is events, not positions or trades — this matters because
this project's own M≥10 threshold is stated in *positions*, a different unit; the two are not
confirmed equivalent without knowing this project's events-per-position ratio). Justified via the
combinatorial-resolution argument above, plus a general power argument. Robustness check at ≥4
events / no filter gives an *identical* classified set to ≥10 events (only the denominator moves,
not the numerator) — because p-values for accounts with <4 events can never reach <0.05 given the
combinatorial bound regardless of filter choice.

### 3. The split-half persistence method — precise mechanics, and the source of the discrepancy

**The split is a fully random draw of each trader's EVENTS into training/test — explicitly NOT a
calendar-time split.** Direct paper language: "We split events randomly rather than by time
because market conditions, including the user base, event types, and liquidity, vary
substantially over the sample period... A random split ensures that both sets contain events
throughout the full sample period and share a comparable user base."

**The persistence figure is a conditional transition probability, not a population share:** it is
`P(classified skilled in test | classified skilled in training)`, read off a row-normalized
transition matrix (Table 3, Panel B) — **46%** (not 44%, see top of document), with the remainder
of the training-skilled row going 22% Lucky, 30% Unlucky, 1% Market-Maker/Anti-skilled. A
secondary rank-correlation statistic is also reported (0.11 overall PnL-rank correlation,
train→test; notably *negative*, −0.12, among training-set winners specifically — profit itself
partially reverses; p-value-rank correlation is smoother at 0.35 overall). Mutual-fund comparison
(Appendix D): 10% of training-skilled funds remain skilled in test (matches this project's cited
"~10% baseline" exactly); 6% for anti-skilled funds (new detail, not previously in this project's
citation).

**Bearing on this project's own 37.0%/18.6% figures:** this project's `instr_v7` test is an
explicit *temporal* split (not the paper's random-event split) and reports a two-group comparison
(a pre-defined skilled cohort vs. a comparison group), not a train→test transition probability of
one group re-classifying itself. These are two axes of difference, both now precisely
characterized rather than assumed: (a) temporal split vs. random-event split — genuinely different
designs, the temporal version is exposed to the regime-change confound the paper's own methods
section explicitly built the random split to avoid; (b) a two-group comparison vs. a
skilled-training→skilled-test conditional transition — different quantities entirely. **Pass 3's
"NOT DIRECTLY COMPARABLE" verdict is confirmed and sharpened, not overturned**, now with the exact
mechanism named rather than inferred.

### 4. The ~3% population figure

Population: all Polymarket, markets created after 2023-01-01, resolved by 2025-12-31. 98,906
events, 210,322 markets, $13.76B volume, 1.72M accounts — all confirmed exactly matching this
project's prior secondhand figures. Filters, in order: (i) market-maker exclusion by *behavior*
(≥100 markets traded, ≥70% volume from limit orders, both-sides-of-an-outcome in ≥70% of markets
— 0.10%/1,660 accounts excluded before classification); (ii) ≥10 events; (iii) p<0.05, two-tailed,
**no multiple-testing correction in the headline specification**. Exact result: 54,325 accounts =
**3.16%** of all 1.72M accounts (rounds to "3%"/"3.2%" in different parts of the paper's own text).

**On the 26.1%-vs-3.16% gap:** across every specification the paper itself reports — including
its most permissive combination (no event filter, no BH correction) — the skilled share ranges
roughly **1.9%–4.8%** of the full population. Nothing in the paper's own reported range approaches
26%. This means the gap is very unlikely to be explained by "the paper uses a stricter numeric
filter than this project does" — the paper's most permissive variant is still an order of
magnitude below 26.1%. The more likely explanation is a difference in population/denominator (this
project's pool may already be pre-filtered to a more-active or research-eligible subset rather
than "all accounts including one-off tourists") or a difference in what the two studies'
underlying skill tests actually measure. **This project's own 26.1% figure should be checked
against what population it is a percentage OF before treating the gap as reconciled or
unreconciled either way** — stated as an open item, not something this pass resolves.

### 5. Multiple-comparisons handling

**Headline/benchmark specification uses no correction**, explicitly acknowledged: "a second
concern is that we apply the test separately to many accounts, which raises multiple-testing
issues... Under the null that no account has skill, about 5% would be flagged as skilled and 5% as
anti-skilled by chance alone." A Benjamini-Hochberg FDR correction is reported as an explicit
robustness check (Table 1, Panel B, applied separately per tail): skilled share drops from 3.16%
to **1.95%** of all accounts at the ≥10-event filter. No Bonferroni anywhere. All of the paper's
substantive price-discovery/persistence results are shown robust across both corrected and
uncorrected classifications (Appendix Table B.1).

### Implementation requirements

- **What this project would need:** already has it — `instr_v7` implements the core
  randomized-direction design. Two precise, adoptable refinements surfaced from primary text: (1)
  the paper randomizes at the **event level**, holding all of a trader's same-event trades to one
  shared sign-flip; this project's harness flips **per-position** (per `instr_v7`'s own
  `validation_detail`) — a finer unit than the source design, potentially overstating independent
  bets in exactly the way the paper's own methods section built the event-level choice to avoid.
  Worth checking, not assumed broken. (2) The paper handles the discreteness/pinning problem via
  mid-p estimation + truncation at `[2^-(E+1), 1−2^-(E+1)]`, not by reporting a pinning-incidence
  diagnostic — this project could adopt the same mid-p/truncation approach as a concrete,
  primary-sourced fix if the 12.5%-pinned-at-floor issue is revisited.
- **Pass-1 assets:** `instr_v7` (the harness itself), `instr_v1`/`instr_v2` (PIT reconstruction
  feeding its cohort), `instr_v5` (clustered bootstrap, referenced but not this paper's own CI
  method).
- **What is missing:** nothing structural — this is the one paper of the three the project already
  has a working, validated instrument for. What's open is unit-of-randomization confirmation and
  whether to adopt mid-p/truncation.
- **Implementable status: IMPLEMENTABLE HERE — already implemented.** Not a shortlist action;
  `S3-8` (the current #1 shortlist item) builds on `instr_v7`'s existing cohort without needing to
  touch the underlying randomization design.

---

## PAPER 3 — Della Vedova, direction/execution decomposition

**Access: SECONDARY ONLY, but with a quality gradient worth preserving.** The paper's own PDF was
never reached (SSRN 403, including the follow-up paper SSRN 6567238). The best source obtained is
the author's own public GitHub reproduction repository (`github.com/jdellavedova/polymarket-index`),
which contains code (`build_fair_prices.py`, `rebuild_history.py`) and a companion methodology.tex
that explicitly mirror and cite the paper's own analysis by exact private script and line number
(`05_return_decomposition.py:76-140`). This is author-authored, code-level material — labeled
**SECONDARY-BUT-AUTHORITATIVE** below for items sourced from it, distinct from ordinary secondhand
material (press, blogs, the author's public dashboard) used for items 2 and 4. Author confirmed:
Joshua Della Vedova, University of San Diego.

### 1. How the decomposition is computed [secondary-but-authoritative]

An **exact per-trade algebraic identity**, not a regression or residual estimate. For each matched
fill: `sign = +1` if the maker's side is BUY else `-1`; `W` = the token's realized terminal payoff
(binary, 0 or 1 — the actual settlement, not a probability); `P` = execution price; `Q` = quantity;
`F` = a fair-value benchmark (see item 3).

- **Directional P&L** = `sign × (W − F) × Q`
- **Execution P&L** = `sign × (F − P) × Q`
- **Total P&L** = `sign × (W − P) × Q` = Directional + Execution **by algebraic construction**, not
  a fitted decomposition.

So directional skill is a dollar-weighted deviation of the realized outcome from a price-implied
benchmark (not a raw win-rate, though a separate quantity-weighted accuracy statistic is also
reported alongside it for descriptive purposes — this is where the 51.3%/49.9% figures come from).
Execution skill is measured directly from its own primitives (distance of `P` from `F`), not
derived as "whatever's left over" after accounting for accuracy, even though the two sum to total
P&L by identity.

**Structural detail:** the paper's own academic analysis is **maker-only** — only the maker-side
leg of each matched fill is scored for a given wallet. The GitHub repo's public dashboard departs
from this (mirrors values onto the taker side for a zero-sum display) but the paper itself does
not.

### 2. The independence claim ("<1% shared variance") [mixed]

Characterized, via the companion methodology.tex, as a **population-level** claim — correlation
**across wallets** (do directionally-skilled wallets also tend to be execution-skilled wallets),
not a within-trader-over-time claim. The follow-up paper (the Private Information Index) is
explicitly built to detect *violations* of this population-level near-orthogonality for specific
flagged wallets — confirming the unit of analysis is per-wallet aggregates, correlated across the
trader population. "Shared variance" implies an R²/ρ² measure. One unreliable secondary figure
(ρ≈0.13, implying ~1.7% shared variance) surfaced via an AI-summarized blog fetch and is
inconsistent with the "<1%" claim — not corroborated anywhere else, flagged as unreliable rather
than incorporated. A separate, more specific secondary figure — "<1% for humans, <4% for bots" —
is consistent with and refines this project's existing "<1% ... for humans" framing.

### 3. The execution measure itself [secondary-but-authoritative] — the most consequential finding in this pass

`F` (`fair_price` in the repro code) is a **per-(market, token) volume-weighted average price
(VWAP), computed only over BUY-side trades, from the full resolved trade tape** — i.e., trade-tape
derived, not order-book-, quote-, or model-based, and built from the *same* tape whose quality it
then judges.

**Direct answer to the circularity question this project asked: yes, this appears to have the
same structural problem this project's own fair-price benchmark work ran into and found "partial
and endogenous."** The paper's own introduction (per the companion methodology.tex, citing Fama
1972 and Anand et al. 2012) argues that other equity-decomposition literature's negative
cross-skill correlations are artifacts of trade-sequence-derived benchmarks, and that prediction
markets "solve" this because they settle to a known scalar (0/1) rather than needing a modeled
benchmark. **That argument only holds for the directional leg** (`W` is a real, benchmark-free
terminal payoff). **It does not hold for the execution leg** — `F` is still an in-sample,
trade-sequence-derived VWAP, exactly the kind of endogenous benchmark the paper's own introduction
criticizes in other work.

An analytical note derived during this pass (not sourced from the paper — flagged explicitly as
inference, not fact, for the record): because `F` enters both components with opposite sign
(`W−F` and `F−P`), measurement noise in `F` would mechanically induce a *negative* correlation
between the two measured components. Whether this materially affects the paper's own
near-orthogonality finding is not resolvable without the paper's actual robustness section — an
open question, not a resolved critique of the result, but a real reason not to treat "prediction
markets solve the shared-benchmark problem" as fully settled by this paper.

### 4. The earliness finding [ordinary secondhand]

Multiple independent aggregator sources converge on "bots enter >8 days before resolution, retail
~3 days," with ~70% of bots' advantage attributed to this timing gap. **The precise operational
definition could not be found anywhere reached** — whether "entering" means first trade, largest
trade, or a size-weighted average, nor what the figures are anchored to (market close? resolution?
the underlying real-world event date, which can differ from market close). Genuinely unresolved,
not assumed.

### 5. Does the decomposition require data this project lacks? [secondary-but-authoritative] — direct, plain answer

**Order book: no.** The benchmark is trade-tape-based, not book-based.

**Maker/taker identity: yes, and it is a native field of every Polymarket on-chain fill, not an
exotic requirement.** Per the repo's own data-source documentation: every trade is an `OrderFilled`
event from the CTF/NegRisk Exchange contracts, and "the event log contains the maker address,
taker address, token identifiers, amount traded, and block number." The decomposition code
consumes `maker_address`, `taker_address`, and `maker_side` directly from this source.

**Stated plainly, as instructed: given that this project's `is_taker` field has zero maker-side
rows across 621,350 labeled trades, the decomposition cannot be computed on this project's data
today.** But — and this is new, not previously established — **that is very likely because
whatever process populated `is_taker` failed to capture or preserve maker/taker identity
correctly, not because Polymarket's underlying data structurally lacks it.** A CLOB necessarily has
makers on essentially every matched trade; a 100%-one-sided field across 621K rows is a strong
signal of an extraction/labeling bug, not genuine absence. This changes the shape of the earlier
open question in `built_b7` (Pass 1): the field is described there as "likely structural... root
cause not established, would require inspecting live Polygon receipts." This pass supplies the
missing piece — the raw on-chain event the receipts would need to be checked against
(`OrderFilled`'s `maker`/`taker` address fields) is now named specifically, not just gestured at.

### Implementation requirements

- **What this project would need:** (1) maker/taker identity re-derived from raw on-chain
  `OrderFilled` events — not currently available from `is_taker` in usable form; (2) a buy-side-only
  VWAP fair-price benchmark per (market, token) — a new instrument; `instr_v3` (`price_at()`) is
  related but distinct (a time-indexed lookup, not a buy-side VWAP aggregate) and would not
  directly substitute; (3) terminal payoff labels — available via `data_d3` (markets table,
  resolution status/outcome), subject to `data_d3`'s own known limits (mostly irrelevant to this
  specific use, since resolution outcome rather than category or resolution_date is what's needed).
- **Pass-1 assets:** `data_d1` (trades, for `P`/`Q`/timestamps), `data_d3` (resolution outcome for
  `W`), `instr_v3` (partial — a different instrument than the needed VWAP benchmark, not a direct
  supply).
- **What is missing:** usable maker/taker identity (present in principle, absent in the project's
  current extraction — an actionable, scoped gap, not a dead end); the buy-side VWAP benchmark
  instrument itself, which does not yet exist in any form.
- **Implementable status: NOT IMPLEMENTABLE TODAY; PARTIALLY IMPLEMENTABLE if maker/taker is
  re-derived from raw on-chain events.** This is a materially different conclusion than the task's
  own framing assumed going in — not "impossible here," but "blocked on a specific, named,
  previously-uninvestigated data-extraction gap."

---

## THE TWO QUESTIONS THIS PASS EXISTS TO SETTLE

### A. Does Mitts & Ofir's permutation test already do the work an activity-matched placebo does here?

**CANNOT DETERMINE FROM AVAILABLE ACCESS.**

No source reached — including four independent academic papers that read and cited the actual
working paper closely enough to quote its methods — specifies the permutation test's mechanics
closely enough to answer this either way. This is not "probably yes" by analogy to Gómez-Cram's
design; Gómez-Cram is a different paper with an independently-documented, confirmed
activity-matched null, and nothing found here establishes that Mitts & Ofir's null shares that
property.

**What the project's version would need to add, given this:** everything. If `S5-1` (or anything
like it) is ever built, it must construct its own activity-matched placebo from the ground up
(using `instr_v6`'s `match_control()`, exactly as Pass 5's original exclusion already assumed
defensively) rather than inherit any protection from Mitts & Ofir's design, because it is unverified
whether that design provides any. If anything, the newly-confirmed retrospective/resolution-dependent
character of the profitability component (§1.3 above, corroborated by three independent sources)
argues for treating the external paper's own design with *more* caution on this front, not less —
it shares a structural shape with the circularity problem this project's own selection work has
already run into.

### B. Should the 2026-09-12 shortlist ordering change?

**No — the case for changing it is not there, stated plainly rather than left implicit.**

Reviewed against every item this pass could bear on:

- **`S5-1` (Mitts & Ofir composite, excluded from the shortlist):** remains correctly excluded.
  Question A above found no basis to lift the placebo objection that excluded it; if anything the
  in-sample-profitability finding reinforces the original caution.
- **`S1-3` (Gómez-Cram split-half + overlap check, in the not-worth-doing list):** the precise
  mechanics extracted here (random-event split, conditional transition probability, event- not
  position-level randomization unit) make `S1-3` easier to *execute correctly* if it were ever
  chosen, but do not change its decidability or consequence scoring — it remains dominated by what
  `instr_v7` already established, per Pass 5's original reasoning.
- **`S2-2` (maker-labeled trades after the CLOB v2 rebate program, currently #3):** unchanged in
  rank, but the interpretation of a *negative* result is now sharper and different than Pass 3
  speculated. Pass 3's `jobB_5` guessed a relayer-hash-attribution complication as the likely
  explanation if `is_taker=0` stays zero post-rebate. This pass's Della Vedova extraction supplies
  a more specific, more checkable alternative: maker/taker identity is a native field of every
  Polymarket `OrderFilled` event, so a persistent zero most likely indicates an extraction bug in
  how this project's writers parse or attribute those on-chain fields — not a payment-incentive or
  relayer-batching story. **This does not change `S2-2`'s cost, decidability, or where it sits on
  the list** — it is still the same hours-scale query with the same two-way-informative payoff —
  but whoever runs it next should know the more specific, more likely follow-up if the result comes
  back negative.
- **Everything else on the shortlist (`S3-8`, `S2-1`, `S3-1`, `S5-2`):** none of the three papers'
  extracted methodology bears on these items' assets, decidability, or consequence in any way this
  pass surfaced.

**Stated as the case, not a recommendation to act on it:** the single most consequential new fact
in this entire pass — that maker/taker identity is a recoverable, native on-chain field rather
than a structurally absent one — does not correspond to any item currently on the shortlist. It
bears on `built_b7`'s open question (Pass 1) and on whether Della Vedova's full decomposition is
someday buildable, neither of which is a shortlist item. Nothing extracted here argues for adding,
removing, or reordering anything on the 2026-09-12 list.

---

## What this pass did NOT do (by design, per scope)

No measurement was run against project data. Nothing was implemented. The 2026-09-12 shortlist was
not reordered and no shortlist item was started. Nothing was modified or written to any production
table. `metric_v2f_oos_result` was not touched (this pass did not open the database at all).
