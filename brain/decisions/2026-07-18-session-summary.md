# 2026-07-18 Session Summary — B4 Build Kickoff, Resequenced by "Forward Data Is Unrecoverable"

## Theme

Started the edge-experiment build per Fable's handover order (B4 → B1 → B5 → B3), leading
with B4 (order-book capture) because "start now — every delayed day is unrecoverable data
loss" per the 2026-07-18 MASTER HANDOVER (§4). Following that literally surfaced a token-ID
gap, and then two silent bugs, before B4 could produce usable data. The same
unrecoverability principle that put B4 first is what then dictated fixing the gap and the
bugs before widening capture — one principle, applied consistently, resolved every fork in
the build.

---

## Resequencing decision (deviation from the literal handover order — recorded)

- Handover order was B4 → B1. **Kept B4 first**, but B4's actual first step turned out to be
  a token-ID backfill: capture is structurally impossible for a market with no
  `clob_token_id_yes`/`_no`, so the backfill had to run before any snapshot code touched those
  markets.
- Two capture bugs (below) had to be fixed **before** widening capture scope — capturing
  corrupt data forward across more markets is racing to collect permanently-lost garbage
  faster, not progress.
- **O-37 characterization** is explicitly slotted **before B1**, not before B4 — order-book
  capture doesn't touch the historical trade-synthetics question at all, so it doesn't block
  B4. It's next because it's read-only and cheap, and B1 (PIT replay) benefits from knowing
  whether `trades`-derived aggregates are trustworthy first.
- **Token-backfill scope decision:** open Geopolitics/Elections markets only (1,159 of them),
  not all resolved markets. B2 (2026-07-17 probe) already proved historical token IDs resolve
  on-demand from Gamma/CLOB at backtest time — batch-backfilling the resolved population now
  would be speculative work for a B3 backtest harness that doesn't exist yet.

---

## What shipped

### 1. Token-ID backfill (first-repo, no code change)

Reused the existing `scripts/backfill_clob_token_ids.py` (confirmed the sole writer of
`clob_token_id_yes`/`_no` — no divergent path; B2's price-history probe was a read-only
reimplementation of the same CLOB-primary/Gamma-fallback lookup logic, not a second writer).
Ran scoped via the script's existing `--market-id` flag in a per-market loop over the open
geo/elec population — structurally can't exceed that scope since each invocation targets one
market_id. No code change; the existing 0.2s inter-request sleep was left as-is.

**Result** (verified directly against `data/polymarket_tracker.db`):
- `clob_token_id_yes` population: **3 → 1,107** table-wide.
- Open Geopolitics/Elections markets with a token: **1,105 / 1,159**. **54 unresolvable**
  (feeds the O-37 note below).
- `resolved=1` population unchanged at **2** — confirms zero collateral writes outside the
  scoped open geo/elec set.
- Backup taken first: `backups/markets_20260718_190744.db` (pre-backfill) precedes
  `backups/markets_20260718_201118.db` (post-backfill, pre-order-book-fix).

### 2. B4 market-scan selection (first-repo, commit `33abc7d`)

Additive selector added to `scripts/snapshot_order_books.py`: open Geopolitics/Elections +
`resolved=0` + has a resolved token + traded in the last 7 days. Self-maintaining `WHERE`
clause, no tunable thresholds — quiet markets fall out and newly-active ones fall in each run
on their own. Unioned with (not replacing) the existing signal-linked selection, deduped by
`market_id` with signal markets taking precedence. Per-run liveness summary line added
(`selected=/captured=/skipped_no_token=/failed_no_book=`), printed and appended to
`logs/order_book_capture.log` — makes a silently-empty run impossible to miss. Stays on the
existing **daily** maintenance cadence, deliberately not moved to hourly yet — prove the
selection logic before touching frequency.

### 3. Two silent bugs found and fixed (same commit, `33abc7d`)

Both had corrupted every order-book capture since the script existed:

- **Sort-order bug** — `fetch_book()` truncated CLOB's `/book` response to `top_n` *before*
  establishing best-of-book. CLOB returns bids price-ascending and asks price-descending
  (worst-price-first on both sides), so index 0 was the worst level on each side, not the
  best. Result: `mid_price` pinned near 0.5 and `spread` near 0.98–0.998 regardless of the
  real price, for every row ever captured. Fixed by sorting before truncating.
- **Wrong-token-side bug** — found only by re-verifying through the production path
  (`snapshot_market()`) after the sort-order fix, because the sort-order fix's own unit test
  called `fetch_book()` directly and bypassed `snapshot_market()`'s token selection entirely.
  The new market-scan selector had set `direction='neutral'` for scan rows; that function only
  special-cases the literal string `'YES'`, so anything else silently falls through to the NO
  token — every scan-sourced row in one full production run fetched the wrong side of the
  book. Fixed by using `'YES'` for scan rows (provenance is already carried by
  `snapshot_type`/`signal_id`, not `direction`). This is the more dangerous of the two — it
  passed a test that looked like it covered the change and didn't.

**Proof of the fix**, checked directly against the DB: all 106 `market_scan` rows currently
in `order_book_snapshots` have `spread<=0.5` (zero above) and `token_id == clob_token_id_yes`
(zero mismatches); `mid_price` tracks `clob_market_price_yes` to 3–4 significant figures on
spot checks.

### 4. Session-garbage cleanup (first-repo)

Deleted this session's own bad rows: **214 market_scan rows** (from two full pre-fix
production runs of 106 each, minus the 106 that survived from the final post-fix run — see
`logs/order_book_capture.log`, which shows three `selected=107/captured=107` runs at
19:20Z, 19:52Z, and 20:59Z) plus **3 ad-hoc verification rows**, **217 total**, scoped to
`snapshot_type='market_scan'` — a value that first existed this session and categorically
cannot match any historical row. Backup `backups/markets_20260718_201118.db` verified first;
zero intersection with signal-linked rows checked before and inside the delete transaction.
Left all pre-existing signal-linked rows untouched (deferred — see O-38).

