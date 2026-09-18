# Component Validation — What Gómez-Cram/Della Vedova Work Would Rest On

**Date:** 2026-09-18
**Depends on:** the 2026-09-18 methodology extraction (`6c9f2d9`), pass 1 asset inventory
(`1bb36e1`), the 2026-09-05 timing/execution inventory and execution-signal-feasibility docs.

**Scope discipline:** nothing found broken was fixed. `timing_score` was not recomputed by this
pass (Part 4b cites an existing, already-committed recomputation-check from 2026-09-05, not a new
one run here). `is_taker` was not backfilled. No research measurement was run. No canonical
definition or harness was modified. Nothing was written to any production table.
`metric_v2f_oos_result`'s canonical hash reconfirmed unchanged: `021be40a...4cd4e`. Part 1 used 3
external API calls total: 1 to `data-api.polymarket.com/trades` (limit=8), 2 to Alchemy's Polygon
RPC (`eth_getTransactionReceipt`).

---

## Reported at the top, per the stop condition — Part 1 finds is_taker IS recoverable, but not the way it was believed to be

**The inherited explanation ("the CLOB taker sends the settling transaction; a resting maker
order may never generate one of its own") is wrong, or at least not the operative cause.** The
real mechanism is different, evidenced directly (not inferred), and it changes which research
branches exist: Della Vedova's decomposition is not "structurally blocked," it is **blocked on a
specific, scoped data-acquisition gap that would require new engineering, not a config fix.** See
Part 1 in full below.

---

## PART 1 — is_taker: extraction bug or structural absence?

### Where it's populated, in code

Two independent writer scripts, exactly as Pass 1 found:

- **`scripts/polygon_maker_taker.py`** — receipt-based. `extract_maker_taker()` (lines 102-157)
  fetches `eth_getTransactionReceipt` for a trade's stored `transaction_hash`, reads the
  `OrderFilled` event's `topics[2]` (maker) and `topics[3]` (taker), and does a literal string
  match against the trader's own address:
  ```python
  maker_addr = "0x" + topics[2][-40:]
  taker_addr = "0x" + topics[3][-40:]
  real_taker = taker_addr.lower() != exchange
  if taker_addr.lower() == trader and real_taker: is_taker_in_tx = True
  if maker_addr.lower() == trader: is_maker_in_tx = True
  if is_taker_in_tx: return "taker"
  if is_maker_in_tx: return "maker"
  ```
  Write: `UPDATE trades SET is_taker = ? WHERE trade_id = ?` (line 235).
- **`scripts/polygon_event_scanner.py`** — `eth_getLogs`-based, symmetric by design:
  `get_logs_for_trader()` (lines 236-278) runs two separate log filters — one with the trader's
  address padded into `topics[2]` (maker role) and one with it in `topics[3]` (taker role) —
  tagging each returned log `role="maker"` or `role="taker"` before the caller assigns
  `is_taker = 1 if role == "taker" else 0` (line 381). Write: `UPDATE trades SET
  transaction_hash = ?, is_taker = ? WHERE trade_id = ?` (lines 422-427), gated on finding a
  **pre-existing** `trades` row to attach to (exact tx-hash match, or a ±30s fuzzy-timestamp
  match for the same trader) — **there is no INSERT path anywhere in this function.** A genuine
  on-chain maker event that has no matching row in `trades` is found, counted in
  `stats["events_found"]`, and then silently discarded.

### What the API actually exposes — verified directly, not assumed

Made one live call to `data-api.polymarket.com/trades?limit=8` and inspected every field on 8 real
records. **Full field list: `proxyWallet, side, asset, conditionId, size, price, timestamp,
title, slug, icon, eventSlug, outcome, outcomeIndex, name, pseudonym, bio, profileImage,
profileImageOptimized, transactionHash`. No `maker`, `taker`, or role field exists anywhere in
this response.** `side` is BUY/SELL — the reporting wallet's own order direction, not a
maker/taker role indicator. All 8 records had distinct `transactionHash` values, each attributed
to exactly one `proxyWallet` — the feed does not emit one row per counterparty to a fill; it
attributes each transaction to a single wallet.

This is the field `monitoring/monitor.py` actually consumes: `trade_id =
trade.get('transactionHash') or trade.get('id')`, `trader_address = trade.get('proxyWallet')`,
`transaction_hash = trade.get('transactionHash', '') or None` (lines 950, 937, 960). This is the
path that populates the overwhelming majority of the 14.9M-row `trades` table (the live 15-minute
monitor). **The maker/taker labeling scripts operate on `transaction_hash` values that arrived
via this feed — they never independently discover a transaction; they only ever look up the
receipt for a hash the API already attributed to one specific wallet.**

Made two live `eth_getTransactionReceipt` calls (Alchemy RPC) for two real, labeled
(`is_taker=1`) trades from the DB. Both receipts contain **multiple `OrderFilled` logs per
transaction**, with our tracked wallet appearing as **taker in one leg and maker in another leg of
the same transaction** (e.g., TX `0x064a0c82...`: wallet `0xeaa35c...` is taker in log `0x42b`
against a different counterparty, and maker in log `0x42f` against counterparty
`0xe2222d27...` — the transaction's own `to` address, i.e. the exchange/settlement contract
itself acting as the internal counterparty for a settlement leg). This confirms directly: **the
on-chain data genuinely distinguishes maker and taker roles per log, correctly, for every
participant in a transaction — including our tracked wallets, when they do appear as maker in an
internal settlement leg.**

**A separate, previously-undocumented code defect, confirmed but not central**:
`polygon_maker_taker.py`'s `EXCHANGE_CONTRACT` constant is hardcoded to
`0xe111180000d2663c0091e4f400237545b87b996b`. Both real transactions inspected here settle through
a *different* on-chain address, `0xe2222d279d744050d28e00520010520000310f59` (this transaction's
own `to` field). Because `real_taker = taker_addr.lower() != exchange` checks against the wrong
hardcoded constant, the script's intended filter ("don't count the exchange contract itself as a
real taker counterparty") silently fails to recognize this second contract as an exchange/internal
leg. In the two cases inspected, this did not flip the final label (the trader was independently a
genuine taker in another leg of the same transaction, and taker-check runs first), but it is a
real, confirmed bug worth naming.

### The actual causal chain — established, not inherited

1. **Root cause, upstream of any labeling code**: the public `/trades` feed (source of ~99% of
   this project's trade rows) attributes each transaction to exactly one wallet, with no
   maker/taker field. Empirically (2/2 checked), that wallet is the transaction's on-chain
   **taker**. A trader's maker-side fills are therefore **never inserted as a `trades` row in the
   first place** by the live monitor — this is a data-acquisition gap, not a mislabeling of rows
   that do exist.
2. `polygon_maker_taker.py` backfills `is_taker` only for rows that already exist — which, per
   (1), are already taker-biased before it ever runs. Its own logic is structurally sound (the
   `EXCHANGE_CONTRACT` bug aside) but operates on an input set that cannot contain much maker
   activity to find.
3. `polygon_event_scanner.py` correctly queries on-chain logs for BOTH roles symmetrically and
   **can and does find genuine maker-role events** for tracked wallets — but has no code path to
   insert a new row for an event that doesn't match an existing `trades` row, so anything it finds
   that the live monitor never captured is discovered and then thrown away.

**Net: 0% maker is not a labeling bug in the sense the project previously believed ("the taker
sends the transaction"), and it is not genuinely structurally absent either (the on-chain data
carries full role information for every participant, confirmed directly). It is a data-acquisition
gap — this project's trade-ingestion pipeline structurally only ever creates a row for a trader's
taker-side activity, and the one script that could find the missing maker-side activity on-chain
has no way to persist what it finds.**

### Recoverability, and cost

**Not recoverable** by re-running the existing backfill scripts against existing rows — bounded,
and blocked further by the `EXCHANGE_CONTRACT` bug for complex/multi-leg settlement transactions.

**Recoverable, with new engineering**, via:
- A direct on-chain sweep (`eth_getLogs`, `topics=[ORDER_FILLED_TOPIC, None, padded_address]` for
  the maker role) per flagged trader — `polygon_event_scanner.py`'s `get_logs_for_trader()`
  already implements exactly this query; the missing piece is an **INSERT path** (not just
  UPDATE) for maker-fill events found on-chain that have no existing `trades` row.
- A maker-side fill's on-chain log gives addresses and token amounts, but **not** directly the
  price/market/outcome fields the `trades` schema expects — reconstructing those would require
  decoding the transfer amounts against the market's token IDs (nontrivial, a real build item, not
  a one-line addition).
- Scale: 14.9M existing trades total, of which only 2,718,718 (18.2%) carry a `transaction_hash`
  at all, and of those, 1,991,455 have never been through `is_taker` labeling (`is_taker IS NULL`)
  — a substantial existing backlog even before considering the maker-side gap. `polygon_event_scanner.py`
  itself estimates real per-trader RPC cost (block-range chunking, ~2×`RATE_LIMIT_SLEEP` per chunk)
  — scanning the full flagged-trader population for maker-role history would be a genuine
  multi-day-to-multi-week engineering and RPC-cost effort, not a quick fix.

**This changes the Della Vedova verdict from "structurally uncomputable" to "not computable today,
computable with a scoped, non-trivial data-acquisition build."**

---

## PART 2 — the directional-skill harness against the primary source

Code read: `scripts/directional_skill_diagnostic.py` (the base module, `REPS=1500`,
`sign_flip_null()`, `classify()`, `bh_correction()`, `split_half()`) and
`scripts/directional_skill_persistence_test.py` (the script that actually produced the committed
37.0%/18.6% figures, which overrides `REPS` to 10,000 for that run and does **not** call
`split_half()` at all — it uses a temporal split at `T_SPLIT` instead, comparing a pre-split
BH-skilled cohort's post-split reclassification against a comparison group's).

| Dimension | Gómez-Cram (primary text) | This project | Verdict |
|---|---|---|---|
| Randomization unit | **Event-level**: one Rademacher flip per event, applied to all of a trader's same-event trades together, explicitly to avoid splitting correlated same-event positions into separate bets | **Position-level**: `sign_flip_null()` draws one independent flip per position (`signs = rng.integers(0,2,size=n)*2-1`, `n` = position count) | **DIFFERS-PROBLEMATICALLY.** The paper built the event-level unit specifically to avoid the failure mode this project's implementation has: a trader with multiple positions in the same event gets those positions flipped independently, which can overstate independent "bets" exactly as the paper's own methods section warns against. Affects both the pre-split classification (which determines cohort membership: the 146/607 split) and the post-split reclassification (the 37.0%/18.6% figures themselves) — this is foundational to `instr_v7`, not a footnote. |
| Complementary price | Looked up from the actual paired/complementary market | Derived algebraically as `1 - price` (not looked up) | DIFFERS-DEFENSIBLY — a documented, reasoned simplification stated in the prereg, not a silent difference. Compounds with the row above for same-event positions specifically. |
| Minimum count | **≥10 events**, justified by a combinatorial-resolution argument (2^10 > B) | **≥10 positions** (`M_CHOSEN=10`) | DIFFERS-DEFENSIBLY numerically identical threshold, different unit. The paper's specific combinatorial justification (2^E > B) does not transfer cleanly to positions, since positions aren't independent binary units the way events are when multiple positions can exist per event — not shown to be wrong, just not validated on this project's own terms. |
| Split-half method | Random draw of **events** into train/test | **Not used for the headline 37.0%/18.6% figure** — that comparison is a **temporal** split at `T_SPLIT`, confirmed via direct code reading of `directional_skill_persistence_test.py`'s docstring and `main()`. A separate `split_half()` function exists in the base module (random draw of **positions**, not events) but is not what produced the committed persistence figures. | Already correctly flagged NOT DIRECTLY COMPARABLE by Pass 3 and the 2026-09-18 methodology extraction — confirmed again here from the code itself, precisely: it's not just "temporal vs random," the internal `split_half()` that IS random also uses the wrong granularity (positions, not events) relative to the paper, so even that secondary function isn't a clean analog. |
| Multiple comparisons | BH as an explicit robustness check; headline spec uses no correction | BH used as the **headline** reporting basis throughout | DIFFERS-DEFENSIBLY, and arguably more conservative — this project reports the more conservative of the two approaches the paper itself validates as headline. |
| p-value floor / pinning | Mid-p estimator (Lancaster 1961) + truncation at the combinatorial bound `[2^-(E+1), 1-2^-(E+1)]`; no pinning-incidence diagnostic reported | Standard add-one Monte Carlo estimator `p = (count_null_exceeds + 1)/(reps + 1)`, no mid-p, no truncation | **DIFFERS-PROBLEMATICALLY, confirmed directly against the actual committed artifact, and worse than previously documented.** See below. |

### The p-value floor — checked against the actual result artifact, not assumed

Read `data/characterizations/directional_skill_persistence_20260906T195734Z.json` — the artifact
that produced the committed **37.0% [29.45%, 45.21%] vs 18.6%** figures — directly. At
`post_split_reps=10000` (floor = 1/10001 ≈ 0.0001):

- **Cohort (n=146): 35 traders (24.0%) pinned at the floor.**
- **Comparison (n=607): 52 traders (8.6%) pinned at the floor.**

This is a different, and for the cohort **worse**, number than the previously-cited "~0.00067 at
1,500 permutations, 12.5% pinned." Tracing that figure: it comes from a **different, earlier
stage** — the pre-split PIT-legal-pool classification (`data/characterizations/directional_skill_pit_legal_pool_20260906T160303Z.json`,
n=5,732, `reps=1500`, floor=1/1501≈0.000666): `pinned_at_floor_rate: 0.1249` — exactly the 12.5%
figure, but this is the step that determines **cohort membership**, not the post-split persistence
step that produces 37.0%/18.6%. **Both stages have real pinning, and the later, higher-REPS stage
that produces the headline number is not the better-behaved one for the cohort specifically.**

**What this does and does not threaten, stated plainly**: pinning limits the *precision* of a
pinned trader's p-value (we know it's ≤ the floor, not how far below), not necessarily their
pass/fail BH classification — a trader pinned at the extreme low end of 10,000 draws is
overwhelmingly likely to also be BH-significant at any reasonable threshold regardless of exactly
how far below the floor their true p-value sits. The asymmetry itself (24.0% cohort vs 8.6%
comparison) is **consistent with, not contradictory to**, genuine skill persistence — the cohort
was selected for extreme pre-split skill, so more of them landing at an extreme post-split value
too is the expected shape if the hypothesis is true, not a red flag on its own. **This finding does
not, on the evidence gathered here, invalidate the qualitative direction of the 37.0%/18.6% result
or the CI-excludes-zero primary-axis conclusion (A1).** It is, however, a real and previously
under-examined precision limitation — nobody had checked pinning incidence at the REPS=10,000
configuration that actually produced the committed number before this pass — and it means a
meaningful fraction of the reported p-values (and by extension, some of the BH-correction rank
ordering near the boundary) rest on a coarser measurement than the headline figures imply.

