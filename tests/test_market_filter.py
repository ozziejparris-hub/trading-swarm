"""
test_market_filter.py
Tests for scripts/market_filter.py — should_include_market().
Complex logic: 300+ exclusion keywords, 12+ regex patterns, no external deps.
Run from repo root: python3 -m pytest tests/test_market_filter.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from scripts.market_filter import should_include_market


class TestSportsExclusion:
    """Known sports markets must return False."""

    def test_nba_teams(self):
        assert should_include_market("Will the Lakers beat the Warriors?") is False

    def test_nfl_championship(self):
        assert should_include_market("Super Bowl 2026: Who will win?") is False

    def test_soccer_league(self):
        assert should_include_market(
            "Will Manchester United win the Premier League 2026?"
        ) is False

    def test_tennis_grand_slam(self):
        assert should_include_market("Wimbledon 2026 Men's Singles winner?") is False

    def test_ufc_fight(self):
        assert should_include_market(
            "Will Jon Jones win the UFC heavyweight title?"
        ) is False


class TestGeopoliticsInclusion:
    """Known geopolitics markets must return True."""

    def test_presidential_election(self):
        assert should_include_market(
            "Will Donald Trump win the 2026 presidential election?"
        ) is True

    def test_ceasefire_agreement(self):
        assert should_include_market(
            "Will Russia and Ukraine agree to a ceasefire by December 2026?"
        ) is True

    def test_parliament_vote(self):
        assert should_include_market(
            "Will UK parliament vote on new immigration policy before June?"
        ) is True

    def test_sanctions_policy(self):
        assert should_include_market(
            "Will the US impose new sanctions on Iran in 2026?"
        ) is True


class TestCryptoExclusion:
    """Crypto price and token markets must return False."""

    def test_bitcoin_price(self):
        assert should_include_market(
            "Will Bitcoin price be above $100,000 by end of 2026?"
        ) is False

    def test_eth_price(self):
        assert should_include_market("Will ETH hit $5,000 by June 2026?") is False

    def test_token_airdrop(self):
        assert should_include_market(
            "Will the new token airdrop exceed 1M addresses?"
        ) is False


class TestAmbiguousWillXWin:
    """Vague 'Will X win?' without geopolitics context must return False."""

    def test_country_no_geo_context(self):
        # "brazil" is in _SPORTS_ENTITIES; "win" present; no geo markers
        assert should_include_market("Will Brazil win?") is False

    def test_player_name_no_context(self):
        # Short title matching vague sports pattern; no geo context
        assert should_include_market("Will Federer win?") is False

    def test_election_context_keeps_true(self):
        # Same structure but WITH election context — must be included
        assert should_include_market(
            "Will Candidate X win the presidential election?"
        ) is True


class TestEdgeCases:
    """Edge cases that must not crash and must return predictable results."""

    def test_empty_string(self):
        # No keywords, no geo signals — default include
        assert should_include_market("") is True

    def test_very_long_title(self):
        # 300-char title with no exclusion keywords — default include
        long_title = ("Long neutral title about nothing specific " * 8)[:300]
        assert should_include_market(long_title) is True

    def test_title_with_slash(self):
        # Forward slash must not crash regex patterns
        assert should_include_market(
            "Will USD/EUR exchange rate exceed 1.10 by Q3?"
        ) is True

    def test_title_with_emoji(self):
        # Emoji after "win?" breaks the vague-sports $ anchor — should include
        assert should_include_market("Will X win? 🏆") is True

    def test_whitespace_only(self):
        # No keywords, no geo signals — default include
        assert should_include_market("   ") is True

    def test_apostrophe_in_name(self):
        # Apostrophe must not crash; election context keeps result True
        assert should_include_market(
            "Will O'Brien win the presidential election?"
        ) is True
