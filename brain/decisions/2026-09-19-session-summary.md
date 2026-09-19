# Session Summary — 2026-09-19 (Server Setup 21)

Documentation only. No computation, no new analysis — everything below draws on
work committed today. Every commit hash and file path cited was checked against
`git cat-file -t` / direct existence on `trading-swarm` (`master`) this session.

**Two discrepancies flagged up front, per instruction not to reconcile silently:**

1. "Server Setup 21" was already used once before, for 2026-06-05's session
   summary — three and a half months earlier than today. The prior summary
   (2026-09-18, "Server Setup 20") flagged the identical pattern for its own
   number against 2026-06-04. The counter does not run strictly with session
   chronology across this corpus; that remains true today, not newly
   discovered.
2. Part C's source brief attributes the Telegram bug-only channel cut that
   missed `_check_consensus_positions` to **2026-09-09**. The actual document
   (`brain/decisions/2026-09-07-telegram-remediation.md`) is dated
   **2026-09-07**. Recorded as given below with this correction noted; the
   substance (an undocumented sender survived the cut) is unaffected by which
   date is right.

---

## HEADLINE — the monitor fixes held, a corpus reader closed a five-month-old blind spot, and the session's own verification of that reader was itself wrong four times, caught only by grep

---

## Part A — The system held

Three monitor fixes (2026-09-17: ingestion fetch-ceiling, notify-queue/cycle-wait,
oos-hash-methodology-and-cycle-compounding), live since 2026-09-18 16:22, held
over their first sustained window:

- Cycle gaps drifted from 904–907s to a 960–1150s band (mean 1011s) — real but
  small, nowhere near the pre-fix 67–85 minute failure.
- Cycle bodies stable 56–239s with **no growth trend** across the window. The
  compounding is gone, not merely quiet.
- Pages settled to 2/cycle, not pinned at 3.
- 3,999 `polymarket_api` trades overnight, ~248/hr against a ~1.3/hr pre-fix
  baseline.
- `notified=0` holding at zero.
- The 429/408 log hits were false positives from substring matching; the
  recurring `offset=20000` error is the expected cursor boundary.
- Observer RSS 209MB, second flat reading — the leak fix holding. (Checked
  live this session: the observer process is currently at 189MB RSS, hours
  after the cited reading — consistent with a flat, non-growing baseline, not
  an independent re-verification of the 209MB figure itself.)

**Open items, recorded not resolved:**

- `check_pending_geo` still reads 1 (a single row from 2026-08-10) despite
  restored ingestion — contradicting the prediction that it would rise.
- An undocumented live Telegram sender (`_check_consensus_positions`, 5
  "CONSENSUS SIGNAL" messages today) was missed by the bug-only channel cut
  (see discrepancy note above on the date). Confirmed this session: the
  sender exists in `monitoring/system_observer.py`.
- The observer's burst-flush recurred — expected, since the blocking
  `sqlite3` calls were never fixed.

---

## Part B — The automation research

Four corners of external research, then a scoping task. The conclusions that
now govern agent work here:

1. Prefer stateless invocation over persistent sessions — a persistent
   session's output depends on accumulated history, making failures
   untraceable.
2. Generate the check, not the verdict. An agent writing a checking function
   that a verifier validates once, which then runs deterministically, is
   reliable; an agent answering "is this compliant?" each time is not.
3. Some grunt work needs no model at all.
4. LLM-as-judge is not the primary gate in production — it is used
   selectively for high-volume offline evaluation.

**The finding that matters most: the repo reached conclusion 2 independently
four months earlier.** `brain/decisions/2026-05-13-ollama-tool-calling-debt.md`
(confirmed present) concluded a Python wrapper calling Ollama only for the
classification step is simpler and more reliable than a tool-calling loop.
`backfill_market_categories.py` is that pattern in production. Today's
literature review rediscovered a conclusion sitting unread in the corpus —
which is itself the argument for the corpus reader built later this session.

**Tier-2.5 scoping outcome** (`a1db987`, confirmed): five candidate
supervisory roles assessed; the corpus reader selected as the only one with
a concrete immediate consumer. The `spawn_agent.sh` session-limit bug named
as gating: a run that hits the limit exits clean, is marked "completed," and
produces silent zero output with no alert. **Unfixed.**

---

## Part C — The wrong-machine incident

A background fork at 13:03 executed on Bruce, a WSL dev clone — not the
production box. It reported the corpus and its basis documents as
nonexistent and refused to proceed.

**The diagnosis, recorded precisely, because the refusal was correct
reasoning from a genuinely empty repo — not softened:** Bruce has no systemd
units installed, no `daily_maintenance.log`, a 1.69GB database symlinked to a
Windows path last modified 2026-05-07, and a trading-swarm clone 628 commits
behind that had not been fetched in five months. `git status` reported "up
to date with origin" because it compares against a stale remote-tracking
ref, not against GitHub's actual current state.

All 11 cited trading-swarm commits resolved on `origin` once fetched.
Nothing was lost.

