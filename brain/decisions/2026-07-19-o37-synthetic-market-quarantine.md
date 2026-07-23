# O-37 · Synthetic-market quarantine — characterization, proof, and remediation

**Status: RESOLVED 2026-07-19.** Closes the O-37 ledger item (`2026-06-29-overhang-ledger.md`, "Synthetic/duplicated rows in `trades` table — 202 markets... scope/cause/impact unknown"). Read-only-first discipline throughout, matching the O-13/O-16 precedent — four full characterization/proof passes before any write, dry-run before persist, STOP-and-surface twice on self-caught methodology errors before commit.

First-repo commit: `5777e45ae580cf18df8ff950e0796d095435d5fd` (`scripts/quarantine_o37_synthetic_markets.py`).

---

## 1. Detection — dual-signal convergence

Two independent signals converged on the same population:
- **Stats heuristic** (the original O-37 trigger, B2 probe session 2026-07-17): distinct `market_id`s sharing byte-identical `(trade_count, avg_shares)`; implausible per-market stats (`trade_count>20000` or `avg_shares>5000`). Anchor: `0x73570416...` (Iran market), 619,473 trades at 222,702-share average.
- **Token-backfill failures** (2026-07-18 session): open geo/elec markets with DB trade history but no resolvable live CLOB/Gamma token. Anchor: `0x08e61703...` ("USA ceasefire agreement before December 2025?"), ~15,028 trades, all `transaction_hash` NULL.

## 2. Proof phase — the detector had false positives in BOTH directions

Reproducing the naive detector (no live token AND zero real `transaction_hash` across all trades, geo/elec) against the live population gave **1,614 markets, 971,886 trades**. That number did not survive scrutiny:

- **Live-API ground truth found the low-volume tail was mostly noise, not fabrication.** Of a 10-market low-volume sample, **10/10 turned out to be real markets** we simply hadn't backfilled a token for — a genuine false-positive direction the naive detector couldn't see. A100 real markets in this DB legitimately have zero `transaction_hash` coverage at low volume (14.9% of confirmed-real low-volume markets show this pattern) — `transaction_hash` is only ~20% populated DB-wide, so "zero txhash" alone is weak evidence at low trade counts. Refined the high-confidence core to `trade_count>1000 OR duplicate-title-cluster` — **88 markets, 99.3% of the flagged trade volume** from 5.5% of the flagged market count.
- **The "high-confidence" mechanical rule ALSO had false positives, the other direction.** Full individual live-verification of all 88 (not sampling) found **4 confirmed real**: two instances each of "Will Trump say 'Peanut' this week?" and "Will Trump's remarks not air?" — legitimate recurring weekly Polymarket market formats that get fresh `market_id`s per instance, incorrectly swept in by the duplicate-title rule.

**Final scope: 1,614 → 84 markets, 965,542 trades — every single one individually live-verified absent from Polymarket via the Gamma/CLOB API (0% false positives on the final set).**

## 3. Blast radius (proven, not estimated)

- **953 traders** ever traded in the 84 markets.
- **0 cohort** (`geo_elo_active>=1800 AND geo_accuracy_pool=1 AND research_excluded=0 AND bot_type IS NULL`), **0 Pool-C** exposure — checked at every stage of this arc, reconfirmed after the write.
- A separate rough "31/43 cohort exposure" alarm from an earlier pass in this same investigation also did not survive ground truth: 4/5 spot-checked "cohort-touched" markets turned out to be real (false positives from the broader unverified detector), leaving at most 1 cohort-adjacent trader with 15 confirmed-synthetic trades out of 1,144 real ones (1.3%) — immaterial, and that trader's `geo_elo_active` (3,573) sits nowhere near either gate.
- **B1 unaffected** — cleared to proceed independently of this remediation.

## 4. Root cause

All 84 markets trace to a **single bulk-import event**: `last_checked` clusters into exactly 44 rows on 2026-01-12, 6 on 2026-01-13, and 34 on 2026-04-01 (a secondary batch), every row with **`api_id IS NULL`** (never a real Polymarket API market ID) and `data_source='live_monitoring'` / `trades.data_source='polymarket_api'` — the fabricated rows masquerade as ordinary live-collected data, no distinguishing `data_source` tag. Fingerprint: independently-fabricated tapes matched to template distributions (disjoint synthetic trader pools of identical size per market, e.g. exactly 182 distinct addresses across 3 wildly-different-volume Iran-market instances with zero address overlap between them; near-simultaneous generation timestamps for sibling instances), not one real market copied under multiple IDs.

**Cross-ref O-18** (`2026-07-02-o18-pre-bug-null-resolution-dates.md`): O-18 independently found "4 rows from a **2026-01-12** `live_monitoring` batch" with an unexplained `winning_outcome='unknown'` row, in the *same table*, on the *same date* as O-37's primary import cluster. Not yet confirmed as the same event, but the date match is a real lead — worth checking whether O-18's 4 rows and O-37's 44 January-12 rows share a common inserting process before either is closed further.

