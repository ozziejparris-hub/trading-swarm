# Why 214,516 Sweep-Resolved Markets Carry `category='Unknown'`

**Date:** 2026-08-31. **Scope:** read-only. Built nothing, changed nothing, recommend
nothing. Live Gamma API calls were made only for the sampling in Q3/Q5 (**~26 calls
total**, ~1 req/s, no rate-limiting seen).
**Predecessor:** `2026-08-31-geo-scoping-inventory.md` (3b367dd) recorded, as `[I]`,
that Gamma's `event.category` (mechanism **M3**) "already ran at ingest on most of
these and returned no mappable category." **This tests that inference directly.**
**Tagging:** `[V]` verified this session (code read / DB query / live API);
`[I]` inferred.

---

## VERDICT

**Primarily explanation B — Gamma genuinely has no category for these markets —
with structural A and C mechanics as real contributing causes that would not matter
even if fixed.**

- **B (dominant, decisive):** Of **97 markets sampled** across both populations and
  queried against Gamma's live API this session, **0 returned any category** — market
  object `category: null`, parent-event `category: null`, `tags` empty — **including
  genuine election markets** (Paris municipal runoff; "Trump meets with Putin"). The
  high-frequency template markets that make up ~85 % of the backlog (crypto
  up/down, sports O/U, weather, tennis ITF, esports) were never categorised by
  Polymarket. **The source cannot fix this. A classifier is required.**
- **A (structural, ~39 % of the population):** the `background_backfill` slice
  (84,186 markets) was written by `background_backfill_worker.py`, which **hardcodes
  `category='Unknown'`** in its `INSERT`, and by `backfill_missing_markets.py`, whose
  tag-keyword map (M10) is near-inert. **Neither path invokes M3 at all.**
- **C (structural, the `live_monitoring` ~60 %):** the monitor *does* consult M3, but
  (i) its event-category cache is built only from Gamma `/events?active=true` —
  closed events are absent; (ii) `markets.category` is written **once**, on first
  sighting, then never revisited (`store_market_from_trade` / `store_market_dict`
  early-return on `market_exists`); (iii) the cache refresh never back-fills category
  onto existing rows; (iv) a separate ingest path (`trader_analyzer` →
  `store_market_dict`) bypasses M3 and the exclusion filter entirely. A cache miss
  writes `'Unknown'` permanently. **But per B, a perfect cache would still yield
  `'Unknown'`, because Gamma has nothing to return.**

**"Ask Gamma first, sweep what comes back geo/elec" (the Q5 hypothesis) does not
work** — Gamma returns no category for the unswept population either (44/44 across two
samples).

---

## Q1 — Which ingestion path created them?

The 214,516 sweep-resolved (`resolution_evidence_source='clob'`) `Unknown` markets, by
`data_source` `[V]`:

| data_source | clob-Unknown | % | has `condition_id` col | classification rate of *all* clob-resolved from this source |
|---|---:|---:|---:|---:|
| `live_monitoring` | 129,256 | 60.3 % | 11 | 110 / 129,366 = **0.09 %** |
| `background_backfill` | 84,186 | 39.2 % | 0 | 2 / 84,188 = **0.002 %** |
| `historical_backfill` | 1,010 | 0.5 % | 1,008 | 147 / 1,157 = 12.7 % |
| `gap_recovery_20260811` | 64 | 0.03 % | 0 | 0 / 64 |

Wider context — classification rate by source is low **everywhere**, not just for
swept markets `[V]`: `live_monitoring` non-swept = **3.66 %** classified (207,341
rows); `background_backfill` non-swept = **0.08 %**; the only source that categorises
well is `historical_backfill` non-swept at **40.4 %** — the one-time 2025-12-11
mass-import (O-16), which pulled categories from the API at import time. So the
Unknown problem is systemic to the live pipeline, not specific to the sweep.

### What each path does about categorisation `[V]`

