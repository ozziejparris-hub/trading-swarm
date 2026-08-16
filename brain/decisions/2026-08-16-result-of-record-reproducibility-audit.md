# Result-of-Record Reproducibility Audit — 2026-08-15 OOS Thesis Result

**Date:** 2026-08-16. **Scope:** read-only on production. **Mechanism used:** `scripts/
trader_skill_metric_v2f.py` was run WITHOUT `--persist`. Verified by reading every
`.execute()`/`.commit()` call site in the file before running: every write (the
`metric_v2f_*` table drops/creates/inserts) is gated behind `if args.persist:` with no
unconditional write path. `_sim_db_guard.py` does not apply — `v2f.py` is not a
`scripts/simulation/` script and does not import it. No writes occurred; nothing in this
audit modified the database.

---

## VERDICT: **UNREPRODUCIBLE**

Not because the headline finding changed character — it didn't (still NULL, still
directionally positive, still underpowered, cohort point estimate still ~2.3x the
placebo's). It is UNREPRODUCIBLE under the criteria fixed in advance because: the input
data has measurably changed since 08-15 (confirmed, general mechanism named below), at
least one of the four figures differs from the persisted record, and this audit could
not produce row-level attribution for every discrepancy — only for some. The criteria
state explicitly that an unattributed discrepancy forces UNREPRODUCIBLE, not DRIFTED,
and forbid rounding an unexplained delta down. That is applied here without softening.

**Code is not a factor.** Addition 3 settled this cleanly: current HEAD **is**
`eaeabbc`, the generator_commit recorded on every persisted `metric_v2f_*` row. Zero
commits have landed in first-repo since the result of record (`git log eaeabbc..HEAD` is
empty; `git diff eaeabbc..HEAD --stat` is empty except three unrelated runtime-state
files — `data/.last_requeue_run`, `data/category_backfill_state.json`, `logs/
focus_ratio_review.json` — none of which touch the v2 pipeline). Every discrepancy below
is data-attributable by construction; there is no code component to decompose.

---

## STEP 1 — CURRENT FINGERPRINT (2026-08-16, read-only)

| Metric | Value |
|---|---|
| `traders` row count | 170,430 |
| `trades` row count | 11,350,510 |
| `positions` row count | 7,476,972 |
| `markets` row count | 722,851 |
| MAX(`trades.timestamp`) | 2026-08-16 14:12:03 |
| MAX(`positions.entry_timestamp`) | 2026-08-16T14:12:03 |
| MAX(`markets.last_checked`) | 2026-08-16 08:58:25.393179 |
| MAX(`traders.last_updated`) | 2026-08-16 11:37:50.408801 |
| `markets.resolved = 1` count | 224,828 |
| Geopolitics/Elections, resolved, gap-clean (no trade requirement) | 10,448 |
| `markets.trade_gap_flag = 1` count | 250 (166 `flag_reason IS NULL` [April 7-18 gap] + 84 `synthetic_quarantine_2026-07-19` [O-37]) |
| `markets.trade_gap_flag = 0` count | 722,603 |
| `markets.trade_gap_flag IS NULL` count | 0 |
| 63 tables total in DB | see Step 2 |
| Trades with `data_source='gap_recovery_20260811'` | 399, all timestamped 2026-08-11 06:19:30–18:24:27 |
| Markets with `data_source='gap_recovery_20260811'` | 178, all `resolution_date IS NULL`, **0 in Geopolitics/Elections** |
| Trades timestamped ≥ result-of-record generation (2026-08-15T19:36:56Z) | 721 |
| Positions with `entry_timestamp` ≥ 2026-08-15T19:36:56Z | 405 |
| Pre-T_split-timestamped (`< 2026-04-01`) trades among the most-recently-inserted 553,800 rows | 162,648 |
| Pre-T_split-timestamped trades among just the last 100,000 inserted rowids, by `data_source` | 8,043 `background_backfill` |

---

## STEP 2 — PRIOR-STATE RECORD: EXISTS, AND FULLY RECONCILED (Addition 1)

**A durable, row-level prior-state record exists** — persisted by the original
`--persist` run, not reconstructed from prose. Read directly (query output verbatim):