**The durable lesson:** nothing in the session-start routine established
which host was in view, and every check written to date returns
plausible-looking answers on the wrong machine. A hostname check is now the
first item of every task. Recorded exactly as instructed: the agent reached
for "this task looks designed to avoid pushback" before the cheaper and
correct hypothesis, "am I where I think I am."

---

## Part D — The corpus reader

Built and run: 4h52m41s detached, 263 of 267 documents indexed (98.5%), 2
explicit failures (`2026-06-29-overhang-ledger.md` timed out at the 1800s
ceiling; `2026-09-10-own-market-calibration.md` hit a malformed JSON escape),
2 never attempted because the script does not recurse into `archive/`. Peak
RSS 28MB against a 500MB ceiling.

**The GPU finding, which invalidates a scoping premise:** the box has 8 GiB
dedicated VRAM plus ~43 GiB GTT under the Radeon 780M's unified memory
architecture. Ollama offloaded 49/49 layers; the full 17.1 GiB model was
GPU-resident throughout, mean 65.3s/call. The scoping document's "4GB UMA,
therefore CPU-bound" is wrong, and every local-agent candidate in it was
assessed on that false premise.

---

## Part E — The false-fabrication correction

**Recorded as the session's most instructive error, not softened.**

The first verification (`f1c5ed2`) reported two index fields unreliable with
confirmed fabrications: `STR-004` in heatmap-pass5, two paths in
geo-backlog-and-category-reach, one in background-backfill-ingest-evaluation.
A structural theory was built on those four — that anchored extraction
succeeds while enumeration fabricates — and presented as the report's most
useful finding.

**Rechecking with grep rather than by reading found all four present
verbatim in their sources.** Both fields were already pure regex — no model
call ever touched them, so a single-document `.findall()` cannot invent a
substring absent from its input. Fabrication was structurally impossible for
either field, in the original script or any replacement.

The real defect was under-matching: the old identifier regex had no pattern
for `RQ-WORD-NNN`, this corpus's dominant convention, and the old path regex
required backticks.

**The lesson is the inverse of the one drawn.** The failure was the
verification producing false positives. A careful manual read concluded four
times that a string was absent; grep disagreed four times. Where a check can
be mechanical, reading is the weaker instrument — including when the reader
is being careful.

The deterministic fix (`4b61fce`, confirmed) recovered 167 identifiers and
1,115 paths across 263 records, with zero fabrications in either direction,
zero identifier regressions, and 4 genuine path losses out of 501 diffs.
Both fields upgraded to trustworthy. The two `archive/` documents were
indexed deterministically, flagged `llm_fields_pending`.

---

## Part F — The mining

`afd9b63` (confirmed):

- **Query 1:** pass 2's claim that 25 of 35 research questions were never
  run holds under mechanical test — none of the 25 appears in any document
  typed `result` or `pre-registration`. One nuance: `RQ-EXT-001` was
  assessed once (`2026-06-11-session-summary.md`, "INCONCLUSIVE (too
  early)") with a re-run scheduled for August 1 that never happened — a
  different shape from never-measured.
- **Query 2:** 14 supersession chains built from 33 declared edges. At least
  4 of 33 (~12%, stated as a floor) have the wrong direction or wrong
  relationship type, including a genuine cycle where two documents each
  claim to supersede the other, and one misattributed from a sentence about
  two unrelated documents. This is the source extraction being wrong about
  direction, not the underlying source documents contradicting each other.
- **Query 3:** citing-neither fell from 26 documents to 5 once corrected
  paths were applied — the earlier figure was an artifact of the
  under-matching regex, not a change in the corpus.
- **Query 4:** 391 candidates from a bigram heuristic, 90% false-match rate
  reported plainly rather than presented as findings. One genuine open
  discrepancy survives — a same-day 361-market disagreement on the
  clob-resolved-Unknown count (214,155 vs 214,516). The result of record
  showed no contradiction across 19 occurrences.

---

## Open threads carried forward

- The auto-push hook fired on two consecutive tasks that said do not push,
  flagged after the fact both times. It needs inverting to opt-in, or every
  such instruction is decorative.
- `spawn_agent.sh`'s session-limit bug — gating for any Claude-backed agent.
- `check_pending_geo` stuck at 1.
- The undocumented `_check_consensus_positions` Telegram sender.
- The blocking `sqlite3` calls in the observer.
- The 2 failed corpus documents (retry cost ~2 minutes; a tighter 300–600s
  timeout recommended given the GPU finding, not applied).
- The 2 `archive/` documents have deterministic fields only, LLM fields
  pending — a separate decision.
- The scoping document's CPU-bound premise needs revisiting for every
  local-agent candidate.
- The 09-12-to-now trade gap, unbackfilled.
- The relevance-classifier §3.10 adjudication, outstanding since 2026-09-03
  — now sixteen days.
- Telegram token rotation, undecided.

---

## What this document does NOT do

No verdict on what to do next, on any open item above. Parts C and E are
stated exactly as their source documents state them, not softened: a correct
refusal on the wrong machine, and a verification that fabricated its own
fabrication findings.