---

## PART 3 — the 26.1% vs 3.16% discrepancy

Read `data/characterizations/directional_skill_pit_legal_pool_20260906T160303Z.json` directly.
**The 26.1% figure is the RAW (uncorrected) skilled rate**: 1,494 raw-skilled / 5,732 classifiable
traders = 26.06%. The **BH-corrected** rate on the same population is 1,178/5,732 = **20.55%** —
a figure the project has not previously put alongside Gómez-Cram's corresponding numbers.

**The comparison as previously framed is not like-for-like — it compares two different
denominators.** Gómez-Cram's cited 3.16% is skilled-count **over the full 1.72M-account
population**. Their own methodology text gives the filtered-population figure directly: 54,325
skilled / ~629,000 accounts meeting the ≥10-event filter = **8.63%** (raw), and 33,522/629,000 =
**5.33%** (BH-corrected) — both recoverable exactly from the primary-text figures already
extracted (33,522 = 1.95% of all 1.72M ⇒ full population ≈1.719M ⇒ 33,522/629,000=5.33%; same
check for the raw figure).

**Comparing on the same basis (skilled-rate among the classifiable/filtered population only):**

| | Raw (uncorrected) | BH-corrected |
|---|---|---|
| This project (PIT-legal pool, Geo/Elec, M≥10 pre-split positions) | 26.06% | 20.55% |
| Gómez-Cram (all Polymarket, ≥10 events) | 8.63% | 5.33% |
| **Ratio** | **~3.0x** | **~3.9x** |

