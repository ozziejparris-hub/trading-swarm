# Step 1 Assessment — The Permanent-`Unknown` Ingest Defect

**Date:** 2026-08-31. **Scope:** read-only. Specify the fix; do **not** implement.
~13 live Gamma calls for the Part 1.3 recovery test.
**Predecessor:** `2026-08-31-why-unknown-investigation.md` (ce35996).
**Tagging:** `[V]` verified this session (code / DB / live API); `[I]` inferred.
Every claim in the task prompt treated as a hypothesis.

---

## BOTTOM LINE (Part 3 up front)

**Defer. This should not be step 1.** The fix stops the monitor writing `'Unknown'`
*permanently*, but every test this session says there is **nothing better to write**:
Gamma returns no category for these markets — not for the backlog (0/97, predecessor),
and not for fresh, still-open, unambiguously-geopolitical markets ingested in the last
14 days (0/34 this session, incl. 8 requeried without the `closed` filter). The
mechanism the fix would repair (write-once category) is real, but it is downstream of
the thing that would supply a category — the classifier. Build the classifier first;
revisit this as a small hook that applies the classifier's output at ingest time. The
daily inflow the fix addresses is ~**13 markets/day**, and the safe version of the fix
is a narrow guarded single-column `UPDATE` that is the *same shape* whether the
category comes from Gamma (≈never) or from a classifier (the real source). There is no
value in building that plumbing against an empty source.

---

## PART 1 — CONFIRM THE MECHANISM

### 1.1 The early-return, quoted `[V]`

`monitoring/database.py`, `store_market_from_trade` (lines 762–811):

```python
def store_market_from_trade(self, trade: Dict, event_category: Optional[str] = None):
    market_id = (trade.get('market_id') or trade.get('conditionId') or
                 trade.get('market') or trade.get('id') or trade.get('asset_id'))
    if not market_id:
        return  # Can't store without market_id
    # Check if market already exists
    if self.market_exists(market_id):
        return  # Already stored          # ← EARLY RETURN
    ...
    category = event_category or trade.get('category') or trade.get('market_category') or 'Unknown'
    ...
    self.update_market(market_id=market_id, title=title, category=category,
                       end_date=end_date, resolved=False, winning_outcome=None)
```

`store_market_dict` (lines 813–872):

```python
def store_market_dict(self, market: Dict):
    api_id = market.get('id'); condition_id = market.get('conditionId')
    if not api_id and not condition_id:
        return
    market_id = api_id or condition_id
    # Check if market already exists (check by either ID)
    if self.market_exists(market_id) or (condition_id and self.market_exists_by_condition_id(condition_id)):
        return  # Already stored          # ← EARLY RETURN (dual check)
    ...
    category = market.get('category') or 'Unknown'
    ...
    resolved = market.get('closed', False) or market.get('archived', False)
    self.update_market(market_id=market_id, title=title, category=category,
                       end_date=end_date, resolved=resolved, winning_outcome=None,
                       condition_id=condition_id)
```

`market_exists` (line 740) / `market_exists_by_condition_id` (line 751) are plain
`SELECT 1 FROM markets WHERE market_id = ? / condition_id = ? LIMIT 1`.

### 1.2 `update_market`'s `ON CONFLICT … DO UPDATE SET category` exists but is unreachable from the monitor `[V]`

`update_market` (lines 509–537):

```python
cursor.execute("""
    INSERT INTO markets (market_id, title, category, end_date, resolved,
                       winning_outcome, resolution_date, last_checked, condition_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(market_id) DO UPDATE SET
        title = excluded.title,
        category = excluded.category,                      # ← the clause we would want
        end_date = COALESCE(excluded.end_date, end_date),
        resolved = excluded.resolved,
        winning_outcome = excluded.winning_outcome,
        resolution_date = COALESCE(resolution_date, excluded.resolution_date, excluded.end_date),
        last_checked = excluded.last_checked,
        condition_id = COALESCE(excluded.condition_id, condition_id)
""", (market_id, title, category, end_date, resolved, winning_outcome,
      effective_resolution_date, datetime.now(), condition_id))
```

`grep` of the whole tree for `.update_market(` → **exactly three callers**:
`store_market_from_trade` (802), `store_market_dict` (862), and
`scripts/simulation/seed_production_data.py:909` (not a production path). Both
production callers early-return on `market_exists` for an existing row, so the
`ON CONFLICT … DO UPDATE` branch **fires only on the INSERT** in practice — the
`category = excluded.category` update line is dead code for every already-stored
market. **Confirmed: exists, unreachable from the monitor.**

### 1.3 The rate `[V]`