| Path (`data_source`) | Categoriser | M3? | M10? |
|---|---|---|---|
| **`monitor.py` `check_for_new_trades` → `store_market_from_trade`** (`live_monitoring`) | Looks up `_event_category_map[market_id]` → `GAMMA_CATEGORY_MAP` → else `'Unknown'`. Also runs `_should_exclude_market` first (excluded markets are **not stored**). | **Yes** — this is M3 | no |
| **`monitor.py` `initial_scan` → `trader_analyzer.scan_for_successful_traders` → `store_market_dict`** (`live_monitoring`, default `data_source`) | `category = market.get('category') or 'Unknown'` from the Polymarket `/markets` REST object. **No event-category lookup, no exclusion filter.** Iterates `get_markets(category=[…,'Unknown'])` — a firehose that includes crypto/sports/weather. | **No** | no |
| **`background_backfill_worker.py`** (`background_backfill`) | `INSERT OR IGNORE INTO markets (…, category, …) VALUES (?, ?, 'Unknown', 0, 'background_backfill')` — **category is the literal string `'Unknown'`.** No categorisation attempt. | **No** | no |
| **`backfill_missing_markets.py`** (`background_backfill`) | `GET gamma/markets/{market_id}` → `map_category(data.get('tags'))` (M10's `CATEGORY_TAG_MAP` keyword match on tag slug/label) → else `trade_category` (M2) → else `'Unknown'`. | **No** | **Yes** |
| **`backfill_o16_tier1/2.py`** (`gamma_backfill_2026-07-02`, `…tier2_2026-07-06`, `historical_backfill`) | `GET gamma/markets/{api_id}` → reads the market object's `category`. | reads Gamma market `category`, not `/events` | no |

**A live-monitored market's category is set by M3 only on the `store_market_from_trade`
path; the `store_market_dict` path (which ingested the crypto/sports/weather flood)
never touches M3. The 39 % `background_backfill` slice never had any categoriser —
one writer hardcodes `'Unknown'`, the other uses a near-inert tag map.**

---

## Q2 — Does M3 actually get consulted, and is `Unknown` ever revisited?

Read `monitor.py` ingest path (`check_for_new_trades`, `_refresh_event_category_map`,
`_should_exclude_market`) and `database.py` (`store_market_from_trade`,
`store_market_dict`, `update_market`). `[V]`

**The cache (M3's input):**
```
_refresh_event_category_map():
    GET {base}/events?limit=100&offset=…&active=true      # ← active events ONLY
    for event: for market in event['markets']:
        new_map[market['conditionId']] = event.get('category')  # may be None
    self._event_category_map = new_map                    # full replace, every ~2.5h
```
- Only **currently-active** events are ever in the map. Once an event closes/resolves
  it is gone from the next refresh.
- The refresh's only DB write is `_batch_update_market_end_dates` — it updates
  `end_date` for existing rows. **It never writes `category`.**

**The ingest write:**
```
event_category  = self._event_category_map.get(market_id)          # cache lookup
internal_category = GAMMA_CATEGORY_MAP.get(event_category or '', 'Unknown')
if await self._should_exclude_market(title, event_category): continue   # not stored
await store_market_from_trade(trade, event_category=event_category)
```
```
store_market_from_trade(...):
    if self.market_exists(market_id): return        # ← EARLY RETURN — no update, ever
    category = event_category or trade.get('category') or 'Unknown'
    self.update_market(..., category=category)
```
`store_market_dict` has the identical `if self.market_exists(...): return` guard.

**So:** category is written **exactly once**, on the first trade/market sighting. If
`market_id` is not in `_event_category_map` at that instant — because the parent event
had already closed, or the market has no parent event, or the 2.5-hour refresh
had not yet run — `internal_category` is `'Unknown'`, and that value is frozen.
Every later trade for that market hits the `market_exists` early-return.
`update_market`'s SQL *does* contain `ON CONFLICT … DO UPDATE SET category =
excluded.category`, but the early-return upstream means that path is never reached
from the monitor. **A cache miss writes `Unknown` permanently.** `[V]`

The monitor tracks flagged traders on 15-minute cycles; their trades routinely land
on markets whose events closed long before (crypto 5-minute markets, day-old sports
markets, months-old markets a newly-flagged trader once traded). At ingest time those
events are not `active`, so they are not in the cache. This is a structural,
permanent-Unknown pathway — **explanation C, mechanically confirmed.** The daily
`backfill_market_categories.py` LLM (M9, ~19 markets/day) is the *only* process that
ever revises an existing market's category.

---

## Q3 — Testing explanation B directly (live Gamma)

**Method `[V]`:** `market_id` for **all 214,516** is a 66-char `0x…` conditionId (the
PK), even though the `condition_id` *column* is populated for only 1,019. Queried
`GET gamma-api.polymarket.com/markets?closed=true&condition_ids=<id>…` in batches of
8. (`/events?condition_ids=` was tested and **silently ignores the filter** — returns
arbitrary events — so it cannot be used; the market object's embedded `events[]` is
the route to event category.) For each market: take `category`, else first non-null
`events[].category`; bucket.

**Sample: 55 clob-resolved Unknown markets, 7 Gamma calls.**

| Bucket | Count |
|---|---:|
| **B1 — Gamma has a mappable category** (Geopolitics / Elections / Global Politics / Ukraine & Russia / US-current-affairs / Politics) | **0** |
| **B2 — Gamma has a category that maps to nothing we keep** (Sports, Crypto, Tech, …) → correctly `Unknown` for us | **0** |
| **B3 — Gamma has NO category** (market found, `category: null`, event `category: null`, `tags` empty/None) or market not found | **55** |

All 55 markets were **found** in Gamma (title, slug, event all present) — they are not
missing, they simply carry no category. This holds for the genuinely political
markets in the sample too:

- `Will the Emmanuel Grégoire List win the most citywide list votes in the runoff of
  the 2026 Paris municipal election…` → `market.category=None`, `market.tags=None`,
  parent event `"Paris Mayoral Election Runoff: Margin of Victory"`
  (`slug=paris-mayoral-election-runoff-margin-of-victory`), `event.category=None`,
  `event.tags=[]`.

For contrast `[V]`: Gamma's `/markets?closed=true` firehose *does* return categories
for old (2020-era) markets — "Will Joe Biden get Coronavirus before the election?" →
`US-current-affairs`; "Will Airbnb begin publicly trading…" → `Tech`. So Polymarket
category data exists historically; it is **absent for the 2026 template-market era**
that dominates this backlog, and absent for the individual political markets in it.

**Conclusion:** for the swept population this is **explanation B**. The markets did
(mostly) reach a categoriser; the categoriser had nothing to give, and still has
nothing to give when re-queried today.

---

## Q4 — How many would Gamma classify as geo/elec?

**Zero, from the structured category field.** `[V]` Gamma returns no category for any
sampled market, geo or otherwise, so Gamma-as-source would map **0** of the 214,516
into Geopolitics/Elections.

By **title** in the same 55-market sample: ~1–2 are genuinely geo/elec (Paris
municipal election; "Elon Musk tweet count" as a stretch) ≈ **2–4 %**, small-n. The
independent title-sampling estimate from
`2026-08-30-category-classifier-investigation.md` was **0.5–1.4 %** (~1,000–3,000
markets). These are the **same order of magnitude** given a 55-market binomial
(95 % CI on 2/55 spans roughly 0.4–12 %) — **no material disagreement**. The
operative point is orthogonal to the count: **Gamma contributes nothing to finding
those markets**, because its category is null for them regardless of whether they are
geo/elec.

---

## Q5 — Same test on the unswept population

**Sample A: 20 unswept (`resolved=0`) Unknown markets** — 3 Gamma calls → **20/20
NOT_FOUND**. This sample (sorted by `market_id` tail) hit a cluster of synthetic
markets: `market_id`s like `0x03972a75…0000000000000000` (trailing-zero padded, not
real Keccak conditionIds) and titles of the form `"Will X win… AND Will Y win…"`
(parlay/derived shape). **30,037 of the 353,047 unswept Unknown titles contain
" AND "** — a large synthetic/derived subset that does not exist in Gamma at all. `[V]`

**Sample B: 22 unswept Unknown markets, filtered to real 66-char conditionIds, no
"AND" titles, randomised** — 3 Gamma calls:

| Bucket | Count |
|---|---:|
| B1 — mappable geo/elec | **0** |
| B2 — other category | **0** |
| B3 — no category / not found | **22** (21 found with `category=null`; 1 not found — "Trump meets with Putin by December 31?", genuinely geopolitics) |

**Combined across both populations: 0 / 97 sampled markets carry a usable Gamma
category.** "Ask Gamma first, then sweep what comes back geo/elec" would return an
empty set — it cannot serve as the relevance filter.

---

## Q6 — Job shape, if Gamma could answer (it can't — recorded for completeness)

`[V]` from a 40-market Gamma batch (4 calls):

- **No event grouping.** 40/40 markets belong to exactly **1 distinct event each** —
  40 markets → 40 events. The events are per-instance template events
  (`sol-updown-5m-1778675100`, `nba-hou-mia-2026-02-28`,
  `lowest-temperature-in-seoul-on-july-17-2026`,
  `fifwc-par-aus-2026-06-25-player-props`). For this population "markets group into
  events" is effectively **false**; ~214,516 markets ≈ ~214,516 distinct events.
- **No event identifier in the DB.** `markets` has `market_id`, `condition_id`,
  `api_id` — **no event column** (`grep` of the schema → 0 hits). Events are
  resolvable only by per-market Gamma lookup.
- **Identifier for the lookup:** `market_id` itself is the conditionId for all
  214,516 rows, so `GET /markets?condition_ids=<id>` works without needing the
  sparsely-populated `condition_id` column.
- **Call volume:** ~8–15 conditionIds per request → **≈ 14,000–27,000 requests** for
  the full 214,516. This session made **~26 calls at ~1 req/s with 1 s sleeps and saw
  no `429`s / rate-limiting**; a full pass is a multi-hour job, not a multi-day one.
- **Expected yield: ~0 categories** (per Q3/Q5). The job is not worth running for
  categorisation. (It *would* be a valid way to refresh `end_date` / event slug /
  `condition_id`, which is a different question.)

---

## WHAT REMAINS UNCHECKED (named, not chased)

- Sample sizes: 55 clob + 42 unswept = 97 markets against Gamma. Consistent and
  unambiguous (0/97 with a category) but not a large-n census.
- Whether a **slug/ticker keyword** approach on Gamma's response (e.g. event slug
  `paris-mayoral-election-runoff…` contains "election") could recover some geo/elec
  markets — the structured `category` field is empty, but the slug often is not. Not
  quantified here; it would be a *new* classifier, not "the source".
- The exact split of the `live_monitoring` 129,256 between the
  `store_market_from_trade` (M3-consulting) path and the `store_market_dict`
  (M3-bypassing) path — no `data_source` sub-tag distinguishes them; inferred from
  the crypto/sports/weather title mix (which `_should_exclude_market` would have
  blocked on the trade path) that `store_market_dict` is the dominant contributor.
- `background_backfill_worker.py`'s exact share of the 84,186 vs
  `backfill_missing_markets.py`'s — both stamp `data_source='background_backfill'`
  and both yield `'Unknown'` for this population, so not separated.
- The 30,037 " AND " unswept titles were characterised as synthetic by shape +
  Gamma-absence, not traced to the specific script that generates them.

No recommendation — this establishes the cause only.
