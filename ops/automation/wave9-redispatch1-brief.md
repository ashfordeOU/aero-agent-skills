# Wave-9 RE-DISPATCH #1 — 16th interruption (relay runtime kill), nothing on disk

Context: Wave-9 parent proc (own profile, background, dispatched
~02:16) DIED at 02:22:03 — all opsmanager sessions show "Operation
interrupted" simultaneously (relay runtime kill pattern, identical to
the 15 prior kills). The parent had spawned delegation deleg_f3611a69
(5 tasks: systems-engineering-safety · flight-mechanics ·
manufacturing-quality · cross-cutting · vehicle-design — ALL
INTERRUPTED mid-research at 02:21:58-02:22:03 BEFORE writing; zero
disk presence). ZERO wave-9 commits landed. HEAD 0632f39 (wave-9 brief
commit); origin/main 279e58f (wave-8 end state — push deferred per
CI-first, correct). Tree CLEAN (0 untracked) — no WIP at risk, nothing
to rescue.

LESSON (16th interruption, relay-runtime class — SAME as the prior 15):
a background parent proc gets ~8-10 min of life per re-dispatch before
the relay's process reaper kills it, and its delegate children die WITH
it. Surviving work = what was COMMITTED before the reap. Therefore:
(a) FAN OUT FIRST — spawn the leaf subagents in the first 60 seconds.
(b) SUBAGENTS COMMIT THEIR OWN LEAF the moment its gates pass (git
access in their session; do NOT wait for the parent to commit).
(c) Parent stays LEAN; abort completions stalled >10 min.

## Execute the wave-9 plan exactly (brief: ops/automation/wave9-brief.md)

The full plan is already committed and unchanged. Run it end to end:

1. **Fan out IMMEDIATELY** — delegate_task, ONE subagent per skill, in
   the FIRST 60 SECONDS. Order: systems-engineering-safety (10) →
   flight-mechanics (10) → manufacturing-quality (11) → cross-cutting
   (11) → vehicle-design (11). SKIP families at 12+. Target +10-16
   verified leaves. Each subagent: brainstorm (Superpowers) → SKILL.md
   + scripts/ contract test + corpus tasks + standards-map ext → 5 REAL
   gates (make validate on its leaf tasks, spec-lint, desc-lint,
   contract test, Hit@1) → **COMMIT ITS OWN LEAF IMMEDIATELY**
   (7-rule commit, subject <=50 chars, imperative, no period, body
   WHAT+WHY). Do NOT wait for other subagents. Do NOT touch other
   leaves.
2. **Corpus merge** — eval/hit1-corpus.yaml 308 -> 308 + 2N tasks (2
   per leaf: leaf-specific + cross-cutting). Update header counts.
   DELETE fragment files after merge.
3. **Router rewrites** — affected family router tables
   (ses/flight-mechanics/manufacturing-quality/cross-cutting/
   vehicle-design) reference ONLY built skills. Clean table rewrites,
   not row adds. Every router description <= 1024 chars (yaml-verified).
4. **Badge + stale guard** — README.md badge "Skills: <new> of 1,000+
   target"; add N29/N30 fixtures to ops/automation/test/run-tests.sh
   (N29 flags planted wave-8-close-era counts '147 skills'/'308 tasks';
   N30 exempts live wave-9 vocabulary); update stale-number-guard.sh
   pattern set if needed.
5. **Gates FRESH** (replay every one, do not trust prior runs):
   make validate -> 5/5 PASS (all tasks Hit@1 deterministic offline);
   make attest -> 3/3 PASS; bash ops/automation/test/run-tests.sh ->
   ALL TESTS PASS (incl N29/N30); python3
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
8. **State note** — append one line to ops/automation/wave9-state.md
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

NEXT after this lands: CEO re-audit -> WAVE-9 gate >= 9.5 -> WAVE-10.
