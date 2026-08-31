# Wave-6 RE-DISPATCH #4 — Rescue-first, fan out IMMEDIATELY (13th interruption: relay reaper)

Context: Wave-6 re-dispatch #3 (proc 79165/79199, session
20260831_234543_9b5405, started 23:45:46) DIED at 23:52:06 (cli_close) —
relay runtime reaper killed the background proc mid-fan-out. The bot DID
spawn all 9 locked-leaf subagents at 23:50:38 (delegate fan-out live), but
the parent was reaped ~6.5 min in, taking the subagents with it
(agent_close 23:52:06). Zero leaf commits, zero wave-6 eval fragments.

LESSON (13th interruption, relay-reaper class): a background parent proc
gets ~8-10 min of life per re-dispatch before the relay's process reaper
kills it, and its delegate children die WITH it. Surviving work = what was
COMMITTED before the reap, not what was being built. Therefore:
(a) FAN OUT FIRST — spawn the leaf subagents in the first 60 seconds, no
long prep phase; prep runs while they build.
(b) SUBAGENTS COMMIT THEIR OWN LEAF the moment its gates pass (they have
git access in their session; do NOT wait for the parent to commit).
(c) Parent stays LEAN: do not pull large tool outputs into the parent
context; do not wait on subagents with idle long completions — if a
completion stalls >10 min, abort and re-dispatch that leaf.
(d) Anything on disk but uncommitted at reap time is RECOVERABLE WIP —
the next re-dispatch rescues it first.

STEP 0 — RESCUE (do not redo): fuselage-sizing rescue ALREADY LANDED
(9522676). Re-dispatch #3's only survivors are 7 untracked prep scripts in
ops/automation/state/ (check-env.sh, wave6-desc-lengths.py,
wave6-inventory.sh, wave6-locate-skills.sh, wave6-merge-corpus.py,
wave6-template-inventory.sh) + scratch_corpus_inspect.py at repo root.
These are YOUR OWN env/merge helpers from the interrupted runs — keep the
ones you will actually reuse, DELETE the rest, and sweep scratch_*.py at
close. Tree must be clean at close. They contain no skill content; nothing
else needs rescue.

## Your job (in /Users/enterprisehq/AeroSkills, ONE main branch)

STEP 1 — FAN OUT THE 9 LOCKED LEAVES NOW, one subagent per skill
(delegate_task), all from the wave-6 brief skill list
(ops/automation/wave6-brief.md):
  1. airfoil-geometry
  2. oblique-shock
  3. dynamic-stability
  4. descent-performance
  5. pursuit-guidance
  6. inertial-navigation
  7. load-spectrum-counting
  8. material-selection
  9. life-cycle-cost
Each subagent: brainstorm (Superpowers) → SKILL.md + scripts/ contract
test + 2 corpus tasks + standards-map ext if new standard → make validate
5/5 REAL gates green → COMMIT IMMEDIATELY ITSELF (7-rule message; subject
≤50 chars, imperative). Do not batch-commit; do not wait for all 9.

STEP 2 — CORPUS MERGE: merge all wave-6 eval fragments
(eval/hit1-wave6-*.yaml) into eval/hit1-corpus.yaml, update header counts,
delete standalone fragments. Baseline 240 tasks → 240+2N (N = leaves
landed).

STEP 3 — ROUTERS: rewrite the thinnest-family router SKILL.md tables
(aerodynamics, flight-mechanics, gnc-autonomy, structures, vehicle-design)
to list ONLY built leaves. Trim descriptions under the 1024-char spec
limit (gnc-autonomy is AT 1024 — trim ~100 chars; structures needs the
full rewrite — its table was mangled in re-dispatch #1: missing
crack-growth/miner-damage/laminate-stiffness rows, broken pipes).

STEP 4 — BADGE: README badge "Skills: N of 1,000+ target" live
(N ≈ 112 + leaves this wave); stale-number guard patterns extended to the
new class (N23/N24 fixtures if a new class appears).

STEP 5 — GATES FRESH (replay, not self-report): make validate 5/5 · make
attest 3/3 · scripts/gate-pytest-contract.sh · bash
ops/automation/stale-number-guard.sh · run-tests ALL PASS (incl
N10/N11/N15-N24 class) · em dashes 0 in live tree (dated docs exempt) ·
git status clean.

STEP 6 — PUSH PRIVATE: push to arjun-0077 via GITHUB_TOKEN_ARJUN
explicitly (credential store holds Ashforde token — NEVER publish,
arjun-0077 stays PRIVATE). Verify with ls-remote (explicit token URL:
https://x-access-token:${GITHUB_TOKEN_ARJUN}@github.com/arjun-0077/aeroskills.git)
that remote main == HEAD.

STEP 7 — POST AS SELF to GROUP topic 160 (telegram -1004333545328:160):
close-out summary with final counts + gate results.

## Hard rules
- Commit EACH skill the moment its gates pass — subagent commits itself.
- Fan out in the FIRST minute. Prep runs parallel to the build.
- Keep the parent session context lean. Delegate per-skill work; do not
  pull large file dumps into the parent conversation.
- If a completion stalls (>10 min no chunks), abort it and retry fresh —
  do not sit in the 600s stale-kill loop.
- If interrupted again: any on-disk WIP must be committed before the next
  re-dispatch (rescue-first pattern).
- 7-rule commit messages (subject ≤50 chars, imperative, body WHAT/WHY).
- No founder contact. Routine progress.
