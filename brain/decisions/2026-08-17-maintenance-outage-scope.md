# Maintenance outage scope: 2026-07-25 → 2026-08-07

**Date:** 2026-08-17
**Scope:** read-only throughout. No repair, no backfill, no re-run of missed maintenance, no data modification. Scope document only — remediation decisions come after this is read, not during.

**Given, not re-investigated:** `daily_maintenance.py` did not run 2026-07-25 through 2026-08-07 (14 dates) because the machine was powered off (boot `-4` ended 2026-07-24 21:46:17 UTC, boot `-3` started 2026-08-07 09:37:02 UTC). No manual catch-up exists for this window (unlike the separate 07-01 gap). 08-08 and 08-11 each ran twice due to same-day reboots.

---

## VERDICT

**SELECTION RISK.**

The recovery mechanism for missed trade history is proven, mechanism-level, and non-random: `background_backfill_worker.py` — the *only* source of outage-window trade rows found in the data (Part 2b) — will only ever fetch a trader's history if that trader currently has **zero** trades in the DB (`_build_batch()`, exact WHERE clause quoted in Part 1). A trader who was already known and had ≥1 trade before the outage is **permanently excluded** from this recovery path; nothing else re-fetches their history. 144/148 (97.3%) of the reproduced OOS cohort and 142/148 (95.9%) of the matched placebo cohort are exactly this kind of already-established trader (Part 3c). Any real-world trading they did during 07-25→08-07 is invisible in this DB and no currently-running mechanism will ever recover it.

