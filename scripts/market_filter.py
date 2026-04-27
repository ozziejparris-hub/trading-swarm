"""
Standalone market filter module.

Copied verbatim from ~/projects/first-repo/monitoring/monitor.py:
  - _keyword_exclusion_check()  (exclusion_keywords list + all regex patterns)
  - geopolitics_signals list from _should_exclude_market()

No dependencies on first-repo classes (no Database, no PolymarketClient, etc.).
No AI/Ollama calls — keyword and regex only.
Last synced from monitor.py: 2026-04-25
"""

import re

# Fast-path geopolitics signals — verbatim from _should_exclude_market()
GEOPOLITICS_SIGNALS = [
    'election', 'president', 'presidential', 'war', 'strike', 'military',
    'sanctions', 'treaty', 'diplomat', 'congress', 'senate',
    'prime minister', 'parliament', 'government', 'minister',
    'ukraine', 'russia', 'china', 'israel', 'gaza', 'iran',
    'nato', 'un security', 'policy', 'tariff', 'peace deal',
    'middle east',
]

# Verbatim from _keyword_exclusion_check() in monitor.py
_EXCLUSION_KEYWORDS = [
    # CRYPTO - Major cryptocurrencies
    'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'xrp', 'ripple',
    'solana', 'sol', 'dogecoin', 'doge', 'cardano', 'ada',
    'price above', 'price below', 'up or down', 'dip to $',

    # CRYPTO AIRDROPS & TOKEN LAUNCHES
    'fdv above', 'fdv >', 'fdv>', 'market cap >', 'market cap>',
    'one day after launch', 'day after launch', '1 day after launch',
    'airdrop', 'token launch', 'token airdrop',

    # GOLD PRICE PREDICTIONS
    'gold close between', 'gold price', 'gold hits', 'gold hit', 'gold reaches',
    'gold above', 'gold below', 'gold closes', 'price of gold',

    # STOCKS - Major tickers and patterns
    'nvda', 'nvidia', 'tsla', 'tesla', 'aapl', 'apple',
    'msft', 'microsoft', 'googl', 'google', 'amzn', 'amazon',
    'meta', 'pltr', 'palantir', 'zm', 'zoom',
    'close at $', 'close above $', 'close below $',
    'finish week', 'quarterly earnings', 'beat earnings',

    # SPORTS BETTING - Critical patterns
    'spread:', 'o/u ', 'over/under', 'moneyline',
    '(-', '(+',  # Point spreads like "Bills (-5.5)"
    'touchdown', 'anytime touchdown', 'first touchdown',

    # SPORTS LEAGUES & CHAMPIONSHIPS
    'nfl', 'nba', 'mlb', 'nhl', 'mls',
    'premier league', 'champions league',
    'serie a', 'bundesliga', 'ligue 1', 'la liga',
    'super bowl', 'world series', 'stanley cup',
    'win the championship', 'make the playoffs',
    'australian open', 'wimbledon', 'french open', 'us open',
    'wta', 'tennis championship', 'tennis open',
    'merida open', 'rio open', 'open akron',
    'atp 250', 'atp 500', 'wta 250',
    'ufc', 'mma', 'nascar', 'pga tour',
    'formula 1', 'formula one', 'f1 ',
    'grand prix', 'grand slam',

    # SOCCER/FOOTBALL - Major teams
    'barcelona', 'manchester', 'real madrid', 'bayern',
    'liverpool', 'chelsea', 'arsenal', 'psg',
    'win on 2025', 'win on 202',  # Match date patterns

    # BRAZILIAN FOOTBALL
    'cruzeiro', 'flamengo', 'palmeiras', 'corinthians',

    # COLLEGE SPORTS
    'ohio state', 'georgia tech', 'alabama', 'michigan',

    # TRADITIONAL SPORTS - Teams and keywords
    'championship', 'playoff', 'vs.', 'game', 'match',
    'warriors', 'thunder', 'lakers', 'celtics', 'cowboys',
    'patriots', 'bills', 'chiefs', 'bengals',
    'maple leafs', 'bruins', 'atp',

    # ENTERTAINMENT - AWARDS & NOMINATIONS
    'academy award', 'oscar', 'oscars', 'grammy', 'grammys',
    'emmy', 'emmys', 'tony awards', 'golden globe', 'bafta',
    'cannes', 'sundance',
    'nominated for best', 'win best actor', 'win best actress',
    'win best director', 'win best picture', 'win best film',
    'best supporting actor', 'best supporting actress',
    'best documentary', 'best animated', 'best song',
    'best film editing', 'costume', 'editing', 'gross', 'grossing',
    'season', 'performance',

    # ENTERTAINMENT - MUSIC
    'songwriter of the year', 'album of the year', 'record of the year',
    'most streamed', 'streamed on spotify', 'spotify',

    # ENTERTAINMENT - MEDIA & STREAMING
    'movie', 'film', 'documentary', 'box office', 'opening weekend',
    'streamer of the year', 'twitch', 'kai cenat',

    # ENTERTAINMENT - BEAUTY PAGEANTS
    'miss universe', 'miss world', 'beauty pageant',
    'venezuela', 'thailand', 'canada',  # Common Miss Universe countries

    # ENTERTAINMENT - MISC
    'album', 'taylor swift',

    # WEATHER
    'temperature', 'highest temperature', 'weather',

    # APP RANKINGS
    '#1 free app', 'app store', 'chatgpt', 'threads',
    'apple app store', 'google play',

    # ATHLETE SEARCHES
    '#1 searched athlete', 'most searched', 'google searches',
    'caitlin clark', 'cristiano ronaldo', 'shohei ohtani',
    'simone biles', 'lamine yamal',

    # OTHER NON-GEOPOLITICS
    'elon musk', 'tweet', 'x post',
    'fed rate', 'interest rate', 'stock market', 'sp500', 's&p',

    # ESPORTS - Direct keywords
    'esports', 'e-sports', 'gaming tournament',

    # ESPORTS - Tournament keywords (future-proof across all games)
    'major', 'starladder', 'iem', 'intel extreme masters',
    'blast', 'esl', 'pgl', 'faceit', 'dreamhack',
    'worlds', 'masters', 'champions', 'the international',
    'epic league', 'weplay', 'gamers galaxy', 'rog',
    'bo3', 'bo5', 'map winner',

    # ESPORTS - Common team names (CS:GO, Valorant, LoL, Dota 2)
    'g2 esports', 'team vitality', 'fnatic', 'astralis',
    'natus vincere', "na'vi", 'navi', 'furia',
    'team falcons', 'ninjas in pyjamas', 'faze clan', 'faze',
    'cloud9', 'team liquid', 'team spirit', 'heroic',
    'mousesports', 'mouz', 'complexity', 'parivision',
    'tyloo', 'eternal fire', 'saw', 'imperial',
    '9 pandas', 'betboom', 'virtus.pro', 'virtus pro',
    'ence', 'big', 'godsent', 'og esports',
    't1 esports', 'gen.g', 'drx', 'jd gaming',
    'edward gaming', 'royal never give up', 'fpx',
    'nongshim', 'kt rolster', 'dplus', 'geng', 'kwangdong',
    'hanwha', 'diplus', 'sandbox gaming',

    # ESPORTS - Game titles
    'cs:go', 'csgo', 'counter-strike', 'counter strike', 'cs2',
    'league of legends', 'lol:', 'valorant', 'dota 2', 'dota2', 'dota',
    'overwatch', 'fortnite', 'rocket league', 'apex legends',
    'call of duty', 'rainbow six',

    # CRICKET/RUGBY
    'test match', 'odi', 't20', 'cricket world cup', 'ashes',
    'ipl', 'big bash', 'county championship',
    'rugby world cup', 'six nations', 'tri nations', 'super rugby',
    'rugby championship', 'rugby league',

    # GENERIC MATCH TERMS
    'match on', 'game on', 'fixture', 'vs on', 'versus on',

    # CLIMATE / WEATHER (137 active markets)
    'hurricane', 'named storm', 'tropical storm', 'tornado',
    'earthquake', 'wildfire', 'flood', 'drought',
    'temperature record', 'celsius', 'fahrenheit',
    'measles', 'pandemic', 'outbreak', 'epidemic',

    # OIL / COMMODITIES (153 active markets — price bets)
    'wti crude', 'brent crude', 'crude oil price',
    'oil price', 'price per barrel', 'barrel',
    'natural gas price', 'lumber price', 'wheat price',
    'corn price', 'soybean',

    # EQUITY INDICES / STOCKS
    'spy ', 'qqq ', 's&p 500', 'nasdaq', 'dow jones',
    'nifty', 'ftse', 'dax ', 'cac 40',
    'vix ', 'volatility index',
    'largest company', 'market cap end',

    # IPO MARKETS
    'ipo closing', 'ipo market cap', 'ipo by',
    'spacex ipo', 'kraken ipo', 'stripe ipo',
    'going public',

    # OLYMPICS / INTERNATIONAL GAMES
    'olympics', 'olympic games', 'medal count',
    'gold medal', 'podium finish',
    'commonwealth games', 'asian games', 'pan american',

    # VIDEO GAMES / GAMING (non-esports)
    'game launch', 'steam sales', 'launch day sales',
    'game of the year', 'goty',
    'copies sold', 'day one sales',

    # SOCIAL MEDIA POST COUNT MARKETS
    'post 200+', 'post 100+', 'posts from april',
    'posts from may', 'posts this week',
    'tweets this week', 'truth social posts',

    # REALITY TV / COMPETITION SHOWS
    'survivor', 'big brother', 'bachelor', 'bachelorette',
    'dancing with the stars', 'american idol', 'x factor',
    'love island', 'drag race',

    # AWARDS NOT ALREADY COVERED
    'booker prize', 'pulitzer', 'nobel prize',
    'man booker', 'hugo award',

    # MISCELLANEOUS NICHE
    'alien', 'ufo', 'bigfoot', 'paranormal',
    'will aliens', 'extraterrestrial',
    'lottery', 'powerball', 'mega millions',

    # INFLUENCER / YOUTUBE
    'mrbeast', 'million subscribers', 'subscribers by',

    # BOXING / COMBAT SPORTS (non-MMA)
    'go the distance', 'fight to go',

    # SPORTS DIVISION / CONFERENCE AWARDS
    'pro football draft',
    'pacific division', 'atlantic division',
    'metropolitan division', 'central division',
    'pacific conference', 'atlantic conference',
]

