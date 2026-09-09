# Telegram Senders Audit — the DB Audit and the LEGENDARY Trader Alert

**Scope:** READ-ONLY. No file in `scripts/audit_invariants.py`, any alert
path, `column_definitions.py`, or the accepted-failures register was
modified. This audits the two Telegram senders named as candidates for
keeping in the wake of the 2026-09-07 telegram remediation
([[2026-09-07-telegram-alert-audit]], [[2026-09-07-telegram-remediation]],
first-repo `51e3b74`/`f6a8b88`): (1) the daily DB integrity audit
(`scripts/audit_invariants.py --alert`), and (2) the observer's LEGENDARY
trader alert (`monitoring/system_observer.py::_check_legendary_trades`).
The hourly report, startup announcements, and slow-trade notices are a
separate task and were not investigated.

Tagging: **[V]** = verified this session (code / DB query / log / git read
directly); **[I]** = inferred from verified facts; **[U]** = undetermined.

---

## STOP CONDITIONS — none triggered

- **None of the five audit invariants is a new, unrecorded, live
  data-integrity failure.** All five are already characterised in prior
  decision docs — principally
  `2026-08-19-pending-invariant-regression.md` (the two `pending`
  checks) and `2026-08-30-end-to-end-verification.md` §4a / ranked
  findings #6, #8, #10, #11 (all five, with trend directions). Two
  *mechanism details* are newly pinned this session — the specific driver
  of the timestamp growth (`backfill_market_dates.py`'s `.isoformat()`)
  and the specific literal behind the 577 (`gap_recovery_20260811`) — but
  both are new detail on already-recorded regressions, not new incidents.
- **The LEGENDARY alert only notifies.** `_check_legendary_trades()` runs
  one `SELECT`, calls `self.telegram._send_message(...)`, and records the
  trade_id in an **in-memory** `set` (`_alerted_legendary_trades`,
  `system_observer.py:1358-1366`). No `INSERT`/`UPDATE`, no file write, no
  downstream consumer. [V]

---

## PART 1 — THE DB AUDIT (`scripts/audit_invariants.py`)

### 1.0 How the alert fires

`daily_maintenance.py` step 7 runs `audit_invariants.py --alert` before
the ELO steps. `send_telegram_alert()` (`:867`) sends **whenever
`criticals or regressions` is non-empty** — i.e. on every run that has any
Tier-1 CRITICAL or any Tier-2/Tier-3 count over floor. It self-loads
`/home/parison/.env_trading` (`:1001`), so its credential path works
(confirmed live in [[2026-09-07-telegram-alert-audit]] Part 1). The five
rows below have made this alert fire every day for months.

### 1.1 Floor provenance (git)

| Constant | Value | Set by | Date | Kind |
|---|---|---|---|---|
| `FLOOR_PENDING_FLAGGED` | 0 | `e72fd5e` (harness creation) | 2026-06-18 | **Aspirational** — comment: *"stays 0 as long as daily evaluation keeps pace."* Baseline run showed 0; broke floor the next day (10,460 on 06-19). |
| `FLOOR_PENDING_GEO` | 0 | `e72fd5e` | 2026-06-18 | **Aspirational** — same comment, same fate (753 on 06-19). |
| `FLOOR_TS_TOTAL` | 24996 | `b30c5ff` | 2026-06-18 | **Point-in-time capture** — comment: *"Set to last-observed total count (2026-06-18); expected until Teardown 3."* Equal to that day's own count. Teardown 3 never happened. Not revalidated when `fc6c6c5` (2026-07-14) reset the `elo_last_updated` per-column floor (23,163 → 22,560) — the sum of per-column floors is now 24,387, not 24,996. |
| `FLOOR_DS_INVALID` | 0 | `393a908` | 2026-06-25 | **Deliberate, with recorded reason** — commit msg: *"the migration verified every row non-NULL + in-set, so any future violation is a genuine regression introduced by a write path."* This 0 is correct by design. |
| `FLOOR_INVESTED_MISMATCH` | 0 | `e72fd5e` | 2026-06-18 | **Aspirational Tier-3** — "structural baseline to be driven down by a specific Teardown" that was never scheduled. Baseline run 0; 23 on 06-19. |

**Same pattern as the backtest test's hardcoded counts:** `FLOOR_TS_TOTAL`
is a captured-baseline nobody revalidated. The two `pending` floors and
`FLOOR_INVESTED_MISMATCH` are "we hope this stays ~0" values, not
measured baselines. Only `FLOOR_DS_INVALID` is a deliberate 0 backed by a
verified post-migration clean state.

### 1.2 Trend history (from the harness's own daily JSON reports, `~/trading-swarm/brain/agent-outputs/data-audit/`, 71 reports 2026-06-18 → 2026-09-09; gap 07-25 → 08-06 = migration/trade-gap window)

| Invariant | 09-08 | 09-09 | Floor | Above floor since | Direction (establishable window) |
|---|---|---|---|---|---|
| pending, resolved non-gap, flagged | 3,127 | 2,829 | 0 | 2026-06-19, ~continuously (brief exact-0 on 06-27, 07-23, 08-08, 08-09, 08-12, 08-18) | **No trend** — oscillates 0 ↔ 600k+ (spikes: 993k 07-03, 300k 07-08, 486k 09-03). Day-over-day shrank 3,127→2,829; over 30 days no monotonic direction. |
| pending, resolved non-gap, geo/elections | 24,103 | 24,644 | 0 | 2026-06-19, continuously (one exact-0 on 06-22) | **Slow net growth.** ~21,000 (late Jul) → ~24,600 now; ≈ +600/month. Day-over-day +541. |
| timestamp mixed formats (total) | 35,065 | 35,447 | 24,996 | PASS 07-06 → 08-23; **REGRESSION continuously since 2026-08-24** (16 days) | **Growing ~+400–580/day.** 26,181 (08-24) → 35,447 (09-09). Entirely in `markets.end_date` (1,836 → 9,768) and `markets.resolution_date` (1,788 → 3,128); `traders.elo_last_updated` stable at 22,551. |
| data_source not in canonical set | 577 | 577 | 0 | **2026-08-12** (580), stepped to **577 on 2026-08-17**, unchanged 23 days | **Static / frozen.** One step down (580→577) on 08-17, flat since. |
| total_invested vs SUM(entry_total_cost) >5% | 14,216 | 14,216 | 0 | ~2026-06-28 continuously (73+ days) | **Growing, stepwise.** 10,073 (08-22) → 14,216 (09-09). Long plateaus (10,055 held ~Jul 21 – Aug 22) punctuated by steps; frozen at 14,216 only 3 days (09-07→09-09). |

### 1.3 Per-invariant findings

#### (1) `pending on resolved non-gap markets (flagged traders)` — 3,127 → 2,829

- **Checks:** count of `trades` rows with `trade_result='pending'` on a
  `resolved=1`, non-gap market, for `is_flagged=1 AND research_excluded=0`
  traders. Unit is **trade rows**, not markets/positions
  (`audit_invariants.py:252-276`).
- **Floor provenance:** `e72fd5e`, 2026-06-18. Aspirational 0.
- **Above floor:** since 2026-06-19 (day after creation), ~continuously,
  with brief returns to exactly 0.
- **Direction:** no trend. This is a **within-cycle backlog gauge**: the
  audit runs at daily-maintenance step 7; `evaluate_new_trader_results.py`
  — whose target population is *exactly* this predicate — runs at step 21.
  Each day's audit reads whatever accumulated since the previous day's
  step 21, before that day's step 21 clears it. Root-caused in
  `2026-08-19-pending-invariant-regression.md` Q4 ("REAL, self-healing").
- **Stranded-markets connection:** **not the same defect.** The flagged
  fast-path (`evaluate_new_trader_results.py`) is a different pipeline
  from `requeue_resolved_market_traders.py` / `last_checked`. Same
  "resolution follow-up" family, different gate.
- **Verdict: floor set wrong** (aspirational 0 for a quantity that has
  never held) **+ already recorded** (2026-08-19 doc). Not a new problem.

#### (2) `pending on resolved non-gap geo/elections markets` — 24,103 → 24,644

- **Checks:** count of `trades` rows with `trade_result='pending'` on a
  `resolved=1`, non-gap market in `category IN ('Geopolitics','Elections')`
  — **every trader**, flagged or not, excluded or not
  (`:279-300`).
- **Floor provenance:** `e72fd5e`, 2026-06-18. Aspirational 0.
- **Above floor:** since 2026-06-19, continuously (one exact-0 on 06-22).
- **Direction:** slow net growth on a generally-rising base.
- **Root cause (recorded):** `2026-08-19-pending-invariant-regression.md`
  Q4 — **no daily evaluator exists for this population.**
  `backfill_trade_results_geo.py` was written specifically to close this
  gap but is **not wired into `daily_maintenance.py`**. Additionally
  `background_backfill_worker.py:305-311` inserts every backfilled trade
  with `trade_result` hardcoded to `'pending'`, never evaluated at ingest
  (63.6% of the backlog is `background_backfill` provenance). Also listed
  as `2026-08-30-end-to-end-verification.md` ranked finding #6.
- **Stranded-markets connection:** **adjacent, not identical.** Both are
  "resolved markets whose downstream never runs," but the stranded defect
  is `pnl_last_updated` on *open positions* via `requeue`; this is
  `trade_result` on *trade rows* via `evaluate`. The 2026-08-30 doc lists
  them as two separate DEGRADING findings (#1 vs #6).
- **Verdict: problem already known and recorded** (2026-08-19 +
  2026-08-30 docs). Floor 0 is also wrong as a gate, but the underlying
  standing gap is real and tracked.

#### (3) `timestamp mixed formats (per-column breakdown)` — 35,065 → 35,447

- **Checks:** for 8 (table, column) pairs, counts rows in the *minority*
  timestamp format for that column (binary `LIKE '%T%'` test), sums them,
  and compares the sum to `FLOOR_TS_TOTAL` (`:328-379`). The **status is
  driven by the summed total**, not the per-column detail.
- **Floor provenance:** `b30c5ff`, 2026-06-18 — explicit point-in-time
  capture ("last-observed total count (2026-06-18); expected until
  Teardown 3"). Never revalidated; stale by construction. **This is the
  same failure mode the task flags in the backtest test.**
- **Above floor:** REGRESSION during 06-19→07-05 (migration noise), PASS
  07-06→08-23 (sat ~23,000, below 24,996), **REGRESSION continuously
  since 2026-08-24.**
- **Direction:** growing ~+400–580/day. **[V]** Entirely in
  `markets.end_date` (per-column floor 946; now 9,768) and
  `markets.resolution_date` (floor 881; now 3,128). Live format
  breakdown: `end_date` = 216,532 space-sep + **9,154 `T…+00:00`** + 990
  `T…Z`; `resolution_date` = 440,684 space-sep + **2,346 `T…+00:00`** +
  975 `T…Z`. The `T…+00:00` slice is what is growing.
- **Driver (newly pinned this session, [V]):**
  `scripts/backfill_market_dates.py`. Its `_parse_end_date()` (`:53-63`)
  returns `datetime.fromisoformat(...).isoformat()` /
  `datetime.fromtimestamp(ts).isoformat()` — Python `.isoformat()` emits
  `T`-separated strings with a `+00:00` offset. Its two writers —
  `UPDATE markets SET end_date=?` (`:335`) and
  `UPDATE markets SET end_date=?, resolution_date=COALESCE(resolution_date,?)`
  (`:383-387`) — bind that string directly. The script runs in
  `daily_maintenance.py` at `--limit 2000/day` (held only during active
  sweep segments, `daily_maintenance.py:~446`); the run cadence began in
  earnest around the 08-21 discovery-gap work (`5fcbffe`, `bd672fb`,
  `e4ddb67`), which lines up with the REGRESSION starting 08-24. The
  `T…Z` slice (≈2,000 rows, static) is older raw-API passthrough, not
  this script.
- **The check itself is also known-flawed** independent of the floor —
  aggregate masking, majority-wins "canonical", `%T%`-binary blindness to
  microsecond/timezone variants: documented at length in
  `2026-06-29-overhang-ledger.md` items 5.1 / O-35 and
  `2026-07-07-silent-failure-audit-FABLE.md` item 5.1.
- **Stranded-markets connection:** none. Timestamp-format hygiene.
- **Verdict: floor set wrong** (stale point-in-time capture; "Teardown 3"
  never happened) **AND a real, recorded, growing write-path regression**
  (2026-08-30 finding #8, "growing ~650/day"). The growth is genuine and
  live, but it is not new or unrecorded; this session adds the specific
  driver. The count now exceeds even the stale floor, so fixing the floor
  alone would not silence it.

#### (4) `data_source not in canonical set (write-path regression)` — 577 → 577 *(FROZEN)*

- **Checks:** per core table, `COUNT(*)` where `data_source IS NOT NULL
  AND data_source NOT IN (<canonical set>)`, IN-clause built at runtime
  from the `cd.DATA_SOURCE_*` frozensets (`:399-428`).
- **Floor provenance:** `393a908`, 2026-06-25 — deliberate 0, backed by a
  verified post-migration all-in-set state. Correct.
- **Frozen? — closed historical set, NOT a dead check. [V]**
  - The check *does* re-measure: it is a live `COUNT` each run, and it
    **stepped 580 → 577 on 2026-08-17** — proof it re-evaluates.
  - It is flat because the offending rows are a **static, bounded set**:
    **178 `markets` rows + 399 `trades` rows, all
    `data_source = 'gap_recovery_20260811'`** (178 + 399 = 577, [V] by
    direct query). That literal — from the 2026-08-11 gap-recovery
    operation — was never added to `cd.DATA_SOURCE_MARKETS` or
    `cd.DATA_SOURCE_TRADES`. Nothing writes it any more; nothing has
    re-stamped those rows.
- **Recorded:** yes — `2026-08-30-end-to-end-verification.md` line 217 /
  ranked finding #10 ("flat at 577 for 3 straight days, frozen legacy
  population, not growing"; classified COSMETIC), and
  `2026-08-30-canonical-writer-column-gap.md` §2.3 ("the already-known,
  already-flat '577 data_source not in canonical set' REGRESSION …
  narrow, frozen, no new [concern]"). This session adds the exact literal.
- **Stranded-markets connection:** none.
- **Verdict: problem already known and recorded; floor is correct.** A
  real-but-static write-path/definitions gap (one missing frozenset
  entry), bounded at 577, non-growing, low severity.

#### (5) `total_invested vs SUM(entry_total_cost) mismatch >5%` — 14,216 → 14,216 *(FROZEN 3 days)*

- **Checks:** count of traders where
  `ABS(total_invested − SUM(positions.entry_total_cost)) / total_invested
  > 0.05`, over `status='closed'` positions, excluding `pnl_skip=1`
  traders (`:489-526`). Tier 3 → REGRESSION when count > floor × 1.10;
  with floor 0 that is any count > 0.
- **Floor provenance:** `e72fd5e`, 2026-06-18 — aspirational Tier-3 0.
- **Frozen? — batch-update cadence, NOT a dead check and NOT a closed
  set. [V]** The check is a live `GROUP BY … HAVING` query each run.
  History shows it holds flat for **weeks** then steps (10,055 held
  ~2026-07-21 → 08-22, then climbed to 14,216). It moves when a
  reconciliation batch (`reconcile_trader_aggregates.py`) or a tranche of
  newly-closed positions lands; 3 days flat (09-07→09-09) is well within
  its normal plateau length. The 07-08 jump (150 → 9,437) coincides with
  the O-15 fix that reset `pnl_skip=0` on 1,421 traders
  ([[project_o15_pnl_worker_datetime_bug]]), suddenly pulling them into
  scope — consistent with a live re-measuring check.
- **Recorded:** `2026-08-30-end-to-end-verification.md` ranked finding
  #11 ("slow drift ~10-15/day … no identified consumer depends on this
  being exact"; classified COSMETIC).
- **Stranded-markets connection:** weak / indirect. The stranded defect
  blocks `pnl_last_updated` reconciliation for ~1,168 traders, which
  *could* contribute, but `entry_total_cost` is entry-side and does not
  change on resolution; the dominant mechanism is new positions opened
  faster than `total_invested` is reconciled, plus the 07-08 pnl_skip
  reset. Not the stranded defect.
- **Verdict: problem already known and recorded; floor is aspirational**
  (a Teardown target never scheduled). Reconciliation lag, not
  corruption.

### 1.4 The two frozen counts — closed set vs dead check

| | 577 (data_source) | 14,216 (invested_mismatch) |
|---|---|---|
| Re-measures each run? | **Yes** — stepped 580→577 on 08-17 | **Yes** — live GROUP BY/HAVING; stepped repeatedly over its history |
| Why frozen | **Closed historical set** — 577 `gap_recovery_20260811` rows, no live writer, no fixer | **Batch-update cadence** — moves only when reconcile / new closed-position tranches land; 3-day flat is normal (held ~4 weeks at 10,055 earlier) |
| Dead check? | No | No |

---

## PART 2 — THE LEGENDARY TRADER ALERT

### 2.1 Which script / function

`monitoring/system_observer.py`, `SystemObserver._check_legendary_trades()`
(`:1215-1354`). Runs under `polymarket-observer.service`; called from the
hourly loop (`:490`) with a 48-hour lookback, dedup by `trade_id` via the
in-memory `_alerted_legendary_trades` set. Emits via
`self.telegram._send_message()` (`:1347`). **Notify-only** — no DB write.

### 2.2 Which column assigns "LEGENDARY", and the threshold

- **Gate (SQL `WHERE`, `:1256-1263`):**
  ```
  (t.geo_elo_active >= {GEO_ELO_LEGENDARY} AND t.geo_accuracy_pool = 1
   AND t.research_excluded = 0 AND t.bot_type IS NULL)
  OR COALESCE(t.watched, 0) = 1
  ```
  plus `tr.timestamp >= <48h ago>` and `tr.shares >= 500`.
- **Badge (`:1285-1287`):** `LEGENDARY` iff
  `geo_elo_active is not None and geo_elo_active >= GEO_ELO_LEGENDARY and
  geo_accuracy_pool == 1`.
- **Column read for the badge: `geo_elo_active`** (the decay-adjusted
  one) — **not** `comprehensive_elo`, not `geo_elo`.
- **Threshold:** `GEO_ELO_LEGENDARY = 2175.0`, imported from
  `monitoring/column_definitions.py` (`system_observer.py:34`;
  `column_definitions.py:89`). Same module and same constant from which
  `cd.LEGENDARY_GATE_WHERE` is built (`column_definitions.py:123-128`).

### 2.3 Does it reference `cd.LEGENDARY_GATE_WHERE` or a canonical constant?

- It does **not** import the `LEGENDARY_GATE_WHERE` string fragment. It
  **hand-rolls the same four predicates** inline in the SQL.
- It **does** use the canonical numeric constant `cd.GEO_ELO_LEGENDARY`
  (via f-string interpolation), not a hardcoded `2175`. This is the
  result of `3919946` (2026-06-23, "Tier-2 Batch 1 — repoint 4 TRIVIAL
  scripts to canonical definitions"), which repointed this file's two
  badge thresholds.
- The SQL `WHERE` disjunct for LEGENDARY is byte-for-byte equivalent to
  `LEGENDARY_GATE_WHERE`. **One latent gap:** the *badge* re-check
  (`:1285`) drops `research_excluded = 0 AND bot_type IS NULL`. Harmless
  for rows that entered via the LEGENDARY disjunct (they already satisfy
  all four), but a `watched=1` trader with a stale
  `geo_elo_active >= 2175` and `geo_accuracy_pool = 1` who is
  `research_excluded = 1` would be badged "LEGENDARY" — unless caught
  first by the `is_watched and elo < 2000 → "WATCHED"` branch (`:1282`).
  Not what happened with Bperil.

### 2.4 The Bperil alert is CORRECT. The premise "1464 does not clear 2175" is a misread.

**[V]** Bperil = `0xc624cccd414dc90ea329f06cf535fafa40d2ee24`, live DB now:

| column | value | clears canonical gate? |
|---|---|---|
| `comprehensive_elo` | **1464.14** | — (not used by the gate) |
| `geo_elo` | 2584.47 | — (not used by the gate) |
| **`geo_elo_active`** | **2564.65** | ✅ ≥ 2175 |
| `geo_accuracy_pool` | 1 | ✅ |
| `research_excluded` | 0 | ✅ |
| `bot_type` | NULL | ✅ |

Bperil **fully clears `cd.LEGENDARY_GATE_WHERE`** right now. The "1464" in
the alert is `comprehensive_elo`, which the message **displays on the
`ELO:` line** (`elo` = `t.comprehensive_elo`, selected `:1238`, formatted
`:1303`, rendered `:1309` as `ELO: {elo_str}  |  Tier: {tier_badge}`). The
badge itself came from `geo_elo_active = 2564.65`. Two different metrics,
one generically labelled "ELO", printed side by side — which is what makes
the alert *look* self-contradictory. **The gate is not broken; the
display is misleading.**

### 2.5 Relationship to the 2026-06-07 fix

The task cites *"MASTER_HANDOVER_2026-09-05 §6"* for the note
*"system_observer.py LEGENDARY badge — Fixed 2026-06-07, comprehensive_elo
→ geo_elo + geo_accuracy_pool."* **[V] That citation is wrong.**
`MASTER_HANDOVER_2026-09-05.md §6` ("KNOWN DEFECTS, LIVE AND UNFIXED")
contains no such line. The note is real but lives in
**`MASTER_HANDOVER_2026-06-10.md:493`** (and
`2026-06-07-session-summary.md:33`). The note's content is accurate.

Git history of this exact code path:

| commit | date | change |
|---|---|---|
| `fa9fdc9` / `d9a7c160` | 2026-02-22 / 02-28 | original; badge from `comprehensive_elo >= 2500`; **`SELECT t.comprehensive_elo` + `ELO:` display line added here** |
| `c6d5842` | **2026-06-07** | **the referenced fix** — badge gate `comprehensive_elo >= 2500` → `geo_elo >= 2175 AND geo_accuracy_pool = 1` |
| `4d05ac0` | 2026-06-10 | `geo_elo` → `geo_elo_active`; add NEAR_LEGENDARY tier |
| `e92b7e5` | 2026-06-11 | re-enable `_check_legendary_trades` (Phase 5 Gate 2) |
| `109da29` | 2026-06-16 | raise threshold / drop ELITE + leaderboard tiers (noise) |
| `3919946` | 2026-06-23 | repoint `2175`/`1800` literals to `cd.GEO_ELO_*` |

**This is the same code path as the 2026-06-07 fix, and the fix is
intact.** The gate moved off `comprehensive_elo` and now uses
`geo_elo_active + geo_accuracy_pool` (plus `research_excluded`/`bot_type`)
correctly. What the 2026-06-07 fix did **not** touch is the Feb-2026
`SELECT t.comprehensive_elo` and the `ELO:` display line — so the message
still surfaces `comprehensive_elo` next to a `geo_elo_active`-derived
tier. **The Bperil alert is neither a regression nor a missed code path —
it is a residual display inconsistency left by a fix that only touched
gating.**

### 2.6 Why `check_canonical_definitions.py` does not flag it

`check_canonical_definitions.py` is a **hardcoded-literal** drift guard
(`scripts/check_canonical_definitions.py`). It scans every `*.py` under
the repo (`ROOT.rglob("*.py")`, exempting only `column_definitions.py` and
itself) — so `system_observer.py` **is in scope** — via three AST/regex
gates:

1. **`visit_Compare`** — flags `geo_elo[_active] <op> <Constant>` where the
   constant is literally in `GATE_THRESHOLDS = {2175, 1800, 1400, 1000,
   500}`. `system_observer.py:1285` is
   `geo_elo_active >= GEO_ELO_LEGENDARY` — the right operand is an
   `ast.Name`, **not an `ast.Constant`** → no match.
2. **`visit_Constant` + `RE_RAW_THRESHOLD`** (`\bgeo_elo(?:_active)?\s*>=\s*(?:2175|…)\b`
   inside a string literal in SQL context) — the observer's SQL is an
   **f-string** (`ast.JoinedStr`), and its `{GEO_ELO_LEGENDARY}` is a
   `FormattedValue`, not part of any string `Constant`. The literal text
   segment is `"… t.geo_elo_active >= "` with **no number in it** → no
   match.
3. **Pool-C copy-paste** — not relevant.

So: **the code already passed this scanner's migration** (`3919946`
explicitly repointed it) and there is genuinely no hardcoded threshold
left to flag. The scanner has **no rule** about which column a message
*displays*, about `comprehensive_elo` being mislabelled "ELO", or about
whether the alert imports `cd.LEGENDARY_GATE_WHERE` versus reconstructing
its predicates — it only bans the literal `2175`. The display
inconsistency is entirely outside its design. (The current violation set
is still exactly 7, all in `trader_skill_metric_v2*.py`, per
`2026-08-30-end-to-end-verification.md` §1c and
[[2026-09-07-canonical-enforcement-part1-stop]].)

### 2.7 Firing history (observer journal; retention starts 2026-06-05, alert re-enabled 2026-06-11)

`[LEGENDARY] Alert sent for …` lines, **2026-08-01 → 2026-09-07 window
(fully enumerated, [V])**:

| date | trader | displayed `comprehensive_elo` | `geo_elo_active` now | ≥ 2175 now? |
|---|---|---|---|---|
| 08-08 (×2) | `0xecaa…77a9` | 1948 | 3829.75 | ✅ |
| 08-09, 08-11 (×2) | `0xecaa…77a9` | 1804 | 3829.75 | ✅ |
| 08-11 | `0x6b02…e5fc` | 757 | 2344.73 | ✅ |
| 08-11 | `0x63c6…3e53` | 2415 | *(not queried)* | — |
| 08-11 (×6) | `0xd218…b5c9` | 1081 | 2414.34 | ✅ |
| 08-11 | `0xc722…1334` | 2066 | *(not queried)* | — |
| 08-18 (×2) | `0x2884…d0c3` | 1014 | **2076.65** | ❌ (below now) |
| 08-24 (×2) | `0xe234…304a` | 569 | **2140.72** | ❌ (below now) |
| 08-29 | `0xc624…ee24` (Bperil) | 1462 | 2564.65 | ✅ |
| 09-06 | `0xc624…ee24` (Bperil) | 1464 | 2564.65 | ✅ |
| 09-07 | `0xc624…ee24` (Bperil) | 1464 | 2564.65 | ✅ |

≈ 23 log lines / ~11 distinct (trader, day) alert events across 8 traders
in that 5½-week window. The repeated bursts on 08-11 are the in-memory
dedup set being lost across observer restarts (the dedup is not
persisted). The **June 11 → July 31** window was **not enumerated** — the
`polymarket-observer` journal query is prohibitively slow at full range
and repeatedly timed out this session (see "What was not determined").

**Note — a genuinely wrong-looking sub-case, distinct from Bperil:**
`0x2884…d0c3` (`geo_elo_active` 2076.65) and `0xe234…304a` (2140.72) sit
**below 2175 today** yet were badged LEGENDARY on 08-18 / 08-24. The alert
SQL selects on the *stored* `geo_elo_active`, which `update_geo_elo.py`
recomputes (with time-decay) on each maintenance run, so at fire time the
stored value was ≥ 2175 and has since decayed below. This is
recompute/decay lag against a stored snapshot, not a wrong-column bug —
and it is exactly the failure mode `column_definitions.py:120-122` warns
about for scripts that use `geo_elo` instead of `geo_elo_active`; this
script is on the correct side of that warning. Whether those two were
≥ 2175 at the precise fire timestamp is **[U]** — no historical
`geo_elo_active` snapshots exist to confirm.

### 2.8 "Avg ROI: −245.5%" alongside +$3,856.34 realized P&L

**Computation [V]:** `traders.avg_roi` is written as the **unweighted
arithmetic mean of per-closed-position `roi_percent`**:
`sum(p.roi_percent for p in closed_positions if p.roi_percent) / n_closed`
(`background_pnl_worker.py:346`, `monitor.py:1168`,
`backfill_synthetic_closes.py:139`;
`reconcile_trader_aggregates.py`: `avg_roi = AVG(roi_percent) WHERE
status='closed'`). The observer then renders it via
`roi_val = avg_roi if avg_roi > 1 else avg_roi * 100` (`:1315`).

For Bperil: stored `avg_roi = −2.4424` → observer prints `−244.2%`
(−245.5% on 09-06, when the value was −2.455; `realized_pnl` has since
ticked +$3,856.34 → +$3,878.56, `avg_roi` → −2.4424 — the figure drifts
slightly run to run).

**Why it is meaningless:**

- It is an **equal-weighted mean of ratios**. A \$0.02 position at −100%
  and a \$5,000 position at −100% count the same. **[V]** 188 of Bperil's
  899 closed positions (21%) have `entry_total_cost < $0.10`; positions
  with a near-zero cost basis produce extreme `roi_percent` values that
  dominate the mean while contributing ≈ nothing in dollars.
- The **dollar-weighted** return, `SUM(realized_pnl) / SUM(entry_total_cost)`,
  is **+5.4%** — positive, consistent with the +$3,878 realized P&L. The
  two headline numbers disagree in *sign* because they measure different
  things (mean-of-ratios vs aggregate-dollars).
- Secondary defects, same statistic: (a) the stored `avg_roi` (−2.44)
  does **not** equal the current `AVG(positions.roi_percent)` (−1.39 on a
  percent scale) — the aggregate is **stale**; (b) `positions.roi_percent`
  is on a **percent** scale (min −100, max +335 for Bperil) while the
  observer's `avg_roi > 1 ? : ×100` heuristic assumes a fraction and
  multiplies by 100, so any legitimately small percent value in (−1, 1)
  is inflated 100×.
- **Same family as the "290.3% ELO coverage"** finding
  ([[2026-09-07-telegram-alert-audit]] Part 4a): a ratio aggregated
  without denominator control (there: numerator not a subset of the
  denominator population; here: unweighted mean of per-position ratios
  with unbounded small denominators), yielding a headline whose label
  ("Avg ROI") corresponds to no economically meaningful quantity. **Not
  evidence of any fault in the LEGENDARY gate.** Not fixed, per scope.

---

## WHAT WAS NOT DETERMINED

- **LEGENDARY firing count for 2026-06-11 → 2026-07-31.** The
  `polymarket-observer` journal is very large (correlation-matrix
  progress spam) and full-range `journalctl` queries timed out
  repeatedly this session. Only the 2026-08-01 → 2026-09-07 window was
  fully enumerated (≈ 23 lines / ~11 events / 8 traders). Total since the
  06-11 re-enable is **not** established.
- **Whether `0x2884…d0c3` and `0xe234…304a` were actually ≥ 2175 at their
  fire timestamps.** No historical `geo_elo_active` snapshots exist; the
  code path implies the stored value satisfied the gate at query time,
  but this cannot be confirmed against a point-in-time record. `[U]`
- **`geo_elo_active` for `0x63c6…3e53` and `0xc722…1334`** (08-11
  alerts) — not queried; both displayed `comprehensive_elo` ≥ 2000 so
  neither is a striking case, but their canonical-gate status was not
  checked.
- **Whether the timestamp REGRESSION's ~+400–580/day is *entirely*
  `backfill_market_dates.py`.** The `T…+00:00` slice growth and the
  `.isoformat()` writers are verified; a second minor contributor (e.g. a
  live-monitoring market upsert path) was not ruled out row-by-row. The
  `T…Z` slice (~2,000 rows) is confirmed static and from a different,
  older path.
- **Exact date the 577 `gap_recovery_20260811` rows were written.** No
  commit accompanies them (data-only operation, 2026-08-11 per the
  literal); the audit trend shows them appearing 2026-08-12 (as 580,
  stepping to 577 on 08-17). The 3 rows that changed 580→577 were not
  identified.
- **Whether `traders.avg_roi`'s staleness (−2.44 stored vs −1.39
  recomputed) is population drift or a scale-convention change** in how
  `roi_percent` has been written over time — not chased.
- **No verdict on what to silence** — out of scope; that decision
  follows this audit.

---

## SOURCES

- `scripts/audit_invariants.py`, `scripts/check_canonical_definitions.py`,
  `scripts/backfill_market_dates.py`, `scripts/daily_maintenance.py`,
  `monitoring/system_observer.py`, `monitoring/column_definitions.py`,
  `monitoring/background_pnl_worker.py` (first-repo, read directly).
- `git log`/`git blame`/`git show` on `e72fd5e`, `b30c5ff`, `393a908`,
  `2b83c07`, `fc6c6c5`, `c6d5842`, `4d05ac0`, `e92b7e5`, `109da29`,
  `3919946`, `5fcbffe`, `bd672fb`, `e4ddb67`.
- `~/trading-swarm/brain/agent-outputs/data-audit/*-audit.json` (71
  reports, 2026-06-18 → 2026-09-09).
- Decision docs: `2026-08-19-pending-invariant-regression.md`,
  `2026-08-30-end-to-end-verification.md`,
  `2026-08-30-canonical-writer-column-gap.md`,
  `2026-06-29-overhang-ledger.md`, `2026-07-07-silent-failure-audit-FABLE.md`,
  `2026-07-06-elo-arc-design-FABLE.md`, `2026-08-20-open-smells-register.md`,
  `MASTER_HANDOVER_2026-06-10.md`, `MASTER_HANDOVER_2026-09-05.md`,
  `2026-06-07-session-summary.md`, `2026-09-07-telegram-alert-audit.md`,
  `2026-09-07-telegram-remediation.md`,
  `2026-09-07-stranded-markets-figure-reconciliation.md`.
- Live read-only queries against `data/polymarket_tracker.db`
  (`PRAGMA query_only`; `sqlite3 -readonly`).
- `journalctl -u polymarket-observer` (partial — see "What was not
  determined").

*Generated 2026-09-09. Read-only audit; no code, alert path, floor, or
register entry modified.*
