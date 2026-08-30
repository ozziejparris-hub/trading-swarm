# End-to-End System Verification — Before Phase 2

**Scope:** read-only verification across five areas (standing failures, end-to-end
market trace, canonical-writer migration state, downstream backlog, Phase 2 input
readiness). No fixes, no migrations, no sweep resumption. Tagging: [V]=verified this
session (query/log/code read directly), [I]=inferred (reasoned from verified facts,
not independently re-checked). Every claim in the task prompt was treated as a
hypothesis to check, not a fact — several turned out to be wrong in useful ways (see
§1a, §4d).

---

## VERDICT (read this first)

**One BLOCKING mechanism bug, confirmed live in production, is the main finding of
this task:** `mark_market_resolved()` — the canonical writer that resolved all
214,016 sweep markets — never sets `last_checked`. `requeue_resolved_market_traders.py`,
the only thing that tells the P&L worker "this trader needs re-processing," gates
entirely on `last_checked`. Result: **195,228 of 214,016 sweep-resolved markets
(91.2%) are permanently invisible to the requeue step** — not delayed, permanently,
because their `last_checked` predates even the *pre-sweep* baseline and nothing will
ever touch it again. Confirmed live: today's and yesterday's requeue runs found "2"
and "6" newly-resolved markets against a true population of ~210,000. Concretely:
4,991 open positions across 594 traders on sweep-resolved markets will never get
`pnl_last_updated` reset, so their P&L is stale specifically *because* they were
touched by the new canonical path — the old, "worse," non-canonical writers
accidentally did this right (their direct `UPDATE` statements set `last_checked`
themselves).

Two further BLOCKING items are non-technical: **no live cohort/candidate-set artifact
exists** for Phase 2 to trade against (only frozen 2025-11-01 and 2026-08-15
snapshots, both pre-dating the sweep and the corrected n=10 LEGENDARY anchor), and
**ingestion-stall detection — which the project's own handover already named
mandatory before any months-long passive run — still does not exist.**

Everything in Part 1 that this project has previously flagged as "probably fine,
dismissed before" turned out to actually be fine this time, **except** that the
specific claim in the prompt ("pre-ELO gate fails daily") was itself wrong — the gate
passes; a different, deliberately-non-blocking step was misread as the gate failing.
That correction matters for calibration going forward as much as any of the real
findings below.

**Phase 2 readiness: NOT READY.** Not because the sweep produced bad data — the sweep
data itself traces cleanly (§2) — but because the wiring between "resolve a market"
and "the rest of the pipeline notices" has a structural gap that is currently eating
the majority of the sweep's output, and none of the three named Phase-2 prerequisites
from the 08-16 handover have been built.

---

## PART 1 — Are the standing failures actually benign?

### 1a. Pre-ELO integrity gate — **the prompt's premise was wrong** [V]

`audit_invariants.py` (step 7, "Integrity audit (pre-ELO gate)") **passed with exit
0 on both 08-28 (71.2s) and 08-29 (71.5s)**, read directly from contiguous,
unfiltered log blocks. The daily `FAILED — exit code 1` belongs to **step 8,
"Canonical definitions drift" (`check_canonical_definitions.py`)** — a different,
explicitly non-blocking step ("a code smell, not a data gate," per its own comment in
`daily_maintenance.py`). My first pass at this got it backwards by grep-filtering
non-adjacent lines out of order; re-read against the raw log corrected it. **Verdict:
NOT A PROBLEM — the gate is not being ignored, it is not failing, and the exit-code
contract in the code (`sys.exit(2)` on CRITICAL, `sys.exit(0)` otherwise, never `1`)
matches what actually happens.**

What the gate *does* report, correctly and non-fatally, is real: 08-30's run —
**26 invariants, 15 PASS, 5 REGRESSION, 0 CRITICAL, 6 OBSERVE.** REGRESSION doesn't
gate (only CRITICAL does, via exit 2); nothing in the 3-day window hit CRITICAL. The
5 REGRESSION rows are the real backlog signal — see §4a and the trend table there.

