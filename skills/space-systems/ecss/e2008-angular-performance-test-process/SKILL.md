---
name: e2008-angular-performance-test-process
description: "Design the incidence-angle sweep a photovoltaic assembly angular performance measurement runs under ECSS-E-ST-20-08C clause 6.4.3.19.2: build the angle schedule, hold a coarse step up to sixty degrees and a further-refined step beyond it where the response leaves the cosine fastest, size the widest gap each region actually leaves, bound the straight-line error a gap admits between measured points, and confirm the sweep reaches the declared maximum angle. Use when an angular sweep is being planned, or an as-run one has to be judged against the step rule. Trigger: ecss, e-st-20-08c-clause-6-4-3-19-2, solar-array-angular-sweep-schedule, incidence-angle-step-refinement, sixty-degree-step-breakpoint, angular-interpolation-error-bound, angular-sweep-truncation-check."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-angular-performance-test-process, solar-array-angular-sweep-schedule, incidence-angle-step-refinement, sixty-degree-step-breakpoint, angular-interpolation-error-bound, angular-sweep-truncation-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Angular Performance Test Process (space-systems/ecss/e2008-angular-performance-test-process)

Use when the task is clause 6.4.3.19.2 of ECSS-E-ST-20-08C -- running or
reviewing the sweep itself. The assembly output is read at a series of
sun incidence angles, and the clause's substance is the spacing of that
series: a coarse step while the response still tracks the cosine, and
further steps once sixty degrees is passed.

## Domain quick reference

- The sweep is the measurement. One angle gives a point; the quantity
  the power budget wants is a curve, and a curve is only as good as the
  spacing of the points it is drawn through.
- Between two measured angles the curve is read by straight-line
  interpolation, and the error that leaves is bounded by the step
  squared over eight times the largest second derivative on the
  interval. For a cosine that derivative is the cosine itself, so the
  arithmetic bound falls as the angle opens.
- The real response does the opposite. Past about sixty degrees the
  coverglass reflection climbs steeply, the illuminated area shortens
  and the response leaves the cosine, so the region where the formula
  says the interpolation is safest is the region where the underlying
  curve is least like the model. That is the whole reason the step
  refines there rather than staying coarse.
- The breakpoint angle is always a measured point, whether or not it
  falls on the coarse grid, because it is the join between two step
  sizes and an unmeasured join is where the two halves of the curve
  disagree.
- The declared maximum angle is also always measured. A sweep that runs
  out of points before it gets there has not produced a short curve, it
  has produced a curve missing the end the off-pointing case needs.
- Coverage has two independent failures. A sweep can hold every
  scheduled angle and still leave a gap where a point was dropped, and
  it can hold the right spacing over a region it never entered.
- Repeated readings at the same angle are one point, not two. Grouping
  them inside a match tolerance before any gap is measured stops a
  dwell from reading as sample density it never provided.

## Workflow

1. Validate the sweep policy first: breakpoint, coarse step, refined
   step, ceiling, match tolerance and error allowance. A refined step
   no smaller than the coarse step is refused -- the sweep takes
   further steps past the breakpoint, not fewer.
2. Build the planned schedule from the policy: coarse multiples up to
   the breakpoint, the breakpoint itself, then refined steps to the
   declared maximum, with the maximum appended when the refined grid
   does not land on it.
3. Normalise the measured angles before judging anything: sort them and
   group repeats inside the match tolerance, so one dwell is one point.
4. List the scheduled angles with no measured point inside the
   tolerance. A missing angle is reported as itself, not folded into
   the gap that swallowed it.
5. Size the widest gap in each region separately, against that region's
   own step. A region entered with fewer than two points has no gap to
   measure and is reported as that, not as a pass.
6. Bound the straight-line interpolation error the widest gap admits
   and hold it under the allowance, so a sweep that meets the step rule
   by arithmetic but not by curvature is still caught.
7. Close on one verdict: sweep not planned, truncated, undersampled, or
   accepted -- with every finding listed, not only the one that set the
   verdict.

## Pitfalls

- Carrying the coarse step past the breakpoint. It is the single most
  common way an otherwise complete sweep loses the region it was run
  for, and the gap check is what catches it.
- Reading a dwell as coverage. Five readings at forty degrees are one
  measured angle; without grouping them the point count looks healthy
  while the spacing is untouched.
- Stopping the sweep when the output gets small. The wide-angle points
  carry the least power and the most information about the departure
  from the cosine, and the off-pointing budget is written there.
- Judging the whole sweep by one gap figure. The coarse and the refined
  regions have different steps, so a single largest-gap number either
  passes a refined-region failure or fails a legitimate coarse step.
- Comparing a derived gap against its step by bare arithmetic. Both are
  differences of floats that can land a few units in the last place
  either side of a limit, so the comparison absorbs that error while
  the step itself is never relaxed.
- Leaving the breakpoint unmeasured because the grid skipped it. The
  two step regimes join there, and with no point at the join nothing
  says whether they describe the same curve.

## Behavior contract (gate 3)

The policy validation, schedule construction, per-angle step selection,
measured-angle normalisation and grouping, missing-angle listing,
per-region gap sizing, interpolation error bound, maximum-angle reach
and the sweep verdict are exercised by the gate 3 contract test:
scripts/test_e2008_angular_performance_test_process.py against
scripts/e2008_angular_performance_test_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_angular_performance_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
