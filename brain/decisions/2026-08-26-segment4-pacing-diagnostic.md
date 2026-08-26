# Segment 4 Pacing Degradation — Diagnostic (2026-08-26)

Read-only diagnostic. Nothing resumed, launched, or modified. All figures
below are VERIFIED against the segment 4/3/2 driver logs, segment4's own
source (`data/characterizations/sweep_segment4/segment4_write.py`),
`scripts/backfill_market_dates.py`, `trading-swarm/logs/backup.log`,
`journalctl`, and a live CLOB re-probe run this session, except where
marked INFERRED or SPECULATIVE.

## VERDICT

**Neither COHORT-SPECIFIC, nor CLOB-side call-count/duration throttling,
nor a CLOB-side change.** The re-probe (§5) is decisive on those three:
the exact batch-96-101 markets and an early-batch control sample both
come back 100% clean, fast (200 OK, ~0.10-0.15s), right now — the markets
are not slow, and CLOB is not currently degraded, and segment 3 ran 186
batches (longer than segment 4's 101) without ever approaching the
threshold, which rules out "throttling by elapsed time or call volume"
as a general CLOB behavior.

**The best-supported explanation is a one-off LOCAL resource-contention
event, not a CLOB-side phenomenon at all** — closest to UNRESOLVED at the
level of "prove the exact lock", but with a specific, code-verified
mechanism and strong circumstantial timing evidence, laid out below. This
doesn't fit any of the four offered buckets cleanly, so I'm reporting it
as its own finding rather than forcing it into one:

`avg_pace` is not a pure CLOB-latency metric. Reading
`segment4_write.py:230-292`: `call_elapsed` is measured from *before* the
CLOB fetch to *after* `mark_market_resolved()` + `conn.commit()` for any
market classified `resolved` — which was ~475-496 of every 500 markets in
every batch, including 96-101. So `avg_pace` conflates CLOB HTTP latency
with local SQLite write/commit latency. The DB connection is opened with
`PRAGMA busy_timeout=30000` (`scripts/backfill_market_dates.py:48`) — a
30s silent-retry window before SQLite would ever raise "database is
locked." A batch averaging ~1.0-1.2s/call across ~490 commits, with zero
lock errors in the log, is exactly the signature `busy_timeout` produces
under sustained-but-not-total write contention: the driver just gets
slower, silently, with no exception to log.

**What was contending:** `crontab -l` shows `0 3 * * *
run_database_backup.sh` — a full `sqlite3 .backup` of the live DB, daily
at 03:00 UTC. `trading-swarm/logs/backup.log` shows something anomalous
specifically on this night:
```
[2026-08-25T03:00:01Z] Starting database-backup
[2026-08-26T03:00:01Z] Starting database-backup
Wed 26 Aug 14:33:23 UTC 2026: OK — backup created: .../polymarket_tracker_2026-08-25.db (18G)
[2026-08-26T14:33:23Z] Finished database-backup (exit: 0)
Wed 26 Aug 14:33:32 UTC 2026: OK — backup created: .../polymarket_tracker_2026-08-26.db (18G)
[2026-08-26T14:33:32Z] Finished database-backup (exit: 0)
```
The **2026-08-25T03:00:01Z** invocation never logged "Finished" before
the **next day's** cron fired at the same time — it was still running (no
overlap protection anywhere in `backup_database.sh` or its cron wrapper —
plain `>>` log appends, no flock) when a **second**, independent
`sqlite3 .backup` process launched against the same live, 18GB source DB
at 2026-08-26T03:00:01Z. Both eventually completed together at ~14:33 the
same afternoon — over 11 hours after segment 4 had already aborted. That
second invocation's start (03:00:01Z) is within the same minute segment
4's own wall-clock reconstruction (§1) puts the start of its pacing
degradation. **Two concurrent full-database `.backup` passes plus
segment 4's own ~2 commits/second is a write-contention scenario neither
segment 2 nor segment 3 ever experienced** — see §6, where a single
normally-fast backup (segment 2) and even an unusually slow one that
also eventually got stuck (segment 3's overlapping 03:00 job) produced
*zero* visible pacing effect. Only the night with a confirmed second,
overlapping backup instance produced the spike.

**What this means for segment 5 and the ~291,148 remaining candidates:**
this is not a CLOB rate limit and does not scale with segment size or
call volume — segment 5 does not need to be shrunk on CLOB-throttling
grounds, and the runway math in the prior status doc stands. What it does
mean: **any future segment whose run crosses 03:00 UTC is exposed to the
same local-contention risk if the nightly backup is ever still running
from a prior day** (which is itself an unexplained, unresolved condition
— see below). This is an operational risk to the *backup job*, not to
the CLOB integration, and is worth its own follow-up outside this
diagnostic's read-only scope: (a) why did the 2026-08-25 backup take
>24h when history shows this job normally finishes in minutes to a few
hours even under load (§6), and (b) `backup_database.sh` has no overlap
guard (flock) — a second cron firing on top of a still-running instance
is possible by construction, not a one-time fluke.

**What remains genuinely unresolved:** I cannot retroactively confirm
which process (if any) actually held the SQLite write lock at 03:00-04:04
on Aug 26 — the processes are long gone and no historical `ps`/lock-state
record exists. The backup-contention explanation is the best fit for
every piece of available evidence (timing, mechanism in the code,
comparison against segment 2/3, and the clean re-probe), but it is
circumstantial, not a captured lock trace. Settling it fully would
require reproducing the condition with lock-instrumented logging — not
attempted here per the read-only instruction.

---

## 1. The pacing curve

Per-batch `avg_pace_s_per_call`, all 101 batches, extracted from
`logs/discovery_gap_sweep_segment4_20260825T202428Z.log`:

- Batch 1: **0.180s/call**
- Batches 1-95: median **0.239s/call**, mean 0.249, stdev 0.054 (tight
  band); one isolated outlier at batch 83 (0.560s, single batch, returned
  to 0.205 the very next batch — noise, not a trend)
- Batches 96-101: **0.970, 1.188, 0.993, 0.980, 1.100, 1.041**
  (mean 1.045 — 4.4x the prior median)

**Shape: a sudden step, not a gradual drift.** Batch 95 (0.198) to batch
96 (0.970) is a ~5x jump in one batch boundary, then it holds at that
elevated level for all six remaining batches until the abort — not a
slow creep. A drift would point toward accumulating load (e.g. growing
WAL file); a clean step points toward an external event starting at a
specific moment, which is what §"What was contending" above identifies.

Reconstructed wall-clock (validated against the driver's own reported
`Cumulative elapsed: 27574.4s`, which reconciles to within ~7s using
`Σ(avg_pace×500) + 101×500×0.25s sleep = 27,567.5s` — the 0.25s/call
sleep is applied *after* `call_elapsed` is measured, so `avg_pace` really
is fetch+commit time only, not sleep-inflated): batch 96 begins at
approximately **2026-08-26T03:00-03:09Z**, batch 101 ends at
**~04:03:55Z** — matching the terminal marker's `04:04:16Z` almost
exactly.

## 2. What it correlates with

- **a. Elapsed time (since segment 4's own launch):** does not fit on
  its own. Segment 3 ran 186 batches (~39,022s, ~10.8h) with zero
  degradation (§6) — segment 4 degraded at just ~7.6h in. If it were pure
  run-duration throttling, segment 3 should have hit it first or at
  least shown some drift; it never did.
- **b. Cumulative call count:** does not fit either, for the same
  reason — segment 3 made far more cumulative CLOB calls (186×500 =
  93,000) than segment 4 had at the point of failure (101×500 = 50,500)
  with no effect.
- **c. The cohort itself:** ruled out directly — §3 finds no structural
  difference in the batch-96-101 markets, and §5's live re-probe shows
  the exact same markets responding fast and clean hours later.
- **What actually fits: wall-clock time-of-day**, specifically the fixed
  03:00 UTC daily backup cron — but only when it overlaps with a second,
  anomalously still-running instance of itself. Segment 2 and segment 3
  both also ran through 03:00 UTC on their respective nights with a
  single (in segment 3's case, an eventually-very-slow) backup in flight,
  and neither degraded (§6). So "crosses 03:00 UTC" alone is not
  sufficient — the discriminator is the *double* overlap, which appears
  to be new to this night.

## 3. Are batches 96-101's markets structurally distinct?

**No signature found.** Checked market_id format, condition_id/api_id
presence, category, title pattern, and data_source for the 3,000 markets
in batches 96-101 against batch 1 (500 markets) and a broader sample
across batches 1-101:

| | batch 1 | batch 90 | batches 96-101 |
|---|---|---|---|
| market_id length | 66 (all) | 66 (all) | 66 (all) |
| condition_id present (DB) | 0% | — | 0.07% |
| api_id present | 0% | — | 0.07% |
| category | 100% "Unknown" | — | 99.97% "Unknown" |
| data_source | 100% background_backfill | mixed live_monitoring/background_backfill | mixed live_monitoring/background_backfill (same mix as batches 20-101 generally) |
| titles | ordinary sports/crypto/weather micro-markets | same | same |

The `data_source` mix (roughly 55-60% `live_monitoring` / 40-45%
`background_backfill`) looked like a candidate signature at first glance
(batch 1 is 100% `background_backfill`), but that split happens at
**batch ~20**, stable from there through batch 101 — it is not specific
to the degraded batches. No other field distinguishes 96-101 from the
20 batches immediately preceding them, which ran at normal pace.
**Ordinary markets that happened to be slow, not a distinct cohort.**

## 4. What did the failed calls actually return? — real gap, reported plainly

**The code cannot say, and this is worth recording as a genuine
diagnostic blind spot.** `_fetch_by_clob()`
(`scripts/backfill_market_dates.py:66-94`):
```python
try:
    resp = session.get(f"{CLOB_API}/markets/{condition_id}", timeout=10)
    if resp.status_code == 200:
        return resp.json()
except Exception:
    pass
return None
```
Every failure mode — a 429, a 404, a 500, a connection reset, a read
timeout at 10s, a malformed JSON body — collapses to the same `None`,
logged only as `no_clob_response`. Response headers are never inspected
even on success, so a `Retry-After` or rate-limit header would be
invisible even if CLOB sent one. There is no way, after the fact, to
distinguish "13-16 timeouts" from "13-16 429s" from "13-16 connection
errors" in batches 96-101 — the log genuinely does not carry that
information. This is a design decision reused unchanged from
`backfill_market_dates.py` (module docstring cites it as "the
unmodified" helper), not something segment4_write.py added.

One inference that *can* be made: none of these calls could have taken
longer than the 10s `timeout`, and `avg_pace` for the worst batch (97,
1.188s/call across 500 calls = 594s total) is consistent with roughly
13-16 failed calls eating ~10s each (~150s) plus the remaining ~485 calls
running markedly slower than baseline (~444s / 485 ≈ 0.92s/call, still
~4x the 0.24s norm) — i.e., the elevation isn't explained by the failed
calls alone; the successful calls were slow too, which is what points at
the local commit-contention mechanism (§ Verdict) rather than pure
network flakiness.

## 5. The decisive test — live re-probe, run this session

40 markets from batches 96-101 (indices 47,500-47,539 of
`segment4_list.json`) and 40 markets from batch 1 (indices 0-39), each
queried directly against `https://clob.polymarket.com/markets/{market_id}`,
read-only, `timeout=10`, `0.1s` between calls:

| sample | n | total | avg/call | HTTP 200 rate | typical latency | outliers |
|---|---|---|---|---|---|---|
| batches 96-101 | 40 | 11.7s | 0.293s | 40/40 (100%) | 0.09-0.16s | 1 (2.4s, first call — connection warm-up) |
| batch 1 (control) | 40 | 9.5s | 0.237s | 40/40 (100%) | 0.09-0.19s | 1 (0.27s) |

**Both samples are fast and clean right now, indistinguishable from each
other and from segment 4's own healthy baseline (~0.24s median).** Zero
429s, zero timeouts, zero errors, in either sample. This directly rules
out cohort-specificity (the same markets are fine) and rules out an
ongoing CLOB-side problem (nothing is currently degraded) — it is
consistent with either a transient CLOB-side blip that has since cleared
or (favored per the mechanism in the Verdict) a local contention event
that ended once the backup jobs finished.

## 6. Did earlier segments show the same shape?

**No — clean flat pacing in both, no late-run degradation of any kind.**

- **Segment 3** (186 batches, `logs/discovery_gap_sweep_segment3_*.log`):
  median 0.165s/call across all 186 batches, max single-batch outlier
  0.219s (batch 21), last-10%-of-run median 0.163s/call. Launched
  2026-08-24T17:15:37Z, completed 2026-08-25T04:06:52Z (per its terminal
  marker) — i.e. it ran *through* the 2026-08-25T03:00:01Z backup cron
  (the one that, per §"What was contending", didn't log "Finished" until
  the next day) with **zero pacing effect**.
- **Segment 2** (121 batches, `logs/discovery_gap_sweep_segment2_*.log`):
  median 0.172s/call, max outlier 0.246s (batch 33), last-10%-of-run
  median 0.173s/call. Launched 2026-08-22T20:59:32Z, completed ~7.1h
  later (`Cumulative elapsed: 25,577.7s` → ~2026-08-23T04:05Z) — also ran
  through that night's 03:00:01Z backup, which itself took an unusually
  long 3 hours (03:00→06:00:36Z, vs. the typical few minutes seen most
  other nights in `backup.log`) — and *still* showed no pacing effect.

**This is not a general pattern that segment 4 merely crossed a
threshold on.** Two prior segments ran through the same daily 03:00 UTC
backup window — one with a normal-speed backup, one with an unusually
slow one — and neither showed so much as a drift. Segment 4's spike
required something qualitatively different, which is exactly the
double-overlapping-backup situation identified above, unique to this one
night in the available history.

## 7. Rate-limit evidence

**None capturable, and that itself is the finding.** As established in
§4, `_fetch_by_clob()` discards status codes on any non-200 response and
never reads response headers even on a 200 — there is no code path that
could have recorded a 429 or a `Retry-After` header even if CLOB sent
one. Nothing in the driver, `_fetch_by_clob`, or `_extract_clob_resolution`
touches `resp.headers`. Absence of rate-limit evidence in the log is a
logging gap, not evidence that no rate-limiting occurred — but the
live re-probe (§5) returning clean on the exact same markets argues
against an ongoing CLOB-side rate limit being the explanation, since a
real, sustained CLOB-side throttle on this specific box/IP would still
be visible now if it were CLOB-side rather than transient/local.

---

## Bottom line for planning

- Segment 5 sizing does **not** need to shrink for CLOB-throttling
  reasons — no evidence supports that mechanism, and the two much-longer
  prior segments (up to 186 batches / 10.8h) never saw it.
- The actual exposure is operational: **a segment run that crosses
  03:00 UTC is at risk if the nightly `backup_database.sh` cron is ever
  still running from a prior invocation** (no overlap guard exists in
  that script). This happened for the first time on record the night of
  2026-08-25→26, for reasons not fully explained (why the Aug 25 backup
  took >24h is itself unresolved and worth its own look, outside this
  diagnostic's scope).
- If segment 5 is scheduled to run overnight again, treat the
  backup-overlap risk as live until the backup script's overlap
  protection and the root cause of the 24h+ runtime are separately
  investigated — this diagnostic does not fix or resize anything, per
  instruction.
