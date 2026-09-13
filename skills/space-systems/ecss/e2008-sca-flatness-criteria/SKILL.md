---
name: e2008-sca-flatness-criteria
description: "Evaluate a measured solar cell assembly deflection against the limiting value its geometry defines under ECSS-E-ST-20-08C clause 6.4.3.17.3: derive the limit from the assembly span with its floor and ceiling, resolve whether the governing limit is drawing-stated or geometry-derived, report a drawing limit sitting above the derived envelope, compare the guard-banded deflection so a result landing on the limit passes, separate a marginal sample from a clear one, and sentence the lot only when the subgroup is large enough. Use when dispositioning a cell assembly flatness record. Trigger: ecss, e-st-20-08c, clause-6-4-3-17-3, sca-flatness-limit-derivation, sca-deflection-limit-disposition, sca-flatness-drawing-limit-provenance, sca-flatness-marginal-result, sca-flatness-lot-sentencing."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-sca-flatness-criteria, sca-flatness-limit-derivation, sca-deflection-limit-disposition, sca-flatness-drawing-limit-provenance, sca-flatness-marginal-result, sca-flatness-lot-sentencing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Flatness Acceptance Criteria (space-systems/ecss/e2008-sca-flatness-criteria)

Use when the task is to disposition a measured cell assembly deflection under
ECSS-E-ST-20-08C clause 6.4.3.17.3 — establishing the limiting value the
geometry of the assembly defines, deciding which limit actually governs, and
sentencing the samples and the lot against it.

## Domain quick reference

- The limit is a function of the part, not a single number for the line. The
  same radius of curvature spends more standoff over a longer span, so a long
  assembly is allowed more deflection than a short one.
- A span term alone is not enough at either end. Below some standoff nothing
  is being measured except the tooling, so the limit needs a floor; and no
  assembly is allowed an unbounded standoff however long it is, because the
  panel stack height and the bond line run out, so the limit needs a ceiling.
- Which of the three terms binds is part of the answer. A limit held up by the
  floor and a limit set by the span behave differently when the geometry
  changes, and a reviewer needs to know which one is in force.
- A control drawing outranks the derived envelope. Where the drawing states a
  limit for the part, that limit governs and the derived value becomes a cross
  check rather than a competing answer.
- A drawing limit above the derived envelope is a decision, not an error. It is
  reported so somebody owns it, and it is never silently tightened back to the
  derived number.
- A measurement arrives with an uncertainty, so there are three outcomes and
  not two. A deflection whose whole guard band stays inside the limit is clear;
  one that is inside only if the instrument is believed exactly is marginal;
  one already over the limit is rejected.
- The boundary belongs to the passing side. A deflection landing exactly on its
  limit, or a guard band reaching exactly to it, is accepted; the comparison
  tolerance absorbs representation error rather than moving the limit.
- A subgroup is a sampling device. Too few samples read leaves the record
  unable to speak for the lot whatever it measured, which is a different
  outcome from a subgroup that was read and found wanting.

## Workflow

1. Validate the declared policy first: the span slope, the floor, the ceiling
   and the subgroup sample floor. A ceiling below the floor is refused rather
   than reordered, and an unrecognised key is refused rather than ignored.
2. Validate the assembly geometry: a positive length and width in millimetres.
3. Take the diagonal as the characteristic span, apply the slope, then hold the
   result between the floor and the ceiling and record which term bound it.
4. Resolve the governing limit: a drawing-stated value if there is one,
   otherwise the derived envelope. Raise a finding when the drawing-stated
   value sits above the derived envelope, and none when it sits on or below it.
5. Sentence each sample against the governing limit in order — rejected when
   the bare deflection is already over, accepted when the whole guard band
   stays at or under, marginal otherwise — and report the margin with it.
6. Sentence the lot: undersized outranks rejected, rejected outranks referred,
   and accepted is what is left.
7. Close with the governing limit, its provenance, the binding term, the worst
   guard-banded sample and every finding attached.

## Pitfalls

- Applying one flatness number to every assembly on the line. A short part and
  a long part do not carry the same allowance, and a single number is either
  unbuildable at one end or meaningless at the other.
- Deriving the limit from the span with no floor. A small assembly then gets a
  limit finer than the measurement itself, and the record reports the fixture.
- Deriving the limit from the span with no ceiling. A long assembly is then
  allowed a standoff the bond line and the stack height envelope cannot take.
- Letting the derived envelope override a control drawing. The drawing governs;
  the derived number is the cross check that makes a permissive drawing limit
  visible instead of invisible.
- Quietly tightening a drawing limit back to the derived envelope. That is a
  change to the acceptance criteria made by the reviewer rather than by the
  authority that owns the drawing.
- Sentencing on the bare deflection and dropping the uncertainty. A part that
  passes only if the instrument is believed exactly is a different disposition
  from one that passes whatever the instrument did.
- Treating a deflection landing exactly on the limit as a failure. The boundary
  belongs to the passing side and the tolerance belongs inside the comparison.
- Accepting a lot on a couple of samples. The sampling floor is its own
  condition and it outranks a good result.

## Behavior contract (gate 3)

The policy and geometry validation, the characteristic span, the derived limit
with its binding term, the governing-limit resolution and its provenance
finding, the three-way sample disposition and the lot verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_sca_flatness_criteria.py against
scripts/e2008_sca_flatness_criteria_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_sca_flatness_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
