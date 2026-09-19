---
name: q7028-component-replacement
description: "Plan the removal and replacement of a component on a populated printed board under ECSS-Q-ST-70-28, with thermal damage held inside limits. Use when a part must come off and the heat reaching the laminate, the new part and its neighbours must be argued first. Reads the profile for peak and time above the damage threshold by interpolating crossings, projects that peak onto each neighbour through a distance decay, decides if a moisture-sensitive part owes a bake, draws the work against the site allowance, then returns proceed, proceed-with-controls or refuse. Trigger: ecss, q-st-70-28, component-removal-replacement, board-rework-thermal-profile, rework-time-above-threshold, adjacent-component-heat-exposure, moisture-sensitive-part-bake, replacement-site-allowance."
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
  tags: [ecss, q-st-70-28-board-repair-scope, q7028-component-replacement, component-removal-replacement, board-rework-thermal-profile, rework-time-above-threshold, adjacent-component-heat-exposure, moisture-sensitive-part-bake, replacement-site-allowance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Board Repair — Component Removal and Replacement (space-systems/ecss/q7028-component-replacement)

Use when the task is the component-replacement part of the repair
methods of ECSS-Q-ST-70-28 — taking a part off a populated board and
fitting its replacement, with the heat that operation puts into the
laminate, into the new part and into everything around it kept inside
what each of them can take.

## Domain quick reference

- A thermal profile is graded on two numbers, not one. The peak says
  whether the laminate was taken past what it can survive at all. The
  time spent above the damage threshold says how much of the bond
  strength between copper and resin was spent getting there.
- Those two are independent: a brief excursion to a high peak and a long
  hold just over the threshold are different failures, and a plan can
  pass on one while failing on the other.
- Time above a threshold is interpolated across the crossings, not
  counted in whole sample intervals. A profile sampled every second
  reports nearly double the true dwell if the partial intervals at each
  end are counted whole, and that error always runs the unsafe way when
  the budget is a few seconds.
- The parts that get damaged are often not the one being replaced. Heat
  spreads through the copper and the laminate, so a neighbour that the
  iron never touches can still exceed its own limit. Projecting the peak
  onto each neighbour through a distance decay is what turns "it looked
  close" into a shielding decision.
- A moisture-sensitive replacement part carries its own precondition.
  Sensitivity level sets a floor life; once that is spent, the part is
  baked before it is fitted, or the moisture in the package flashes to
  steam during reflow and delaminates it from the inside.
- Sites are budgeted. The pad and the laminate beneath it survive a
  limited number of replacements, so the count is checked before the
  profile is designed, not after the part is already off.

## Workflow

1. Validate the profile, the neighbour list and the site history; a
   profile with non-increasing times, a negative count or a
   non-numeric temperature is an input error, not a severe plan.
2. Read the peak from the profile and compare it with what the laminate
   can take, using a named tolerance at the boundary.
3. Compute the time above the damage threshold by interpolating the
   crossing on each ramp, and compare it with the dwell budget.
4. Project the peak onto every neighbour at its distance through the
   decay length, and list each one whose projected exposure exceeds its
   own limit — those are the shielding actions.
5. Take the replacement part's sensitivity level and accumulated floor
   time and decide whether it owes a bake; an already-baked part does
   not owe a second one.
6. Draw the work against the site's replacement allowance.
7. Refuse on an over-temperature peak, an over-budget dwell or an
   exhausted site; otherwise return proceed-with-controls when any
   shielding, bake, preheat or last-allowance finding stands, and
   proceed only when none does.

## Pitfalls

- Grading a profile on its peak alone. Two plans with the same peak can
  put very different amounts of energy into the pad bond, and only the
  time above the threshold separates them.
- Counting whole sample intervals as time above the threshold. The
  partial intervals at each crossing have to be interpolated, or a
  coarsely sampled profile reads as far worse or far better than it is.
- Checking only the part being replaced. The neighbours are where
  unplanned damage shows up, and they are assessed from their distance,
  not from whether they looked close to the work.
- Fitting a moisture-sensitive part straight from a shelf because the
  reflow profile is within limits. The profile is not the issue; the
  moisture already in the package is, and it is removed by baking
  before the part is fitted.
- Designing the profile before checking the site allowance. A site out
  of allowance is not workable at any profile, so the count comes
  first.
- Trading an out-of-limit peak against a comfortable dwell, or the
  reverse. Each limit protects a different failure mode and neither
  buys headroom for the other.

## Behavior contract (gate 3)

The profile validation, peak reading, interpolated time-above-threshold,
neighbour exposure projection, moisture-sensitivity bake decision, site
allowance and the refuse / proceed-with-controls / proceed ladder are
exercised by the gate 3 contract test:
scripts/test_q7028_component_replacement.py against
scripts/q7028_component_replacement_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7028_component_replacement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
