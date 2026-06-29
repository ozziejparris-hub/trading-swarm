# O-6 Comprehensive ELO Writer Map
**Date:** 2026-06-29  
**Scope:** Exhaustive reconnaissance of all `comprehensive_elo` writers across first-repo  
**Purpose:** Design input for Layer 2 (O-7) reconciler  
**Status:** Investigation complete — change nothing

---

## 0. Population Context

| Metric | Value |
|--------|-------|
| Total flagged traders | 22,563 |
| Clean research pool (`research_excluded=0`) | 22,398 |
| With real pnl_modifier (≠1.0) | 18,165 |
| Average comprehensive_elo | 1,370.8 |
| Range | 506 – 3,306 |
| Elite (≥1,550) | 3,500 |

---

## 1. Exhaustive Writer Inventory

Four distinct writers exist. Trading-swarm has zero writers (read-only consumer only).

---

### Writer A — Sunday Full Recalculation
**File:** `monitoring/elo_bridge.py` → `UnifiedELOMonitoringBridge.full_elo_recalculation()`  
**Entry point:** `scripts/recalculate_comprehensive_elo.py` → `scripts/run_sunday_elo.sh`  
**Trigger:** `polymarket-sunday-elo.timer` — `OnCalendar=Sun *-*-* 03:00:00 UTC`, Persistent=true  

**Shell command (run_sunday_elo.sh):**
```bash
python3 scripts/recalculate_comprehensive_elo.py \
  --skip-correlation --skip-contrarian --skip-advanced-metrics
```

**Effective flags passed to `full_elo_recalculation()`:**
```python
full_elo_recalculation(
    verbose=True,
    force_refresh=True,
    skip_correlation=True,     # network/correlation skipped
    skip_contrarian=True,      # contrarian skipped
    skip_advanced_metrics=True # calibration/risk/regret skipped
)
```

**Theoretical formula (as coded in `get_trader_global_elo`):**
```
adjusted = base_elo                                   # elo_system.get_overall_elo()
adjusted *= behavioral_multiplier                     # consistency×diversification×style×activity, clamped [0.80, 1.40]
adjusted += behavioral_bonus                          # kelly/patience/timing, additive [-100, +100]
adjusted *= pnl_multiplier                            # from positions table, [0.40–2.50]
comprehensive_elo = min(adjusted, 1500 + resolved×150)  # soft cap
```

**Empirical formula (confirmed by DB measurement today 2026-06-29):**
```
comprehensive_elo = base_elo × pnl_multiplier         # behavioral terms not materializing
```
Evidence: For 8 sample traders with `behavioral_modifier` 1.11–1.28 and `pnl_modifier` 1.11–2.20,  
`|comp - base×pnl| = 0.00` exactly; `|comp - base×behavioral×pnl|` = 145–785 ELO points off.

**The discrepancy:** `behavioral_modifier` is stored (computed AFTER `get_trader_global_elo` returns) but the value used INSIDE `get_trader_global_elo(apply_behavioral=True)` is effectively 1.0. Root cause not resolved from static analysis — this is a Layer 2 investigation item. Most likely: `_load_behavioral_data() → analyze_all_traders()` produces a dict whose keys do NOT match what `calculate_consistency_modifier` / other sub-calculators expect, causing all sub-components to fall through to `return 1.0` defaults, combined = 1.0 clamped to 1.0. The SEPARATE post-loop call to `calculate_behavioral_multiplier()` then computes the "correct" value from a different code path and stores it. The two calls disagree silently.

**Trader scope:** All `is_flagged = 1` traders (attempted ~22,563; ~20,035 processed today — failures are exceptions per-trader, not aborts).  
**DB columns written:** `comprehensive_elo`, `base_category_elo`, `behavioral_modifier`, `advanced_modifier`, `pnl_modifier`, `kelly_alignment_score`, `patience_score`, `timing_score`, `elo_last_updated`  
**Run time today:** Completed at `08:46:35 UTC` (started 03:00 UTC, ~5h46m for ~20K traders)

---

### Writer B — Daily P&L Modifier Pass
**File:** `scripts/apply_full_elo_modifiers.py` → `main()`  
**Entry point:** `scripts/daily_maintenance.py` STEPS list, step 24 of 29 (blocking)  
**Trigger:** Cron `0 6 * * *` → `/home/parison/trading-swarm/scripts/cron_wrappers/run_daily_maintenance.py`  

