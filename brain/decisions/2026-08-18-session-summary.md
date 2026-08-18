# Session Summary — 2026-08-18

## THEME

Long session. Opened with a combined system-state census and daily progress check, then
followed the findings wherever they led rather than working a pre-set list. Closed the
population-conditioning question that had been open since 2026-08-16 — both components
of v2f's 254-market shortfall from canonical are now characterised, not just named — and
corrected a wrong figure in the master handover. Six investigations and one
documentation correction. Nothing in the codebase was repaired.

## THREE REUSABLE LESSONS (record them)

**A prompt's own premises are claims, not givens.** Four separate premises written into
today's prompts by chat-Claude proved wrong on verification: Writer A's 2026-07-19
canonical run, carried for a month as "never confirmed," actually happened (a
2026-07-21 session summary already said so — the 07-18 handover's "verify this first"
had simply never been checked); `is_taker`/`transaction_hash`, carried as "unread by
anything," now has three readers; the 88→101→103 pending-resolution markets, framed as
suggesting "active production" i.e. recent onset, actually span mid-2024 to March
2026 — broad historical residue, continuously discovered, not a recent problem; and the
v2f verdict field, flagged as printing SUPPORTED when it should print NULL, turned out
not to exist on the table being read — the real field, on a different table, has always
said NULL. The standing instruction to treat prompt claims as hypotheses was written
this morning and earned its place by the afternoon, catching errors in both directions —
real bugs and false alarms alike.

