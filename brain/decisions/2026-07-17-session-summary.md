# 2026-07-17 Session Summary — Phase Shift: "Build the System" → "Prove the Edge"

## The Headline

After ~2 months of hardening (ELO arc nearly complete, data clean), Oscar made an explicit
strategic call today: the project pivots from **building the system** to **proving the edge**.

The point right now is running experiments on **real data** to prove or disprove whether
following proven high-ELO traders produces tradeable edge in geopolitics prediction markets.
**Disproof is a valid, valuable outcome** — grounds for redirection or improvement, not failure.

The swarm (autonomous automation) is **deferred behind this proof**: make it work / prove it
works before automating.

**Oscar's chosen edge framing:** AGGREGATE behaviour of the proven high-ELO cohort (not
individual mirroring) — the edge is in having many skillful traders on the radar plus an ELO
system accurate enough to identify the genuinely elite.

---

## 1. Strategic Orientation + Feasibility Discussion

Reframed the project into three layers:
- **Foundation** — nearly solid (infrastructure, data hygiene, ELO arc)
- **The Edge** — unproven; the real open question
- **Swarm automation** — deferred until the edge is proven

Everything built so far is infrastructure for a signal not yet demonstrated profitable.
Sequencing agreed: **prove the edge (cheap) before building the autonomous machine to exploit
it (expensive)**.

## 2. Fable Edge-Proof Experiment Design (main deliverable)

Commissioned Fable to design the experiment. Output:
`brain/decisions/2026-07-17-edge-proof-experiment-design-FABLE.md` (trading-swarm `ff02856`).
Reviewed as excellent — rigorous, honest, disprovable, diagnostic.

Key elements:
- **H1**: does the point-in-time LEGENDARY cohort's aggregate positioning beat the **market
  price** (hardest benchmark) after realistic lag + costs?
- **Blocker resolved**: point-in-time ELO IS recoverable — true `elo_snapshots` since
  2026-06-11 (33 addresses cycled through LEGENDARY in 30 days, so turnover is real and PIT
  matters), plus `geo_elo` is a deterministic, replayable fold before that.
- **The real blocker**: no historical price series (only 2 of 10,108 markets have token IDs)
  → the whole experiment hinges on **B2 (price-history probe)** as the first go/no-go.
- **Two-phase**: Phase 1 backtest (fast, disprovable-cheaply, pre-registered spec,
  train/validate/frozen-holdout) → Phase 2 forward paper-trade (trustworthy, 4-9 months,
  limit-order-only).
- **Diagnostic ladder (rungs A-D)**: isolates *where* the thesis fails (information absent /
  ranking is hindsight / edge decays too fast / costs kill it) — every "no" is a specific
  diagnosis. Plus 2 placebos: random-cohort (does the ranking add value vs. just tracking?)
  and inverted-cohort (look-ahead-leak fraud alarm).
- Learned from STR-002's specific failures (share-weighting, NEAR_RESOLVED contamination,
  crowded-field YES trap) — spec fixes each.
- Honest power statement: certifies edges >=~8pt; can't distinguish 3pt from 0 (fine — a 3pt
  edge dies to costs anyway).

## 3. Sample-Thinness Verified Real

Checked the funnel before building: confirmed the thin sample (268 markets with >=3 cohort
traders) is genuine, **not** a category-filter or unbuilt-position artifact. The experiment's
power limits are real — proceed with Fable's Pool-C-widening fallback in mind.

## 4. Prior Timing Work Checked

RQ2.2 (2026-04-26) tested 7-day post-entry price drift → null result (coin-flip; top-tier did
*worse*). Not a lag-decay curve, but a useful prior — the lag-sweep (design doc §4.3) may find
flat/near-zero decay. STR-002's `edge_at_entry` can't separate "late" from "wrong" — the exact
gap §4.3 fills, so it's genuinely new work, not redundant.

## 5. B2 Probe Launched — the first go/no-go

`scripts/b2_price_history_probe.py` (first-repo), detached (PID 78324, PPID 1 — survives
disconnect), checkpointed/resumable. Writes verdict to
`brain/decisions/2026-07-17-b2-price-history-probe-result.md`. Tests whether CLOB
prices-history retains usable data for old/resolved geo/elec markets.

**Status as of session end: IN PROGRESS (45/50 markets processed).** Preliminary numbers look
strong: clobTokenId resolved 44/45 (98%), CLOB prices-history retained 44/44 of resolved
(100%), median gap 30 min (on target), coverage full-to-resolution 32/44 (73%). No age
degradation seen yet (old and recent both 100% retained). **Not final — re-read on
resume.**

Connection dropped twice this session (internet outage killed an earlier session-attached
fork). **Lesson: detach long jobs (nohup + disown) — flaky internet joins flaky power as a
reason to always detach.** The re-launched probe is properly detached.

## 6. Two Data-Integrity Findings From the Probe (ledgered `a4775cf`)

- **O-36 (HIGH)**: `markets.resolution_date` can be badly wrong — NYC mayoral shows
  2026-06-04 but trade tape + real election ended 2025-11-05 (~7mo stale). Load-bearing
  (requeue gates, O-33 logic, **and** the edge experiment's PIT train/test splits). May need
  fixing *before* the backtest can trust resolution-date splits. **Investigate this weekend.**
- **O-37**: synthetic/duplicated trade rows — 202 geo/elec markets (2,858 DB-wide) with
  implausible stats (one: 619K trades @ 222K shares avg; distinct market_ids with identical
  trade counts). Scope/cause/ELO-impact TBD.

---

## Next Session (this weekend)

1. Read the B2 probe verdict once complete (can we get historical entry prices? via CLOB or
   trade-tape fallback?).
2. Investigate O-36 (`resolution_date`) — likely first, since it could undermine the
   experiment's temporal integrity. Roughly half a session to know if it's a shrug or a real
   systematic problem; fix scales with severity.
3. Then O-37 if time.
4. If B2 is GO and O-36 is manageable: proceed to B4 (order-book capture ON — start
   regardless), B1 (PIT replay engine), per Fable's build order.
5. Background: ELO arc — Writer A's first canonical run is **Sunday 03:00** (proven safe via
   the dry-run). Stage 5 cleanup still pending.

## Still Open (deferred, not forgotten)

- `is_taker`/`transaction_hash` decision — Fable's design confirms this experiment does not
  rescue it.
- Swarm respawn/verification build + paused-agent reactivation.
- O-29 / O-28.
- The two 07-15 swarm bugfixes.
- Tier-3 governance decision.