**Formula:**
```python
dampening = (0.60 if base >= 2500 else
             0.80 if base >= 2000 else
             1.00)

new_elo = base + base × (pnl_mult - 1.0) × dampening
        = base × (1 - dampening + pnl_mult × dampening)

# Guards applied before dampening:
# confidence_cap: clamps pnl_mult to 1.30x–2.20x depending on closed_position count
# thin-sample gate: if resolved_count < 10 and mult > 1.0 → forces mult = 1.0
# asymmetric penalty: if mult < 1.0 and base >= 2000 → loss amplified ×1.30
# hard cap: min(new_elo, 3500)
```

**Base ELO source:** Reads `base_category_elo` from DB (written by Writer A or prior backfill). Falls back to `comprehensive_elo` only if `pnl_modifier` is NULL or ≈1.0 (meaning no prior modifier applied). Will NOT touch `base_category_elo` if it's already set to non-1500 value.

**Modifiers applied:**
- P&L: **YES** (from `positions` table, with dampening + confidence gate)
- Behavioral: **SKIPPED** (by design — script header explicitly notes this)
- Advanced/network/contrarian: **SKIPPED**

**Trader scope:** Only traders with `closed_positions >= 1` in `pnl_cache` (~35 flagged + ~190 non-flagged per run, based on Monday-Saturday elo_last_updated counts: 2,473 flagged Mon-Sat this week).

**DB columns written:** `comprehensive_elo`, `pnl_modifier`, `elo_last_updated`, `base_category_elo` (conditionally: only if NULL or == 1500.0 ± 0.0001)  
**Does NOT write:** `behavioral_modifier`, `advanced_modifier`, `kelly_alignment_score`, `patience_score`, `timing_score`

**Sunday ordering:** On Sundays, Writer B runs inside daily_maintenance which starts at 06:00 UTC. Writer A finishes at ~08:46 UTC (AFTER Writer B). For `is_flagged=1` traders, Writer A overwrites Writer B's Sunday output. Writer B's Sunday writes survive only for non-flagged traders.

---

### Writer C — Behavioral Integration Pipeline (DISABLED since 2026-06-05)
**File:** `scripts/integrate_behavioral_elo.py` → `run_unified_elo_with_behavioral()`  
**Entry point:** Previously called from `monitoring/system_observer.py` — DISABLED at line 2956–2977  
**Trigger:** None (dead code path, commented out)

**Formula:**
```python
comprehensive_elo = system.get_trader_global_elo(
    trader_address,
    apply_behavioral=True,
    apply_advanced=False,
    apply_network=False,
    apply_contrarian=False,
    apply_pnl=False          # NOTE: NO P&L applied
)
behavioral_modifier = comprehensive_elo / max(1, base_elo)  # derived ratio stored
```

**Scope:** All traders in `elo_system.get_all_traders()` (those with resolved trades in ELO system memory).

**Why disabled (system_observer.py line 2956–2960):**
> "DISABLED 2026-06-05: behavioral_modifier is written here but silently discarded by apply_full_elo_modifiers.py which overwrites comprehensive_elo without reading it. Intentionally disabled until comprehensive_elo formula is redesigned (RQ-CONTESTED-001, July 2026)."

**Key design flaw:** Writer C applied behavioral WITHOUT P&L. Writer B then overwrote with P&L WITHOUT behavioral. The two passes were never unified. The same flaw (behavioral not materializing) now applies to Writer A's empirical behavior.

---

### Writer D — Monitoring Cycle Quick Update
**File:** `monitoring/elo_bridge.py` → `UnifiedELOMonitoringBridge.quick_elo_update_for_traders()`  
**Entry point:** `monitoring/trader_analyzer.py:303` — called after market resolution during 15-minute monitoring cycles  
**Trigger:** Continuous; fires when `db.get_traders_with_recent_evaluated_trades(hours=24)` returns results

**Formula (via `_process_trader_chunk` → `_batch_store_elo_results`):**
```python
comprehensive_elo = elo_system.get_trader_global_elo(
    trader_address,
    apply_behavioral=True,
    apply_advanced=True,      # NOTE: advanced IS applied (differs from Sunday)
    apply_network=False,
    apply_contrarian=False,
    apply_pnl=True
)
```

**Empirical formula:** Same discrepancy as Writer A — behavioral likely not materializing. Effective formula: `base × advanced_mult × pnl_mult` (advanced is included but behavioral is 1.0 in practice — same root cause as Writer A).

