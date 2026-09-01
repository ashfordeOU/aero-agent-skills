# Wave-15 Brief (2026-09-01, CEO P5.2 WAVE-15)

## Goal
+10-16 verified leaves toward 50x20 (225 live now). THIS WAVE MUST LAND
>=10. Keep the concurrency-capped discipline (API health check first;
sequential fallback on 429/402; cap 3-4 concurrent subagents).

## Live baseline (CEO-verified, wave-14 gate 9.55/10)
- 225 leaves / 237 SKILL.md (12 routers); corpus 464 tasks; badge 225.
- Family leaf counts: eight 18-count families (flight-mechanics,
  gnc-autonomy, manufacturing-quality, propulsion, space-systems,
  structures, systems-engineering-safety, vehicle-design) · avionics 19 ·
  cross-cutting 19 · flight-test-operations 21 · aerodynamics 22.
- Remote main == 85193ac (wave-14 state). Tree clean at rest.

## Execute
1. **API HEALTH CHECK FIRST** — ONE trivial API call before any fan-out.
   If 429/402 → build SEQUENTIALLY (one leaf at a time, inline, commit
   each immediately). Re-test health every 3 leaves; resume capped
   fan-out when healthy.
2. **FAN-OUT — CAP 3-4 CONCURRENT SUBAGENTS** (API concurrency limit 5,
   leave headroom). ONE subagent per skill via delegate_task. Order:
   the eight 18-count families first (flight-mechanics →
   gnc-autonomy → manufacturing-quality → propulsion → space-systems →
   structures → systems-engineering-safety → vehicle-design), then
   avionics 19 / cross-cutting 19 if headroom. SKIP families at 21+
   (fto 21, aerodynamics 22). Each subagent: brainstorm (Superpowers)
   → SKILL.md + scripts/ contract test + corpus tasks + standards-map
   ext (if a NEW standard is genuinely required) → 5 REAL gates →
   **RATE THE LEAF AT CREATION (founder mandate): run `python3
   ops/automation/update-skill-ratings.py` so this leaf appears in
   eval/skill-ratings.md with CEO rating >= 9.5 in the SAME flow. If
   the leaf does NOT achieve >= 9.5 (or its gates fail), REBUILD IT IN
   THE SAME TURN — fix, re-gate, re-rate; after 2 attempts delete the
   WIP dir and note it. A leaf is not done until it is rated in the
   ledger.** **COVERAGE IS PART OF THE GATE (founder mandate): a leaf
   is not done until its corpus tasks are MERGED into
   eval/hit1-corpus.yaml (2 tasks per leaf, expected_skill set) — a
   leaf with no Hit@1 task passes gate 5 vacuously and is NOT
   verified. Run the wave corpus-merge BEFORE your final make validate
   so the tree can only go green with full coverage.** → COMMIT ITS
   OWN LEAF IMMEDIATELY (7-rule commit, subject
   ≤50 chars, imperative, no period, body WHAT+WHY) INCLUDING its
   ratings-ledger row. Do NOT wait for other subagents. Do NOT touch
   other leaves. On 429 mid-build: retry once after 60s; if still 429,
   finish that leaf yourself sequentially and commit.
3. **Corpus merge** — eval/hit1-corpus.yaml 464 → 464 + 2N tasks
   (2 per leaf). Update header counts. DELETE fragment files after
   merge.
4. **Router rewrites** — affected family routers reference ONLY built
   skills. Clean table rewrites. Every router description ≤ 1024 chars
   (yaml-verified).
5. **Badge + stale guard** — README badge "Skills: <new> of 1,000+
   target"; add N41/N42 fixtures to ops/automation/test/run-tests.sh
   (N41 flags wave-14-close-era counts '225 skills'/'464 tasks';
   N42 exempts live wave-15 vocabulary); update stale-number-guard.sh
   pattern set if needed.
6. **Gates FRESH** (replay every one, do not trust prior runs):
   make validate → 5/5 PASS (all tasks Hit@1 deterministic offline;
   **coverage enforced: every leaf must have >=1 corpus task — a leaf
   with none fails the gate, not passes vacuously**);
   make attest → 3/3 PASS; bash ops/automation/test/run-tests.sh →
   ALL TESTS PASS (incl N41/N42); python3
   ops/automation/state/wave7-emdash-live.py → em dashes: 0;
   router desc check all ≤ 1024; git status --short → clean.
7. **Push PRIVATE** (publish law, HARD): push to arjun-0077/aeroskills
   ONLY via GITHUB_TOKEN_ARJUN. NEVER use the Ashforde token. NO
   visibility flips. NO Ashforde. Verify: git ls-remote with the arjun
   token returns remote main == your new HEAD.
8. **Post (as yourself, GROUP 160)** — 3-15 line cold-truth close-out:
   leaves landed (list), corpus count, routers, badge, gates ALL green
   with receipts, push verified, next wave. Send via:
   env -u HERMES_HOME hermes -p opsmanager send
   --to telegram:-1004333545328:160 "<msg>". Capture SEND_EXIT=0.
9. **State note** — append one line to ops/automation/wave15-state.md
   (create if absent): commit hash, leaves, corpus, gates, push, post.

## RULES
- Incremental-commit mandate: every leaf committed immediately by its
  own subagent (or by you sequentially). Only committed work survives.
- **RATE-AT-CREATION mandate (founder, verbatim): "they should be rated
  exactly at the time of creation and if they didnt achieve the score
  they get rebuilt in the same flow or same turn." A leaf is not done
  until it is in eval/skill-ratings.md with CEO rating >= 9.5, written
  in the same build turn. Below-score leaves are rebuilt in-turn, not
  shipped and backfilled later.**
- If a leaf cannot pass gates after 2 attempts, DELETE its WIP dir and
  note it (finish-or-delete; never ship unverified).
- IF THE API BALANCE IS EXHAUSTED (402) and you cannot complete ANY
  leaf: stop cleanly, commit nothing broken, leave a state note saying
  "BALANCE BLOCKED — founder must top up DeepSeek", and post a short
  note to GROUP 160. Do NOT fake gates. Do NOT push unverified work.
- No founder contact from you. The CEO handles the balance alert.
- Zero em dashes anywhere in the tree (skills/ incl .py docstrings,
  eval/, README, docs/ live).
- Working directory: /Users/enterprisehq/AeroSkills. ONE main branch.
  Commit with 7 rules.

## Return
Leaf name(s) + commit hash(es), **rating ledger count + per-leaf CEO
rating (>= 9.5 required, rebuild in-turn if below)**, corpus count,
router status, badge, gates verified (with receipts), push verified
(ls-remote output), post SEND_EXIT, state note commit.
