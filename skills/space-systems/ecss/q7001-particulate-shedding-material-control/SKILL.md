---
name: q7001-particulate-shedding-material-control
description: "Assess the particulate-shedding materials of an installation against the cleanliness budget of ECSS-Q-ST-70-01C and decide the controls each one owes: resolve the shedding family of every paint, textile, blanket edge, foam, tape edge and hook-and-loop strip, take the control that family carries by construction, weight each source by its exposed area, the orientation of the receiving surface and the view factor between them, roll the exposure hours into a percent area coverage, compare the stack with the level the surface is held to, and name the dominant source. Use when a layout or a materials list is reviewed for particulate. Trigger: ecss, q-st-70-01c, particulate-shedding-material-control, hook-and-loop-fastener-shedding, unsealed-paint-shedding, percent-area-coverage-budget, particulate-fallout-capture-factor, edge-sealing-control."
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
  tags: [ecss, q-st-70-01c-cleanliness-scope, q7001-particulate-shedding-material-control, hook-and-loop-fastener-shedding, unsealed-paint-shedding, percent-area-coverage-budget, particulate-fallout-capture-factor, textile-edge-sealing-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness -- Particulate-Shedding Material Control (space-systems/ecss/q7001-particulate-shedding-material-control)

Use when the task is the control ECSS-Q-ST-70-01C imposes on materials that
shed particulate -- paints, textiles, blanket edges, foams, tape edges,
hook-and-loop fastener -- installed where the particulate can reach a
surface held to a cleanliness level.

## Domain quick reference

- Shedding is a property of the family, not of the individual part. A
  hook-and-loop strip, a cut textile edge and an unsealed paint shed by the
  construction they have; a conversion coating and a polished metal face
  barely shed at all. Resolving the family first is what makes the estimate
  reproducible across two reviewers.
- Some families carry a control by construction, and the control is the
  answer, not the finding. Edges get bound and sealed, paints get sealed
  and their adhesion verified, foams get encapsulated, fastener gets
  enclosed or moved out of line of sight. A control correctly applied
  leaves a residual source; it does not delete one.
- Geometry decides what arrives. Fallout lands on an upward-facing surface,
  largely misses a vertical one and barely touches a downward-facing one,
  and the view factor between source and surface scales all three. A large
  shedder facing away is a smaller problem than a small one overhead.
- The quantity that has a budget is percent area coverage, and it
  accumulates with exposure hours. The same installation is compliant for a
  short integration flow and non-compliant for a long one, so the hours are
  an input to the decision and not a footnote.
- Levels differ by orders of magnitude. A stack that is comfortable at the
  loosest level is refused at the tightest, so the level the surface is
  held to is resolved before any source is added up.
- The useful output is the dominant source. A total tells a reviewer the
  installation fails; the ordered contribution list tells them which strip
  of fastener to move.

## Workflow

1. Resolve the shedding family of every source, refusing a family outside
   the recognised set rather than defaulting to the mildest one.
2. Normalise each source: exposed area, orientation of the receiving
   surface, view factor, and whether the mandatory control was applied;
   refuse a duplicated source name.
3. Compute the capture factor from orientation and view factor.
4. Compute each contribution from the family index, the control credit, the
   source-to-surface area ratio, the capture factor and the exposure hours.
5. Sum the contributions and compare with the budget the cleanliness level
   admits, absorbing an exact-equality case with a named tolerance.
6. Report the controls still owed, the ordered contributions, the dominant
   source and the verdict.

## Pitfalls

- Grading a material by name instead of family. Two paints differ by
  whether they are sealed, and the family is where that lives.
- Treating an applied control as a removed source. The credit is a
  reduction; a controlled fastener still contributes, and a stack of them
  still adds up.
- Ignoring orientation. A downward-facing surface collects a small fraction
  of what an upward-facing one does, and a layout review that omits this
  moves the wrong part.
- Quoting a coverage figure with no exposure hours attached. The number is
  a rate integrated over a duration, and the duration is what changes
  between integration flows.
- Reporting only the total. The ordered contribution list is what makes the
  finding actionable, because one source usually carries most of it.

## Behavior contract (gate 3)

The family resolution, the mandatory-control credit, the orientation and
view-factor capture, the exposure-scaled contribution, the budget
comparison against the cleanliness level, the controls-owed list and the
dominant-source ordering are exercised by the gate 3 contract test:
scripts/test_q7001_particulate_shedding_material_control.py against
scripts/q7001_particulate_shedding_material_control_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7001_particulate_shedding_material_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
