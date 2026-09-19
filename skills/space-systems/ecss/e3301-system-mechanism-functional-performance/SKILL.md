---
name: e3301-system-mechanism-functional-performance
description: "Verify the kinematic performance a mechanism owes per position change, under ECSS-E-ST-33-01C clause 4.4. Use when every commanded position change has to be shown achievable and each function graded against what was specified: taking the travel, the allowed window and the velocity and acceleration limits, deciding whether the profile saturates its velocity limit or stays triangular, computing the shortest time and the peak velocity that follow, reporting the time margin left in the window, summing changes and dwells into a function duration against its budget, and grading the end-position error against its tolerance. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-position-change-time, mechanism-kinematic-profile, trapezoidal-velocity-profile, mechanism-time-margin, mechanism-positioning-accuracy, mechanism-function-duration-budget."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-system-mechanism-functional-performance, mechanism-position-change-time, mechanism-kinematic-profile, trapezoidal-velocity-profile, mechanism-time-margin, mechanism-positioning-accuracy, mechanism-function-duration-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — System and Mechanism Functional Performance (space-systems/ecss/e3301-system-mechanism-functional-performance)

Use when the task is the functional performance obligation of
ECSS-E-ST-33-01C clause 4.4 -- stating what each commanded position
change has to achieve, and showing that the drive can actually do it
inside the window it was given.

## Domain quick reference

- The specification is per position change, not per mechanism. Each
  change carries a travel, a window it must complete in, and the
  velocity and acceleration the drive may use. A mechanism that meets
  an average slew rate can still miss a short change it has no room to
  accelerate through.
- Two profiles cover the common drive. A short travel runs triangular:
  the drive accelerates to a peak and immediately decelerates, never
  reaching its velocity limit, and the time goes as twice the root of
  travel over acceleration. A long travel runs trapezoidal: the limit
  is reached and coasted, and the time is travel over velocity plus
  velocity over acceleration.
- The two meet where the travel equals the square of the velocity
  limit over the acceleration limit. Both expressions give the same
  time there, which is the check that the branch has been written
  correctly -- a branch that jumps at the boundary is wrong.
- Peak velocity is a result, not an input. On a short change it is the
  root of travel times acceleration and sits below the limit; the
  limit is only reached once the travel passes saturation. Sizing a
  motor from the limit when the change never gets there overstates the
  duty.
- A feasible change is not yet an acceptable one. The window has to
  keep a margin, because the closed-form time assumes ideal ramps and
  no control settling, and a change sized to exactly fill its window
  has nothing left for the real drive.
- The function is the sum of its changes plus the dwells between them,
  and it carries a budget of its own. Every individual change can pass
  and the sequence still overrun.
- Times come from roots and ratios, so a change built to sit exactly
  on its window or a margin built to sit exactly on its requirement
  can evaluate a hair under. The comparison absorbs that; the
  requirement is not relaxed.

## Workflow

1. Write each position change down with an identifier, its travel, its
   allowed window, and the velocity and acceleration limits the drive
   may use, plus any dwell that follows it.
2. Compute the saturation travel from the two limits and decide the
   profile. Read a travel sitting on the boundary as saturated, since
   both forms agree there and the peak velocity is then the limit.
3. Compute the shortest achievable time and the peak velocity the
   change actually reaches, and report the profile alongside them so
   the number can be argued with.
4. Take the time margin as the unused fraction of the window, and
   grade it against the required margin. Report an infeasible change
   and a thin-margin change differently -- they are repaired by
   different design changes.
5. Grade the end-position error against the stated tolerance. A stated
   tolerance with no demonstrated error is not a pass, and a change
   with no tolerance at all is an incomplete specification rather than
   a compliant one.
6. Sum the change times and dwells into a function duration and
   compare it with the function budget. Close only when every change
   and the assembled function both hold.

## Pitfalls

- Sizing every change from the velocity limit. A short change is
  acceleration bound and never reaches the limit, so dividing travel by
  the limit gives a time the drive cannot achieve and hides the real
  constraint.
- Writing the profile branch with a bare comparison. The saturation
  travel is a quotient of two limits, so a travel written to sit on it
  lands on either side depending on the platform, and a branch that
  disagrees at the boundary makes the answer platform dependent.
- Reporting feasibility as compliance. A change that exactly fills its
  window has zero margin for control settling, friction rise over life
  and off-nominal supply, and the clause is met by the specification,
  not by the ideal profile.
- Grading the changes and forgetting the function. Dwells are real
  time, and a sequence of individually comfortable changes can still
  miss a deployment window.
- Accepting a tolerance that was stated and never measured. The
  specification half of the clause is easy to satisfy on paper; the
  demonstration half is what the tolerance is for.
- Taking a signed position error at face value in a comparison. The
  tolerance is a magnitude, so an error carried with its sign can pass
  a limit it exceeds on the other side.

## Behavior contract (gate 3)

Profile selection, peak velocity, the minimum transition time and its
agreement at the saturation boundary, the time margin, end-position
grading, the function duration and the overall verdict are exercised by
the gate 3 contract test:
scripts/test_e3301_system_mechanism_functional_performance.py against
scripts/e3301_system_mechanism_functional_performance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3301_system_mechanism_functional_performance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
