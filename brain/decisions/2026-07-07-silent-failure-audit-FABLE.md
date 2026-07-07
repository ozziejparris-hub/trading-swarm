# Silent-Failure Audit & Leak-Prevention Map — 2026-07-07 (FABLE)

**Scope:** Systematic hunt for the 7 silent-failure classes across first-repo, trading-swarm, and their connection. READ-ONLY audit — no fixes applied. ELO subsystem audited but frozen; anything touching it rides the ELO-arc design (`2026-07-06-elo-arc-design-FABLE.md`), not this document.

**Method:** Every finding below was verified against live code (file:line) and, where possible, live DB/log data during this session. Findings are tagged **PROVEN** (mechanism read in code and/or confirmed with live data) or **INFERRED** (pattern identified; needs one verification step before acting). Severity: **ACTIVE** (causing harm now), **LATENT** (armed, will fire on a trigger), **DORMANT** (dead code / stale data trap).

**Headline:** 3 previously-unknown ACTIVE failures found (7.1 requeue date-gate miss, 2.5 manual-exclusion clobber, 7.7 category-backfill no-op bug), plus one structural theme that explains why this system keeps producing silent failures: **almost every guard tests presence, nothing tests absence or liveness** — work that stops happening, columns that stop being read, and steps that succeed while doing nothing are all invisible to the current harness.

---

## CLASS 1 — Stored-but-never-applied columns

*The behavioral_modifier pattern: data computed, stored, and consumed by nobody (or consumed as a no-op).*

