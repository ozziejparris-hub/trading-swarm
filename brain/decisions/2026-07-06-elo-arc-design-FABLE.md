# ELO Arc Design — Unified comprehensive_elo Architecture (RQ-CONTESTED-001 / O-7)

**Date:** 2026-07-06
**Author:** Claude Fable (design session, deep reasoning)
**Status:** DESIGN FOR HUMAN REVIEW — no production code changed, ELO subsystem remains FROZEN. **Stage 0 COMPLETE 2026-07-13** (0a redefined+passing+write-time-corrected, 0b resolved `W_beh=0`, 0c done, 0d harness OBSERVE-mode invariants landed — see §5). **Stage 1 partially done 2026-07-13**: pure formula built and proven zero-diff against production (unit tests + live-data validation, both green) — see §5. Still open: the `elo_shadow` side table, nightly shadow job, and human-reviewed delta report.
**Inputs:** `2026-06-29-comprehensive-elo-writer-map.md` (O-6, verified against live code today), `2026-06-29-overhang-ledger.md` (O-5/O-6/O-7), `2026-06-30-str002-thesis-cell-analysis.md` (downstream cost), `system_observer.py:2956` (freeze rationale), live DB verification queries run 2026-07-06 (Appendix A), **independent re-verification of Claims 1–2 run 2026-07-06 same day (see Correction section below)**
**Resolves:** RQ-CONTESTED-001 (deferred 2026-06-05 → July 2026 — this is that deliverable)

---

## CORRECTION (2026-07-06, same day — independent re-verification)

This document's two load-bearing claims were independently re-verified against live code and the live DB before being banked as plan of record. **Claim 1 (Writer D fully dead, exactly 2 live writers) was CONFIRMED** — no exception found; see Appendix B below. **Claim 2 (Stage 2's output-neutrality) was FALSE AS ORIGINALLY WRITTEN** — three concrete discrepancies were found between "canonical formula at `W_beh=0`" and actual production Writer B. This section documents what was wrong, the fix, and re-confirms the corrected claim. §2.1, §2.4, §2.5, §4.1, and §5 (Stages 2–3) below have been revised in place to match; this section is the changelog.

**What broke, quantified against today's live Writer-B population (n=20,054):**

1. **Bonus leak (material — 85% of the population).** The original formula scaled the behavioral *multiplier* by `W_beh` but scaled the kelly/patience *bonus* by a separate, independent constant `W_bonus` ("1.0 at launch"). Setting `W_beh=0` therefore zeroed the multiplier term but left the bonus term fully active. Measured: **17,053 / 20,054 traders (85%) with resolved ≥ 10 would receive a nonzero bonus injection averaging +9.37 points**, purely from deploying the supposedly-neutral Stage 2. Not neutral.
2. **Soft cap (material, small population).** The original formula applied Writer A's soft cap (`1500 + resolved×150`) unconditionally, including at `W_beh=0`. Writer B's actual production code has **no soft cap at all** — only the 3,500 hard cap. Measured: **9 real traders today** exceed the soft cap while under the hard cap; canonical-at-`W_beh=0` would have silently *lowered* their values by **5.1 to 297.2 points** versus what Writer B actually wrote this morning.
3. **Floor at 400 (latent, not currently binding, but a real difference).** Writer B has no floor; the original formula added one unconditionally. Checked: today's minimum raw Writer-B value is 479.0, so this specific difference doesn't currently change any output — but it is a genuine, unacknowledged behavioral difference from "Writer B, exactly," not an algebraic identity as claimed.

**The fix, applied below:**

