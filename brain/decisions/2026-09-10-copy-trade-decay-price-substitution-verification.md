# Copy-Trade Decay — Price-Substitution Verification

**READ-ONLY diagnostic.** Nothing was modified, no ladder was re-run, no
corrected curve was produced, no production table was written. This
checks one thing: whether the N=0 → N≈30–60min *rise* in the 2026-09-10
decay result (first-repo `c9619a4`, trading-swarm `9732bc9`) is a
price-semantics artifact.

**Finding, up front: it is.** The substitution takes the next trade in
the market at or after `entry+N` **from any outcome**, and `trades.price`
is outcome-specific (`P(Yes) + P(No) ≈ 1.0`). **37.58%** of the N=15min
substitutions land on the *opposite* outcome from the position held, so a
complement price `≈ 1 − p` is substituted for `p`. Recomputing the
N=15min broad-pool rung with **outcome-matched substitutions only** gives
**+0.01592, CI [−0.00130, +0.03317]** (straddles zero) against the
published **+0.03434** — i.e. with the complement substitutions removed
the rise from N=0 (+0.01208) essentially disappears. Survivorship (Part
4) is a real but negligible contributor (~0.0001 of a ~0.019 rise).

The published curve **stands as computed**; this is a diagnostic
estimate for Oscar, not a corrected result. **No verdict on whether to
re-run — that is Oscar's.**

Tags: **[V]** verified this session (query/command shown), **[I]**
reasoned judgment.

---

## 0. Running shells

Three detached `bash -c` wait-loop shells from the decay run remain alive
(PIDs 43016, 43045, 43191), each blocked in a `sleep` inside an
`until ! pgrep …; do sleep N; done` loop whose newlines were collapsed at
spawn so it never terminates cleanly. **[V]**

- Their only commands are `pgrep`, `sleep`, and (if they ever break out)
  `tail` / `ls` / `git status` — **all reads. None writes to the DB or to
  any artifact.**
- The actual `copy_trade_decay_diagnostic.py` Python process and the
  `run_tests.py` process are **both finished** (`pgrep` returns nothing;
  the artifact `data/characterizations/copy_trade_decay_20260910T191052Z.json`
  was written 19:10 and committed in `c9619a4`).
- `data/polymarket_tracker.db-wal` is 0 bytes; the DB is quiescent apart
  from the normal 15-minute production monitor cycle.

**This read-only check cannot interfere and is not interfered with.** The
shells were left running per the task's "do NOT interfere" instruction.

---

## PART 1 — what `trades.price` means, established empirically

Method (MASTER_HANDOVER_2026-08-15 §1, methodology rule 4): take paired
opposite-outcome (`Yes` / `No`) trades on the **same** resolved,
non-gap Geopolitics/Elections market, matched to the nearest
opposite-outcome trade within a short window, and look at the
distribution of `price_Yes + price_No`.

Population: 739,459 `Yes`/`No` trade rows on resolved non-gap geo/elec
markets. **[V]**

| match window | n pairs | mean sum | median | p1 | p5 | p25 | p75 | p95 | p99 | in [0.98,1.02] | in [0.95,1.05] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 s | 45,984 | 1.00054 | 1.00000 | 0.9807 | 0.9980 | 0.9990 | 1.0010 | 1.0089 | 1.0272 | **97.9%** | 99.4% |
| 60 s | 67,256 | 1.00117 | 1.00000 | 0.9680 | 0.9900 | 0.9990 | 1.0010 | 1.0120 | 1.0482 | 95.3% | 98.6% |
| 300 s | 100,323 | 1.00152 | 1.00000 | 0.9400 | 0.9880 | 0.9990 | 1.0015 | 1.0200 | 1.0700 | 92.0% | 97.2% |

The sum is **tightly centred on 1.0** (median exactly 1.00000 at every
window; interquartile range [0.999, 1.001] at 10 s). The spread widens
with the window purely because price genuinely moves over the interval.
The "not complementary" tail (sum < 0.5 or > 1.5) is **~0.01–0.05%**.

**Plain statement:** `trades.price` **is `P(the outcome that trade
bought)`, for both sides.** A `No` trade at 0.70 means the market priced
`No` at 0.70 and `Yes` at ~0.30. It is **not** a single normalised
`P(Yes)` series, and it is **not** something else (e.g. a notional or a
size). The `side` (BUY/SELL) does not change the price level — a SELL of
`Yes` at 0.60 still means `P(Yes) ≈ 0.60`; only the `outcome` flips the
price to its complement.

### STOP-condition check — does this reach the N=0 computation?

**No.** N=0 (and the result of record) uses `positions.entry_avg_price`,
not the trade tape. **[V]**

- 4,000 randomly sampled OOS geo/elec positions: **0.00%** had any entry
  trade on an outcome different from the position's own outcome
  (`json_extract(entry_trade_ids)` → `trades.outcome` vs `positions.outcome`).
