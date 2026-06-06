# STR-003 Inter-Signal Conflict Gap
**Identified:** 2026-06-06
**Priority:** LOW — resolves naturally as markets resolve
**Status:** DOCUMENTED, not yet implemented

## The Gap
signal-agent has no inter-signal conflict check for same-election markets.

## Example
STR003-005 (Keiko Fujimori YES, $3,836) and STR003-006 (López Aliaga YES, $4,958) are both ACTIVE signals on the same June 7 2026 Peruvian presidential election first round. Only one candidate can win. Both signals were correctly registered per STR-003 criteria — the same LEGENDARY trader (0xecaa8806) holds both positions simultaneously, likely as a multi-scenario bet on first-round dynamics.

## Recommended Fix
Before registering a new STR-003 signal, signal-agent should:
1. Check if an active signal already exists for the same market's parent election/event
2. If so, flag the new signal as status: "CONFLICTING" with a note referencing the existing signal
3. Still register it — the trader's position is real — but alert Oscar to review

## Implementation Note
This requires the signal-agent to identify "sibling markets" — markets that are part of the same election event. The market title and resolution_date are the best proxies. Markets with the same resolution_date and overlapping title keywords (candidate names for the same election) should be flagged.

## Resolution
Will self-resolve June 7 2026 when Peru markets settle. Implement before next major election cycle with multiple candidate markets.
