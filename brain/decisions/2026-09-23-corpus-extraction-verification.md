# Corpus content extraction — full-output verification (2026-09-23)

**Host:** `trading-swarm` (confirmed first; 290 files in `brain/decisions/` at start).
**Verdict: the index (`brain/corpus_content_index.jsonl`) should NOT be used as shipped.** It is mechanically
clean (schema 277/277, no stored-vs-recomputed disagreement, dedup and raw preservation intact) but
**claim text is not reliably supported by its own quote**, one known fabrication reproduced on the
largest document, and four of the seven fields are unreliable. The index was therefore **not committed**
(left untracked); this document, the verification script and its artifact are committed instead.
No synthesis, ranking or conclusions were drawn from corpus content.

Marking convention: **[V]** = recomputed by the committed script
(`scripts/verify_corpus_content_index.py` → `brain/corpus_content_verification_20260923.json`);
**[R]** = my hand-reading, single reader, not blinded — a judgement, not a measurement.

---

## 1. Did it finish? — yes, cleanly [V]

| | |
|---|---|
| PID 113783 | gone; finished `2026-09-22T22:40:17Z`, wall **21,352 s (5.93 h)**, started 16:44:24Z |
| End condition | clean `=== finished ===` line; no kill condition (ceiling now 24 h) |
| Documents | 2nd invocation: **115 extracted + 5 failed** of 120 attempted. Index now **277 records**; discovered corpus 282; **5 documents have no record** |
| Across both invocations | 162 + 115 = **277 successes**; 168 + 120 = 288 call attempts; 11 failure rows (6 + 5) |
| Retries | of the 6 prior timeouts, **1 succeeded** (`2026-07-10-trading-swarm-deep-audit-FABLE.md`), **5 failed again at exactly the same length-scaled ceiling**: overhang-ledger (1503 s), pool-c-decline (300 s), 06-29-session-summary (300 s), structural-survey (352 s), backtest-snapshot-drift (440 s) |
| Pre-launch assertion | ran and passed twice: dry-run 16:41 (119 docs, 29,888 s / 8.30 h projected) and launch 16:44 (120 docs, 30,016 s / 8.34 h); launch ceiling 69,120 s of 86,400 s. Actual 21,352 s = 71% of projection |
| Per-call time (ok) | min 14.7 s, median 109.5 s, mean 132.3 s, p90 223.4 s, max 1,258.8 s (`discovery-gap-closure-prereg.md`, timeout 2,741 s). No successful call above 0.80× its ceiling; none flagged `over_safety_margin` |
| By invocation | first: median 94.8 s / mean 113.0 s; second: median 139.6 s / mean 159.4 s (second half's documents are longer: mean 356 vs 192 lines) |
| RSS (extractor own) | peak 34.8 MB (1st), 29.9 MB (2nd) |

**Per-document ceiling question (not a formula question):** the 5 repeat failures include a 7.9 KB
document (pool-c-decline, 92 lines) and a 15 KB one, which the median call would finish in ~110 s. Timing out
at 300 s twice on identical input looks like non-terminating generation on that input, not a length shortfall.
**[inferred — `eval_count` is null on failures, so this is untested]**. Raising the ceiling is unlikely to help.

## 2. Flock probe — UNTESTED in production

The run ended 22:40Z, ~7.3 h **before** the 06:00 maintenance; the first invocation (09-21 16:16–22:18Z)
also never crossed 06:00. The extractor log contains **no** "waiting"/maintenance lines. The probe was
*called* between documents (and returned False each time — it did not error), but it has **never met a held
lock**. It is verified only by its offline tests (31/31 per the 09-22 doc). Not implied to work.
Maintenance was not refused today: 06:00:01Z Starting → 10:43:43Z Finished (exit 0), 4 h 43 m.

## 3. Two-halves check — NOT indistinguishable, but confounded with document date [V]

Split rule: `indexed_at < 2026-09-22` → first (162 docs), else second (115).

| | first | second |
|---|---:|---:|
| schema pass | 162/162 | 115/115 |
| quotes | 4,046 | 3,048 |
| exact | 56.33% | 21.23% |
| normalized | 21.23% | 45.21% |
| structural | 15.20% | 21.85% |
| **unverified** | **7.24%** | **11.71%** |
| verified (all tiers) | 92.76% | 88.29% |
| mean claims/field (raw): findings / open / proposed / decisions / failures / contradicts | 9.38 / 4.28 / 3.93 / 3.78 / 0.98 / 0.51 | 9.17 / 5.01 / 3.31 / 4.31 / 1.43 / 0.81 |
| duplicates removed per doc | 0.346 | 0.417 |
| mean doc length (lines) | 192 | 356 |

Schema, claim counts and dedup rate are alike. **Quote-verification tier mix is not**: exact fell from 56% to 21%
and unverified rose 7.2% → 11.7%.

**Is this the two script versions or the documents?** The split is also a date split: the first invocation
processed Mar→Aug 26, the second Aug 26→Sep 22 plus the MASTER_HANDOVERs. Inside the first half alone,
unverified rises with document date [V]: by month exact/unverified = May 85%/0.8%, Jun 72%/4.3%, Jul 69%/6.9%,
Aug 37%/10.3%. **The only month both halves cover in bulk is August (May/Jun/Jul each have 1–2 second-half documents): unverified
10.3% (first, n=77 docs) vs 10.2% (second, n=17)** — indistinguishable. Within August exact is 37% vs 25% with different mean line length
(101 vs 73). So the unverified-rate gap is consistent with a document-date/style effect, not an orchestration
effect **[inferred — only one overlapping month; cannot be proven]**. The extraction prompt, schema, model,
dedup and timeout formula are byte-identical per the 09-22 doc; I did not re-diff the code. The halves are
reported separately in the artifact. The fourth pilot's 88.8% verified is matched by the second half (88.3%)
and beaten by the first (92.8%).

## 4. Full verification

1. **Schema** [V]: 277/277 valid (fourth pilot 8/8). Caps respected everywhere.
2. **Quotes, all 7,094, all three tiers, recomputed** [V]: exact 2,926 (41.25%), normalized 2,237 (31.53%),
   structural 1,281 (18.06%), **unverified 650 (9.16%)** → **90.84% verified** (fourth pilot 88.8%).
   **0** disagreements between stored `_verification` and the recomputed tier. No source document was modified
   after it was indexed.
3. **Dedup** [V]: 104 duplicates removed (question 11, findings 16, open 32, proposed 17, decisions 19,
   failures 7, contradicts 2); 52 of 277 documents (18.8%) padded. Most padded: `2026-07-13-elections-calibration-break`
   (7), `2026-08-19-market-resolution-write-cluster` (7), `2026-08-19-trade-evaluator-convergence` (6). Recomputed
   dedup matches stored for every record; raw == deduped + removed for every field of every record (raw preserved).
   **Dedup is per-field only**: **629 claims (8.9%) reuse a quote already used in another field of the same record**
   (277 of them in `decisions_recorded`, 170 in `proposed_not_done`), and 98 pairs share a quote with a different
   claim inside one field. A consumer counting items will double-count.
4. **Fabrication — 15 documents read directly [R]** (the 10 longest, plus 5 chosen for retry-history or high
   "not determined" density): discovery-gap-closure-prereg (1884 lines), copy-trade-decay-prereg (1066),
   canonical-resolution-write-design (952), heatmap-pass1 (869), slug-fetch-unswept (854), heatmap-pass2 (761),
   tier25-supervisory-agent-scoping (733), directional-skill-persistence-prereg (666), MASTER_HANDOVER_server-pre-setup-1
   (617), track2-ci-power-prereg (563), 2026-06-15-session-summary, archive/MASTER_HANDOVER_2026-05-20,
   telegram-alert-audit, geo-drain-blast-radius, deep-audit-FABLE.
   **Numbers are not the problem** [V]: of 1,808 claims containing a number, only 2 contain a number absent from the
   source document (both "80" for a stated 0.8 — benign). **The problem is claim-vs-quote entailment**, which the
   mechanical tiers cannot see. Failure modes found, each with an example:
   - **Claim contradicts or is unsupported by a verbatim, verified quote.** discovery-gap-closure-prereg
     `explicitly_open[0]` (see 5); `explicitly_open[6]` "details of handling the 16,000-market gap … are not determined"
     against a quote beginning "Decision: segment 5 must resume segment 4's own list …". In heatmap-pass1,
     `proposed_not_done` "the test does not include the directional skill question" is contradicted by the same quote
     (it *is* the directional-skill test), and `decisions_recorded` "decision … not to fix the match_control
     determinism" contradicts the same record's own `failures_and_causes` (fixed 2026-09-06).
   - **Pending TODO turned into a completed fact.** 2026-06-15-session-summary: "Counter-signal detector *fully*
     validated with week of data" is an open item in `explicitly_open`, yet `findings` says "has been validated" and
     `decisions_recorded` says "now live and validated" — the quote (unverified, "fully" dropped) is exactly why it
     was flagged; the claims are false against the source.
   - **Template claims with invented uncertainty.** archive/MASTER_HANDOVER_2026-05-20: 9 of 10 `explicitly_open`
     items are "The system has not yet determined the full implications of X"; one directly contradicts its own quote
     ("Checked: no impact on first-repo"). heatmap-pass2: five "whether STR-00x would reopen … is not yet determined"
     items, where the quote states *what would reopen it*. deep-audit-FABLE: six `explicitly_open` claims are the
     placeholder "What was not determined about X." Corpus-wide, **198 of 1,270 `explicitly_open` claims (15.6%)**
     have the "not determined / not yet known / not specified" shape [V] — some are genuine (tier25, geo-drain,
     telegram-alert-audit are correct), so this is a screen, not a defect count.
   - **Rejected alternatives filed as "not proposed"** (discovery-gap `proposed_not_done`, 5–6 of 9), and
     **status/observation filed as decision** ("NOT FIXED as of…" → "decision was made to not fix").
   - **Quote anchored to a nearby header that does not entail the claim** (slug-fetch-unswept: claim "fetch aborted
     due to synthetic-id clustering" quoted as "Script abort logic (…), unchanged at f6830d7:").
   - **Degenerate quotes.** 38 quotes are ≤15 characters; **35 of them "verify" as exact** [V] — tier25
     `failures_and_causes` for five agents each quote the single word "same". Exact-match on a 4-character string
     proves nothing.
   - **Prompt echo** [V]: 3 quotes are the extraction prompt's own field descriptions, all in `question_addressed`,
     all correctly unverified (`2026-08-17-session-summary`, `2026-09-01-slug-fetch-unswept`, `2026-09-12-session-summary`).
   - **Ellipsis-stitched quotes** [V]: 147 quotes contain "…"/"..." (fragments joined). Most of the unverified
     population I inspected was this — so *unverified ≠ fabricated*, and *verified ≠ supported*.
   Documents with no material problem in my reading: copy-trade-decay-prereg, MASTER_HANDOVER_server-pre-setup-1,
   track2-ci-power-prereg, geo-drain-blast-radius, directional-skill-persistence-prereg (minor), telegram-alert-audit (minor).
5. **The two known fabrications, exact-text search over all 7,094 claim+quote strings** [V]:
   - *"the exact timing of when the sweep will begin is not determined"* — **PRESENT as a production claim** in
     `2026-08-21-discovery-gap-closure-prereg.md` (the 1,884-line document that produced the original), record
     `explicitly_open[0]`, verbatim claim text, paired with a real (normalized-tier) quote from line 4: "No writer
     modified, no sweep run … Every operational detail below (pacing, batch size, thresholds …) is fixed **before** any
     of it runs". The quote says the opposite of the claim [R]. **This is the failure mode string-matching cannot catch,
     and it recurred.** Also appears in `2026-09-20-…-repilot.md` and `2026-09-21-…-fourth-pilot.md`, which merely
     *quote the search string as a thing that is "not present"*; the extraction misfiled it as an open item (exact quote,
     wrong claim — meta-document contamination).
   - *"the final runtime estimate after all adjustments is not yet known"* — absent from the discovery-gap record; only
     in the same two meta-documents (as the quoted search string).
6. **Heatmap passes 1–5 comparison — partial.** Pass 2 names its read-in-full set; pass 1 names only 9 of its 24
   (7 handovers + 2 audits), so the "~48" is not fully enumerable **[V: from the pass JSONs]**. I compared extraction
   claims to the pass conclusions for eight named documents (gate-result, gate-recall-diagnosis,
   limit-restore-and-sweep-closure, n0-gap-check, directional-skill-persistence-test-run and -run-2,
   skilled-presence-causal-vs-compositional, str002-thesis-cell-analysis) [R]:
   agreement on 7. **One disagreement:** pass 2 withholds a grade on STR-002 stating it "did not locate and read … a formal
   result document with a CI" and cites 34% accuracy over 227 rows, while listing `2026-06-30-str002-thesis-cell-analysis.md`
   among documents read in full. That document (and its extraction) contains **9/40 = 22.5%, Wilson 95% CI [12.3%, 37.5%],
   gate ≥60% failed** (line 6, line 64) [V: grep of source]. The extraction is faithful to the source; pass 2's stated
   gap is wrong about the corpus. (Populations differ — 40 scored vs 227 rows — so the two accuracy figures are not
   necessarily inconsistent; the "no CI document exists" premise is.) Nothing else compared disagreed.
7. **Field reliability [R, from the 15-document read + the corpus-wide screens]:**

   | field | verdict |
   |---|---|
   | `explicitly_open` | **UNRELIABLE — do not use.** Template filling, contradicted quotes, reproduced fabrication |
   | `proposed_not_done` | **UNRELIABLE.** Mixes rejected options, negations, done items, TODOs |
   | `contradicts_or_corrects` | **UNRELIABLE.** 5 vacuous "corrects the understanding of X" claims; garbled elsewhere; sparse |
   | `failures_and_causes` | **UNRELIABLE.** Category errors (non-failures), degenerate "same" quotes |
   | `decisions_recorded` | **Weak.** Status filed as decision; 25% (277/1109) duplicate another field's quote |
   | `question_addressed` | Weak label only; 3 prompt echoes, some vague or wrong |
   | `findings` | Best field; still contains contradicted/false items (e.g. "validated"); use only via the quote |
   | `path`, `quote`, `line` | Mechanically verified (90.84%); the only trustworthy content — as a **pointer** |

   An index of fewer trustworthy fields beats a complete one that is not: the defensible use today is
   **quote+line pointers into the source**, never claim text as fact.

**Not done, deliberately:** no synthesis; no re-extraction; extractor, structural index and flock guard untouched.
The 5 failed documents have no record and should not be assumed covered.

## 5. Brief health (2026-09-23 ~16:15Z)

- **Host uptime:** up 11 d 3 h; last boot 2026-09-12 13:07 — **no reboot since 09-12**.
- **Services:** `polymarket-monitoring`, `polymarket-observer`, `trading-swarm` all active.
- **BUT both polymarket services restarted at 06:58:17Z today** (NRestarts=0; not a crash). Journal: `apt-daily-upgrade`
  triggered a systemd reload at 06:57:39; observer stop 06:57:47; observer hit its stop timeout and was **SIGKILLed**
  ("State 'stop-sigterm' timed out"); it had consumed 10 h CPU and **3.8 GB memory peak**. The orchestrator also came
  back ("Orchestrator online" 06:57:49). **Monitor RSS's last reading before the restart, from the observer's own
  log: 1,369.7 MB** — up from 1,340 (71 h) and 1,345.6 (yesterday), i.e. **not a settled plateau**; the trajectory has
  reset. Now: monitor **395.4 MB** and observer **250.8 MB** at 9 h 24 m uptime. This needs a fresh baseline.
- **06:00 maintenance:** completed, exit 0, 06:00:01→10:43:43Z (4 h 43 m; earlier reference 4 h 13–25 m). No refusal and
  no overlap/flock message. The category-backfill and resolution passes logged one API error each (`422`, `errors=1`);
  I did not audit individual steps for failure beyond the exit code.
- **`polymarket-sunday-elo.timer`:** disabled, inactive (first Sunday without it: 2026-09-27, ahead).
- **Telegram, last 24 h:** the only send I could find in the logs is the orchestrator "online" message at 06:57:49;
  observer reports alerts enabled, legendary alert silenced, pre-resolution messages suppressed (44 logged). I did not
  find a per-message send log, so "zero others" is not proven.
- **Repos:** first-repo in sync with origin/main (0/0), tracked-file modifications are the same six runtime state/log
  files as at session start; trading-swarm in sync (0/0) with untracked run artifacts (index, failures, state, agent-output
  audits).
- **`metric_v2f_oos_result` canonical hash:** `021be40a87df48c1f37efb8265f223b005c9c50bca8e32ee1bcb134fe074cd4e` — **unchanged** [V].
- **Tests:** trading-swarm pytest **178 passed**; first-repo `run_tests.py` **31/31 files pass** (its test count is
  flagged "partial — unparseable counts"). Plain `pytest` on first-repo reports 31 errors (`fixture 'results' not found`)
  — the repo does not use pytest as its runner; those are collection artifacts, not failures.

## Follow-ups (not actioned; need a decision)

1. Do not synthesize from this index. Options: expose only `path`/`line`/`quote`; or add a claim-entailment second pass
   before any reuse — the existing tiers cannot detect the dominant failure.
2. The 5 timed-out documents fail deterministically; investigate generation (not the ceiling).
3. Monitor/observer memory needs a new baseline after the 06:58 restart; the observer's SIGTERM hang recurred.
4. The heatmap pass-2 STR-002 gap is factually wrong about the corpus; correct the register if it is to be relied on.
