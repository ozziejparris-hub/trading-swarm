#!/usr/bin/env python3
"""
run_trader_profiling.py

Generates structured trader profile cards for all core traders (LEGENDARY + NEAR-LEGENDARY)
using Claude Sonnet via Anthropic API. Profiles stored as individual JSON files in
brain/trader-profiles/. Designed for weekly delta updates by trader-intelligence-agent.

Usage:
  python3 run_trader_profiling.py              # profile all traders
  python3 run_trader_profiling.py --update     # only update traders with new resolved trades
  python3 run_trader_profiling.py --tier legendary  # only LEGENDARY tier
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

PROFILES_DIR = Path('/home/parison/trading-swarm/brain/trader-profiles')
PROFILES_DIR.mkdir(exist_ok=True)

INPUT_FILE = Path('/home/parison/trading-swarm/brain/mythos_profiling_input.json')

SYSTEM_PROMPT = """You are a quantitative analyst for a Polymarket trading intelligence system.
Your job is to produce structured trader profile cards from raw trade data.

You must respond with ONLY a valid JSON object. No preamble, no explanation, no markdown fences.

The system tracks prediction market traders on geopolitics and elections markets.
Key concepts:
- geo_elo_active: recency-decayed ELO score (threshold for LEGENDARY = 2175)
- directionality: fraction of trades going the same direction (near 1.0 = always buys same side)
- Near-certainty trading: buying YES at 0.95+ or NO at 0.05- is not genuine forecasting
- LP_ARTIFACT: traders placing both YES and NO to provide liquidity (directionality ~0.5)
- Genuine forecasters: diverse markets, directional conviction, entry at contested prices (0.10-0.80)

Archetypes to classify into (pick the single best fit):
- GENUINE_FORECASTER: diverse markets, real directional calls, contested price entries
- DOMAIN_SPECIALIST: genuine edge in 1-2 domains, noise outside them
- VOLUME_SPECIALIST: high accuracy from niche theme repetition (ceasefire, single candidate)
- YIELD_HARVESTER: near-certainty positions, collecting small premiums on obvious outcomes
- CONVICTION_SIZER: large positions on strong views, occasionally catastrophic losses
- DORMANT: was active, now inactive after large loss or withdrawal
- THIN_SAMPLE: fewer than 30 resolved trades, archetype unclear"""

PROFILE_PROMPT = """Analyse this trader and produce a structured profile card.

TRADER DATA:
{trader_json}

Produce a JSON profile with exactly these fields:

