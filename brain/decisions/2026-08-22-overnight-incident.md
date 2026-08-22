# 2026-08-22 — Overnight Performance Incident: Diagnosis (Read-Only)

## VERDICT: NO DAMAGE, CAUSE IDENTIFIED

`PRAGMA integrity_check` returns clean (`ok`). No count anomalies, no
constraint/trigger damage, no evidence of any write occurring during the
incident window. Root cause: a **Mullvad VPN / Tailscale network-layer
outage** on the host itself (`trading-swarm`), beginning **03:24:13 UTC**
and lasting until an unexplained reboot at **09:29:56 UTC** — roughly 6
hours, longer than the operator's 1–2h estimate (which likely reflects
only when SSH specifically was tested, not the full degradation window).
This is unrelated to yesterday's discovery-gap-closure work. The widened
`backfill_market_dates.py --limit 35000` step (commit `5fcbffe`) **never
ran** last night — `daily_maintenance.py` stalled 24 steps earlier, in the
routine "Resolution sweep" step, entirely because of the network outage.

One item remains genuinely unresolved (not damage, not blocking): what
triggered the 09:29:56 reboot. See §6.

All claims below are tagged **[V]** verified (I ran the command/read the
file myself this session) or **[I]** inferred (reasonable conclusion from
verified evidence, not directly observed).

---

## 1. Was there a reboot or crash

**[V]** The box did **not** crash or go down during the actual incident
window. Boot ID `39ffa0a8` (`journalctl --list-boots` idx -1) started Fri
2026-08-21 03:00:59 UTC and its journal continues, **without any gap
greater than 60 seconds**, all the way through the incident window and
past it, to 2026-08-22 09:28:50 UTC. (Verified by binning `journalctl -o
short-unix` timestamps and checking consecutive-line deltas across
2026-08-21 22:00 → 2026-08-22 09:30 — zero gaps >60s found.) The box was
up and logging the entire time; it became unreachable/slow while staying
up, not because it went down.

**[V]** A reboot *did* happen, but **this morning**, at 2026-08-22
09:29:56 UTC (boot `80bf1b8c`) — immediately after the incident window
ends, not overnight. `uptime` confirms current boot age ≈2h17m at session
start (11:47 UTC), consistent.

**[I]** This 09:29:56 reboot is not explained by the routine mechanism
that produces most of this host's other reboots. `last reboot` shows
several prior reboots that line up with `unattended-upgrades` installing
kernel packages and self-scheduling a reboot (e.g. 2026-08-20 06:28:58
log: "Packages that will be upgraded: ... linux-image-generic ...",
"Found /var/run/reboot-required, rebooting", "Reboot scheduled for Fri
2026-08-21 03:00:00 UTC" — which is exactly the boot that then ran through
the incident window). By contrast, `unattended-upgrades.log`'s only run
touching today's incident window (2026-08-22 06:09:41) installed **only**
`libpq5 vim vim-common vim-runtime vim-tiny wget xxd` — no kernel/libc
packages — and logged no `reboot-required` flag. So the standard
auto-update-reboot path does not account for the 09:29:56 reboot.

**[I]** The boot-1 journal tail (last ~200 lines before the gap) shows no
graceful-shutdown sequence (no systemd-logind "reboot requested",
no "Reached target Shutdown", no service-stop cascade) — it simply stops
mid-stream in the middle of ordinary Mullvad/Tailscale reconnect churn.
That pattern is more consistent with an abrupt reset (hard power-cycle,
hardware watchdog, or kernel-level hang requiring a hard reset) than a
commanded `reboot`/`shutdown -r`. This session has no `sudo` password
available (`sudo systemctl status` failed with "a password is required"),
so `/var/log/auth.log` could not be checked to identify who/what issued
it. **Unresolved** — flagged in §6, not blocking the verdict since it
postdates the incident and integrity is independently confirmed clean.

---

## 2. What was running during the window

### 2a. Did daily_maintenance.py run, and did it reach the widened step?

**[V]** Yes, it started on schedule: `logs/daily_maintenance.log` shows
`[2026-08-22T06:00:01Z] Starting daily-maintenance` (cron: `0 6 * * *
/home/parison/trading-swarm/scripts/cron_wrappers/run_daily_maintenance.sh`,
confirmed present in `crontab -l`, confirmed fired via
`journalctl -b -1 | grep CRON` → `Aug 22 06:00:01 ... CRON[22690]:
(parison) CMD (.../run_daily_maintenance.sh)`).