```
metric_v2f_oos_result:
('cohort',  3032, 120, 0.0315983580923187,  -0.008811471790337956, 0.07101264180859905,
 'SKILLV2F-2026-08-15-v1', '2026-08-15T19:36:56.852700+00:00', 'eaeabbc')
('placebo', 2569, 110, 0.01270654030764884, -0.021009443931438377, 0.04614399725878763,
 'SKILLV2F-2026-08-15-v1', '2026-08-15T19:36:56.852700+00:00', 'eaeabbc')

metric_v2f_findings (objective2, json_value):
{"t_split": "2026-04-01 00:00:00", "presplit_cohort_n": 148, "control_n": 148,
 "oos_result": {"n_pairs": 1455, "n_traders": 120, "n_markets": 489, ...},
 "placebo_result": {"n_pairs": 1345, "n_traders": 110, "n_markets": 561, ...}}

metric_v2f_intersection_cohort: 295 rows (Objective 1's sig-95+M>=10+edge>=0.02 cohort
— a DIFFERENT, larger population than Objective 2's 148 pre-split-qualifying traders)
```

**Addition 1's check — CONFIRMED, no disagreement.** The persisted tables match the
handover's stated figures exactly: n=3,032 / 148 qualifying / 120 surviving / point
estimate 0.0315983580923187 (≈+0.0316) / CI [-0.008811, +0.071013] / placebo +0.012707
[-0.021009, +0.046144]. The number of record genuinely is the number that was persisted
— this audit proceeds on the ordinary drift-vs-reproduction track, not the "the figure
was never real" branch.

**What is NOT recorded:** the actual trader addresses of the 148 pre-split-qualifying /
120 surviving cohort, or of the 148 matched placebo controls. Only `metric_v2f_
intersection_cohort` (the 295-trader Objective-1 population) has a persisted address
list. Objective 2's cohort — the population underlying the headline number — has **no
persisted membership list**, only aggregate counts. This gap is material to the
attribution below and is reported again under Step 5.

