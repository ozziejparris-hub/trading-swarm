# 2026-08-22 — Correction to the overnight incident report (696b49d)

**Not damage. A factual correction to how far yesterday's partial
`daily_maintenance.py` run actually got**, found during today's
session-start progress check. The incident report's verdict (NO DAMAGE,
CAUSE IDENTIFIED — Mullvad/Tailscale network outage, widened backfill
limit cleared) **stands unchanged**. Only the "where did it stall" claim
is wrong and is corrected here.

## What the incident report said

696b49d states the run "stalled at step 5" (Resolution sweep) and that
this step made zero writes for its entire runtime, based on a log excerpt
that appeared to show `resolution_sweep.py`'s own per-trader trade-fetch
loop hammering `data-api.polymarket.com` and failing on DNS.

## What actually happened [V]

That per-trader `[N/3737] processed (running: fetched=X matched=Y)` log
line does **not** belong to `resolution_sweep.py`. Grepping
`scripts/*.py` for its exact format string
(`processed (running: fetched=`) finds it in exactly one file:
**`backfill_transaction_hashes.py`** — step 12 of 33, not step 5.

Reconstructing forward from `logs/daily_maintenance.log` (using each
child script's own distinctive print signature, since the *parent*
process's own step-header prints were lost — see mechanism below), steps
1 through 11 of yesterday's (2026-08-22 06:00:01) run **completed, in
full**, in order:

| # | Step | Result |
|---|---|---|
| 1 | Update research exclusions | OK |
| 2 | Sync trade categories | OK — updated=3, gained_geo=3, lost_geo=0 |
| 3 | Detect ARB_BOT patterns | OK — 0 wallets flagged |
| 4 | Promote high-P&L traders | OK — 245 promoted |
| 5 | **Resolution sweep** | **OK, completed with real results** — 57 markets resolved (last 7d), 77 qualifying traders, 6 promoted, 71 already flagged |
| 6 | Reconcile geo resolved counts [pre-audit] | OK — `Traders whose geo_resolved_trades_count will change: 0`; Pool C 3660→3660 (no change), LEGENDARY 10→10 (no change) |
| 7 | Integrity audit (pre-ELO gate) | OK, exit 0 — 26 invariants checked: 16 PASS, 4 REGRESSION, **0 CRITICAL**, 6 OBSERVE. Did not block. |
| 8 | Canonical definitions drift | Ran, non-blocking — 7 violations detected (all hardcoded `geo_elo >= 2175` thresholds across `trader_skill_metric_v2*.py` + one characterize script; same recurring code-smell this step always flags) |
| 9 | Update geo ELO scores | OK — 5 traders updated |
| 10 | Score insider signals | OK — 7 signals, 4 correct/3 wrong, 57.1% accuracy |
| 11 | Score STR-003 signals | OK — 8 signals, 6/8 resolved, 50% accuracy, finding `2026-08-22-STR003-ACC-006` written |
| **12** | **Backfill transaction hashes** | **STALLED HERE.** `[BACKFILL] tier=pool_c dry_run=False — 3737 traders to process`, then every fetch failed on the same DNS `NameResolutionError` the incident report already documented. Reached `[590/3737]` before the log stops (file mtime 09:22, ~7 min before the 09:29:56 reboot). |
| 13–33 | (Label maker/taker roles, Verify market titles, ... through WAL checkpoint / Backfill market dates / Hydrate stub markets) | **Never ran.** |

**Why the original report missed this:** `daily_maintenance.py`'s own
`run_step()` prints `\n--- Step: {label} ---` via a buffered `print()`
before invoking each child script as a subprocess with inherited stdout.
When the log is redirected to a file (as cron does here), the parent's
own buffered output sits unflushed while each child subprocess's stdout
writes straight through. The parent process was killed by the 09:29:56
reboot before its buffer was flushed, so **none** of its own
`--- Step: label ---` headers survived to disk for yesterday's run — only
the child scripts' own (unbuffered/directly-written) output did. A grep
for the parent's own header strings therefore found nothing past the
start marker, which is what produced the "stalled at step 5" reading.
Reconstructing from each child script's own distinctive print signature
(confirmed by grepping each candidate script for the exact string) gives
the true picture above.

## Does this change the verdict?

No. It strengthens it:

- **Resolution sweep (step 5) is not implicated at all** — it completed
  normally, with real (non-zero) results, well before the network outage
  degraded enough to break DNS resolution for API calls. The actual
  outage-affected step is `backfill_transaction_hashes.py` (step 12),
  which is unrelated to yesterday's shipped code changes (it is not one
  of steps 1/2/3 from the discovery-gap-closure arc).
- **The widened `--limit 35000` "Backfill market dates" step is even
  further from having run than previously stated** — it is step 32 of
  33, twenty steps past where the run actually stalled (step 12), not
  five. It remains untouched by this incident.
- **No new inconsistent state.** The one step whose completion could in
  principle need a downstream reconcile — "Sync trade categories"
  (step 2, `gained_geo=3`) — was in fact followed by "Reconcile geo
  resolved counts [pre-audit]" (step 6), which ran and explicitly
  reported zero traders needed a `geo_resolved_trades_count` change. No
  drift was left uncorrected. "Reconcile geo resolved counts [post-eval]"
  (the second reconcile) never ran, but neither did anything upstream of
  it that would have created drift for it to catch (`Evaluate new trader
  results`, step ~21, never ran either). Every step that *did* complete
  is either self-contained or was itself the thing that would have
  reconciled it.

## What is genuinely incomplete (not damage, just undone)

Steps 12 (partially) through 33 did not run to completion yesterday:
`backfill_transaction_hashes.py` (partial, 590/3737), maker/taker
labeling, market-title verification, market-category backfill,
`fast_resolution_check.py`, the STR-002 pipeline, LEGENDARY market
resolution, `evaluate_new_trader_results.py`, the post-eval reconcile,
`requeue_resolved_market_traders.py`, `apply_full_elo_modifiers.py`,
`resync_position_counts.py`, counter-signal detection, ELO/order-book
snapshots, integration-health write, the test suite, the WAL checkpoint,
**the widened Backfill market dates step**, and Hydrate stub markets.
None of this is inconsistent state — it is simply undone work, waiting
for the next scheduled run (2026-08-23 06:00:01 UTC; no run has happened
since the 09:29:56 reboot, and no catch-up/anacron mechanism was found).

Commit and push.
