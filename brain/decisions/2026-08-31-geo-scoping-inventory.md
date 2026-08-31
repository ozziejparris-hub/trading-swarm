# Geopolitics/Elections Scoping Mechanisms — Full Inventory

**Date:** 2026-08-31. **Scope:** read-only. Build nothing, change nothing, recommend
nothing — the recommendation comes after this is read.
**Why:** at least five geo-scoping mechanisms have been rediscovered separately over
the last month, each treated as new. This is all of them, side by side, with their
dependency graph, their disagreements on live data, the history of what was built and
abandoned, and coverage against the current sweep-classification problem.
**Tagging:** `[V]` verified this session (read the file / queried the DB / read git);
`[I]` inferred. Every claim in the task prompt was treated as a hypothesis.

Repos: `first-repo` = `/home/parison/projects/first-repo`; `swarm` =
`/home/parison/trading-swarm`. DB = `first-repo/data/polymarket_tracker.db`.

---

## VERDICT (Part 4c up front)

**One authority, documented and enforced: `markets.category`.** Everything else is
either an *input* that writes it, a *derived mirror* of it, a *trader-scoped* metric
built on top of it, or a *coarse keyword re-derivation* that never writes back.

**No existing mechanism is a usable relevance filter for the remaining sweep.**
The column-based ones (`markets.category`, `trades.market_category`, the v2f/backtest
predicates, the Pool-C / geo_elo family) return **0** on Unknown markets by
construction — that is the problem, not a solution. The keyword INCLUDE filters
(37-keyword, `GEOPOLITICS_SIGNALS`, `CATEGORY_TAG_MAP`) select 1.3–3.8 % of the
Unknown backlog but over-select true geo/elec by 2–3× (substring false positives:
`war`→"Warsaw"/"Warriors", `policy`, `china`→"China Grand Prix", `strike`→sports) and
none of them is a *classifier* — each still needs a decision step (LLM, human, or the
source category) behind it. The one exclusion-only filter (`_is_geopolitics` in
`detect_insider_activity.py`) passes **87 %** of the Unknown backlog as "geo" and is
unusable as a relevance filter. The only components that actually decide geo-vs-not
are the two LLM paths (monitor's Mistral gate, `backfill_market_categories.py`'s
Qwen) and the source category (Gamma `event.category`) — and the source category
already ran on these markets and left them Unknown. **A relevance filter for the
remaining sweep does not exist today in reusable form.** Whether the answer is
re-running an existing classifier on the right scope or building something new is the
open question this document is written to inform — not answered here.

---

## PART 1 — THE INVENTORY

### A. MARKET-scoped mechanisms (classify a *market* as geo/elec)

