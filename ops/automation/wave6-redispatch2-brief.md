# Wave-6 RE-DISPATCH #2 — Rescue COMPLETE, Fan-out NOW (11th kill)

Context: Wave-6 first dispatch (22:48) killed mid fan-out (10th kill, zero commits).
Redispatch #1 (23:00) completed STEP 0 rescue (commit 9522676 "feat: add
fuselage-sizing leaf" — SKILL.md + logic + contract test, gates green) then
spawned the 9-leaf fan-out; ALL delegate children interrupted ~76s in by the
relay runtime (11th kill, 23:07). NO leaves committed after the rescue.
Tree clean at HEAD 9522676; remote main still 2865cb9 (push deferred per
CI-first — correct). This is RE-DISPATCH #2.

## Your job (in /Users/enterprisehq/AeroSkills, ONE main branch)

STEP 0 (ALREADY DONE — do not redo): fuselage-sizing rescue landed 9522676.

STEP 1 — FAN OUT THE REMAINING 9 LOCKED LEAVES, one subagent per skill
(delegate_task), all from the wave-6 brief skill list (ops/automation/wave6-brief.md):
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
gates green → COMMIT IMMEDIATELY (incremental-commit mandate — the 9 prior
kills lost whole waves because work sat uncommitted).

STEP 2 — CORPUS MERGE: merge all wave-6 eval fragments (eval/hit1-wave6-*.yaml
or equivalent) into eval/hit1-corpus.yaml, update header counts, delete
standalone fragments. Baseline 240 tasks → 240+2N (N = leaves landed).

STEP 3 — ROUTERS: rewrite the 5 thinnest-family router SKILL.md tables
(aerodynamics, flight-mechanics, gnc-autonomy, structures, vehicle-design)
to list ONLY built leaves. Trim descriptions under the 1024-char spec limit.

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
- If interrupted again: any on-disk WIP must be committed before the next
  re-dispatch (rescue-first pattern).
- 7-rule commit messages (subject ≤50 chars, imperative, body WHAT/WHY).
- No founder contact. Routine progress.
