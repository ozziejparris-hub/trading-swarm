# Telegram Bot Token Logged in Cleartext — Root Cause, Fix, Verification

**Scope:** logging fix only. Token not rotated. journalctl history not
purged. `.env_trading` not modified. No alert path disabled. Observer not
restarted. Found in the 2026-09-11 progression check (Server Setup 16,
Section 9): polymarket-observer's journal contained the live Telegram bot
token in cleartext in an HTTP request log line.

Tagging: [V]=verified this session (code/log/live read, or run directly),
[I]=inferred.

---

## PART 1 — Scope

### 1.1 Root cause — the exact code path [V]

The leaked line:

```
2026-09-11 10:13:17 - INFO - HTTP Request: POST https://api.telegram.org/bot<REDACTED-LIVE-TOKEN>/sendMessage "HTTP/1.1 200 OK"
```

This is **httpx's own built-in request logger, not project code building a
log message.** `python-telegram-bot` v22.7's `Bot` class uses `httpx`
0.28.1 as its HTTP backend. httpx logs every request at INFO through
`logging.getLogger("httpx")`:

```python
# httpx/_client.py:117
logger = logging.getLogger("httpx")
...
# httpx/_client.py:1025-1031 (and :1740, the async path)
logger.info(
    'HTTP Request: %s %s "%s %d %s"',
    request.method, request.url,
    response.http_version, response.status_code, response.reason_phrase,
)
```

Telegram's Bot API puts the bot token in the URL path
(`/bot<TOKEN>/sendMessage`), not in a header, so `request.url` — logged
verbatim — contains the live credential. This is standard, documented
httpx behavior (its own docs note the same thing and recommend capping
this logger), not something anyone in this project wrote.

**Why it was invisible until now:** by default this logger's effective
level resolves to the root logger's (`NOTSET` → root's default is
`WARNING` with no handler, so nothing is emitted). It only becomes visible
once *something* in the process calls `logging.basicConfig(level=INFO,
...)`, which installs a handler on the root logger and raises the
effective level for every logger that hasn't set its own level —
`"httpx"` included.

Confirmed [V]: three project modules do exactly this, unconditionally, at
**import time** (module top level, not inside a function):

```python
# analysis/calibration_analysis.py:37-41
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

# analysis/risk_adjusted_returns.py:41-45  — identical
# analysis/regret_analysis.py:38-42        — identical
```

`logging.basicConfig()` is a one-shot no-op after the first call in a
process, so whichever of these gets imported first wins for the rest of
that process's lifetime. In the observer, `system_observer.py`'s daily
01:00 UTC analysis-scheduler trigger deferred-imports
`analysis.risk_adjusted_returns` (`analysis_scheduler.py:1059`) and
`analysis.calibration_analysis` (`:1110`). Once that fires once a day, the
observer process's root logger is INFO+handler for its remaining uptime,
and every subsequent httpx call — including every later Telegram send —
gets its full URL (token included) written to stderr, which systemd
captures into the journal. `monitoring/main.py:71` does the same
`logging.basicConfig(level=INFO, handlers=[FileHandler('logs/monitoring.log'),
StreamHandler()])` **unconditionally at its own top level**, so the
monitoring service's root logger is INFO+handler from process start,
every time.

