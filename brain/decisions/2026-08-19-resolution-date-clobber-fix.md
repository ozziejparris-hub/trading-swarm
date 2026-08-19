# 2026-08-19 — close the demonstrated live overwrite in `batch_update_resolved_markets`

**This is a plug, not a resolution.** It closes the one demonstrated-live
clobber path named in `2026-08-19-market-resolution-write-cluster.md`
(`85965c5`). It does **not** address the broader finding from that same
doc: the O-36 write-time-vs-event-time `resolution_date` bug shape is
present in **at least 8 of the 13 write sites** in this cluster. This fix
touches exactly one of those 8. The other 7, and the cluster's lack of a
canonical write path, remain exactly as characterized — nothing about
this change should be read as the cluster being fixed.

Every claim tagged **[V]** (verified — command/output given) or **[I]**
(inferred). Standing instruction applies.

---

## Pre-change checks

**1. Pattern match, confirmed [V].** All three guarded sibling sites in
`scripts/fast_resolution_check.py` use the identical text
`resolution_date = COALESCE(resolution_date, ?)`:

```
$ grep -n "resolution_date = COALESCE" scripts/fast_resolution_check.py
388:    resolution_date = COALESCE(resolution_date, ?),
498:    resolution_date = COALESCE(resolution_date, ?),
595:    resolution_date = COALESCE(resolution_date, ?),
```

The fourth site (line 267, inside `batch_update_resolved_markets`) read
`resolution_date = ?` — unconditional. The fix applies the exact same
`COALESCE(resolution_date, ?)` text, no variant.

**2. Authority check, confirmed [V] — did not stop.** Per the cluster
doc (`2026-08-19-market-resolution-write-cluster.md`, the overwrite-matrix
row for this pair): the value being lost is `monitor.py`'s proxy
`resolution_date`, derived from a real Gamma `/events` or CLOB end-date
lookup — genuine API evidence, even though it's explicitly a forward-looking
estimate rather than a confirmed resolution fact. The value that
overwrites it is `datetime.now()` — the moment the script happened to
run, carrying **no evidence at all** about the market. Guarding preserves
the value with *some* evidentiary basis over the value with none. The
cluster doc's own language: *"arguably a downgrade in evidence quality
even though neither writer claims to represent the true resolution
timestamp."* This does not say otherwise — proceeded.

**3. Before figure, measured [V]:**

```sql
SELECT COUNT(*) FROM markets
WHERE (resolved = 0 OR resolved IS NULL) AND resolution_date IS NOT NULL;
-- 1349
```

**1,349 markets** currently hold a non-null `resolution_date` while
`resolved=0` — the full population at risk of clobber by this specific
write path, should any of them be matched against Gamma's resolved-markets
feed on a future run.

---

## The change

`scripts/fast_resolution_check.py:267`, one line:

```diff
                         cursor.execute("""
                             UPDATE markets
                             SET resolved = 1,
                                 winning_outcome = ?,
-                                resolution_date = ?,
+                                resolution_date = COALESCE(resolution_date, ?),
                                 last_checked = ?
                             WHERE market_id = ?
                         """, (winner, datetime.now(), datetime.now(), market_id))
```

`git diff --stat`: 1 file changed, 1 insertion(+), 1 deletion(-). Nothing
else in the file touched.

---

## Verification 1 — before/after clobber proof (would fail against pre-fix code)

**[V]** Built an isolated, no-network, in-memory-SQLite test: seeded one
market row with a pre-existing `resolution_date` (`2026-08-01 12:00:00`,
standing in for a monitor.py proxy value) and `resolved=0`, then ran the
**exact SQL text** from the pre-fix git blob (`git show HEAD:scripts/fast_resolution_check.py`,
confirmed byte-identical to the reconstructed pre-fix statement before
running) and the exact post-fix SQL from the working tree, against
independent copies of that seeded row.

```
PRE-FIX  (git blob, unconditional): proxy_date='2026-08-01 12:00:00' write_time='2026-08-19 19:52:05.270251' result='2026-08-19 19:52:05.270251' preserved=False
POST-FIX (working tree, COALESCE-guarded): proxy_date='2026-08-01 12:00:00' write_time='2026-08-19 19:52:05.271244' result='2026-08-01 12:00:00' preserved=True

PASS: pre-fix clobbers (preserved=False), post-fix preserves (preserved=True).
```

**Why this isn't tautological:** the pre-fix statement was extracted from
`git show HEAD`, not hand-retyped from memory — it is the actual code
that shipped until this session. Running it against the seeded row
genuinely destroys the proxy value (result becomes the write-time
timestamp); the same test harness run against the post-fix statement
genuinely preserves it. A test that couldn't distinguish the two would
either not touch `resolution_date` at all or would seed a `NULL` value
(where `COALESCE` and unconditional-assignment are indistinguishable) —
this test deliberately seeds a **non-null** value, which is the only
input that separates the two behaviors.

---

## Verification 2 — dry-run against production data, real rows