---

## Ledger

**O-38 (new)** — written and ledgered this session in
`brain/decisions/2026-06-29-overhang-ledger.md`, citing commit `33abc7d`. Verified directly
against the DB just now:
- **65** total signal-linked rows currently in `order_book_snapshots`.
- **63 corrupt** (62 pre-existing rows from 2026-06-12 through 2026-07-18T08:56:58Z, all
  `STR003-001/004/007/008`, `spread` 0.98/0.998, plus 1 additional row from tonight's
  *first* pre-fix run at 19:11:11Z, `spread` 0.98). **Deliberately left in place** — real
  STR-003 signal history, deserving its own scoped cleanup decision (delete vs.
  leave-with-a-caveat-flag), not a same-night sweep alongside the two clearly-disposable scan
  batches.
- **2 clean** — both captured tonight *after* the sort-order fix landed: 19:43:12Z and
  20:50:16Z (both `STR003-001`, `spread=0.01`). Note this is one more clean row than the
  ledger entry's prose implies at first read (it discusses the 63-corrupt figure in detail
  but doesn't itemize the 2 clean rows by name) — confirmed directly against the DB for this
  summary, not a discrepancy in the fix itself.
- Future cleanup of the 63 deferred rows must preserve these 2 clean rows.

**O-37 (unchanged this session, but a new corroborating angle found)** — the 54 token-backfill
failures from item 1 above are a **second, orthogonal detector** for the same synthetic-market
population O-37 already flagged: "has substantial DB trade history but no live CLOB/Gamma
listing" independently points at the same duplicate-title markets the trade-stats heuristic
found. Confirmed instance: `0x08e61703a0151fb8b5cd3f589be989b56a1e5349ccfafcc05844a965e901ae9d`
("USA ceasefire agreement before December 2025?", Geopolitics, `resolved=0`, no
`clob_token_id_yes`) — **15,028 trades**, all 15,028 `trade_id`s distinct, all 15,028
`transaction_hash` values NULL. This is one of the five markets O-37 already named as sharing
byte-identical trade stats. This sharpens the O-37 characterization query for next session:
for each geo/elec market with trades, does it resolve a live CLOB token? The ones that don't,
cross-referenced with the duplicate-title clusters, are plausibly the synthetic set. The
ledger entry itself (line 559) has not yet been updated with this angle — that's next
session's characterization work, not done tonight.

---

## Methodology thread

The resequence held under pressure the whole way down: the "forward data is unrecoverable"
principle that put B4 first is the same one that (a) put the token-backfill before capture,
(b) put both bug-fixes before widening capture, (c) justified cleaning this session's own
garbage now while deferring the pre-existing 62 rows to their own decision. One principle
resolved every fork.

Also: the wrong-token-side bug was caught **only** because the sort-order fix was
re-verified through the actual production call path instead of trusting the unit test that
had "confirmed" it — a recurrence of this project's own recurring lesson class (MASTER
HANDOVER §6, pattern 2: "a metric can look like it measures your concern and actually not").
Worth restating because it cost real time here even with the lesson already documented.

---

## State for next session

- **B4 is live and correct**: signal-linked + open-geo/elec-recent-traded selection, daily
  cadence, per-run liveness summary. Accumulating clean forward calibration data; no further
  attention needed unless the liveness log ever shows a silent drop to zero.
- **FIRST THING NEXT SESSION: confirm Writer A's Sunday 2026-07-19 03:00 UTC canonical run
  came clean.** First real run of the Stage 3 canonical ELO path (dry-run forecast a 98.95%
  match baseline — see MASTER HANDOVER §7). Check it matched the forecast, no formula
  divergence, no unexpected drift. This gate has been open since before this session; it just
  needed the clock to catch up.
- Then: **O-37 characterization** (read-only, own session, sharpened query above) → then
  **B1** (PIT replay engine, validated by reproducing the existing 30 `elo_snapshots`
  exactly).
- Deferred/unchanged: O-36 (`fast_resolution_check.py` still stamps `resolution_date` at
  check-time, not event-time — the trade-tape-end workaround insulates the experiment; the
  real fix is not scheduled), the elections-calibration finding (worse-than-naive on
  all-elections, shapes B3/B5 geo/elec stratification, not yet resolved), `is_taker`/
  `transaction_hash` retire-or-wire decision, Tier-3 governance, swarm respawn/verification —
  everything sitting behind the experiment per the 2026-07-15 sequencing call.

---

## Repo state

- **first-repo**: commit `33abc7d` (order-book capture + both bug fixes) pushed to
  `origin/main`. Token-ID backfill and the row cleanup were data/DB operations, not code
  changes, so they don't have their own commit. Routine cron state files
  (`data/.last_requeue_run`, `data/category_backfill_state.json`,
  `logs/focus_ratio_review.json`) committed alongside as a routine state-update commit,
  consistent with prior sessions' convention.
- **trading-swarm**: this summary plus the O-38 ledger entry, `brain/findings.json` (routine
  `score_str003_signals` cron output) and `brain/integration-health.json` (routine daily
  maintenance stamp) committed together. Untracked routine agent-output files
  (`brain/agent-outputs/data-audit/2026-07-18-audit.json`,
  `brain/agent-outputs/pre-resolution/2026-07-18-pre-res-scan.json`,
  `brain/agent-outputs/str002-scoring/2026-07-18-str002-scoring.json`) committed as
  cron-generated artifacts, not session work product.