### 1b. Test suite — stable, matches the documented failure set [V]

`tests/LATEST_TEST_RESULTS.md` (08-29 run, 158.5s): **exactly 5 `[FAIL]` lines in the
entire 18-file suite, all inside `test_backtest_window_population.py`** (T2, T2b,
T2c, T2d, T2f — the documented snapshot-vs-live drift: `4658→4660`, `54→52`,
`555→578`, `573→643`, `4660+578+643≠6348`). Nothing outside that file failed. 08-28's
run (156.5s) reported the same `WARNING — FAILURES DETECTED` status at a matching
duration but its detail file was overwritten by 08-29's run before this check, so
that day's exact line-for-line content isn't independently re-verifiable — inferred
stable from matching status/duration, not directly read. **Verdict: NOT A PROBLEM,**
with the 08-28 caveat noted rather than asserted away.

### 1c. Canonical definitions drift — same 7, unchanged [V]

Identical 7 violations on 08-28, 08-29, and 08-30, byte-for-byte: `trader_skill_metric_v2.py:390`,
`v2b.py:613`, `v2c.py:506`, `v2d.py:418`, `v2e.py:437`, `v2f.py:380` (all
`geo_elo >= 2175` hardcoded instead of `cd.LEGENDARY_GATE_WHERE`), plus
`characterize_legendary_overlap_recompute.py:84`. Not growing, not shrinking — dead
weight. **Verdict: DEGRADING, not cosmetic** — see §Findings, this is the exact set
of scripts that compute the metric Phase 2 would consume, and the LEGENDARY
threshold they hardcode is known to be a decaying/moving target (`geo_elo_active`),
not a fixed constant.

---

## PART 2 — End-to-end trace

5 sweep-resolved markets (`resolution_evidence_source='clob'`, highest trade volume)
and 5 organically-resolved markets (untagged, `last_checked` in the last 2 weeks,
highest trade volume in that set) [V, live queries]:

| | Sweep-resolved (clob) | Organically-resolved (untagged) |
|---|---|---|
| Sample markets | Eurovision/World-Cup novelty markets, Bessent Fed Chair, Hormuz strait | Iran/geopolitics niche markets, 1 election |
| n_trades range | 6,066 – 10,911 | 268 – 652 |
| avg pending-rate | **~2.2%** (122–245 pending per market) | **~11.5%** (6–102 pending per market) |
| positions: synthetic-close rate | 0% – 7.9% (1 of 5 markets nonzero) | 3.3% – **33%** (all 5 nonzero, 3 of 5 above 15%) |
| ELO recompute (sample traders, `elo_last_updated` ≥ resolution) | 3,976/3,976 (100%) | 115/116 (99%) |
| in frozen backtest snapshot (`bt_pop_2025-11-01_v1`) | 0/5 (snapshot predates all of it) | 0/5 (same) |
| `resolution_date` sanity | Realistic (matches `resolution_recorded_at` for 4/5) | One neighboring cohort (not sampled markets, but same population) carries `resolution_date=2028-11-07` — a scheduled *future* election date copied in as "resolution," not an event time |

**Comparison, plainly [V]:** on the metrics this trace could directly measure, the
sweep-resolved sample does **not** look worse than the organic sample — if anything
the opposite (lower pending-rate, lower synthetic-close rate). The organic sample's
elevated synthetic-close rate on small/low-volume markets is a real, visible
divergence but wasn't root-caused in this pass (flagged, not chased — scope
discipline). The ELO-recompute check is a weak signal by construction (it shows the
general daily pass touched these traders' rows, not that this specific market's
outcome was correctly folded into the number) and should not be read as full
verification of the ELO stage.