- `|entry_avg_price − share-weighted mean of the position's entry-trade
  prices|`: median **0.00000**, p95 0.0009, 98.5% within 0.02.
- My reconstruction's weighted N=0 gap on the broad pool reproduces the
  published figure exactly: **+0.01208** (published +0.01208; and the
  published N=0 gate already matched `measure_oos` bit-identically).

So `entry_avg_price = P(held outcome)` — outcome-correct. **The defect is
confined to the `N>0` tape substitution. STOP condition not triggered.**

---

## PART 2 — the substitution does not match outcome to outcome

Two predicates, quoted verbatim from
`scripts/copy_trade_decay_diagnostic.py`.

**(a) The tape (`build_trade_tape`, lines 184–187):**

```python
        rows = conn.execute(
            f"SELECT market_id, timestamp, price FROM trades "
            f"WHERE market_id IN ({ph}) ORDER BY market_id, timestamp", chunk
        ).fetchall()
```

**(b) The pick (`substitute_price_at_N`, lines 213–230):**

```python
        target = entry_dt + pd.Timedelta(seconds=n_seconds)
        target_str = target.strftime("%Y-%m-%d %H:%M:%S")
        rec = tape.get(row.market_id)
        if rec is None:
            n_no_tape += 1
            n_excluded += 1
            continue
        tss, pxs, tape_end = rec
        if target_str > tape_end:
            n_excluded += 1
            continue
        j = bisect.bisect_left(tss, target_str)
        if j >= len(tss):
            # target_str <= tape_end but strictly greater than every stored
            # string: only possible on formatting edge cases; treat as excluded.
            n_excluded += 1
            continue
        sub_px = pxs[j]
```

**(c) The position loader (`OOS_POSITIONS_SQL`, lines 141–153)** selects
`p.trader_address, p.market_id, m.category, p.entry_avg_price,
p.entry_timestamp, t.trade_result` — **`p.outcome` is not selected at
all.**

### Exactly what this does

- **Predicate selecting the substituted trade:** the first row, ordered
  by `timestamp`, among all trades in `row.market_id` whose `timestamp`
  string is `>= strftime("%Y-%m-%d %H:%M:%S", entry_ts + N)` (via
  `bisect_left` on the per-market timestamp list), excluding the position
  only if `entry_ts + N` is past the market's last trade (`tape_end`).
- **Outcome constraint:** **none.** The tape query has no `outcome`
  filter; `substitute_price_at_N` never references the position's
  outcome (it is not even loaded). The substituted price is
  `pxs[j]` for whatever trade sits at index `j`, `Yes` or `No`.
- **Side constraint:** **none.** No `side` filter. Per Part 1 this does
  not corrupt the price *level* (a SELL of an outcome trades at that
  outcome's price), so side is not the problem — **outcome is.**
- **Implication:** when the trade at index `j` is on the opposite
  outcome, `sub_px ≈ 1 − P(held outcome)` is substituted where
  `P(held outcome)` belongs. For a position that won (typically entered
  at `p > 0.5`), `edge = won − price` is then computed as
  `1 − (1 − p) = p` instead of `1 − p`, inflating that position's
  measured edge by `2p − 1 > 0`. For a position that lost (typically
  `p < 0.5`) the complement *deflates* it. Winners in this pool
  outnumber and out-price losers, so the net effect on the mean is
  upward — matching the observed signature (N=0 from the recorded
  price: +0.012; every delayed rung from the tape: +0.031 and flat).

### Fraction opposite-outcome at N=15min (broad pool)

Reconstructed the N=15min (900 s) rung with `p.outcome` and the
substituted trade's `outcome` attached (reproduces the published rung
exactly: `point_gap=0.03434`, CI `[0.01369, 0.05622]`, `n_pairs=19496`,
`n_pos=35468` — identical to `c9619a4`). **[V]**

| | count | share of substitutions |
|---|---|---|
| substitutions made | 35,468 | — |
| same-outcome | 22,138 | **62.42%** |
| **opposite-outcome** | **13,330** | **37.58%** |
| excluded (`tape_end < entry+N`) | 653 | — |

The mechanism is present at **every `N>0` rung** by construction (the
tape query never filters outcome); N=15min is the rung the prompt asked
for.

---

## PART 3 — magnitude at N=15min, broad pool (DIAGNOSTIC ESTIMATE — NOT a corrected result)

**The published curve stands as computed. The number below is a
diagnostic for Oscar. A corrected run, if any, must be separately
pre-registered.**

Same rung, same machinery (`weighted_pair_table` cap5 +
`weighted_two_way_gap_bootstrap`, `seed=42`, `reps=1500`), restricted to
substitutions where the substituted trade's `outcome` **equals** the
position's `outcome`:

| N=15min, broad pool | point_gap | 95% CI | n_positions | n_pairs | n_traders |
|---|---|---|---|---|---|
| **published** (any-outcome substitution) | **+0.03434** | [+0.01369, +0.05622] | 35,468 | 19,496 | — |
| **outcome-matched only** (diagnostic) | **+0.01592** | **[−0.00130, +0.03317]** | 22,138 | 13,853 | 3,012 |
| opposite-outcome only (context) | +0.06693 | — | 13,330 | 8,796 | — |
| N=0 reference (recorded entry price) | +0.01208 | [−0.00168, +0.02645] | 36,121 | 19,922 | — |

- **THIN check** (pre-registration's own rule, amendment item F):
  threshold = `max(30, 5% × N=0 pairs)` = `max(30, 996)` = **996**.
  Outcome-matched `n_pairs = 13,853` ≫ 996 → **NOT THIN**. The rung is
  fully computable on matched substitutions alone.
- With the complement substitutions removed, the N=15min edge
  (**+0.01592, CI including zero**) is within noise of the N=0 value
  (**+0.01208, CI including zero**). **The rise from N=0 to N=15min is
  essentially entirely attributable to the ~37.6% opposite-outcome
  substitutions.** The opposite-outcome subset alone sits at +0.06693,
  where the inflation is concentrated.

---

## PART 4 — survivorship (§5b exclusions), checked independently

At N=1min, 514 positions are excluded because `tape_end < entry + 1min`
(they are in markets that stopped trading within a minute of entry).
Comparison of those 514 against the 35,607 retained: **[V]**

| | excluded at N=1min (514) | retained (35,607) | diff (excl − ret) |
|---|---|---|---|
| mean N=0 edge (`won − entry_avg_price`) | +0.01039 | +0.01319 | **−0.00281** |
| median N=0 edge | +0.00200 | +0.00800 | — |
| win rate | 0.7879 | 0.6032 | +0.1847 |
| mean entry price | 0.7776 | 0.5900 | +0.1876 |
| **weighted N=0 gap** (cap5, same machinery) | — | **+0.01217** | vs full-pop **+0.01208** → **+0.00009** |

The excluded positions do have slightly lower N=0 edge (they are
high-confidence entries in fast-resolving markets — high win rate, high
entry price, thin edge). But the effect on the curve is **negligible**:
dropping them shifts the weighted N=0 gap from +0.01208 to +0.01217, a
move of **+0.00009**, against a published N=0 → N=1min rise of ~**+0.019**.

**Which mechanism is supported, and by how much:** the **complement-price
substitution** accounts for essentially the entire rise (outcome-matched
N=15min +0.016 ≈ N=0 +0.012; CI includes zero). **Survivorship** is a
real but **~0.5%** contributor (0.00009 / 0.019). Both are live; they are
not close to co-equal.

---

## What was not determined

- **Why the tape query omits the outcome filter** — whether it was a
  deliberate "any trade a copier could see" reading of the
  pre-registration's §1 ("the next trade in that market … from any
  trader") or an oversight. §1 says "from any *trader*"; it does not
  address *outcome*. Not adjudicated here.
- **The rungs other than N=15min.** Only N=15min was recomputed
  outcome-matched, per the prompt's scope. The opposite-outcome share is
  structurally non-zero at every `N>0` but its exact value and the
  matched-only curve shape across the full ladder were not computed (that
  would be re-running the ladder).
- **Per-category (geo vs elections) breakdown of the matched-only
  estimate.** Not computed.
- **The direction/size of the effect on losing positions specifically.**
  The aggregate is dominated by winners; the per-outcome-state
  decomposition beyond the "context" opposite-only figure was not done.
- **Whether outcome-matched substitution is itself the right
  construction** — a real copier sends an order on the outcome they want
  and transacts against whatever is on the book; "nearest same-outcome
  trade" is one repair, not obviously the only one. Out of scope.
- **Any corrected curve.** Explicitly not produced. The published
  `copy_trade_decay_20260910T191052Z.json` stands as computed until a
  corrected run is separately pre-registered — Oscar's call.

---

## Reproducibility

- Read-only. Scratch scripts only (not committed): the Part 1 Yes+No
  sum test, the Part 2/3 rung reconstruction (which reproduces the
  published N=15min rung to full precision), the Part 4 survivorship
  split, the STOP-condition `entry_avg_price` check. All reuse
  `weighted_pair_table` / `weighted_two_way_gap_bootstrap` and the
  `directional_skill_pit_legal_pool` loaders unmodified; `seed=42`,
  `reps=1500`, `cap5`, `T_SPLIT=2026-04-01 00:00:00`.
- No write to any `metric_v2f_*` or other production table.
- `copy_trade_decay_diagnostic.py` unmodified; the ladder was not re-run.
