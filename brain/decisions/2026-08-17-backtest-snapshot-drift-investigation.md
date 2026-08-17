# bt_pop_2025-11-01_v1 snapshot drift — characterisation

**Date:** 2026-08-17
**Scope:** read-only characterisation only. No writes to the production DB, no snapshot re-freeze, no test-file edits.
**Trigger:** today's `daily_maintenance.py` test-suite step failed 5/24 in `test_backtest_window_population.py` §2 (snapshot reconciliation): frozen snapshot expects 4658/54/555/573, live reconciliation gives 4660/52/553/580.

## Verdict

**DATA DRIFT**, with one compounding but distinct finding: **T2f is a test-completeness bug**, not itself evidence of drift — it would fail on any day a specific class of row exists, independent of when the snapshot was frozen.

- Pinned side (`backtest_population_snapshots`): **intact**. 4,712 rows, single generation event, no code path other than an idempotent `INSERT OR IGNORE` touches the table.
- Predicate (`backtest_window_sql()` / `column_definitions.py` §6): **unchanged since introduction**. Confirmed via git history.
- Live side (`old_method_market_ids()`, i.e. `markets.category` / `markets.resolution_date`): **moved**, because two ongoing daily backfill processes silently mutate those columns for rows that are *inputs* to the comparison, with no audit trail (no timestamp co-write) marking which rows they touched or when.

T2 (4658→4660) and T2b (54→52) are a matched ±2 pair: 2 snapshot markets flipped from "excluded by old method" to "included by old method." T2c (555→553) / T2d (573→580) reflect further live-side reshuffling in the same direction, dominated in raw count by a structurally separate issue (T2f) rather than by genuinely new false positives.

---

## Q1 — What each failing assertion actually compares

Read directly from `tests/test_backtest_window_population.py`, function `run_tests()`, §2 (lines 217–259). Two input sets are built:

- `snapshot = snapshot_market_ids(conn, 'bt_pop_2025-11-01_v1')` — **frozen**: `SELECT market_id FROM backtest_population_snapshots WHERE snapshot_id = ?`.
- `old = old_method_market_ids(conn, '2025-11-01')` — **live, re-queried every run**: `category IN ('Geopolitics','Elections') AND resolved=1 AND resolution_date >= '2025-11-01' AND (trade_gap_flag=0 OR trade_gap_flag IS NULL)`.

From these:

| Assertion | Computed as | Compares |
|---|---|---|
| T2 | `len(snapshot & old)` | frozen ∩ live-old, vs constant 4658 |
| T2b | `len(snapshot - old)` | frozen-only (false negatives under old method), vs constant 54 |
| T2c | of `old - snapshot`, those whose live-queried `tape_end` (`MAX(trades.timestamp)`, computed fresh via `tape_end_map()`) is `NULL` | live-old-only markets with zero trades, vs constant 555 |
| T2d | of `old - snapshot`, those with `tape_end IS NOT NULL AND tape_end < '2025-11-01'` | live-old-only markets whose real tape predates the window, vs constant 573 |
| T2f | `len(agree) + len(zero_trade) + len(false_positives) == len(old)` | whether T2c+T2d (+T2, implicitly) fully account for the live `old` total |

The critical fact: **only `snapshot` is frozen.** `old` and every `tape_end` lookup are executed live, against the current state of `markets` and `trades`, every time the test runs. The docstring's claim that these are "fixed facts... will never legitimately change" is true only if `old`'s inputs (`markets.category`, `markets.resolution_date`) never change after the snapshot is frozen — which they do (see Q4).

## Q2 — Is the snapshot itself intact

**Yes — pinned side unchanged, only the live side moved.**

- `backtest_population_snapshots` schema: `PRIMARY KEY (snapshot_id, market_id)`, columns `generated_at, sql_version, window_start, window_end, market_id, tape_end`.
- Row count for `bt_pop_2025-11-01_v1`: **4,712** — exactly matches `SNAPSHOT_COUNT`, T1 passes.
- Provenance: single distinct `(generated_at, sql_version, window_start, window_end)` tuple across all 4,712 rows — `2026-07-24T18:54:00Z | 1 | 2025-11-01 | NULL`. One generation event, not multiple/re-run.
- Write-path audit (`grep -rn "backtest_population_snapshots" --include="*.py" .`): the **only** code that writes to this table is `scripts/snapshot_backtest_population.py` line 113, `INSERT OR IGNORE INTO backtest_population_snapshots ...`. Idempotent by design (composite PK), no `UPDATE`, no `DELETE`, anywhere in the codebase. `scripts/build_event_cluster_labels.py` only reads it (`JOIN`).

Conclusion: nothing has written to this table since 2026-07-24T18:54:00Z. The artifact is exactly what was frozen. All observed movement is on the live side.

## Q3 — Enumerated rows (the core deliverable)

Computed with a read-only script reproducing the test's exact logic (`sqlite3.connect(..., mode=ro)`), executed against production DB as of 2026-08-17 ~17:00 UTC.

```
snapshot total:        4712
old total (live):      5988
agree (snapshot ∩ old): 4660   (test expects 4658)
false_negatives (snapshot − old): 52   (test expects 54)
old_only (old − snapshot): 1328
  zero_trade:      553   (test expects 555)
  false_positives: 580   (test expects 573)
  [uncounted 3rd bucket — see T2f below]: 195
  553 + 580 + 195 = 1328 ✓ (accounts for all of old_only)
```

**Direction A — in snapshot, NOT in live `old`** (`false_negatives_snap`, current count 52; full list):

