# Wave-8 RE-DISPATCH #1 — Rescue-first, fan out IMMEDIATELY (14th interruption: relay runtime kill)

Context: Wave-8 parent proc 1528 (own profile, background, started
00:57) DIED at 01:14:16 — all opsmanager sessions show "Operation
interrupted" at 01:14:16 simultaneously (relay runtime kill pattern,
identical to the 13 prior kills). The parent had spawned 2 delegate
batches: deleg_390d5f4f (3 tasks: cfd-mesh-generation ·
parasite-drag · payload-range-diagram — ALL INTERRUPTED before
writing, zero disk presence) + deleg_e7312478 (10 tasks: skill-authoring
· goodman-diagram · composite-bolted-joints · widespread-fatigue-damage
· calculix-nonlinear · star-tracker · command-data-handling ·
state-space-analysis · dilution-of-precision · attitude-dynamics — ALL
INTERRUPTED at 01:14:16). Zero wave-8 commits landed. HEAD d31c7c5
(wave-8 helpers commit); origin/main d31c7c5 == HEAD (push deferred per
CI-first — correct; wave-7 end state was 7cc431d on remote, wave-8 has
nothing new to push yet).

LESSON (14th interruption, relay-runtime class — SAME as the prior 13):
a background parent proc gets ~8-10 min of life per re-dispatch before
the relay's process reaper kills it, and its delegate children die WITH
it. Surviving work = what was COMMITTED before the reap. Therefore:
(a) FAN OUT FIRST — spawn the leaf subagents in the first 60 seconds.
(b) SUBAGENTS COMMIT THEIR OWN LEAF the moment its gates pass (git
access in their session; do NOT wait for the parent to commit).
(c) Parent stays LEAN; abort completions stalled >10 min.
(d) Anything on disk but uncommitted at reap time is RECOVERABLE WIP —
the next re-dispatch rescues it first.

## Verified WIP on disk (orchestrator, FRESH at 01:16 — recover, don't redo)

COMPLETE leaves (SKILL.md + scripts + test present — commit each after
gates pass, ONE commit per leaf):
1. skills/space-systems/adcs/star-tracker (SKILL.md + star_tracker_logic.py + test_star_tracker.py)
2. skills/structures/composites/composite-bolted-joints (SKILL.md + composite_bolted_joints_logic.py + test_composite_bolted_joints.py)
3. skills/structures/damage-tolerance/widespread-fatigue-damage (SKILL.md + wfd_logic.py + test_wfd.py)
4. skills/structures/fatigue/goodman-diagram (SKILL.md + goodman_logic.py + test_goodman.py)

PARTIAL leaves (logic + test but NO SKILL.md — finish SKILL.md + 2
corpus tasks + 5 REAL gates, or DELETE; never ship without SKILL.md):
5. skills/gnc-autonomy/control/state-space-analysis (state_space_logic.py + test_state_space.py)
6. skills/gnc-autonomy/navigation/dilution-of-precision (dop_logic.py + test_dop.py)
7. skills/structures/fem/calculix-nonlinear (calculix_nonlinear_logic.py + test_calculix_nonlinear.py)

LOGIC ONLY (no SKILL.md, no test — finish fully or DELETE):
8. skills/cross-cutting/sep2640/skill-authoring (authoring_logic.py only)

Eval fragments (5, merge into corpus at close):
eval/hit1-wave8-command-data-handling.yaml ·
eval/hit1-wave8-composite-bolted-joints.yaml ·
eval/hit1-wave8-goodman-diagram.yaml ·
eval/hit1-wave8-star-tracker.yaml ·
eval/hit1-wave8-widespread-fatigue-damage.yaml

Helpers/fixtures (keep — YOUR prep, expected): ops/automation/state/
wave8-router-desc-len.py + ops/automation/test/fixture-legit-144-class/
+ ops/automation/test/fixture-stale-131-class/ (badge 131→144 class
prep). Sweep any tmp_* at close.

MISSING leaves (interrupted before writing — re-fan-out):
- aerodynamics/cfd/cfd-mesh-generation
- aerodynamics/drag-polars/parasite-drag
- vehicle-design/conceptual/payload-range-diagram
- space-systems/subsystems/command-data-handling (fragment exists, no dir)
- gnc-autonomy/space/attitude-dynamics

## Your job (in /Users/enterprisehq/AeroSkills, ONE main branch)

STEP 0 — RESCUE NOW: run 5 REAL gates on the 4 COMPLETE leaves and
commit EACH as its own 7-rule commit immediately. Then finish-or-delete
the 4 PARTIAL leaves (each its own commit once gates pass).

STEP 1 — FAN OUT IMMEDIATELY: one subagent per skill (delegate_task)
for the 5 MISSING leaves + 2-6 more from thinnest sub-packs (structures
composites/fatigue/fem, space-systems/adcs, gnc-autonomy/control/
navigation, vehicle-design/conceptual, aerodynamics/cfd) — target
+8-14 verified leaves THIS wave total (rescue + new). Each subagent:
brainstorm → SKILL.md + scripts/ contract test + 2 corpus tasks →
make validate 5/5 REAL gates green → COMMIT ITSELF immediately.

STEP 2 — CORPUS MERGE: merge ALL eval/hit1-wave8-*.yaml fragments into
eval/hit1-corpus.yaml + header counts (276 → 276+2N). Delete fragments.

STEP 3 — ROUTERS: clean router table rewrites for touched families
(structures/composites+fatigue+fem+damage-tolerance, space-systems/adcs,
gnc-autonomy/control+navigation+space, cross-cutting/sep2640,
aerodynamics/cfd+drag-polars, vehicle-design/conceptual) — list ONLY
built skills, descriptions ≤1024 (wave8-router-desc-len.py exists).

STEP 4 — BADGE: README badge → new live count. Stale-number guard
patterns 131-class → new class + N27/N28 fixtures (144-class fixtures
already prepped — wire them).

STEP 5 — GATES FRESH (replay, not self-report): make validate 5/5 ·
make attest 3/3 · run-tests ALL PASS (incl N10/N11/N25-N28) · stale
guard · em dashes 0 live tree · git status clean (tmp sweep).

STEP 6 — PUSH PRIVATE: GIT_TOKEN=GITHUB_TOKEN_ARJUN git push origin
main (credential store holds Ashforde token — arjun token explicitly;
NEVER publish to Ashforde; arjun-0077 stays PRIVATE). Verify remote
main == HEAD via ls-remote with explicit token URL.

STEP 7 — POST as yourself to GROUP 160 (3-15 lines, cold truth,
evidence: leaves landed, corpus count, gates green, badge count, push
verified).

## HARD RULES
- Commit EVERY skill immediately after gates pass. Never hold
  uncommitted work (14 kills — only committed work survives).
- Routers reference ONLY built skills (build or trim).
- One agent per skill via delegate_task; never build serially.
- No founder contact (routine progress; 50x20 release bar not met).