**Scope:** Only traders with recent evaluated trades (~few traders per 15-minute cycle; typically 0–20 per cycle).  
**DB columns written (via `_batch_store_elo_results`):** `comprehensive_elo`, `base_category_elo`, `behavioral_modifier`, `advanced_modifier`, `pnl_modifier`, `elo_last_updated`  
**Does NOT write:** `kelly_alignment_score`, `patience_score`, `timing_score`

**Formula deviation from Writer A:** Writer D includes `apply_advanced=True` (calibration/risk/regret multiplier); Writer A skips it via `--skip-advanced-metrics`. So a trader touched by Writer D during the week may have a different `advanced_modifier` than one touched by Writer A on Sunday.

---

### Writer E — Archive/Simulation (NOT PRODUCTION)
**Files:** `scripts/simulation/calculate_elo_simple.py`, `scripts/archive/backfill_elo_ratings.py`  
**Status:** Not in any active production pipeline. Standalone scripts only. Not analyzed further.

---

## 2. Formula Divergence — Side by Side

### Theoretical formulas

| Path | Formula |
|------|---------|
| **Writer A (Sunday) — theoretical** | `min((base × beh_mult + bonus) × pnl_mult, 1500 + resolved×150)` |
| **Writer A (Sunday) — empirical** | `base × pnl_mult` (beh=1.0 effective, bonus=0) |
| **Writer B (Daily)** | `base + base × (pnl_mult − 1) × dampening` |
| **Writer D (Monitoring)** | `base × adv_mult × pnl_mult` (beh=1.0 effective) |

For `dampening = 1.0` (base < 2,000): Writer B simplifies to `base × pnl_mult` — **identical** to Writer A empirical.  
For `dampening < 1.0` (base ≥ 2,000): Writer B is more conservative than Writer A empirical.

### Worked example: hypothetical trader (base=1,500, beh=1.1, adv=1.05, pnl=1.2)

**Writer A — Sunday theoretical** (skips advanced per shell flags):
```
((1,500 × 1.1) + 0) × 1.2 = 1,650 × 1.2 = 1,980
```

**Writer A — Sunday empirical** (behavioral not applied in practice):
```
1,500 × 1.2 = 1,800
```

**Writer B — Daily** (base < 2,000, dampening = 1.0):
```
1,500 + 1,500 × (1.2 − 1.0) × 1.0 = 1,800
```
*Writers A-empirical and B produce identical results at base < 2,000.*

**Divergence (theoretical Sunday vs daily):** 1,980 − 1,800 = **+180 points (+10%)**  
**Divergence (empirical Sunday vs daily):** **0 points** (match exactly for base < 2,000)

### Worked example: high-ELO trader (base=2,200, beh=1.1, pnl=1.2)

**Writer A — Sunday theoretical:**
```
(2,200 × 1.1) × 1.2 = 2,904
```

**Writer A — Sunday empirical:**
```
2,200 × 1.2 = 2,640
```

**Writer B — Daily** (base ≥ 2,000, dampening = 0.80):
```
2,200 + 2,200 × (1.2 − 1.0) × 0.80 = 2,200 + 352 = 2,552
```

**Divergence (theoretical Sunday vs daily):** 2,904 − 2,552 = **+352 points (+14%)**  
**Divergence (empirical Sunday vs daily):** 2,640 − 2,552 = **+88 points (+3.4%)**  

The real (empirical) divergence between Sunday and daily paths is SMALLER than the theoretical one because behavioral is not materializing. The residual divergence at high ELO comes entirely from dampening.

---

## 3. The Interleaving — What Actually Happens to a Trader Over a Week

### Sunday (weekly cadence)

| Time (UTC) | Event | Who writes | Formula applied |
|------------|-------|-----------|-----------------|
| 03:00 | Sunday ELO timer fires → `run_sunday_elo.sh` starts | — | — |
| ~06:02 | Daily maintenance cron starts | — | — |
| ~08:39–08:44 | Writer B (`apply_full_elo_modifiers.py`) runs as step 24 | Writer B | `base × pnl` (dampened) for ~35 flagged traders |
| 08:46:35 | Writer A finishes, commits all traders at once | Writer A | `base × pnl` (empirical) for ~20,035 flagged traders — OVERWRITES Writer B's Sunday writes |
| ~08:50 | Daily maintenance completes (remaining steps 25–29 + post-loop) | — | — |

**Result on Sunday:** Writer A is always the last writer for `is_flagged=1` traders. Writer B's Sunday writes are erased.

### Monday–Saturday (daily cadence)

