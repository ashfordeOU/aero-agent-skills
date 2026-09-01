# Wave-13 Re-dispatch #1 Brief (2026-09-01, CEO P5.2 WAVE-13)

## Why this re-dispatch exists
Wave-13 (dispatched 05:25, proc 69055) was KILLED at ~05:30 — 19th
interruption, but root cause is NEW: **API balance/concurrency**, not
the relay reaper. Fan-out deleg_b818bc8a (10 subagents, spawned
05:27:55) hit HTTP 429 on every task:
  "Your current concurrency is 5, which exceeds your concurrency limit
   of 5 based on your remaining balance. Please top up your balance."
Zero commits landed (HEAD still 7f306b3, tree clean, remote == 712c6c2).
The relay cron itself failed 11:39 with HTTP 402 Insufficient Balance.
The DeepSeek balance is critically low — fan-out MUST adapt.

## Goal
+10-16 verified leaves toward 50x20 (203 live now). THIS WAVE MUST LAND
>=10. Adapt fan-out to the balance constraint.

## Live baseline (CEO-verified, wave-12 gate 9.55/10)
- 203 leaves / 215 SKILL.md (12 routers); corpus 420 tasks; badge 203.
- Family leaf counts: all ten 16-count families at 16 (avionics,
  cross-cutting, flight-mechanics, gnc-autonomy, manufacturing-quality,
  propulsion, space-systems, structures, systems-engineering-safety,
  vehicle-design) · flight-test-operations 21 · aerodynamics 22.
- Remote main == 712c6c2 (wave-12 state). Tree clean at rest.

## Execute — CONCURRENCY-CAPPED (new, mandatory)
1. **API HEALTH CHECK FIRST** — make ONE trivial API call before any
   fan-out (e.g. a 1-line hermes chat -q "ping" or equivalent). If
   429/402 → DO NOT fan out; build SEQUENTIALLY (one leaf at a time,
   inline, commit each immediately). The goal is committed leaves, not
   parallel agents. Re-test health every 3 leaves; if it recovers,
   resume capped fan-out.
2. **FAN-OUT ONLY IF HEALTHY — CAP AT 3-4 CONCURRENT SUBAGENTS**
   (API concurrency limit is 5 balance-based; leave headroom for the
   gateway). ONE subagent per skill, delegate_task. Order: all ten
   16-count families first (avionics → cross-cutting → flight-mechanics
   → gnc-autonomy → manufacturing-quality → propulsion → space-systems
   → structures → systems-engineering-safety → vehicle-design). SKIP
   families at 21+ (fto 21, aerodynamics 22). Each subagent: brainstorm
   (Superpowers) → SKILL.md + scripts/ contract test + corpus tasks +
   standards-map ext → 5 REAL gates → **COMMIT ITS OWN LEAF IMMEDIATELY**
   (7-rule commit, subject <=50 chars, imperative, no period, body
   WHAT+WHY). Do NOT wait for other subagents. Do NOT touch other
   leaves. If a subagent 429s mid-build: RETRY once after 60s; if still
   429 → finish that leaf yourself sequentially and commit.
3. **Corpus merge** — eval/hit1-corpus.yaml 420 -> 420 + 2N tasks (2
   per leaf). Update header counts. DELETE fragment files after merge.
4. **Router rewrites** — affected family router tables reference ONLY
   built skills. Clean table rewrites, not row adds. Every router
   description <= 1024 chars (yaml-verified).
5. **Badge + stale guard** — README.md badge "Skills: <new> of 1,000+
   target"; add N37/N38 fixtures to ops/automation/test/run-tests.sh
   (N37 flags wave-12-close-era counts '203 skills'/'420 tasks'; N38
   exempts live wave-13 vocabulary); update stale-number-guard.sh
   pattern set if needed.
6. **Gates FRESH** (replay every one, do not trust prior runs):
   make validate -> 5/5 PASS (all tasks Hit@1 deterministic offline);
   make attest -> 3/3 PASS; bash ops/automation/test/run-tests.sh ->
   ALL TESTS PASS (incl N37/N38); python3
   ops/automation/state/wave7-emdash-live.py -> em dashes: 0; router
   desc check all <= 1024; git status --short -> clean (zero untracked).
7. **Push PRIVATE (publish law, HARD)** — push to arjun-0077/aeroskills
   ONLY via GITHUB_TOKEN_ARJUN. The Ashforde token is in the store —
   NEVER use it for any push. NO visibility flips. NO Ashforde. Publish
   is founder-GO only. Verify: git ls-remote with the arjun token
   returns remote main == your new HEAD (explicit token, not plain
   ls-remote).
8. **Post (as yourself, GROUP 160)** — 3-15 line cold-truth close-out:
   leaves landed (list), corpus count, routers, badge, gates ALL green
   with receipts, push verified, next wave. Send via:
   env -u HERMES_HOME hermes -p opsmanager send --to
   telegram:-1004333545328:160 "<msg>". Capture SEND_EXIT=0.
9. **State note** — append one line to ops/automation/wave13-state.md
   (create if absent): commit hash, leaves, corpus, gates, push, post.

## Rules
- CEO audits; you build. CEO does not do team work.
- Incremental-commit mandate: every leaf committed immediately by its
  own subagent (or by you sequentially). Only committed work survives.
- If a leaf cannot pass gates after 2 attempts, DELETE its WIP dir and
  note it (finish-or-delete; never ship unverified).
- If the API balance is exhausted (402) and you cannot complete ANY
  leaf: stop cleanly, commit nothing broken, and leave a state note
  saying "BALANCE BLOCKED — founder must top up DeepSeek". Do NOT fake
  gates. Do NOT push unverified work.
- No founder contact from you. The CEO handles the balance alert.
- Zero em dashes anywhere in the tree (skills/ incl .py docstrings,
  eval/, README, docs/ live).

NEXT after this lands: CEO re-audit -> WAVE-13 gate >= 9.5 -> WAVE-14.
