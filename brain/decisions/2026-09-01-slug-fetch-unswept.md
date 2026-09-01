# Gamma Slug Fetch — Unswept Residual — SESSION-START CHECK + PHASE-2 BLOCKER

**Date:** 2026-09-01, ~15:28–15:40 UTC. **Type:** read-only check, then a
blocked launch. **Prior:** `2026-08-31-slug-fetch.md` (291aeb1), OUTSTANDING
section. **Script:** first-repo `scripts/fetch_relevance_slugs.py` @ f6830d7.
**Tagging:** `[V]` verified this session · `[!]` blocker.

---

## VERDICT

**Phase 1 check: CLEAN.** All services up, DB intact, daily_maintenance
completed with the pre-ELO gate passing, staging table and markets/trades
fingerprint consistent (only NULL/unresolved buckets moved, all explained by
two days of normal resolution progress — no count decreased in any total).

**Phase 2: COMPLETE** after a two-blocker chain, each surfaced and handled
explicitly rather than worked around:

1. **Synthetic-id front-loading.** `--population unswept` as-is trips the
   hardcoded 10 % not_found abort at batch ~2 — 3,396 (7.76 %) synthetic
   zero-padded/malformed ids cluster in the first keyset decile, spiking the
   *cumulative* not_found rate to 46–95 % early. **Handled (option 1):**
   pre-staged the 3,396 as a provenance-distinguishable a-priori `not_found`
   (`http_status=NULL`, distinct `run_id`), which scoped the fetch to the
   40,351 real conditionId-shaped ids via the script's own resume-skip —
   **zero script change**.