Whether this materially moved the **+0.0316** headline number is **not settled** by this investigation, and should not be rounded into NO IMPACT: the cohort shows 0 positions and the placebo 2 positions with `entry_timestamp` inside the outage window, out of ~3,035 and ~2,528 respectively — but position-entry rate for this specific cohort was *already* collapsing before the outage began (927 positions in the OOS window's first 14 days vs. 5 in the 14 days immediately preceding the outage — Part 3b/5), so a near-zero outage-window count is not distinguishable from trend continuation using data alone. The mechanism is real and the affected population is the majority of the cohort; the magnitude of what it actually cost the headline result is unknown and plausibly small, not zero.

---

## PART 1 — What didn't run

`scripts/daily_maintenance.py` (`STEPS` list, lines 32-80) has 29 steps every day, plus `Run test suite`, `WAL checkpoint`, `Backfill market dates`, `Hydrate stub markets` appended in `main()` (33 total on a weekday), plus `Discover leaderboard traders`, `Sync trade categories [full]`, `Deduplicate trades table` on Sundays (36 total).

| # | Step | What it does | 14-missed-runs consequence | Class |
|---|---|---|---|---|
| 1 | Update research exclusions | Re-applies exclusion criteria to current trader stats | Re-evaluates from current state on resume; nothing time-windowed | **SELF-HEALING** |
| 2 | Sync trade categories `--incremental` | Syncs `trades.market_category` from `markets.category`, 7-day lookback | 7-day incremental window means early-outage trades could be missed by the daily incremental path, but the **weekly `--full-sync`** (no window, full mismatch scan) ran 2026-08-09, 2 days after recovery — catches everything | **SELF-HEALING** (backstopped) |
| 3 | Detect ARB_BOT patterns | Pattern-matches current trader stats | State-based, not time-windowed | **SELF-HEALING** |
| 4 | Promote high-P&L traders | `realized_pnl > 50000` threshold on current state | State-based | **SELF-HEALING** |
| 5 | Resolution sweep | Sweeps traders from newly-resolved geo/elec markets into monitored pool | Docstring shows an optional `--days` lookback; daily-maintenance's default invocation and its default window were **not verified** in this pass | **UNKNOWN** (plausible SELF-HEALING, not confirmed) |
| 6 | Reconcile geo resolved counts [pre-audit] | Recomputes `COUNT(DISTINCT market_id)` aggregate from current state | Pure recompute | **SELF-HEALING** |
| 7 | **Integrity audit (pre-ELO gate)** — `audit_invariants.py --alert` | Read-only Tier-1/2/3 invariant CHECK against the DB; writes JSON report + Telegram alert on failure | Nothing captured, nothing lost — but **zero verification for 14 days**. First post-outage run (08-08) passed cleanly, so no Tier-1 CRITICAL was sitting undetected as of recovery, but nothing checked it during the gap itself | **DEFERRED-HARM** |
| 8 | **Canonical definitions drift** — `check_canonical_definitions.py --alert` | Static code-scan for hardcoded ELO thresholds vs. canonical constants | Pure code-lint, not data/time-dependent; low materiality | **DEFERRED-HARM** (trivial) |
| 9 | Update geo ELO scores | Incremental: traders with `geo_elo IS NULL` or trade-count > stored count | State-diff based, catches up fully | **SELF-HEALING** |
| 10-11 | Score insider / STR-003 signals | Score unscored signals against currently-resolved markets | Backlog-based | **SELF-HEALING** |
| 12 | **Backfill transaction hashes** — `backfill_transaction_hashes.py --tier pool_c` | Fetches tx hashes via Polymarket Data API, which "returns recent trades only (~last few days)" per its own docstring | **PARTIAL PERMANENT LOSS, confirmed empirically** (Part 2b): NULL tx-hash rate for Pool C trades is 40.5% in the outage window vs. 13.1% in the pre-outage 14-day baseline. By the time this step resumed (08-08), the Data API's short retention window had already rolled past most of the outage period | **PERMANENTLY LOST** (partial) |
| 13 | Label maker/taker roles | Needs `transaction_hash` (Polygon RPC receipts) to label a trade | Downstream of #12 — rows that never got a tx hash can never get maker/taker labels either | **PERMANENTLY LOST** (partial, inherits #12) |
| 14 | Verify market titles | Gamma API check for legendary-position / 30-day-recency markets | Current-state, rolling window | **SELF-HEALING** |
| 15 | Backfill market categories | `WHERE category='Unknown'` backlog (11,572 classified on 08-17 alone) | Backlog just grew 14 days' worth; no time-window dependency (already documented interacting with the frozen backtest snapshot — see 2026-08-17 snapshot-drift doc, unrelated to this outage specifically) | **SELF-HEALING** |
| 16 | Fetch new market resolutions — `fast_resolution_check.py` | Bulk scan of **all** currently-resolved markets via Gamma API — resolution status is queryable at any later time, not recency-limited like the Data API | Confirmed empirically (Part 2c): 41/43 geo/elec markets whose write-time `resolution_date` falls in the outage window are captured (`resolved=1`, `winning_outcome` set) | **SELF-HEALING** |
| 17-19 | Register / enrich / score STR-002 signals | `register_str002_signals.py` reads **daily pre-resolution scan files** (`brain/agent-outputs/pre-resolution/*.json`, a *separate* trading-swarm process, not a daily_maintenance step) chronologically; "first-seen wins" | **Pre-res scan files are missing for 2026-07-25 through 2026-08-06** (confirmed: `...07-24-pre-res-scan.json` then next is `...08-07-pre-res-scan.json`, 13 dates gone). Any market+direction that would have first crossed the STR-002 divergence threshold in that window was never observed at that moment — the signal is either never registered, or (if still divergent on 08-07) registered with the *wrong* registration-time state (price, smart-money%, tier as of 08-07, not as of its true first crossing) | **PERMANENTLY LOST** (registration integrity for that 13-day span; separate research track from the OOS thesis result, see Part 3) |
| 20 | Resolve LEGENDARY trader markets | Targeted Gamma queries for still-unresolved LEGENDARY-position markets | State-based | **SELF-HEALING** |
| 21 | Evaluate new trader results | Processes `trade_result='pending'` for flagged/non-excluded traders in resolved markets | Self-healing as a mechanism, but starved of input for any trade row that was never recovered (inherits the trades-recovery gap, Part 2/3) | **SELF-HEALING** (step itself); **inherits** trade-recovery gap |
| 22 | Reconcile geo resolved counts [post-eval] | Same recompute as #6 | Pure recompute | **SELF-HEALING** |
| 23 | Requeue resolved market traders | Timestamp-file gated (`data/.last_requeue_run`); explicitly documented "safe to run multiple times" | Fully idempotent catch-up | **SELF-HEALING** |
| 24 | Apply full ELO modifiers | Recomputes from current DB state | State-based | **SELF-HEALING** |
| 25 | Resync position counts | Recomputes denormalized counters from `positions` | State-based | **SELF-HEALING** |
| 26 | Detect counter-signals | Examines current proven-trader positions vs. signal registration date | Self-healing as a mechanism, but a LEGENDARY/ELITE trader's outage-window reversal is invisible if that trader is in the "already-known" bucket (Part 2d) — same inherited gap as #21 | **SELF-HEALING** (step); **inherits** trade-recovery gap |
| 27 | **Snapshot ELO scores** — `snapshot_elo_scores.py` | Append-only, one row per trader per **calendar day**, into `elo_snapshots` | **PERMANENTLY LOST, confirmed empirically**: zero `elo_snapshots` rows for any date 2026-07-25 through 2026-08-07 (query in Part 1 evidence below). 14 daily trader-state snapshots gone — cannot be reconstructed since trader state has since moved on | **PERMANENTLY LOST** |
| 28 | **Snapshot order books** — `snapshot_order_books.py` | Captures CLOB order-book depth for active signal markets; own docstring: *"Book history CANNOT be backfilled — every missed day is permanently lost"* | **PERMANENTLY LOST, confirmed empirically**: zero `order_book_snapshots` rows for any date 2026-07-25 through 2026-08-07 | **PERMANENTLY LOST** |
| 29 | Write integration health | Writes `brain/integration-health.json` from current DB state | Self-healing for the data it reports, but see Part 4 — the file's own staleness went undetected during the gap | **SELF-HEALING** (mechanism); detection gap noted separately |
| 30 | Run test suite | Runs the full test suite, writes `tests/LATEST_TEST_RESULTS.md` (gitignored, overwritten each run) | 14 days with zero verification of any invariant the suite covers | **DEFERRED-HARM** |
| 31 | WAL checkpoint | `PRAGMA wal_checkpoint(PASSIVE)` | Not time-windowed; one checkpoint clears whatever's accumulated | **SELF-HEALING** |
| 32 | Backfill market dates | `WHERE resolution_date IS NULL`, Gamma API, `--limit 500` | Backlog-based, no recency dependency on the Gamma side | **SELF-HEALING** |
| 33 | Hydrate stub markets (external_seed) | `WHERE resolution_date IS NULL AND market from external_seed`, Gamma API, `--limit 200` | Backlog-based, Gamma metadata isn't recency-limited the way the trades Data API is | **SELF-HEALING** |
| Sun | Discover leaderboard traders | "Top N most-traded" ranking evaluated **at run time** | Two Sundays (07-26, 08-02) never ran. A trader who was only prominent *during* the outage window, if since overtaken in the "top N" ranking by others, may never surface via this discovery path — narrow, low-probability, but a genuine partial loss of *discovery* coverage for that window | **PERMANENTLY LOST** (narrow: only traders whose top-N prominence was outage-window-specific and has since faded) |
| Sun | Sync trade categories [full] | No time window, full mismatch sweep | Ran 08-09, catches everything | **SELF-HEALING** |
| Sun | Deduplicate trades table | Pure current-state dedup | State-based | **SELF-HEALING** |

**Evidence for the two confirmed PERMANENTLY LOST snapshot gaps:**
```
elo_snapshots distinct dates, 07-15..08-15:        ...07-23, 07-24, [GAP], 08-08, 08-09...
order_book_snapshots distinct dates, 07-15..08-15: ...07-23, 07-24, [GAP], 08-08, 08-09...
```
Both tables are `PRIMARY KEY` on `(date, ...)`, `INSERT OR IGNORE`, append-only by design (per their own docstrings) — there is no code path to backfill a historical snapshot date.

---

## PART 2 — What the data did during the outage

### 2a. Row counts vs. neighboring windows

| Window | Trades (event ts) | Markets (resolution_date in window) |
|---|---|---|
| before: 07-11 → 07-24 (14d) | 249,008 | 416 |
| **outage: 07-25 → 08-07 (14d)** | **128,344** | **182** |
| after: 08-08 → 08-17 (10d) | 83,888 | 267 |

Raw comparison alone is misleading (Part 5): the "after" window's *daily* trade rate (8,389/day) is actually **lower** than the outage window's (9,167/day) — overall trade-timestamp volume has been on a general downward trend across this whole period (consistent with the low live-ingestion rate noted in the 2026-08-17 session-start check), not something that started with the outage. The outage-vs-before comparison is real and large, but part of it rides a pre-existing trend, not purely the outage.

### 2b. When were outage-window rows inserted — provenance

`data_source` distribution for trades with **event timestamp** inside 07-25→08-07:
```
background_backfill   128,322
polymarket_api             22
```
**Zero** `live_monitoring`-equivalent live-capture rows, as expected (box was off). For comparison, the "before" window's mix is `background_backfill: 247,926, polymarket_api: 1,082` — `background_backfill` is the dominant `data_source` even in *normal* operation (it's the everyday historical-trade-fetch path, not a special outage-recovery process), so its presence alone doesn't distinguish outage rows from routine rows.