```
0x04cfc9a207e0d14f1eb70b6334e7436f4492cd7e75d2f857a83984a237c008ca
0x05643fb63793e2f30638f3b91c2c474529bf6357e524427a7ac9f2ea227cfc7b
0x0e579bcc61a9bd64af71ff9ddbf44c22bd7809acff1a53244e45fba4d07f9073
0x1161a32141bb18119d627d6747f1cec4f7de6aeed15abad0e6b1aa8af3b1a844
0x135096de7aea3a66f65be697fa6d6162b28828ae15f4802a41f2c3b719792e5c
0x17898a96b75e23f9bc7a14cf5bfb3b699984c1b729471bbfecfbc9f2fdecfdfc
0x18f7637335809af5c5fdc9f3158207bc06a63fbb71fe35d8a7e812142f91f701
0x1e3d9b0dd4ec88715195d7dcc4e5a700558c932acff03e10c1addaaf7f50d8c2
0x23e488a00557f5518b4f923621c4f13b77fed917ae0a7cb9590a37917bc6ec76
0x2953a5f45c2908c95bd190a782401cb61aa49c58f11efddabc79f3cae3a9c25b
0x2de705343408346161b21ddf3f9218378dd5c9ba0400d46597910e443b414044
0x31f8d949361c237709f81890ed313b25809d8333e78e155f34035fe99b9b5d1c
0x3c0585e53f8a8ac29b1e81fbc89485dcdf451f0409648fa36417cc9f0487317b
0x3d16ed6f91ad7d3ffb1633e792a6b5595cbd30cf8a9f63883ade9e6e97c8bdc8  ← known regression-guard fixture (US-Venezuela)
0x408682d9dab27e0df883c87db798313c718015ae48a94eb97447cbd80d462e53
0x491630ca8fed90f86de81b89a658404dc27c849c711d7a33ead464fe5773ed08
0x4a937f5db5c57600543afd2f3ca39f5ae53fa15911ee24fa2aae509ac8edc4d9
0x521aa5c71f3392f1009b5660cc0f23e6b0cbf098227977004122334ba554037d
0x540c08ef981da66f30cd8185329251235bde07e080ae4036c321338cd708c124
0x56112b7c36a3e7ab7a52c4edc76a18369934c1b4f091cdfd7e633b5632771831
0x564dc4a385305c482015061537989c4af69f1556f40b958a7bd6e4cf84ad1e2c
0x5b627c7b2f82ea92dfb69650a87724664ad771d33ff838c11907efa71c5a4d61
0x621c5b98c500aed261c73924a6a2ea747266415eedf11e9e443604e3d324951d
0x667c5b79bb2d8ffc24024e2d3e80a9e72117b2ed4b4f571f1bb1ce9252a7eee1
0x68f3f79ee22ffd2e212bd9f1e1491baf15501e4186782702dfa646c10465720a
0x6a84da96dd65af304fe37d1c45548dffdd5d1be2a0dcdb81feb164ecaf44312f
0x715eb6357edc59dc38d9f7da929e63be58fa4d3b7bd1415d7950a60bd4317827
0x72fd34356ac9f6c6da2de4e46e8913f6caa775e7c6bfdb391832c9d76017879e
0x86952fac5f5a55265ccbf5972c1016308291f3819b1405919080ff79be9928ec
0x89f4e3a08d3c39a9af5d6177c18d90b537228599375ff81ac5171da7921cb204
0x90394c2848abe272fc43ab6d3842efc6ebcf41aee50ec9fdca1980a6452ff19a  ← known regression-guard fixture (Babis)
0x91e0a718041ddbf0855fb655cfcb5944636b33ce8ccaaee7dce0940aa80465ab
0x94c99f6465739a323859e4bdcb5091ce6e064b67a956b5c603974e574807efe6
0x9a3fccf3300a8c7a8d30d40f343742ef9f2a8a1a5066c00492af3e5c1f9ee68a
0xa067b73f3c00536f841ceeab84998af6c0d96c213dfe095db4d7e3f41dd6dc0d
0xa12079c3462f7d278f3b4184ccb7ce503bd6cc44e192131a2f71780037aed634
0xa559347a8eccf6f3d07d7e5b5b749a0b677acc066f4101037aa53b880d1598ea
0xa56afcf5b2db4531f9f339edc04acc9c29a777127b79164cf8850556d164f5ea  ← known regression-guard fixture (Zelenskyy-Putin)
0xab03a5adc30a70d64279a1e894b94665583fcec6ef6d6fcfd2d4687968847ef5
0xb326f67a9fb3feb7fc007e75871f2496dbac995cb63f4729702822dcff4af51f
0xb54dfd7b69391e65fcdeb291e09606e2f3c44ef3a3e7b6dbd1d411a4ed4c2b54
0xc89a8835e1638383338f6f5925591fa1dcb0f7c470c232f53a7c36fcdab96c40
0xcff999e258f449a28ba7e6985a822abbfbbe07b846b477beaf1f68ea469cec4c
0xd562bb4ace325b68081b92e594621294e0012ac39d3af48f2b1fd43cab925f69
0xd6b3dba9eefc9b556c3bb0f140e7d530759e70ed1283caeb162c31df477c1e1a
0xd757680e9e73d40ffcd21f729d49394305e70ecca655a10f56ea17fd654a2d8e
0xdb6ee0278db8c3d686ff52f75258209ac4d5394b0c8cc2c643f0abdeaae6afff
0xdf7970971fee58026dd3331e3ebafa799382443267f5b4f959f2e14e05c7900c
0xe106f68456bb41fd58bee7f2f4481722cb55e34fcdb6bb72003cde9f4e37fecc
0xe49a5564a920c756d51f8b171db40a65bada3059e324eddea98dcd6305f37c47
0xf4960b7cfb93cd311931bce236580d78982e88bfe01cb8669cfa4808813282ad
0xf60726a45cd436184484829eba1159b06f55cc0f83249dfc655702766d158e3d
```

