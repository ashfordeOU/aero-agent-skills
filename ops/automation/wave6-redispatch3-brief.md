# Wave-6 RE-DISPATCH #3 — Fresh context, fan-out NOW (12th interruption: PROVIDER HANG)

Context: Wave-6 re-dispatch #2 (proc 72186, started 23:12) HUNG — NOT a relay
kill. The bot completed its prep (read gate scripts, wrote
ops/automation/state/check-env.sh, ran fixture-tree + env checks — last DB
message 23:14:51) then the DeepSeek completion for a ~73k-token context went
STALE: agent.log shows two consecutive 600s stale-stream kills (23:24:54,
23:34:54, "no chunks received, killing connection") and the retry loop would
have repeated forever. Zero commits landed, zero delegate children spawned,
CPU frozen 0.3%. Orchestrator SIGKILLed 72186 at 23:44 after confirming the
hang (not a stall: no file writes for 30 min, no children, no net activity).

LESSON (provider-hang class, 12th interruption): a bot whose LLM call goes
stale can look alive (proc up) while making zero progress. Guard: (a) keep
context LEAN — do not accumulate large tool outputs in the parent; delegate
the per-skill work so each subagent holds small context; (b) after ANY long
completion, verify progress by checking for new commits / file writes; (c) if
a completion seems stuck >10 min, do not wait for the 600s stale kill —
abort and retry with a fresh, smaller request.

STEP 0 (ALREADY DONE — do not redo): fuselage-sizing rescue landed 9522676.
Remote main still 2865cb9 (push deferred per CI-first — correct).
Tree: HEAD 38cba93, 1 untracked = ops/automation/state/check-env.sh (your own
env helper, 910 bytes — keep or sweep, your call; tree must be clean at close).

## Your job (in /Users/enterprisehq/AeroSkills, ONE main branch)

STEP 1 — FAN OUT THE 9 LOCKED LEAVES, one subagent per skill (delegate_task),
all from the wave-6 brief skill list (ops/automation/wave6-brief.md):
  1. airfoil-geometry
  2. oblique-shock
  3. dynamic-stability
  4. descent-performance
  5. pursuit-guidance
  6. inertial-navigation
  7. load-spectrum-counting
  8. material-selection
  9. life-cycle-cost
Each subagent: brainstorm (Superpowers) → SKILL.md + scripts/ contract test +
2 corpus tasks + standards-map ext if new standard → make validate 5/5 REAL
gates green → COMMIT IMMEDIATELY (incremental-commit mandate — 11 prior
interruptions lost whole waves because work sat uncommitted).

STEP 2 — CORPUS MERGE: merge all wave-6 eval fragments (eval/hit1-wave6-*.yaml
or equivalent) into eval/hit1-corpus.yaml, update header counts, delete
standalone fragments. Baseline 240 tasks → 240+2N (N = leaves landed).

STEP 3 — ROUTERS: rewrite the thinnest-family router SKILL.md tables
(aerodynamics, flight-mechanics, gnc-autonomy, structures, vehicle-design)
to list ONLY built leaves. Trim descriptions under the 1024-char spec limit.
NOTE: the structures router table was observed MANGLED in re-dispatch #1
(missing crack-growth/miner-damage/laminate-stiffness rows, broken pipes) —
repair it in this rewrite.

STEP 4 — BADGE: README badge "Skills: N of 1,000+ target" live; stale-number
guard patterns extended to the new class (N23/N24 fixtures if a new class
appears).

STEP 5 — GATES FRESH (replay, not self-report): make validate 5/5 · make
attest 3/3 · scripts/gate-pytest-contract.sh · bash ops/automation/stale-number-guard.sh
· run-tests ALL PASS (incl N10/N11/N15-N24 class) · em dashes 0 in live tree
(dated docs exempt) · git status clean.

STEP 6 — PUSH PRIVATE: push to arjun-0077 via GITHUB_TOKEN_ARJUN explicitly
(credential store holds Ashforde token — NEVER publish, arjun-0077 stays
PRIVATE). Verify with ls-remote that remote main == HEAD.

STEP 7 — POST AS SELF to GROUP topic 160 (telegram -1004333545328:160):
close-out summary with final counts + gate results.

## Hard rules
- Commit EACH skill the moment its gates pass. Never hold work uncommitted.
- Keep the parent session context lean. Delegate per-skill work; do not pull
  large file dumps into the parent conversation.
- If a completion stalls (>10 min no chunks), abort it and retry fresh —
  do not sit in the 600s stale-kill loop.
- If interrupted again: any on-disk WIP must be committed before the next
  re-dispatch (rescue-first pattern).
- 7-rule commit messages (subject ≤50 chars, imperative, body WHAT/WHY).
- No founder contact. Routine progress.