**Not eightfold — roughly three-to-four-fold**, once the denominators are matched. Ruled out as an
explanation for the remaining gap: the choice of correction (BH vs raw) — the gap persists at a
similar order of magnitude under either convention, so multiple-testing-correction choice is not
the driver. Also checked and not a likely driver: alpha-per-tail convention — Gómez-Cram's own
text ("about 5% flagged skilled AND 5% anti-skilled by chance alone") implies the same one-tailed
5%-per-direction convention this project's `classify()` uses (`skilled = actual > null_p95`), not
a stricter combined two-tailed 5% total.

**What plausibly explains the residual ~3-4x**: this project's population is restricted to
Geopolitics + Elections markets specifically, excluding the high-frequency, low-research-intensity
categories (crypto up/down, sports, pop-culture) that make up a large share of Gómez-Cram's
all-Polymarket population. A genuinely more skill-differentiated subpopulation in
research-intensive categories is a plausible, substantively different explanation from "the two
numbers aren't comparable" — but **this is stated as a plausible candidate, not a confirmed
finding.** It would need a category-matched or time-window-matched re-computation of Gómez-Cram's
own method to confirm, which this pass did not run (out of scope).

**Answer to the task's framing**: closer to "the two numbers measure different things" (a
denominator mismatch, now corrected) than to "the filter genuinely concentrates skill eightfold" —
but a real, smaller (~3-4x) gap remains after correcting the denominator, and that residual gap
*could* still represent genuine, prospectively-useful filter concentration. Not established either
way at the ~3-4x level; the ~8x framing specifically is not supported once like-for-like
denominators are used.