**The same bound can be reached for different reasons, and the reason determines
durability.** Both population-shortfall components came back structurally unable to
touch the measured out-of-sample edge, but for unrelated reasons: the 88/103
`trade_result='pending'` markets are bounded by a *size* property (median 1 trade,
below the cohort's M≥10 floor); the orphan-SELL markets are bounded by a *temporal*
property of the population definition itself (100% pre-split by construction, so
post-split dropped-market count is always zero). Had either bound been assumed from the
other's result, the finding would have been right by accident and would not have
survived the counts changing, which they did — 88→103 climbing, 166→161 falling, in
opposite directions, over the same two days.

**Characterisation is not cost-free.** Seven investigations today, one repair-equivalent
action (the handover correction). Each characterisation was individually justified and
they collectively closed a real question — but the project has now spent four
consecutive sessions (08-15 through 08-18) establishing state rather than changing it.
Worth naming plainly rather than letting it pass unremarked.

## WHAT WAS ACHIEVED

1. **System-state census (20 open items audited).** `13 VERIFIED-OPEN, 4 VERIFIED-CLOSED,
   3 CHANGED, 3 UNVERIFIABLE-HERE.` Two of the prompt's own premises were wrong and were
   corrected by verification, not restated: Writer A's 07-19 canonical run DID happen,
   and `is_taker`/`transaction_hash` is no longer unread. The 88 pending-resolution
   markets had grown to 101 at the time of the census (103 by the time the dedicated
   characterisation ran ~27 minutes later).
   (`2026-08-18-system-state-census.md`, commit `c1ba9fb`)

2. **Today's outage — 93 minutes, 14:45:50→16:19:04 UTC.** Unclean prior boot
   (fsck/journal recovery, no shutdown command logged) — same signature as the
   2026-07-24 event. Second crash in a month, neither gracefully shut down. Today's
   `daily_maintenance.py` ran at 09:21, hours before the outage, so its clean 31/33
   result does not cover the rest of the day; the census fingerprint was taken
   post-recovery (~18:01) and is current. No market resolved in the window. Nothing
   alerted, confirmed empirically, not assumed. New finding that partially revises the
   08-17 SELECTION RISK framing: 5 of 7 affected traders matched the known
   "already-known traders get no backfill" mechanism, but 2 already-known traders WERE
   recovered anyway, via the live monitor's ordinary cursor catchup fetching the 500
   most recent trades at boot. Recovery is not binary by trader class — it is bounded by
   gap length against a 500-trade catchup window. That threshold is unmeasured. 93
   minutes at current live rates (~81 trades/24h) fits comfortably inside it; 13.5 days
   does not.
   (`2026-08-18-outage-scope.md`, commit `6f33220`)

3. **Pending-resolution component (88 → 101 → 103): PERSISTENT-BOUNDED.** Permanent —
   nothing ever clears `trade_result` — but zero overlap with the 295-trader cohort
   superset. The bound is structural, not coincidental: affected markets have median 1
   trade (baseline 7) and cohort membership requires M≥10, so they cannot reach the
   cohort by construction. Mechanism: `markets.resolved` has 10 write sites across 6
   files, including a Sunday cron; `trades.trade_result` has exactly one writer
   (`TradeEvaluator`), invoked only by two scripts present in neither crontab nor
   `daily_maintenance.py`. One field updates on a schedule, the other only when someone
   remembers to run a script. Affected markets span mid-2024 to March 2026 — historical
   residue continuously discovered, not recent onset.
   (`2026-08-18-pending-resolution-inconsistency.md`, commit `aa6eb28`; script
   `scripts/characterize_pending_resolution_inconsistency.py`, commit `31d65ac`)

4. **No-FIFO-close component (166 → 161): TOUCHING, then scoped.** Single, exhaustive
   failure mode — every affected group is an orphan SELL with no matching BUY anywhere
   in `trades`, silently dropped by `PositionTracker._match_group` at
   `position_tracker.py:330`. Independent of the `trade_result` mechanism above — these
   trades already have `trade_result` correctly populated; the blocker is that FIFO
   never created a position row to join through. Profile: median 1 trade (baseline 7),
   81.4% Elections (baseline 64.6%), 83.2% resolving No (baseline 71.0%) — a real,
   tested selection effect, not eyeballed. Direction of bias is undeterminable, not
   merely uncomputed: no entry price exists anywhere in the DB for an orphan SELL.
   (`2026-08-18-no-fifo-close-markets.md`, commit `969d9a1`; script
   `scripts/characterize_no_fifo_close_markets.py`, commit `3fcb083`)

5. **Orphan-SELL scope against the true result-of-record populations: MATERIAL-OPEN,
   narrowly.** The real intersection is smaller than the 295-trader superset proxy
   suggested: 4 true presplit-cohort members, **3 true OOS survivors** (not 7), 6
   placebo-pool members, 5 placebo survivors. The structural finding: the orphan-SELL
   population is 100% pre-split by construction — the population definition itself is
   `tape_end < T_split` — so every affected trader's post-split dropped-market count is
   exactly zero, verified directly. This mechanism can affect *who qualifies*; it cannot
   touch the *measured OOS edge*. MATERIAL-OPEN rather than BOUNDED because two traders
   (`0x0a7aaf83...`, `0x2c719eda...`) would cross the M≥10 threshold if their dropped
   markets counted, and whether they would actually have qualified is unknowable without
   entry prices for those markets. The tempting inference — that their current negative
   visible edge means they wouldn't have qualified anyway — was explicitly named and
   declined: visible markets are not a random sample of their record, they're the subset
   where a BUY happened to exist. Placebo exposure 4.05% vs. cohort 2.70%, reported as a
   null at a sample size too small to call direction, not upgraded to "no differential."
   Zero overlap with any characterised outage window or the O-37 quarantine.
   (`2026-08-18-orphan-sell-scope.md`, commit `29d10e4`; script
   `scripts/characterize_orphan_sell_scope.py`, commit `5141fc1`)

6. **v2f verdict-field check: NO DISCREPANCY.** A false alarm raised incidentally during
   item 5 above, walked back here. `metric_v2f_oos_result` has no verdict column at all;
   the actual `thesis_verdict` string lives in `metric_v2f_findings.objective2` and
   reads NULL — matching the code logic replayed line by line, and matching every
   narrative document including the 08-15 handover. Nothing downstream reads the field.
   (`2026-08-18-v2f-verdict-field.md`, commit `cd3e008`)

7. **LEGENDARY overlap recompute and handover correction.** The wrong figure reproduces
   exactly (15/81, 18.5%) — it was the wrong denominator (a hardcoded, non-canonical
   `geo_elo >= 2175` predicate), not data drift. Correct figure:
   **3/10 (30.0%), as-of 2026-08-18T19:25:10Z.** Decomposition: the `geo_elo_active`
   time-decay condition alone disqualifies 69/81 (85.2%) of the inflated set;
   `geo_accuracy_pool` removes 21, `research_excluded` removes 4, `bot_type` removes 1;
   20 fail more than one condition. The handover's claim survives but was overstated by
   roughly 1.6x — 70% of the canonical LEGENDARY tier is still absent from the new
   cohort, not 81.5%. Handover amended: corrected figure with a mandatory as-of
   timestamp and an n=10 instability warning, the superseded 15/81 figure retained and
   marked rather than silently overwritten, §6.1's cutover anchor updated to the
   corrected n=10 set.
   (`2026-08-18-legendary-overlap-recompute.md`, commit `dd2261a`; script
   `scripts/characterize_legendary_overlap_recompute.py`, commit `fd9e329`; handover
   amendment, commit `c3b0ff6`)

All seven items above, plus this summary, are committed and pushed as of this session
(`c1ba9fb`, `6f33220`, `aa6eb28`, `31d65ac`, `969d9a1`, `3fcb083`, `29d10e4`, `5141fc1`,
`cd3e008`, `dd2261a`, `fd9e329`, `c3b0ff6`).

## STATE FOR NEXT SESSION

The order below is **proposed, not decided.** Split by whether deferral makes the item
worse or unrecoverable, versus merely leaving it open.

**TIME-CONSTRAINED:**

a. **Ingestion detection.** Oscar has ruled out a box-down alert as unnecessary — he
   restarts the box himself and knows when it happens. The ingestion-*stall* case
   survives that objection: the 08-11 gap had the box up, maintenance running, and
   trades quietly missing, found only by luck. Now sharpened by today's item 2: loss is
   non-linear in gap length, self-healing below some unmeasured boundary and permanent
   above it. Still mandatory before any passive run.
b. **The recovery threshold itself** — where the 500-trade catchup window stops covering
   a gap. Unmeasured, and it determines the cost of every future outage.
c. **B4 order-book capture and `elo_snapshots`** — append-only, no backfill path. Every
   day of downtime is permanently lost. 14 days already gone to the July outage.
d. **Handover §6.8 is now stale in a way that understates our knowledge.** It still
   describes the 254-market bypass as "of unknown direction and magnitude" and lists the
   88 as open. Both components are now characterised and bounded (items 3–5 above).
   Should be amended from this summary early next session.

**OPEN, NOT TIME-CONSTRAINED:**

e. **Pin-mechanism design for Objective 2 cohort persistence.** Three attributions were
   blocked today by absent membership snapshots (166→161 unattributable, the census
   figures, the 08-16 cohort). The schema pattern exists and is unused. This is a build,
   not a characterisation, and needs a pre-registration.
f. **Track 2 CI power diagnostic** — still not committed. Its A3 stop condition still
   needs amending: a reproduction miss means substrate drift, not a broken harness.
g. **The two unresolvable orphan-SELL traders** (item 5) — settleable only by
   re-ingesting missing BUYs from the API; reachability for old markets unverified.
h. **`position_tracker.py:330`'s silent drop — deliberately NOT fixed.** It cannot touch
   the measured edge, so fixing it changes historical qualification for no current gain,
   and nothing has established what else consumes position rows. Needs a
   pre-registration before any change.
i. **`resolution_date` mutability with no audit trail; T2f test partition redesign; the
   six hardcoded `geo_elo` sites** (repointing them touches `eaeabbc`, the pinned
   `generator_commit` — a judgement about what the pin is for, and Oscar's call).
j. **Carried from 08-15, unchanged:** the cutover decision (now anchored on the
   corrected n=10 set per item 7); the category-split cost floor; the consensus
   question; the `comprehensive_elo` sign error; elections calibration re-run (O-40);
   O-38; O-18.

## BIG PICTURE

The thesis result (+0.0316, CI [−0.0088, +0.0710], NULL but directionally positive and
underpowered) is unchanged and has now survived four independent challenges:
`comprehensive_elo` contamination (NO CONTACT, 08-16), substrate drift (UNREPRODUCIBLE
procedurally, but the finding did not change character, 08-16), and both
population-shortfall components characterised today (neither can touch the measured
edge). The metric's population conditioning is now characterised rather than unknown.
What remains unresolved is what was unresolved on 08-15: the result is underpowered, and
the honest resolution is more out-of-sample observations, not more analyses of these.
Phase 2 remains the primary experiment, and whether it can resolve the thesis in finite
time (Track 2) is still unanswered.

**Plain statement, not to be softened in a future read of this file:** one documentation
correction was made this session (the handover's LEGENDARY-overlap figure). Nothing in
the codebase was repaired. Seven investigations produced characterisations, not fixes.