httpcore (httpx's own transport layer) was checked too: it only logs via
`self.logger.debug(...)` (`httpcore/_trace.py:47,87`) — below INFO, so it
was never a leak vector even under the current config. python-telegram-bot's
own `telegram/request/_httpxrequest.py` adds no logging of its own; httpx
is the sole source.

### 1.2 Every sender checked [V/I]

| Sender | Live? | HTTP client | Leak vector present? | Action |
|---|---|---|---|---|
| `monitoring/system_observer.py` → `telegram_health_bot.py` (`TelegramHealthBot`) | **YES** — confirmed leaking today, `polymarket-observer.service` | `telegram.Bot` → httpx | **YES, confirmed** | **Fixed** |
| `scripts/audit_invariants.py` (`_send_telegram_async`) | YES — daily_maintenance step 7, sends when invariants alert | `telegram.Bot` → httpx | Not observed leaking (its process never independently calls `logging.basicConfig`), but nothing stops something upstream of it doing so | **Fixed defensively** |
| `scripts/check_canonical_definitions.py` (`_send_telegram_async`) | YES — daily_maintenance step 8; fixed 2026-09-07 (`51e3b74`) to actually load credentials, so this is a genuinely live path now, not moot | `telegram.Bot` → httpx | Same as above — not observed leaking, same latent exposure | **Fixed defensively** |
| `monitoring/telegram_bot.py` (`TelegramNotifier`) | **NO** — `monitor.py:86-87` hardcodes `self.telegram = None`, `self.elo_bot = None`, deliberately disabled since 2026-01-27 (`423b3b5`, per [[2026-09-07-telegram-alert-audit]]); confirmed still true this session [V] | `telegram.Bot`/`telegram.ext.Application` → httpx | Dead code path currently — cannot leak because it is never instantiated | **Fixed defensively** (in case ever reactivated; `monitoring/main.py` already runs INFO+handler unconditionally, so if this bot is ever turned back on the exposure is immediate and every alert type leaks) |
| `trading-swarm/orchestrator/orchestrator.py` (`send_telegram`) | YES, continuous | manual `urllib.request` | **No** — `urllib.request`/`http.client` has no logging integration by default; only `log.info(f"Telegram [{bot}]: {message[:80]}...")` is emitted, which logs the message text, never the URL/token | None needed |
| `trading-swarm/scripts/run_feedback_loop_agent.py` | YES, weekly cron `0 7 * * 1` | manual `urllib.request` | No, same reason | None needed |
| `trading-swarm/scripts/polymarket_changelog_monitor.py` | YES, weekly cron `30 7 * * 1` | manual `urllib.request` | No, same reason | None needed |
| `orchestrator/ollama_agent_loop.py` (`tool_send_telegram`) | YES, agent tool | manual `urllib.request` (per grep — no `httpx`/`requests` import in the module) | No, same reason | None needed |
| `monitoring/health_checker.py` (`check_telegram_bots`) | YES, but only does `from telegram import Bot` to test importability — no `Bot(token=...)`, no network call (comment: "removed token validation — too strict and network-dependent") | n/a | No — never makes a request | None needed |
| `monitoring/telegram_elo_bot.py` | **NO** — not imported by any live entrypoint; only referenced by `scripts/verify_telegram_fix.py` and two files under `scripts/archive/` | `telegram.Bot` → httpx | Latent (dead code) | **Not fixed** — flagged for Oscar; trivial to patch the same way if ever revived |
| `scripts/get_telegram_chat_id.py` | Manual one-off setup utility, not part of any cron/systemd/daily_maintenance path [V] | `telegram.Update`/likely `Application` polling | Latent, low-priority — a human runs this interactively, output goes to their own terminal, not journald, unless they redirect it | **Not fixed** — out of scope, noted for Oscar |
| `data/characterizations/sweep_common/sweep_terminal_signal.py` | **NO** — belongs to the sweep effort formally stopped 2026-09-04 ([[project_limit_restore_and_sweep_closure]]); referenced only by its own test and by other stopped-sweep segment scripts | `telegram.Bot` → httpx | Latent (dead code) | **Not fixed** — out of scope, dead code from a closed initiative |
| `scripts/detect_counter_signals.py` (`_fire_alert`), `scripts/register_signal.py` (`_fire_telegram_alert`) | Live triggers, but per [[2026-09-07-telegram-alert-audit]] Part 1, both only `print()` — **no Telegram API call exists in either function** | n/a | No — structurally cannot leak, cannot even send | None needed |

Net: **4 files fixed** (the one confirmed-leaking sender plus three more
using the same library that could leak under the same conditions). Three
additional files identified as using the library but currently dead code
— reported, not fixed, per the "small and contained" framing; trivial
one-liner if Oscar wants them covered too.

### 1.3 How far back in journalctl, and whether it's the live token [V/I]

**Confirmed [V]: this is the live, currently-active token.** Compared
against `.env_trading` without ever printing the value (boolean
comparison only, run in a subshell): the leaked token matches
`telegram_alerts_token`, `TELEGRAM_BOT_TOKEN`, **and**
`TELEGRAM_AGENTS_TOKEN`. It is not a stale/rotated credential —
`TELEGRAM_ORCHESTRATOR_TOKEN` and `TELEGRAM_METRICS_TOKEN` are different
values and unaffected.

**Extent — partially bounded, not exhaustively determined [V/I]:**

- The current `polymarket-observer` process has 0 restarts and has been
  running continuously since **2026-09-09 18:25:58 UTC** (`systemctl show
  -p ExecMainStartTimestamp`). The confirmed leak (10:13:17 UTC today)
  falls inside that window. The daily 01:00 UTC analysis-scheduler trigger
  that flips the process into the leaking state would have fired at least
  twice in that window (Sep 10 and Sep 11, both 01:00 UTC) — consistent
  with, though not proof of, every Telegram send since roughly Sep 10
  01:00 UTC onward also having leaked.
- Whether **prior** observer process instances (before Sep 9 18:25) also
  leaked was **not determined**. `journalctl -g` (regex search) across the
  full journal — which spans back to boot `-9`, 2026-07-18 — did not
  complete inside 90-120s and was killed rather than left running
  unattended; even scoped to just the `polymarket-observer` unit, a
  single-unit full-history grep was killed by its own 60s timeout without
  finishing. This box has a documented history of near-total
  unresponsiveness from unmonitored runaway processes; I judged an
  open-ended grep across 3.0 GB of multi-boot journal not worth the risk
  to establish a number that Part 4's rotation question likely moots
  anyway.
- **journal retention**: `/etc/systemd/journald.conf` has no explicit
  `SystemMaxUse`/`MaxRetentionSec` (all commented/default) — distro
  defaults apply (bounded by available disk, not by a fixed time window).
  Current usage: 3.0 GB, oldest entries from boot `-9`
  (2026-07-18 03:00 UTC) through the current boot (`0`, since
  2026-09-06 03:00 UTC). So the token *could* be present anywhere from
  2026-07-18 to now if this condition existed earlier — not established
  either way.

**File-based logs and committed artifacts — checked, clean [V]:**

- `logs/monitoring.log` (142 MB, spans 2026-04-18 → now, continuously
  appended by the same `FileHandler`): **0 matches** for
  `api.telegram.org` or the token. (Consistent with §1.2: the sender that
  would write here, `telegram_bot.py`'s `TelegramNotifier`, has been dead
  code since January.)
- `logs/daily_maintenance.log`: **0 matches**.
- Full git history, both repos, `git log --all -S"<token>"`: **0 commits**
  in either repo ever added or removed a line containing the token. STOP
  condition not triggered.
- Working tree (tracked + untracked) of both repos' actual source/doc
  trees (`scripts/`, `monitoring/`, `analysis/`, `docs/`, `brain/`,
  `tests/`, `archive/`, `paper_trading/`, `experiments/`, `config/`, and
  top-level files): **0 matches**.
- **Not checked**, and flagged rather than assumed clean: first-repo's
  `backups/` (466 GB — confirmed by directory listing to be exclusively
  `.db` SQLite snapshots, not logs, so structurally an implausible vector
  for a *log line* regardless), `data/` outside the tracked source tree
  (126 GB, mostly the live DB + `data/external` 1.3 GB + `data/characterizations`
  149 MB + `data/checkpoints` 16 MB — JSON/checkpoint output files, not
  terminal captures, so also a low-probability vector but not exhaustively
  grepped), and `reports/` (182 MB). None of these were grepped — two
  broad greps against the full repo tree (including these directories)
  were killed by their own timeouts before finishing, for the same
  box-load reasons as the journal search.

---

## PART 2 — The fix

**One line, defensive, applied at the point each sender constructs its
`Bot`:**

```python
logging.getLogger("httpx").setLevel(logging.WARNING)
```

This works regardless of *when* it runs relative to any `basicConfig`
call elsewhere in the process: a logger's own explicitly-set level takes
precedence over the inherited root level when Python resolves whether a
given call is enabled, so once `"httpx"`'s level is explicitly `WARNING`,
its `logger.info(...)` request-line call is filtered out no matter what
the root logger's handler/level end up being.

**Files changed (first-repo):**

- `monitoring/telegram_health_bot.py` — added at module top level, right
  after `from telegram import Bot` (the observer's sender — this is the
  one confirmed leaking).
- `monitoring/telegram_bot.py` — added at module top level, same
  placement (currently dead code per §1.2, fixed for when/if reactivated).
- `scripts/check_canonical_definitions.py` — added inside
  `_send_telegram_async`, immediately before `Bot(token=token)` (this
  function does its `telegram` import locally/deferred, not at module
  top, so the guard has to live at the same point).
- `scripts/audit_invariants.py` — same placement, same reasoning.

**What still logs after the change — nothing about error visibility was
touched:**

- httpx communicates transport failures (timeouts, connection errors, bad
  status codes it's asked to raise for) via **raised exceptions**
  (`httpx.RequestError`, etc.), not via `logger.error()`/`logger.warning()`
  calls on this logger — confirmed by reading `httpx/_client.py` and
  `httpcore`'s trace module; neither calls this logger above INFO for
  anything. So capping `"httpx"` to WARNING loses only the benign
  access-log line, nothing else.
- Every sender's own error handling is untouched and still fires exactly
  as before: `check_canonical_definitions.py`/`audit_invariants.py` still
  `print(f"[TELEGRAM] Failed: {exc}", file=sys.stderr)` on any exception;
  `telegram_health_bot.py._send_message` still
  `print(f"[TELEGRAM] Error sending message: {e}")`/`"[TELEGRAM] Unexpected
  error: {e}"` on failure, and still executes its 429 retry-with-backoff
  logic. None of this touches the `"httpx"` logger — these are all
  application-level `except` blocks around the awaited call.
- `monitoring/main.py`'s and `analysis/{calibration,risk_adjusted,regret}`'s
  own `basicConfig(level=INFO, ...)` calls are **unchanged** — the
  project's own INFO-level operational logging (the thing the
  2026-09-07 audit said needs to stay visible, given alert-delivery
  failures went unnoticed for 11 weeks partly from under-logging) is
  fully intact. Only the third-party `"httpx"` logger's threshold moved.

---

## PART 3 — Verification

Ran from a scratch script (`/tmp/.../scratchpad/verify_telegram_fix.py`,
session-local, not part of either repo), not the live services — per
scope, the observer was **not restarted**, so this proves the fix works
in the code, not that the currently-running observer process (still on
the old, unfixed module) is fixed yet.

**1. Real send under the exact leak-triggering condition, token
confirmed absent from the log:**

The script first calls `logging.basicConfig(level=INFO, stream=<buffer>,
force=True)` — reproducing precisely what
`calibration_analysis.py`/etc. do — *then* imports the now-fixed
`monitoring.telegram_health_bot` and sends a real message through
`TelegramHealthBot._send_message()`:

```
[SETUP] Root logger forced to INFO with a StreamHandler -- reproducing the condition that caused today's leak.
[SEND] bot._send_message() returned: True
[CHECK] token substring present in captured log output: False
[CHECK] 'api.telegram.org' present in captured log output: False
[CHECK] captured log buffer length: 0 chars, 0 lines
```

The captured-log check never printed the buffer unless both flags were
False, as a safety net — the raw buffer was empty, so nothing sensitive
was ever at risk of being echoed here regardless.

**2. Delivery confirmed:** `bot.send_message()` returned normally
(`_send_message` → `True`) — python-telegram-bot raises `TelegramError`
on any non-success response, so a clean `True` return means Telegram's
API accepted and sent it (Bot API's `sendMessage` is synchronous; a
network/auth/permission failure raises rather than returning). The
message itself: **"🧪 TEST MESSAGE — ignore. Verifying the token-in-log
fix... Sent by an automated verification script, not a real alert."**,
sent to the configured chat (Oscar's channel), clearly marked as a test
per instructions.

**3. Deliberate failure still logs a useful error:** same script,
second half, constructs a `Bot` with an intentionally invalid token
(`"123456:this-is-not-a-real-token"`) and calls `_send_message` again:

```
[TELEGRAM] Error sending message: Unauthorized
[FAIL-TEST] bot._send_message() returned: False (expect False)
[FAIL-TEST] error output non-empty and informative: True
```

Real, informative error, exactly as before the fix — confirms the fix
suppresses only the request-line noise, not genuine failures.

**4. Committed regression test:**
`tests/test_telegram_httpx_log_redaction.py` (new, 10 checks) — verifies
(a) importing `monitoring.telegram_health_bot`/`monitoring.telegram_bot`
caps the `"httpx"` logger to WARNING, (b) a sample httpx-style INFO
request line (fake token, never a real one) against the fixed logger
produces zero captured output, (c) WARNING/ERROR-level records through
the same `"httpx"` logger **do** still come through (regression guard
against over-suppression) and an unrelated project logger's INFO level is
untouched, (d) `check_canonical_definitions.py`/`audit_invariants.py`'s
deferred-import senders carry the same guard, verified statically (no
live send in the committed test — matches the existing
`test_telegram_alert_gating.py`'s stated convention of "no live Telegram
send, no subprocess"). Ran via `run_tests.py` (not bare pytest), full
suite: **26 files, 339,919 checks, 0 failures**, including the new file
(10/10).

**Not yet true:** the currently-running `polymarket-observer` process
(PID unchanged since 2026-09-09 18:25:58, per §1.3) is still running the
**old** `telegram_health_bot.py` in memory — Python doesn't hot-reload.
**The fix is inert until the service restarts.** Per scope, I did not
restart it. Also per the task's own warning: the observer's last two
restarts hung on SIGTERM and needed SIGKILL — a plain `systemctl restart`
is not necessarily a clean, fast operation on this service; worth Oscar's
attention if/when a restart is scheduled, independent of this fix.

---

## PART 4 — Historical exposure (report only, no action taken)

**How much journal history could contain it:** not established
precisely (§1.3). Bounded fact: at least the ~49 hours from the current
observer process's start (2026-09-09 18:25:58 UTC) to now. Unbounded
above that: journal retention has no explicit cap and currently holds
~2 months (back to 2026-07-18) across 3.0 GB; whether earlier observer
process instances hit the same condition was not checked, for the
box-load reasons in §1.3.

**Purge vs. rotate — options, not a recommendation beyond the practical
observation that they answer different questions:**

- **Purging journalctl history** (`journalctl --vacuum-time=` or similar)
  removes the *evidence* of past exposure but does nothing about the
  *exposure itself* if the token was ever read by anyone/anything with
  access to the box in the window it was present. It also destroys
  unrelated operational history (this box's ~2 months of journal covers
  far more than this one issue) for a benefit that's purely
  record-keeping, not security.
- **Rotating the token** is the only action that actually closes the
  exposure window regardless of how far back it goes or who may have
  seen it — it makes the "how far back" question moot for future risk
  (past captures of the old token become worthless), which is likely why
  the task frames it as the cleaner answer. It does not, by itself, prove
  or disprove whether anyone used the exposure.
- These aren't mutually exclusive, but rotation is the one with a real
  security effect; purging is closer to housekeeping.

**If rotation is chosen — what it would touch (identified this session,
not executed):**

- `/home/parison/.env_trading` — three separate variable names carry
  this same token value: `telegram_alerts_token`, `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_AGENTS_TOKEN` (confirmed via boolean comparison, §1.3).
  Rotating means updating all three to the new token (or, better, an
  opportunity to collapse three env vars pointing at one bot into one —
  out of scope here, just an observation).
  `TELEGRAM_ORCHESTRATOR_TOKEN`/`TELEGRAM_METRICS_TOKEN` are unaffected,
  different bots.
- Every sender that reads one of those three vars would need its process
  restarted to pick up the new value: `polymarket-observer.service`
  (`TELEGRAM_BOT_TOKEN`), `polymarket-monitoring.service`
  (`TELEGRAM_BOT_TOKEN`, though currently unused per §1.2),
  `audit_invariants.py`/`check_canonical_definitions.py`
  (`telegram_alerts_token`, self-loaded fresh each cron invocation — no
  restart needed, next daily_maintenance run just picks it up),
  `orchestrator.py`'s `"agents"` bot and anything else reading
  `TELEGRAM_AGENTS_TOKEN` (`trading-swarm.service`, restart needed).
- **What would break during the swap**: a window between updating
  `.env_trading` and restarting every long-running consumer where the
  *running* processes still hold the old token in memory (harmless — old
  token still valid until actually revoked at Telegram's BotFather) but
  any *new* process picks up the new one — no outage as long as the old
  token isn't revoked before every consumer restarts. If BotFather's
  "revoke and regenerate" is used (the only way to actually invalidate
  the leaked token, as opposed to just changing what's configured), then
  every long-running consumer still holding the old token in memory
  breaks immediately until restarted — so revocation should happen after
  all four consumers are confirmed restarted onto the new value, not
  before. Given the observer's documented SIGTERM-hang history, that
  restart alone is worth planning as its own step.

**Rotation is explicitly Oscar's call — not performed.**

---

## What was not determined

- Whether any observer process instance **before** 2026-09-09 18:25:58 UTC
  ever hit this condition and leaked — bounded search only, per the
  box-load risk noted in §1.3.
- Whether the token appears anywhere in first-repo's `backups/` (466 GB
  of `.db` snapshots — structurally implausible but not grepped),
  `data/` outside the tracked source tree (126 GB), or `reports/`
  (182 MB) — not grepped, for the same reason.
- Whether anyone/anything actually *read* the token from the journal
  during its exposure window — no way to determine this from the box
  itself; only Telegram's own bot-activity log (not checked here, not
  something this session has access to) could show unexpected API usage
  from a different source.
- Whether `scripts/get_telegram_chat_id.py`,
  `monitoring/telegram_elo_bot.py`, and
  `data/characterizations/sweep_common/sweep_terminal_signal.py` are
  truly permanently dead, or just currently unreferenced — identified as
  not-live-today and left unfixed by design (§1.2), not exhaustively
  proven unreachable.

---

## Scope constraints honored

- Token **not** rotated.
- journalctl history **not** purged.
- `.env_trading` **not** modified (read via boolean-comparison-only
  subshell checks that never printed the value, to determine whether the
  leaked token is current vs. rotated — no line of it was written to
  disk or echoed).
- No alert path disabled — every sender's error/success logging is
  unchanged; only the third-party `"httpx"` access-log line was capped.
- `polymarket-observer` **not** restarted — the fix is committed but
  inert in the running process until it is; flagging the service's
  history of hanging on SIGTERM as a separate concern for whoever
  schedules that restart.

---

*first-repo commit: (see git log after this doc is filed — files changed:
`monitoring/telegram_health_bot.py`, `monitoring/telegram_bot.py`,
`scripts/check_canonical_definitions.py`, `scripts/audit_invariants.py`,
`tests/test_telegram_httpx_log_redaction.py`)*
