---
name: q7001-cleanliness-verification-plan
description: "Plan the verification of every cleanliness requirement on a space product. Use when a contamination control plan under ECSS-Q-ST-70-01C has to state, requirement by requirement, which measurement method substantiates it and at which programme point: match each particulate or molecular limit to a method whose detection floor sits below it by a declared margin, refuse a method whose minimum sample area exceeds the accessible surface, report a limit carried only by a qualitative look or a critical surface carried only by an indirect witness as uncovered, place points through to the last milestone the surface stays reachable at, and give back the covered fraction. Trigger: ecss, q-st-70-01c, cleanliness-verification-plan, cleanliness-method-allocation, cleanliness-verification-point, cleanliness-detection-floor-margin, contamination-control-plan-coverage, cleanliness-witness-surface-allocation."
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
  tags: [ecss, q-st-70-01-cleanliness-scope, q7001-cleanliness-verification-plan, cleanliness-method-allocation, cleanliness-verification-point, cleanliness-detection-floor-margin, contamination-control-plan-coverage, cleanliness-witness-surface-allocation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness -- Verification Planning (space-systems/ecss/q7001-cleanliness-verification-plan)

Use when the task is the planning step of cleanliness verification under
ECSS-Q-ST-70-01C: a list of particulate and molecular cleanliness
requirements exists, a catalogue of measurement methods is available to
the programme, and the question is which method carries which requirement
and at which milestone the measurement is taken.

## Domain quick reference

- A cleanliness requirement is not verified by naming a method. It is
  verified when a method of the right kind reaches below the limit with
  discrimination to spare, fits the surface it has to sample, and is
  scheduled at a point where the surface is still reachable.
- Detection floor and limit are different quantities. A method whose
  floor sits exactly at the limit cannot separate a pass from a fail, so
  capability is a margin factor on the floor, not a bare comparison.
- Minimum sample area is a hard constraint, not a preference. A method
  needing a quarter of a square metre cannot substantiate a limit that
  applies to a fifty square centimetre optical bench, however sensitive
  it is.
- A direct measurement reads the hardware surface; an indirect one reads
  a witness surface standing in for it and inherits every assumption in
  that transfer. A criticality-driven surface therefore cannot rest on a
  witness alone.
- A qualitative observation reports a presence, not a number. It
  supports a numeric limit only alongside an instrumented method; on its
  own it leaves the requirement uncovered no matter how carefully it is
  performed.
- Verification points follow accessibility. Once a surface is closed out
  behind a panel or inside a fairing it can no longer be sampled, so the
  last point has to sit at the last milestone it is still open at.

## Workflow

1. Validate each requirement: contamination kind, numeric limit, the
   accessible area the limit applies to, the ordered milestones it spans,
   the last milestone the surface is reachable at, and whether it is
   criticality-driven.
2. Validate the method catalogue: kinds measured, detection floor in the
   units of the limit, minimum sample area, whether it returns a number,
   and whether it reads the hardware or a witness surface.
3. For each requirement, keep the methods of the matching kind whose
   minimum sample area fits the surface and whose floor sits below the
   limit divided by the margin factor; absorb representation error at
   that boundary with a named tolerance rather than by softening the
   margin.
4. Rank the survivors direct before indirect, then by lowest floor, then
   by name so the selection is reproducible, and take the first as the
   selected method with the rest recorded as alternates.
5. Place verification points at every milestone up to and including the
   last accessible one.
6. Raise the findings the entry earns: no method of the kind, qualitative
   coverage only, no method fitting the area, no method reaching the
   margin, or a criticality-driven surface on a witness alone.
7. Aggregate the entries into a plan carrying the covered fraction, the
   uncovered requirement identifiers and the pooled finding list.

## Pitfalls

- Reading a method catalogue entry as coverage. A method listed against a
  requirement whose floor sits above the limit adds a row to the plan and
  nothing to the verification.
- Letting a witness surface carry a criticality-driven requirement. The
  witness reports its own accumulation; transferring that to the hardware
  is an assumption the plan has to state and a direct measurement has to
  bound.
- Planning a final verification point after the surface is closed out.
  The point exists in the schedule and cannot be performed, which is
  discovered at the milestone rather than during planning.
- Treating a black-light or visual pass as substantiating a numeric
  level. It records that nothing was seen under those conditions, which
  is a different statement from a measured value below a limit.
- Sizing a sample area from the method datasheet without checking the
  hardware. The area the limit applies to, not the area of the largest
  nearby panel, is what the minimum has to fit inside.
- Loosening the margin factor to make a marginal method capable. That
  moves the discrimination problem from the plan into the acceptance
  decision, where the exceedance is no longer separable from the noise.

## Behavior contract (gate 3)

The requirement and method validation, kind matching, floor-margin and
sample-area capability rules, ranking, verification-point placement,
per-requirement findings and plan aggregation are exercised by the gate 3
contract test:
scripts/test_q7001_cleanliness_verification_plan.py against
scripts/q7001_cleanliness_verification_plan_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_cleanliness_verification_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