---

## PART 4 — the execution-timing instruments

### 4a. Entry-to-resolution lag, tape_end-anchored

**This instrument, as described in the task ("100% coverage, zero negative-lag artifacts"), was
not found to exist anywhere in this codebase.** Confirmed directly (grep across `monitoring/`,
`analysis/`, `scripts/` for entry-to-resolution/lag-related terms) and independently corroborated
by the committed 2026-09-05 timing-execution-inventory document's own finding: **"No
market-open/listing timestamp exists anywhere... Nothing in the ELO/edge pipeline computes
[entry-to-resolution lag]."**

The one thing that resembles it — `scripts/detect_insider_activity.py`'s `s4_days_before_resolution`
signal (part of a separate, narrow live insider-detection loop, not a general skill/edge
instrument) — is **not** tape_end-anchored and does **not** use the canonical `backtest_window_sql()`.
Read directly (lines 223-259): it queries `SELECT resolution_date FROM markets WHERE market_id = ?`
and computes `days_before = (res_dt - trade_dt)` from that **raw** column. Pass 1 already documents
`markets.resolution_date` as ~11% logically-impossible values, with `tape_end` established as the
validated workaround specifically because of this defect — a defect this specific signal does not
route around. **This is a direct, concrete instance of the "documented history of scripts
bypassing the canonical function" the task asked about.**