**The trace's real finding is not in this table — it's upstream of it.** Every
sweep-resolved market in the sample has a `last_checked` value from **March–May
2026**, months before its `resolution_recorded_at` (Aug 24–28). None of the 5 would
ever pass `requeue_resolved_market_traders.py`'s gate. See §3/§4b for the mechanism
and full-population count. This is the one place the two populations genuinely
diverge, and it's structural, not statistical: **canonical-path (sweep) resolutions
are silently excluded from requeue; non-canonical (organic) resolutions are not**,
because the old direct-`UPDATE` writers happen to set `last_checked` in the same
statement and the new canonical writer does not.

---

## PART 3 — The half-migrated canonical state

### 3a. Writer census [V, `scan_write_paths.py` + manual read of each file]

13 production files touch `markets.resolved` / `winning_outcome` / `resolution_date`
via `UPDATE` (excluding tests/archive/characterizations/simulation, which are not
live production paths):

| File | Routes through `mark_market_resolved()`? | Live/scheduled? |
|---|---|---|
| `monitoring/resolution_writer.py` | — (the module itself) | n/a |
| `scripts/backfill_market_dates.py` | **Yes** (line 273) | Daily (held via sweep-checkpoint recency) |
| `scripts/hydrate_stub_markets.py` | **Yes** (line 233) | Daily |
| `scripts/fast_resolution_check.py` | **Mixed** — 1 of 4 write branches (line 310); 3 branches write directly (lines 222, 440, 550, 647) | Daily |
| `monitoring/database.py` | No | Unconfirmed if the touched function is on a live call path — not chased further |
| `scripts/resolve_legendary_markets.py` | No | Daily, `--limit 50` |
| `scripts/legendary_positions_scan.py` | No | Weekly (Monday cron) |
| `scripts/backfill_o16_tier1.py` | No | Legacy, O-16 tier-1 completed 2026-07-02 per prior record — likely dormant |
| `scripts/backfill_o16_tier2.py` | No | Legacy, unblocked 2026-07-06 — likely dormant |
| `scripts/fetch_market_resolutions.py` | No | Not present in `daily_maintenance.py` STEPS — not on the standing schedule |
| `scripts/fix_expired_unresolved.py` | No | One-off fix script, not scheduled |
| `monitoring/monitor.py` (2 matches) | No, but **doesn't actually set `resolved`** — only fills `end_date`/`resolution_date` via `COALESCE`-guarded proxy where `end_date IS NULL`. Not a resolution writer in the relevant sense. | Live (15-min loop) |

**So: not "1 of 13."** 3 files (plus the module) have at least a partial canonical
path; `fast_resolution_check.py` is genuinely mixed within a single file. 2 of the
non-canonical writers (`resolve_legendary_markets.py`, `legendary_positions_scan.py`)
are actively scheduled today (daily and weekly respectively) and will keep growing
the untagged population going forward, not just historically.

### 3b. The split, quantified [V]

| | count | % of resolved |
|---|---|---|
| Total resolved | 438,392 | 100% |
| Tagged (`resolution_evidence_source` set: clob=214,016, gamma=62, hydration_fill=1) | 214,079 | 48.8% |
| **Untagged** (written by a non-canonical path) | **224,313** | **51.2%** |

Both populations are read by the same downstream consumers (same `markets` table,
same `resolved=1` predicate everywhere in `evaluate_new_trader_results.py`,
`requeue_resolved_market_traders.py`, the audit checks, etc.) — there is no
consumer-side distinction between a canonically-written row and a legacy one. The
practical effect isn't data corruption (§2 shows both trace cleanly on the metrics
checked) — it's that **the atomicity/provenance guarantee the canonical writer
exists to provide only covers 48.8% of the resolved population**, and per §3a, two
still-active writers keep adding to the uncovered half.

### 3c. `check_resolution_write_atomicity`'s actual visibility [V]

