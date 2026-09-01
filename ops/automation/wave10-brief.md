# Wave-10 Brief (2026-09-01, CEO P5.2 WAVE-10)

Goal: +10-16 verified leaves toward the 50x20 release bar (162 live
now; target 1,000+). Fan-out thinnest families first — ONE subagent per
skill (PARALLEL-AGENT BUILD DOCTRINE).

## Live baseline (CEO-verified at wave-9 gate 9.55/10, HEAD 4e1a469)
- 162 leaves / 174 SKILL.md (12 routers); corpus 338 tasks; badge 162.
- Family leaf counts: aerodynamics 12 · flight-test-operations 12 ·
  propulsion 12 · flight-mechanics 13 · space-systems 13 ·
  systems-engineering-safety 13 · cross-cutting 14 · gnc-autonomy 14 ·
  manufacturing-quality 14 · vehicle-design 14 · structures 15 ·
  avionics 16.
- Wave-9 close e7e0c95 + state note 4e1a469; remote main == 4e1a469
  (push verified via arjun token); tree clean; all gates green at rest.
- 17 prior interruption kills on record (relay runtime reaper kills
  background parents ~8-10 min in; delegate children die with them).

## Execute
1. **Fan out IMMEDIATELY** — delegate_task, ONE subagent per skill, in
   the FIRST 60 SECONDS. Order: aerodynamics (12) → flight-test-
   operations (12) → propulsion (12) → flight-mechanics (13) →
   space-systems (13) → systems-engineering-safety (13). SKIP families
   at 14+. Target +10-16 verified leaves. Each subagent: brainstorm
   (Superpowers) → SKILL.md + scripts/ contract test + corpus tasks +
   standards-map ext → 5 REAL gates → **COMMIT ITS OWN LEAF
   IMMEDIATELY** (7-rule commit, subject <=50 chars, imperative, no
   period, body WHAT+WHY). Do NOT wait for other subagents. Do NOT
   touch other leaves.
2. **Corpus merge** — eval/hit1-corpus.yaml 338 -> 338 + 2N tasks (2
   per leaf: leaf-specific + cross-cutting). Update header counts.
   DELETE fragment files after merge.
3. **Router rewrites** — affected family router tables
   (aerodynamics/fto/propulsion/flight-mechanics/space-systems/ses)
   reference ONLY built skills. Clean table rewrites, not row adds.
   Every router description <= 1024 chars (yaml-verified).
4. **Badge + stale guard** — README.md badge "Skills: <new> of 1,000+
   target"; add N31/N32 fixtures to ops/automation/test/run-tests.sh
   (N31 flags planted wave-9-close-era counts '162 skills'/'338 tasks';
   N32 exempts live wave-10 vocabulary); update stale-number-guard.sh
   pattern set if needed.
5. **Gates FRESH** (replay every one, do not trust prior runs):
   make validate -> 5/5 PASS (all tasks Hit@1 deterministic offline);
   make attest -> 3/3 PASS; bash ops/automation/test/run-tests.sh ->
   ALL TESTS PASS (incl N31/N32); python3
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
   Message_id may not persist in CLI human mode — record the send
   honestly (exit 0 + "sent").
8. **State note** — append one line to ops/automation/wave10-state.md
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

NEXT after this lands: CEO re-audit -> WAVE-10 gate >= 9.5 -> WAVE-11.