{{
  "address": "full address",
  "profile_date": "YYYY-MM-DD",
  "geo_elo_active": number,
  "tier": "LEGENDARY|NEAR_LEGENDARY|ELITE",
  "archetype": "one of the 7 archetypes above",
  "archetype_confidence": "HIGH|MEDIUM|LOW",
  "archetype_reasoning": "2-3 sentences explaining the classification. Be specific about trade patterns.",

  "primary_domain": "Trump_US|LatAm|Russia_UKR|Iran_ME|Europe|China_Asia|Other|DIVERSE",
  "domain_strengths": ["domain1", "domain2"],
  "domain_blindspots": ["domain: reason for caution"],
  "domain_summary": "1-2 sentences on where this trader has genuine edge vs where to discount",

  "signal_weight": "FULL|PARTIAL|DOMAIN_ONLY|MINIMAL|EXCLUDE",
  "signal_weight_reasoning": "Why this weight recommendation for STR-003 signal generation",
  "trusted_domains": ["domains where FULL weight applies"],
  "discounted_domains": ["domains where signal should be ignored or discounted"],

  "behavioural_flags": ["list of notable patterns: entry timing, sizing, doubling-down, exits"],
  "risk_patterns": ["patterns that suggest caution: sunk-cost behaviour, concentration, etc"],

  "notable_calls": [
    {{"market": "short title", "side": "YES/NO", "entry_price": 0.0, "result": "WON/LOST/OPEN", "significance": "why this call matters"}}
  ],

  "open_positions_summary": "Brief summary of current live bets and what thesis they imply",
  "watch_items": ["specific things to monitor about this trader in coming weeks"],

  "overall_signal_value": "HIGH|MEDIUM|LOW|NOISE",
  "summary": "3-4 sentence overall assessment. Be direct. Note strengths and weaknesses."
}}"""


def profile_trader(trader_data: dict) -> dict:
    """Send single trader to Claude Sonnet for profiling."""

    # Trim to keep context manageable - most recent 15 trades only
    trimmed = dict(trader_data)
    trimmed['recent_resolved'] = trader_data.get('recent_resolved', [])[:15]

    trader_json = json.dumps(trimmed, indent=2)

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return {
            'address': trader_data.get('address'),
            'profile_date': datetime.now().strftime('%Y-%m-%d'),
            'error': 'ANTHROPIC_API_KEY not set',
            'geo_elo_active': trader_data.get('geo_elo_active'),
        }

    try:
        import urllib.request

        payload = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 3000,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": PROFILE_PROMPT.format(trader_json=trader_json)}
            ]
        }

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            response = json.loads(resp.read())

        # Extract text content
        content = response.get('content', [])
        text = ''
        for block in content:
            if block.get('type') == 'text':
                text += block.get('text', '')

        # Clean and parse JSON
        text = text.strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
        if text.endswith('```'):
            text = text.rsplit('```', 1)[0]
        text = text.strip()

        try:
            profile = json.loads(text)
        except json.JSONDecodeError:
            # Truncated response: back off from the end until the longest
            # valid prefix parses once we re-close the open object.
            profile = None
            for i in range(len(text), 0, -1):
                for suffix in ('"}', '}'):
                    try:
                        profile = json.loads(text[:i] + suffix)
                        break
                    except json.JSONDecodeError:
                        continue
                if profile is not None:
                    break
            if profile is None:
                raise json.JSONDecodeError("unrepairable truncated JSON", text, 0)
        profile['profile_date'] = datetime.now().strftime('%Y-%m-%d')
        profile['data_snapshot'] = {
            'geo_elo': trader_data.get('geo_elo'),
            'geo_elo_active': trader_data.get('geo_elo_active'),
            'resolved_trades': trader_data.get('geo_resolved_trades'),
            'distinct_markets': trader_data.get('distinct_geo_markets'),
            'directionality': trader_data.get('directionality'),
            'pnl': trader_data.get('realized_pnl'),
        }
        return profile

    except Exception as e:
        return {
            'address': trader_data.get('address'),
            'profile_date': datetime.now().strftime('%Y-%m-%d'),
            'error': str(e),
            'geo_elo_active': trader_data.get('geo_elo_active'),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--update', action='store_true',
                        help='Only re-profile traders with new trades since last profile')
    parser.add_argument('--tier', choices=['legendary', 'near_legendary', 'all'],
                        default='all')
    parser.add_argument('--limit', type=int, default=None,
                        help='Max traders to profile (for testing)')
    args = parser.parse_args()

    with open(INPUT_FILE) as f:
        all_traders = json.load(f)

    # Filter by tier
    targets = {}
    for short_addr, data in all_traders.items():
        elo = data.get('geo_elo_active', 0)
        if args.tier == 'legendary' and elo < 2175:
            continue
        if args.tier == 'near_legendary' and not (1800 <= elo < 2175):
            continue

        # Skip if recent profile exists and --update not requested
        profile_path = PROFILES_DIR / f"{data['address']}.json"
        if not args.update and profile_path.exists():
            existing = json.loads(profile_path.read_text())
            if existing.get('profile_date') == datetime.now().strftime('%Y-%m-%d'):
                print(f"  SKIP {short_addr} (profiled today)")
                continue

        targets[short_addr] = data

    if args.limit:
        targets = dict(list(targets.items())[:args.limit])

    print(f"Profiling {len(targets)} traders...")
    print(f"Output: {PROFILES_DIR}")
    print()

    results = {'profiled': 0, 'errors': 0, 'skipped': 0}

    for i, (short_addr, trader_data) in enumerate(targets.items()):
        elo = trader_data.get('geo_elo_active', 0)
        tier = 'LEGENDARY' if elo >= 2175 else 'NEAR_LEGENDARY' if elo >= 1800 else 'ELITE'
        print(f"[{i+1}/{len(targets)}] {short_addr} | {tier} | elo={elo:.0f} | ", end='', flush=True)

        profile = profile_trader(trader_data)

        if 'error' in profile:
            print(f"ERROR: {profile['error']}")
            results['errors'] += 1
        else:
            # Write profile
            profile_path = PROFILES_DIR / f"{trader_data['address']}.json"
            profile_path.write_text(json.dumps(profile, indent=2))

            archetype = profile.get('archetype', '?')
            signal_val = profile.get('overall_signal_value', '?')
            primary = profile.get('primary_domain', '?')
            print(f"{archetype} | {signal_val} | domain={primary}")
            results['profiled'] += 1

        # Rate limit - 1 request per second
        if i < len(targets) - 1:
            time.sleep(1)

    print()
    print(f"Complete: {results['profiled']} profiled, {results['errors']} errors")

    # Write summary index
    index = {}
    for profile_file in PROFILES_DIR.glob('*.json'):
        try:
            p = json.loads(profile_file.read_text())
            if 'error' not in p:
                index[p['address']] = {
                    'tier': p.get('tier'),
                    'archetype': p.get('archetype'),
                    'overall_signal_value': p.get('overall_signal_value'),
                    'primary_domain': p.get('primary_domain'),
                    'signal_weight': p.get('signal_weight'),
                    'profile_date': p.get('profile_date'),
                    'geo_elo_active': p.get('geo_elo_active'),
                }
        except:
            pass

    index_path = PROFILES_DIR / '_index.json'
    index_path.write_text(json.dumps(index, indent=2))
    print(f"Index written: {len(index)} profiles → {index_path}")


if __name__ == '__main__':
    main()
