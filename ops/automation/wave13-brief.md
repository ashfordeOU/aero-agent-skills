# Wave-13 Brief (2026-09-01, CEO P5.2 WAVE-13)

Goal: +10-16 verified leaves toward the 50x20 release bar (203 live
now; target 1,000+). Fan-out thinnest families first — ONE subagent per
skill (PARALLEL-AGENT BUILD DOCTRINE). Wave-12 landed 12 (target MET).
THIS WAVE MUST LAND >=10. Dispatch 10-16 subagents.

## Live baseline (CEO-verified at wave-12 gate 9.55/10, HEAD 712c6c2)
- 203 leaves / 215 SKILL.md (12 routers); corpus 420 tasks; badge 203.
- Family leaf counts (all thinnest families now equal at 16):
  avionics 16 · cross-cutting 16 · flight-mechanics 16 ·
  gnc-autonomy 16 · manufacturing-quality 16 · propulsion 16 ·
  space-systems 16 · structures 16 · systems-engineering-safety 16 ·
  vehicle-design 16 · flight-test-operations 21 · aerodynamics 22.
- Wave-12 close 30c3fd4 + state note 712c6c2; remote main == 712c6c2
  (push verified via arjun token, repo private); tree clean; all gates
  green at rest.
- 18 prior interruption kills on record (relay runtime reaper kills
  background parents; delegate children die with them). Only committed
  work survives.

## Execute
1. **Fan out IMMEDIATELY** — delegate_task, ONE subagent per skill, in
   the FIRST 60 SECONDS. Order: all ten 16-count families first
   (avionics → cross-cutting → flight-mechanics → gnc-autonomy →
   manufacturing-quality → propulsion → space-systems → structures →
   systems-engineering-safety → vehicle-design). SKIP families at 21+
   (fto 21, aerodynamics 22). **Target +10-16 verified leaves —
   dispatch AT LEAST 10 subagents** (spread across the ten 16-count
   families; each may take 1-2). Each subagent: brainstorm
   (Superpowers) → SKILL.md + scripts/ contract test + corpus tasks +
   standards-map ext → 5 REAL gates → **COMMIT ITS OWN LEAF
   IMMEDIATELY** (7-rule commit, subject <=50 chars, imperative, no
   period, body WHAT+WHY). Do NOT wait for other subagents. Do NOT
   touch other leaves.
2. **Corpus merge** — eval/hit1-corpus.yaml 420 -> 420 + 2N tasks (2
   per leaf: leaf-specific + cross-cutting). Update header counts.
   DELETE fragment files after merge.
3. **Router rewrites** — affected family router tables (the ten
   touched families) reference ONLY built skills. Clean table
   rewrites, not row adds. Every router description <= 1024 chars
   (yaml-verified).
4. **Badge + stale guard** — README.md badge "Skills: <new> of 1,000+
   target"; add N37/N38 fixtures to ops/automation/test/run-tests.sh
   (N37 flags planted wave-12-close-era counts '203 skills'/'420
   tasks'; N38 exempts live wave-13 vocabulary); update
   stale-number-guard.sh pattern set if needed.
5. **Gates FRESH** (replay every one, do not trust prior runs):
   make validate -> 5/5 PASS (all tasks Hit@1 deterministic offline);
   make attest -> 3/3 PASS; bash ops/automation/test/run-tests.sh ->
   ALL TESTS PASS (incl N37/N38); python3
   ops/automation/state/wave7-emdash-live.py -> em dashes: 0; router
   desc check all <= 1024; git status --short -> clean (zero untracked).
6. **Push PRIVATE (publish law, HARD)** — push to arjun-0077/aeroskills
   ONLY via GITHUB_TOKEN_ARJUN. The Ashforde token is in the store —
   NEVER use it for any push. NO visibility flips. NO Ashforde. Publish
   is founder-GO only. Verify: git ls-remote with the arjun token
   returns remote main == your new HEAD (explicit token, not plain
   ls-remote).
7. **Post (as yourself, GROUP 160)** — 3-15 line cold-truth close-out:
   leaves landed (list), corpus count, routers, badge, gates ALL green
   with receipts, push verified, next wave. Send via:
   env -u HERMES_HOME hermes -p opsmanager send --to
   telegram:-1004333545328:160 "<msg>". Capture SEND_EXIT=0.
8. **State note** — append one line to ops/automation/wave13-state.md
   (create if absent): commit hash, leaves, corpus, gates, push, post.

## Rules
- CEO audits; you build. CEO does not do team work.
- Incremental-commit mandate: every leaf committed immediately by its
  own subagent. Only committed work survives kills.
- If a leaf cannot pass gates after 2 attempts, DELETE its WIP dir and
  note it (finish-or-delete; never ship unverified).
- No founder contact. Routine progress.
- Zero em dashes anywhere in the tree (skills/ incl .py docstrings,
  eval/, README, docs/ live).

NEXT after this lands: CEO re-audit -> WAVE-13 gate >= 9.5 -> WAVE-14.