**Verdict: NOT FIT FOR PURPOSE, and more precisely: does not exist as an instrument at all.** No
recorded coverage or negative-lag-artifact claim for a tape_end-anchored version was found
anywhere; the only present analog inherits a known ~11% data-quality defect and was never built to
route around it.

### 4b. timing_score (Component 3, relative entry percentile)

Code read: `analysis/trading_behavior_analysis.py:443-605`, `calculate_timing_quality()`. Confirmed:
relative entry percentile among all traders in the same market (`timing_score = 1.0 -
avg_percentile/100`), using raw `MIN(timestamp)` from the `trades` table directly — no `tape_end`,
no canonical population function. Two structurally different ways to land at exactly `0.5`: (i) a
genuine median-timing computation, and (ii) the explicit fallback path when fewer than 3
same-market entrants exist — **these are indistinguishable from the stored value alone.**

**This pass did not recompute anything new** — it cites the existing, already-committed
recomputation check from `2026-09-05-execution-signal-feasibility.md` §2a, which re-derived
`calculate_timing_quality()` live (unmodified) against a random sample of 300 of the then-8,372
traders stored at exactly 0.5:

- **297/300 (99.0%): confirmed FALLBACK** — genuine contamination.
- **1/300 (0.3%): genuine tie** — a real market qualified and recomputed to exactly 50.0.
- **2/300 (0.7%): STALE/DRIFTED** — recomputation produced neither the fallback nor 0.5, but a
  *different* value entirely (0.256 and 0.462 in the two cases found). **This is the figure the
  present task cites** — it means the stored column has drifted from what the live function would
  produce today for at least some non-fallback traders too, a third failure mode beyond simple
  fallback contamination.