**[V]** Bounded, read-only (no `--test`/write path exercised at all —
every query used a `mode=ro` connection or the class's own read methods).
Rather than an unbounded full API sweep, targeted the **known at-risk
population directly**: sampled 20 markets from the live
`(resolved=0/NULL) AND resolution_date IS NOT NULL` set with
`resolution_date` in the near-past (2026-06 through 2026-08-18 — the
segment most likely to have genuinely resolved by now), queried each
individually against the real Gamma API, and ran the actual
`FastResolutionChecker.extract_winner()` method (unmodified by this fix)
against each response.

**12 of the 20** returned a non-`None` winner — i.e., **12 real,
currently-`resolved=0` production markets** are candidates for
`batch_update_resolved_markets`'s next run, each already carrying a
non-null `resolution_date`:

| market_id (truncated) | api_id | current resolution_date | pre-fix would write | post-fix would write |
|---|---|---|---|---|
| `0xbd0c2d5f58650e031a` | 906980 | `2026-06-02T00:00:00+00:00` | today's write-time (clobber) | unchanged (preserved) |
| `0x438d579956a8a9142d` | 825093 | `2026-06-16 00:00:00` | clobber | preserved |
| `0xf18497fa69a4ca7a92` | 825095 | `2026-06-16 00:00:00` | clobber | preserved |
| `0xe5ffa71675ff53e730` | 825098 | `2026-06-16 00:00:00` | clobber | preserved |
| `0x08b39100a4d3d6ad10` | 608362 | `2026-06-30 00:00:00` | clobber | preserved |
| `0x08e4cea3c55ded3bb7` | 826115 | `2026-08-11 00:00:00` | clobber | preserved |
| `0xf67b35a73ee7b84b14` | 826143 | `2026-08-11 00:00:00` | clobber | preserved |
| `0x198cd5dc8827b5e577` | 826144 | `2026-08-11 00:00:00` | clobber | preserved |
| `0x3af7fbb58a66ab5d54` | 799358 | `2026-08-11T00:00:00+00:00` | clobber | preserved |
| `0x9743ef770e5caafc6a` | 700645 | `2026-08-18 00:00:00` | clobber | preserved |
| `0x0a9c99dad5dfcd8c54` | 700646 | `2026-08-18 00:00:00` | clobber | preserved |
| `0x6415588e3e9bef8cae` | 704476 | `2026-08-18 00:00:00` | clobber | preserved |

**Rows affected: 12 of 20 sampled (60%).** This is not a rare edge case —
it is actively present in production data right now, unresolved only
because these specific markets haven't yet been reached by a full,
unbounded run of `batch_update_resolved_markets` (which pages through
Gamma's `closed=true` feed and would eventually reach them). The other 8
of the 20 sampled either returned `closed=False` with no price-threshold
winner yet, or (in an earlier, wider sample from the oldest end of the
at-risk population, 2020–2022-dated entries) were long-voided/ambiguous
markets (`outcomePrices` like `["0","0"]` or `["0.5","0.5"]`) that
`extract_winner` correctly returns `None` for — not candidates for this
write path at all, pre- or post-fix.

---

## Verification 3 — `run_tests.py` (canonical runner)

**[V]** `python3 run_tests.py --verbose`, full run (~140s):

```
Files  : 15 run, 14 passed, 1 failed
Tests  : 339,700 run, 339,695 passed, 5 failed
  FAIL  test_backtest_window_population.py  (24 tests, 19 passed)
RESULT: FAILURES DETECTED
```

**Identical to the stated baseline** (14/15 files, 19/24 in the one known
failing file). **No new failure.** Specifically checked
`tests/test_resolution_date_cowrite.py` — the O-17 test file covering the
7 *other* write paths this cluster's `resolution_date` bug touched —
still passes 11/11. That file's own docstring names
`batch_update_resolved_markets` as one of the *"working writers"* whose
`datetime.now()` value it treated as already-correct source-of-truth at
O-17's fix time (2026-07-01) — it never asserted anything about
`batch_update_resolved_markets` being unconditional, so this fix does not
contradict any existing assertion in that file. **[I]** That docstring
line is now mildly stale (it no longer accurately describes this site as
simply "working"), but editing it is outside this task's one-line scope
and was not done.

---

## Scope statement, stated explicitly per the task's instruction

**This closes exactly one clobber path**, in exactly one of the 13 write
sites characterized in `2026-08-19-market-resolution-write-cluster.md`.
It does **not**:
- Address the other 7 sites still using `datetime.now()` write-time
  semantics instead of true event-time `resolution_date` (`fast_resolution_check.py`'s
  3 sibling passes now guarded-but-still-write-time,
  `resolve_legendary_markets.py`, `legendary_positions_scan.py`,
  `fetch_market_resolutions.py`, `fix_expired_unresolved.py`).
- Touch the two writers with a genuinely unconditional `resolved`/`winning_outcome`
  path (`monitoring/database.py`'s `update_market` ON CONFLICT branch,
  `update_market_resolution`) — both still latent, per the prior doc's own
  finding that neither is reachable via a confirmed live call site today.
- Implement `mark_market_resolved()` or any canonical write path — that
  decision remains unmade, as instructed.
- Fix the 123 `resolved=1/winning_outcome=NULL` rows or the 8
  `resolved=1/resolution_date=NULL` residual — both already fully
  attributed to other, unrelated mechanisms in the prior doc, unaffected
  by this change.

**The cluster is not fixed.** One demonstrated-live clobber path, out of
several characterized risks, is closed.

---

*Generated 2026-08-19. Sources: `scripts/fast_resolution_check.py`
(before/after diff, `git show HEAD` for the pre-fix blob),
`2026-08-19-market-resolution-write-cluster.md` (`85965c5`),
`tests/test_resolution_date_cowrite.py`, live DB queries against
`data/polymarket_tracker.db`, live Gamma API queries (bounded, read-only,
20 markets sampled from the known at-risk population), and a full
`run_tests.py --verbose` run. No production write performed by any
verification step; `fast_resolution_check.py` was not run in write mode
against production.*