**Wider shape-based search, as required by the resumed task:**
- All 63 tables in the DB were enumerated (Step 1's table list, reproduced here):
  `backtest_population_snapshots`, `dilution_guard_signals(_guard_diffs)`,
  `elo_formula_audit_findings/pre_registration`, `elo_shadow`, `elo_snapshots`,
  `event_cluster_labels`, `geo_elo_derivation_audit(_findings)`, `insider_clusters`,
  `insider_signals`, `layer0*` (9 tables), `markets`, `metric_v2*` (24 tables, full
  v2→v2f lineage), `monitor_state`, `monitoring_status`, `order_book_snapshots`,
  `positions`, `price_convention_audit_*` (3 tables), `sqlite_sequence`, `str002_signals`,
  `trader_categories`, `traders`, `trades`. Every table not part of the already-known v2
  lineage was checked by name against its evident purpose (audit/monitoring/signal
  tables unrelated to trader-skill metrics) — none contains an unrecognized snapshot of
  DB state as of 08-15 beyond the `metric_v2f_*` family already read above.
- Git history, both repos, searched by content (`git log --all -S"3,032"` and
  `-S"0.0316"`): matches found only in the three already-known documents —
  `2026-08-15-skill-metric-rebuild.md`, `MASTER_HANDOVER_2026-08-15.md`, and this
  session's own `2026-08-16-comprehensive-elo-dependency-trace.md`. No other committed
  file, in either repo, contains these figures.
- No durable artifact file (CSV/JSON/parquet/txt) written by the v2 script family was
  found outside the DB tables above — the v2f script's `--json-out` option exists but no
  file from an 08-15 invocation was found on disk in either repo.
- `logs/daily_maintenance.log` (34MB, spans the relevant period) exists but was not
  fully searched line-by-line within this audit's remaining budget — flagged as
  incomplete coverage, not asserted clean.

**Conclusion for Step 2: the prior-state record for the four headline figures is
complete and trustworthy (the persisted `metric_v2f_*` tables). The prior-state record
for cohort/placebo MEMBERSHIP does not exist.** This is the reproducibility discipline's
real gap: the rule pins code and parameters, and it turns out to also — accidentally —
pin the aggregate result via `--persist`, but it does not pin which rows produced that
aggregate. A different set of 148 traders could in principle produce the same count and
a similar point estimate; there is no way to prove today's 148 are last month's 148.

---

## STEP 3 — RE-RUN AS COMMITTED (no `--persist`, seed=42 default, T_split unchanged)

Actual output, unedited:
```
[load] entries: 342482 positions, 27238 traders
[objective1] reproduced cohort: 361 traders (expect 360)
INTERSECTION cohort (sig-95 AND M>=10 AND edge>=0.02): n=298
  overlap with LEGENDARY: 15/81
[presplit] 183827/342482 positions resolved by 2026-04-01 00:00:00 (PIT-correct via tape_end)
pre-split intersection cohort: 148 traders
[match] matched 148/148 cohort traders to controls
[oos:cohort]  3033 positions, 120 surviving traders, gap=0.03184400367920137,
              CI=[-0.007585120028687408, 0.07185867099456918]
[oos:placebo] 2518 positions, 106 surviving traders, gap=0.01391568978328761,
              CI=[-0.022851151650710198, 0.04776103914029016]
[VERDICT] cohort CI excludes zero: False. placebo CI excludes zero: False.
[THESIS VERDICT] NULL — unchanged.
```

---

## STEP 4 — SIDE-BY-SIDE COMPARISON AND ATTRIBUTION

| Figure | 08-15 (persisted) | Today (no-persist re-run) | Delta |
|---|---|---|---|
| Objective 1: "360-cohort" reproduction | not separately persisted (v2e reference value: 360) | **361** (script's own comment: "expect 360") | +1, drifted at the full-population stage too |
| Objective 1: intersection cohort (sig-95+M≥10+edge≥0.02) | **295** | **298** | +3 |
| Objective 1: LEGENDARY overlap | not persisted numerically (rebuild doc states 15/81) | 15/81 | 0 — unchanged |
| Objective 2: presplit-qualifying cohort | **148** | **148** | 0 — unchanged (count) |
| Objective 2: control pool matched | 148/148 | 148/148 | 0 — unchanged |
| Objective 2 cohort: n_positions | **3,032** | **3,033** | +1 |
| Objective 2 cohort: n_surviving_traders | **120** | **120** | 0 — unchanged (count) |
| Objective 2 cohort: point estimate | **0.0315983580923187** | **0.03184400367920137** | +0.000246 |
| Objective 2 cohort: CI | **[-0.008811, +0.071013]** | **[-0.007585, +0.071859]** | shifted, still spans zero |
| Objective 2 placebo: n_positions | **2,569** | **2,518** | **−51** |
| Objective 2 placebo: n_surviving_traders | **110** | **106** | **−4** |
| Objective 2 placebo: point estimate | **0.01270654030764884** | **0.01391568978328761** | +0.001209 |
| Objective 2 placebo: CI | **[-0.021009, +0.046144]** | **[-0.022851, +0.047761]** | shifted, still spans zero |

**Row-level attribution, per discrepancy:**

1. **Objective-1 population (+1 on the 360-cohort, +3 on the 298-vs-295 intersection).**
   NOT attributed at row level within this audit. General mechanism confirmed active
   (see item 4 below — background backfill continues to insert historical trades), but
   the specific trader(s)/position(s) crossing the significance or effect-size threshold
   were not individually identified. **Unattributed.**

2. **Cohort n_positions 3,032 → 3,033 (+1), point estimate +0.000246.** Same fixed seed
   (42) on both runs, same code (Step 3 confirmed HEAD=eaeabbc) — a nonzero point-estimate
   shift under an identical seed on identical code is only possible if the underlying
   *data* fed to the bootstrap changed. One net additional position appearing in the
   qualifying cohort's post-split window is consistent with a single backfilled or newly
   resolved position for one of the (likely, not provably) same 120 surviving traders.
   **The general mechanism is confirmed (item 4), but the specific position/trader/market
   responsible was not individually named. Unattributed at the row level required by the
   criteria**, despite being a small and plausible-looking delta.

3. **Placebo n_positions −51, n_surviving_traders −4, point estimate +0.0012 — the
   largest discrepancy.** This is NOT a direct data change to the placebo's own trades —
   the placebo cohort is *re-selected* every run by `match_control()`, a greedy
   nearest-neighbour match (seed=42) over the full `elig_pool` (every trader with
   `n_pairs >= 10` in the pre-split population), excluding the 148 treatment traders.
   If the composition, ordering, or per-trader feature vectors (log positions, log
   markets, log activity-span) of that pool shifted at all since 08-15 — which is
   expected, since the pool depends on the ENTIRE pre-split trading history, not just the
   148 qualifying traders — the greedy match can select **different control traders**
   under the identical seed, because the candidate array itself differs. This fully
   explains why the placebo moved more than the cohort (whose 148/120 counts held): the
   eligible pool feeding placebo selection is far larger and structurally more exposed to
   any backfill anywhere in pre-split history. **The mechanism is well-understood and
   named, but this audit did not reconstruct `elig_pool`'s composition as of 08-15 (it
   was never persisted — see Step 2) and therefore cannot name which specific traders
   were swapped in or out of the match. Unattributed at the required row level.**

4. **General mechanism confirmed active (supports, but does not complete, items 1-3):**
   background backfill is actively inserting **pre-T_split-timestamped** trades into the
   DB after 08-15. Verified directly, not inferred: of the 553,800 most-recently-inserted
   trade rows (by rowid), 162,648 carry `timestamp < 2026-04-01`; of just the last
   100,000 inserted rowids with pre-split timestamps, all 8,043 carry
   `data_source = 'background_backfill'`. This is exactly the kind of write that would
   silently shift both the Objective-1 population and the Objective-2 pre-split
   eligibility pool without ever touching a "recent" date range — a naive check of "what
   changed since 08-15" that only looks at recent timestamps would miss it entirely.
   This audit deliberately checked rowid-vs-timestamp mismatch for this reason.

5. **Ruled out, with row-level evidence, as causes of any of the above:**
   - **O-49 gap-flagging (the 0 → 4,979 → 20,211 trajectory).** Addition 2, settled:
     this number was never applied to `markets.trade_gap_flag`. It is a manually-run,
     ad-hoc readiness-check count ("tape_end in outage window") reported in session-
     summary prose each session, explicitly deferred every time — direct quote from
     `2026-08-14-session-summary.md`: "Gap-flagging deferred again. Do not execute until
     two consecutive readings are materially unchanged." No table in the DB stores this
     count; it was never a write. Today's `trade_gap_flag=1` count (250 = 166 April-gap
     + 84 O-37-quarantine) is the SAME two components that have applied since before
     08-15 — confirmed by `flag_reason` breakdown (`NULL`: 166, `synthetic_quarantine_
     2026-07-19`: 84). **The 20,211 figure and the 250 figure were never measuring the
     same thing** (candidate readiness count vs. actual applied flag) — this is the
     "scoped differently" branch of Addition 2's four options, confirmed by direct
     evidence, not the other three.
   - **08-11 gap recovery (`gap_recovery_20260811`).** 399 trade rows (not 402 — a minor
     discrepancy against the session-summary's rounded figure, not chased further; the
     `data_source` value and row count are the only facts needed here) and 178 market
     rows, all with `resolution_date IS NULL` and **zero rows in Geopolitics or
     Elections**. This recovery event cannot be a contributor to any Objective-1 or
     Objective-2 figure — confirmed empirically by category, not assumed from the name.
   - **The 10,091 (07-18 handover) → 10,448 (today) Geopolitics/Elections resolved
     gap-clean pool.** Reconciled exactly: 8,980 markets with `tape_end < 2026-07-18`,
     30 with `tape_end` in [07-18, 08-15), **0** with `tape_end ≥ 08-15`, and 1,438
     zero-trade markets (no `tape_end` at all, LEFT-JOIN-counted) — sum = 10,448,
     matching the fingerprint exactly. Zero markets in this category have accrued new
     trade activity (`tape_end`) since 08-15 — the pool's growth is entirely pre-08-15
     accrual plus the always-present zero-trade-market bucket, not an ongoing process
     that could explain the Step-3 deltas. **Ruled out as a cause of the Objective-2
     drift**, though it does not fully explain its own 07-18→today growth composition
     (how much of the 357-market growth is genuinely new zero-trade markets being marked
     resolved vs. reclassification) — flagged as unresolved but immaterial to the
     headline-result question.
   - **Code changes.** Ruled out entirely (Addition 3): HEAD = eaeabbc, zero commits
     since the result of record.