| # | Mechanism | Where | What it does | Built | Status | Read/used by |
|---|---|---|---|---|---|---|
| **M1** | **`markets.category`** (column) | `markets.category TEXT`; written by M3–M10 | The canonical per-market category string. **792,792 rows: 778,986 `Unknown` (98.3 %), 7,937 `Elections`, 4,030 `Geopolitics`**, plus legacy stragglers (`US-current-affairs` 386, `Global Politics` 58, `Ukraine & Russia` 46, `Politics` 1). | column exists by ~Dec 2025 `[V]` (CATEGORY_BUG_FIX.md 2025-12-04) | **LIVE — the authority** | `column_definitions.py` §1 & §6, `trader_skill_metric_v2/v2f`, `update_geo_elo.py`, `legendary_positions_scan.py`, `audit_invariants.py`, `sync_trade_categories.py`, ~30 `characterize_*`/`verify_*` scripts |
| **M2** | **`trades.market_category`** (column) | `trades.market_category TEXT`; written at ingest by `monitor.py:921`, then **overwritten daily** by `sync_trade_categories.py` from M1 | Denormalized per-trade copy of M1. `sync_trade_categories.py` (daily_maintenance step "Sync trade categories --incremental") does `UPDATE trades SET market_category = m.category WHERE t.market_category != m.category`. | column ~Dec 2025; sync script later | **LIVE — derived mirror, kept identical to M1 daily** | `backfill_market_dates.py --geo-only`, `detect_insider_activity.py:514`, `calibrate_composite_threshold.py`, `quarantine_o37_synthetic_markets.py`, `update_geo_elo.py` (partial), swarm `trader-intelligence-agent` template |
| **M3** | **Gamma `event.category` → `GAMMA_CATEGORY_MAP`** | `monitor.py:34–42`, applied `:877–878`, `:911`, `:921`; mirrored in `swarm/scripts/market_filter.py:23` | Reads Polymarket **Gamma `/events` `event.category`** (refreshed on startup + every 10 monitor cycles into `_event_category_map`), maps 6 source values → internal 2-value: `Geopolitics`→Geopolitics, `Elections`→Elections, `Global Politics`/`Ukraine & Russia`/`US-current-affairs`/`Politics`→Geopolitics. **The primary writer of M1 for live-monitored markets.** | Nov 2025 origin; map refined over time | **LIVE** — Gate 0 of market ingest | writes M1 & M2 |
| **M4** | **`HARD_INCLUDE_CATEGORIES` / `HARD_EXCLUDE_CATEGORIES`** frozensets | `monitor.py:27–33`; `market_filter.py:20–26` | Tag-first keep/drop before keyword or AI. INCLUDE = {Global Politics, Ukraine & Russia, Geopolitics, Elections}. EXCLUDE = {Sports, Crypto, Pop-Culture, NBA Playoffs, Chess, Art, NFTs, Olympics, Poker}. | Nov 2025 | **LIVE** | market ingest gate; `market_filter.should_include_market` |
| **M5** | **`monitor.py._keyword_exclusion_check`** — ~150 exclusion keywords + regex | `monitor.py:366–585` | Exclusion list: title contains any of ~150 sports/crypto/entertainment/gold/stock keywords → EXCLUDE; otherwise keep. **This is the ORIGINAL Nov-2025 mechanism** ("eliminate sports and crypto prices … keep geopolitics, economics, policy"). | 2025-11-14 → 2025-11-30 `[V]` | **LIVE** — fallback gate when M3 has no category | market ingest |
| **M6** | **`monitor.py._ai_categorization_check`** — local **Mistral** (Pydantic AI) | `monitor.py:289–345` | LLM prompt returns `KEEP` (geopolitics/economics) or `EXCLUDE`. Cached (`ai_cache`). Active in `AI_FILTER_MODE = "hybrid"` (current setting). Local model — **no Claude cost**. | Nov/Dec 2025 | **LIVE** (hybrid mode) | market ingest |
| **M7** | `monitor.py` regex pattern detection (esports / sports-spread / gold-range) | `monitor.py:586–650`; copied in `market_filter.py:302–395` | Regex catches structured non-geo patterns keywords miss; a `_geo_guard` / `geo_context` sub-list re-includes titles with election/president/etc. context. | Nov 2025+ | **LIVE** | market ingest; `market_filter` |
| **M8** | **`swarm/scripts/market_filter.py` `should_include_market()`** | `swarm/scripts/market_filter.py` (whole file) | Standalone **no-AI verbatim copy** of M4+M5+M7 plus a 26-keyword `GEOPOLITICS_SIGNALS` INCLUDE fast-path. `should_include_market` = Gate1 exclusion (M5/M7) → Gate2 geo-signal include. Header: **"Last synced from monitor.py: 2026-05-02"** — has not been re-synced since. | forked 2026-05-02 `[V]` | **LIVE but STALE** (frozen at May-2026 monitor.py state; drifted from M5/M6/M7 since) | `run_feedback_loop_agent.py:349` (weekly); RQ2.2 / RQ3.2 quant-research one-offs; `tests/test_market_filter.py` |
| **M9** | **`backfill_market_categories.py`** — 37-keyword `KEYWORD_FILTER` + Qwen3-Coder LLM | `first-repo/scripts/backfill_market_categories.py:31–38` (list), `:98` (SQL), `:117–184` (LLM) | 37-keyword INCLUDE prefilter on `title` → batches of 20 to local **Ollama Qwen3-Coder 30B** → writes only `confidence=HIGH` + `Geopolitics`/`Elections` to M1 **and** M2. Runs `--limit 50/day` in daily_maintenance. Local model — no Claude cost. (Full behaviour analysed in `2026-08-30-category-classifier-investigation.md`.) | **2026-06-02** `[V]` (`cbd322a`) | **LIVE** (daily, ~19 markets/day classified) | writes M1 & M2 |
| **M10** | **`backfill_missing_markets.py` `CATEGORY_TAG_MAP`** — ~30 keyword→category dict (12 geo/elec keys) | `first-repo/scripts/backfill_missing_markets.py:27–55` | Keyword→category map (`politics/election/president/congress/senate`→Elections; `geopolitics/war/conflict/ukraine/russia/israel/nato`→Geopolitics; also Economics/Crypto/Sports keys) applied when inserting backfilled markets (`data_source='background_backfill'`). | ≤ 2026-06-25 `[V]` (`3617361`) | **LIVE but effectively inert** — of 253,008 `background_backfill` markets, **252,864 are still `Unknown`** (map rarely fires) | writes M1 |
| **M11** | **`detect_insider_activity.py._is_geopolitics`** + `EXCLUSION_KEYWORDS` (~50) | `first-repo/scripts/detect_insider_activity.py:39–82`; used `:409`, `:524` | Exclusion-only: title matching none of ~50 sport/crypto/entertainment/religion keywords → treated as geo. Header: **"inline copy from monitor.py"** — an older, smaller snapshot of M5. Used only as a **secondary guard** after a SQL `tr.market_category IN ('Geopolitics','Elections')` filter (M2) already scoped the set. | copy of an early monitor.py state `[I]` | **LIVE** as secondary guard (`score_insider_signals` in daily_maintenance) | insider-signal scoring only; does **not** write M1/M2 |
| **M12** | **`backfill_market_dates.py --geo-only`** predicate | `first-repo/scripts/backfill_market_dates.py:186–208`, `:381` | Optional flag: restrict date-backfill candidates to markets having ≥1 trade with `t.market_category IN ('Geopolitics','Elections')` — i.e. scoped via **M2, not M1** (the 2026-08-21 "`--geo-only` finding"). | ~2026 H1 | **DORMANT** — flag + code path exist; **dropped from the daily invocation on 2026-08-21/22** (first-repo `5fcbffe`, "discovery-gap closure step 2"). `daily_maintenance.py:402` comment: "`--geo-only` dropped … full population stays." Not invoked by any live scheduler. | nothing live; documented as *not* equivalent to the discovery-gap population (`2026-08-21` decision docs) |
| **M13** | **`legendary_positions_scan.py` `GEO_CATEGORIES`** | `first-repo/scripts/legendary_positions_scan.py:66` | `('Geopolitics', 'Elections', 'Global Politics')` — a **3-value tuple** (the only mechanism that still reads `Global Politics`, which M3 now folds into Geopolitics; 58 legacy rows carry it). Reads M1. | ~2026 | **LIVE** (weekly cron Mon 07:30) | its own positions-scan JSON output |
| **M14** | **`build_event_cluster_labels.py` `FAMILY_PATTERNS`** — ~26 hand-written regex | `first-repo/scripts/build_event_cluster_labels.py:105–170` | A **one-time human hand-labeling pass (2026-07-24)** of election *event families* (CA top-two primaries, 2nd-round runoffs, seat/coalition thresholds, date-band families) for B5 event-clustering, against the frozen `bt_pop_2025-11-01_v1` snapshot — which is already M1-geo-filtered. Labels family membership, **not** geo-relevance. | 2026-07-24 `[V]` | **DEAD / one-off** — single labeling pass, never re-run | `event_cluster_labels` table (B5) |