**[V]** It completed "Update research exclusions" (Step 0) and several
subsequent early steps normally (research-exclusion propagation, trade
category sync, ARB_BOT detection) within the first ~15 seconds. It then
entered **Step 5 of the `STEPS` list, "Resolution sweep"**
(`resolution_sweep.py`, non-blocking — confirmed by reading
`scripts/daily_maintenance.py:32-81`), which prints its own header
"Resolution Sweep — Channel 2 Discovery" and iterates individual traders
fetching trades from `data-api.polymarket.com`. **Every single fetch in
this step failed** with
`NameResolutionError: Failed to resolve 'data-api.polymarket.com'
([Errno -3] Temporary failure in name resolution)` — a direct symptom of
the concurrent network outage (§3/§5).

**[V]** It got through only **590 of 3737** traders (`[590/3737]
processed (running: fetched=0 matched=0)` is the last progress line in
the file) before the log file simply stops — no completion banner, no
timeout/kill message, no traceback. `logs/daily_maintenance.log`'s last
modification time is 09:22 (checked via `stat`/`ls -la`), ~7 minutes
before the 09:29:56 reboot. **[I]** The absence of any timeout message
(the step's default 3h/10800s subprocess budget — `DEFAULT_STEP_TIMEOUT`
in `daily_maintenance.py:24` — would have expired around 09:00 and, per
the code, should print a WARNING on expiry) combined with the log simply
ceasing mid-line is consistent with the underlying process being killed
by the abrupt reboot at 09:29:56 rather than hitting its own timeout
handler.

**[V] The widened `--limit 35000` "Backfill market dates" step never
ran.** Reading `daily_maintenance.py:306-320` confirms this step sits
near the **very end** of the run — after ~25 other steps, immediately
before "Hydrate stub markets" and the final `MAINTENANCE COMPLETE`
banner (confirmed by yesterday's 2026-08-21 log entry showing this exact
sequence: `--- Step: WAL checkpoint ---` → `--- Step: Backfill market
dates --- ... OK (134.9s)` → `--- Step: Hydrate stub markets ---` →
`=== MAINTENANCE COMPLETE ===`). Since last night's run stalled at step 5
of ~29 and was killed before finishing, it structurally could not have
reached this step. For reference, yesterday's (2026-08-21) run of this
same step — the last time it actually executed — took **134.9 seconds**,
nowhere near the "~2h26m" figure cited in the prompt; that number is not
something this investigation reproduced or needed to explain the
incident, since the step didn't run at all last night.

### 2b. Manual invocation outside daily_maintenance.py?

**[V]** No. `journalctl -b -1` for the full window (2026-08-21 22:00
through the reboot) was grepped for `backfill_market_dates\.py` and
`fast_resolution_check\.py`; the only matches are the two daily cron
firings of `run_daily_maintenance.sh` itself (06:00:01 both days). No
standalone/manual invocation found.

### 2c. Was the sweep/tranche started?

**[V]** Confirmed not started, not assumed. `data/checkpoints/` does not
exist anywhere under `/home/parison/projects/first-repo` (`ls` returns
"No such file or directory"). No process matching `sweep|tranche` is
currently running (`ps aux` grep, empty). The only "sweep" activity found
is `resolution_sweep.py` running as its normal, non-blocking, every-day
Step 5 of `daily_maintenance.py` (see 2a) — this is routine scheduled
behavior, not a manually-started sweep/tranche, and it made zero writes
(see §4c).

---

## 3. Resource exhaustion signature

**[V]** Ruled out — this was not a memory or CPU/disk exhaustion event.
Pulled `sar -r`, `sar -S`, `sar -u`, `sar -b` from
`/var/log/sysstat/sa21` and `sa22` for the full window (2026-08-21 22:00
→ 2026-08-22 09:30, the last data point before "LINUX RESTART" in the
sar log):

- **3a. Memory/swap:** `%memused` stayed between 0.71–1.29% of ~90GB the
  entire window; `kbswpused` was **0 the entire window** (0.00% swap
  used, every single 10-minute sample). No OOM killer activity anywhere
  in the boot-1 journal (`grep -iE "out of memory|oom.?kill|killed
  process|invoked oom|memory cgroup"` → zero matches).
- **3b. Disk I/O:** `sar -b` shows 30–90 tps throughout, no saturation,
  no sustained heavy-write signature.
- **3c. OOM killer:** Did not fire. Nothing was killed by it.

**[I]** The ping-latency sawtooth and "no route to host" pattern described
in the prompt is therefore **not** a resource-exhaustion signature on
this box — it is consistent with a network-interface-level problem
(VPN/tunnel flapping causing intermittent loss of default route), which
is exactly what §5 finds independently in the Mullvad/Tailscale logs.

---

## 4. Database integrity (priority)

**[V] 4a.** `PRAGMA integrity_check;` → **`ok`** (single-row clean
result, full output — no truncation).

