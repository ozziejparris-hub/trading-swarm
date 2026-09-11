# Session Summary — 2026-09-11 (Server Setup 16)

Documentation only. Every commit hash and figure below was checked
against its source this session. first-repo `main`, trading-swarm
`master`.

---

## HEADLINE — a live credential was found leaking in cleartext, fixed same-day; three more falsifications, all negative

**A Telegram bot token was found in cleartext in `polymarket-observer`'s
journal during the morning progression check.** Root-caused, fixed at
four senders, verified with a real send and a real failure, same day —
see the token-leak section below, stated as a security item.

**Three more causal-vs-compositional tests ran today, following the same
falsification method as the 2026-09-10 copy-trade-decay and own-market-
calibration work.** Skilled-trader presence survived matching but was
killed by its own activity-matched placebo (the fifth conditioning
variable the placebo has now killed). All three ELO-tier variables
(LEGENDARY, NEAR_LEGENDARY, Pool C) failed *before* reaching the
placebo — a stronger negative result. **Nothing found today survives as
a tradeable signal.** What does survive: a size/activity characterisation
that says something real about where skilled traders concentrate, and an
inventory of an unread table that turns out to have two dormant readers,
not zero.

---

## THE ARC IN SEQUENCE

### 1. Start-of-session progression check — read-only, no commit

Section 1 (leftover-process check) came back clean: none of the 5
shells + 1 monitor process reported running at last night's session
close were still present — the last SSH session (pts/0) shows a clean
`exit=0` logout at 21:00 UTC, consistent with detached `bash -c`
wait-loops dying on SIGHUP without `disown`/`setsid`, not with anything
still doing work. All three services active; daily maintenance ran and
completed (33/34 steps OK, the one non-blocking failure being the known
canonical-drift finding); `metric_v2f_oos_result` sha256 unchanged; full
test suite green. **The one substantive finding: the Telegram bot
token appeared in cleartext in `polymarket-observer`'s journal** —
carried into item 2. Delivered as a report in the reply; no artifact
committed (matches the 09-10 convention for a pure information-gathering
task).

### 2. Telegram token cleartext-logging fix — first-repo `dd0fb5e`, trading-swarm `d5fbd0d` (19:35 UTC)

See the dedicated section below.

### 3. Skilled-presence causal-vs-compositional test — first-repo `e3ac29e`, trading-swarm `4372920` (19:57–19:59 UTC)

See "The fifth falsification" below.

### 4. ELO-tier-conditioned calibration + `elo_snapshots` inventory — first-repo `22f435b`, trading-swarm `8c7e146` (20:28–20:30 UTC)

See "The sixth through eighth falsifications" and "`elo_snapshots`
inventory" below.

---

## THE TOKEN LEAK — a security item, not a curiosity