2. **`closed=true` hardcoded for every population.** Correct for `swept`
   (resolved markets) but wrong for `unswept` (locally-unresolved) — direct
   Gamma re-query showed all 83 batch-1 "not_found" ids are real, live
   markets, absent only because they're `closed=False`. Probed the param
   (Part 2): it's a strict binary filter, no "both" value. **Fixed (Part 3,
   user-approved):** `closed` kwarg on `gamma_batch()` defaulting to today's
   exact `swept` query (byte-diffed, unchanged), plus a two-pass
   `closed=false`+`closed=true` merge for `unswept` only, paired pacing
   baseline (18.6 s vs swept's unchanged 9.3 s), 429-on-either-call handling.
   Verified against a known-open+known-closed pair and against the same 83
   ids (now 83/83 `found`).

**Result:** `run_id=slugfetch-unswept-20260901T155139Z`, **COMPLETE** in
44 min, **40,257 found / 94 not_found (0.233 %) / 0 no_slug / 0 error**
over the 40,351 real ids. `event_slug` non-empty for 100 % of found rows.
`markets` untouched, `trades` +1 (live monitor), atomicity check 0, terminal
marker + Telegram fired. Side-finding: **33,716 of the 40,257 (83.7 %) are
already closed on Gamma while locally `resolved=0`** — a direct measure of
the O-36 detection lag. `run_tests.py` — see §(h).

---

## PHASE 1 — SESSION-START CHECK

### 1. Services / uptime / boot `[V]`

| check | result |
|---|---|
| `polymarket-monitoring` | **active** |
| `polymarket-observer` | **active** |
| `polymarket-sunday-elo` | inactive/dead (oneshot; expected — not Sunday) |
| uptime | **10 days** (up since 2026-08-22 09:29) |
| boot since 2026-08-31 | **none** — last boot 2026-08-22 09:29, current boot id unchanged since |

### 2. Today's `daily_maintenance` `[V]`

| field | value |
|---|---|
| start / end | **2026-09-01 06:00:01 → 09:51:23Z** (13,882 s ≈ 3.85 h) |
| exit code | **0** |
| steps | **31 / 33 OK** — 29 numbered + 4 post-suite (WAL checkpoint, backfill dates, hydrate stubs) minus overlap; summary line: `FAILURES: 31/33 OK` |
| failed steps | (a) **[8/29] Canonical definitions drift** — `check_canonical_definitions.py` exit 1, **non-blocking**, chronic (16th occurrence in the log; present every day 08-28…09-01). (b) **Run test suite** — `test_backtest_window_population.py` only (5 hardcoded-count-drift tests), pre-existing, = the established baseline. |
| **pre-ELO gate** | **[7/29] Integrity audit (pre-ELO gate)** — `audit_invariants.py` **OK (72.1 s)** → gate **PASSED**, ELO steps 9–27 all ran OK |
| long pole | [12/29] backfill_transaction_hashes 11,248 s (~3.1 h) — normal for this step |

**M9 — [15/29] Backfill market categories (`backfill_market_categories.py`) `[V]`:**
**ran, OK (83.4 s), did real work — not a no-op.**
`category_backfill` 09:24:51 → 09:26:14, finished `classified=11910 skipped=7974
errors=1`. Day-over-day delta vs 08-31 (`classified=11880 skipped=7944
errors=1`): **+30 classified, +30 skipped, errors flat at 1**. The single error
is persistent and identical across 08-29 / 08-30 / 08-31 / 09-01 — a stable
known bad row, not a new regression. `category_backfill_state.json` offset
18844 → 19904 (vs last-committed baseline, i.e. accumulated drift, not one day).
No `category` / `category_source` / `category_classification_log` writes from
this step affect the slug-fetch scope.

### 3. DB integrity `[V]`

| check | result |
|---|---|
| `PRAGMA integrity_check` | **ok** (full run on the ~19 GB DB, exit 0) |
| `PRAGMA journal_mode` | **wal** |
| `check_resolution_write_atomicity` run 1 | **0** |
| `check_resolution_write_atomicity` run 2 | **0** → **stable**, not transient |
| `trg_resolved_no_unresolve` exists | yes (only trigger in `sqlite_master`) |
| `trg_resolved_no_unresolve` fires | **yes** — `UPDATE markets SET resolved=0 WHERE resolved=1` inside a txn → `RAISE(ABORT, 'resolved cannot transition from 1 to 0')`, exit 1, rolled back, resolved counts unchanged |

### 4. `relevance_slug_staging` intact `[V]`

| field | 2026-08-31 post-fetch | now | Δ |
|---|---|---|---|
| rows / distinct `market_id` | 26,506 / 26,506 | **26,506 / 26,506** | 0 |
| `found` | 26,491 | **26,491** | 0 |
| `not_found` | 15 | **15** | 0 |
| `no_slug` / `error` | 0 / 0 | **0 / 0** | 0 |
| `run_id` | `slugfetch-swept-20260831T192901Z` (all) | **same, all rows** | — |

Row count matches the 26,506 target exactly; outcome breakdown byte-unchanged.

### 5. markets / trades fingerprint vs 2026-08-31 post-fetch `[V]`

| metric | 08-31 post-fetch | 2026-09-01 now | Δ | note |
|---|---:|---:|---:|---|
| markets_total | 792,793 | **792,814** | +21 | ↑ ok |
| trades_total | 12,514,904 | **12,514,980** | +76 | ↑ ok |
| category_source NULL | 780,826 | **780,847** | +21 | ↑ tracks markets_total |
| category_source legacy | 11,967 | **11,967** | 0 | stable |
| resolved = 0 | 354,181 | **354,067** | **−114** | ↓ — see below |
| resolved = 1 | 438,612 | **438,747** | +135 | ↑ |
| resolution_evidence_source NULL | 577,954 | **577,584** | **−370** | ↓ — see below |
| resolution_evidence_source clob | 214,775 | **215,162** | +387 | ↑ |
| resolution_evidence_source gamma | 63 | **67** | +4 | ↑ |
| resolution_evidence_source hydration_fill | 1 | **1** | 0 | stable |
| category_classification_log rows | 0 | **0** | 0 | stable — no classification writes |
| category distribution | 24 values | **24 values** (Unknown 778,978) | — | same value set |

**Two COUNT DECREASES, both benign and fully explained — NOT flagged as
corruption `[V]`:**

- `resolved=0` **−114** while `resolved=1` **+135**: markets transitioned
  0→1 over two `daily_maintenance` cycles (08-31, 09-01) + live monitor.
  Net new markets +21; 135 − 114 = 21 balances exactly. The
  `trg_resolved_no_unresolve` trigger (verified firing, §3) forbids the
  reverse. This is `fast_resolution_check` + `resolution_sweep` doing their job.
- `resolution_evidence_source=NULL` **−370** while clob **+387** / gamma **+4**:
  same resolution progress — NULL rows acquire an evidence tag as they resolve.
  −370 ≈ +391 non-NULL − 21 new NULL rows. Consistent.

No absolute/total count decreased (markets_total, trades_total, legacy,
classification_log, clob, gamma all flat-or-up). Fingerprint **PASS**.

### 6. Last night's 03:00 backup `[V]`

| field | value |
|---|---|
| ran? | **yes** — cron `0 3 * * *` fired 2026-09-01 03:00:01Z |
| lock | **acquired** (flock; no `SKIPPED` line — ran as sole instance) |
| finished | 04:02:15Z — exit **0** |
| duration | **~62 min** |
| artifact | `data/backups/polymarket_tracker_2026-09-01.db` (19,019,685,888 B ≈ 17.7 GiB; +11 MB vs 08-31 — normal growth) |
| retention | 4 backups kept |

### 7. Git `[V]`

| repo | branch | vs remote | source changes pending? |
|---|---|---|---|
| first-repo | `main` | **level with `origin/main`** (0 ahead / 0 behind) | **none** |
| trading-swarm | `master` | **level with `origin/master`** | **none** (this doc is new, uncommitted by design of the task) |

Working trees carry only automation-generated dirt — first-repo: 4 modified
state/log files (`data/.last_requeue_run` → 2026-09-01T09:35:53Z,
`data/category_backfill_state.json`, `logs/arb_bot_exclusions.log`,
`logs/focus_ratio_review.json`) + untracked characterization/checkpoint JSONs
(incl. the 08-31 `slug_fetch_swept_*` markers); trading-swarm: brain state
JSONs, agent logs, `agent_registry.json`, untracked dated agent-outputs. Same
class of files as the session-start snapshot. No code or decisions unpushed.

---

## PHASE 2 — THE UNSWEPT RESIDUAL FETCH

### Residual re-derivation (live, today) `[V]`

Query = `POPULATIONS["unswept"]` verbatim from the script:
`category='Unknown' AND (resolved=0 OR resolved IS NULL) AND title IS NOT NULL`,
then `prefilter(title) == "RESIDUAL"` (`monitoring/relevance_prefilter.py`).

| | 2026-08-31 doc | 2026-09-01 live | Δ |
|---|---:|---:|---:|
| raw WHERE rows | — | 352,930 | — |
| **RESIDUAL after prefilter** | **43,837** | **43,747** | **−90** |
| batches of 100 | ~438 | **438** | — |
| already staged (would skip) | — | **0** | — |
| net work | — | **43,747 → 438 batches** | — |

The population moved by −90 in one day, as the prior doc predicted ("moves
daily"). 0 overlap with the 26,506 swept rows (swept = resolved+clob; unswept =
unresolved — disjoint by construction). Net work is the full 43,747.

### Synthetic-id fraction `[V]`

| check on the 43,747 residual `market_id`s | count | % |
|---|---:|---:|
| conditionId-shaped `^0x[0-9a-fA-F]{64}$` | 40,351 | 92.24 % |
| contains a 16×`0` synthetic-padding run | 3,371 | 7.71 % |
| length ≠ 66 (incl. 1 empty string) | 3,396 | 7.76 % |
| **NOT conditionId-shaped (synthetic)** | **3,396** | **7.76 %** |

Prior work quoted ~7.3 %; today **7.76 %**. Synthetic ids share the low
`0x03..` prefix (`0x0300`–`0x03ff`), e.g.
`0x030000ac451176a0c4d1202153e18e08080000000000000000000000000000`.

### Expected not_found floor `[V]`

- Structural floor from synthetic ids (each is guaranteed not_found — not a
  real conditionId Gamma can return): **7.76 %**.
- Real-conditionId miss rate, from the swept run: **0.057 %** of the 92.24 %
  real portion ≈ **0.05 %**.
- **Expected overall not_found ≈ 7.8 %.** A final-tally not_found in the
  **7–9 %** band is consistent with the synthetic fraction and is **NOT** an
  abort signal. Only a final rate **materially above ~9 %**, with the excess
  concentrated in conditionId-shaped ids, would indicate a real Gamma coverage
  gap. The script's hardcoded 10 % constant is **not** being raised.

### `[!]` BLOCKER — the abort check trips on keyset ordering

The 3,396 synthetic ids are **front-loaded**, not spread through the run:

| keyset decile (`market_id ASC`) | synthetic count |
|---|---:|
| decile 0 (first ~4,375 ids) | **3,372** |
| decile 9 (last) | 24 |
| all others | 0 |

They cluster because they all share the `0x00..`–`0x03..` prefix and the run is
ordered by `market_id ASC`. First non-synthetic id is at keyset index 1;
the synthetic block runs ~contiguously to index ~3,400.

Script abort logic (`fetch_relevance_slugs.py:270-280`), unchanged at f6830d7:

```
seen    = tally["found"] + tally["no_slug"] + tally["not_found"]
if seen >= 100:
    nf_rate = tally["not_found"] / seen           # cumulative, whole run
    if nf_rate > 0.10:  -> ABORT + ABORTED marker + Telegram
                           "identifier assumption likely wrong"
```

Simulated cumulative not_found rate (synthetic → not_found, real → found):

| after batch | n seen | cum not_found rate |
|---:|---:|---:|
| 1 | 100 | ~1 % |
| **2** | 200 | **~46 %** ← **ABORT FIRES HERE** |
| 3 | 300 | ~64 % |
| 10 | 1,000 | ~88 % |
| 30 | 3,000 | ~95 % (peak) |
| 40 | 4,000 | ~84 % |
| 70 | 7,000 | ~48 % |
| ~340 | ~34,000 | first drops below 10 % |

**Run as-is, `--population unswept` aborts at batch 2** with a spurious
"identifier assumption likely wrong" signal and Telegram. It cannot complete.
The prior doc's guidance ("read the 10 % threshold with [the synthetic
fraction] in mind") assumed the fraction lifts the *overall* rate to ~8 %; it
did not account for the *ordering* making the *running cumulative* rate spike
to 95 % mid-run. Reasoned about explicitly, not silently patched, per standing
instruction.

