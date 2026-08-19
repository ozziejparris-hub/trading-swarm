# 2026-08-19 — TradeEvaluator vs. `backfill_trade_results_geo.py`'s `evaluate_trade()`: convergence check

Read-only. Neither evaluator was run against production in write mode;
nothing was repointed or wired. Every claim tagged **[V]** (verified this
session — command/file:line given) or **[I]** (inferred, explicitly
marked). Findings recorded here only.

Committed script: `scripts/compare_trade_evaluators.py` (first-repo).
Re-run: `python3 scripts/compare_trade_evaluators.py`. Writes a timestamped
JSON artifact to `data/characterizations/`. Today's run:
`data/characterizations/trade_evaluator_convergence_20260819T180423Z.json`.

---

## Verdict: **IDENTICAL-REPOINTABLE**

Outputs agree on all **1,582,064** compared rows — zero disagreements.
Every edge case checked either never fires against the actual data shape
in this database, or is already handled identically by both
implementations via a shared upstream SQL filter. The repoint is
mechanical: swap a 3-argument local function call for a 2-argument method
call on an already-available dict; no signature adaptation, connection
change, or batching change is required. One minor, non-blocking
addition (§4) would be needed for full semantic parity on a fallback path
that has never yet been exercised. Full detail below.

---

## 1. The two implementations, read in full

**Canonical: `monitoring/trade_evaluator.py:16`,
`TradeEvaluator.evaluate_trade(self, trade: Dict, winning_outcome: str) -> str`.**
Reads `trade['outcome_bet']` (falls back to `trade['outcome']` if falsy),
`trade['side']` (via `trade.get('side', 'buy')`), and the `winning_outcome`
parameter. No `self.db`/`self.client` reference inside this method — pure
given its arguments, despite the class requiring `(database,
polymarket_client)` at construction.

**Geo-backfill: `scripts/backfill_trade_results_geo.py:30`,
`evaluate_trade(outcome_bet: str | None, side: str, winning_outcome: str) -> str`.**
Module-level function, three scalar arguments. Reads only what's passed in
— it has no access to an `outcome` fallback field at all, because its
caller's SQL (`fetch_pending_trades`, line 44) never selects `trades.outcome`.

**Statement-level differences, enumerated (not summarised):**

| # | TradeEvaluator | geo-backfill's `evaluate_trade` | Behavioral consequence |
|---|---|---|---|
| 1 | `trade.get('outcome_bet') or trade.get('outcome', '')` — falls back to a second field | `if not outcome_bet: return 'invalid'` — no fallback field exists in this function's interface at all | TradeEvaluator can resolve a trade the geo-backfill would call `invalid`, **if** `outcome_bet` is falsy but `outcome` is populated. See §2 for whether this ever occurs. |
| 2 | `side = trade.get('side', 'buy').lower()` — defaults to `'buy'` only when the **key is absent**; if the key is present with value `None`, `.lower()` on `None` **raises `AttributeError`** (not caught here) | `(side or 'buy').strip().lower()` — defaults to `'buy'` whenever `side` is **any falsy value** (missing, `None`, `''`), never raises | TradeEvaluator can crash on `side=None`; geo-backfill cannot. Also: for `side=''` specifically, TradeEvaluator falls through to the SELL branch (`'' != 'buy'`) while geo-backfill treats it as BUY (`'' or 'buy'` → `'buy'`) — opposite branches for the same edge input. |
| 3 | No `.strip()` on `side` | `.strip()` on `side` before lowering | A whitespace-padded side value (e.g. `' buy '`) is misread as SELL by TradeEvaluator (`' buy ' != 'buy'`) but correctly read as BUY by geo-backfill. |
| 4 | Interface: `Dict` + separate `winning_outcome` string | Interface: 3 explicit scalar args | Not a behavioral difference by itself, but it's *why* difference #1 exists — the narrower interface structurally cannot carry an `outcome` fallback value even if the caller wanted it to. |

None of these are cosmetic — #1, #2, #3 are real branch-level divergences.
Whether they matter is an empirical question, answered in §2 (they do
not fire) and named as latent risk in §3.

---

## 2. Do they agree — empirical, not inspection-only

**[V]** Ran both implementations, read-only, against every trade currently
`trade_result IN ('won','lost')` on a Geopolitics/Elections market — the
full already-evaluated population, not a sample:

```
rows_compared = 1,582,064
TradeEvaluator vs geo-backfill: agree = 1,582,064, disagree = 0
TradeEvaluator result distribution:  {'won': 704517, 'lost': 877547, 'invalid': 0}
geo-backfill result distribution:    {'won': 704517, 'lost': 877547, 'invalid': 0}
```

**Zero disagreements across 1.58M rows.** The distributions are
identical, not just the totals — same won/lost/invalid split from both.
This is the headline finding of the task and is reported first rather
than buried: **the two implementations produce identical output on every
row that exists in this database today.**

**Why, given §1's real branch-level differences:** checked directly.
- `outcome_bet` is **never** null or empty on this population — `SELECT
  SUM(CASE WHEN outcome_bet IS NULL OR outcome_bet='' THEN 1 ELSE 0 END)
  ... = 0` across 1,582,064 evaluated rows **and** across the 24,719
  currently-pending geo/elec rows. Difference #1 (the `outcome` fallback)
  is structurally unreachable with this data — not because both
  implementations handle it the same, but because the triggering
  condition never occurs.
- `side` is stored as exactly `'BUY'` or `'SELL'` (uppercase, unpadded,
  never `NULL`) DB-wide — `SELECT DISTINCT side FROM trades WHERE
  UPPER(side) NOT IN ('BUY','SELL') OR side IS NULL` returns **zero rows**.
  Differences #2 and #3 (side defaulting/stripping) are also structurally
  unreachable today.

**Secondary, unrequested finding, reported because it surfaced during the
comparison:** both implementations disagree with the **currently stored**
`trades.trade_result` on the same **24** rows (out of 1,582,064 — 0.0015%)
— same trade_ids, same direction, for both evaluators. This means these
24 rows' stored value is stale relative to what either evaluator would
compute *today*, most plausibly because the market's `winning_outcome`
was corrected after the original evaluation and nothing re-evaluated the
affected trades. **[I]** Mechanism not traced further — out of scope for
this task (which asks about TradeEvaluator vs. geo-backfill agreement,
not either vs. the DB), flagged rather than chased, full trade_ids in the
committed artifact if anyone wants to follow up.

---

## 3. Edge-case coverage