New `'Unknown'` markets by `data_source`, measured two ways (first-trade date and
`last_checked` recency; both agree on the live path):

| Source | New `Unknown` / day | Path & categoriser |
|---|---|---|
| `live_monitoring` | **6–28, mean ~13** (11-day window, stable) | (a) `check_for_new_trades` → `store_market_from_trade` — consults M3 (`_event_category_map` → `GAMMA_CATEGORY_MAP`); (b) periodic re-scan every 10 cycles ≈ 2.5 h → `scan_for_successful_traders` → `store_market_dict` — **no M3, no exclusion filter** |
| `background_backfill` | 200–2,700, **declining** (2,681 on 08-12 → 184 on 08-30) | `background_backfill_worker.py` **hardcodes** `category='Unknown'` in its INSERT; `backfill_missing_markets.py` uses the near-inert M10 tag map. **A category-revision fix cannot help this path** — there is no categoriser to make revisable. It is a winding-down campaign, not steady state. |
| `historical_backfill` / `gap_recovery` | 0–10 | one-off imports |

**The fix's addressable rate is ~13 markets/day** (the `live_monitoring` inflow). The
large `background_backfill` numbers are out of scope for a "make category revisable"
change.

### 1.4 The recoverable fraction — ~0% `[V]`

The predecessor sampled 97 *already-Unknown* markets → 0 had a Gamma category. This
session tested the sharper question: **for markets entering NOW, is the cause a cache
miss on a categorised event, or does Gamma have nothing?**

Sample: **34 `live_monitoring` `Unknown` markets with `last_checked` in the last 14
days**, titles overwhelmingly genuine geopolitics/elections — "Haiti elections
delayed again?", "Israel withdraws from Lebanon by Aug 31", "US x Iran permanent
peace deal", "Will Russia target Kyiv", "Will the Democratic Party candidate win the
2026 NY-10 House" (×8), "2027 Tlaxcala Governor", "2026 Vaughan / Brampton mayoral"
(×5), "Sachsen-Anhalt parliamentary election Grüne vote share", "Brazil presidential
election first round 2nd place".

| Bucket | Count |
|---|---:|
| B1 — Gamma has a **mappable** category | **0** |
| B2 — Gamma has a category that maps to nothing we keep | **0** |
| B3 — Gamma has **no** category (`market.category=None`, `event.category=None`, `event.tags=[]`) or market not returned | **34** |

The 26 initial "not found" were the `closed=true` filter excluding still-open
markets. Requeried **without** the filter, 8 of the clearest geopolitical ones — Kyiv,
NY-10 House, Brampton mayoral, Israel/Lebanon, Sachsen-Anhalt Grüne, Vaughan mayoral,
Brazil 1st-round, Strait of Hormuz — **all return `closed=False`, `market.category =
None`, `event.category = None`, `event.tags = []`.** Event *slugs* are richly
descriptive (`ny-10-house-margin-of-victory-2026`,
`brazil-presidential-election-first-round-2nd-place`,
`sachsen-anhalt-parliamentary-election-grune-vote-share`) — the geo/elec signal is
there — but **the structured `category` field the ingest path reads is empty**, even
for live markets, even for markets that are obviously geopolitics.

**Plain statement:** the cache-miss is *not* the operative cause. `_event_category_map`
returning `None` for a market is not a stale-cache artifact — it is what Gamma
actually holds. A fixed ingest mechanism would re-run `GAMMA_CATEGORY_MAP.get(None or
'', 'Unknown')` → `'Unknown'` on every re-sighting. **The fix would stop the write
being *permanent*, but the value it would write is still `'Unknown'`** until a
different mechanism (a classifier; or a slug/keyword heuristic — a *different*
mechanism, out of scope here) supplies something better.

---

## PART 2 — SPECIFY THE FIX (not implemented)

### 2.4 The three options, with failure mode and blast radius

All three are gated by the same ceiling (§1.4): the source has ~nothing to supply.
And all three are **safe only if the write is a targeted single-column statement**
—`UPDATE markets SET category = ? WHERE market_id = ? AND category = 'Unknown'` — and
**never** a re-call of `update_market()` (see §2.5 for why).