**Net: two ruled-out candidates with full row-level evidence (O-49, gap_recovery_
20260811), one confirmed-active general mechanism (background_backfill touching
pre-split-timestamped trades) that plausibly explains the shape of the drift but was not
traced to the individual rows responsible for each of the four figures, and zero
row-level identification of the specific traders/positions behind the +1/+3/−51/−4
deltas.** Per the fixed criteria, this composition — some causes ruled out with evidence,
the general active mechanism named but not resolved to specific rows — is exactly the
UNREPRODUCIBLE case, not DRIFTED. DRIFTED requires every discrepancy attributed with
row-level evidence; this audit has that for zero of the four discrepancy classes, only
for the negative (ruled-out) side.

---

## STEP 5 — PIN MECHANISM FINDING

**No mechanism currently pins or versions dataset state alongside a decision-carrying
number.** Confirmed by inspection of every `metric_v2f_*` table's schema (all columns
read in Step 2): each row carries `spec_version`, `generated_at`, `generator_commit` —
i.e., **code** and **run-time** are pinned, but nothing about the *data* is recorded:
no row-count fingerprint, no content hash, no reference to a frozen population snapshot,
no list of which trader addresses or position IDs constituted the cohort. This is the
same code-vs-data asymmetry the project's reproducibility rule already names for code
("committed script writing to a durable artifact with generating parameters recorded")
but the rule, as currently practiced, does not extend to data provenance.

