# Session Summary: Server Setup 13 — 2026-05-27

## What Was Built

### 1. Signals spam fixed
- `geo_elo_oos` `validation_requested` and `RQ-GEO-ELO-001` `hypothesis_ready` both marked processed/approved in `signals.json`
- Orchestrator spam eliminated

### 2. Etherscan API integrated — Polygon wallet lookup
- API key obtained (free tier, 100K calls/day, 5/sec)
- Stored in `~/.env_trading` as `ETHERSCAN_API_KEY`
- `scripts/polygon_wallet_lookup.py` built with 4 functions:
  - `get_wallet_first_transaction`
  - `get_wallet_usdc_funding_source`
  - `enrich_insider_signals`
  - `check_cluster_shared_funding`
- **Key finding:** Polymarket proxy wallets have zero Etherscan-visible activity — all 435 Pool C traders returned no data; proxy architecture bypasses standard transaction visibility
- **Exception:** Gnosis Safe wallets with direct on-chain activity ARE visible
  - Signal ID 3 (`0x53e55b`): created 2024-07-03, seeded with $10 USDC
  - Signal ID 2 (`0xde7be6`): created 2026-02-21, true age 7 days (confirmed insider pattern)

### 3. `wallet_age_days` corrected to Polymarket-native age
- Was: unreliable value (62 appearing repeatedly as fallback)
- Now: days between `traders.first_seen` and `trade_timestamp`
- Backfilled for all 7 existing insider_signals
- `detect_individual_signals` and `detect_cluster_signals` both updated
- Signal 2 correctly shows -1 (trade before our first_seen — brand new wallet)

### 4. Mitts/Ofir composite score — `MIN_COMPOSITE_SCORE` raised to 0.45
- Calibration on 179,204 resolved geo/elections trades confirmed:
  - 0.45 threshold → 700 trades → 59.4% win rate
  - 0.30 threshold → 32,837 trades → 51.6% win rate
- 30-day live backtest: 0 signals at calibrated threshold (correct — no noise)

### 5. RQ1.1 June 2026 script built and validated
- `rq1_1_elo_persistence.py` created, fully pre-registration compliant
- Fixed period boundaries, `trade_gap_flag` filter, NULL ELO exclusion, hard `n<30` exit, Spearman secondary, stopping rule check
- Contract validation range amended: `clean_pool [450,700]` → `[10000,20000]`; pool grew legitimately from 493 to 12,223 via leaderboard discovery
- Run confirmed: contract passes, `n=10 < 30` gate fires correctly
- `rq1_1_insufficient_n` signal written to `signals.json`, `next_run: 2026-07-01`
- Script ready for July 1 rerun

## Key Decisions

- Blockchain wallet data not viable for Pool C traders (proxy architecture)
- `first_seen` is the correct Polymarket-native wallet age proxy
- RQ1.1 will be INCONCLUSIVE on June 1 (`n=10`) — correct per pre-registration
- July 1 rerun is the real target with Period 2 extended to September 1
- Etherscan API retained for specific one-off investigations of non-proxy wallets

## Next Session Priorities

1. Test Tier 2.5 → Tier 3 handoff on a real research task (only viability test done so far — not tested on production work)
2. STR-003 concurrent markets criterion — all qualified geo_elo LEGENDARY traders disqualified by holding 15–1626 markets; strategy cannot fire
3. Clean up 620MB of April ELO recalc logs from `~/projects/first-repo/logs/`
4. Monitor overnight — did Fix 1+2+3 continue holding? Check for freeze events
5. June 1 — RQ1.1 will self-halt at `n<30`, no action needed
6. July 1 — RQ1.1 rerun with extended Period 2 (to September 1)