# Verbatim from _keyword_exclusion_check() in monitor.py
_SPORTS_ENTITIES = [
    # Cricket/Rugby nations
    'australia', 'england', 'india', 'pakistan', 'south africa',
    'new zealand', 'sri lanka', 'west indies', 'bangladesh',
    # Soccer nations (when in sports context)
    'brazil', 'argentina', 'france', 'germany', 'spain',
    'italy', 'portugal', 'netherlands', 'belgium',
    # US Sports cities
    'boston', 'new york', 'chicago', 'philadelphia',
    'dallas', 'houston', 'miami', 'seattle',
]

_GEO_MARKERS = ['election', 'vote', 'president', 'minister',
                 'parliament', 'policy', 'government', 'referendum']

# Structural patterns that catch sports regardless of team/player names
SPORT_PATTERNS = [
    r'.+:\s*.+\s+vs\s+.+',        # "City/Tournament: Player vs Player"
    r'^exact score:',              # Exact score betting
    r'anytime goalscorer',         # Soccer goalscorer markets
    r'^map \d+:',                  # Esports map betting
    r'leading at halftime',        # Soccer halftime markets
    r'xauusd|xagusd|wti crude',   # Commodity tickers
    r'nhl.*(trophy|division|conference)',  # NHL awards
    r'nba.*(trophy|division|conference)', # NBA awards
    r'\d+\s*-\s*\d+.*\?$',       # Score prediction format
    # Post count markets (Will X post N-M posts from DATE to DATE?)
    r'post\s+\d+[-–]\d+\s+posts',
    r'post\s+\d+\+\s+posts',
    # Price target markets (Will X hit $N by DATE?)
    r'hit \(high\)',
    r'hit \(low\)',
    r'hit \$[\d,]+',
    # Goalscorer / player performance
    r'top .* goal scorer',
    r'anytime (goal|try|touchdown)',
    r'first (goal|try|touchdown)',
    # NFL draft pick markets
    r'drafted \d+(st|nd|rd|th) overall',
    # "Will X say Y during Z" trivial speech markets
    r'will .+ say ".+" during',
    # Press briefing lateness markets
    r'be \d+[-–]\d+ minutes late',
]