**[V] 4b.** `polymarket_tracker.db-wal` is currently **0 bytes**;
`-shm` is 32KB (normal steady-state size). No orphaned or oversized WAL
file — no evidence of an interrupted checkpoint. `PRAGMA journal_mode;`
confirms `wal` (unchanged, as required).

**[V] 4c. Current fingerprint** (re-derived this session):

| Metric | Value |
|---|---|
| traders | 171,540 |
| trades | 11,663,141 |
| positions | 7,689,429 |
| markets | 745,066 |
| markets resolved (`resolved=1`) | 224,981 |
| trade_gap_flag = 0 | 744,816 |
| trade_gap_flag = 1 | 250 |
| Geo/Elec resolved + gap-clean | 3,708 |
| resolution_evidence_source: NULL | 745,053 |
| resolution_evidence_source: gamma | 12 |
| resolution_evidence_source: hydration_fill | 1 |
| resolution_evidence_source: clob | 0 |

**[I] Caveat, stated plainly rather than papered over:** I searched
`brain/decisions/2026-08-21-*.md` and
`first-repo/data/characterizations/step{2,3}_verification/` for a
committed, same-methodology fingerprint from yesterday's session-end to
diff against, and **found none** — none of yesterday's step2/step3
implementation or stop docs recorded a full-table count baseline. I am
**not** claiming a verified "no count decrease" from a literal diff,
because no baseline artifact exists to diff against. What I can say with
verification: none of the current counts are internally inconsistent,
negative, or otherwise structurally implausible.

Independent of a count diff, two pieces of direct evidence argue against
any write having occurred during the incident:
1. **[V]** The only DB-touching process active in the window (the
   "Resolution sweep" step, §2a) logged `fetched=0 matched=0`
   continuously for its entire runtime — it never successfully fetched
   data from the API, so it had nothing to write.
2. **[V]** The actual production writer — the 15-minute
   `polymarket-monitoring` service (`pnl_worker`) — ran continuously and
   healthily through the whole window: 1,975 log lines between 03:00–
   09:30, its own internal counter stayed at `errors: 0` throughout,
   `processed` climbed steadily from 53,200 to 62,100+, and it never
   restarted or crashed (`journalctl -u polymarket-monitoring` shows no
   start/stop/exit events in the window — only 5 isolated, gracefully-
   handled DNS-failure log lines matching the same network outage).

Combined with the clean `integrity_check` and empty WAL, this is strong
evidence against data loss even though a literal yesterday-vs-today count
diff isn't available.

**[V] 4d.** The `resolution_evidence_source` CHECK constraint is present
and unmodified:
```sql
resolution_evidence_source TEXT CHECK (resolution_evidence_source IN
  ('clob','gamma','manual_verified','hydration_fill')
  OR resolution_evidence_source IS NULL)
```
Atomicity check — rows where `resolution_recorded_at` is set but
`resolution_evidence_source` is null, or vice versa —
returns **0 rows**.

**[V] 4e.** `trg_resolved_no_unresolve` trigger exists and its body is
unchanged (`BEFORE UPDATE OF resolved ... WHEN OLD.resolved = 1 AND
NEW.resolved = 0 ... RAISE(ABORT, ...)`).

---

## 5. Was this the widened limit's fault

**[V] No.** `daily_maintenance.py` did run overnight (on schedule,
06:00:01) but stalled in "Resolution sweep" (step 5 of ~29) and never
reached "Backfill market dates" (the widened step) at all — see §2a. The
widened `--limit 35000` change from commit `5fcbffe` was never exercised
last night, so it cannot be implicated in this incident.

**[V] The actual driver was an external network-layer outage on the
host**, confirmed via journal analysis:

- Log volume for `mullvad-daemon` + `tailscaled` combined jumped from a
  baseline of ~500–1,100 lines/hour (2026-08-21 22:00–2026-08-22 02:00)
  to **25,542 lines in the 03:00 hour, then 40,000+/hour sustained**
  through 09:00, dropping only when the box rebooted at 09:29:56.
  `mullvad-daemon` alone contributed 120,091 lines and `tailscaled`
  111,134 lines in the 03:00–09:30 window — 92% of all journal volume for
  the period — versus 2,247 lines from `polymarket-monitoring` (normal)
  and effectively none from any DB-related script until
  `daily_maintenance` itself started at 06:00 (§2a).
- Onset pinpointed to **03:24:13 UTC**: first `mullvad-daemon` ERROR is
  `"Failed to automatically adjust MTU based on dropped packets"`,
  immediately followed by cascading `mullvad_api::rest: HTTP request
  failed` / `Connection refused` / `No route to host (os error 113)`
  entries and `tailscaled` DERP-relay connect failures
  (`dial tcp: connect: network is unreachable`). Per-10-minute volume for
  `mullvad-daemon` alone: 1 line (03:00), 1 line (03:10), then 1,961
  (03:20), 3,657 (03:30), 3,512 (03:40), 3,273 (03:50) — a sharp,
  sustained step-change, not a gradual ramp.