| Time (UTC) | Event | Who writes |
|------------|-------|-----------|
| 06:00 | Daily maintenance starts | — |
| ~08:xx | Writer B runs as step 24 | Writer B — ~35 flagged, ~190 non-flagged |
| Rest of week | No ELO writes (monitoring Writer D fires only when markets resolve) | Writer D — few traders per cycle |

**Result on weekdays:** Writer B is the last writer for ~35 flagged traders with closed positions. By Saturday, those ~35 traders have `elo_last_updated` = the most recent weekday. All other flagged traders retain Sunday's value.

### State of the database at any given weekday (mid-week)

| Population | Count (approx) | Last writer | Formula applied |
|------------|---------------|-------------|-----------------|
| Flagged, touched by Writer B this week | ~35 × N_days | Writer B | `base × pnl` (dampened) |
| Flagged, NOT touched by Writer B | ~22,500 | Writer A (last Sunday) | `base × pnl` (empirical) |
| Non-flagged, with P&L data | ~190 × N_days | Writer B | `base × pnl` (dampened) |
| Flagged, no ELO ever | ~29 | None | NULL |

**Practical conclusion:** Because Writer A's empirical formula = Writer B's formula at base < 2,000 (dampening=1.0), the two paths produce nearly identical results for most traders. The only real divergence is for traders with base ≥ 2,000 touched by Writer B (dampening reduces pnl gain), versus the same trader untouched by Writer B (no dampening applied by Writer A).

### Can `elo_last_updated` tell us which path last wrote each trader?

Yes, approximately:

| `elo_last_updated` pattern | Last writer |
|---------------------------|-------------|
| `2026-06-29 08:46:35` | Writer A (today's Sunday run) |
| Weekday between 06:00–10:00 UTC | Writer B (daily maintenance) |
| Time within 15-min monitoring cycle | Writer D (market resolution event) |
| NULL or very old date | No ELO ever calculated |

**Current split (2026-06-29, immediately post-Sunday run):**

| Last writer | Flagged trader count | elo_last_updated |
|-------------|---------------------|------------------|
| Writer A (today) | 20,035 | 2026-06-29 |
| Writer B (Mon-Sat this week) | 2,473 | 2026-06-23 to 2026-06-28 |
| Old (before this week) | ~26 | before 2026-06-23 |
| Never written | 29 | NULL |

---

## 4. Which Formula Is "Right"?

### Design intent evidence

**For Writer A being canonical:**
- The docstring in `full_elo_recalculation` describes it as "Full ELO recalculation for ALL traders (6/6 dimensions)" — clearly the intended authoritative pass.
- The `get_trader_global_elo` comment says "All 6 dimensions" when all flags are True — behavioral was always intended to be part of comprehensive_elo.
- `integrate_behavioral_elo.py` was explicitly built to add behavioral intelligence.
- `system_observer.py` line 2957 treats the behavioral skip as a BUG: "silently discarded" — this language implies it should NOT be discarded.

**For Writer B's dampening being notable:**
- The `apply_full_elo_modifiers.py` header says dampening "prevents high-ELO inflation." This is a deliberate design choice.
- The #42 note flagged Writer B's dampening as "may be canonical." The confidence gate (capping pnl multiplier by closed_position count) is also defensible: a trader with 1 closed position shouldn't get a 2.5x pnl boost.

**Evidence summary:**
- Writer A was designed as the authoritative 6-dimensional formula. Writer B was designed as a daily approximation to apply P&L when behavioral data was unavailable.
- Writer A's failure to include behavioral (the empirical bug) means the two paths currently produce nearly the same result — but this is accidental, not intentional alignment.
- Writer B's dampening + confidence gate are defensible and may be worth incorporating into a unified formula.
- Writer A's soft cap (`1500 + resolved × 150`) is a different kind of guard: prevents inflation for traders with few resolved trades.

**Layer 2 recommendation (do not decide here):** The unified formula should be Writer A's theoretical formula (behavioral × pnl multiplicative) with Writer B's dampening at high ELO (≥2,000) and Writer B's confidence gate on pnl multiplier. The resulting formula would be:
```
adjusted = base × behavioral_mult + behavioral_bonus  # full behavioral
adjusted *= pnl_mult_confidence_gated                  # Writer B's confidence gate
# dampening on the GAIN only (not on full pnl):
adjustment = adjusted - base
if base >= 2500: adjustment *= 0.60
elif base >= 2000: adjustment *= 0.80
comprehensive_elo = min(base + adjustment, hard_cap)
```
But this is a Layer 2 design decision, not an O-6 finding.

---

## 5. Harness Gap

**Current state:** Zero invariants for `comprehensive_elo` exist in any test file. `tests/test_data_source_write_paths.py` checks schema existence but not value correctness.

**Proposed coverage for Layer 2 to build:**

| Test | Rationale |
|------|-----------|
| **Range bounds**: 500 ≤ comp_elo ≤ 5,000 for any non-NULL value | Catch runaway inflation or collapse |
| **Formula consistency**: \|comp_elo − base × pnl\| / base < 0.60 (60% tolerance) | Confirms behavioral never inflates past 1.6× base even with full behavioral=1.4 × pnl=2.5 |
| **Behavioral materialization**: If `behavioral_modifier > 1.05`, then `comp_elo > base × pnl × 1.02` | Detects the current "behavioral stored but not applied" bug — this invariant FAILS today |
| **Population drift**: Mean comp_elo within ±250 of 1,500 each week | Catches sustained inflation from formula bugs |
| **Cross-path consistency**: Traders written by Writer B within 7 days: \|comp_elo − base × pnl\| / base < 0.30 | Confirms dampening stays within expected range |
| **Soft-cap compliance**: comp_elo ≤ 1,500 + resolved_count × 150 for all traders | Ensures Writer A's soft cap was applied |
| **Last-writer detection**: After Sunday run, all is_flagged=1 elo_last_updated within 24h of each other (all touched in same batch) | Detects if Sunday run aborted mid-way |

Note: The **behavioral materialization** test would FAIL on the current codebase. This is intentional — it surfaces the existing bug as a test gate.

---

## 6. Cluster D Connection

**Contamination map finding (from #42):** ~1,346 traders with modifiers at 1.0 across the population.

**Current DB measurement:**

| Segment | Count | Avg comp_elo |
|---------|-------|-------------|
| `is_flagged=1, research_excluded=0`, all modifiers ≈ 1.0 | 15 | 1,500 |
| `is_flagged=1, research_excluded=1`, all modifiers ≈ 1.0 | 16 | 1,500 |
| `is_flagged=0, research_excluded=0`, all modifiers ≈ 1.0 | 104 | 1,500 |
| `is_flagged=0, research_excluded=1`, all modifiers ≈ 1.0 | 100,759 | 1,500 |

The 100,759 non-flagged, excluded traders are the bulk of Cluster D (if the contamination map used all traders). These are traders who:
1. Were never processed by Writer A (scope = `is_flagged=1` only)
2. Were not eligible for Writer B (no closed positions in pnl_cache)
3. Therefore have `comprehensive_elo = 1500` (DB default), `pnl_modifier = 1.0`, `behavioral_modifier = 1.0`

**Connection:** Cluster D is not a formula error — it's a **scope gap**. Writer A and Writer B together reach ~22,563 flagged traders but ignore ~65,000+ non-flagged traders who are nonetheless in the `traders` table with `comprehensive_elo = 1500`. If downstream systems use `comprehensive_elo` for non-flagged traders, they always see 1,500 regardless of actual performance.

The 1,346 figure from #42 likely comes from a different sub-population criterion (possibly `research_excluded=0, is_flagged=1` with old stale scores rather than exactly 1.0, or was measured before today's Sunday run). The clean pool (15 currently) is much smaller after today's write.

---

## 7. Key Findings Summary for Layer 2 (O-7 Design Input)

| Finding | Implication |
|---------|-------------|
| **4 writers, not 3** — Writer D (monitoring cycle) writes comprehensive_elo intra-week | Writer D can overwrite Sunday's values before next Sunday; add to interleaving model |
| **Behavioral multiplier stored ≠ behavioral multiplier applied — CORRECTED: not a key mismatch.** `behavioral_modifier` column (e.g. 1.4) is from Sunday's Writer A. `comprehensive_elo` (= base × pnl) is from Monday's Writer B. They are from DIFFERENT writers at DIFFERENT times. Writer B does NOT write `behavioral_modifier`, so Sunday's value persists as a column artifact while Writer B's `comprehensive_elo` has no behavioral. The apparent contradiction is a temporal artifact, not a formula bug. The behavioral code in `get_trader_global_elo` is correct. | KNOWN INTENTIONAL decision per `monitoring/system_observer.py:2956–2977` (disabled 2026-06-05). Fix = RQ-CONTESTED-001 (July 2026). See Section 9. |
| **Sunday and daily paths produce same empirical result (base × pnl) — CORRECTED: not because formulas match, but because Writer B overwrites Sunday.** Sunday's path correctly computes base × behavioral × pnl. Writer B runs daily and overwrites with base × pnl. The result is indistinguishable from "formulas agree" unless you check timestamps. | DB timestamps prove it: 20,035 traders at Jun 29 08:46:35 (Writer B) vs 2,471 at Jun 28 04:16 (Sunday ELO). Sunday is NOT the last writer for 20,035 traders with closed positions. |
| **Real divergence at base ≥ 2,000** — daily's dampening (0.8x) reduces pnl gain; Sunday doesn't dampen | ~3,500 elite traders could see 5–15% ELO difference between Sunday and daily last-writer states |
| **~~Sunday always overwrites daily~~ CORRECTED: Writer B (daily maintenance) overwrites Sunday** — elo_last_updated timestamps prove June 28 (Sunday ELO, 04:16 UTC) → 2,471 traders; June 29 (Writer B, 08:46:35 UTC) → 20,035 traders. Writer B runs EVERY day at 06:00+ UTC (cron `0 6 * * *`), including Monday after Sunday. For the 20,035 traders with ≥1 closed position, Writer B's Monday run overwrites Sunday's behavioral-inclusive ELO with `base × pnl`. The 2,471 traders without closed positions retain Sunday's write. | **This is the behavioral no-op root cause.** Behavioral IS applied on Sunday for ~2.5–4.5 hrs. Then Monday's Writer B strips it for 20,035 traders by writing `comprehensive_elo = base × pnl`. behavioral_modifier column is untouched by Writer B and retains Sunday's value (1.4), creating the contradiction. |
| **Write B's base_category_elo update is conditional** — only updates if NULL or == 1500.0 | After Sunday sets `base_category_elo = 1499.98`, daily will NOT reset it. Base is preserved across daily writes. |
| **Cluster D is a scope gap** — ~100K non-flagged traders are stranded at 1,500 | Not a formula bug; an intentional scope limit of Writers A and B. Decide whether non-flagged traders should ever receive modifier updates. |
| **Writer C (integrate_behavioral_elo.py) is dead** | Remove or redesign as part of O-7. Do not re-enable as-is; it would apply behavioral without P&L and then get overwritten by Writer B anyway. |
| **No test coverage for formula correctness** | The "behavioral materialization" test would fail today and surface the core bug as a blocking gate. |

---

## 8. Files Referenced

| File | Role |
|------|------|
| `monitoring/elo_bridge.py:469–662` | Writer A: `full_elo_recalculation` |
| `monitoring/elo_bridge.py:330–467` | Writer D: `quick_elo_update_for_traders` |
| `monitoring/elo_bridge.py:208–257` | Writer D: `_batch_store_elo_results` (actual DB write) |
| `scripts/apply_full_elo_modifiers.py:148–270` | Writer B: P&L formula + dampening + guards |
| `scripts/integrate_behavioral_elo.py:213–295` | Writer C: disabled behavioral-only path |
| `scripts/recalculate_comprehensive_elo.py:148–155` | Passes skip-flags to Writer A |
| `scripts/run_sunday_elo.sh` | Shell entry point; hardcodes `--skip-correlation --skip-contrarian --skip-advanced-metrics` |
| `deploy/polymarket-sunday-elo.timer` | `OnCalendar=Sun *-*-* 03:00:00 UTC` |
| `scripts/daily_maintenance.py:58,173–179` | Writer B scheduling; Sunday note |
| `analysis/unified_elo_system.py:1895–1960` | `get_trader_global_elo` — the formula engine |
| `analysis/unified_elo_system.py:682–713` | `_load_behavioral_data` — behavioral cache (root of discrepancy) |
| `analysis/unified_elo_system.py:822–930` | `calculate_behavioral_elo_bonus` — kelly/patience/timing additive bonus |
| `analysis/unified_elo_system.py:1046–1111` | `calculate_behavioral_multiplier` — consistency×diversification×style×activity |
| `monitoring/system_observer.py:2956–2977` | Writer C disable comment; explains why |
| `monitoring/trader_analyzer.py:285–318` | Writer D call site — monitoring cycle |

---

## 9. ROOT-CAUSE REPORT — Behavioral No-Op (Part 2 + Part 3 of Deep Investigation)

**Date of investigation:** 2026-06-29  
**Status:** PROVEN. Change nothing — diagnosis only.

---

### PART 1 — The No-Op: PROVEN

**Population-wide count:**

| Traders | Match `comp_elo ≈ base × pnl` (within 1.0 pt) | Match `comp_elo ≈ base × beh × pnl` |
|---------|-----------------------------------------------|--------------------------------------|
| 17,685 flagged, non-excluded, all modifiers non-null | **17,685 / 17,685 (100%)** | 0 / 17,685 |

**Extreme-modifier evidence (10 traders with behavioral_modifier > 1.3):**

| Address (truncated) | comp_elo | base × pnl | base × beh × pnl | beh_mod | diff (no beh) | diff (with beh) |
|---------------------|----------|------------|------------------|---------|--------------|-----------------|
| 0x47fa4ec...150e | 1690.48 | **1690.48** | 2366.67 | 1.40 | **0.00** | 676.19 |
| 0x01da955...4b7b | 1954.02 | **1954.02** | 2735.63 | 1.40 | **0.00** | 781.61 |
| 0x66892ef...3cc6 | 1500.00 | **1500.00** | 2100.00 | 1.40 | **0.00** | 600.00 |
| 0xb951481...a65d | 2390.38 | **2390.38** | 3282.50 | 1.37 | **0.00** | 892.12 |

All 15 extreme-modifier traders: `diff_no_beh = 0.0`, `diff_with_beh = 300–900`. The behavioral column diverges from comprehensive_elo by 300–900 ELO points. **Behavioral is definitively NOT in comprehensive_elo.**

---

### PART 2 — Mechanism: PROVEN

**The contradiction resolved:**

`behavioral_modifier = 1.4` is stored from Sunday's write (04:16 UTC June 28).  
`comprehensive_elo = base × pnl = 1690` is stored from Writer B's write (08:46:35 UTC June 29).  
These are from **two different writers at two different times.** There is NO contradiction — they are independent columns written independently.

**DB timestamp proof:**

| Write date | Trader count | Time window | Writer |
|------------|-------------|-------------|--------|
| 2026-06-28 | 2,471 | 04:16:53 – 04:16:54 UTC | Writer A (Sunday ELO, `full_elo_recalculation`) |
| 2026-06-29 | **20,035** | **08:46:35** (exact, all same second) | **Writer B (`apply_full_elo_modifiers.py`)** |

**The causal chain:**

```
Sun Jun 28, 03:00 UTC
  → Sunday ELO timer fires
  → full_elo_recalculation() for 22,650 traders
  → per-trader: comprehensive_elo = get_trader_global_elo(apply_behavioral=True, apply_pnl=True)
                                   = base × behavioral × pnl  (e.g. 1500 × 1.4 × 1.127 = 2367)
  → per-trader: behavioral_modifier = calculate_behavioral_multiplier() = 1.4 (stored separately)
  → DB write at 04:16:53 UTC: {comprehensive_elo=2367, behavioral_modifier=1.4, elo_last_updated=Jun28 04:16}
  → 22,650 traders updated. Done at ~04:17 UTC.

Sun Jun 28, 06:00 UTC
  → daily_maintenance.py fires (cron: 0 6 * * *)
  → step 24: apply_full_elo_modifiers.py
  → reads base_category_elo from DB (=1499.98, set by Sunday ELO)
  → formula: new_elo = base + base × (pnl_mult - 1.0) × dampening
             = 1499.98 × pnl_mult  (since base < 2000, dampening = 1.0)
             = 1499.98 × 1.127 = 1690.48
  → DB write at ~08:46 UTC Jun 28: {comprehensive_elo=1690, pnl_modifier=1.127, elo_last_updated=Jun28 ~08:46}
  → Does NOT write behavioral_modifier (stays 1.4 from 04:16)
  → 20,035 traders with ≥1 closed position updated. Behavioral STRIPPED.

Mon Jun 29, 06:00 UTC
  → daily_maintenance.py fires again
  → step 24: apply_full_elo_modifiers.py (AGAIN)
  → same formula, same result
  → DB write at 08:46:35 UTC Jun 29: {comprehensive_elo=1690, pnl_modifier=1.127, elo_last_updated=Jun29 08:46:35}
  → CURRENT STATE IN DB
```

**Writer B SQL (does NOT write behavioral_modifier):**
```python
# apply_full_elo_modifiers.py lines 240–252
SET comprehensive_elo = ?,   ← overwrites Sunday's 2367 with 1690
    pnl_modifier = ?,         ← overwrites
    elo_last_updated = ?,     ← overwrites
    base_category_elo = CASE  ← conditionally preserved (stays 1499.98 since ABS(1499.98-1500) > 0.0001)
        WHEN base_category_elo IS NULL OR ABS(base_category_elo - 1500.0) <= 0.0001
        THEN ?
        ELSE base_category_elo
    END
WHERE address = ?
-- behavioral_modifier NOT in this UPDATE — stays at 1.4 from Sunday
```

**Why `calculate_behavioral_multiplier()` returns 1.4 but comprehensive_elo ≠ base × 1.4 × pnl:**  
Because they were computed at different times by different writers. The behavioral_modifier column is a SNAPSHOT from Sunday's `full_elo_recalculation`. The comprehensive_elo column is the CURRENT value from Writer B's daily overwrite. They are not coupled.

---

### PART 3 — Timeline

**Was behavioral EVER applied?** YES.

Sunday's `full_elo_recalculation` correctly applies behavioral via `get_trader_global_elo(apply_behavioral=True)`. The code path is sound:
- `analysis/unified_elo_system.py:1933–1940`: `adjusted_elo *= behavior_data['combined_multiplier']`
- Behavioral cache confirmed populated (June 28 run log line 49144: 39 keys present, including `bet_size_consistency`, `diversification_score`, etc.)
- Behavioral IS applied for the ~4.5-hour window after Sunday timer finishes until daily maintenance step 24 runs

**When does behavioral get stripped?** Every day, step 24 of `daily_maintenance.py` runs `apply_full_elo_modifiers.py`. For all 20,035 traders with ≥1 closed position, `comprehensive_elo` is overwritten with `base × pnl`. Behavioral is in comprehensive_elo for ~4.5 hours per week (Sunday 04:17 – Sunday ~08:46 UTC). The rest of the week it's stripped.

**Was this known?** YES. `monitoring/system_observer.py:2956–2977`:
> "DISABLED 2026-06-05: behavioral_modifier is written here but silently discarded by apply_full_elo_modifiers.py which overwrites comprehensive_elo without reading it. Intentionally disabled until comprehensive_elo formula is redesigned (RQ-CONTESTED-001, July 2026)."

This confirms the conflict was documented on 2026-06-05 and a fix was deferred to July 2026. The system_observer's Writer C was disabled as a consequence.

**Is commit `bd82fd7` implicated?** NO. `bd82fd7` added kelly/patience/timing snapshot write-back — the commit message explicitly states "ELO outputs byte-identical." It added 18 lines to elo_bridge.py that only write `kelly_alignment_score`, `patience_score`, `timing_score` columns (never touched by Writer B). The behavioral no-op is pre-existing, first documented 2026-06-05.

**Prior state (before RQ-CONTESTED-001 was documented):** No evidence behavioral was ever consistently applied. Writer B has been in daily_maintenance since before June 2026. Behavioral analysis only produces valid output when the behavioral cache is warm (requires `analyze_all_traders()` call). The design always had Writer B overwriting Writer A's output the same day.

---

### Summary: The Complete Picture

| Question | Answer |
|----------|--------|
| **No-op: PROVEN?** | YES — 17,685/17,685 (100%) traders match `comp_elo = base × pnl`, with zero matching `base × beh × pnl`. Extreme modifiers (1.4x) deviate 300–900 pts from what comp_elo should be if behavioral were applied. |
| **Mechanism** | Writer B (`apply_full_elo_modifiers.py`, daily maintenance step 24) overwrites `comprehensive_elo = base × pnl` every day. It does NOT read or apply behavioral. Sunday's behavioral-inclusive write is undone every day at 08:46 UTC. |
| **The "contradiction"** | `behavioral_modifier = 1.4` and `comprehensive_elo = base × pnl` are from DIFFERENT writers at DIFFERENT times. No contradiction — they're independently sourced. The behavioral_modifier column is a Sunday artifact; comprehensive_elo is a Monday artifact. |
| **Timeline** | Was behavioral ever applied? YES — for ~4.5 hrs/week. This is pre-existing; documented in system_observer.py as of 2026-06-05 (RQ-CONTESTED-001). |
| **bd82fd7 implicated?** | NO. Snapshot write-back only; formula byte-identical per commit message. |
| **Behavioral code correct?** | YES — `get_trader_global_elo` code is correct. `calculate_behavioral_multiplier` returns 1.4. The bug is in the WRITER SEQUENCE, not the formula. |
| **Fix direction** | Remove Writer B from daily maintenance OR make Writer B read `behavioral_modifier` from DB and apply it alongside P&L (the RQ-CONTESTED-001 design fix, deferred to July 2026). |

---

*Root-cause report appended 2026-06-29. Investigation complete — no code changes made.*