### B. TRADER-scoped mechanisms (classify a *trader's* geo relevance — Part 2d)

**These do not classify markets.** They measure whether a *trader* has traded/performed
on markets already classified geo by M1. Conflating them with market scoping is the
category error the prompt warns about.

| # | Mechanism | Where | What it is | Derives from |
|---|---|---|---|---|
| **T1** | `geo_resolved_trades_count` (column) | `column_definitions.py:51–59` `GEO_RESOLVED_TRADES_COUNT_SQL` | `COUNT(DISTINCT market_id)` of a trader's won/lost trades on **M1-geo** markets, gap-excluded. No price filter (canonical). | **M1** |
| **T2** | `geo_elo` / `geo_elo_active` (columns) | `update_geo_elo.py` (writer); `compute_geo_elo_active()` `column_definitions.py:163` | 6-dimensional ELO computed **only over M1-geo qualifying trades**; `_active` applies time-decay `geo_elo × 0.5^(days_dormant/180)`. | **M1** (via `update_geo_elo`'s `m.category IN (...)` qualifying filter, lines 86/105/130/263) |
| **T3** | `geo_accuracy_pool` = **Pool C** (column) | `column_definitions.py:104–116` `POOL_C_GATE_WHERE` / `POOL_C_POPULATE_SQL`; `refresh_pool_c()` | `geo_accuracy_pool = 1` iff `geo_elo NOT NULL AND geo_elo_active ≥ 500 AND geo_resolved_trades_count ≥ 10 AND geo_directionality_score NOT NULL AND bot_type IS NULL AND not wash/bot-suspect`. | **T1 + T2** → M1 |
| **T4** | **LEGENDARY** tier / `LEGENDARY_GATE_WHERE` | `column_definitions.py:123–128`; `derive_tier()` `:194` | `geo_elo_active ≥ 2175 AND geo_accuracy_pool = 1 AND research_excluded = 0 AND bot_type IS NULL`. | **T3 + T2** → M1 |
| **T5** | ELITE / QUALIFIED / NEAR_LEGENDARY / DEVELOPING tiers | `derive_tier()` `column_definitions.py:194–228` | `geo_elo_active` thresholds (2175/1800/1400/1000); ELITE & QUALIFIED need no pool membership. | **T2** → M1 |

### C. METRIC-pipeline predicates (all read M1 directly)

| # | Mechanism | Where | Predicate |
|---|---|---|---|
| **P1** | `BACKTEST_WINDOW_BASE_WHERE` (Section 6) | `column_definitions.py:469–471` | `m.resolved = 1 AND m.category IN ('Geopolitics','Elections') AND (m.trade_gap_flag = 0 OR IS NULL)`. Population windowed on `tape_end` (event-time). Structural self-test `:659–662` **asserts** the generated SQL contains `m.category IN (...)` and does **not** contain `trades.market_category`/`tr.market_category`. |
| **P2** | `trader_skill_metric_v2f.py` | `:208, :243, :324, :481` | `m.category IN ('Geopolitics','Elections')`; additionally splits fee-free Geopolitics vs ~4 % feeRate Elections for cost-floor. Imports the `v2 → v2c → v2d → v2e` chain. Built **2026-08-15** (`eaeabbc`). |
| **P3** | `trader_skill_metric_v2.py` | `:97, :192, :213` | `m.category IN ('Geopolitics','Elections')`; explicit comment: *"markets.category, never the denormalized [trades] column"*. Built 2026-08-15 (`5e93131`). |
| **P4** | ~30 `characterize_*` / `verify_*` / `audit_invariants` / `discovery_gap_*` scripts | various | all `m.category IN ('Geopolitics','Elections')` (a handful also/instead use `tr.market_category IN (...)` — kept equivalent by M2's daily sync) |

---

## PART 2 — HOW THEY RELATE

### 2a. Dependency graph

```
        Polymarket source
   ┌───────────┴────────────┐
Gamma event.category   market title text
   │ (M3)                    │
   ▼                         ├─► M5 keyword-exclusion (orig. Nov-2025)
GAMMA_CATEGORY_MAP           ├─► M6 Mistral KEEP/EXCLUDE (local LLM)
M4 HARD_INCLUDE/EXCLUDE      ├─► M7 regex patterns
   │                         ├─► M9 37-kw prefilter → Qwen LLM
   └──────────┬──────────────┴─► M10 CATEGORY_TAG_MAP (near-inert)
              ▼
        ╔═══════════════╗
        ║  M1 markets.  ║ ◄──── THE ROOT / AUTHORITY
        ║  category     ║
        ╚═══╤═══════╤═══╝
   daily sync│       │
      ▼      │       ├──────────────► P1 BACKTEST_WINDOW_BASE_WHERE ─► P2/P3 v2f/v2
   M2 trades.│       ├──────────────► P4 (~30 analysis scripts)
  market_cat │       ├──► T1 geo_resolved_trades_count
      │      │       ├──► T2 geo_elo / geo_elo_active
      │      │       │        └──► T3 geo_accuracy_pool (Pool C)
      │      │       │                 └──► T4 LEGENDARY / T5 tiers
      │      │       └──► M13 legendary_positions_scan (+ literal 'Global Politics')
      │      │
      ▼      ▼
   M8 market_filter.py  ◄─ verbatim fork of M4/M5/M7 @ 2026-05-02 (never re-synced)
   M11 _is_geopolitics  ◄─ older inline fork of M5
   M12 --geo-only       ◄─ reads M2 (dormant)
        (M8/M11/M12 are SIDE re-derivations — they never write back to M1)
```

- **`markets.category` (M1) is the single root.** Every trader-scoped column (T1–T5)
  and every metric predicate (P1–P4) derives from it. `[V]`
- **M3–M10 are inputs** that write M1 at ingest/backfill time. **M2 is refreshed *from*
  M1 every day** by `sync_trade_categories.py`. `[V]`
- **M8, M11, M12 are the "rediscovered" ones** — they are independent keyword
  re-derivations that read a title (M8/M11) or M2 (M12) and are consumed by one
  narrow caller each; **none writes back to M1**, so they can and do drift from it. `[V]`
- `geo_accuracy_pool` does **not** derive from `markets.category` "independently" — it
  derives from it *transitively* through `geo_resolved_trades_count` and `geo_elo`,
  both of which filter on `m.category IN ('Geopolitics','Elections')`. `[V]`

### 2b. Where two mechanisms could disagree — quantified on live data

Populations: **clob-resolved Unknown** = 214,516 markets (the swept backlog);
**unswept Unknown** = 353,047 markets (`resolved = 0/NULL`, category `Unknown`).
Keyword counts are `LOWER(title) LIKE` approximations — they **over-count** via
substrings (`war`⊂"Warsaw"/"Warriors", `policy`, `china`⊂"China Grand Prix",
`strike`⊂sports). `[V]`

| Pair | Disagreement |
|---|---|
| **M1 vs M2** | **Zero.** 672,845 markets with both populated, 0 disagreements (whole DB). Enforced daily by `sync_trade_categories.py`. `[V]` (also established in `2026-08-30-geo-backlog-and-category-reach.md`) |
| **M1 vs M9's 37-kw prefilter** on clob-Unknown | M1 says 0 geo; the 37-kw filter flags **5,412** as candidates (2.5 %). Of those, prior sampling (`2026-08-30-category-classifier-investigation.md`) put the genuinely geo/elec fraction of clob-Unknown at ~1,000–3,000 → the prefilter **over-selects ~2–3×**. |
| **M1 vs M8 `GEOPOLITICS_SIGNALS`** (include gate only) on clob-Unknown | M1 says 0; `GEOPOLITICS_SIGNALS` flags **8,113** (3.8 %). Even looser than M9 (`policy`, `strike` are broad). |
| **M1 vs M10 `CATEGORY_TAG_MAP`** (title approx) on clob-Unknown | **2,793** (1.3 %). |
| **M1 vs M11 `_is_geopolitics`** on clob-Unknown | M1 says 0; `_is_geopolitics` calls **186,354 (86.9 %)** "geo" — its ~50-keyword exclusion list does not catch crypto up/down, weather, or most sports O/U titles. Complete disagreement; unusable as a positive filter. |
| **M13 (`Global Politics`) vs M1's 2-value output** | 58 markets DB-wide still carry `Global Politics`; M13 includes them, every other consumer (P1–P4, T1) does not. Small but a real live divergence. |
| **M12 (`--geo-only`, reads M2) vs the discovery-gap population it was assumed to equal** | Documented non-equivalence (`2026-08-21` decision docs): `--geo-only`'s `trades.market_category` join produced 360 markets vs 524,410 for the widened query; it was dropped for this reason. |

### 2c. Which is the authority — settled?

**Yes, explicitly and in writing.** `monitoring/column_definitions.py` is declared
*"the single canonical source of truth"* (Integration Contract 18.5.1, module
docstring). Section 6 carries the comment *"category IN (...) reads markets.category —
never trades.market_category (O-2/O-30: the trades-table column is a write-time
denormalization that can lag or diverge …, which is canonical for this purpose)"* and
a **structural self-test** (`:659–662`) that fails the build if the generated SQL
references `trades.market_category`. `trader_skill_metric_v2.py:97` repeats it. So:
**`markets.category` is the authority; `trades.market_category` is explicitly
subordinate; the metric pipeline is locked to `markets.category` by a test.** `[V]`

What is **not** settled anywhere: which mechanism should *populate* `markets.category`
for the Unknown backlog (M3 source-category vs M6 Mistral vs M9 Qwen vs something
new), and whether the keyword forks M8/M11 should exist at all.

### 2d. Trader-relevance vs market-relevance

`geo_accuracy_pool`, `geo_resolved_trades_count`, `geo_elo`, `geo_elo_active`,
LEGENDARY (T1–T5) are **trader-scoped**. They answer *"has this trader traded /
performed on geo markets?"* — where "geo market" is defined **by M1**. They take M1 as
input and cannot classify a market. They must not be used, or cited, as a market
relevance filter. The only market-scoped mechanisms are M1–M14. `[V]`

---

## PART 3 — WHAT THE EARLY WORK ACTUALLY DID

### 3a. The original scoping mechanism (before `markets.category`, before any LLM)

Project initial commit **2025-11-05**. The first scoping work, **2025-11-14 →
2025-11-30** (`6af7150`, `8fc40f5`, `105f11d`, `661bd6e`, and `ENHANCED_FILTERING_ADDED.md`
2025-11-30): an **exclusion-keyword filter in `monitor.py`** = today's **M5**. Its
framing was subtractive, not a positive geo classifier —
*"exclude entertainment, sports, crypto airdrops, and gold price prediction markets
while keeping geopolitics, economics, and policy markets"*, "eliminate 90 % noise",
150+ exclusion keywords + regex. "Geo" meant "whatever survived the exclusion list."
`[V]`

### 3b. Curated list / seed set / source-provided category

- **Source-provided category — used from the start and still used.** By 2025-12-04
  (`CATEGORY_BUG_FIX.md`) the `markets.category` / `trades.market_category` columns
  existed and were populated from Polymarket's own API `category` field (that doc
  shows Elections 499 / Geopolitics 327 / Economics 185). This became **M3**
  (`GAMMA_CATEGORY_MAP` over Gamma `/events event.category`). Never abandoned. `[V]`
- **One curated / hand pass exists: M14** — `build_event_cluster_labels.py`, a
  human-reasoned one-time labeling of ~26 election event families on **2026-07-24**,
  for B5 event-clustering. It labels *family membership within an already-geo
  population*, not geo-relevance, and was never re-run. `[V]`
- **No standalone curated geo market list / seed set / watchlist** was found in either
  repo beyond M14. `[V]` (grep for `seed_market`/`curated`/`manual_categor`/`watchlist`
  → only test fixtures and M14.)

### 3c. What was abandoned, and why

Nothing was cleanly retired — the layers **accreted**, each added because the previous
was insufficient, and most still run:

| Layer | Added | Reason the prior was insufficient | Fate |
|---|---|---|---|
| M5 keyword exclusion | 2025-11 | (original) | still LIVE as fallback |
| M3 source category + M4 hard sets | ~2025-11/12 | keyword list couldn't scale / was noisy | still LIVE, primary writer |
| M6 Mistral KEEP/EXCLUDE | ~2025-12 | keyword + tag still missed vague titles ("Will Australia win?") | still LIVE (hybrid mode) |
| M8 `market_filter.py` fork | 2026-05-02 | swarm agents needed the filter without importing `monitor.py`'s classes / AI | LIVE but **STALE** — "last synced 2026-05-02", never re-synced, silent drift |
| M9 37-kw + Qwen LLM backfill | 2026-06-02 | source category left ~98 % of the historical market table `Unknown` | LIVE, ~19 markets/day (its own throughput problems: `2026-08-30-category-classifier-investigation.md`) |
| M12 `--geo-only` | 2026 H1 | date-backfill wanted to prioritise geo | **DORMANT** — explicitly dropped 2026-08-21/22 (`5fcbffe`) after it was found to scope via `trades.market_category` and not match the intended discovery-gap population |
| M14 hand labels | 2026-07-24 | native neg_risk covered only ~40 % of families; the rest needed the mutual-exclusivity test applied by hand | **one-off**, done, not maintained |

The recurring failure mode is **M8 and M11**: keyword logic copied *by value* out of
`monitor.py` into standalone files, then never kept in sync — which is exactly why
they keep being re-encountered as "new."

---

## PART 4 — COVERAGE AGAINST TODAY'S PROBLEM

**The problem:** `markets.category = 'Unknown'` for 214,516 sweep-resolved (`clob`)
markets and 353,047 unswept (`resolved = 0/NULL`) markets. Which mechanism, applied
today, would classify how many of each as geo/elec?

### 4a & 4b — per-mechanism coverage

| Mechanism | clob-Unknown (of 214,516) | unswept-Unknown (of 353,047) | Notes |
|---|---|---|---|
| **M1** `markets.category` | **0** (0.0 %) | **0** | definitionally — "Unknown" is the absence of a classification |
| **M2** `trades.market_category` | **0** | **0** | mirror of M1; `Unknown` wherever M1 is |
| **M3** Gamma `event.category` | **≈0 additional** `[I]` | unknown without API calls | already ran at ingest on most of these and returned no mappable category → they are `Unknown` *because* M3 had nothing; re-running = live Gamma calls, unproven yield |
| **M9** 37-keyword filter | **5,412** (2.5 %) | **10,526** (3.0 %) | prefilter only — still needs the Qwen LLM behind it to decide; ~2–3× over true geo/elec |
| **M8** `GEOPOLITICS_SIGNALS` include gate | **8,113** (3.8 %) | **16,683** (4.7 %) | include gate only (not applying M8's own exclusion pass); loosest of the include filters |
| **M10** `CATEGORY_TAG_MAP` (title approx) | **2,793** (1.3 %) | **6,217** (1.8 %) | tightest keyword set; still not a classifier |
| **M11** `_is_geopolitics` (exclusion-only) | **186,354** (86.9 %) | **304,200** (86.2 %) | passes almost everything — misses crypto-up/down, weather, most sports; **unusable as a relevance filter** |
| **P1–P4 / T1–T5** | **0** | **0** | all consume M1 |
| **M13** `GEO_CATEGORIES` (+`Global Politics`) | **0** additional | **0** | reads M1; the extra value adds nothing on `Unknown` rows |
| **M12** `--geo-only` | **0** | **0** | reads M2; `Unknown` there too |
| **M6** Mistral / **M9** Qwen (the LLM paths) | not counted — these *decide*, they don't pre-select; M9 already runs at ~19/day and reaches the keyword-filtered slice only | | the only components that actually classify |
| **M14** hand-labeling | n/a — human pass, ~26 families, not a filter | | |

For context (from `2026-08-30-category-classifier-investigation.md`, `[V]` there): the
**genuinely** geo/elec fraction of clob-Unknown is ~**1,000–3,000 markets
(0.5–1.4 %)** by title sampling + tight keyword bounds. Every keyword filter above
sits *above* that band → all over-select.

*Caveat:* the "~305,000 unswept candidates" in the prompt ≈ this document's 353,047
`resolved = 0/NULL AND Unknown` (or 354,180 ignoring category). A narrower
"sweep-eligible" definition (has trades, not gap-flagged, has an end_date) would land
nearer 305k; the per-mechanism *ratios* above are stable to that choice. `[I]`

### 4c — Is any existing mechanism good enough?

**No.** Stated plainly:

- **The column mechanisms (M1, M2) and everything built on them (P1–P4, T1–T5, M13)
  return 0 on the backlog by construction.** They *are* the gap.
- **The keyword INCLUDE filters (M8, M9's prefilter, M10)** are coarse pre-selectors,
  not classifiers. They over-select true geo/elec by 2–3×, and behind each one still
  has to sit a decision step. They could *narrow* a re-classification job, not *do* it.
- **The exclusion-only filter (M11)** passes 87 % of the backlog — worse than useless
  as a relevance filter.
- **The source category (M3)** already ran on this population and produced `Unknown`;
  re-querying Gamma is a live-API job of unproven yield, not a filter sitting ready.
- **The actual classifiers (M6 Mistral, M9 Qwen)** are the only things that decide
  geo-vs-not, and M9 is already the daily backfill — with its own throughput ceiling
  documented separately.

So the relevance filter this project now needs **is not sitting finished in the
codebase**. Whether to (a) re-scope and re-run M9/M6, (b) re-run M3 against Gamma at
scale, or (c) build something new, is the decision to be taken after this document —
**not made here.**

---

## WHAT REMAINS UNCHECKED (named, not chased)

- Keyword-coverage figures in Part 4 are `LOWER(title) LIKE` approximations of the
  real Python `in` checks (which some mechanisms run against Gamma slug/tags, not
  title) — directionally right, not exact; substring false positives inflate them.
- M6 (`monitor.py` Mistral) current runtime behaviour — verified it is wired and
  local, not measured for volume or accuracy this session.
- Whether M10's `CATEGORY_TAG_MAP` matches against Gamma tags, slug, or title in its
  live code path (assumed tags/slug from context; the near-zero hit rate is the
  observed fact regardless).
- Exact "sweep-eligible" definition behind the prompt's "~305,000" — used
  `resolved = 0/NULL` (353,047 Unknown) as the stand-in.
- The `v2 → v2c → v2d → v2e` chain was confirmed to scope on `m.category` at each
  documented entry point, not line-by-line audited end to end.

No recommendation — that is the next step, on top of this.