| Option | Mechanism | Failure mode | Blast radius |
|---|---|---|---|
| **A. Remove / narrow the `market_exists` early-return** | Let a later sighting reach an `UPDATE` when it has a strictly-better category. | *Naive removal:* full §2.5 blast radius — `trg_resolved_no_unresolve` ABORT, wiped `winning_outcome`, clobbered `title`. *Narrowed* (proceed only when `existing.category='Unknown'` AND new ≠ `'Unknown'`): fires ~never (§1.4). If the write is left as `update_market()` rather than a scoped UPDATE, reintroduces the full blast radius. | Naive: **severe — breaks the running monitor loop**. Narrowed + scoped UPDATE: ~nil, but ~nil value. |
| **B. Separate periodic pass over `Unknown` markets** | A job that revisits `category='Unknown'` rows and re-queries a source. | This **already exists**: `backfill_market_categories.py` (M9) is exactly this, via LLM, ~19/day. A *Gamma-based* sibling would query per-market and find ~nothing (§1.4). Rate-limit exposure; races M9 (§2.6). | Low if own process + scoped UPDATE. **Negative ROI** — API load for ~zero yield. |
| **C. Cache refresh back-fills category onto existing rows** | Add a `_batch_update_market_categories` next to the existing `_batch_update_market_end_dates` in `_refresh_event_category_map`, for rows where `category='Unknown'` and the now-seen event has a mappable category. | (i) Only covers **currently-active** events — the entire failure population is markets whose events already closed when the trade landed, so it never sees them. (ii) Active events also return `category=None` (§1.4), so even the covered slice yields ~zero. (iii) Rewrites every 2.5 h unless guarded on `category='Unknown'`. | Contained **iff** the batch update is the scoped single-column UPDATE. Smallest code change; stays in one function that already writes the DB. Still ~zero yield. |

### 2.5 What the early-return protects — the pre-flight `[V]`

The early-return is **not primarily a category guard**. It is a blunt write-once guard
that stops the ingest path — which only ever carries **stub** resolution/title values
— from overwriting rows that authoritative processes have since enriched. Every column
`update_market`'s `ON CONFLICT DO UPDATE` would touch if the guard were removed:

| Column | `ON CONFLICT` clause | `store_market_from_trade` re-sighting passes | Consequence |
|---|---|---|---|
| `title` | `= excluded.title` **unconditional** | `'Unknown Market'` when the trade object has no title | **good title overwritten with `'Unknown Market'`** |
| `category` | `= excluded.category` **unconditional** | `event_category or … or 'Unknown'` → `'Unknown'` (§1.4) | the intended target — but value is `'Unknown'` |
| `end_date` | `COALESCE(excluded.end_date, end_date)` | `None` usually | kept; a wrong trade-embedded `endDate` would overwrite |
| `resolved` | `= excluded.resolved` **unconditional** | `False` (hardcoded) | for a market resolved since first sighting: `1 → 0` → **`trg_resolved_no_unresolve` `RAISE(ABORT)`** → whole statement aborts → exception out of `store_market_from_trade` → **monitor trade-storage loop breaks**. This is the *common* case — flagged traders routinely trade on already-resolved markets (the reason the backlog exists). |
| `winning_outcome` | `= excluded.winning_outcome` **unconditional** | `None` (hardcoded) | **wipes the winner** of a resolved market (masked only by the `resolved` trigger aborting first; if `resolved` were already 0, it nulls silently) |
| `resolution_date` | `COALESCE(resolution_date, excluded.resolution_date, excluded.end_date)` | `effective_resolution_date = end_date` | bare `resolution_date` = existing value → kept if set; if NULL, **speculatively stamps `end_date` as a resolution_date** on an unresolved market — collides with the O-17/O-18 resolution_date canonicalisation and `audit_invariants` expectations |
| `last_checked` | `= excluded.last_checked` | `now` | harmless (its purpose) |
| `condition_id` | `COALESCE(excluded.condition_id, condition_id)` | `None` (from `store_market_from_trade`); real id from `store_market_dict` | kept if new is NULL; filled if missing (benign) |

`store_market_dict` additionally passes `resolved = market.get('closed') or
market.get('archived')` — a transient Gamma `closed=False` on a resolved market would
also trip `1 → 0` → ABORT.

**Explicit answer to the prompt:** *yes* — a naive removal/loosening of the
early-return, left routed through `update_market()`, **would write `markets.resolved`,
`markets.winning_outcome`, and `markets.resolution_date`**. Those six provenance
columns (`resolved`, `winning_outcome`, `resolution_date`, `resolution_recorded_at`,
`resolution_evidence_source`, `resolution_evidence_detail`) have a single sanctioned
writer — `monitoring/resolution_writer.py::mark_market_resolved()` — and a DB-level
invariant (`trg_resolved_no_unresolve`). `update_market` already writes three of the
six; making it run on every sighting would make the ingest path a second,
unsanctioned resolution writer and would collide with both the canonical function and
the trigger. **A correctly-scoped fix — a single-column
`UPDATE markets SET category = ? WHERE market_id = ? AND category = 'Unknown'`, not
`update_market()` — touches none of these.**