Population-wide contamination has nearly tripled since the original Stage 0b check: 21.2%
(8,372/39,465, as of 2026-09-05) vs 7.25% (1,541/21,249, as of 2026-07-12) — driven by
`resolution_sweep.py` adding thin, single-event traders who structurally can't clear the ≥3-entrant
filter.

**Cohort-specific state is materially better than the population-wide figure**: of the 169-trader
Track2/directional-skill-adjacent cohort, only 1 trader sits at 0.5 (confirmed fallback via direct
recomputation), and that trader has **zero** OOS positions — contamination touches **none** of the
cohort's 3,795 OOS positions. The real completeness gap for this specific cohort is 10 `NULL`-valued
traders covering 54/3,795 positions (1.4%).

**Verdict: split by scope.** VALID WITH CAVEATS for the specific, already-defined 169-trader Track2
cohort (contamination is not a live problem for those positions; a small 1.4% NULL-coverage gap
remains). **NOT FIT FOR PURPOSE at the general population level** without a fresh, full
fallback/genuine/stale reclassification first — both because of the now-21.2% contamination rate
and because the newly-confirmed stale/drifted failure mode means even non-0.5 stored values cannot
be trusted as current without individual verification.

---

## PART 5 — price_at() for execution benchmarking

Two distinct instruments, two distinct and different limitations, both already independently
established and reconfirmed by reading the source docs directly:

- **`price_at()` (`instr_v3`)**: PROVEN on the primary CLOB source, but only 73.1% cross-source
  stratified agreement against a 90% pre-registered bar (Pass 1) — degrades specifically for
  **old/thin markets** (a market-level, not trader-level, axis of degradation).
- **The trade-tape fair-price benchmark** (the candidate Della Vedova-style execution benchmark,
  from `2026-09-05-execution-signal-feasibility.md` §1a-1d): explicitly **endogenous** by the
  document's own honest characterization — built from nearby trades in the same tape it's meant
  to judge — and **degrades specifically in the high-volume tercile**, confirmed across all three
  tested windows (±1h, ±6h, ±24h): the high-volume tercile has the *lowest* mean density of nearby
  comparison trades at every single window, not a noisy or window-specific effect. **This is
  exactly the subpopulation where the project's own research cohort concentrates** — the traders
  a skill/execution test cares about most are the ones this benchmark supports least well.

The only non-endogenous alternative identified anywhere in the corpus — B4/`data_d4` order-book
mid-price — covers 3.57% of Geopolitics+Elections markets and has **zero overlap** with the
research cohort (confirmed independently by both Pass 1 and the 2026-09-05 inventory).