Note: this set legitimately still contains the two of the test's own regression-guard fixture markets (US-Venezuela, Babis) — those are *supposed* to be in `snapshot − old` by design (T2 §5's whole point). The historical 54 always included them; the current 52 do too. The 2-market shrinkage happened elsewhere in this set, among the other 49.

**Direction B — in live `old`, NOT in snapshot, but tape_end already qualifies canonically** (the T2f leak, 195 markets; full list below). All 195 satisfy `category IN ('Geopolitics','Elections') AND resolved=1 AND resolution_date>='2025-11-01' AND gap-clean` **and** `tape_end >= '2025-11-01'` — i.e. they would be selected by `backtest_window_sql()` itself, live, today — but are absent from the frozen snapshot:

```
0x02685b4bba2ebaeb29185cb05b34b70dd43c76d2d36b73eb580b926551cbebcd  0x05069df3b825fb89843fae06511c6af786e6f4e1ccb172778e1d7a84e2b7214e
0x0eada57dcf53965a321f61c9dc6adb655367fabeb1f2ecbe7746f3f1a6ff7769  0x114ba3133f9949f6a34f75caf515b6eb43eecf19a71958fdb0950f4bd94cf10e
0x125d64e41a8b3225d81e84ec1fbeb58b1d8091fa9d54a9f500e01a00586baf9a  0x151b13b0d75a282ea864a2835963c0164c03e8fa3064c4d44026e3af5f2ff8d4
0x151f00b091b2e346656190b49c06644920fdba4f1280f7976e7f5f6bdfec7bb3  0x15a99b7ac17e9cb8972f852ee2798dfba6fc977a53ff3bf2f99527305e690411
0x1ed0129a282b77400f585b1061c252ee9c29601328d5fead07a17bea2b3d9510  0x1ee55986634de427650d59fe8f8beb86347a78d29f5e8a5a729c587cf3e878a0
0x20af55ab35186377b81219db6cb8615240cba42cea41731091be9484a5f5b122  0x22776ecdacca07302e6cc578cdcf26df93b4233d5a8166cbf131cb32fec425b9
0x23138fc034c49853887431d6009400c26dbfb09525e0edc80878c218d19e28e8  0x253a4a01dd09a35fd73e6671ddaacada7af886af4d5c196dfc9a6d50b1e735ba
0x29c4546d17267601dc346e53e437fd4ea859582230d41f4fbd9af709f066b1d5  0x2e40c0874cf8c3e27d678b5a610c1b91fba1b1ab6565d375e2777a740187722f
0x306bbce53f9a77906b9a928d52728bdee2e48f3354d19a9d6f0db7c9a1d4230d  0x34c1cf28ad9c8bf47029851c867257248a30956ff463e504a36b270c68fa853c
0x3ccf6d97e3e2177d6788186739b68f058188a5959ae1555beeda65be2161dec3  0x403a2992ce3adb0df0af7054074191b5dffe20fbd3bdcd4b993224529f6d4e4b
0x45c0fbb37227cc6bc74b537aa1ed20c81990155f447cbaaa47514b6e90611288  0x54340f047993498875e98e36447577fffa83a23de09b613ab7b2e98bbb7b41dc
0x5c821128f7511d890298bcdab4a2424a40c35349d3e994a117c7e36db0fcab9b  0x619165fe3568255c0a048d9350b5011c19f17bcec0474e867a1a983e6411ceff
0x6912f57515190db649735f6d70f004291335136da50ea181632f6d5e6f89a0d4  0x6a5589de888a72e9e1d711a323ceb1794c9135d4f4a2029fe3bb1cb6cad66e22
0x6a9cec83f126fe719234360176ec90d6e9ddf7738dd18fc24591acfa4ffeb438  0x6bb7b47236aafe3cde3389214c31055abaa815b7170d9c12dcbea43b8a884925
0x7622efdc8a2625beacfaac2456ed56227d5d1bff20d66ec54233b2822a95887f  0x7c27e0e039c587c0dd63104ddb3031fd635cfc1e1b011c748259a54cb942bf0e
0x7e7f59ff239a1ee48639c75a64cc459980f04baf138381d5ec161d7e4a8c6ef6  0x8a69c2f5a3745b17fa805e65c4f8ba75b407559093925b12417307b5683d73bb
0x8d240de0d0ab5a55bc688eb09ca7066a023fc0942a08d6cb2607971eb87d936f  0x8df7ab1fbb9bd8991546a6c5066dd24790047e6eb8033abf93993506c0f3c75c
0x922428a849cc40477adf1360da7690a418a6ef95cb3bc35ce737860670e2ce9c  0x9b6e858181395f22b4042acb2084dbd39d77660370bbbb19012e8279c3292d08
0x9d1520ab624df1c766771be60573788eb01dc365d682445e1a9c2d093de26291  0x9e795dc2cb31d95fff415eca5f715d8eb23806181bcc2b4f152de2503b6cdc3f
0x9f4f66e277053f6905baa70ad780534e891830293047b713fe14ae08faedaf33  0x9f8bb7bf0e271ed0a67f0145005a5be21d9750f65b35d647c88866251b04d5f4
0xa5cb362d7f20279f44174870044de409b50ce2838d6316df61c1f235c7b64ab0  0xaa25aa5ffdb235f693e38b8eee295604bd431d87fda4f79c5dc5f152ea875b17
0xaaa219cff0f1a418e0fa2aa11b47a3bc642e499dffc19312c55b25fad570bd18  0xacdc5858c069dec87214c3409548e26f81ac7af2919d501bcd3801041d52933b
0xb476051cd7933d0059cbaa04ea57ad8f1ecceb32b19c5497d6332b839c62ccc9  0xb83df8ea773e1f6693320c4ee94f28ab3fbe10d270d695b6e0f76d03cabeed4d
0xba77e43ce5eec1c4a53410eaef174bcd95de755140074084e8fa1c5ed0c1d48a  0xba8add06562a7bfd4fdd8f0a1882b5e2596540bd61c67a32359487694838f0a5
0xbc63ab257269b6d88696a7c395c22a032dd8bcaec0f20b22083ac17dd8a9221c  0xbe08b5f2fbf360dc62c8ec2f4dd7c3e76d894d50999f5186769c9a31c05f489a
0xbe08ec8bd0b841076cc5ec9c0a2299d180d4af07014c08c447000f6fcb85323f  0xbe138cc6f69100766dab81d6f5306a8e2a3ee0eba63ec1a853279b7ba1fedda1
0xbe1b6be48dec02bf55faf971e45829b8957f2e4638907bff3c13a898cde69f16  0xbe48dfd8fb2d44ebad08c3b170799c6633af2b68ce0df17e633e12a89ed734e3
0xbe6526cea1f4310d1d673a1c288e1b19e4c8a84224c4b839f92e3f1b8a02b4af  0xbe6cc146674e6deb0e52030c79d613d4f29c7b7184319e37be437ac535fa10fc
0xbe71102a0093af78a467e514f62886d851aeae2287872843c0c1a4ce04b9794c  0xbe7a2a1d37a76438d423a8bc08d51a4b211bcf8d5b25ad48ea5df336b2fec5e3
0xbe8c57909e95787b09254f9c0e874fed7526c9f03fb70d34bf12a54409db6c2d  0xbe8e69a4cf0a4cc446f4b9dd47fa589f705e7959535453cc5d0161a55d02cb94
0xbe950fa6909d526df398b462ba10fa29a607d259d0a3abcb4f36ab82a7d00d34  0xbea088d2cfa887c5985be2b3feea2ea5ef8fdede3933ec0a415d1de3813a48a1
0xbeb74a94f27ced60a901e58f199c8a72df7de3cced3a117a57da3133c538dc6f  0xbebac39466bd7d503f0fe371ed373545a7547d05435bec576b6a9c2761b8a929
0xbec45bb74e6841a83cd8f2f77aec733550e3338799bdcc5ca6d87feb5f94c6e1  0xbecdf702d1e16f84b868262b17d733b0da89f3b48613ce54e3a2ae41d17fbc0b
0xbecfcab892fc16aabf72d5180094c6c51ba33ac8005c3f9497b7c6d05bbee7f1  0xbed351bb30927153045ccbab822757e8ec08e8c9456d478e13186ac241e593c1
0xbed3697cb31169b73712384630bafcd452689df1315321414e8445ce4d89221c  0xbee17eafface542ca5f3d99260820f9d52645e7f5a13b73a089b9e558a5a0ed4
0xbf08ec6654ade883d96f3e25a5330ccf4aae0d8e9efa690c694305e95738e8a1  0xbf1168b23c7a12efdb4313988bc32faf436b75999f12154a3c214eb45859b72c
0xbf1274b2f04186ebcf58b2ce3002fc473bd5d6bf7e7d163bd43d44a7859e05b0  0xbf175df87f4cbcbcd65d85866b9e837e0ef1f2d0f1c14b6e01791ec28c3413fa
0xbf245f51ee0cb5020ffc948b2e63d86ca112c2691665a043a2e139f0c9d4d1f1  0xbf262e0e0200561f117d405a0e3808d4465a16329d5a41129568400b7c2a349d
0xbf2cba044810364349878bce032b495875a0ae8b575286388e79cc4bddde4a6c  0xbf3ccd086ae9cedce80fc8ddc4a28b3d23cd2f591265b82bb0e9454c975e5fa5
0xbf41c2452187f46fab6c463c801c5205d1b574409896ff406fb2a201dbb1abda  0xbf45221e809a94af5ab5a9398dde4faeee21598316a1d3032eb822bec0790389
0xbf4d039a4b98d686391d2181ce4fd2848ff2e606d8e0738e480e168e2f544321  0xbf5cf28247aee9a31ffe6fa766f4ebe4659bc5ac0fbed58db4947cdab963b231
0xbf6925f233fd9f08edbcdd14c8f53df141d7f6c0e968d9bfb891f3115f2fcc40  0xbf693e9301e39676b1b5afa333c563f305ded7f77871e2650a50a6ac9dffeb0b
0xbf7069a49fd9dd31f8d1bd95f66f3de8b91574729ba69bb1d6be5733df45ccea  0xbf75c48fe5c894bb4f00759128bf70052d7c18bd63b17922601c269aeab27850
0xbf7ff429bd5aaa450ed4d732fddfca7d5faefe9f65e8c638595964977b83a9c2  0xbf872e641e789e0c61fba517434d3e203d59beb64068ad6ed460fe20e0c096f3
0xbf87c41fd13d8cd40cb13c7fc41ea13dc6d45c65033caf60f21bcb95d3bb5131  0xbf8ae6bfa433b023e1fd7a78033dc8945ccab08a7e8ab746214e8450dbcc2356
0xbf9d13154d05a217594727b2dba49d21af0cd78da1c0fa7e28515ac7c749fe95  0xbfa0b56a900d2b292ec8a9d678b7bb970bf6e37d3248aca4caabaf5dd38df6ea
0xbfa1cb90e3a3148df952edd8a291012313f4375f989c0c7f9a7ecddf08bfeb07  0xbfa6ad49231dbf3a70909f888736c3f117aa0d2c48f6196b098661cc9308869d
0xbfa91c5f24d1d6b69c6c974624ac72b07c5ecd92ea6c95686367a55129a0c9a5  0xbfabdf938f53c42c66b408277da312864cedabee54e79feae46b04dcbb5f9f41
0xbfb0390157f5ba2421213ab9d289333a11f2d04139b79c3084d69a0e71cb6e7a  0xbfbe9c61a42b64390212edbe9db81c20c470a8e3c35a16f47084abd8a19220b9
0xbfc1a3326c705a1dd4abf7ade1f5093292231dd9bb0d8a791e6051af8883f21f  0xbfc25a82b6a6476895991401059bab3a73df1a9278400d70dfad080774a981c4
0xbfc7d5cbc18e44fae4c882d807c4654d81438e178c333c15769fafc878ed7da4  0xbfd4bb8d6a1e16404dd95d2e5c4af005f11f07d37da91f1e9e442e4dd9878e6d
0xbfdc5ba2770c376634562bb9e16929aa2fb413cfd0b086dedcffbbf16ec8b9ad  0xbfe5ca05ae10db910b5082d022bddb7a0a82619cfa1ee80b7ac7c38fb7407750
0xbfe76fd28533a0f8b5d1a509d49c7df1297a5bdc43dc84f3dd01448cddb49aad  0xbff1b2e77a9962967464139bc28b22e19ed0170348695446df1d6ce45340640a
0xc001223d696cafc2d974c2d96d90482de4d917834a71274bfd3715351e8ef40f  0xc00ec2caa89444187c0d3d4423bb0f237b0fecc4308157a78594f7e706e56fea
0xc0246b177923d449838e24a115cd686f3140910a449e0f4b3b28427c95655018  0xc025ab2a9dbfb28842f8647b13092609dbe746d4928eeeff90d4b342139be5cc
0xc02b21787c321c3fa735d85622ee7e9b62b309b2ab68934e2ddefa30a4644330  0xc02fd37d2b71352797778104dd352b539a0bd888b083755798b6ab9e3bac6676
0xc0313a0e32c392f3c8de35a1699872ae29e5c243d43ebd4913cb525f00beb8aa  0xc032ef77d794182020de96660aa02b5648018d06ad459fe81e080e3ebb2eeb0a
0xc045aeb1a1024620dfec1848ff8dccd37b415be49a343a7b21bf192f141d7e07  0xc04aed039e66ca7537a0021c58f8d15373c539eef59ef2cfd560b64a2025f194
0xc04bde8627546452ee1c24b98b850d1da8082b3013a600e4d2b5058208ec7326  0xc04e02596267da95078dc9505c3a7879f1630aa87423063d162afcbe6cae221d
0xc0531ca3aa67e9aec21f8265fdacf39f960c24f3faed1a3e5ac9b4613e6fcd98  0xc05e696945f81c3b1f6a8835c95b243a7b8f88a1a4fa99abfd677f5ea7f24a80
0xc073cfc409e04f715dec877108b33c51bc309bf32ff5d448299f5b2155e839a1  0xc09535a2f39877de8b488263bcb271868e36a55d21bc25ba4106ec0f14b9754b
0xc0b20d588e04ccffee57380fdd9143fda8f61f227981a901c4ebef87e4e600a2  0xc0b86f7d763f85cc1756f8c8f7db483714deb39e9d79e946b5416dcd16f457a4
0xc0ca47efaff5155cf78d38b18753f46d7420e0d917297b0483936222e5a6fb39  0xc129e566b938291673288175ad61b296e7115bbe7667b6f79875eb4cb904d3ac
0xc12f336bfc3dd24975e0a9b0917f772aa804987ded738e1a14cec374906bd395  0xc13ab85091ee26b477ddbdfbef89c07f379b05b320f7f63fb1faa502a23750d7
0xc13bdd1a21dff58156106bb60e8c3ce83d0a1140c3ca8a1d37d588981c52a778  0xc1457c33f935215844032549909227eb97ae02954fe46ca441cd8327cf1279b4
0xc14c3aa3de29a0154a5ff211169158b71c53c63326668d190aecdc9fcfb304aa  0xc14cfbaf7092d8d74c4e576900eb9c93acd67257e9d47bc4fbb4824daa55e947
0xc14e9e3c85790585cd24593d1b150e3f225f8663fa7542139d79c602f6cc0911  0xc1777b639dfc67c2570350689b07667d29b9b83046e30e8a02b93cb1cee1052a
0xc189f9adf110af4a3052e2de2d3728bb7f3593cd4645b7034347824d287a77b4  0xc18b1b9c7ffca0f781bce2fe53538bb5b752fd41ec4757c9047e1a097ccfff1c
0xc18d22c0eda93990349730b4c7c219637b2ce5f4bdb0b771a1ef5336bb5f5fc2  0xc198136ea31aa64a8429a61d3ee30fe06cbea57e217a024904672f3c7f78a96d
0xc19eed341534fd9e710b435d3eda630bdd9458a3c0c32d15027442f5835ec037  0xc1e6e7ddb5bc4119391c57f62bc3f2ed1fdf1d2b02cbba15df7782a988fe74b4
0xc1e8d635902f36a4b37d6cdfaee40ae60c2c638bd0ec22eb4e2380b3ea233fff  0xc1f43db60906fb03f0db0283a1841bd77d9e0efb12e203b7949e620505821077
0xc1f6c6e03bf5546c214eb477f676416bdeba77c6566d22186887ec9795fad9e0  0xc52cdfdf348a4ac084c8b08f19f8d69fbe8cfd61cdeca9950b0c3954ba634510
0xc5316711513de452a70861aab65ace15cfec2610f278e14a1785d0d954a043d0  0xc5331256bff341491df0656772c4245a99a483c58eeda2faa70fa6bb8b7b0405
0xc54459e2f195f986d34e39d01cbc749611df14b2cd535a3d1fa1a3b9eaeb1686  0xc56012b36287545832942b89dd7de8699f589850b1dc829855b4b5393278a706
0xc57f9705caa5090a1b98ec3c2b34f659ad8631683481d183e1e9830b72a25b74  0xc580316aebca4d2aa5ff9bd0f876a148d8ee665c0cbbefe3a29f01438dae9094
0xc587bda904f031a973ad3cb57128ca011bfab0f45e6cb3734ed2227c4d4be419  0xc590d9cbe40506aa3c8b70302839730a8261c288f7828df5c5a5dfdb89f3ff89
0xc5ac0a65974594860f532b28767941aaf584f23a7480896b69cfe6e94ece0ff1  0xc5ba5bcafd5abfe6d6f08ffcfc45ee3cf1b8abc9a108a476fa20f7da6f43709b
0xc5baa8d1483c553b6ac5f541ae4d01352dbcc9987a8b281c25d83ced8e4d91cb  0xc5c7e75579ebc7dd442e3a0bc40e47cbfcb641666ad3f8ea0bea24ae51d7523a
0xc5e50bdb528eb82586b52e6d696ce95cad15e4d50e2263b55bb49009a5bb2e12  0xc5e87c9eda4161d4690906c26ffc51522a6de1c831b36a4162b68e0cdd0a4b4a
0xc5ea40be6215b0fdce559737f90f19ad77185d2a13b8d365fb8960678a4b65ec  0xc5f5660224c9b9a7e28846072e98acbc7c252c422e5f1fe7f99d7da56fd33bb7
0xc5f91c8e11216dc5f1241aa1c0e454059713c1da4bcecb5dea8840fa15463288  0xc60a01a86797f61188a3e593501a25af1d0fb3ef593987f18e0369f086207392
0xc61c21cf4d51e0840c70c1510d68cdff68daaed284d3cfba305380ed02fea010  0xc624c1a09abf480ab5de0dc250762cf816b3d9d19b6b9e5bf9cd34e51c26c485
0xc6296fc30f85af142333de2e6e909833cc18403952cd1b181b8a15ed541d1776  0xc645adc49c70afb8e6afb45d7b2b68135a9b82d7a97dfd7d97fbd8654d643b03
0xc6789a2ac662dd271d11f0d4e65fb0f323b680619de5ffd57815342aa3a6cecf  0xc686195f3430d7e557866f91e92fbe55b98d2935ce3a9a42926cfada945e20bc
0xc69829a2b2060ac927db1d6a0d31306c5788be788b425c4b9db48c775cf24c97  0xc7d75ccd731990bf4104a1cb5354fa3fe18dd00c1959f7f85aee2bc4413167c8
0xc7f8cd42502a48cc6b2b54764f4ce26b1132df329ee9cf49d7e3461bbd718b0c  0xc80dc8d53efc821c44ada24435a9108ca7396e1364a9e9dfa625b6ec4cffd036
0xc88b9d1e8be96dea8d9d2a1e580e24b4b3d090aa1ebbc1d234813fbde40b80e7  0xc8bf5b2024ac0bf8cd5937fcf8d80811a00fd89bc7d4365b24a13f8a0111a862
0xc8c0c2020987aa83646e7e08fe1843004f593e052e390ce6a5efb93f29afeb01  0xcbeb3b9ca5c6c02342b22b457f1e18354696bd47707aeffea0fda7342060a456
0xcc34539220f4eb126de2959bee1b494b992e7d748e39afc23a9ba6140770a90a  0xcca3ac50c29fedb63022f03e456b2322e98629712def780c5f5467c59d8aac51
0xcd0c21f04ee9ab58dd9c823f792b5bb2d2baa1b674e36dae25f66257a19f38a1  0xcd42609d25d917422949eba8efe5ba9faf3d8374d26ec9fb7192c117c63ef022
0xcd4e5bf8cefe10729cd72eeca5724469b8b4c675c822962f991a6b5cd4cc2592  0xcd8c8bbbae729acd83366d3f118e428864be2db0678496879e446aa09d284345
0xcf0cac30bf9143151a350dad947f8370847a0bbd3be9b88336e83c0b6d5774e9  0xd02cc74affc0c07798aa12e0beb6f5bf7eb23134a34f074cac985dc86e7e0e84
0xd25c820d3aee1c735c0fa62c36f4905632ab8c6988653b5b4134593b3209eb7f  0xd482f14b4a09d5d554589e8049d4c8eb367bd5caf01c9cb6d45e058b73cf1835
0xd4d0d31d6ddcd7912f2b9eae2cd6d897a21707eed18b6535acd03d60846eb738  0xde07228f2e6db44b37afae1059d2dd13aca52c0803bcc2b67d874a5b39d85ee1
0xe20b49311390ed5f5e0fc23d242ec527f0203ffc4512764d9fe94447e33055ab  0xe53a3545d1b55e0075b3f4863d538e959dc722c066293a0f41ce5a429ee9fcd0
0xe6703820029400bb3989c9ca94511ae96bcb6bb212e76bfce28fbc3d0712e7da  0xeb33df1334122ae60e1c3c3a7eb9420a7a12e3391523ce7dcd6e20a0d015e3f9
0xec4dc95b761c2122d08ad01c6741be853d5cfab5987bb47229f27e1236c38745  0xedd9faaa96ae2f00e92d3d59e19b75ccfbc388b5873ea419bf579dcc870d5fb2
0xf461f2ca1c982950ac5af660f9c6cd52e08c135f546bc659fa2851aa1c0b6db0
```

