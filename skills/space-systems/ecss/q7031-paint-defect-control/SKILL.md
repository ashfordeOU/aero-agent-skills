---
name: q7031-paint-defect-control
description: "Evaluate the imperfections found on an applied coat under ECSS-Q-ST-70-31C and turn them into a disposition: group each one under a defect family -- run, sag, orange peel, pinhole, inclusion, contamination -- scale that family's size and density allowances by the surface it sits on, grade it against both, then map a breach to a local rework, a strip and recoat or a referral, escalating anything out of limits on an optical face. Use when a post-application inspection record has to be dispositioned rather than merely listed. Trigger: ecss, q-st-70-31c-paint-quality, coating-defect-family-allowance, paint-run-and-sag-limit, coating-pinhole-density-limit, paint-surface-criticality-allowance, coating-defect-disposition."
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
  tags: [ecss, q-st-70-31c-paint-quality-scope, q7031-paint-defect-control, coating-defect-family-allowance, paint-run-and-sag-limit, coating-pinhole-density-limit, paint-surface-criticality-allowance, coating-defect-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Paint Application -- Defect Control (space-systems/ecss/q7031-paint-defect-control)

Use when the task is the defect control of ECSS-Q-ST-70-31C: a coat has been
applied and inspected, imperfections have been recorded, and the question is
what each one earns -- nothing, a local rework, a strip and recoat, or a
referral to the review board.

## Domain quick reference

- The recorded imperfections fall into families that behave differently.
  Runs, sags and orange peel are flow and atomisation faults that sit on the
  surface. Pinholes are through-film voids from trapped solvent or air.
  Inclusions are foreign matter caught in a wet film. Contamination is
  material on or under the coat that was never meant to be there.
- The families carry different consequences and therefore different
  dispositions. A run is cosmetic-to-mechanical and reworks locally. A
  pinhole population is a barrier failure and takes the coat off. Silicone or
  release-agent contamination usually takes the coat off too, because the
  next coat will not wet over it.
- Allowances are not a property of the defect alone; they are a property of
  the defect on that surface. The same pinhole count is unremarkable on an
  internal structural panel, marginal on a thermo-optical control surface,
  tight on a bonding or electrical contact face, and not allowed at all on an
  optical face.
- Two independent criteria apply to each family: an individual size limit and
  a density limit over the inspected area. A single large defect and a fine
  scatter of small ones fail for different reasons, and reporting only a
  count hides the first while reporting only a worst case hides the second.
- The lot carries the worst disposition present on it. Averaging or majority
  voting across defects loses the one that governs, which is the whole point
  of the roll-up.

## Workflow

1. Validate the inspection record: a positive inspected area, a known family
   and surface category per defect, an integer count of at least one, and a
   non-negative size.
2. Look up the family's structural-surface allowances and scale both of them
   by the surface category factor, so an optical face keeps none.
3. Form the areal density of each defect from its count over the inspected
   area and grade it against the scaled density limit; grade its size against
   the scaled size limit independently.
4. Map a breach to the family's disposition, then escalate to a referral when
   the surface is optical. Keep the size breach and the density breach as
   separate findings.
5. Group the counts by family, form the total density, and roll the
   per-defect dispositions up to the worst one on the lot.
6. Return the disposition with the per-defect records and every finding
   named, so the reason a coat is coming off is visible without re-deriving
   it.

## Pitfalls

- Reporting a defect count without the inspected area. A count is not a
  density, and the acceptance criterion is a density, so a count alone cannot
  be graded at all.
- Grading a defect against a single tree-wide limit. The allowance depends on
  the surface, and a panel limit applied to a radiator or an optical face
  passes work that should have been stopped.
- Collapsing the size and density criteria into one verdict. They fail
  independently; a coat can be inside every size limit and still be a barrier
  failure on density.
- Reworking locally over contamination. Local rework leaves the contaminant
  under the repair, and the repair then delaminates in the same place, so the
  family's disposition is deliberately not negotiable per defect.
- Taking the average or the most common disposition across the lot. The worst
  one governs; anything else lets one referral-grade defect ship inside a
  population of accepted ones.

## Behavior contract (gate 3)

The record validation, family and surface lookups, the surface-scaled size
and density allowances, the independent size and density grading, the
optical-face escalation, the family roll-up and the worst-disposition
selection are exercised by the gate 3 contract test:
scripts/test_q7031_paint_defect_control.py against
scripts/q7031_paint_defect_control_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7031_paint_defect_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
