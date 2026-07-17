# B2 Price-History Probe — Result

Status: FINAL (50/50 markets processed)
Generated: 2026-07-17T21:08:21+00:00

Probe of item B2 from `2026-07-17-edge-proof-experiment-design-FABLE.md`: does CLOB `prices-history` retain usable ~30min-granularity data for resolved geo/elec markets, and how well does the local trade tape cover the gap when it doesn't. Read-only against production DB; no writes.

## Sample composition

- Target: 50, sampled: 50
  - old: 26 markets
  - recent: 24 markets
- Age windows: old = 2025-11-01..2026-01-01, recent = last 60 days (>= 2026-05-18)
- Volume tiers: notional (sum shares*price from local trades) split at the median within each age bucket

## Funnel

- clobTokenId resolved: 49/50 (98%)
- CLOB prices-history retained data (of resolved): 49/49 (100%)
- CLOB prices-history empty/failed (of resolved): 0/49 (0%)
- Token not resolved at all: 1/50 (2%)

## Granularity & coverage (CLOB-retained markets)

- Median observed gap between points: 30.0 min (target was 30 min)
  - <= ~30min: 49/49, ~hourly: 0/49, coarser: 0/49
- Coverage full to resolution (last point within 24h of resolution_date): 36/49 (73%)

## Age degradation (old Nov-Dec 2025 vs recent)

- recent: token resolved 24, CLOB retained 24/24 (100%)
- old: token resolved 25, CLOB retained 25/25 (100%)

## Verdict

CLOB `prices-history` retains data for the large majority of resolved geo/elec markets in this sample. It can serve as the **primary** entry-price source per §4.3; the trade-tape path stays a fallback as designed. Check the age-degradation and granularity numbers above before finalizing — if either strata or granularity skew badly, narrow the design's claim accordingly.

## Raw per-market results

See `logs/b2_price_history_probe_state.json` (first-repo) for full per-market detail.