| Case | TradeEvaluator | geo-backfill | Divergence? |
|---|---|---|---|
| Null/missing `winning_outcome` | `not winning_outcome` after `str().strip().lower()` → `'invalid'` | Same check, same normalization → `'invalid'` | **No** — identical. |
| `outcome_bet` null, `outcome` populated | Falls back to `outcome`, resolves normally | No `outcome` field available; `not outcome_bet` → `'invalid'` immediately | **Yes, structurally** (§1 #1) — **never fires today** (§2), confirmed empirically on both the evaluated and the pending population. |
| Multi-outcome markets (candidate names, `Up`/`Down`/`Over`/`Under`, etc.) | Direct string equality, no binary assumption | Same | **No** — neither hardcodes Yes/No; both handle N-way outcomes identically by construction. `winning_outcome` DB-wide has 20+ distinct non-Yes/No values confirmed present in Geo/Elections resolved markets. |
| `neg_risk` groupings | Not modeled — no `neg_risk` column exists anywhere in `markets` schema | Same | **No divergence between the two** — both are blind to grouping identically; this is a shared gap in the data layer, not a per-implementation difference. |
| SELL-side trades | Explicit `else` branch: win iff outcome ≠ winner | Explicit `else` branch: identical logic | **No** — same branch, same condition. |
| Zero-size trades (`shares=0`) | Not read by `evaluate_trade` — `shares` isn't a parameter of either function | Same | **No** — neither function reads share size; a zero-size trade is evaluated identically to any other by outcome/side, for good or ill (share size affects P&L weighting elsewhere, not win/loss). |
| Quarantined markets (O-37, `flag_reason='synthetic_quarantine_2026-07-19'`, 84 markets) | Not filtered by `evaluate_trade` itself — filtering happens at the caller level (`batch_evaluate_resolved_markets` reads `get_resolved_markets()`, which is not itself checked here) | Filtered at the SQL level via `trade_gap_flag = 0 OR trade_gap_flag IS NULL` in `fetch_pending_trades` — **not** via `flag_reason` directly | **Coincidentally no** — verified all 84 O-37-quarantined markets also carry `trade_gap_flag=1`, so geo-backfill's existing filter excludes them today. **[I]** This is not a structural guarantee: a future quarantine that doesn't also set `trade_gap_flag` would pass geo-backfill's filter untouched. Flagged as a latent gap in the *filter*, not in `evaluate_trade` itself, and out of this task's scope to fix. |
| Markets `resolved=1` with no `winning_outcome` | `batch_evaluate_resolved_markets` explicitly skips (`if not winning_outcome or not market_id: continue`, line 158) | Excluded at the SQL level (`m.winning_outcome IS NOT NULL AND m.winning_outcome NOT IN ('unknown','')`) | **No** — both skip, via different mechanisms (Python-level vs. SQL-level), same outcome. Currently **zero** Geo/Elections markets are in this state (`resolved=1 AND (winning_outcome IS NULL OR ='')` → 0 rows), so this is untested by real data either way. |

---

## 4. Is the repoint mechanical

**[V] Yes.** `evaluate_trade()` on the canonical side has no side effects
and no DB/client dependency in its body — only the constructor,
`TradeEvaluator.__init__(self, database, polymarket_client)`, nominally
requires two objects, and neither is referenced inside `evaluate_trade`
itself (confirmed by reading the full 191-line file). The current call
site (`backfill_trade_results_geo.py:96`,
`evaluate_trade(trade['outcome_bet'], trade['side'],
trade['winning_outcome'])`, and the identical dry-run call at line 84)
already operates on a `dict` row (`fetch_pending_trades` returns
`[dict(row) for row in cursor.fetchall()]`) — the exact shape
`TradeEvaluator.evaluate_trade` expects.

**What would need to change, concretely:**
1. `from monitoring.trade_evaluator import TradeEvaluator` added to the
   imports.
2. One instantiation, e.g. `_evaluator = TradeEvaluator(None, None)` —
   with a comment noting the constructor args are unused by
   `evaluate_trade()`, since passing `None` for `database`/`polymarket_client`
   is a deliberate, slightly unusual choice a future reader should not
   mistake for an oversight. Constructing *real* `Database`/`PolymarketClient`
   objects instead is possible but adds a live-API-client dependency
   (`PolymarketClient` needs an API key) to a script that is otherwise
   read-only against the local DB — worth avoiding, not required.
3. Replace both `evaluate_trade(trade['outcome_bet'], trade['side'],
   trade['winning_outcome'])` call sites with
   `_evaluator.evaluate_trade(trade, trade['winning_outcome'])` — `trade`
   is already the right dict shape.
4. Delete the now-dead local `evaluate_trade()` function (lines 30-41).
5. **Not required for current-output parity, but needed for full semantic
   parity:** add `t.outcome` to `fetch_pending_trades`'s `SELECT` list
   (line 46-51) so `TradeEvaluator`'s `outcome_bet`-fallback path is
   actually reachable rather than silently absent. Named because §1's
   difference #1 is real in the code even though §2 shows it never fires
   today — if that ever changes, only fetching `outcome_bet` and not
   `outcome` would silently reintroduce the pre-repoint divergence.

**No batching or connection-handling change is needed** — the script's
own raw-`sqlite3.Connection` batch-fetch/batch-commit structure (1,000
rows/commit) is entirely independent of which function computes
won/lost/invalid per row.

**No assumption the canonical evaluator carries that the backfill script
would violate.** `evaluate_trade()` does not assume a particular trader
population, does not filter by `is_flagged` or anything else (that
filtering happens in the *caller's* SQL, which is untouched by this
repoint), and does not write anything as a side effect — the "evaluation
only, no write" requirement is already satisfied by the canonical
function as-is.

---

## 5. What else uses each — blast radius of the repoint

**[V] `TradeEvaluator` callers (via `grep -rln "TradeEvaluator(" --include=*.py .`):**
- `scripts/evaluate_new_trader_results.py:28` — **live**, `daily_maintenance.py`
  step 21, runs daily.
- `scripts/backfill_trade_results.py:31` — **unwired** (confirmed in
  `2026-08-19-geo-backfill-wiring-prereg.md`), manual-only.
- `scripts/archive/test_trade_evaluation.py` — archived test, not live.

**[V] `evaluate_trade` (geo-backfill's own function) callers:** none, found
via `grep -rn "from scripts.backfill_trade_results_geo import" .` and
`grep -rln "backfill_trade_results_geo"` — zero hits outside the file
itself. It is called only from within its own `run()` function, twice
(dry-run path and live-write path).

**Blast radius of the repoint itself:** since `TradeEvaluator.evaluate_trade`
is a pure function with no state, repointing `backfill_trade_results_geo.py`
to call it changes nothing for its two existing live/dormant callers
(`evaluate_new_trader_results.py`, `backfill_trade_results.py`) — they
would continue calling their own already-instantiated `TradeEvaluator`
objects exactly as before; adding a third caller does not alter the
method's behavior for anyone. **The blast radius is confined to
`backfill_trade_results_geo.py` itself**, and per §2, its output does not
change on any row that exists in the database today.

---

## 6. The third-implementation question

**[V] Yes — this is a third, independent implementation of the same
underlying comparison, scoped to a different unit and a different output
type.** `monitoring/position_tracker.py:366`, `apply_synthetic_closes()`,
lines 409-416:

```python
pos_outcome = (pos.outcome or '').strip().lower()
win_outcome = (winning_outcome or '').strip().lower()
if pos_outcome == win_outcome:
    close_price = 1.0   # Winning outcome redeems at $1.00
else:
    close_price = 0.0   # Losing outcome is worthless
```

This answers the same real-world question both `evaluate_trade`
implementations answer — did the held/bet outcome match the market's
actual resolution — using **no shared code** with either. It operates on
**positions**, not **trades** (a position is, by construction, an
already-BUY-established holding — schema comment: *"Entry (BUY trades)"* —
so there is no BUY/SELL branch here; the position-level "outcome" field
already encodes what TradeEvaluator's BUY branch alone would need). It
produces a **price** (`1.0`/`0.0`) for P&L math, not a categorical
`won`/`lost`/`invalid` label for `trades.trade_result`.

**A genuine behavioral gap from the other two, not just a different
shape:** neither `pos_outcome` nor `win_outcome` being empty triggers any
`invalid` state here — if both happened to be `''` after normalization,
`'' == ''` is `True`, and the position would be marked a **winning**
close (`close_price = 1.0`) rather than rejected. Both trade-level
evaluators explicitly guard this exact case and return `'invalid'`.
**[I]** Whether this can occur in practice was not fully traced (would
require confirming `positions.outcome` can never be empty given its
`NOT NULL` schema constraint, and that every market fed into
`apply_synthetic_closes` via `get_resolved_markets_for_trader()` has a
non-empty `winning_outcome` — not verified this session, flagged as
unresolved and out of this task's stated scope) — named as a real
divergence in *shape of failure handling*, whether or not it is currently
reachable, per the same standard applied to §1's differences.

**Stated plainly, per the task's own framing:** yes, this is a third
implementation. The arc's logic — collapse divergent implementations of
the same determination onto one canonical function, enforced structurally
— applies to it exactly as it applies to the two `evaluate_trade`
functions this task was asked to compare. This was not investigated
further for repointability here (different unit, different output type,
a materially larger refactor than the mechanical repoint in §4) — named
as a follow-up question for whoever owns this arc next, not answered.

---

## Summary table

| Question | Answer |
|---|---|
| Statement-level differences? | Yes, 3 real branch-level divergences (§1) |
| Empirically agree? | **Yes — 1,582,064/1,582,064 rows, zero disagreements** |
| Edge cases | All checked cases either don't fire on real data, or are handled identically via a shared upstream SQL filter (one filter, `trade_gap_flag`, coincidentally but not structurally covers O-37 quarantine) |
| Repoint mechanical? | **Yes** — swap a 3-scalar-arg call for a 2-arg method call on an already-available dict; no connection/batching change; one optional SQL-column addition for full (currently-inert) semantic parity |
| Blast radius | Confined to `backfill_trade_results_geo.py` itself; its two other callers (`evaluate_new_trader_results.py`, `backfill_trade_results.py`) are unaffected |
| Third implementation? | **Yes** — `position_tracker.py`'s `apply_synthetic_closes()`, different unit/output type, no `invalid`-handling (a real, unresolved-reachability gap) |

**VERDICT: IDENTICAL-REPOINTABLE.**

---

*Generated 2026-08-19. Sources: `monitoring/trade_evaluator.py` (full
read), `scripts/backfill_trade_results_geo.py` (full read),
`monitoring/position_tracker.py` (lines 366-427),
`2026-08-19-elo-write-architecture-recon.md` (`59a2aee`),
`2026-08-19-geo-backfill-wiring-prereg.md` (`9610f99`), live DB queries
(side/outcome_bet population checks, O-37/trade_gap_flag overlap,
NULL-winning_outcome counts), and this session's new
`scripts/compare_trade_evaluators.py` (first-repo) →
`data/characterizations/trade_evaluator_convergence_20260819T180423Z.json`
(first-repo, both committed this session). No code changed, no evaluator
run in write mode, no repoint implemented.*
