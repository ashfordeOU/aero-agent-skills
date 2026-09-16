---
name: e2008-sca-flatness-test-purpose
description: "Use when scoping or reviewing a cell assembly flatness campaign. Determine whether a flatness measurement on a completed solar cell assembly serves the purpose ECSS-E-ST-20-08C clause 6.4.3.17.1 gives it, showing how flat the assembly is before integration: map each declared integration step onto the flatness objective the measurement demonstrates, accumulate those sensitivities into one integration demand, decide whether the mounting route and that demand earn the measurement at all, then confirm the planned run follows every operation that sets the shape of the stack and reads enough subgroup samples to speak for the lot. Trigger: ecss, e-st-20-08c, clause-6-4-3-17-1, sca-flatness-purpose, pre-integration-flatness-demand, sca-bond-line-thickness-control, sca-coverglass-clamp-down-stress, sca-flatness-subgroup-sampling."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-sca-flatness-test-purpose, sca-flatness-purpose, pre-integration-flatness-demand, sca-bond-line-thickness-control, sca-coverglass-clamp-down-stress, sca-flatness-subgroup-sampling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Flatness Test Purpose (space-systems/ecss/e2008-sca-flatness-test-purpose)

Use when the task is to state and defend why the flatness of a completed cell
assembly is established before integration under ECSS-E-ST-20-08C clause
6.4.3.17.1 — what the measurement is meant to protect, whether the integration
route justifies it, and whether the planned run actually reports the shape the
panel will receive.

## Domain quick reference

- Flatness is an integration property, not a cosmetic one. Nothing on the
  build line cares what shape the stack relaxes into; everything downstream
  does, so the measurement is bought by the integration route rather than by
  the assembly.
- The stack acquires its shape from the operations that build it. A brittle
  cell, a coverglass bonded to its front and interconnects welded to its back
  were joined at different temperatures, and the assembly settles into a bow
  or a twist of its own once it comes off the tooling.
- Each integration step turns a bow into a distinct hazard, and therefore into
  a distinct objective. A bond line loses thickness control, a hold-down bends
  the assembly until the coverglass carries the stress, thermal contact to the
  facesheet is only as good as the area that touches, vacuum tooling cannot
  seat what it cannot pull down, and a stack height envelope is spent before
  the assembly is placed.
- Steps of different kinds are only comparable once scaled. A sensitivity
  expressed as a share of the step tolerance the deviation can spend lets
  unlike integration steps accumulate into one integration demand.
- Justification is a joint condition. An assembly that is never constrained by
  a rigid surface has no shape worth measuring beforehand however sensitive its
  handling is, and a genuinely tolerant integration route does not earn the
  measurement however bowed the assembly may be.
- Order is what makes the reading evidence. A reading taken on a bare cell
  before its coverglass is bonded reports the cell, and a reading taken after
  the assembly is on the panel reports the panel.
- A subgroup is a sampling device. Too few samples read leaves the result
  unable to speak for the lot even when the run is well placed.
- A stated purpose is not a served purpose. An assembly that earns the
  measurement but has none planned is a distinct outcome from one whose
  planned run sits in the wrong place, and the two carry different actions.

## Workflow

1. Validate the declared policy first: per-step weights, the demand trigger and
   the subgroup sample floor. An unrecognised step in the weights is refused
   rather than ignored, so a typo cannot silently drop a demand.
2. Validate the integration inventory: recognised step names, no duplicates,
   and a sensitivity expressed as a share of the tolerance the step carries.
3. Validate the shape-setting operations the assembly actually went through,
   refusing an unrecognised or repeated operation.
4. Map each integration step to the flatness objective the measurement
   demonstrates against it, and append the shared planarity objective when the
   assembly goes onto a rigid panel at all.
5. Accumulate the weighted sensitivities into one integration demand.
6. Decide whether the measurement is justified: a rigid integration route and a
   demand at or above the trigger. A demand landing exactly on the trigger
   earns the measurement; the comparison tolerance absorbs representation error
   and the trigger does not move.
7. When it is justified, grade the planned run — does it follow every declared
   shape-setting operation, is it taken before integration, and does it read
   enough subgroup samples — and report each shortfall with the value it owed.
8. Close on one verdict: not required, justified but not planned, planned but
   under scope, or serving its purpose, with the objectives attached to it.

## Pitfalls

- Treating flatness as a build line acceptance number. The build line has no
  use for it; the measurement exists because an adhesive laydown, a hold-down
  and a stack height envelope downstream all spend the deviation.
- Reading only the most sensitive integration step. A route of several tolerant
  steps can demand more of the shape than one sensitive step, and it is the
  accumulation the assembly has to answer.
- Adding raw sensitivities across unlike steps. A bond line thickness and a
  nozzle seating are not interchangeable until each is scaled against the
  tolerance it carries.
- Standing the measurement down because the assembly looks flat. The decision
  follows the declared inventory, so an undeclared integration step silently
  removes an objective the subgroup was supposed to demonstrate.
- Measuring before the stack is finished. A bare cell is not the part that gets
  placed, and a reading taken on it describes a shape that coverglass bonding
  and interconnect welding still change.
- Measuring after integration. The panel holds the assembly to its own surface,
  so the reading reports the constraint rather than the shape the assembly
  brought to it.
- Calling a justified measurement satisfied because some flatness data exists.
  Data taken in the wrong place, or from too few samples, leaves the purpose
  unserved, and that is a finding rather than a pass.

## Behavior contract (gate 3)

The policy validation, integration inventory checks, shape-setting operation
validation, objective mapping, integration demand accumulation, justification
decision, planned-run grading and the purpose verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_sca_flatness_test_purpose.py against
scripts/e2008_sca_flatness_test_purpose_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_sca_flatness_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