**Root cause: `httpx` (python-telegram-bot's HTTP backend) logs every
request's full URL at INFO, and Telegram's Bot API puts the bot token in
the URL path** (`/bot<TOKEN>/sendMessage`). This is standard, documented
`httpx` behaviour — **not project code building a log message.** It was
invisible until something in the process called
`logging.basicConfig(level=logging.INFO)`, which installs a root
handler and raises every unconfigured logger's effective level —
`"httpx"` included. Three analysis modules
(`analysis/calibration_analysis.py`, `analysis/risk_adjusted_returns.py`,
`analysis/regret_analysis.py`) do exactly this, unconditionally, **at
import time**; `monitoring/main.py` does the same thing unconditionally
at its own top level. In the observer, the daily 01:00 UTC
analysis-scheduler trigger deferred-imports `risk_adjusted_returns` and
`calibration_analysis`, flipping the process into the leaking state once
a day, after which every subsequent Telegram send — including the
routine health heartbeat that actually leaked — writes its full URL,
token included, to stderr, captured by journald.

**The leaked token is the LIVE one.** Confirmed via a boolean-only
comparison (never printed the value) against `.env_trading`: it matches
three separate variable names — `telegram_alerts_token`,
`TELEGRAM_BOT_TOKEN`, and `TELEGRAM_AGENTS_TOKEN`.
`TELEGRAM_ORCHESTRATOR_TOKEN` and `TELEGRAM_METRICS_TOKEN` are different,
unaffected.

**Confirmed present at least since the current observer process
started, 2026-09-09 18:25:58 UTC** (0 restarts since, per
`systemctl show -p ExecMainStartTimestamp`). **Earlier extent
deliberately not chased** — an open-ended `journalctl -g` regex search
across ~3.0 GB of multi-boot journal (back to 2026-07-18) did not
complete inside 90–120 s even scoped to a single unit, and was killed
rather than left running unattended, given this box's documented history
of near-total unresponsiveness from unmonitored processes. Journal
retention has no explicit cap in `journald.conf` (distro defaults apply,
bounded by disk not time).

**STOP condition checked and clear: the token is NOT in either repo's
git history** (`git log --all -S"<token>"`, zero commits in either repo)
**or working tree** (grepped the actual source/doc trees in both repos;
466 GB of first-repo `backups/` — confirmed by directory listing to be
SQLite `.db` snapshots only, not logs — and other large data
directories were *not* exhaustively grepped, for the same box-load
reason, and are flagged as not-determined rather than assumed clean).
File-based logs checked and clean: `logs/monitoring.log` (142 MB,
spanning April 18 to today) and `logs/daily_maintenance.log`, zero
matches in both.

**Fixed at four senders, one line each** —
`logging.getLogger("httpx").setLevel(logging.WARNING)`, placed at the
point each sender constructs its `Bot`: `monitoring/telegram_health_bot.py`
(the observer's sender — the one confirmed leaking),
`monitoring/telegram_bot.py` (currently dead code — `monitor.py`
hardcodes `self.telegram = None` since January — fixed defensively for
if it's ever reactivated), `scripts/check_canonical_definitions.py`, and
`scripts/audit_invariants.py` (both deferred-import senders, not
observed leaking but exposed to the identical mechanism). `httpx`
reports transport errors via raised exceptions, not via this logger, so
nothing about error visibility was touched. **Verified with a real send**
(reproduced the exact leak-triggering root-logger condition, sent a
real, clearly-marked test message through the fixed code — arrived,
captured log buffer empty, token absent) **and a deliberately failed
send** (bad token — still logged `"[TELEGRAM] Error sending message:
Unauthorized"` clearly). New committed regression test,
`tests/test_telegram_httpx_log_redaction.py` (10 checks). Full suite:
26 files, 26 passed both before and after.

**RECORD AS OUTSTANDING:**
- **The fix is inert until the observer restarts** — Python does not
  hot-reload, and the currently-running process (PID unchanged since
  2026-09-09 18:25:58) still has the old module in memory. The observer
  was **not** restarted this session, per scope. Per the task framing
  carried into this session: the observer's last two restarts hung on
  SIGTERM and needed SIGKILL — a plain restart is not necessarily a
  clean operation here; this detail is carried from the task's own
  stated history, not independently re-verified this session.
- **Rotation has not been done.** Rotation is the only action that
  actually closes the exposure window regardless of how far back it
  goes or who may have seen it; purging journalctl removes the
  *evidence* of past exposure, not the exposure itself, and destroys
  ~2 months of unrelated operational history for a housekeeping benefit.
  **The sequence, if rotation is chosen:** update `.env_trading` (all
  three variable names carry the same token) → restart every consumer
  that holds it in memory (`polymarket-observer.service`,
  `polymarket-monitoring.service` even though its sender is currently
  dead code, `trading-swarm.service` for the orchestrator's agents bot)
  → confirm each has picked up the new value → **only then** revoke the
  old token at BotFather. Revoking first breaks every running consumer
  immediately, since each still holds the old token in memory until it
  restarts. **Rotation is Oscar's call — not performed.**
- **Three more files use `python-telegram-bot`/`httpx` and were not
  fixed** — flagged, not live: `monitoring/telegram_elo_bot.py` (dead
  code, not imported by any live entrypoint), `scripts/get_telegram_chat_id.py`
  (manual one-off setup utility, not part of any cron/systemd path),
  `data/characterizations/sweep_common/sweep_terminal_signal.py` (dead
  code from the sweep effort formally stopped 2026-09-04).

Full writeup: `2026-09-11-telegram-token-log-leak.md`.

---

## THE FIFTH FALSIFICATION — skilled-trader presence (compositional, not causal)

`scripts/skilled_presence_causal_test.py`, first-repo `e3ac29e`,
decision doc `2026-09-11-skilled-presence-causal-vs-compositional.md`
(trading-swarm `4372920`). Tests the 2026-09-10 own-market-calibration
Part 3 live thread: markets where a PIT-legally-identified
directionally-skilled trader took a position carry a higher
recalibration slope than markets where none did, at every horizon, but
present and absent CIs overlap at every horizon, and skilled-present
markets are the 57.7% majority.

- **Part 1 — the two populations differ grossly on size/activity.**
  Skilled-present markets carry a **4.5×–18.5×** higher median on
  n_trades (18 vs. 3, 6×), n_distinct_traders (9 vs. 2, 4.5×), volume
  ($1,387 vs. $75, 18.5×), and lifetime (351 h vs. 34 h, 10×). *(The
  task prompt for this summary characterised this range as "6–18×" —
  the actual per-committed-doc range is 4.5×–18.5×, since
  n_distinct_traders's ratio is 4.5×, below 6×. Flagged per the
  discrepancy-reporting instruction, not silently reconciled.)* Base
  rate gap +3.97pp [+2.16, +5.78] — real but under the 10pp confound
  threshold, so the test proceeded.
- **Part 2 — matched comparison.** Purpose-built market-level matching
  (not `match_control()` — that function matches traders on activity,
  not markets on size/composition; a dedicated `match_markets()` was
  built, justified in-script). Matched on log(1+n_trades),
  log(1+n_distinct_traders), log(1+volume), log(1+lifetime_hours),
  within category, caliper 1.0. **2,743/4,134 (66%) absent markets
  matched**, balance closed to near-parity (lifetime 445.5 vs. 446.1 h
  post-match). **Direction survived at 6/6 horizons** — not a pure
  size/activity/category composition artifact.
- **Part 3 — the placebo.** `match_control()` (a legitimate reuse here
  — this genuinely is the trader-activity-matching problem it was built
  for) drew a same-size (1,494), activity-matched, **not**
  skill-selected trader set from the PIT-legal classifiable pool.
  **The placebo reproduced the elevation at 4/6 horizons, at
  near-identical magnitude to the real numbers**: matched-present
  **1.369** [1.190, 1.609] vs. placebo-present **1.352** [1.218, 1.530]
  at ~0.5h; matched-absent 1.200 vs. placebo-absent 1.220. **Stop
  condition tripped — presence is a proxy for ACTIVITY, not skill.**
  Part 4 (edge-units vs. cost floors) was not run — nothing skill-
  specific survived to measure.

A genuine methodology bug was found and fixed while building Part 3 —
see "The recurring defect class" below.

---

## THE SIXTH THROUGH EIGHTH FALSIFICATIONS — ELO tier, all three arms negative, none reached the placebo

`scripts/elo_tier_causal_test.py`, first-repo `22f435b`, decision doc
`2026-09-11-elo-tier-causal-test-and-elo-snapshots-inventory.md`
(trading-swarm `8c7e146`). Same pipeline, reused unchanged, conditioned
on current ELO tier instead of the PIT-legal skill classification.

**Framing, stated explicitly in the source doc and repeated here: `geo_elo`
is condemned for skill-ranking. ELO tier is used here strictly as a
conditioning variable on mispricing — never as a skill measure, never
as a selector.**

- **LEGENDARY (n=9 traders, 697 markets present):** base rate gap
  +4.15pp, under threshold — proceeded to Part 2. **Direction REVERSED
  at 5/6 horizons under matching** (matched-absent slope exceeded
  matched-present at every horizon except ~3d). **Stopped at Part 2** —
  effect disappears/reverses under matching, a complete negative
  finding. None of the six horizons was market-count-thin enough to
  mark UNCOMPUTABLE (n=223–648 per matched arm), but CIs are
  correspondingly wide.
- **NEAR_LEGENDARY (n=26, 921 markets present)** — the one other clean
  tier rung in `derive_tier()` (1,800 ≤ geo_elo_active < 2,175, clean
  pool member), chosen because it is an actual boundary in the
  canonical ladder, not an invented one. Base rate gap +0.19pp,
  essentially zero. **Direction preserved at only 3/6 horizons — not a
  majority.** Stopped at Part 2.
- **Pool C (n=4,483, 8,777 markets present):** base rate gap
  **+16.62pp [+14.24, +19.00]** — far past the 10pp confound threshold.
  **Stopped at Part 1**, before matching was even attempted.
  Absent-of-Pool-C markets have a **~3-minute median lifetime** —
  essentially untraded, not a comparable population; Pool C's own gate
  (≥10 resolved geo trades, non-NULL directionality score) means "no
  Pool C member ever traded here" selects almost entirely for markets
  nobody minimally-qualified ever engaged with.

**None of the three ELO arms reached the placebo stage.** This is a
**stronger negative** than skilled-presence, which at least survived
Parts 1 and 2 before the placebo killed it at Part 3 — here, LEGENDARY
and NEAR_LEGENDARY are killed by matching itself (not composition-proof,
reverses/collapses), and Pool C is killed by an even earlier,
un-matchable base-rate confound.

---

## THE ASSET — where skilled traders concentrate, recorded as a finding, not just a covariate

**Part 1's characterisation is not a null.** Skilled-present markets
carry 4.5×–18.5× the median trades, distinct traders, volume, and
lifetime of skilled-absent markets. **Skilled traders concentrate in
big, long-lived, liquid markets** — and per the 2026-09-10 own-market-
calibration Part 1b/2, this is exactly where the calibration deviation
is **smallest** (the solid deviations live in the price-extreme
deciles, not the size-driven middle) and where **~81% of trader entry
volume already sits**. Recorded as a finding about where the
competition already is — traders are not distributed at random across
market size, they are concentrated exactly where the market is most
efficient and most contested — not merely as a matching covariate that
happened to explain away today's slope gap.

---

## THE RECURRING DEFECT CLASS — a pattern, not a one-off, four instances in a week

**The same mechanism, four times: a name that reads as authoritative
over a population that was defined for a different purpose, and the
obvious reuse turning out to be silently wrong.**

1. **The copy-decay harness's price substitution** (2026-09-10): "the
   next trade in that market at or after `entry+N`, from any trader"
   never addressed *outcome*. `trades.price` is `P(that trade's own
   outcome)`; an opposite-outcome trade contributes `≈1−p` where `p`
   belongs. **37.58% of N=15 min substitutions were on the opposite
   outcome** (13,330 of 35,468) — a name (`price`) that reads as
   unambiguous over a quantity that is conditional on something the
   query never filtered.
2. **`test_failure_age_tracking.py:307–313`** — an earlier version
   hard-asserted the committed register `== {"entries": {}}`, and broke
   the moment the first real entry landed, because the register is a
   *live, human-maintained file that gains entries over time*, not a
   frozen fixture the way the test's own literal treated it.
3. **`test_backtest_window_population.py`** — hardcoded exact counts
   (4,690 / 4,636 / etc.) against `backtest_window_sql()`, which is a
   **live** query (`tape_end` grows as new trades accrue — measured
   4,690→4,702→4,712 *within a single day*). The population moving was
   not the bug; asserting a frozen number against a query defined to
   move was.
4. **Today: `build_presplit_cohort()`'s `elig_pool` is NOT the
   PIT-legal classifiable pool.** Found while constructing Part 3's
   placebo for the skilled-presence test. `elig_pool`
   (`n_pairs >= M_CHOSEN`, from `compute_cap5_metric`'s EB-shrinkage
   pair construction) has **3,037** traders; the actual pool that
   produced the 1,494 skilled traders
   (`directional_skill_pit_legal_pool.py`'s own `n_positions >=
   M_CHOSEN` on the `tape_end<T_SPLIT` canonical set) has **5,917**.
   **536 of the 1,494 skilled traders were not even members of the
   wrong pool.** Fixed by rebuilding the pool via the correct loaders
   directly, matching the construction that actually produced the
   skilled cohort.

**Common mechanism, stated once for all four:** in every case a
downstream consumer reused something that *sounded* like the right
population or quantity — "the next trade's price," an assertion against
"the register," a count against "the backtest population," an
"eligible pool" — without checking that the thing so named was built
for *this* purpose rather than a structurally similar but different
one. The fix in every case was the same shape too: go back to the
actual defining query/construction and verify empirically, rather than
trust the name.

---

## `elo_snapshots` INVENTORY — the one unexploited asset found

**232,536 rows, 70 distinct dates (2026-06-11 → 2026-09-11), 6,149
distinct traders, 3,547 with ≥30 snapshots** (of a max possible 70).
**Coverage is NOT continuous — 7 gaps**, the largest **15 days
(2026-07-24 → 08-08)**, which encompasses both known outage dates named
in the task (07-26, 08-02) and considerably more (three weeks with only
the endpoints recorded, not two isolated missed days).

**The table's entire population is, by construction, the historical
record of Pool C membership over time** — `snapshot_elo_scores.py`
snapshots only `WHERE geo_accuracy_pool = 1`. This explains
**`bot_type` being 100% NULL across all 232,536 rows**: Pool C's own
gate requires `bot_type IS NULL`, so a bot-flagged trader can never be
in Pool C, so can never appear here — a consequence of the population
definition, not a writer gap (the live `traders` table does have 685
non-NULL `bot_type` rows, confirming the column itself works elsewhere).
`comprehensive_elo` is 0.32% (747/232,536) at the exact schema default
1500.0 — the rest are not obviously uncomputed by that test.

**Two dormant, non-scheduled scripts genuinely read the table** —
`scripts/verify_dilution_guard.py` and `scripts/validate_pit_geo_elo.py`
— via real `SELECT` queries. Neither is wired into `daily_maintenance.py`
or found in crontab. **Nothing live reads it** — the task's framing was
correct in spirit — but it is not literally true that nothing reads it
at all.

All observed `tier` values (`QUALIFIED, DEVELOPING, ELITE,
NEAR_LEGENDARY, LEGENDARY`) match the current `derive_tier()` scheme
exactly. **No retired or drifted tier strings found.**

Full writeup: `2026-09-11-elo-tier-causal-test-and-elo-snapshots-inventory.md`.

---

## WHERE THE ELO SYSTEM STANDS, FOR THE RECORD

**`geo_elo` was condemned for skill-ranking in August**
(`MASTER_HANDOVER_2026-08-15` §1: five independent defects — a sign
error, an improper scoring rule that pays a zero-skill favourite-No
bettor for free, 35.7% sell contamination, 52.3% double-counting, and
uncalibrated parameters including tier thresholds copied from a
discredited prior system — "the response was a rebuild, not a patch").
**`comprehensive_elo` was deprecated with its behavioural modifiers
inert since `W_BEH=0.0`, set 2026-07-12** on a well-powered null
(R²=0.00018, n=21,218). **And as of today, the tiers do not work as a
mispricing MARKER either** — none of LEGENDARY, NEAR_LEGENDARY, or Pool
C survived matching, let alone reached a placebo test.

**The honest synthesis, stated plainly: skilled traders exist and are
identifiable** — directional persistence 37.0% vs. 18.6% at the
2026-09-06 harness calibration, a real, replicated effect — **but what
makes them profitable is execution, which a follower cannot inherit.**
The copy-decay result (2026-09-10, `+0.01233` at the 15-minute cadence,
CI `[-0.00186, +0.02410]`, COLLAPSES-BEFORE-CADENCE) already established
there is nothing to inherit from a trader's entry. Today's results
close the other door: presence doesn't mark a mispriced market either
— it's a proxy for how much anyone active trades there, and the ELO
tiers that might have offered a cheaper, always-current substitute for
the frozen PIT-legal skill classification don't survive their own
matched comparison. **"Identify the best and copy them" fails on the
second clause (copy them), not the first (identify the best).** Skill
is real and measurable; it is not transferable through observation of
presence or entry price alone.

---

## OSCAR'S STATED DIRECTION FOR THE NEXT PHASE

*Recorded as stated, not endorsed here — carried forward from
instruction, not independently arrived at this session.*

**The focus is now the full-context heatmap** — a systematic sweep of
everything built over the last 10–12 months, cross-referenced against
current external research, looking for combinations and applications
not yet tried. **Expected to take weeks. Leave no rock unturned.** This
is explicitly framed as a **different kind of work** from the
test-and-falsify cycle that has run for the past several sessions
(copy-decay, own-market calibration, skilled-presence, ELO tiers) and
**should be scoped as its own arc**, not folded into the next quick
falsification test.

---

## OPEN THREADS CARRIED FORWARD

1. **Observer restart.** The token-logging fix is committed but inert
   until `polymarket-observer.service` restarts. Not restarted this
   session, per scope. Its last two restarts reportedly hung on SIGTERM
   and needed SIGKILL (per the task's own stated history, not
   independently re-verified this session) — worth planning around when
   a restart is scheduled.
2. **Token rotation — undecided, Oscar's call.** See the token-leak
   section for the required sequence if chosen (update `.env_trading` →
   restart every consumer → confirm → only then revoke at BotFather).
3. **Three dormant files use the same `httpx`-logging library and were
   not fixed** — `monitoring/telegram_elo_bot.py`,
   `scripts/get_telegram_chat_id.py`,
   `data/characterizations/sweep_common/sweep_terminal_signal.py`.
   Flagged as latent, not live.
4. **Geo pending backlog, day 1 of the new steady state: 122** —
   inside the predicted 100–600 range. The `background_backfill`
   re-ingestion pattern recurs, but at **79 rows**, not the ~210 flagged
   as a possible sign the ingest fix wasn't fully closed — the fix
   appears to have reduced the pattern, not eliminated it. One more
   day's reading needed before drawing a trend.
5. **Accumulating untracked files** — 16 in first-repo
   (`data/characterizations/`, `data/checkpoints/`), 46 in trading-swarm
   (all `brain/agent-outputs/`), roughly a month's worth, neither
   committed nor gitignored.
6. **CLAUDE.md's documented DB size (~1.6 GB, April 2026) vs. the
   actual 20.7 GB (now 20 GB rounded, still growing)** — the
   documentation is stale by roughly 13×; not corrected this session
   (out of scope for a documentation-only task; flagged for whoever
   next touches CLAUDE.md).
7. **The relevance-classifier gate adjudication** — still outstanding
   as of the 09-10 summary (2026-09-03 gate: precision PASS, recall
   FAIL 90.35%; 09-04 diagnostic indicated §3.11(a) abandon; Oscar's
   formal call pending). Not touched this session; carried forward
   unchanged.

---

*Generated 2026-09-11 (documentation only; no computation). Sources:
first-repo commits `dd0fb5e`, `e3ac29e`, `22f435b`; trading-swarm
commits `d5fbd0d`, `4372920`, `8c7e146`; artifacts
`data/characterizations/skilled_presence_causal_test_20260911T195254Z.json`,
`data/characterizations/elo_tier_causal_test_20260911T202445Z.json`;
decision docs `2026-09-11-telegram-token-log-leak.md`,
`2026-09-11-skilled-presence-causal-vs-compositional.md`,
`2026-09-11-elo-tier-causal-test-and-elo-snapshots-inventory.md`.
`MASTER_HANDOVER_2026-09-06.md` remains the entry point and is not
superseded by this summary.*