`resolution_recorded_at IS NOT NULL` count = 214,079, exactly equal to the tagged
count above (confirms `mark_market_resolved()` always sets both together, as
designed). **The check can see 214,079 / 438,392 = 48.85% of resolved rows. It is
blind to the other 51.15% by construction**, exactly as its own docstring warns and
as the prompt's hypothesis anticipated — quantitatively confirmed, not just
theoretically true. Ran it twice this session: `(0, 0, 0, [])` both times, stable —
within the population it *can* see, nothing has gone wrong. That's a weaker
statement than it sounds given the coverage number above.

---

## PART 4 — Did downstream keep up with the sweep?

### 4a. `evaluate_new_trader_results.py` backlog [V]

The script's own scope (by design, read from source) is **`is_flagged=1` traders
only** — not the full trader population. Two backlog numbers matter, and they tell
different stories:

- **Unscoped, whole-population pending-on-resolved:** 1,170,665 trades, of which
  886,907 sit on sweep-resolved (clob) markets. This number is **not** the relevant
  backlog — the vast majority belongs to traders the script was never designed to
  touch (unflagged/excluded). Reporting it as "the backlog" would overstate the
  problem by ~45x.
- **In-scope (flagged, non-excluded, `winning_outcome` set) pending:** **26,213**
  total, **21,955 (84%) on sweep-resolved markets specifically.** This is the real
  number.

Trend over the 3-day window, from the daily audit's own REGRESSION rows [V]:

| metric | 08-28 | 08-29 | 08-30 | direction |
|---|---|---|---|---|
| pending, resolved non-gap, flagged traders | 22,163 | 19,726 | 9,881 | **shrinking fast** |
| pending, resolved non-gap, geo/elections | 22,894 | 23,208 | 23,161 | **flat — not shrinking** |
| timestamp mixed formats | 29,564 | 30,195 | 30,795 | **growing, ~650/day** |
| `data_source` not canonical | 577 | 577 | 577 | flat (frozen legacy) |
| `total_invested` vs cost mismatch >5% | 13,954 | 13,968 | 13,983 | slow growth, ~10-15/day |

The divergence between the two "pending" rows is the real signal: general flagged-
trader backlog is draining fast, but **geo/elections specifically — the category the
entire skill-metric thesis is built on — is not draining at all.**

### 4b. `requeue_resolved_market_traders.py` — the sweep's output was largely dropped [V]