**What the schema would already support, without building anything new:**
- `backtest_population_snapshots` already exists and does exactly this for one thing
  (the market population) — it freezes `(snapshot_id, market_id, tape_end)` rows with a
  `sql_version`. The same *pattern* — not the same table — could in principle capture a
  cohort's member list the same way `metric_v2f_intersection_cohort` already does for
  Objective 1 (trader, spec_version, generated_at, generator_commit) — Objective 2's
  148/120/148 cohorts simply never got the equivalent table. The schema convention
  already exists; Objective 2 didn't use it.
- SQLite's own `rowid` is already available on `trades` and could support an "as-of
  max-rowid" bound the way `tape_end` already bounds by timestamp — the 08-16 backfill
  detection in this audit (rowid vs. timestamp mismatch) demonstrates this is queryable
  today with no schema change.
- No content-hash mechanism exists anywhere in the schema (no checksum column on any
  table). This is not proposed as a fix — noted only because the question asked what the
  schema would already support, and hashing is not among the things it currently
  supports without new columns.

This finding is reported, not remediated — no table, column, or script was created or
modified as part of this audit.

---

## WHAT REMAINS (explicitly, not attempted further within this audit's budget)

- Row-level identification of the specific trader(s)/position(s) responsible for the
  Objective-1 +1/+3 deltas and the Objective-2 cohort's +1 position.
- Reconstruction of the `elig_pool` composition as of 08-15 (would require either a
  time-machine query against a backfill-aware position log that doesn't exist, or
  accepting that this specific reconstruction is not achievable post-hoc given no
  snapshot was taken).
- Full line search of `logs/daily_maintenance.log` (34MB) for any 08-15-adjacent
  maintenance-run anomaly not already covered by the session-summary record.
- The 10,091→10,448 pool's zero-trade-market sub-composition (immaterial to the
  headline result, noted above as unresolved but out of scope).

---

*Audit performed 2026-08-16, entirely read-only. All DB access via `sqlite3 -readonly` or
a Python `mode=ro` URI connection, or via `trader_skill_metric_v2f.py` run without
`--persist` (verified no unconditional write path exists in that script). No writes
attempted or made. No files modified other than this report.*