`false_positives_snap` (580) and `zero_trade_snap` (553) are large and mostly pre-existing (see Q4); representative samples of each are below rather than full lists, all reproducible from the read-only script described in Q4.

## Q4 — Per-direction attribution, with row-level evidence

### The 195 "leaked" markets (T2f) — attribution: CATEGORY BACKFILL, mechanism confirmed in code

These are markets currently `category IN ('Geopolitics','Elections')`, `resolved=1`, `resolution_date >= 2025-11-01`, gap-clean, and `tape_end >= 2025-11-01` — i.e. they satisfy `backtest_window_sql()` today — yet are absent from a snapshot generated by running that exact query on 2026-07-24.

`scripts/backfill_market_categories.py` line 107/200:
```python
WHERE category = 'Unknown'
...
"UPDATE markets SET category = ? WHERE market_id = ?"
```
This is `daily_maintenance.py` step 15 ("Backfill market categories"), which runs **every day**. Today's run alone: `classified=11572 skipped=7452 errors=0` (`logs/category_backfill.log`, 08:01:34–08:02:59). `markets.category` is currently `'Unknown'` for 709,398 of 722,908 rows (98%) — this backfill is a large, still-early-stage, continuously running process.

Mechanism: a market with `category='Unknown'` at freeze time (2026-07-24) is invisible to `backtest_window_sql()` at freeze time regardless of its `resolved`/`resolution_date`/`tape_end` state, so it cannot appear in the snapshot. If the market already had `resolved=1`, a qualifying `resolution_date`, and pre-existing trades with `tape_end >= 2025-11-01` — which is common, since `data_source` for these 195 is a mix of `live_monitoring` (97), `background_backfill` (40), `historical_backfill` (23), `gamma_backfill_2026-07-02` (16), `gamma_backfill_tier2_2026-07-06` (19) — then the day this daily category-backfill step reclassifies it out of `'Unknown'`, it starts satisfying `old` **and** the canonical predicate simultaneously, but the snapshot can never retroactively include it (append-only, by design). This is a permanent, structural, ever-growing gap between "live canonical population" and "frozen snapshot" — expected and by design (T1b explicitly tests for this: live count ≥ snapshot count, monotonic growth). **The bug is that T2f's own partition (`agree + zero_trade + false_positives == old`) never accounted for this third bucket**, so it was mathematically guaranteed to fail as soon as even one such market existed. This is a test-completeness defect, not itself "drift."