### Options (need a decision — none taken this session)

1. **Pre-exclude the 3,396 synthetic ids from the population**, stage them
   directly as `not_found` (outcome is known a priori), and run the fetch over
   the 40,351 real conditionId-shaped ids only. Cleanest: the fetch's
   not_found rate then reflects only genuine Gamma coverage gaps and the 10 %
   check works as designed; ~34 fewer batches (~3 min). The synthetic ids
   still reach the LLM stage on title only, exactly as the 15 swept not_found
   do. Requires either a one-off staging insert + a `--population` variant or a
   small script change.
2. **Change the abort check to compute nf_rate over conditionId-shaped ids
   only** (exclude known-synthetic from numerator and denominator). Keeps one
   pass; a script edit to `fetch_relevance_slugs.py`.
3. **Run with the not_found abort disabled / raised**, monitor the tally by
   hand, and reason about the final rate against the 7.8 % floor. The task
   explicitly forbids doing this *silently*; doing it *documented* is on the
   table but is the weakest option (loses the guard for the whole run).

Runway is not the constraint: current 2026-09-01 15:35 UTC, next maintenance
boundary 2026-09-02 02:30 UTC = **10.9 h**; projected run 438 × 4.6 s ≈
**33.6 min**. Fits with hours to spare under any of the three options.

---

## VERIFICATION ITEMS (a–g) — NOT EXECUTED

The fetch was not launched. Items (a) staged-count / outcome split, (b)
synthetic-vs-real split of not_found, (c) `event.slug` non-empty fraction,
(d) markets/trades fingerprint before/after, (e) `check_resolution_write_
atomicity = 0` post-run, (f) terminal marker + Telegram, (g) `run_tests.py`
vs the 18/1 baseline — all pending the §Options decision.

Baseline for (g), unchanged and confirmed this session: **first-repo
`run_tests.py` = 19 files, 18 pass, 1 fail (`test_backtest_window_
population.py`, 5 count-drift tests)**. Any *other* file failing blocks.

---

## UPDATE 2026-09-01 ~15:40–15:50 UTC — option 1 executed, NEW blocker found

User directed: proceed with **option 1, pre-exclude the synthetics**.
Rationale on record: the 3,396 zero-padded/malformed ids are not real
conditionIds, Gamma cannot return them, their outcome is knowable a priori,
and asking anyway wastes calls and pollutes a guard built specifically to
detect the identifier assumption failing. Pre-staging them records what is
already known and leaves the guard measuring genuine Gamma gaps among real
conditionIds.

### 1. Synthetic-id predicate — defined and verified live `[V]`

```
synthetic  :=  market_id does NOT match  ^0x[0-9a-fA-F]{64}\Z
```
i.e. not a 66-character `0x`-prefixed 64-hex-digit string — the exact and only
shape Gamma's `conditionId` takes. Complementary to "conditionId-shaped" by
construction, so the two sets partition the residual with zero overlap.