- **Bonus leak →** `W_bonus` is **retired as an independent knob**. The bonus term is now scaled by the *same* `W_beh` as the multiplier term (§2.1). At `W_beh=0`, both the multiplicative term and the bonus term are exactly zero — `beh_gain = 0` in full, not just its multiplicative half. This is the direct fix: one behavioral dimension, one weight, both halves zero together.
- **Soft cap and floor →** these are **no longer applied unconditionally by the pure formula**. The formula now takes explicit `apply_soft_cap` / `apply_floor` parameters (§4.1). **Stage 2 calls with both `False`** (Writer B's own bounds only: hard cap 3,500, nothing else) — genuinely reproducing Writer B's existing bounds, not Writer A's. **Stage 3 flips both to `True`** (where Sunday's output is already changing for other reasons, and the soft cap is native to Writer A's own history anyway).

**Re-verified corrected claim — term by term, at `W_beh=0`, `apply_soft_cap=False`, `apply_floor=False`:**

| Term | Writer B (production) | Canonical, corrected | Match? |
|---|---|---|---|
| P&L gating (confidence cap, thin-sample gate, loss amplification) | `apply_full_elo_modifiers.py:159-191`, verbatim | Same three guards, same order, same constants | ✓ identical |
| Behavioral multiplier contribution | none | `base × (beh_applied − 1.0)` where `beh_applied = 1.0 + (beh_mult−1.0)×0 = 1.0` → contributes 0 | ✓ zero |
| Behavioral bonus contribution | none | `bonus × W_beh = bonus × 0 = 0` | ✓ zero (was the bug; now fixed) |
| Dampening | `0.60 / 0.80 / 1.00` by base, applied to `base×(mult−1)` | identical thresholds, applied to `pnl_gain + 0` = `pnl_gain` | ✓ identical |
| Soft cap | none | `apply_soft_cap=False` → not applied | ✓ identical (fixed; was previously applied) |
| Hard cap | `min(new_elo, 3500.0)` | `min(comp, 3500)` | ✓ identical |
| Floor | none | `apply_floor=False` → not applied | ✓ identical (fixed; was previously applied) |

**Result: at these settings, `comp = base + base×(pnl_gated−1.0)×damp, capped at 3500` — exactly Writer B's formula, term for term, with no residual difference.** Re-running the same live-population checks that found the original 3 discrepancies (Appendix B below) against the corrected formula: bonus contribution is 0 for all 20,054 traders (not 17,053 nonzero); soft cap is not applied so the 9-trader discrepancy disappears; floor is not applied so it's moot in Stage 2 by construction, not by luck. **Stage 2's dry-run would now produce byte-identical `comprehensive_elo` and `pnl_modifier` values against today's actual Writer B output** — the property Stage 2 requires. This closes the gap; the corrected design is accurate as plan of record.

**Net effect on the design:** the architecture, the migration stage count (still 6), the harness spec, and the O-5 sequencing are unchanged — this was a formula-internals correction, not a structural one. The only substantive change to the *shape* of the design is that Stage 2 now genuinely does nothing but plumbing (bounds move to Stage 3, where they belong conceptually anyway — Stage 3 is where Sunday's output changes for other reasons).

---

## 0. Executive summary

`comprehensive_elo` — the composite rating that gates LEGENDARY/ELITE/QUALIFIED tiers and feeds the signal layer — is written by multiple writers with different formulas, and its behavioral component is stripped daily (proven population-wide; re-verified today: 19,944/19,944 of today's Writer-B population satisfy `comp = base × pnl` exactly). This design:

1. **Picks a canonical formula**: Writer B's dampened-additive-gains structure, extended with a bounded behavioral gain term — NOT Writer A's multiplicative compounding. Behavioral enters as a compressed, thin-sample-gated, dampened additive gain, never as a raw multiplier on top of P&L.
2. **Re-incorporates behavioral behind a validation gate**: the architecture ships with behavioral structurally wired but weight-parameterized (`W_beh`); a read-only predictiveness study decides the launch value. If behavioral proves non-predictive, `W_beh` stays 0 and the redesign still delivers its main value (single formula, single-writer semantics, harness coverage).
3. **Unifies to one formula implementation** (a pure function in a new module) called by both surviving cadences (Sunday full pass + daily incremental pass), with an atomic full-column-set write helper — killing the entire class of "columns from different writers at different times" artifacts.
4. **Migrates in 6 staged, individually-reversible steps**, with an output-neutral structural cutover (Stage 2–3) separated from the single formula change (Stage 4), which is togglable by one constant.
5. **Specifies 8 harness invariants**, including a formula-reproducibility check that mechanically enforces single-writer semantics forever.
6. **Corrects the O-5 sequencing assumption**: most of O-5 does NOT block O-7. The real precursors are narrower — and one of them (O-15, positions-table integrity) was fixed today and is currently self-healing, which sets the earliest safe date for migration baselines.

---

## 1. Verified current state (2026-07-06) — what changed since the writer map

The writer map (2026-06-29) was re-verified against live code and DB today. Three findings, one of them significant:

**1a. Writer D is DEAD — the map is outdated on this point.** Commit `ca30c07` (2026-07-02, the O-13 stall fix) deleted `check_market_resolutions()` from `trader_analyzer.py`, and the `quick_elo_update_for_traders()` call site was **inside that deleted function** (confirmed via `git show ca30c07`: the call sat in the post-resolution "Step 3" block). `quick_elo_update_for_traders` still exists in `elo_bridge.py:330` but has **zero production callers** — only archive scripts and the manual `--quick-update` CLI branch (`elo_bridge.py:794`) reach it. *This was an unintended side effect of O-13, not a deliberate ELO change — but it simplifies this design substantially: the live writer set is now exactly A + B.*

**1b. The no-op mechanism holds exactly, today.** Live re-verification (Appendix A):
- 20,054 flagged traders last written 2026-07-06 (Writer B, this morning's maintenance): **19,944/19,944** of those with complete modifier columns satisfy `|comp − base × pnl| < 1.0` — 100%, matching the map's 2026-06-29 finding.
- 2,491 flagged traders retain Sunday 2026-07-05's write (Writer A — traders without closed positions, whom Writer B never touches). For these, I verified the **full Sunday formula** including terms the map's Section 1 couldn't isolate: `min((base × beh_mult + bonus) × pnl, 1500 + resolved×150)` reproduces **2,435/2,476 (98.3%)** within 2 ELO points, using the stored kelly/patience/timing columns to reconstruct the step-function bonus. (The 41 misses are consistent with adaptive-weight edge cases where a sub-score is NULL; not investigated further — they don't change any conclusion.) This confirms the map's Section 9 correction with higher precision than before: **Sunday's behavioral code path works; Writer B strips it daily.**

**1c. Current population (flagged):** n=26,806 with non-NULL comp; mean 1,400.5; range 479–3,315; 4,238 at ≥1,550; 1,393 at ≥1,800 (ELITE gate). Modifier distributions (flagged, non-excluded): behavioral mean 0.999, range [0.80, 1.40] (≈8,026 above 1.05); advanced mean 1.084, range [1.00, 1.10]; pnl mean 0.932, range [0.40, 2.20].

**1d. Also confirmed:** `run_sunday_elo.sh` still passes `--skip-advanced-metrics`, so `advanced_modifier` is **stored but never applied** on any live path (Writer D, the only path that applied it, is dead) — the same stored-but-not-applied artifact class as behavioral. And `apply_full_elo_modifiers.py:152` writes `elo_last_updated` via `datetime.now().isoformat()` (T-separated) — **this is the O-3 timestamp-debt generator** (23,518 non-canonical rows, the entire remaining O-3 count).

---

## 2. DECISION 1 — The canonical formula

### 2.1 The decision

```
# Inputs (per trader):
#   base       = base_category_elo (re-derived Sunday; read from DB daily)
#   beh_mult   = behavioral multiplier, stored range [0.80, 1.40]
#   bonus      = behavioral ELO bonus, stored range [−100, +100] (kelly/patience; timing EXCLUDED — see 3.4)
#   pnl_raw    = P&L multiplier from positions table [0.40, 2.50]
#   closed     = closed_positions count (from pnl_cache / positions table)
#   resolved   = resolved_trades_count
#
# apply_soft_cap, apply_floor: bool, caller-controlled (NOT tunable weights — see
# Correction section above and §4.1/§5). Stage 2 = (False, False); Stage 3+ = (True, True).

# P&L gain — Writer B's guards, verbatim (unchanged from production):
pnl_gated = min(pnl_raw, confidence_cap(closed))        # 1.30–2.20 by closed count
if pnl_gated > 1.0 and resolved < 10: pnl_gated = 1.0   # thin-sample gate
if pnl_gated < 1.0 and base >= 2000:                    # asymmetric loss amplification
    pnl_gated = 1.0 − (1.0 − pnl_gated) × 1.30
pnl_gain = base × (pnl_gated − 1.0)

# Behavioral gain — bounded and gated. CORRECTED 2026-07-06: both the multiplicative
# term AND the bonus term are scaled by the SAME weight (W_beh) so they zero together.
# (Originally the bonus was scaled by an independent W_bonus that stayed 1.0 regardless
# of W_beh — this was the bug the independent re-verification caught; see Correction
# section above. W_bonus no longer exists as a separate knob.)
if resolved < 10:
    beh_gain = 0.0                                      # same thin-sample philosophy as P&L
else:
    beh_applied = 1.0 + (beh_mult − 1.0) × W_beh        # W_beh = 0.5 → effective range [0.90, 1.20]
    beh_gain    = base × (beh_applied − 1.0) + bonus × W_beh   # SAME W_beh scales both halves

# Compose additively, dampen the TOTAL gain:
damp = 0.60 if base >= 2500 else 0.80 if base >= 2000 else 1.00
comp = base + (pnl_gain + beh_gain) × damp

# Bounds — applied conditionally, NOT baked into the formula unconditionally:
if apply_soft_cap:
    comp = min(comp, 1500 + resolved × 150)             # Writer A's soft cap — Stage 3+ only
comp = min(comp, 3500)                                  # Writer B's hard cap — always, all stages
if apply_floor:
    comp = max(comp, 400)                               # absolute floor — Stage 3+ only (today's empirical min: 479)
```

Equivalently: **`comp = WriterB_today(base, pnl) + damp × beh_gain`** at `apply_soft_cap=apply_floor=False` — the canonical formula is exactly today's production Writer B output plus a bounded, dampened behavioral delta. This decomposition is deliberate: it makes the migration previewable (§5, Stage 1) and the behavioral term independently toggleable (`W_beh = 0` reproduces today's values exactly, **now including the bonus** — see Correction section above for why this needed fixing).

### 2.2 Justification against the three criteria

**(a) No high-ELO inflation.** The behavioral delta is bounded at `damp × (0.20 × base + 100)`: +400 at base 1,500; +464 at base 2,400 (where damp=0.8 bites). Compare Writer A's theoretical multiplicative form at base 2,400 with beh 1.3: **+720 from the multiplier alone, before the bonus and before P&L compounds on top of it**. Dampening applies to the *total* gain, so behavioral and P&L cannot jointly escape it. Both caps survive: Writer B's hard 3,500 and Writer A's resolved-indexed soft cap (which binds meaningfully — 206 of the current Sunday population sit exactly on it).

**(b) Behavioral actually incorporated.** A trader with beh 1.2 / bonus +40 at base 2,400 gains +224 over today's pnl-only value (worked example H below) — most of a tier width where it matters for ELITE gating, which is precisely the STR-002 complaint being fixed.

**(c) Sane population values.** Population behavioral mean is 0.999 — the multiplier term is near-zero-mean by construction, so the population mean shift ≈ mean(bonus × damp) among resolved≥10 traders. This is measured exactly in the shadow stage before anything ships (§5, Stage 1); with timing excluded (§3.4), the bonus loses its flat +10-for-everyone offset, further centering it.

### 2.3 Rejected alternatives (and why)

**Rejected: Writer A's theoretical formula (multiplicative behavioral × pnl, soft cap only).** Three reasons. (i) *Compounding tails*: multiplying two noisy estimates inflates variance superlinearly — beh 1.4 × pnl 2.5 = 3.5× base at the joint extreme; each estimate's error amplifies the other's. Additive gains bound each dimension's contribution independently and auditable-y. (ii) *Backwards risk-weighting*: a multiplicative behavioral term contributes proportionally MORE ELO at higher base — ±40% of 2,400 is ±960 points — exactly where inflation does most tier-gating damage, and no behavioral estimate is ±960-points reliable at any sample size. (iii) *Un-gated P&L*: Writer A applies raw `pnl_raw` with no confidence cap and no thin-sample gate — a 1-closed-position trader can get 2.5×. Writer B's gates are simply better engineering, and the empirical evidence (worked example T below) shows what they prevent.

**Rejected: Writer B unchanged (permanent behavioral exclusion).** Defeats the tier system's premise. The STR-002 evidence (§3.1) shows pnl-momentum-gated tiers performing at 27.3% (ELITE) and 11.8% (QUALIFIED) — keeping comprehensive_elo a P&L proxy while calling its tiers "skill" is the status quo failure mode this design exists to end.

**Rejected: dampened formula but behavioral as a multiplier on the dampened result** (`B_output × beh_applied`). Re-introduces compounding (behavioral would multiply P&L gains), and makes the behavioral delta base-and-pnl-dependent, breaking the clean `B + delta` decomposition that the migration relies on.

### 2.4 Worked examples

**Revised 2026-07-06** (corrected bonus scaling — see Correction section above; numbers below supersede the original pass). `W_beh = 0.5` scales *both* the behavioral multiplier and the bonus (no separate `W_bonus`); timing excluded from bonus. `apply_soft_cap=apply_floor=True` for L/M/H/T/X below — i.e. these show **Stage 4 (fully-launched) behavior**, not Stage 2 (which is deliberately bounds-free per the Correction section, and is byte-identical to B-today by construction, not shown as a separate case here). "A-theor" = Writer A's coded formula; "B-today" = production Writer B; "U" = canonical.

| Case | Inputs | A-theor | B-today | **U (canonical)** | U − B |
|---|---|---|---|---|---|
| **L** low base, good behavior | base 1200, beh 1.20, bonus +40, pnl 1.5, closed 5, resolved 15 | (1200×1.2+40)×1.5 = **2220** | 1200+1200×0.5 = **1800** | gains 600+120+20 = 740 → **1940** | **+140** |
| **M** mid base, poor behavior | base 1600, beh 0.90, bonus −20, pnl 1.8, closed 10, resolved 25 | (1440−20)×1.8 = **2556** | 1600+1600×0.8 = **2880** | gains 1280−80−10 = 1190 → **2790** | **−90** |
| **H** high base, good behavior | base 2400, beh 1.20, bonus +40, pnl 1.4, closed 25, resolved 60 | (2880+40)×1.4 = **4088** | 2400+2400×0.4×0.8 = **3168** | gains 960+240+20 = 1220 ×0.8 → **3376** | **+208** |
| **T** thin sample | base 1500, beh 1.40, bonus +100, pnl_raw 2.5, closed 1, resolved 4 | (2100+100)×2.5 = 5500 → soft cap **2100** | conf cap 1.30, thin-gate → mult 1.0 → **1500** | pnl AND behavioral both thin-gated → **1500** | **0** |
| **X** joint extreme | base 2400, beh 1.40, bonus +100, pnl_raw 2.5, closed 25, resolved 60 | 3460×2.5 = **7975** (soft cap 10,500 doesn't bind!) | 4704 → hard cap **3500** | gains 2880+480+50=3410 ×0.8=2728 → 5128 → hard cap **3500** | 0 (both capped) |

Readings: **L/M/H** — U discriminates in both directions (good behavior +140/+208, poor behavior −90) while staying between B's conservatism and A's inflation; these deltas are smaller than the original (pre-correction) pass's +160/+224/−100 because the bonus half now shares the same 0.5 compression as the multiplier half, instead of contributing at full strength — a direct, visible consequence of the fix. **T** — the thin-sample gate now covers behavioral too (decision: a 4-resolved-trade trader's "consistency" is noise; without this, T would jump on style metrics alone). **X** — A-theoretical produces 7,975 (its soft cap is useless at high resolved counts: 1500+60×150 = 10,500); B and U both cap at 3,500 — at the joint extreme the cap absorbs discrimination, which is acceptable: exactly 0 traders currently exceed 3,315.

### 2.5 Sub-decisions inside the formula

- **`advanced_modifier`: EXCLUDED from formula v1, still computed and stored.** It's currently stored-but-never-applied (§1d), its range is tight (1.00–1.10 — low discriminating power), and its underlying modules only started returning real data in April 2026. Adding a third live dimension mid-migration multiplies validation surface for little gain. Revisit after behavioral has post-launch evidence. *Alternative rejected: include it now as another additive gain — more moving parts in the exact stage where we most need attributable diffs.*
- **Floor at 400 (new, explicit — Stage 3+ only, see Correction section above).** Worst-case additive composition can reach ~350 at low base (P&L floor 0.40 + behavioral floor + bonus floor); today's empirical min is 479, and the independent re-verification confirmed today's minimum *raw, unfloored* Writer-B value is also 479.0 — so the floor is currently dormant, not currently binding, and is deliberately staged to Stage 3 (alongside the soft cap) rather than Stage 2, so Stage 2 reproduces Writer B's actual bounds (hard cap only) with no unacknowledged behavioral difference. *Judgment call, flagged.*
- **`W_beh = 0.5` (i.e., behavioral multiplier's applied range compressed [0.80,1.40] → [0.90,1.20], and — after the 2026-07-06 correction — the bonus term's effective range compressed [−100,+100] → [−50,+50] too, since both halves now share one weight).** Rationale: P&L is the system's declared dominant factor ("ROI-FIRST"); behavioral measures process (consistency/diversification/style/activity), not outcomes, and should not be able to out-contribute the outcome measure. At 0.5, max behavioral gain (0.20×base + 50) stays below max gated P&L gain (up to 1.2×base). **This is a tunable judgment call, not a derived constant** — the Stage 0 validation study (§3.3) is the mechanism for revising it before launch. (`W_bonus` no longer exists as a separate knob — see Correction section above; it was the source of the Stage-2-neutrality bug the independent re-verification caught.)

---

## 3. DECISION 2 — The behavioral question

### 3.1 Was disabling it correct?

**Yes, as a stopgap — the 2026-06-05 disable was the right call at the time.** Writer C applied behavioral *without* P&L, then Writer B overwrote with P&L *without* behavioral; letting them fight produced values that depended on write timing rather than trader quality. Disabling the weaker writer pending redesign was correct triage.

**But permanent exclusion is not defensible.** The tier system's premise — and STR-002's registry description ("6-dimensional ELO") — is a skill measure. What actually gates ELITE/QUALIFIED today is a P&L-momentum proxy, and the measured result is ELITE 27.3%, QUALIFIED 11.8% accuracy (vs. the 60% gate), while the only tier gated on something other than comprehensive_elo (LEGENDARY, via geo_elo) went 1/1.

### 3.2 Honest evidence assessment (proven vs. inferred)

**Proven:** comprehensive_elo is base×pnl for ~89% of flagged traders (100% of the Writer-B population); STR-002's comprehensive-gated tiers underperform badly; the behavioral computation pipeline works (Sunday's writes verify against the full formula at 98.3%).

**Inferred, NOT proven:** that `behavioral_modifier` is *predictive of outcome accuracy*. The STR-002 evidence shows pnl-only gating is bad; it does not show behavioral specifically is good (LEGENDARY's 1/1 success is n=1 and gated on domain-specific base ELO, not behavioral). **No direct validation of behavioral's predictive value exists anywhere in the investigation record.**

### 3.3 The resolution: re-incorporate behind a validation gate

This design deliberately decouples two decisions that have been conflated:

1. **The architecture decision** (unify writers, one formula, atomic writes, harness) — justified regardless of behavioral's value. Ships in every scenario.
2. **The empirical bet** (behavioral improves tier quality) — gets a cheap, read-only test *before* launch: **Stage 0 validation study**: for traders with ≥10 resolved trades, regress resolved-trade accuracy (and STR-002-relevant hit rates) against stored `behavioral_modifier` and bonus components, controlling for base ELO and pnl_modifier. Three outcomes:
   - Clear positive signal → launch `W_beh = 0.5` as designed.
   - Weak/noisy signal → launch smaller (0.25), revisit with more data.
   - Zero/negative signal → launch `W_beh = 0`: identical values to today, but the architecture is unified and behavioral becomes a one-constant flip whenever evidence arrives.

This converts "the crux" from an argument into a measurement. **The migration does not depend on the answer.**

**RESOLVED 2026-07-12 — `W_beh = 0`.** Stage 0b ran exactly the study scoped above (market-relative edge instead of raw win rate — win rate turned out to correlate with entry price at r=0.98, i.e. it's mostly favorite-buying, not skill — see the study for why that substitution mattered). Result: `behavioral_modifier`'s incremental R² over `base_category_elo + pnl_modifier` is 0.00018 (n=21,218, well-powered enough to detect R² down to that same floor — a clear null, not an underpowered non-finding); the one marginally-significant coefficient has the wrong sign and doesn't replicate in a higher-reliability subsample. Decomposition into `kelly_alignment_score`/`patience_score` found both tiny-to-null individually, and — separately — both *negatively* correlated with the `behavioral_modifier` composite itself (r≈−0.59), i.e. the current behavioral columns aren't internally coherent as a construct, independent of the predictiveness question. Full study, methodology, and all numbers: `2026-07-12-behavioral-validation-study-STAGE-0B.md` (commit `37d2171`).

**This lands the "zero/negative signal" branch exactly as anticipated in this section**: architecture ships unchanged, behavioral off, one-constant flip preserved. **Consequence for Stage 2 specifically**: at `W_beh=0` the canonical formula (§2.1) is byte-identical to today's live Writer B by construction (see the Correction section above) — so Stage 2 is now known, not just designed, to be a pure plumbing unification with zero value changes, not a live behavioral-weight decision bundled into the migration. This lowers Stage 2's risk profile relative to how this design doc originally scoped it.

### 3.4 The timing term: EXCLUDE from the bonus while timing is disabled

CLAUDE.md warning #3: timing quality is intentionally disabled; all traders receive a neutral score. A neutral score (0.5) lands in the bonus step function's `0.4 ≤ t < 0.6` band → **+10 flat for every trader** — a constant offset with zero discrimination, i.e., pure inflation. Fix: pass `has_timing=False` into the bonus computation (its adaptive-weight system then rebalances kelly/patience to 50/50, already-coded behavior). Re-enable only when the timing column actually exists. *This also removes a +10×damp population mean shift that would otherwise pollute the Stage 4 drift measurement.*

---

## 4. DECISION 3 — The single-writer architecture

### 4.1 The core move: one formula, one write shape

**New module: `analysis/comprehensive_elo_formula.py`** — a pure function, no DB I/O, no imports from the ELO system:

```python
def compute_comprehensive_elo(base, beh_mult, bonus, pnl_raw, closed, resolved,
                              w_beh=W_BEH,
                              apply_soft_cap=True, apply_floor=True) -> EloResult
# EloResult: comp, pnl_gated, beh_applied, gain_pnl, gain_beh, damp, cap_applied — full audit trail
#
# CORRECTED 2026-07-06 (independent re-verification): no separate w_bonus parameter —
# the bonus term is scaled by the same w_beh as the multiplier (both halves of the
# "behavioral" dimension zero together). apply_soft_cap / apply_floor are explicit
# bounds-control params, not tunable weights: Stage 2 calls with both False (reproduces
# Writer B's actual bounds — hard cap only); Stage 3+ calls with both True. See the
# Correction section at the top of this document and §5 below.
```

**New write helper (in `monitoring/database.py`): `write_elo_result(conn, address, result, components)`** — writes the **full column set atomically, every time**: `comprehensive_elo, base_category_elo, behavioral_modifier, advanced_modifier, pnl_modifier, kelly_alignment_score, patience_score, timing_score, elo_last_updated` (canonical timestamp format — the O-3 writer fix lands here). **No caller may write any subset.** This single rule kills the entire artifact class that produced RQ-CONTESTED-001: "behavioral_modifier from Sunday, comprehensive_elo from Monday" becomes structurally impossible, because every write refreshes every column from one coherent computation.

### 4.2 What each writer becomes

| Writer | Today | Becomes |
|---|---|---|
| **A** — Sunday full recalc (`elo_bridge.full_elo_recalculation`) | Own formula: `(base×beh+bonus)×pnl`, soft cap | **Survives as the weekly full pass**: re-derives base ELO from trade history, refreshes behavioral + pnl caches, then calls `compute_comprehensive_elo` + `write_elo_result`. Its formula internals are deleted. |
| **B** — daily (`apply_full_elo_modifiers.py`) | Own formula: `base + base×(pnl−1)×damp`, no behavioral | **Survives as the daily incremental pass**: refreshes pnl for traders with closed positions, **reads behavioral components from DB** (Sunday snapshots), calls the same `compute_comprehensive_elo` + `write_elo_result`. |
| **C** — `integrate_behavioral_elo.py` | Disabled dead code since 2026-06-05 | **DELETE.** Its design flaw (behavioral without P&L) is superseded; it's also a rogue writer of `resolved_trades_count` (§7.1). The system_observer disable-comment block goes with it. |
| **D** — `quick_elo_update_for_traders` | Dead since 2026-07-02 (O-13 side effect, verified §1a) | **Retire in cleanup stage**: remove the method, `_process_trader_chunk`, `_batch_store_elo_results`, and the `--quick-update` CLI branch. *Decision: do NOT rebuild a monitoring-cycle ELO writer — resolution-driven freshness is already handled by requeue → pnl worker → next daily pass; a third cadence is writer-proliferation, the exact disease.* |
| **E** — simulation/archive | Guarded (a5f9bb7) | Out of scope, unchanged. |

### 4.3 Two cadences, one writer — why keep the daily pass at all

*Alternative rejected: Sunday-only writes (writer map option (a)).* STR-002 consumes comprehensive_elo daily for live tier-gating; killing the daily pass means up to 6-day-stale P&L in tier decisions for the ~20K traders with position flow — a real signal-quality regression to fix a purity concern. The disease was never "two schedules"; it was "two formulas." After Stage 3, both cadences produce **identical values for identical inputs** — last-writer-wins becomes harmless, because both writers are the same function.

Division of labor (unchanged in spirit from today): **base ELO and behavioral re-derive weekly** (slow-moving, expensive — behavioral cache requires `analyze_all_traders()`); **P&L refreshes daily** (fast-moving, cheap). The daily pass reads Sunday's stored `base_category_elo` and `behavioral_modifier` — up to 6-day staleness on the slow components is the accepted cost, now applied *consistently* instead of by-accident-of-writer.

### 4.4 `get_trader_global_elo` and its flag-soup

The `apply_behavioral/apply_advanced/...` flag interface in `unified_elo_system.py` stays (other consumers use it for ad-hoc queries), but **no production comprehensive_elo write path calls it anymore** — writers call the canonical function with explicit inputs. This removes the trap where shell-script flags (`--skip-advanced-metrics`) silently reshape the stored formula.

---

## 5. DECISION 4 — The migration path

Design constraints: live system, frozen area, every step individually reversible, every step verified before the next. The controlling idea: **separate plumbing changes (output-neutral, Stages 2–3) from the formula change (Stage 4, one constant)** — never both in one step.

### Stage 0 — Precursors (no frozen-area contact)
- **0a. RESOLVED 2026-07-12 (redefined), CORRECTED 2026-07-13 (write-time bug — see O-33).** The original "wait for the absolute count to plateau" gate turned out to be measuring the wrong population (99.97% non-flagged discovery-pool traders, structurally incapable of going flat — see O-20). Replaced 2026-07-12 with `stale_elo_orphans` (BUY, no position, `is_flagged=1 AND research_excluded=0`, >24h stale by trade `timestamp`) — but that ">24h stale" clause gated on event-time, the same trap as O-21, and the first confirmatory sample came back 528 (not 4), driven entirely by 2 traders bulk-backfilled that same day. Corrected 2026-07-13: stale bound is now `MAX(tr.timestamp, COALESCE(t.backfill_attempted, tr.timestamp)) < now - 24h` — write-time via `traders.backfill_attempted` (stamped by `background_backfill_worker.py` at bulk-insert time), falling back to event-time only for traders never bulk-backfilled. **Resampled clean: 1, 1, 1 across 3 samples — Passing.** Verified the fix excludes the 2 same-day backfills while still catching a genuine 3-week-old orphan from a third trader. Full derivation in the overhang ledger's O-20 and O-33 entries.
- **0b. RESOLVED 2026-07-12.** Behavioral validation study (§3.3) complete: `W_beh = 0`. Full evidence in `2026-07-12-behavioral-validation-study-STAGE-0B.md` (commit `37d2171`) and §3.3 above.
- **0c. RESOLVED 2026-07-12 (first-repo commit `61adaf5`).** Dead Writer C (`integrate_behavioral_elo.py`) deleted, dormancy independently re-verified. `resolved_trades_count`'s scheduled writer set is now single.
- **0d. DONE 2026-07-13 (first-repo `434a6dd`).** Added 5 Tier-0/OBSERVE invariants to `audit_invariants.py` per §6 (range bound, soft-cap compliance, write atomicity, behavioral materialization, population drift). Baselines recorded (n=26,665): range 0 violations, soft-cap 16, write-atomicity 270, behavioral-materialization 7,660 (consistent with the ~8,026 cited above from a week earlier), drift check self-bootstrapped (no prior baseline, recorded today's snapshot). All report OBSERVE status — gate nothing yet, as scoped.
- **Rollback:** trivial (0c is a dead-code delete; everything else is read-only).
- **Stage 0: COMPLETE.**

### Stage 1 — Shadow computation (zero production writes)
- **Pure formula + tests: DONE 2026-07-13 (first-repo `0800a5e`).** Built `analysis/comprehensive_elo_formula.py` exactly per this section's corrected §4.1 spec (no DB I/O, bonus/multiplier share `w_beh`, `apply_soft_cap`/`apply_floor` explicit params). Three suites, 339,663 assertions total, all green: golden tests pin all 5 of §2.4's worked examples exactly; property tests (335,296 assertions) cover monotonicity in `pnl_raw`, behavioral-gain boundedness, cap/floor compliance, and thin-sample gating — note the property test derives its behavioral bound directly from the corrected formula rather than trusting §2.2(a)'s prose bound, which the Correction section's revision list never actually included (see the flag at the end of this stage's entry); **the zero-diff equivalence test — ZERO diffs across a 61,248-point grid** against an independent verbatim port of `apply_full_elo_modifiers.py` (`tests/_writer_b_reference.py`), covering both dampening thresholds, every confidence-cap breakpoint, the thin-sample boundary, and the full `pnl_raw` range; also proves `beh_mult`/`bonus` have zero effect at `w_beh=0` (the specific bonus-leak bug class) across every grid point.
- **Live-data validation: DONE 2026-07-13.** `scripts/validate_stage1_equivalence.py` (read-only) ran the pure formula against real component values for 25,635 eligible flagged/non-excluded traders: **99.87% match (25,587/25,620) on the Writer-B-written population.** All 33 mismatches share the exact same `elo_last_updated` timestamp (one maintenance run) with `pnl_last_updated` strictly later for 32/33 — confirmed as ordinary post-write P&L drift, not a formula defect. The single Writer-A mismatch and single unknown-writer mismatch are both expected (Writer A still runs its own formula pre-Stage-3; the "unknown" case had a NULL `elo_last_updated` — never written by either ELO writer, a schema-default value, not a comparable production output).
- **Flag for whoever reviews Stage 2 next: §2.2(a)'s stated behavioral-delta bound ("damp × (0.20×base+100)") is stale.** The 2026-07-06 Correction section's revision list names only §2.1/§2.4/§2.5/§4.1/§5 as updated after the bonus-scaling fix — §2.2 was missed. The correct general bound (verified against the corrected formula and consistent with all 5 golden examples) is `w_beh × (0.4×base + 100)` on the positive side, not `0.20×base+100` (which implicitly assumes `w_beh=0.5` baked into the multiplier coefficient while leaving the bonus term unscaled). Doesn't change any decision here — §2.2's qualitative conclusion (bounded, asymmetric-safe) still holds — but §2.2 itself should get the same correction pass §2.1/2.4/2.5/4.1/5 already received, next time this doc is touched.
- Shadow side-table (`elo_shadow`) + nightly job + delta report: **not yet built** — next up for Stage 1 to fully close (the pure function existing and proven doesn't by itself populate the shadow table or produce the human-reviewed delta report this stage still promises).
- **Rollback:** trivial — the formula module and its tests are inert until something calls them; nothing in production references `comprehensive_elo_formula.py` yet.

### Stage 2 — Writer B onto canonical plumbing, output-neutral (`W_beh=0`, `apply_soft_cap=False`, `apply_floor=False`)
- Replace `apply_full_elo_modifiers.py` formula internals with `compute_comprehensive_elo(w_beh=0, apply_soft_cap=False, apply_floor=False)` + `write_elo_result`. At these settings the canonical formula **is algebraically Writer B, term for term** (re-confirmed in the Correction section above after fixing the original bonus-scaling and unconditional-bounds bugs) — so this cutover is provably value-neutral.
- **Verification:** full dry-run on a DB snapshot — assert byte-identical `comprehensive_elo`/`pnl_modifier` for all ~20K against the old code path, with **zero tolerance, not a rounding epsilon**. Exactly **two intentional diffs allowed**: (i) `elo_last_updated` switches to canonical space-separated format (the O-3 writer fix — after this, the O-3 count stops growing); (ii) behavioral/advanced/snapshot columns now refresh atomically per §4.1 (value-identical if caches unchanged — assert that too). *Any other diff means the plumbing isn't neutral yet — do not proceed to Stage 3 until the dry-run is clean.*
- **Rollback:** git revert; values were never different.

### Stage 3 — Writer A onto canonical plumbing, AND the soft cap + floor turn on (`W_beh=0` still; `apply_soft_cap=True`, `apply_floor=True` from here on)
- Replace `full_elo_recalculation`'s per-trader formula with the same canonical call, now with `apply_soft_cap=True, apply_floor=True` — this is the stage where Writer A's soft cap and the new floor are deliberately introduced (moved here from the original Stage 2 draft per the Correction section above, since Sunday's output is already changing in this stage for other reasons, and the soft cap is native to Writer A's own history).
- **Both writers now share `apply_soft_cap=True, apply_floor=True` going forward** — this also retroactively affects Writer B's daily pass from this stage on (previously Stage-2-only bounds-free; Stage 3 turns the unified bounds on everywhere). Verify the 9-trader soft-cap population (identified in the Correction section) explicitly at this cutover — expect their values to drop to the soft cap, by design.
- Sunday's output changes from `(base×beh+bonus)×pnl, soft-capped` (Writer A's old formula) to canonical-at-neutral (= gated/dampened base×pnl, dual-capped, floored).
- **Who actually changes lastingly:** the ~2.5K no-closed-positions traders (Writer B never overwrites them). For the other ~20K, Sunday values already get overwritten by (now-canonical) Writer B within 24h — the change shrinks their weekly 4.5-hour behavioral window to zero, which is the honest version of what the system already does for 163 of 168 hours a week.
- **Verification:** pre-flip shadow diff scoped to exactly the 2.5K Sunday-retained population, PLUS the 9 identified soft-cap traders and any trader near the new floor; human reviews (expect: values *drop* for high-behavioral thin traders — e.g., worked example T's 2,100 → 1,500 — this is the un-gated-pnl and thin-sample corrections landing, defensible and visible; expect the 9 soft-cap traders to drop by exactly the amounts quantified in the Correction section).
- **After this stage the writer disease is dead:** both cadences compute the same function with the same bounds; interleaving is harmless; `comprehensive_elo` can only be computed one way. **This is O-7's structural deliverable, delivered before any formula change.**
- **Rollback:** git revert; next Sunday rewrites old-style values (self-healing ≤ 7 days). Harness invariant #3 flips to gating mode at the END of this stage (formula-reproducibility now must hold).

### Stage 4 — Enable behavioral (the one formula change)
- Set `W_beh` to the Stage-0b-validated value in **one constant in one module**. Both cadences pick it up on their next run.
- **Pre-flip:** final shadow report — exact per-trader deltas (bounded by `damp×(0.2×base+100)`); **tier-migration table** (traders crossing 1500/1800/2175 — the direct answer to "what does this do to STR-002's gates"); flag any trader moving >1 tier.
- **Post-flip:** harness fully gating; watch population drift (invariant #6) and STR-002 tier composition for 2–3 weeks. STR-002's v2 pre-registration (the 2026-06-30 doc §6) should date its "post-fix" signal cohort from this flip.
- **Rollback: set `W_beh = 0`.** Values self-restore within 24h for the ~20K (daily pass) and ≤7 days for the rest (Sunday). No data repair needed — this is the payoff of the `B + delta` decomposition.

### Stage 5 — Cleanup and unfreeze
- Retire Writer D remnants (`quick_elo_update_for_traders`, `_process_trader_chunk`, `_batch_store_elo_results`, `--quick-update` CLI).
- One-time `elo_last_updated` backfill (the existing 23.5K non-canonical rows; generator already fixed in Stage 2) — closes O-3 entirely (`traders.elo_last_updated` was its last driver).
- Update docs: CLAUDE.md ELO section, STR-002 registry description (either restore "6-dimensional" honestly or say what it is), memory files, ledger (O-3, O-6, O-7 closed).
- **Unfreeze `recalculate_comprehensive_elo.py`** — the freeze's stated exit condition (Layer 2 done + harness clean) is met.

---

## 6. DECISION 5 — Harness coverage (currently ZERO formula invariants)

To add to `audit_invariants.py`. Tiers follow the existing T1(critical)/T2(regression) convention.

| # | Tier | Invariant | Why / notes |
|---|---|---|---|
| 1 | T1 | `400 ≤ comprehensive_elo ≤ 3500` for all non-NULL flagged | Runaway inflation/collapse. Passes today (479–3,315). |
| 2 | T1 | `comp ≤ 1500 + resolved_trades_count×150 + ε` | Soft-cap compliance — would catch a writer bypassing caps. |
| 3 | T1 | **Formula reproducibility**: for every flagged trader with complete components, `|comp − compute_comprehensive_elo(stored components)| < ε` | **The single-writer enforcement invariant.** Only possible because §4.1 writes all inputs atomically with the output. Any rogue writer, manual UPDATE, or formula drift trips it within one audit cycle. Gating from end of Stage 3. |
| 4 | T1 | Write atomicity: 0 traders where `comprehensive_elo` is non-NULL but any component column is NULL, post-first-canonical-write | Detects partial writes (the RQ-CONTESTED-001 artifact class). |
| 5 | T2 | **Behavioral materialization**: count of traders with `behavioral_modifier > 1.05 AND resolved ≥ 10` whose comp equals the `W_beh=0` value within ε — must be ~0 once Stage 4 ships with `W_beh > 0` | The direct regression test for THIS bug ever returning. Fails by design today (~8,026) — OBSERVE mode until Stage 4. If Stage 0b lands `W_beh=0`, this invariant stays OBSERVE with a comment, not deleted. |
| 6 | T2 | Population drift: weekly mean within ±100 of trailing mean; tier counts (≥1500/≥1800/≥2175) change <20%/week | Slow-inflation detector; also catches upstream input corruption (pnl_cache, behavioral cache). |
| 7 | T2 | Cadence consistency: the formula-reproducibility check reported split by last-writer cadence (Sunday vs daily) | Same check as #3 but the split localizes which pass broke. |
| 8 | T2 | `elo_last_updated` canonical format, floor 0 (after Stage 5 backfill) | Folds the last O-3 driver into permanent coverage. |
| 9 | T1 | Post-Sunday completeness: Monday audit asserts ≥99% of flagged traders have `elo_last_updated` within the last 8 days | Detects a silently-aborted Sunday run (today ~26 stragglers predate this week — set floor accordingly). |

---

## 7. DECISION 6 — O-5 sequencing, corrected

The ledger says O-5 (non-ELO competing writers) "should precede Layer 2." Verified against what the canonical formula actually reads, **most of O-5 does not block O-7**:

### 7.1 Real precursors (must land before Stage 2)
- **`resolved_trades_count`** — feeds the soft cap AND the thin-sample gates. Verified today: live writers are `evaluate_new_trader_results.py:72` (legitimate, daily) and **`integrate_behavioral_elo.py:196` — dead Writer C**. (`recalculate_trader_stats.py:51` is a Python local, not a DB write.) **Deleting Writer C (Stage 0c) makes this column single-writer with zero additional work.**
- **Positions-table integrity** (feeds `pnl_cache` → `pnl_raw` and `closed` — the confidence cap reads `closed_positions` **from pnl_cache/positions, NOT the contested `traders.closed_positions` column**; verified in `apply_full_elo_modifiers.py:177-178`). This is **O-15, fixed today** — the precursor is *waiting for the backlog drain to stabilize* (Stage 0a), not new work.

### 7.2 NOT precursors (parallel track, on their own merits)
- `trader_statistics.successful_trades` — not read by any ELO formula path.
- `monitor.py`'s `traders.open/closed_positions` column writers — not read by the formula (see above; the column is display/aggregate only).
- `analysis_scheduler.specialisation_ratio` — not read by the formula.

**Corrected sequence:** `Stage 0c (Writer C delete) + Stage 0a (O-15 drain settles) → Stages 1–5.` The rest of O-5 proceeds independently whenever convenient. This pulls the ELO arc forward by whatever time full-O-5 would have cost.

### 7.3 O-3 fold-in (from today's session finding)
The remaining O-3 timestamp debt is entirely `traders.elo_last_updated`, generated by Writer B's `.isoformat()` (§1d). It folds into this migration cleanly and is already scheduled: **generator fix in Stage 2** (canonical write helper uses canonical format), **backfill in Stage 5**. No separate O-3 workstream needed for this column.

---

## 8. Uncertainties and explicitly-flagged judgment calls

1. ~~**`W_beh = 0.5` is a judgment, not a measurement**~~ — **RESOLVED 2026-07-12**: Stage 0b measured it. `W_beh = 0` (see §3.3). No longer a free parameter at launch; Stage 4's one-constant rollback/flip mechanism remains the path if better evidence arrives later.
2. ~~**Behavioral predictiveness is unproven**~~ (§3.2) — **RESOLVED 2026-07-12**: tested directly, no economically meaningful signal found (§3.3, full study `2026-07-12-behavioral-validation-study-STAGE-0B.md`). The design's structuring so this uncertainty couldn't block architecture value turned out to matter — it didn't.
3. **The 41/2,476 Sunday-formula residuals** (§1b) are unexplained in detail (suspected adaptive-weight NULL-score edge cases). They don't affect any decision here, but Stage 1's golden tests should include a few of these traders to pin exact current behavior before replacement.
4. **Bonus step-function shape retained as-is** (kelly/patience thresholds) — inherited, not re-derived. Re-deriving it is out of scope; the compression via `W_beh` (which now scales the bonus too — see Correction section) and the thin-sample gate bound its damage either way.
5. **Cluster D / non-flagged scope gap** (~100K non-flagged traders parked at 1,500) — **deliberately out of scope.** This design unifies how comprehensive_elo is computed, not who gets one. Widening scope mid-migration would confound every population diff. Revisit post-Stage-5 as its own item.
6. **Advanced modifier exclusion** (§2.5) — means "6-dimensional ELO" remains aspirational (it becomes ~4-dimensional: base, behavioral-mult, behavioral-bonus, pnl). Docs must say so honestly (Stage 5).
7. **Stage 0a's drain-stabilization estimate (1–2 weeks) is a guess** — gate on the harness plateau, not the calendar.
8. **Writer A's ~5h46m Sunday runtime is untouched** by this design (same computation, different final arithmetic). If Sunday ever overruns into daily maintenance, that's an ops issue this design neither causes nor fixes.

---

## Appendix A — Verification run 2026-07-06 (all read-only)

| Check | Result |
|---|---|
| Writer D call site | `git show ca30c07`: `quick_elo_update_for_traders` call was inside deleted `check_market_resolutions()` — dead 2026-07-02. Zero production callers remain (grep: only archive/ + CLI branch). |
| No-op, Writer B population (written 2026-07-06) | 19,944/19,944 match `comp = base×pnl` (<1.0 pt), 100% |
| Sunday population (written 2026-07-05) | 2,435/2,476 (98.3%) match `min((base×beh+bonus)×pnl, 1500+resolved×150)` (<2 pts), bonus reconstructed from stored kelly/patience/timing via the step function in `unified_elo_system.py:860-930` |
| Last-writer split | 20,054 @ 2026-07-06 (Writer B) vs 2,491 @ 2026-07-05 (Writer A) — mechanism live |
| Modifier distributions (flagged, non-excl) | behavioral 0.999 avg [0.80–1.40]; advanced 1.084 avg [1.00–1.10]; pnl 0.932 avg [0.40–2.20] |
| Population | n=26,806, mean 1,400.5, range 479–3,315, ≥1800: 1,393 |
| `resolved_trades_count` writers | `evaluate_new_trader_results.py:72` (live) + `integrate_behavioral_elo.py:196` (dead Writer C only) |
| Confidence-cap input source | `apply_full_elo_modifiers.py:177-178` — pnl_cache (positions table), not `traders.closed_positions` |
| O-3 generator | `apply_full_elo_modifiers.py:152` `datetime.now().isoformat()` → `elo_last_updated` T-format |
| Sunday shell flags | `run_sunday_elo.sh` still passes `--skip-correlation --skip-contrarian --skip-advanced-metrics` |

---

## Appendix B — Independent re-verification, 2026-07-06 (same day, separate pass)

Run specifically to stress-test this document's two load-bearing claims before banking it as plan of record. Read-only; no code changed.

| Claim | Check | Result |
|---|---|---|
| **1. Writer D fully dead** | Grepped every reference to `quick_elo_update_for_traders` in both repos | Only `elo_bridge.py:330` (def), `elo_bridge.py:794` (manual `--quick-update` CLI branch, `__main__`-only), and 6 `scripts/archive/*` test files. Zero hits in trading-swarm. |
| | Checked full crontab, `/etc/systemd/system/`, `deploy/` for any reference to `elo_bridge.py` or `--quick-update` | Zero references anywhere. The only ELO systemd unit (`polymarket-sunday-elo.service`) runs `run_sunday_elo.sh` → `recalculate_comprehensive_elo.py` → `full_elo_recalculation` (Writer A), not `elo_bridge.py`'s own CLI. |
| **1. Exactly 2 live writers** | Grepped every `SET`/write to `comprehensive_elo` in both repos, excluding archive/simulation | Exactly 3 files: `integrate_behavioral_elo.py:254` (Writer C), `elo_bridge.py:244` (inside `_batch_store_elo_results`, reachable only via Writer D — dead) + `elo_bridge.py:601` (inside `full_elo_recalculation` — Writer A, live), `apply_full_elo_modifiers.py:242` (Writer B, live). |
| | Checked every other reference to `integrate_behavioral_elo.py` (Writer C) across both repos for a live caller | All are comments, docstrings, or `print("Run: ...")` suggestions in `test_behavioral_integration.py`, `validate_pnl_data.py`, `validate_roi_rebalancing.py`, `reconcile_trader_aggregates.py`, `diagnostics.py` — none execute it. Its one real historical caller (`system_observer.py`) is the disabled comment block. |
| | **Verdict** | **Claim 1 CONFIRMED. Exactly 2 live writers (A + B). No exception found.** |
| **2. Stage 2 output-neutrality at `W_beh=0`** | Pulled exact Writer B code (`apply_full_elo_modifiers.py:155-201`) and compared term-by-term against the original formula draft | Confidence-cap's conditional application (`if mult>1.0`) vs. canonical's unconditional `min()` — algebraically equivalent (caps are always ≥1.30>1.0); **not** a real discrepancy. |
| | Reconstructed the bonus (kelly/patience, timing excluded) for today's Writer-B population (n=20,054) and checked whether it was zero at the original `W_beh=0` | **17,053/20,054 (85%) nonzero, avg +9.37 pts** — the bonus leak, because the original formula scaled bonus by an independent `W_bonus=1.0` regardless of `W_beh`. |
| | Checked whether the soft cap (`1500+resolved×150`) ever binds below the hard cap for today's Writer-B population | **9 real traders**, deltas **5.1–297.2 points** (e.g. `0xbe997afc...`: actual 3297.2 vs. soft-capped 3000.0) — Writer B has no soft cap in production; the original formula added one unconditionally. |
| | Checked whether the new 400-floor currently binds on any Writer-B-processed trader (raw, uncapped value) | Minimum raw value today: 479.0 — floor doesn't currently bind, but is a real, unacknowledged behavioral difference from "Writer B, exactly" as originally specified. |
| | **Verdict (original)** | **Claim 2 BROKEN as originally specified** — 2 material live discrepancies (bonus leak, soft cap) + 1 latent one (floor). Reported back; fixes applied above (Correction section, §2.1, §2.4, §2.5, §4.1, §5). |
| | **Verdict (corrected formula, re-checked against the same live data)** | Bonus now scales by the same `W_beh`, so it's exactly 0 for all 20,054 traders at `W_beh=0` (not 17,053 nonzero). Soft cap and floor are now explicit `apply_soft_cap`/`apply_floor` parameters, both `False` in Stage 2, so the 9-trader soft-cap discrepancy and the floor difference no longer apply during Stage 2. **Corrected Stage 2 formula is now genuinely, term-for-term identical to production Writer B.** |

---

*Design complete 2026-07-06. Corrected same day following independent re-verification of Claims 1–2 (Appendix B). No code changed. ELO subsystem remains frozen pending human review of this document.*