### T2 / T2b (agree 4658→4660, false_negatives 54→52) — attribution: silent `resolution_date` fill on already-frozen population

For a market already inside the snapshot (i.e. `category`/`resolved`/gap-clean/`tape_end` all already satisfied `backtest_window_sql()` at freeze time — confirmed, since that's how it got into the snapshot), the **only** variable in `old`'s WHERE clause that can differ is `resolution_date >= window_start`. `category`, `resolved`, and gap-clean are identical clauses in both `old` and `backtest_window_sql()`, so a snapshot member cannot flip on those without a double-flip (out then back), which is not supported by any write path found. So a snapshot member moving `false_negatives_snap → agree_snap` requires its `resolution_date` to go from `NULL`/`< 2025-11-01` to `>= 2025-11-01` after 2026-07-24T18:54:00Z.

Grep of every `UPDATE markets ... resolution_date` write path in the codebase:
```
scripts/backfill_market_dates.py:229      resolution_date = COALESCE(resolution_date, ?)   -- no last_checked write
scripts/hydrate_stub_markets.py:201       resolution_date = COALESCE(resolution_date, ?)   -- no last_checked write
scripts/backfill_o16_tier1.py / tier2.py  resolution_date = COALESCE(resolution_date, ?)
scripts/fast_resolution_check.py:265/385/495/592   mixed: some unconditional (only fire on resolved=0 markets), some COALESCE
monitoring/database.py:527                resolution_date = COALESCE(resolution_date, excluded.resolution_date, excluded.end_date)
monitoring/monitor.py:221/276             resolution_date = COALESCE(resolution_date, ?)
```
Every path capable of touching an *already-resolved* market (as all snapshot members are) is `COALESCE`-based — fires once, only if `resolution_date` is currently `NULL`, and **none of `backfill_market_dates.py` or `hydrate_stub_markets.py`'s `UPDATE` statements touch `last_checked`** (verified by reading both statements in full). This is corroborated directly: a scan of every market in `agree_snap` (4,660), `false_positives_snap` (580), and `zero_trade_snap` (553) for `last_checked > 2026-07-24 18:54:00` (the freeze instant) returns **zero rows in all three sets**. Every visible resolution_date value in the current agree/FN/zero-trade/false-positive buckets was written at or before the freeze — consistent with the actual flips having happened through a write path that doesn't stamp any audit column at all.

**Gap disclosed:** I can name the *exclusive mechanism class* (a silent, COALESCE-guarded `resolution_date` fill from a NULL value, on a market whose `category`/`resolved`/`gap_flag` were already snapshot-qualifying) with certainty — the snapshot's immutability plus the predicate's stability plus the write-path audit rules out every other explanation. I cannot name the exact 2 `market_id`s: the current 52 `false_negatives_snap` members all have non-NULL `resolution_date` today (0 have `NULL`), so the 2 that already flipped out are indistinguishable, post-hoc, from the 4,660 members that were always in `agree`. **This is not recoverable read-only** because the responsible write paths do not record which rows they touched or when (no co-written timestamp, no changelog table for `markets.resolution_date`). This is the one sub-item of Q4 I could not fully settle to row-ID level; the mechanism itself is settled.

### T2c / T2d (zero_trade 555→553, false_positives 573→580)

`false_positives_snap` (580) is **dominated by already-known, already-documented contamination**, not new drift: a sample of the lowest-trade-count members shows `last_checked` values of exactly `2026-04-01 16:19:1X` and `2026-06-04 21:36:39` — these are precisely the two bulk-backfill contamination events named in the test file's own docstring (single-trade markets like "Finnish Presidential Election: Will Jutta Urpilainen win?", "Will Sweden join NATO by January 31?", genuinely 2023/2024 events wrongly resolution_date-stamped as 2026). These predate the freeze by months and are not part of the drift.

Zero `false_positives_snap` or `zero_trade_snap` members show `last_checked` after the freeze (same check as above) — same silent-write blind spot as T2/T2b. `backfill_transaction_hashes.py` (today's longest step, 6,153s) was checked and confirmed to only `UPDATE trades SET transaction_hash=...` on existing rows — it cannot create the "market gains its first trade" event that would move a market from `zero_trade` to `false_positive`. The specific script responsible for inserting a previously-untraded market's first (historically-dated) trade row was not identified with certainty within this investigation's time budget — **this is the second disclosed gap**: the net ±2/+7 reshuffle in T2c/T2d is real (live-side movement, not snapshot mutation, per the same immutability/predicate proof as above) but its exact trade-insertion write path is not pinned down.

## Q5 — Is the predicate stable

**Yes — confirmed stable since introduction.**

```
git log --oneline -- monitoring/column_definitions.py
cfbc1cd feat: backtest population snapshots (O-45 follow-up) — pin the population B5/B3 must consume
8470e8b feat: canonical backtest-window population (tape_end, not resolution_date) — B5 repointed
... (5 earlier commits, none touching backtest_window_sql)
```

`git log -p` filtered to `BACKTEST_WINDOW_BASE_WHERE` / `BACKTEST_WINDOW_TAPE_END_CTE` / `BACKTEST_WINDOW_SQL_VERSION` shows these three symbols appear in exactly two commits: `8470e8b` (introduced them) and `cfbc1cd` (added the version-bump-obligation *comments*, no value change). `BACKTEST_WINDOW_SQL_VERSION` is still `"1"` — never bumped. No commit since `cfbc1cd` (2026-07-24) touches `monitoring/column_definitions.py` at all. The predicate the snapshot was frozen under and the predicate the live query runs today are **identical**. This rules out PREDICATE DRIFT.

## Q6 — When did it start

`daily_maintenance.py`'s "Run test suite" step, reconstructed from every occurrence in `logs/daily_maintenance.log` (which spans 2026-05-31 to today, uninterrupted as a single file):

| Date | Result | Runtime |
|---|---|---|
| 2026-06-30 → 2026-07-23 (22 consecutive daily runs) | **PASS — ALL TESTS PASSED** | 1.2s → 4.4s |
| **2026-07-24T06:00:01Z** | **WARNING — FAILURES DETECTED** | **117.3s** ← |
| *(no maintenance ran 2026-07-25 → 2026-08-07 — 15-day gap, separate finding, flagged below)* | | |
| 2026-08-08 → 2026-08-17 (10 consecutive daily runs, today included) | WARNING — FAILURES DETECTED, every run | 127–162s |

The runtime jump from ~4.4s to 117.3s, occurring exactly on 2026-07-24, is consistent with this being the first execution of the new DB-backed §1/§2 tests (real queries against `markets`/`trades`/the new snapshot table) rather than the earlier lightweight version of the file. **The test suite has never been observed green since this heavier test file went live** — every run from 2026-07-24 onward failed, with no passing run in between.

**Caveat, disclosed:** `tests/LATEST_TEST_RESULTS.md` is gitignored and overwritten every run, and `daily_maintenance.log` only records the step-level PASS/FAIL summary, not which of the 24 individual assertions failed, for any run before today. So I can prove the *file-level* step has been continuously red since 2026-07-24 with certainty, but I cannot prove from the log alone that T2/T2b/T2c/T2d/T2f specifically (as opposed to some other section of the same file) were the failing assertions on every one of those runs. What I can independently prove: T2f is a structural partition bug that would fail on day one given even a single leaked market, and external_seed/category-Unknown markets with qualifying trade history plausibly existed well before 2026-07-24 (the category backfill and `external_seed` discovery source both predate the freeze per code comments referencing 2026-06-08). Combined with the observed runtime/failure coincidence on 2026-07-24 itself, the most defensible reading is: **T2f has likely never passed since introduction** (NEVER GREEN in effect for that one assertion), while **T2/T2b/T2c/T2d are genuine post-freeze drift** that only started diverging from the hardcoded constants (measured 07-24 19:03) at some unknown point(s) between 2026-07-24 and today — most likely concentrated in the unexamined 2026-07-25→08-07 gap or the following daily runs, but not narrowed further without the missing per-run detail.

## Separate finding, out of scope but worth flagging

`daily_maintenance.py` did not run at all between **2026-07-24T08:23:39Z and 2026-08-08T06:00:01Z** (~15 days) — visible directly in `logs/daily_maintenance.log` as a gap between two `Starting daily-maintenance` markers with no explanatory content in between. This is the same window during which the snapshot was frozen (18:54 on 07-24, after that day's run had already finished) and during which the drift under investigation here had its first (and largest, uninstrumented) opportunity to accumulate. Recommend checking systemd/cron history for that window separately; not investigated further here per the read-only/characterisation-only scope of this task.

## Reproducibility

All counts and enumerations above were produced by three short read-only Python scripts (`sqlite3.connect(..., mode=ro)`) that reuse `old_method_market_ids()` / `snapshot_market_ids()` / `tape_end_map()` verbatim from `tests/test_backtest_window_population.py`, plus direct reads of `monitoring/column_definitions.py`, `git log`, and `logs/daily_maintenance.log`. Scripts were run from the scratchpad directory and not committed (this investigation made no changes to the repository other than this document).
