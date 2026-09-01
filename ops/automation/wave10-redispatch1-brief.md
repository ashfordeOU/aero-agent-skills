# Wave-10 RE-DISPATCH #1 — 18th interruption (relay runtime kill), WIP RECOVERABLE

Context: Wave-10 parent proc (own profile, background, started 02:52,
pid 94053) DIED ~03:03 — delegation live dirs show ALL THREE fan-out
batches torn down simultaneously (deleg_fd18fff2 10 tasks 9/10
interrupted, deleg_37f13368 10/10 interrupted, deleg_83339766 10/10
interrupted at 03:03:30; relay runtime kill pattern, identical to the
17 prior kills). state.db-wal last write 03:03. HEAD a5d154f — 2 leaves
COMMITTED by subagents before the reap: 65082a2 swept-wing-
aerodynamics + a5d154f glide-flight-test. origin/main 4e1a469 (wave-9
end state — push deferred per CI-first, correct).

## Recoverable WIP (CEO-verified 03:10, DO NOT rebuild from scratch)
COMPLETE untracked leaves (SKILL.md + logic + test all present):
1. skills/aerodynamics/boundary-layer/boundary-layer-theory
2. skills/aerodynamics/ground-effects/ground-effect
3. skills/aerodynamics/high-speed/transonic-similarity
4. skills/flight-test-operations/envelope/stall-characteristics-testing
5. skills/flight-test-operations/performance/takeoff-distance-determination

PARTIAL untracked leaves (finish-or-delete):
6. skills/aerodynamics/high-lift/high-lift-systems — logic+test, NO SKILL.md
7. skills/flight-test-operations/envelope/flight-loads-survey — logic+SKILL.md, NO test
8. skills/flight-test-operations/stability/dynamic-stability-flight-test — logic only
9. skills/propulsion/turboprop/free-turbine — logic only

Eval fragments (7): eval/hit1-wave10-{boundary-layer-theory, glide-flight-test,
ground-effect, stall-characteristics-testing, swept-wing-aerodynamics,
takeoff-distance-determination, transonic-similarity}.yaml — unmerged.
Helper: ops/automation/state/wave10-leafcount.py (bot prep — expected, keep).

Interrupted with ZERO disk presence (need full rebuild): wave-drag-area-rule ·
vortex-lattice-method · panel-method · airfoil-optimization · supercritical-airfoil ·
engine-flight-test · flight-test-safety · telemetry-data-acquisition ·
test-point-matrix-design · turbine-stage · combustor-design · intake-design ·
exhaust-mixer · turboprop-engine · ramjet-scramjet · liquid-rocket-engine ·
solid-rocket-motor · electric-propulsion · engine-cycle-matching ·
secondary-power-systems · energy-height · acceleration-performance ·
ceiling-performance · engine-out-performance.

LESSON (18th interruption, relay-runtime class — SAME as the prior 17):
a background parent proc gets ~8-10 min of life per re-dispatch before
the relay's process reaper kills it, and its delegate children die WITH
it. Surviving work = what was COMMITTED before the reap. Therefore:
(a) FAN OUT FIRST — spawn the leaf subagents in the first 60 seconds.
(b) SUBAGENTS COMMIT THEIR OWN LEAF the moment its gates pass (git
access in their session; do NOT wait for the parent to commit).
(c) Parent stays LEAN; abort completions stalled >10 min.

## Execute (rescue-first, then continue the wave-10 plan)

0. **RESCUE FIRST (STEP 0)** — commit the 5 COMPLETE untracked leaves
   EACH as its own 7-rule commit after 5 REAL gates (spec-lint,
   desc-lint, contract test, make validate on its leaf tasks, Hit@1).
   Do NOT batch. Do NOT rebuild — the files exist; verify + commit.
1. **Finish-or-delete the 4 PARTIAL dirs** — high-lift-systems: add
   SKILL.md (logic+test exist); flight-loads-survey: add contract test;
   dynamic-stability-flight-test + free-turbine: add SKILL.md + test.
   NEVER ship a leaf without a green contract test. If a leaf cannot
   pass gates after 2 attempts, DELETE its WIP dir and note it.
2. **Continue fan-out to hit wave target** — delegate_task ONE subagent
   per skill, FIRST 60 SECONDS, thinnest families first:
   aerodynamics (12) → flight-test-operations (12) → propulsion (12) →
   flight-mechanics (13) → space-systems (13) → systems-engineering-
   safety (13). SKIP 14+ families. Target +10-16 VERIFIED leaves THIS
   WAVE (rescue counts: 2 committed + 5 rescue = 7 → need >=3 more to
   clear 10; aim 12-16). SUBAGENTS COMMIT THEIR OWN LEAF IMMEDIATELY.
3. **Corpus merge** — eval/hit1-corpus.yaml 338 -> 338 + 2N tasks (2
   per leaf). Update header counts. DELETE all wave-10 fragments after
   merge (incl the 7 on disk).
4. **Router rewrites** — affected family router tables
   (aerodynamics/fto/propulsion/flight-mechanics/space-systems/ses)
   reference ONLY built skills. Clean table rewrites, not row adds.
   Every router description <= 1024 chars (yaml-verified).
5. **Badge + stale guard** — README.md badge "Skills: <new> of 1,000+
   target"; add N31/N32 fixtures to ops/automation/test/run-tests.sh
   (N31 flags planted wave-10-close-era counts '162 skills'/'338 tasks';
   N32 exempts live wave-10 vocabulary); update stale-number-guard.sh
   pattern set if needed.
6. **Gates FRESH** (replay every one, do not trust prior runs):
   make validate -> 5/5 PASS (all tasks Hit@1 deterministic offline);
   make attest -> 3/3 PASS; bash ops/automation/test/run-tests.sh ->
   ALL TESTS PASS (incl N31/N32); python3
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
   Message_id may not persist in CLI human mode — record the send
   honestly (exit 0 + "sent").
9. **State note** — append one line to ops/automation/wave10-state.md
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