**Cross-ref O-38** (`order_book_snapshots` bid/ask sort-order bug, this ledger): during O-37 characterization, exactly 1 `order_book_snapshots` row was found referencing a flagged market (`0x657195fda8c315771f...`, "Putin to invade by June 2026?"), `signal_id='STR003-004'`, `snapshot_type='daily'`, dated 2026-06-12 — spread≈0.98, mid_price=0.5, matching O-38's documented bug signature (STR003 signal family, `daily` type, same date range, same degenerate spread) exactly. This row is very likely already one of O-38's 62-63 known-bad rows, not a separate O-37-specific contamination — no additional order-book remediation needed here; it's covered by O-38's existing open item.

## 5. Remediation — quarantine, not delete

**Design:** reused the existing `markets.trade_gap_flag` exclusion mechanism (already honored by `scripts/update_geo_elo.py` and ~15 other call sites — zero code changes needed), paired with a new forensic-only `markets.flag_reason` column (`'synthetic_quarantine_2026-07-19'`) so this is distinguishable from the pre-existing Apr 7–18 gap flagging. No trade rows deleted; full forensic record preserved.

**Bounded recompute**, scoped to the 953 affected traders via the real production functions (`update_geo_elo.py`, unmodified):
- **27 traders** still clear the 5-qualifying-trade floor on real trades alone — freshly recomputed.
- **926 traders** only cleared the floor because of now-flagged trades — brought to the system's existing "hasn't qualified" representation: `geo_elo`/`geo_elo_active`/`geo_directionality_score = NULL`, `geo_resolved_trades_count` = the real remaining count. This matches the convention already in use for ~9,900 other never-qualified traders in the DB (empirically confirmed before writing — no new sentinel invented). **[CORRECTED 2026-07-23, see §8] All 926 show `geo_resolved_trades_count = 0` under the canonical flag-excluded definition** — their entire non-synthetic geo/elec resolved-trade history was concentrated in the 84 quarantined markets, so excluding those markets correctly zeroes their count. The originally-cited "17 fully-synthetic (0) / 909 partial (1-4)" split was the **pre-exclusion** count (i.e. counting the now-quarantined markets too), not the post-correction value as worded.

**Verification:** independent fresh flag-aware recompute against all 953 post-write — **0 mismatches**. `audit_invariants.py`: 0 CRITICAL, no Stage-0d regression (3 pre-existing REGRESSION items unchanged or improved). `run_tests.py`: 339,663 tests, all green.

## 6. Methodology catches worth keeping on the ledger

1. **A "clean isolated diff" can still be wrong in a non-obvious way.** The dry-run comparison (flagged-scratch vs. an unflagged control, both computed at the same moment — correctly designed to strip out ordinary time-decay drift) still produced a misleading top-line number (418/904 "materially different") because it silently mixed two different things: traders who got a genuine fresh recompute, and traders whose value was frozen (skip-on-thin-sample) in one branch but freshly recomputed in the other. The freshly-recomputed-vs-frozen asymmetry between the two branches wasn't the same "quarantine effect" being measured — it was partly "does a full recompute ever reproduce a previously-stored value," a different question. Caught only by running the real persist and comparing its raw counts against the dry-run's own raw counts, not by trusting the diff's summary number.
2. **"Set the exclusion flag" and "the stored value now reflects it" are not the same claim**, and a codebase whose incremental-update logic assumes monotonic growth (trade counts only ever increase) has no existing path for the reverse case (a trader's qualifying trade count *drops* because some of their history got excluded). The persist step silently left 926 traders in a flag-says-excluded / value-still-includes-it state — caught before commit only because the plan explicitly required re-deriving the "success invariant" and proving it on live data rather than accepting a clean-looking mechanism as sufficient. A literal "0 traders have any trade in a flagged market" check is also the wrong test once you've deliberately chosen quarantine-over-delete — the correct proof is "stored value matches an independent fresh flag-aware recompute," not "no flagged row exists in their history" (which is permanently unsatisfiable by design once rows are preserved).

## 7. Files
- First-repo: `scripts/quarantine_o37_synthetic_markets.py` (commit `5777e45`) — the checked-in, idempotent, reviewable record of exactly what was executed against production. Includes the explicit 84 `market_id` list (not a re-derived heuristic).
- This document.

## 8. Correction — §5 wording (2026-07-23)

Verified 2026-07-23 via four-way measure comparison on the 926: stored value vs. canonical flag-excluded live recompute vs. pre-exclusion (raw) count vs. price-filtered qualifying-trade count. Stored ≡ canonical-recomputed (both 0 for all 926) — no writer divergence, nothing over-zeroed. The pre-exclusion count reproduces the "1-4 mostly, some at 0" pattern originally cited, confirming that figure was pre-correction, not post-correction as §5 stated. O-37 success invariant (0 traders with a qualifying `geo_elo` dependent on a flagged market) and 0 cohort/Pool-C exposure were reconfirmed at the same time. No code or data changes.