| check | result |
|---|---:|
| residual total | 43,747 |
| conditionId-shaped | 40,351 (92.24 %) |
| synthetic | **3,396 (7.76 %)** — matches the 3,396 figure from the Phase-1 check |
| partition exact (shaped + synthetic = total) | **True** |
| overlap shaped ∩ synthetic | **0** |
| synthetic already present in staging | **0** |

Sub-characterisation of the 3,396 (all un-askable — none is a valid
`condition_ids` value for Gamma's `/markets` endpoint):

| shape | count | example |
|---|---:|---|
| 62-hex-digit zero-padded pseudo-id (`0x03..0000`) | 3,371 | `0x030000ac451176a0c4d1202153e18e08080000000000000000000000000000` |
| bare 6-digit decimal internal id | 24 | `559695` |
| empty string | 1 | `''` |

### 2. Pre-stage — written, verified distinguishable `[V]`

3,396 rows inserted into `relevance_slug_staging`:

| column | value |
|---|---|
| `outcome` | `'not_found'` (same value as a genuine Gamma miss — outcome is the same fact) |
| `market_slug` / `event_slug` / `event_title` / `n_events` / `gamma_closed` | **NULL** — nothing was fetched, nothing to record |
| `http_status` | **NULL** — distinguishes "no request was made" from a real 200-with-nothing-returned; a genuine ask-and-miss always carries `http_status=200` |
| `run_id` | `slugfetch-unswept-prestage-synthetic-20260901T154100Z` — carries the *reason* in the id itself, so a reader doesn't need a side table to know why |
| `fetched_at` | pre-stage timestamp |

Verification:

```
run_id                                                | outcome   | http_status | count
slugfetch-swept-20260831T192901Z                      | found     | 200         | 26,491
slugfetch-swept-20260831T192901Z                      | not_found | 200         | 15
slugfetch-unswept-prestage-synthetic-20260901T154100Z | not_found | NULL        | 3,396
```

`prestage rows with non-NULL http_status = 0`; `real not_found rows (200) =
15` (all swept, none unswept-prestage) — **fully distinguishable, confirmed
`[V]`**. `markets`/`trades` fingerprint before/after the pre-stage: **792,814
/ 12,514,980 → unchanged** (staging-table insert only, same reasoning as
`2026-08-31-slug-fetch.md` §5 — INSERT-only into a non-core table, no
UPDATE/DELETE/ALTER anywhere in the pre-stage script).

**Revert:** `DELETE FROM relevance_slug_staging WHERE run_id =
'slugfetch-unswept-prestage-synthetic-20260901T154100Z'` — fully reversible,
one `run_id` predicate, touches nothing else.

### 3. Scoping the fetch — script change: NONE `[V]`

No edit to `fetch_relevance_slugs.py`. Scoping is achieved entirely through
the script's own resume-skip: `already_staged()` (lines 121-125) excludes
every `market_id` with a non-`'error'` outcome from `work`, regardless of
which run wrote it. Pre-staging the 3,396 synthetics with a definitive
outcome makes the script's *own* logic exclude them:

```
[2026-09-01T15:41:39Z] residual markets: 43,747  ->  438 batches of 100
[2026-09-01T15:41:39Z] resume: 29,902 market_ids already in staging — skipping them
[2026-09-01T15:41:39Z] to fetch this run: 40,351
```

`29,902 = 26,506 swept + 3,396 pre-staged`; `40,351` = exactly the
conditionId-shaped population, confirmed by the independent live count in §1.
**Minimal (zero diff) and trivially revertible** (delete the pre-stage rows
and the next run's `work` reverts to the full 43,747).

One cosmetic side-effect, noted so it isn't misread: `n_batches` in the
checkpoint/marker is computed from `len(residual)` = 43,747 → 438, not from
`len(work)` = 40,351 → 404 — so a completed run's marker will show
`batches_completed=404, n_batches=438`. The `COMPLETE` verdict itself is
judged against `len(work)` (script line 320), so this does **not** affect
correctness, only the two numbers look mismatched at a glance.

Launched: `set -a; source ~/.env_trading; set +a`, confirmed both Telegram
vars present, then `nohup python3 -u scripts/fetch_relevance_slugs.py
--population unswept > logs/slug_fetch_unswept.log 2>&1 & disown`. Runway at
launch (15:41:20 UTC): **10.81 h** to the 02:30 UTC boundary vs a projected
**31.0 min** run (404 × 4.6 s) — fits with hours to spare. No sweep segment or
`daily_maintenance` running (checked).

### 4. `[!]` NEW BLOCKER — not the synthetic-id issue; a `closed=true` mismatch

The guard fired again, immediately — but for a **different, deeper reason**
than the front-loading issue in the original blocker:

```
[2026-09-01T15:41:42Z] ABORT: not_found rate 83.0% > 10% at n=100 — identifier assumption likely wrong
[2026-09-01T15:41:43Z] === END  status=ABORTED  batches=1/438  tally={'not_found': 83, 'found': 17}  telegram_sent=True ===
```

**Root-caused, not assumed.** Pulled all 83 `not_found` `market_id`s from
this run's staged rows and re-queried Gamma directly, **without** the
`closed=true` parameter the script hardcodes:

```
queried 83 without closed filter -> 83 found on Gamma
closed-flag breakdown among found: {False: 83}
genuinely missing from Gamma even without closed filter: 0
```

**All 83 of 83 exist on Gamma right now, with real slugs, and are `closed:
False`.** Single-id confirmation:

| | with `closed=true` (what the script sends) | without a `closed` filter |
|---|---|---|
| `0x00000977…ff707` ("Will Zelenskyy and Putin meet next in Saudi Arabia before 2027?") | `[]` — not found | `{conditionId: …ff707, slug: 'will-zelenskyy-and-putin-meet-next-in-saudi-arabia', closed: False, active: True, archived: False}` |

`gamma_batch()` (`fetch_relevance_slugs.py:138`) hardcodes
`q = [("closed", "true"), ...]` for **every** population. That is correct for
`swept` (population = `resolution_evidence_source='clob'`, i.e. markets this
DB already knows are resolved — closed on Gamma too, matching the 08-31 run's
clean 0.057 % not_found). It is **structurally wrong for `unswept`**, whose
population is *defined* as `resolved=0 OR resolved IS NULL` — locally
unresolved markets, the overwhelming majority of which are, correctly,
**still open on Gamma** (`closed=False`). Querying them with `closed=true`
asks Gamma for the one flag value they don't have.

This is **not** a batch-position artifact like the synthetic-id issue — it
follows from what the `unswept` population *is*, so it is expected to depress
`found` (inflate `not_found`) across the **entire** 40,351, not just the
keyset head. A control check confirmed omitting the `closed` param entirely
does not fix it either — it returns 0 rows for a known-swept (resolved,
`closed=true`) id, i.e. Gamma's `closed` filter is a hard binary switch with
no "both" mode from a single value; the fetch needs `closed=false` (or two
passes, `true` and `false`, merged) for a population that is mostly open.

**State after this abort — verified clean `[V]`:**

| check | result |
|---|---|
| `markets`/`trades` fingerprint | **792,814 / 12,514,980 — unchanged**, incl. after the aborted run |
| `check_resolution_write_atomicity` | **0** |
| `relevance_slug_staging` total | 26,506 (swept) + 3,396 (prestage) + 100 (this run's batch 1) = **30,002** |
| this run's batch-1 rows | `found=17`, `not_found=83` — **the 83 are Gamma-real, `closed=False` markets, mislabeled `not_found` by the query bug**, not a true coverage gap |
| terminal marker | written, `status=ABORTED`, `reason` text as logged (accurate as far as it goes — the *guard* fired correctly; my root-cause goes one level past what the reason string says) |
| Telegram | fired, `telegram_sent=True` |
| checkpoint `last_market_id` | `"561275"` — the lexicographically-largest pre-staged synthetic id (a bare decimal, string-sorts after all `0x…` ids); cosmetic only, `work` was never filtered by it (§3) |

**Stopping here rather than re-running.** This is a fetch-logic defect, not a
threshold-calibration question, and fixing `gamma_batch()`'s `closed` param
is a real behaviour change to the shared script (both populations call the
same function) — outside "minimal, revertible scoping" and squarely a
decision the task's own standing instructions (verify before propagating,
reason explicitly, don't silently patch) put back to the user. **The 100
rows staged under `run_id=slugfetch-unswept-20260901T154134Z` in this aborted
attempt contain 83 rows currently mislabeled `not_found` that are real,
open, Gamma-known markets** — flagged here rather than corrected
unilaterally; they should be deleted or re-fetched once the `closed` handling
is resolved, not treated as valid coverage data in the meantime.

### Options for the `closed` fix (none taken)

1. **`closed=false`** for `--population unswept` (population-conditional
   param) — matches what the population is *defined* to be; simplest fix,
   correct for the ~overwhelming majority. Misses the edge case of a market
   that resolved on Gamma before our local `resolved` flag caught up
   (known-lagged per `project_o36_resolution_date_reliability` — LATE-biased
   detection, not early, so this direction is the less likely edge case here).
2. **Two passes per batch** (`closed=true` and `closed=false`, merged,
   `found` if either returns a row) — fully correct regardless of local/Gamma
   staleness in either direction, ~2× the request volume (~62 min instead of
   ~31).
3. **Drop the `closed` param and inspect what Gamma actually defaults to**
   — the control check above (0 rows for a known-closed id with no `closed`
   param) suggests omitting it does **not** mean "both"; would need one more
   direct probe to confirm the default behaviour precisely before relying on
   it.

Runway is not the constraint for any of these — 10+ h remained at launch
against a ≤62-min worst case.

---

## UPDATE 2026-09-01 ~16:00 UTC — probe the `closed` param, clear the mislabeled rows, state the fix (no re-run)

User directed: option 3 (probe first), Part 1 cleanup, then stop for
confirmation before any re-run.

### Part 1 — mislabeled rows cleared `[V]`

The 100 rows staged by the aborted `slugfetch-unswept-20260901T154134Z` run
(17 correct `found` + 83 mislabeled `not_found`, `http_status=200` —
indistinguishable from a genuine miss, and would be skipped by resume-skip
on any future run) are gone.

```sql
DELETE FROM relevance_slug_staging WHERE run_id = 'slugfetch-unswept-20260901T154134Z';
```

| | before | after |
|---|---:|---:|
| `relevance_slug_staging` total | 30,002 | **29,902** |
| rows under `slugfetch-unswept-20260901T154134Z` | 100 | **0** |
| pre-staged synthetic rows (`…prestage-synthetic-20260901T154100Z`) | 3,396 | **3,396 — untouched** |
| swept rows (`slugfetch-swept-20260831T192901Z`) | 26,506 | **26,506 — untouched** |
| `markets_total` / `trades_total` | 792,814 / 12,514,980 | **unchanged** |

Only write this part. `relevance_slug_staging` is back to exactly the
post-pre-stage state (26,506 swept + 3,396 synthetic-prestage = 29,902), ready
for a corrected fetch to resume into.

### Part 2 — probing Gamma's `closed` param, established not assumed `[V]`

Controlled id set: one **known-closed** market
(`0x0000fc81…81fb47`, `wta-gasanov-bandecc-2026-07-13`, resolved/swept-found
under `closed=true` in the 08-31 run) and one **known-open** market
(`0x00000977…ff707`, `will-zelenskyy-and-putin-meet-next-in-saudi-arabia`,
confirmed live and `active` above), queried together in one request per form:

| form | rows returned | which market |
|---|---:|---|
| `closed=true` | 1 | **only the closed one** (`closed: True`) |
| `closed=false` | 1 | **only the open one** (`closed: False`) |
| *omitted entirely* | 1 | **only the open one** — identical result to `closed=false` |

**Established: `closed` is a strict binary filter with no "both" mode.**
Omitting the parameter is not "return everything" — it behaves exactly like
`closed=false` (matches the earlier single-id control test, where omitting it
returned 0 rows for the known-closed id alone). **No single value of this
parameter returns both a closed and an open market in the same call.**　

Per the task's own framing: since no single form covers both, **the two-pass
merge (option 2) is not merely the safer choice among preferences — it is the
only form that gives complete coverage of a population that can legitimately
contain both open and lagged-but-already-closed markets.** `closed=false`
alone (option 1) would systematically miss any `unswept` market that Gamma
has already closed but this DB's `resolved` flag hasn't caught up to yet —
a real, non-hypothetical case per `project_o36_resolution_date_reliability`
(LATE-biased local resolution detection, 29% of resolved geo/elec markets
off >14 days on `resolution_date` — the same underlying detection lag, not
just a date-accuracy issue, can leave a market Gamma-closed while still
`resolved=0` locally).

### Part 3 — the fix, specified but NOT applied

Minimal change, confined to `gamma_batch()` and the batch-request call site;
nothing else in the script changes.

**1. Parameterise `closed` with a default that reproduces today's exact
query for any caller that doesn't pass it:**

```python
def gamma_batch(cond_ids: list[str], closed: str = "true") -> tuple[int, dict]:
    q = [("closed", closed), ("limit", "500")] + [("condition_ids", c) for c in cond_ids]
    ...
```

Today's hardcoded line is `q = [("closed", "true"), ("limit", "500")] + …` —
with `closed: str = "true"` as the default, a call site that passes nothing
produces **the byte-identical query string** it produces today.

**2. Guarantee for `swept`: its call site is not touched.** The only call
site today is `fetch_relevance_slugs.py:236`, `status, by_cid =
gamma_batch(cond_ids)` — no `closed=` argument. `swept` keeps calling it
exactly that way (default → `closed=true`, same as now, same 26,506-row
result already staged and verified 08-31). The guarantee is structural, not
a promise to be careful: **there is only one call site in the file today**
(`grep -n "gamma_batch(" fetch_relevance_slugs.py` → line 138 def, line 236
call), so "don't touch the swept path" reduces to "leave line 236 as
`gamma_batch(cond_ids)` unchanged" and add the new two-pass logic only inside
an `if pop == "unswept":` branch around a *new* call site.

**3. `unswept` gets a second call site, two passes merged:**

```python
if pop == "unswept":
    t0 = time.time()
    status_f, by_cid_f = gamma_batch(cond_ids, closed="false")
    status_t, by_cid_t = gamma_batch(cond_ids, closed="true")
    req_s = time.time() - t0
    by_cid = {**by_cid_f, **by_cid_t}   # disjoint by conditionId; a real id
                                        # is closed XOR open, never both
    status = status_f if status_f == 200 else status_t   # 200 if either succeeded
else:
    t0 = time.time()
    status, by_cid = gamma_batch(cond_ids)
    req_s = time.time() - t0
```

Consequences to record, not yet acted on:
- **~2× request volume for `unswept`** — two Gamma calls per batch instead of
  one. Projected run time roughly **~62 min instead of ~31 min** for the
  404-batch real-id population; runway (10+ h to the next 02:30 UTC boundary
  at last check) absorbs this easily.
- The not_found abort guard (`fetch_relevance_slugs.py:270-280`) needs no
  change — it reads `tally`, which is fed by the merged `by_cid`, so
  `not_found` after the fix means "absent from Gamma under **either** closed
  state" — a genuine gap, which is what the guard is supposed to measure.
- `req_s` / pacing-abort logic should time the pair together (as sketched
  above) rather than either call alone, so the existing `PACING_ABORT_MULT`
  threshold is being compared to the right quantity (two round-trips, not
  one) — worth flagging explicitly rather than leaving it comparing a
  doubled real cost to a single-call baseline.

**Not applied.** No edit made to `fetch_relevance_slugs.py`. Awaiting
confirmation before writing this change and before any re-run.

---

## UPDATE 2026-09-01 ~15:50–16:55 UTC — fix applied, verified, full run launched

User directed: apply the Part-3 fix, verify it directly (not by inference),
then run the fetch. All steps below in order.

### The change — applied `[V]`

`scripts/fetch_relevance_slugs.py`, 3 hunks, +45/-9 lines, `py_compile` clean:

1. **`gamma_batch(cond_ids, closed: str = "true")`** — `closed` param added
   with a default that reproduces today's hardcoded query for any caller
   that doesn't pass it.
2. **Main loop, new `if pop == "unswept":` branch** around the request —
   two sequential calls (`closed="false"` then `closed="true"`), merged
   `by_cid = {**by_cid_f, **by_cid_t}` (disjoint — a market is closed XOR
   open, never both), `status = status_f if status_f == 200 else status_t`,
   with an explicit `if 429 in (status_f, status_t)` check so a 429 on
   *either* call is caught (the naive single-`status` version would have
   missed a 429 on the second call whenever the first succeeded). `swept`'s
   branch (`else:`) is the original two lines, unmoved.
3. **Pacing baseline**: `PAIR_BASELINE_REQ_S = 2 * BASELINE_REQ_S = 6.2s`,
   selected via `pace_baseline = PAIR_BASELINE_REQ_S if pop == "unswept"
   else BASELINE_REQ_S`. Threshold `PACING_ABORT_MULT * pace_baseline`:
   **swept 3.0 × 3.1s = 9.3s (unchanged)**, **unswept 3.0 × 6.2s = 18.6s**
   (paired duration compared to a paired baseline, not a single-call
   baseline — the exact fix asked for).

`not_found` classification: because `by_cid` is the union of both passes,
`by_cid.get(mid) is None` in `classify_row` is true **only when the mid is
absent from both** — there's no code path that sees "absent from pass 1"
alone, since `by_cid` doesn't exist until after both calls return. Confirmed
by test (c) below, not just by reading the code.

### Verify the fix before the full run

**(a) swept's query byte-identical — diffed, not asserted `[V]`**

Imported the actual module, monkeypatched `urlopen` to capture the
constructed URL, called `gamma_batch(cond_ids)` exactly as the `swept`
call site does (no `closed=` argument) and compared byte-for-byte against
the pre-fix hardcoded construction:

```
old hardcoded URL: https://gamma-api.polymarket.com/markets?closed=true&limit=500&condition_ids=0xAAAA&condition_ids=0xBBBB&condition_ids=0xCCCC
new default (swept-style) URL: https://gamma-api.polymarket.com/markets?closed=true&limit=500&condition_ids=0xAAAA&condition_ids=0xBBBB&condition_ids=0xCCCC
BYTE IDENTICAL: True
```

**(b) two-pass path against a known-open + known-closed control set `[V]`**

Called the real `gamma_batch()` (network, not mocked) with the same two
control ids from the earlier probe, through the exact merge logic the
script now runs:

```
status_f (closed=false): 200  keys: ['...ff707' (open)]
status_t (closed=true): 200   keys: ['...81fb47' (closed)]
merged status: 200  merged keys: [both]
 classify_row -> 0x0000fc8139b0 outcome=found slug=wta-gasanov-bandecc-2026-07-13        (closed)
 classify_row -> 0x00000977017f outcome=found slug=where-will-zelenskyy-and-putin-meet-next (open)
```

**Both found.** This is the direct test of what the fix is for, and it
passes.

**(c) the 83 previously-mislabeled ids, re-tested through the real code
path `[V]`**

```
re-testing 83 previously-mislabeled ids through the actual two-pass code path
status_f: 200 n=83   status_t: 200 n=0   merged n=83
outcome tally: {'found': 83}
found-but-empty-slug: 0
```

**83 / 83 now `found`, all via the `closed=false` pass** (`status_t n=0` —
none of them were ever closed on Gamma; they were simply never askable
under the old hardcoded `closed=true`), all with real, non-empty
`market_slug`. These are the exact ids that produced this fix, and they are
now the evidence it worked — not a fresh sample.

### The full run — launched `[V]`

Residual re-derived live at launch time: **43,747** (unchanged from the
earlier derivation this session — no new categorisation between the two
checks). `resume: 29,902 market_ids already in staging — skipping them` →
**`to fetch this run: 40,351`** — the resume-skip scoping confirmed from the
log, not assumed, matching the independent live count
(`already staged (will skip): 3,396`, `NET WORK: 40,351 → 404 batches`).

| | |
|---|---|
| launch | **2026-09-01 15:51:39 UTC** |
| run_id | `slugfetch-unswept-20260901T155139Z` |
| runway to 02:30 UTC boundary | **10.64 h** |
| projected run (404 batches × ~9.1s: 2×3.1s paired req + 1.5s sleep + overhead) | **~61.3 min** |
| expected not_found floor | **≈0.06%** — the swept run's baseline (genuine Gamma absence under *either* closed state), now that the population is scoped to real conditionIds and both closed states are checked. A rate near 8% would indicate the fix regressed; a rate near 0.06% confirms it. The 10% threshold is unchanged and now measures this. |
| no conflicting job | confirmed — no `daily_maintenance` / other sweep segment running |
| batch 1 | `req=5.0s tally={'found': 100}` — **0% not_found**, pacing 5.0s well under the 18.6s paired threshold |

Launched detached: `set -a; source ~/.env_trading; set +a` (both Telegram
vars confirmed present) `; nohup python3 -u scripts/fetch_relevance_slugs.py
--population unswept > logs/slug_fetch_unswept.log 2>&1 & disown`.

### The full run — COMPLETE `[V]`

| | |
|---|---|
| status | **COMPLETE** — 404/404 work batches |
| wall time | **15:51:39 → 16:36:00 UTC = 44 min 21 s** (faster than the ~61 min projection — the two calls pipeline at ~5.0 s/batch, not 9.1 s) |
| pacing | 4.9–5.5 s/batch throughout, **no slow-batch warnings, no 429, no errors, no abort** (`grep` of the full log for slow/abort/error/429/retry → nothing) |
| `n_batches` field | 438 (the residual-based over-count noted earlier); `COMPLETE` is judged against `len(work)` = 404, correctly |
| terminal marker | `data/checkpoints/slug_fetch_unswept_terminal.json` — `status="COMPLETE"`, `batches_completed=404`, `cumulative_tally={"found":40257,"not_found":94}`, `written_at_utc=2026-09-01T16:36:00Z` |
| Telegram | `[TELEGRAM] Terminal notification sent.` · `telegram_sent=True` |

### VERIFICATION

**(a) staged count vs today's residual, outcomes separate `[V]`**

Residual (live, this session): 43,747 → 3,396 synthetic (pre-staged) + 40,351
conditionId-shaped. This run (`run_id=slugfetch-unswept-20260901T155139Z`):

| outcome | count |
|---|---:|
| `found` | **40,257** |
| `not_found` | **94** |
| `no_slug` | **0** |
| `error` | **0** |
| **total / distinct `market_id`** | **40,351 / 40,351** — exactly the conditionId-shaped population |

not_found rate on real conditionIds = **94 / 40,351 = 0.233 %** — above the
swept run's 0.057 %, far below the unchanged 10 % threshold. The elevation is
expected: the unswept population reaches further into obscure / delisted /
never-activated Unknown markets than the swept (all-CLOB-settled) one. The
guard measured this correctly and did not fire.

**(b) not_found split three ways `[V]`**

| source | count | `http_status` | meaning |
|---|---:|---|---|
| pre-staged synthetic (`…prestage-synthetic-20260901T154100Z`) | **3,396** | **NULL** | not a real conditionId — never asked |
| real id, absent from **both** passes (`…-20260901T155139Z`) | **94** | 200 | genuine Gamma coverage gap |
| swept (`…-20260831T192901Z`), unchanged | 15 | 200 | (prior run) |
| anything else | **0** | — | — |

The `http_status` cleanly separates "never asked" (NULL) from "asked, Gamma
had nothing" (200), exactly as designed in Part 2.

**(c) found rows by pass — the O-36 lag, quantified `[V]`**

`gamma_closed` records the `closed` flag Gamma returned; a row found only via
the `closed=false` pass carries 0, one found via `closed=true` carries 1.

| found via | `gamma_closed` | count | % of 40,257 found |
|---|---|---:|---:|
| `closed=true` pass — **Gamma has already closed these** | 1 | **33,716** | **83.7 %** |
| `closed=false` pass — genuinely still open on Gamma | 0 | 6,541 | 16.3 % |

**All 33,716 have local `resolved = 0`** (not NULL — our pipeline explicitly
evaluated them and recorded "not resolved"), yet Gamma has them settled.
This is the O-36 detection lag, measured directly:
**≈33.7 k Unknown-category markets this system believes are unresolved are in
fact closed on Gamma.** It also settles the option-1-vs-option-2 question
retroactively — a `closed=false`-only fetch would have mislabeled all 33,716
as `not_found` (a 84 % miss), and the original `closed=true`-only code
mislabeled the 6,541 truly-open ones (plus the 94) — 6,635 / 40,351 = 16.4 %,
which is why it aborted. The two-pass merge was necessary, not cautious.

**(d) `event.slug` non-empty fraction `[V]`**

| denominator | non-empty `event_slug` | % |
|---|---:|---:|
| `found` rows (40,257) | 40,257 | **100.00 %** (also `market_slug`, `event_title` — all 100 %) |
| full residual population (40,351, swept's comparison basis) | 40,257 | **99.767 %** |

vs swept's **99.94 %** on the same population basis. The 0.17-point gap is
entirely the higher not_found rate (0.233 % vs 0.057 %); every market Gamma
returned has all three slug fields, same as swept.

**(e) `markets` / `trades` untouched `[V]`**

| | before run (15:41 / 15:51) | after run (16:40) |
|---|---:|---:|
| `markets_total` | 792,814 | **792,814 — identical** |
| `trades_total` | 12,514,980 | 12,514,981 (**+1**) |

`markets` byte-count identical. `trades` +1 is live `monitor.py` ingestion
during the 44-min window (≈3 fifteen-minute cycles) — `fetch_relevance_slugs.py`
has no `trades` write path (grep-verified, and re-confirmed by this diff:
the script only ever touches `relevance_slug_staging`). No decrease in any
count. `relevance_slug_staging`: 26,506 + 3,396 + 40,351 = **70,253**.

**(f) `check_resolution_write_atomicity` `[V]`** — **0** (post-run).

**(g) terminal marker + Telegram `[V]`** — both confirmed, see the run table
above.

**(h) `run_tests.py` vs baseline `[V]`**

**19 files run, 18 passed, 1 failed** — the single failure is
`test_backtest_window_population.py` (sub-tests T2/T2b/T2c/T2d/T2f), with the
**exact same observed numbers** recorded in the Phase-1 check
(`tests/LATEST_TEST_RESULTS.md`, 09:42 run): `T2 got 4660`, `T2b got 52`,
`T2c got 578`, `T2d got 644`. Zero drift from baseline. `test_relevance_prefilter.py`
**63/63 PASS**; `test_sweep_terminal_signal.py` (the reused terminal-marker
module) **19/19 PASS**; `test_data_source_write_paths.py` **30/30 PASS**.
**No NEW failure — does not block.** (Baseline this session is 19/18/1; the
08-31 doc's "18 files" predates a test file being added.)

### O-36 side-finding worth carrying forward

The `gamma_closed=1 / local resolved=0` count — **33,716** Unknown-category
markets settled on Gamma but not locally — is a concrete, dated measurement
of the resolution detection lag flagged in
`project_o36_resolution_date_reliability`. It is a by-product of this fetch,
not something it was scoped to fix, but it quantifies the gap far above the
"small edge case" this doc guessed at under option 1. Candidate input for
whatever revisits O-36 / the resolution sweep coverage for Unknown-category
markets.

---

## SCOPE NOT TOUCHED (constraints honoured)

No LLM stage, no prompt. No validation-gate samples. No `category` /
`category_source` / `category_classification_log` writes. `M9`
(`backfill_market_categories.py`), `monitoring/monitor.py`,
`scripts/daily_maintenance.py` unmodified. Services never stopped.

`scripts/fetch_relevance_slugs.py` **was** modified in the final phase
(Part 3, user-approved, +45/-9): the `closed` param on `gamma_batch()` and
the `unswept` two-pass merge. `swept`'s code path is byte-identical (verified
(a)). The earlier phases (pre-stage, scoping) touched no code. The only DB
writes this session: 3,396-row synthetic pre-stage insert, 100-row delete of
the aborted run, and the 40,351-row fetch output — all into
`relevance_slug_staging` only, `markets`/`trades` verified untouched
throughout.