Root cause, read directly from both files: `mark_market_resolved()`'s `UPDATE`
statement sets `resolved, winning_outcome, resolution_date, resolution_recorded_at,
resolution_evidence_source, resolution_evidence_detail` — **never `last_checked`**.
`requeue_resolved_market_traders.py` gates on
`datetime(last_checked) > datetime(last_run)`, by explicit design choice (its own
comment cites the O-16 precedent and deliberately avoids gating on `resolution_date`
event-time — the *previous* silent-drop bug — without realizing `last_checked`
write-time has the identical failure mode for a writer that doesn't touch it).

Quantified at full population: **195,228 / 214,016 sweep-resolved markets (91.2%)
have `last_checked` timestamps that predate even the sweep's own pre-launch
baseline (2026-08-14) and will never pass the gate.** Confirmed live in the actual
log, not just theoretically: 08-29's run logged `Markets resolved since last run: 6`;
08-30's logged `2`. Concrete downstream damage: **4,991 open positions across 594
distinct traders**, on sweep-resolved markets, will never have `pnl_last_updated`
reset by this mechanism.

Note the irony for §2's comparison: the **non-canonical** direct-`UPDATE` writers
(the ones this migration is trying to retire) include `last_checked = ?` in their own
`SET` clause and therefore correctly trigger requeue. The canonical writer is the
one that broke this.

### 4c. P&L worker and `apply_full_elo_modifiers` [V, partial — see caveat]

`apply_full_elo_modifiers.py` ran successfully (exit 0) both days checked, in **7.5s
and 7.7s** — suspiciously fast for a "full" pass, and consistent with it processing a
near-empty priority queue, which is exactly what you'd expect if its trigger
(`pnl_update_priority`/`pnl_last_updated=NULL`) is set almost entirely by requeue,
and requeue is firing on 2-6 markets/day instead of thousands. `background_pnl_worker.py`
runs continuously as part of the live 15-min loop and does honor `pnl_skip`, but its
exact selection predicate for "needs reprocessing" wasn't traced line-by-line this
session (named, not chased further — scope discipline). **The causal chain
(mark_market_resolved doesn't set last_checked → requeue doesn't fire → pnl_last_updated
never reset → worker has no signal) is established with high confidence from §4b's
verified facts; the worker's internal predicate is inferred, not independently
re-read.**

### 4d. Daily-maintenance runtime growth — **not the backlog** [V]

3h15m (08-28) → 3h57m (08-29) → 11h53m+ and still running (08-30, a Sunday) is fully
explained by `discover_leaderboard_traders.py`, a documented, budgeted,
Sunday-only step (10h timeout, historically 5.45–7.19h even when it doesn't hang —
already a known "proven offender," O-27). The backlog-adjacent steps show **no**
day-over-day slowdown: `Evaluate new trader results` 94.4s→92.0s, `Requeue resolved
market traders` 1.7s→3.3s, `Apply full ELO modifiers` 7.7s→7.5s — flat, consistent
with a small, roughly-constant candidate set each day (further corroborating §4b:
if requeue's true population were thousands rather than a handful, these step
durations would show it). **Verdict: NOT A PROBLEM** — the runtime growth is
Sunday's known weekly step, not a symptom of the sweep's backlog.

---

## PART 5 — What would Phase 2 actually consume?

| Input | Exists? | Current? | Compromised by Parts 1-4? |
|---|---|---|---|
| **Cohort membership** | Only frozen artifacts: `metric_v2f_intersection_cohort`/`metric_v2f_oos_result` (2026-08-15), `bt_pop_2025-11-01_v1` (2025-11-01) | **No** — both predate the sweep and the 08-18 corrected n=10 LEGENDARY anchor entirely | **BLOCKING** — no live cohort definition exists to trade against; §6.1 cutover decision (which metric even defines the cohort) is explicitly not made |
| **Live market data** | Yes — 15-min monitor loop, active | Yes | Not directly compromised by this task's findings |
| **Entry prices** | Yes — `price_history.py`/CLOB, characterized "primary-with-fallback," 73.1% cross-check on a stratified sample (prior session finding, not re-verified here) | Yes, but reliability is age/liquidity-dependent per its own characterization | Unchanged by this task; carries its own known caveat, not re-tested |
| **Position tracking** | Yes — live FIFO tracker, `is_synthetic_close` flag exists | Yes | **DEGRADING** — §2 found elevated synthetic-close rates (up to 33%) on smaller organic markets, not root-caused |
| **Outcome resolution** | Yes, but **half-migrated** (§3) | Mixed — 48.8% tagged/canonical, 51.2% untagged, and 2 active writers still add to the untagged side | **DEGRADING** (provenance/atomicity coverage) |
| **P&L** | Yes — `background_pnl_worker.py`, live | **No, for the sweep-affected population** — §4b's requeue gap means 594 traders' resolved-position P&L is not being triggered for reprocessing | **BLOCKING** for that subset — and that subset is exactly "traders with open positions in markets the sweep just resolved," i.e. the population most relevant to validating the sweep's own output |
| **Ingestion-stall detection** | **No** | n/a | **BLOCKING** per the project's own 08-16 handover, which named this mandatory before any months-long passive run — unchanged, still not built, as of this check |

---

## FINDINGS, RANKED

### BLOCKING
1. **`mark_market_resolved()` omits `last_checked`, silently defeating `requeue_resolved_market_traders.py` for 91.2% of sweep-resolved markets** (195,228/214,016 markets; 4,991 open positions, 594 traders currently stuck). §3a/§4b. This is a code fix (one column added to one `UPDATE` statement) but its *effect* is currently blocking, and per the read-only scope of this task it has not been touched.
2. **No live cohort/candidate-set exists for Phase 2 to consume** — only two frozen snapshots (2025-11-01, 2026-08-15), both pre-dating the sweep and the corrected LEGENDARY anchor. The cutover decision that would define this is explicitly unmade. §5.
3. **Ingestion-stall detection does not exist**, despite being named mandatory by the project's own handover before any months-long passive run. §5.

### DEGRADING
4. Canonical-writer migration is 48.8%/51.2% split, not "1 of 13" — real but bounded; 2 actively-scheduled writers (`resolve_legendary_markets.py`, `legendary_positions_scan.py`) keep growing the untagged side going forward. §3.
5. `check_resolution_write_atomicity` can only see 48.85% of the resolved population by construction — the atomicity guarantee is real but partial, and shrinking in relative coverage as long as non-canonical writers stay active. §3c.
6. Geo/elections pending-trade-result backlog is flat (~23,000), not draining, while the general flagged-trader backlog drains fast — divergent trend in exactly the category the thesis depends on. §4a.
7. `check_canonical_definitions.py`'s 7 hardcoded-threshold violations sit in the exact six scripts (`trader_skill_metric_v2*.py`) that compute the candidate metric, against a threshold (`geo_elo_active`) known to decay/drift — a latent correctness risk for Phase 2's own metric, not just a style nit. §1c.
8. "timestamp mixed formats" REGRESSION growing ~650/day — an active, ongoing write-path inconsistency, not historical residue. §4a.
9. Elevated position synthetic-close rate on smaller organic markets (up to 33%), not root-caused this session. §2.

### COSMETIC
10. "`data_source` not in canonical set" — flat at 577 for 3 straight days, frozen legacy population, not growing.
11. "`total_invested` mismatch >5%" — slow drift (~10-15/day), no identified consumer depends on this being exact.
12. Duplicate/contradictory Telegram log lines ("Alert sent." immediately followed by "Credentials not found — skipping alert.") in the same audit run — confusing but harmless.

### NOT A PROBLEM (investigated, cleared)
13. **Pre-ELO integrity gate does not fail daily** — the prompt's own premise was wrong; it passes (0 CRITICAL, both checked days), and the real daily failure belongs to a different, deliberately non-blocking step. §1a.
14. Test suite failure set is stable and matches the documented snapshot-vs-live drift exactly; nothing new joined. §1b.
15. Canonical-definitions-drift violation set unchanged (still exactly 7) across the window. §1c.
16. `PRAGMA integrity_check` = ok; `trg_resolved_no_unresolve` armed; `check_resolution_write_atomicity` stable at 0/0 within its (partial) visibility. §3c.
17. Daily-maintenance's runtime growth is fully explained by the known, budgeted Sunday `discover_leaderboard_traders.py` step — not the sweep's backlog. §4d.
18. Sweep-resolved markets do not trace *worse* than organically-resolved ones on trade-result completion or position-close cleanliness in the sampled comparison — if anything the reverse. §2.

---

## WHAT REMAINS UNCHECKED (named, not chased — scope discipline)

- `monitoring/database.py`'s direct resolved-write (line 551): not confirmed whether it sits on an actually-invoked live path or is dead code.
- `background_pnl_worker.py`'s exact trigger predicate: not read line-by-line; the requeue→P&L causal chain is inferred from `requeue`'s documented purpose (reset `pnl_last_updated` to NULL) plus §4b's verified numbers, not from tracing the worker's own SELECT.
- Synthetic-close-rate divergence between sweep and organic markets (§2): observed, not root-caused.
- `backfill_o16_tier1.py`/`backfill_o16_tier2.py`/`fetch_market_resolutions.py`/`fix_expired_unresolved.py`: presumed dormant/legacy based on prior project history and absence from `daily_maintenance.py`'s STEPS list, not independently confirmed no cron/manual invocation exists anywhere.
- 08-28's exact test-suite failure lines (file was overwritten by 08-29's run before this check); inferred stable from matching status/duration only.

No plan is proposed here, per the task's instruction — this is the read.