`rowid` ranges (insertion-order proxy) for the three windows overlap heavily and interleave rather than forming one distinct contiguous block — recovery of the outage window happened gradually, mixed in with ordinary ongoing backfill of other periods, not as a single deliberate sweep.

One exception: `data_source='gap_recovery_20260811'` (399 trades) — but its **event timestamps** are all 2026-08-11 06:19–18:24, i.e. this targets the smaller *same-day* 08-11 reboot gap, not the 14-day outage. No script in the current codebase (`grep -rln "gap_recovery"`) produces this tag — it was written by an ad-hoc/manual process with no reproducible code path in the repo. **No equivalent targeted recovery effort exists for the 07-25→08-07 window** — whatever got recovered there came entirely through the ordinary, continuously-running `background_backfill_worker.py`.

### 2c. Markets resolved during the outage — were they captured

Using write-time `resolution_date` (known-unreliable per O-36 — most of these values come from `COALESCE(resolution_date, gamma_end_date)` backfill paths, not "now"-stamps, since nothing could write "now" while the box was off): 182 markets total, 43 geo/elec + gap-clean, of which **41/43 (95%) show `resolved=1` with `winning_outcome` set** — 2 do not.

Using the canonical **tape_end** (event-time, matches yesterday's backtest-population convention) restricted to markets that are *actually* resolved (excluding still-active markets whose last trade merely happens to fall in this window — see Part 5): **18 geo/elec markets** have `resolved=1`, `winning_outcome` set, and `tape_end` inside 07-25→08-07 — i.e., they stopped trading during the outage and their resolution was captured afterward via the Gamma bulk scan (self-healing, per Part 1 #16).

**Candidate genuine holes** (last trade during outage, `resolution_date` already in the past, still `resolved=0` today): **11 markets**, e.g. `0xcf18ec177d891f1ef83de4d8ac6a4bccd0d1310281c64cc874d70c1885915a0a` ("Will Mircea Geoană be the next Prime Minister of Romania?", resolution_date 2026-05-31, last trade 2026-08-05), `0x0c9ada12c527451fbdd43c0397a8a006b8aaf2a01567ae069d37220b51937595` ("Will Karen Bass win the 2026 Los Angeles mayoral election?"), `0x6f78fd69fd6dafb695a8f4074dac11971b1da612bd150aa0c837efbd86417292` ("Will Genter Drummond win the 2026 Oklahoma Governor Republican primary election?"), plus 8 more (full list held in the scratch query, reproducible via the tape_end/resolution_date join in this doc's methodology). These are **candidates for manual review, not confirmed permanent losses** — a resolution_date in the past doesn't guarantee the real-world market has actually concluded (UMA resolution can lag genuinely contested outcomes); distinguishing "still genuinely pending" from "resolution-detection missed it" requires a targeted Gamma check, which is out of scope for this read-only pass.

### 2d. Traders first active during the window — known vs. new

`background_backfill_worker.py`'s trader-selection query (`_build_batch()`):
```sql
SELECT address FROM traders
WHERE is_flagged = 1 AND research_excluded = 0
  AND (SELECT COUNT(*) FROM trades WHERE trader_address = traders.address) = 0
  AND backfill_attempted IS NULL
ORDER BY ... LIMIT 1
```
This **only ever selects a trader with zero trades currently in the DB**, and stamps `backfill_attempted` (never re-selecting them again) after one full-history fetch (paginated, capped at 2,000 trades). It is the sole confirmed source of outage-window trade rows (Part 2b).

Naive test (does the trader have any trade with event-timestamp < 07-25?) initially looked reassuring: of traders with outage-window trades, 1,238 are "known_before_outage" vs. only 72 "new". But this is **misleading** — checked further:
```
backfill_attempted for the 1,238 "known_before_outage" traders:
  after outage (08-08+):  1,202   (97%)
  before outage:             10
  during outage (n/a):       24   (likely a local-vs-UTC timestamp quirk, not re-checked)
  NULL:                        2
```
**1,202 of 1,238** were actually processed by the zero-trade worker **for the first time after 08-08** — meaning at the moment they were "known" (had event-timestamp trades before 07-25) they still had **zero rows in the DB** until a single post-outage fetch dumped their entire real-world trade history (which happens to span before/during/after the outage, since they'd been trading on the actual platform for a while before we ever discovered/processed them). Confirmed on a 5-trader sample of *genuinely* pre-outage-onboarded traders (`backfill_attempted` dated 2026-05-19 through 2026-06-15, well before the outage): **4 of 5 show zero trades in all three windows (before/outage/after)**; the fifth shows 6 trades before, 0 during, 0 after. **No currently-running mechanism has added a single new trade for a genuinely pre-existing, already-onboarded trader since their initial backfill — this is true of the whole recent period, not specific to the outage.** The outage didn't create this gap; it's how the system already behaves for anyone past initial onboarding. The outage just means this pre-existing structural gap now also covers 07-25→08-07 for anyone who was already known before it.

---

## PART 3 — Does it touch the result of record

Reproduced `trader_skill_metric_v2f.py`'s Objective 2 cohort/placebo (read-only: `build_presplit_cohort()`, `match_control()`, `measure_oos()`, called directly with `T_SPLIT="2026-04-01 00:00:00"`, `SEED=42`, no `--persist`, no writes). Reproduction: **n=148 cohort traders / 148 matched placebo, 3,035 cohort positions / 2,528 placebo positions** — close to but not identical to the persisted result of record (3,032 / 2,569; cohort matches almost exactly, placebo differs by 41, plausibly from DB drift or matching-order sensitivity in the 2 days since the 08-15 run). Same order of magnitude, same cohort size — adequate for outage-window intersection analysis, not a byte-for-byte replay of the frozen artifact.

### 3a. Event timestamps inside the outage window
```
OOS COHORT (n=3,035 positions): 0 with entry_timestamp in 07-25..08-07
PLACEBO   (n=2,528 positions): 2 with entry_timestamp in 07-25..08-07
  0x4d0121_0xbe48df_Yes_1785354866  trader 0x4d0121458bb2f96c6440c0f3835d675ad3ce1645  market 0xbe48dfd8fb2d44ebad08c3b170799c6633af2b68ce0df17e633e12a89ed734e3  2026-07-29T19:54:26
  0xc281ad_0xbf08ec_No_1785864509   trader 0xc281ad222df6d91ba397fb3b086130998fd6e079  market 0xbf08ec6654ade883d96f3e25a5330ccf4aae0d8e9efa690c694305e95738e8a1  2026-08-04T17:28:29
```
Both placebo traders have `backfill_attempted` on **2026-08-10** — after the outage, consistent with Part 2d's "looked new at recovery time" mechanism (both markets, incidentally, are also members of yesterday's snapshot-drift T2f leak set).

### 3b. Fraction of OOS-window calendar days with no ingestion
Literal answer, measured by event-timestamp presence: **0 of 139 days** (04-01→08-17) have zero trade rows — because backfilled rows retain their true historical event timestamp, so a day can show "coverage" purely from data recovered weeks later. **This is the wrong question to answer with this metric** (Part 5) — it reads as "no gap" when the real gap is in *live* capture, not event-timestamp presence, which Part 2b already answers correctly (0 `polymarket_api`/live-sourced trades in the outage window). Restated correctly: **14 of 139 days (10%) of the OOS window had zero live capture**, fully consistent with the machine being off.

### 3c. Selection effect on the OOS population — established concretely
```
OOS cohort backfill_attempted:    before_outage=144 (97.3%)  after_outage=3   NULL=1
Placebo cohort backfill_attempted: before_outage=142 (95.9%)  after_outage=4   NULL=2
```
The cohort/placebo populations are **not** the "new since outage" population that dominates Part 2's raw outage-trade-count analysis — they are overwhelmingly (95-97%) genuinely pre-existing, already-onboarded traders. Per Part 2d, this is exactly the population for whom the outage-window recovery mechanism structurally does not exist. If these traders traded materially during 07-25→08-07, that activity is gone and unrecoverable by any means currently running.

**Boundary check (Part 5, required):** is the observed near-zero count (0 cohort, 2 placebo) evidence the gap bit them, or just that they weren't trading much anyway? Position-entry rate for this exact cohort, by 14-day window:
```
04-01..04-14 (early OOS):        927 cohort / 641 placebo
07-11..07-24 (pre-outage 14d):     5 cohort /   2 placebo
07-25..08-07 (OUTAGE 14d):         0 cohort /   2 placebo
08-08..08-17 (post-outage, 10d):   0 cohort /   0 placebo
```
Position-entry activity for this specific cohort had **already collapsed to single digits in the two weeks immediately before the outage began** — nearly all of the ~3,035/2,528 OOS positions were entered in the weeks right after T_split (04-01), tapering sharply thereafter. Given that trend, an outage-window count of 0-2 is not distinguishable from ordinary trend continuation using data alone; it would very plausibly have been small even with zero outage. **This is not evidence of no impact** — the recovery-mechanism gap (Part 1/2) is real regardless of magnitude and would apply to any position these specific traders entered in that window — it is evidence that the magnitude of what was actually lost, if anything, cannot be pinned down from what's observable, precisely because what's missing is missing.

### 3d. Does the snapshot's 07-24 freeze timing add anything beyond yesterday's characterisation
`bt_pop_2025-11-01_v1` was frozen 2026-07-24T18:54:00Z — **before** the outage began (boot `-4` didn't end until 21:46:17 that day). The snapshot table is confirmed append-only/intact (yesterday's investigation) and nothing in the outage touches an already-frozen, read-only artifact. The outage does not add a new snapshot-integrity risk. It does, however, widen the live-side drift yesterday's doc already characterized (category `'Unknown'` → `Geopolitics`/`Elections` reclassification continuing after the freeze) by adding 14 extra days to that backlog before the reclassification step resumed — consistent with, not separate from, yesterday's finding.

---

## PART 4 — Detection

### 4a. Was there any alert
**Partially — one indirect, retroactive signal, no direct one.** `monitoring/system_observer.py`'s ELO-staleness monitor (`_check_elo_staleness()`, runs every 10 min, Telegram-alerts via `_should_send_alert('elo_staleness_warning', minutes=360)`) fired **once the box came back up**:
```
Aug 07 10:10:11 polymarket-observer: [OBSERVER] ELO staleness: last recalc 2026-07-24 (14 day(s) ago)
Aug 07 10:10:11 polymarket-observer: [OBSERVER] WARNING ELO staleness alert sent (14 days)
```
This is a real, working alert — but it is a **proxy** (ELO recalculation staleness, not "box is down" or "maintenance hasn't run"), it could only fire *after* recovery (the observer service was itself off during the outage — no possible detection during the 14 days), and it carries no record of when the gap started or how long it had been building had the box stayed down longer. **No alert, log banner, or notification exists that would have caught the outage while it was happening**, and none exists today that specifically says "maintenance hasn't run in N days" as opposed to this one ELO-specific proxy.

### 4b. What could support detection without new infrastructure
- `brain/integration-health.json` already computes a `last_maintenance` timestamp (`write_integration_health.py::get_last_maintenance_timestamp()`, via DB file mtime) but **never evaluates it** — the existing `alerts` list only checks `clean_pool`, `clean_markets`, `wal_mode`. Adding an age threshold to that same list is a small change to code that already exists and already runs as the last maintenance step.
- `system_observer.py`'s `_check_elo_staleness()` is a ready-made template (staleness computation + rate-limited Telegram alert) that already exists and already runs continuously (independent of `daily_maintenance.py`). The same pattern, pointed at "time since last `daily_maintenance.py` completion" instead of "time since last ELO recalc," would catch this class of gap directly, using code that's already proven to work.
- `journalctl --list-boots` / systemd already records exactly the boot-gap evidence used throughout this and yesterday's investigation — a boot-time check (e.g. "was there a boot gap since the last known-good state") is available without any new tooling.

### 4c. Does any status surface show "last successful run" prominently
No. `build_banner()` (`daily_maintenance.py`) only reports **that day's own** step pass/fail counts — `"=== MAINTENANCE COMPLETE — ALL OK: 33/33 steps === Xs total ==="` or the FAILURES variant. It has no memory of any previous run and prints only to `logs/daily_maintenance.log`. The 08-08 resumption's banner is indistinguishable in form from any ordinary day's banner — nothing in it signals that 14 days had passed since the previous one.

---

## PART 5 — Boundary check (applied throughout, summarized)

- **Part 2a** (raw trade-count comparison): flagged as partly a boundary artifact — the "after" window's daily rate is *lower* than the outage window's, showing a broader declining trend that the before/outage comparison alone would not reveal.
- **Part 2c** (markets resolved during outage): the first version of this query (tape_end-in-window, no `resolved=1` filter) produced a list of "unresolved markets" that was actually just ordinary still-trading, far-future-dated markets — a boundary artifact of not filtering on `resolved`. Corrected before reporting.
- **Part 3b** (OOS-window ingestion-gap fraction): the literal metric requested (days with a trade timestamp present) reads as 0% missing, which is an artifact of backfilled rows keeping their true historical timestamps — not evidence the outage didn't matter. Reported both the literal (misleading) number and the corrected one (live-capture-based, 10%).
- **Part 3c** (selection risk magnitude): the observed near-zero outage-window position count for the OOS cohort could look like confirmation of harm, but the immediately-preceding 14-day window already shows the same near-zero rate — a different comparison window (uniform density across the full 139-day OOS span, ~306 expected) would have made 0 look dramatically anomalous; the correct local comparison (trend-adjacent window) makes it unremarkable. Reported as genuinely unsettled rather than picking whichever comparison produced the more dramatic story.

---

## Reproducibility

Part 1 classifications are from reading each script's docstring/header and, where load-bearing, its actual WHERE-clause logic (`background_backfill_worker.py::_build_batch()` quoted in full; `write_integration_health.py` read in full). Parts 2-3's counts come from short read-only Python scripts (`sqlite3.connect(..., mode=ro)` where the query stood alone; the OOS reproduction used the project's own `db_connect()` since it's called via the actual `trader_skill_metric_v2f.py` functions with no `--persist` and no write statements issued) run from a scratch directory, not committed. Part 4's boot/alert evidence is from `journalctl` (systemd, local) and `logs/daily_maintenance.log`. This investigation made no changes to the repository or the database other than this document.