### 2.6 Interaction with the ~19/day LLM backfill (M9) `[V]`

M9 (`backfill_market_categories.py`) is the **only** production process that does
`UPDATE markets SET category` today (line 200; it also mirrors to
`trades.market_category`, line 204). It selects from the same pool
(`WHERE category='Unknown'` + 37-keyword filter, `LIMIT/OFFSET` by `market_id`).

- **No corruption:** SQLite serialises writes (WAL + `busy_timeout`).
- **Compose safely only if both sides guard on `category='Unknown'`.** With the guard,
  whichever runs first wins and the other's `AND category='Unknown'` makes it skip —
  no duplicated work, no clobber. **Without the guard** (i.e. an `update_market()`
  re-call), the ingest path writing its usual `'Unknown'` can overwrite an M9
  `Geopolitics` result back to `'Unknown'` on last-writer-wins. Another reason the fix
  must be the scoped UPDATE.
- **Minor drift interaction:** M9 paginates `LIMIT/OFFSET` over the shrinking
  `category='Unknown'` set and already has an offset step-over bug
  (`2026-08-30-category-classifier-investigation.md`). A concurrent ingest-side
  classifier removing rows from that set accelerates the step-over. Not a
  correctness issue for M9's *outputs*, but it widens the set M9 never revisits.

---

## PART 3 — SHOULD THIS BE STEP 1?

**No. Defer it until the classifier exists.** The evidence:

1. **Addressable rate is small** — ~13 new `Unknown` markets/day via the path a
   category-revision fix can touch. The large `background_backfill` numbers are a
   winding-down campaign whose worker hardcodes `'Unknown'` and which the fix does not
   reach.
2. **Recoverable fraction is ~0%** — 0/97 (predecessor) + 0/34 fresh `live_monitoring`
   markets this session, including 8 still-open, obviously-geopolitical markets
   requeried without the `closed` filter, have any Gamma category. The fix would make
   the write non-permanent, but re-writes `'Unknown'` every time because the source is
   empty. **There is nothing better to write until a classifier produces it.**
3. **The early-return is load-bearing** (§2.5). The only safe version of the fix is a
   narrow, guarded, single-column `category` UPDATE — which is *exactly the shape* of a
   future "apply the classifier's category at ingest / on refresh" hook. Building it
   now means building it against a source that returns nothing; building it after the
   classifier means building it against a source that returns something. Same code,
   better time.
4. **M9 already is "the periodic pass that revisits `Unknown` markets."** The missing
   piece is a *category worth writing*, i.e. the classifier. Sequencing the plumbing
   before the thing it plumbs is backwards, and the prompt's own framing — "the
   classifier may be the thing that supplies the category the ingest path would
   write" — is correct.

**Consequence for the growth-of-backlog concern:** the backlog does keep growing at
~13 relevant markets/day, and this defect is why. But those 13/day are not
*recoverable* by fixing the defect in isolation — they are recoverable only by a
classifier, which would also clear the far larger existing backlog. Once that exists,
the cheapest place to also catch the daily 13 is a small hook here (Option C shape:
back-fill `category` from the classifier's output onto `category='Unknown'` rows, via
the scoped UPDATE). That hook is a genuine step — just not step 1, and not against
Gamma.

*Not in scope, flagged once:* the descriptive event **slugs** returned by Gamma
(`…-parliamentary-election-…`, `…-mayoral-election-…`, `…-house-margin-of-victory-…`)
carry the geo/elec signal that the empty `category` field does not. A slug/keyword
classifier is a *different mechanism* from "the source", and evaluating it belongs
with the classifier work, not here.

---

## WHAT REMAINS UNCHECKED (named, not chased)

- §1.4 sample is 34 recent `live_monitoring` markets (+8 requeries). Unanimous (0
  with a category) but not a census; a larger sample could surface a rare categorised
  event, though the predecessor's 97 + these 34 = 131 markets at 0 makes that
  unlikely to change the conclusion.
- The exact split of the ~13/day `live_monitoring` inflow between the
  `store_market_from_trade` (M3-consulting) and `store_market_dict` (M3-bypassing,
  every 2.5 h) sub-paths — no `data_source` sub-tag distinguishes them.
- Whether `_batch_update_market_end_dates` (the existing refresh-time DB write)
  itself has any guard/lock interaction with M9 — assumed benign (different columns),
  not traced.
- The `background_backfill` campaign's end date / remaining volume — observed
  declining, not projected.

No implementation. This is the specification and the sequencing call.
