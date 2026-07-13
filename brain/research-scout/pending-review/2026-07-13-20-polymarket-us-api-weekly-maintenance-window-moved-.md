# Polymarket US API: weekly maintenance window moved to Thursday 02:00-06:00 ET, effective July 9, 2026
## Source
https://docs.polymarket.us/changelog
## Domain
docs.polymarket.us
## Summary
Polymarket's official changelog confirms the weekly API maintenance window shifted from Thursday 06:00-08:00 ET to Thursday 02:00-06:00 ET starting July 9, 2026. Any scheduled scrapes, signal pulls, or order actions during that window on Thursdays may fail or return stale data.
## Action
Check orchestrator/agent cron schedules for Thursday-morning ET jobs that hit the Polymarket API and shift them outside 02:00-06:00 ET.
## Verified
Yes — fetched via Claude CLI web search