- This is a VPN/tunnel-level reconnect storm (WireGuard tunnel timing
  out, DERP relays unreachable, repeated relay-selection/access-method
  fallback attempts by Mullvad, repeated Tailscale netmon/rebind churn),
  not anything triggered by or downstream of the polymarket codebase. It
  fully explains both reported symptoms independently of any DB
  operation: the sawtooth ping latency (path instability while the
  tunnel repeatedly drops and reconnects) and the "no route to host" SSH
  failures (the default route disappearing during
  `wg0-mullvad: Link DOWN` / route-deletion events, e.g. `Aug 22 09:28:40
  systemd-networkd[1197]: wg0-mullvad: Link DOWN`).
- Kernel-level (`journalctl -k`) messages at the 03:00 onset show nothing
  but routine UFW-blocked IGMP multicast from the LAN router — no
  wifi-driver crash or firmware fault at the point the storm began.

**Conclusion:** this incident's proximate cause was Mullvad/Tailscale
network instability external to the trading-swarm codebase; the
`daily_maintenance.py` "Resolution sweep" step was a **downstream victim**
of it (repeated DNS failures, stalling for hours without making progress
or writing anything), not a cause. The widened backfill limit is cleared.

---

## 6. Anything else (one line each, not further investigated)

- **[I] Unresolved:** trigger for the 09:29:56 reboot could not be
  determined from available (non-root) logs — see §1. Worth a follow-up
  with root access to `/var/log/auth.log` / `wtmp` reason codes if this
  recurs.
- **[V]** `resolution_sweep.py` has no visible retry/backoff configuration
  (`grep`'d for `Retry|backoff|max_retries|Session()|HTTPAdapter` — zero
  matches); its ~590-users-in-~3h processing rate during the outage
  (vs. presumably much faster under normal DNS) suggests it may be
  hanging on TCP-connect timeouts during the intervals when DNS
  intermittently succeeded but routing was still broken, rather than
  failing fast — worth hardening with an explicit short request timeout
  so a future network blip doesn't stall this step for hours.
- **[V]** CLAUDE.md's documented DB size ("~1.6 GB as of April 2026") and
  row counts (87,063+/1M+/220K+/1,064K+) are stale by a wide margin —
  actual current size is ~17.3GB (`ls -la`), and `backup.log` shows it
  was already 16G on 2026-08-12, ten days before this incident — this is
  organic growth over ~4 months, unrelated to last night, but the doc is
  due for a refresh.
- **[V]** Working tree had pre-existing uncommitted changes at session
  start (`data/.last_requeue_run`, `data/category_backfill_state.json`,
  `logs/arb_bot_exclusions.log`, `logs/focus_ratio_review.json`) plus new
  untracked characterization files dated 2026-08-20/21 — these are
  routine artifacts of `daily_maintenance.py` Step 0 and prior
  characterization runs, not touched by this investigation, unrelated to
  the incident.
- **[V]** `unattended-upgrades` did run and install packages at 06:09:41
  this morning (`libpq5 vim vim-common vim-runtime vim-tiny wget xxd`)
  — mid-incident, but non-kernel and logged as successful; not implicated
  in the network outage or the later reboot.

---

## Evidence commands (for reproduction)

```bash
journalctl --list-boots
journalctl -b -1 --since "2026-08-21 22:00:00" --until "2026-08-22 09:30:00" -o short-unix   # gap analysis
journalctl -b -1 --since "2026-08-22 03:00:00" --until "2026-08-22 09:30:00" -o short-iso | awk -F'trading-swarm ' '{print $2}' | awk '{print $1}' | sed 's/\[.*//' | sort | uniq -c | sort -rn
sar -r -f /var/log/sysstat/sa22 -s 03:00:00 -e 09:30:00
sar -S -f /var/log/sysstat/sa22 -s 03:00:00 -e 09:30:00
sar -u -f /var/log/sysstat/sa22 -s 03:00:00 -e 09:30:00
sar -b -f /var/log/sysstat/sa22 -s 03:00:00 -e 09:30:00
sqlite3 data/polymarket_tracker.db "PRAGMA integrity_check;"
sqlite3 data/polymarket_tracker.db "SELECT COUNT(*) FROM markets WHERE (resolution_recorded_at IS NOT NULL AND resolution_evidence_source IS NULL) OR (resolution_recorded_at IS NULL AND resolution_evidence_source IS NOT NULL);"
```