| # | Instance | Evidence | Severity |
|---|----------|----------|----------|
| 1.1 | `behavioral_modifier` / `advanced_modifier` (traders) | The class exemplar (RQ-CONTESTED-001, ledgered). Stored + displayed by `view_trader_rankings.py`, never applied by Writer B. | ACTIVE — **rides ELO arc Stage 4, no action here** |
| 1.2 | `markets.difficulty_score` — dead headline feature | **123 of 581,214 markets non-null (0.02%).** Sole consumer: `analysis/calculate_weighted_metrics.py`; its only production caller is `integrate_behavioral_elo.py` — **dead Writer C, already slated for deletion in ELO-arc Stage 0c.** CLAUDE.md still advertises "market difficulty weighting" as a headline capability. PROVEN. | DORMANT — docs actively misleading |
| 1.3 | `trades.is_taker` + `transaction_hash` chain — unread data at 2.4h/day cost | `is_taker`: 297,130 rows labeled, **zero readers in either repo** (only writers: `polygon_maker_taker.py`, `polygon_event_scanner.py`). `transaction_hash` (1.88M rows): only reader is `polygon_maker_taker.py` itself. The feeder steps — `backfill_transaction_hashes.py` (8,332s today) + `polygon_maker_taker.py` (208s) — consumed **78% of today's maintenance wall-time** producing data nothing consumes. This is also the chain that hung maintenance twice (the RPC timeout incident). PROVEN no-reader; **intent unknown — needs Oscar** (future LP/insider analysis input, or retire?). | ACTIVE cost, zero benefit realized |
| 1.4 | `trades.was_successful` | **0 non-null rows**, 2 references (both schema/write-side). Fully dead column. PROVEN. | DORMANT |
| 1.5 | API-4 columns (`wallet_creation_date`, `true_wallet_age_days`, `funding_wallet`, `is_contract_wallet`) | **Zero code references in either repo** — stronger than O-4's standing "rename" plan assumed: nothing even writes them anymore; `wallet_creation_date` confirmed all-NULL. PROVEN. | DORMANT — O-4 should drop, not rename |
| 1.6 | `traders.unrealized_pnl` — placeholder with a live reader | Permanent 0.0 placeholder (contract §6b), but `trader_performance_analysis.py` reads it as if real — any consumer silently understates open exposure while appearing to include it. PROVEN placeholder + reader. | LATENT — misleading, not corrupting |
| 1.7 | `elo_period1_cutoff` | Referenced only by RQ1.1 research scripts + `verify_elo_recalculation.py`. One-time research artifact. | DORMANT |
| 1.8 | `weighted_win_rate` | Known dead (O-4); writer is dead Writer C. Rides Stage 0c. | DORMANT |
| 1.9 | `kelly/patience/timing_score` snapshots | Stored, NOT ELO inputs (verified session #42), read by display tools only. Documented. | LOW — cosmetic |

**Structural prevention (Class 1):** Extend `monitoring/column_definitions.py` into a **column registry with declared readers** — each governed column names its consumer(s), and a periodic script (piggyback on `check_canonical_definitions.py`, which already scans 252 files daily) verifies at least one declared reader still references the column. A column whose readers all disappear gets flagged the week it happens, not 7 months later. Cheap: the drift-guard infrastructure already exists.

---

## CLASS 2 — Multi-writer convention drift

| # | Instance | Evidence | Severity |
|---|----------|----------|----------|
| 2.1 | `comprehensive_elo` (Writers A+B) | The exemplar. Design banked, frozen. **No action here — ELO arc owns it.** | — |
| 2.2 | `geo_elo` family — cross-repo competing writer, dormant but armed | Canonical daily writer: first-repo `update_geo_elo.py` (writes geo_elo + directionality + count + geo_elo_active atomically, no wipe). Competing: swarm `calculate_geo_elo.py` (last run 2026-06-08) — **different algorithm, wipe-then-rewrite (`UPDATE traders SET geo_elo = NULL...`, line 143), no `geo_elo_active` co-write, and a different `geo_resolved_trades_count` definition** (per-trade count vs canonical COUNT(DISTINCT market)). One re-run = silent mass overwrite. The ollama write allowlist (6.1) keeps `UPDATE traders SET geo_elo` open to agents, so the door isn't just unlocked for humans. Mitigant: harness `check_geo_recon` would catch the count mismatch next 06:00 — ~24h exposure window. PROVEN. | LATENT-HIGH |
| 2.3 | Market-resolution writers: 8 files, still no shared helper | Live `resolved=1` writers: `database.py:483`, `fast_resolution_check.py` ×4, `fetch_market_resolutions.py`, `fix_expired_unresolved.py:93`, `resolve_legendary_markets.py:210/215`, `legendary_positions_scan.py:304/314`, `backfill_o16_tier1/2.py`. O-17 patched the 5 broken co-writes but **the shared `mark_market_resolved()` helper was deferred** — a 9th writer inherits nothing. And conventions STILL differ: `resolve_legendary_markets.py:210/215` and `database.py:update_market_resolution` bind raw `datetime.now()` objects → space-sep **with microseconds** (non-canonical per contract §16); `fix_expired_unresolved` uses `datetime('now')` (canonical); backfill_o16 uses strftime (canonical). **35 `last_checked` + 6 `resolution_date` micro-format rows exist right now** (one day after the 07-06 full normalize), regrowing at resolve_legendary's daily cadence — and the harness cannot see them (5.1b). PROVEN. | ACTIVE (slow leak) |
| 2.4 | `elo_last_updated` 3-format zoo | Writer B `isoformat()` → T+micro (22,945 rows stamped today); Sunday Writer A → space+micro (23,493 rows, 07-05 04:19 signature); legacy space-seconds (canonical). O-3/ELO-arc covers Writer B; **verify the Stage-2 canonical write helper also covers Writer A's format** — the space+micro population is the larger one and is invisible to the harness (counted as canonical-side by the `%T%` test). PROVEN. | Rides ELO arc — one design check to add |
| 2.5 | `research_excluded` — manual writes silently reverted by the daily state machine | **PROVEN with live data:** trader `0x44a1159b` was manually excluded 2026-06-10 (documented in integration-contract §6c). Today: `research_excluded=0, bot_type=NULL, resolved_trades_count=148`. `update_research_exclusions.py` CLEAR_SQL re-includes anyone with ≥20 resolved trades and no durable flag — the manual exclusion was clobbered on the next 06:00 run and **the trader has been back in the research pool for ~4 weeks** while the contract documents him as excluded. (0xf0d3c90f survived only because it got durable `bot_type=LP_ARTIFACT`.) Any past or future manual exclusion without a bot_type is auto-reverted. Same file also documents (comment, line ~127) that `wash_trade_audit.py` is **archived** — the wash-detection axis is permanently frozen at 57 stale flags, recorded nowhere but a code comment (see 7.5). | **ACTIVE — research-pool contamination** |
| 2.6 | `resolved_trades_count` — second live writer until Stage 0c | `evaluate_new_trader_results.py:70` writes it daily (COUNT DISTINCT won/lost markets, flagged scope); dead Writer C writes a different definition. ELO design §7's "single-writer for free" claim becomes true **only after Stage 0c actually deletes Writer C** — until then the conflict is dormant, one accidental invocation away. PROVEN. | DORMANT — closes at Stage 0c |
| 2.7 | `trades.trade_result` | 2 writers (`database.py:593` via evaluator; `backfill_trade_results_geo.py:102`), both use string convention correctly. Spot-checked. | LOW |

**Structural prevention (Class 2):** (a) **Execute O-17's deferred shared-helper extraction** — `Database.mark_market_resolved()` — and route all 8 writers through it; this is the proven pattern (the O-17 design already scoped it). (b) Add a **`db_now()` canonical-timestamp helper** to `column_definitions.py` and a drift-guard rule to `check_canonical_definitions.py` banning raw `datetime.now()` / `.isoformat()` as SQL bind-params in writer scripts — that turns the convention into a mechanically-enforced rule, which is exactly what O-17's root-cause analysis said was missing ("a convention that was never encoded as a shared helper, lint rule, or test"). (c) Give `update_research_exclusions.py` a **durable manual-override mechanism** (e.g., `bot_type='MANUAL_EXCLUDE'` or a `manual_override` column the state machine never touches).

---

## CLASS 3 — No-timeout / no-bound calls

| # | Instance | Evidence | Severity |
|---|----------|----------|----------|
| 3.1 | `daily_maintenance.py run_step()` — **no subprocess timeout** (line 152) | Any of the 29+ steps can hang forever; the log just stops mid-run and nothing alerts (see 4.6/4.9). The maker/taker RPC fix treated one script; **the class remains for every current and future step.** Same for the dedup (line 121) and WAL-checkpoint (line 204) subprocess calls. PROVEN. | LATENT-HIGH — the structural gap behind both 80-min hangs |
| 3.2 | `sqlite3.connect` without `busy_timeout` in ~25 daily-step scripts | Includes blocking Step 0 `update_research_exclusions.py:221`, `fast_resolution_check.py` ×8, `verify_market_titles.py:113`, `sync_trade_categories.py:37`, `update_geo_elo.py:57`, `resync_position_counts.py:19`, and most snapshot/backfill steps. Default 5s vs a monitor writing every 15 min — I hit `database is locked` on first attempt during this session. A locked step either aborts maintenance (blocking) or gets silently WARN-skipped (non-blocking). PROVEN exposure, intermittent trigger. | LATENT — intermittent silent step-skips |
| 3.3 | `backfill_transaction_hashes.py` — unbounded `while True` pagination, growing runtime | 8,332s today inside the no-timeout runner. Growth trend INFERRED (single data point) — check step-duration history; if it grows with trade volume it eventually pushes maintenance into collision with other crons. Compounded by 1.3: this runtime feeds unread columns. | LATENT + active waste |
| 3.4 | Gamma Pass-1 50K assumption vs ~2.1K real | Known (O-16); keyset migration still pending. Carried, not re-audited. | OPEN (O-16 item 4) |
| 3.5 | HTTP layer: **clean** | All `requests.*` calls repo-wide carry timeouts (0 hits in census); aiohttp/ollama clients use ClientTimeout. The maker/taker lesson was applied at the HTTP layer. PROVEN. | ✅ fixed class-wide at this layer |

**Structural prevention (Class 3):** (a) Per-step `timeout=` in `run_step()` — add a budget column to the STEPS tuples (default e.g. 3× the step's rolling median, hard cap 2h); a timeout is a FAILED step, subject to blocking/non-blocking handling. (b) A shared `connect()` helper (in `column_definitions.py` or a new `db_utils`) with WAL + busy_timeout baked in; drift-guard rule against raw `sqlite3.connect` in scripts/. (c) Persist per-step durations to a JSON the harness reads — "step duration >2× its 14-day median" as a Tier-2 invariant. That catches both hangs-in-progress and unbounded growth (3.3) mechanically.

---

## CLASS 4 — Silently-swallowed exceptions & false success

Census: **96 except→pass/continue sites** (first-repo: 17 bare / 28 broad / 41 narrow; swarm: 10 total). Full list retained in session; the ones that matter:

| # | Instance | Evidence | Severity |
|---|----------|----------|----------|
| 4.1 | **"all steps succeeded" banner is unconditional** — `daily_maintenance.py:232` | The completion banner is a hardcoded string printed regardless of non-blocking step failures, test-suite failures, or the final 2 steps' outcomes (their return values are discarded, lines 216–228). Anyone — human or AI observer — grepping the log for health is lied to. PROVEN. | ACTIVE — false health signal, daily |
| 4.2 | `trading_behavior_analysis.py` — **5 bare excepts inside ELO behavioral inputs** (lines 202, 399, 492, 555, 737) | A parse/calc failure silently degrades behavioral scores toward defaults — the *exact mechanism* of the April "neutral 1.0× modifiers" incident, still present in the module that feeds the Sunday recalc. Existence PROVEN; per-site blast radius INFERRED (read each before fixing — frozen-area adjacent, so fix rides ELO-arc discipline). | LATENT-HIGH |
| 4.3 | `database.py:786` — bare except swallows `end_date` parse failures | Market gets stored with `end_date=NULL` silently → feeds the exact "no endDate → structurally unreachable by resolution passes" population O-16 spent 194K markets cleaning up. PROVEN code path. | LATENT — regrows the O-16 class |
| 4.4 | `monitor.py:841` — broad except-pass on batch watermark timestamp parse | Bad batch → watermark silently None. Moderate. | LATENT-LOW |
| 4.5 | Zero-output-forever family (the check_market_resolutions signature) | (a) **`backfill_market_categories.py` — see 7.7, a guaranteed daily no-op with exit 0.** (b) `hydrate_stub_markets.py` — same 200 not-found rows reground daily, ≥7 consecutive zero-output runs (see 7.6). (c) `backfill_market_dates.py` — now grinding 316 permanent not-founds (benign while matching-set < its 500 limit, watch it). All three print "Done — OK". PROVEN from log history + query shapes. | ACTIVE (a, b) |
| 4.6 | **Nothing detects absence of expected work** | The observer has zero maintenance-freshness checks (grepped: no check that the 06:00 run happened, no check that the daily audit JSON was written). Cron wrapper logs exit codes to a file nobody reads. If maintenance dies at step 1, the *only* symptom is a missing Telegram audit message — a dog that didn't bark. PROVEN gap. | LATENT-HIGH — structural |
| 4.7 | Ollama loop tool errors surface only to the LLM agent | `run_sql`/`run_sql_write` return `{"error": ...}` dicts to the model; repeated failures produce no human-facing telemetry beyond a log file. INFERRED gap (no aggregation found). | LATENT-LOW |
| 4.8 | Benign/acceptable | `fast_resolution_check.py:282` (title ASCII fallback), psutil/ImportError guards, worker's deliberate retry-on-restart patterns (documented in docstrings). Not defects. | — |

**Structural prevention (Class 4):** (a) Derive the maintenance banner from an outcomes list; print `N steps, M failed: [names]` and pass a nonzero exit if any *blocking-tier* concern exists. (b) **Absence detection**: maintenance writes a completion sentinel (timestamp + step outcomes JSON); the observer — which already runs 24/7 — gains one check: sentinel older than 26h → Telegram. This single guard would have caught the July-1-class outage, a step-1 crash, and a hang, uniformly. (c) **Zero-yield alarm**: steps already print work counts; persist them (same JSON as 3c) and alert on "N consecutive zero-work days" for steps with nonzero backlogs. This is the generalized O-13 lesson — it would have caught check_market_resolutions in week 1 instead of month 7. (d) Drift-guard rule: no bare `except:` in `monitoring/` + `analysis/` (grep-able, ~17 sites to convert).

---

## CLASS 5 — Harness checks that test the wrong thing

| # | Instance | Evidence | Severity |
|---|----------|----------|----------|
| 5.1 | Timestamp check tests the wrong thing on 3 axes (`audit_invariants.py:312–363`) | **(a) Majority-wins canonical:** `elo_last_updated` and `positions.entry/exit_timestamp` are "protected" toward **T-sep** (`canonical_is_T=True`) — the *opposite* of contract §16's repo-wide space-sep standard. The harness literally counts correct-format rows as debt for those columns. **(b) Wrong axis:** the binary `%T%` test misses microseconds/timezone variants — the 23,493 space+micro rows (Sunday writer) and today's 35+6 market micro-rows count as canonical. **(c) Aggregate masking, live today:** `elo_last_updated` = 23,504 > its per-column floor 23,163 (recorded as REGRESSION in the detail payload), but the check's status uses the summed total (23,556 < 24,996) → headline **PASS**. One column's improvement (end_date/res_date: 1,827 → 52 after O-16 fixes) bought another column's regression a free pass. All PROVEN. | ACTIVE — passing while the named property is violated |
| 5.2 | Floors never ratchet down — improvements widen the alarm dead-zone | `FLOOR_API_NO_LOCAL=114,047` vs actual 13,436 (could regress **8.7×** silently); `FLOOR_VOL_OUTLIERS=75` vs 25; `FLOOR_SUCC_CONTRA=608` vs 0. Tier-3 alerts only above floor×1.1. PROVEN numbers. | LATENT — silent-regression headroom |
| 5.3 | `check_dup_market_id` is vacuous | market_id is PRIMARY KEY; the check can never fire (fine as a schema tripwire, zero value as claimed coverage). | Cosmetic |
| 5.4 | `geo_elo` range checked only for pool members | Non-pool traders can hold absurd geo_elo (the swarm's own findings noted a 5464 outlier); `geo_elo_active` has no range check at all. Minor — signal paths gate on pool membership. | LOW |
| 5.5 | **Coverage gaps — every recent burn lacks a standing invariant** | Zero harness coverage for: (a) `resolved=1 AND resolution_date IS NULL` (the O-17/O-18 class — floor would be 55); (b) `resolved=0 AND end_date < -7d AND resolution_date IS NULL` (the O-16 class — floor ~606 today, would catch regrowth incl. via 4.3); (c) `pnl_skip=1` count (the O-15 class — a floor-0 count check would have alerted at ~50 instead of 1,421); (d) **open positions on resolved markets** (the 7.1 class — 256K rows right now, no check); (e) writer-liveness / max-write-age for key columns (the behavioral_modifier 7-month-silence class); (f) maintenance-freshness (4.6). `comprehensive_elo` coverage rides the ELO arc's 9 invariants. PROVEN absences (read all 20 checks). | The highest-leverage list in this audit |
| 5.6 | `write_integration_health.py` "contract_valid" can only detect apocalypse | Tests 3 of the contract §9's 9 metrics, against thresholds ~60× below current values (clean_pool 440 vs 26,621; clean_markets 11,000 vs 223,541). `SCHEMA_VERSION` hardcoded "2026-04-30", self-describedly "updated manually" — never updated through 2.5 months of schema-critical commits. Swarm agents are told to trust this file *instead of* running §9 themselves. PROVEN. | ACTIVE — cross-repo health signal that is ~always green |

**Structural prevention (Class 5):** (a) Rebuild the timestamp check: canonical format defined **once** in `column_definitions.py` (strict pattern incl. micro/tz axes), per-column floors gate per-column status, headline = worst column. (b) **Auto-ratcheting floors**: move floors from constants to a git-tracked JSON; when a check comes in below floor for 7 consecutive days, the harness lowers the floor and logs it. Improvements then permanently tighten the net. (c) Add the six 5.5 invariants — each is a ≤10-line COUNT check, and together they retro-cover O-15, O-16, O-17, O-18, and finding 7.1. (d) Implement contract §9 fully in `write_integration_health.py`, with expected ranges generated from live values + tolerance rather than hand-edited constants; derive SCHEMA_VERSION from `PRAGMA schema_version`/table-info hash.

---

## CLASS 6 — The repo connection (O-9, folded in)

**Write topology (complete):** trading-swarm touches first-repo's DB through exactly 3 code paths — `calculate_geo_elo.py` (dormant writer, see 2.2), `orchestrator/ollama_agent_loop.py` (agent read+write tools), and read-only scripts (`run_feedback_loop_agent.py` mode=ro ✅, `write_integration_health.py`, RQ scripts). Plus cron topology: swarm cron_wrappers launch first-repo's maintenance and backups.

| # | Instance | Evidence | Severity |
|---|----------|----------|----------|
| 6.1 | **Agent write allowlist is prefix-matched — any allowed first column smuggles arbitrary columns** (`ollama_agent_loop.py:54–71, 293`) | `^UPDATE\s+traders\s+SET\s+geo_elo\b` happily matches `UPDATE traders SET geo_elo=1500, comprehensive_elo=9999 WHERE ...` — **a frozen-column write path for a local LLM**, inside the 50K-row cap. Also allowed: `ALTER TABLE traders ADD COLUMN` (schema drift by agent; DDL explicitly skips the row-count guard, line 321). Allowlist also references `accuracy_pool` (column dropped 2026-06-05) and `trader_notes` (table has never existed) — guard vs schema drift in both directions. PROVEN by regex semantics + schema check. | **LATENT-HIGH** — one agent hallucination from frozen-area corruption |
| 6.2 | Mandatory read filters are advisory, not enforced | `tool_run_sql` permits arbitrary SELECT against any DB under /home/parison/. Contract §2's mandatory filters (research_excluded, trade_gap, winning_outcome…) exist only in prompts/docs. Research contamination requires nothing but an agent forgetting a WHERE clause — the class of error LLMs make most. PROVEN. | LATENT — quiet research corruption |
| 6.3 | Agent writes to state-machine columns can't stick (or clobber) | Allowlist exposes `research_excluded` and `bot_type` — writes to the former are silently reverted within 24h by Step 0 (the 2.5 mechanism); writes to `geo_elo` are silently overwritten by the next `update_geo_elo.py` run. Either direction, the agent's action and the daily machine disagree and nobody is told. PROVEN mechanism. | LATENT |
| 6.4 | Contract §9 ranges & pool numbers stale by up to 10× | Contract (v2.13, 06-23) predates the O-16 backfill world: clean_markets "≈24,184" vs 223,541 actual. Alert bounds one-sided, so nothing fires — but any agent that *does* sanity-check against documented ranges would conclude the DB is corrupt. INFERRED impact. | LOW-MODERATE — chronic doc drift |
| 6.5 | Positive findings worth keeping | Connection pattern (WAL + busy_timeout 30s) correctly copied in swarm writers; MAX_WRITE_ROWS=50K guard works (executes-then-rollback is transactionally sound); feedback-loop opens mode=ro; `run_daily_maintenance.sh` uses `set -uo pipefail` + exit-code logging. | ✅ |

**Structural prevention (Class 6):** (a) **Replace raw-SQL agent writes with named operations** — the allowlist's job is better done by 5 parameterized functions (`set_geo_elo(addr, val)`, …) that route through the same canonical helpers first-repo uses; regex-allowlisting SQL from an LLM is structurally unwinnable. Stopgap (one line each): anchor patterns to forbid additional assignments (match up to `=` then reject `,` outside quotes), and delete the `accuracy_pool`/`trader_notes`/`ALTER` entries. (b) **Enforce read filters with SQL views**: create `research_trades_v` / `research_traders_v` in first-repo with contract §2 baked in; contract mandates agents query views, and `tool_run_sql` can enforce table-name restrictions mechanically. (c) Contract expected-ranges become generated, not hand-written (same fix as 5.6).

---

## CLASS 7 — Circuit-breakers / silent scope shrink

| # | Instance | Evidence | Severity |
|---|----------|----------|----------|
| 7.1 | **Requeue date-gate misses the entire O-16 backfill — the audit's biggest live finding** | `requeue_resolved_market_traders.py:76` gates on `resolution_date > last_run`. The O-16 backfills deliberately wrote **historical** resolution dates (2024–2025), which can never exceed the last-run timestamp — **0 of ~193K backfilled markets ever triggered a requeue.** Right now: **256,452 open positions across 10,403 traders** sit on resolved backfilled markets with no synthetic-close path; **5,468 are flagged traders, 5,225 of them untouched by the P&L worker since before the backfill (07-02).** Their realized_pnl → pnl_modifier → ELO are silently stale, and — directly relevant to the ELO arc — **the O-15 "backlog drain plateau" (Stage 0a gate) is being measured against a queue this cohort never entered**, so the plateau will read as arrived while a 5K-trader backlog hides behind the date gate. Trade-side partially self-heals (`evaluate_new_trader_results.py` has no date gate — but its flagged-non-excluded scope leaves 122,265 pending trades on backfilled markets, most out of scope by design). Fix is one `--force` run (idempotent by design) + changing the gate to `last_checked` (write-time, not event-time). PROVEN + quantified. | **ACTIVE-HIGH** |
| 7.2 | `pnl_skip` — fixed, but recurrence is invisible | O-15 fixed; count is 0 today. No harness watch → next occurrence silently re-accumulates until someone investigates (that's how it reached 1,421 last time). Coverage gap 5.5c. | LATENT |
| 7.3 | `backfill_attempted` one-shot stamp | Stamped after any "successful" fetch — including an empty-but-HTTP-200 response during an API bad window → trader permanently skipped for historical backfill. Timeout path correctly leaves it unstamped. LATENT-LOW, by-design tradeoff worth a note in the column registry. | LATENT-LOW |
| 7.4 | Manual exclusions reverted (scope silently *grows*) | See 2.5 — the inverse failure: excluded bad actors silently re-enter. | ACTIVE (same item as 2.5) |
| 7.5 | Wash-trade detection axis frozen | `wash_trade_audit.py` archived; 57 stale flags from an unknown-date run; **no new wash detection ever occurs.** Recorded only in a code comment — not in the ledger, contract known-limitations, or any doc an agent reads. Needs a decision (restore or formally retire) + a ledger entry either way. PROVEN. | ACTIVE gap in detection coverage |
| 7.6 | `hydrate_stub_markets.py` — rotation-less queue permanently jammed | Query `WHERE m.resolution_date IS NULL ... LIMIT 200` with no ordering/attempt-marker → fetches the **same 200 unfindable markets every day** (≥7 consecutive 0-updated runs in the retained log). The thousands of stubs behind them are never attempted. Exactly the pattern the O-13 round-robin fix (`6c08afc`) solved for resolution passes. PROVEN. | ACTIVE — step is dead while reporting OK |
| 7.7 | `backfill_market_categories.py` — limit bug makes step 15 a guaranteed no-op | Line 245: `if state["total_classified"] + state["total_skipped"] >= args.limit` compares **lifetime state-file totals (17,584)** against the per-run `--limit 50` → instant stop, every day, exit 0, "OK (0.0s)". The step has been structurally incapable of doing work since its lifetime counter passed 50, which is part of why O-2's Unknown backlog (138,608, REGRESSION) never drains despite a "daily backfill." One-line fix (per-run counter). PROVEN. | **ACTIVE** |
| 7.8 | By-design gates (fine) | `is_flagged` monitor scope, insider-detection windows, MAX_WRITE_ROWS, worker in-memory 5-failure skip (resets on restart, documented). | — |

**Structural prevention (Class 7):** Every skip/exclusion flag and bounded queue gets a **population gauge in the harness** — `pnl_skip` count, hydrate-backlog attempted-vs-total, requeue candidates matched-vs-eligible. A circuit breaker without a gauge is a silent amputation; the gauge is one COUNT per flag. Plus: event-time vs write-time rule of thumb — **queue triggers must gate on write-time (`last_checked`), never event-time (`resolution_date`)**, because backfills legitimately write old event times (7.1's root cause, worth encoding in the contract as an architecture rule).

---

## PRIORITIZED ACTION LIST

**FIX NOW (small, active harm, this week):**
1. **7.1 Requeue miss** — run `requeue_resolved_market_traders.py --force` once (idempotent; ~10K traders reset; worker clears at ~50/min) **and** change the gate to `last_checked`. Coordinate with O-15 watching: the queue metric will spike, then give an *honest* Stage-0a plateau. Highest impact-to-effort in this audit.
2. **2.5 Re-exclude `0x44a1159b`** durably (bot_type route) + add the manual-override mechanism to `update_research_exclusions.py`. Update contract §6c.
3. **7.7 Category-backfill limit bug** — one line; restores the O-2 drain path.
4. **7.6 Hydrate rotation** — add attempted-marker rotation (pattern exists from `6c08afc`).
5. **6.1 stopgap** — tighten allowlist regexes; delete `accuracy_pool`/`trader_notes`/`ALTER` entries.
6. **4.1 Honest maintenance banner** + per-step timeout (3.1) in the same small PR.

**ADD HARNESS COVERAGE (next session-or-two):**
7. The six 5.5 invariants (resolution co-write, O-16 backlog, pnl_skip count, open-positions-on-resolved, writer-liveness max-age, maintenance-freshness sentinel). Retro-covers every burn from the past month.
8. Rebuild the timestamp check (5.1) against contract §16 with per-column gating.
9. Floor auto-ratcheting (5.2).
10. Zero-yield step alarm + step-duration telemetry (4.5/3.3 prevention — the generalized O-13 lesson).

**CONVENTIONS / STRUCTURAL (scheduled work):**
11. `Database.mark_market_resolved()` shared helper (O-17's deferred item — 8 writers route through it).
12. Shared `connect()` + `db_now()` helpers + new drift-guard rules (no raw sqlite3.connect in scripts/, no raw datetime.now() bind-params, no bare except in monitoring//analysis/).
13. Ollama agent writes → named operations; reads → contract-enforcing views (6.1/6.2 proper fix).
14. Contract §9 / integration-health generated from live values; SCHEMA_VERSION automated (5.6/6.4).
15. Drop dead columns (1.4, 1.5 → fold into O-4 as *drop*, not rename) + retire or revive `difficulty_score` (1.2) and fix CLAUDE.md's claim.

**NEEDS OSCAR'S JUDGMENT (can't be decided by audit):**
- **1.3** — `is_taker`/`transaction_hash` chain: 2.4h of maintenance daily for data nothing reads. Intended future consumer, or pause the steps until one exists?
- **7.5** — wash-trade detection: restore `wash_trade_audit.py` or formally retire the axis (ledger entry either way).
- **4.2** — the 5 bare excepts in `trading_behavior_analysis.py` are frozen-area-adjacent: fix inside ELO-arc discipline, or accept until Stage 4?
- Research-scout cron runs 2×/day (08:00 + 20:00) — intentional?
- Whether the 122K out-of-scope pending trades on backfilled markets (7.1 residual) matter for any research query that doesn't go through the flagged pool.

**Explicitly NOT proposed here (frozen):** any change to comprehensive_elo writers, formulas, or schedule — 1.1, 2.1, 2.4, 2.6 and `comprehensive_elo` harness coverage all ride the ELO-arc design's staged migration as already planned.

---

## The one-sentence synthesis

Every silent failure in this system's history reduces to one of two missing reflexes: **nothing verifies that expected work keeps happening** (liveness), and **nothing verifies that stored things are still connected to consumers** (reachability) — the prevention map above is mostly those two reflexes, mechanized cheaply on infrastructure (drift-guard, harness, observer) that already exists.

*Audit: Claude Fable, 2026-07-07. READ-ONLY session — this document is the only artifact written. Not yet committed — pending Oscar's review.*
