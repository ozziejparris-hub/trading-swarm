# B5 event-clustering — structural check results

**Snapshot:** `bt_pop_2025-11-01_v1` (4,712 markets, first-repo `event_cluster_labels` table)
**Generator:** `scripts/build_event_cluster_labels.py`
**Run:** 2026-07-24

## Label counts

| label_type | count |
|---|---|
| native_negrisk | 1,891 (522 groups) |
| hand_standalone | 143 |
| hand_sibling | 0 |
| unsure | 0 |
| trivial_standalone | 2,678 |
| **total** | **4,712** |

All 143 ambiguous-zone markets (candidate-shaped, `neg_risk=False`, keyword-prefiltered) resolved to STANDALONE under the mutual-exclusivity test. 26 reasoned families (multi-advance formats, per-party/coalition thresholds, nested date/probability bands) + 15 true singletons + the 9-market "presidential novelty" group (Biden/Harris both resolved YES for the same nominal 2027 race — definitive non-exclusivity proof).

## Check 1 — merge errors (>=2 cluster members resolved YES)

**0 found**, across all 3,343 clusters (522 native + 143 hand-standalone singletons + 2,678 trivial-standalone singletons).

## Check 2 — incoherent tape_end window within a cluster

23 native clusters flagged (tape_end spread > 45 days). All 23 inspected individually — every one is a legitimate multi-candidate field (Peru presidential race, several US Senate primary fields, Denmark PM candidates, TX-18 special election, CA/LA/Oregon/NY primaries, Costa Rica/Peru "most seats," Honduras turnout bands, Baden-Württemberg). Spread explained by losing candidates' markets going quiet before resolution while the eventual winner's stays live — not a merge error.

## Check 3 — summed YES-price at a shared per-cluster timestamp

~1,750 live `price_at()` calls across 382 multi-member native clusters (380 had priceable data). 9 clusters flagged (sum > 1.15): Malta "most seats" (2.69), TX Dem Senate margin bands (1.88), OK Senate GOP nominee (1.60), Bucharest vote-share bands x2 (1.58, 1.49), Peru "finish 4th" (1.57), CA Gov "finish first" (1.57), DHS shutdown date bands (1.52), Iran-supreme-leader daily field (1.36).

Cross-checked against Check 1: **all 9 have YES_count <= 1** (never 2). Read as ordinary early/thin-market overround (several outcomes priced at identical round numbers, e.g. Malta's minor parties all at 0.385) rather than a genuine exclusivity violation — Polymarket's own protocol enforces exclusivity at settlement for native negRisk groups regardless of interim pricing inefficiency.

## NOT YET DONE — external audit gap

Check 1 catches merge errors (wrongly grouped) but is structurally blind to **false splits** (a genuine sibling-set wrongly labeled as separate standalones) — the direction that inflates bet count n. Since all 143 ambiguous markets came back standalone, an undetected false split would hide here with no mechanical signature.

**4 hand-standalone labels carry acknowledged reasoning uncertainty**, pending external verification (the way Singapore/California format facts were verified in the 2026-07-24 calibration):

1. **`ca_ltgov_advance`** (2 members: Sean Collinson, Ebie Lynch, both resolved NO) — zero resolution-data confirmation either direction; call rests entirely on "CA top-two primary applies to Lt. Governor too."
2. **`bg_seat`** (4 members: BSP, APS, ITN, Velichie, all resolved NO) — zero resolution-data confirmation; call rests on "Bulgaria's proportional system typically seats multiple small parties," not this election's actual outcome.
3. **`tx_senate_flip`** (2 members: "Cornyn flip Paxton... by Jan 31" / "...by March 2", both NO) — murkiest reasoning in the batch; unclear whether "flip" resolves on a polling-lead crossover (my working assumption) or a final-outcome check at two dates. Least confident label in the whole run.
4. **The 15 raw singletons** — candidate-shaped markets with no matched family; each is either genuinely standalone or has real siblings elsewhere in the population that weren't matched by the family-pattern regexes. List: Hungary "TISZA constitutional majority," Honduras "Nasralla flips Asfura," TX Senate Primary turnout/margin (x2), NYC "Sliwa drops out and Cuomo wins," NYC Eric Adams >1%, LA Mayoral first-round outright winner, Japan CRA 173+ seats, Canada election called by June 30, Bucharest >50% outright, FL Senate seat, Iran-strikes-vs-Fed-nominee compound bet, US Senate "Democrats flip Republicans," Poland snap election called.

`ca_gov_advance` (21 members, the calibration exemplar, only 1/21 resolved YES) was also flagged as a hard case in the pre-shutdown review but is lower-priority for re-audit since it's a direct restatement of the calibration-confirmed fact, not a new inference.

**Next-session action: verify these 4-5 cases before B5 is treated as final for B3.** See `brain/decisions/2026-07-24-shutdown-state-of-play.md` for full resume context.