**Stated plainly, per instruction: this project cannot construct a defensible, non-endogenous
execution-quality benchmark for the population where it matters — the endogenous benchmark is
weakest exactly where the cohort concentrates, and the clean alternative doesn't cover the cohort
at all.** Any execution-quality claim built on the trade-tape benchmark would be measuring
execution quality against a standard partially contaminated by the same informed trading it's
trying to net out, for precisely the highest-volume, most research-relevant traders. This
constrains what any execution test can honestly claim, independent of whether `is_taker`
(Part 1) is ever recovered — recovering maker/taker identity would let the *direction/execution
split itself* be computed, but would not, on its own, fix the benchmark's endogeneity problem for
the execution leg specifically (as the 2026-09-18 methodology extraction's Della Vedova section
already found: the paper's own `F` benchmark has this same structural issue).

**Verdict: NOT FIT FOR PURPOSE** for a rigorous execution-quality benchmark on the cohort that
matters, using anything currently in this project's data. Fit only for a benchmark on
low-to-moderate-volume subpopulations where nearby-trade density is adequate, which is not where
the project's own skill-persistence cohort lives.

---

## Verdict summary

| Component | Verdict | What it would take to change the verdict |
|---|---|---|
| `is_taker` / maker-taker identity | **NOT FIT FOR PURPOSE today; recoverable with new engineering** | An on-chain `eth_getLogs` sweep (extending `polygon_event_scanner.py`'s existing maker-role query) with a genuine INSERT path for previously-uncaptured maker fills, plus price/market reconstruction from decoded on-chain amounts. A real, scoped, multi-day-to-multi-week build, not a config change. |
| Directional-skill harness (`instr_v7`) | **VALID WITH CAVEATS** | Randomization unit differs from the primary source (position- vs event-level) — a foundational, not cosmetic, difference. p-value floor pinning is real and worse than previously documented (24.0% cohort / 8.6% comparison at the actual headline REPS=10,000 configuration), though it does not appear to flip the qualitative 37.0%/18.6% direction on the evidence gathered here. |
| 26.1% vs 3.16% comparison | **NOT LIKE-FOR-LIKE AS PREVIOUSLY FRAMED; corrected figure is ~3-4x, not ~8x** | A category- or time-window-matched re-derivation of Gómez-Cram's own method on this project's population would be needed to confirm whether the residual ~3-4x is genuine filter concentration or a further unmatched variable. |
| Entry-to-resolution lag (tape_end-anchored) | **NOT FIT FOR PURPOSE — does not exist as described** | Would need to be built from scratch, anchored on `tape_end` via the canonical population function, not on raw `resolution_date`. |
| `timing_score` | **VALID WITH CAVEATS for the 169-trader Track2 cohort; NOT FIT FOR PURPOSE at the general population level** | A full DB-wide fallback/genuine/stale reclassification (the 2026-09-05 doc already demonstrates this is tractable at small-sample scale; scaling it DB-wide is the remaining work) before treating any general-population `timing_score` value as trustworthy without individual verification. |
| Execution-quality price benchmark | **NOT FIT FOR PURPOSE for the cohort that matters** | Either meaningfully expand B4/order-book coverage into the research cohort's markets, or accept an explicitly-labeled endogenous benchmark with the tercile-degradation caveat stated alongside any result that uses it. |

---

## What was not determined

- Whether the `EXCHANGE_CONTRACT` hardcoding bug in `polygon_maker_taker.py` ever flips a final
  `is_taker` label from "taker" to something else in any real case DB-wide — only 2 transactions
  were inspected directly; both happened to have the trader as a genuine taker in another leg
  regardless, so the bug's net effect there was zero, but this was not checked at scale.
- Whether the p-value floor pinning identified in Part 2 changes any specific trader's BH
  pass/fail classification near the decision boundary — argued as unlikely (pinned traders are, by
  construction, at the extreme low end) but not individually verified against a
  higher-precision (e.g. higher-REPS or analytic) re-classification, which would be a research
  measurement and is out of this pass's scope.
- Whether the residual ~3-4x gap in Part 3 (after denominator correction) reflects genuine
  category-driven skill concentration or a further, unidentified population difference — stated as
  a plausible, unconfirmed candidate only.
- What fraction of the 1,991,455 `transaction_hash`-having-but-unlabeled trades, if run through
  the existing (bug-fixed) labeling scripts, would resolve to maker vs taker — not estimated, since
  doing so would require running the scripts, out of scope.
- Whether `timing_score`'s STALE/DRIFTED failure mode (Part 4b, 0.7% of the 2026-09-05 sample) has
  grown or shrunk since that check, given the population-wide 0.5-contamination rate has nearly
  tripled since Stage 0b — not re-checked here, since doing so would require the recomputation this
  pass was explicitly scoped not to run.