def _keyword_exclusion_check(market_title: str) -> bool:
    """
    Returns True if the market matches exclusion criteria
    (crypto/sports/entertainment/esports). Verbatim logic from monitor.py.
    """
    title_lower = market_title.lower()

    # Check if any exclusion keyword is in the title
    for keyword in _EXCLUSION_KEYWORDS:
        if keyword in title_lower:
            return True

    # REGEX PATTERN DETECTION - Catches patterns that keywords might miss

    # PATTERN: Spread betting (captures any point spread like "(-5.5)")
    if re.search(r'spread:.*\(-?\d+\.?\d*\)', title_lower):
        return True  # EXCLUDE sports spread betting

    # PATTERN: Over/Under betting (captures "O/U 61.5")
    if re.search(r'o/u\s+\d+\.?\d*', title_lower):
        return True  # EXCLUDE over/under bets

    # PATTERN: Stock price ranges "$XXX-$YYY"
    if re.search(r'close at \$\d+-\$\d+', title_lower):
        return True  # EXCLUDE stock price predictions

    # PATTERN: Gold price ranges "$X-$Y" (e.g., "gold close between $3500 and $3600")
    if re.search(r'gold.*\$\d+.*and.*\$\d+', title_lower):
        return True  # EXCLUDE gold price predictions

    # PATTERN: "Will [Team] win on [Date]" - Soccer/sports matches
    if re.search(r'will \w+ win on 20\d{2}-\d{2}-\d{2}', title_lower):
        return True  # EXCLUDE soccer/sports matches

    # PATTERN: Beauty pageants (Miss Universe, Miss World, etc.)
    if 'miss universe' in title_lower or 'miss world' in title_lower:
        return True  # EXCLUDE beauty pageants

    # PATTERN: "#1 searched" or "#1 app" rankings
    if '#1' in title_lower and any(x in title_lower for x in ['searched', 'app', 'free app']):
        return True  # EXCLUDE ranking markets

    # ESPORTS PATTERN DETECTION: "Will [Team] win the [Tournament]?"
    # This catches esports markets even if team/tournament names aren't in our keyword list
    if title_lower.startswith('will ') and ' win the ' in title_lower:
        # Extract what comes after "win the" to check if it's a tournament context
        parts = title_lower.split(' win the ')
        if len(parts) >= 2:
            tournament_part = parts[1]

            # Indicators this is likely an esports/gaming tournament:
            tournament_indicators = [
                # Year patterns (tournaments often have years)
                '2024', '2025', '2026', '2027',
                # Generic tournament words that appear in esports but not politics
                'tournament', 'cup', 'league', 'season',
            ]

            # Words that prove this is geopolitics, not a tournament
            _geo_guard = ['election', 'president', 'presidential', 'minister',
                          'parliament', 'vote', 'war', 'treaty', 'senate', 'congress',
                          'referendum', 'campaign', 'primary', 'ceasefire']

            for indicator in tournament_indicators:
                if indicator in tournament_part:
                    if not any(word in tournament_part for word in _geo_guard):
                        return True

            # Check if the team name (before "win the") contains typical esports markers
            team_part = parts[0].replace('will ', '')
            esports_team_markers = [
                'team ', 'clan', 'gaming', 'esports', 'e-sports',
            ]

            for marker in esports_team_markers:
                if marker in team_part:
                    return True

    # ===== VAGUE SPORTS MATCH DETECTION =====
    # Short, context-free "Will X win?" = likely sports
    # These lack the specificity of geopolitics ("Will X win the presidential election?")
    if len(market_title) < 50:
        # Pattern: "Will [name] win?" with no context
        if re.search(r'^will [\w\s]+ win(\?)?$', title_lower.strip()):
            # Check if it has geopolitics context
            geo_context = ['election', 'president', 'presidential', 'minister',
                           'parliament', 'vote', 'campaign', 'primary', 'referendum']

            if not any(ctx in title_lower for ctx in geo_context):
                return True  # EXCLUDE vague match without geopolitics context

    # ===== SPORTS COUNTRY/TEAM IN NON-GEOPOLITICS CONTEXT =====
    # Countries that appear frequently in cricket, rugby, soccer betting
    for entity in _SPORTS_ENTITIES:
        if entity in title_lower and 'win' in title_lower:
            # Check for geopolitics markers
            if not any(marker in title_lower for marker in _GEO_MARKERS):
                return True  # EXCLUDE country without geopolitics context

    # ===== MATCH WITH DATE PATTERN =====
    # "Will X win on [date]" or "Will X win [month] [day]" = sports match
    if re.search(r'will \w+ win (on )?(20\d{2}[-/]\d{2}[-/]\d{2}|\w+ \d{1,2})', title_lower):
        # Check if it's NOT an election date
        if 'election' not in title_lower and 'vote' not in title_lower:
            return True  # EXCLUDE match with specific date

    # Structural patterns that catch sports regardless of team/player names
    for pattern in SPORT_PATTERNS:
        if re.search(pattern, title_lower):
            return True

    return False


def should_include_market(title: str) -> bool:
    """
    Returns True if market should be included in analysis.
    Copied verbatim from first-repo/monitoring/monitor.py
    _keyword_exclusion_check() and _should_exclude_market().
    No AI/Ollama — keyword and regex only.
    Last synced from monitor.py: 2026-04-25 (extended categories)
    """
    # Keyword/regex exclusion runs first — prevents 'president' in "Presidents' Trophy"
    # from short-circuiting via the geopolitics fast-path before NHL exclusion fires.
    if _keyword_exclusion_check(title):
        return False

    # Geopolitics fast-path: strong signal → include
    title_lower = title.lower()
    if any(signal in title_lower for signal in GEOPOLITICS_SIGNALS):
        return True

    # Default: conservative, include if uncertain
    return True
