---
name: e2006-maximum-permitted-surface-voltage
description: "Use when derive the maximum permitted surface potential of an external spacecraft surface under ECSS-E-ST-20-06C clause 6.2.1: look up the material-family ceilings for absolute-surface-potential, differential-surface-potential and dielectric-breakdown-field, convert the field ceiling into the equivalent potential the dielectric-thickness allows, take the binding ceiling as the lower of the two, apply the mission safety-factor and any mission-specific override, compare the predicted worst-case surface potential and the internal-field it produces against that ceiling, and return the binding constraint, the remaining margin and a discharge-onset verdict per surface. Trigger: ecss-e-st-20-06c, clause-6-2-1, surface-potential-ceiling, dielectric-breakdown-field, differential-surface-potential, electrostatic-discharge-onset, discharge-inception-threshold, field-derived-potential-limit."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-maximum-permitted-surface-voltage, ecss-e-st-20-06c, surface-potential-ceiling, dielectric-breakdown-field, differential-surface-potential, electrostatic-discharge-onset, field-derived-potential-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Maximum Permitted Surface Potential (space-systems/ecss/e2006-maximum-permitted-surface-voltage)

Use when the task is fixing the ceiling that an external surface
potential must stay under per ECSS-E-ST-20-06C clause 6.2.1 -- the
critical-potential ceiling of the material family, the
dielectric-breakdown-field ceiling of the layer, and which of the two
actually binds for the thickness in front of you.

## Domain quick reference

- Clause 6.2.1 sets two ceilings, not one. The first is a
  critical-potential ceiling: above a certain differential-surface-potential
  a dielectric face will initiate a discharge to its neighbour more or
  less regardless of how thick it is, because the discharge path runs
  along the surface and across the triple-point where dielectric,
  conductor and vacuum meet. The second is a
  dielectric-breakdown-field ceiling on the field inside the layer.
- The two ceilings interact through thickness. The field-derived
  potential is the breakdown-field ceiling multiplied by the
  dielectric-thickness, so a thin layer is limited by its field and a
  thick layer is limited by the critical-potential of the material. The
  permitted potential is the lower of the two, and which one binds is
  itself a design finding worth reporting: thickening a
  field-limited layer buys margin, thickening a potential-limited one
  buys nothing.
- A mission safety-factor divides the binding ceiling. A mission may
  also impose its own override ceiling -- driven by a
  sensitive-payload susceptibility rather than by the material -- and
  the override only ever lowers the result; a mission cannot raise a
  material ceiling by declaring a larger number.
- The verdict is graded, not binary. A predicted potential far under
  the permitted ceiling is compliant; one approaching the ceiling is
  marginal and warrants an environment re-run or a design change; one
  at or above it is a discharge-onset case. Grade the ratio, and
  compare at the ceiling with a relative tolerance so a surface sitting
  exactly on the limit reads compliant -- the limit itself is never
  widened.

## Workflow

1. Identify the material family of the outer layer and pull its three
   ceilings: absolute-surface-potential, differential-surface-potential
   and dielectric-breakdown-field. Reject an unknown family rather than
   substituting a generic value, because the ceilings differ by more
   than an order of magnitude across families.
2. Convert the breakdown-field ceiling into a field-derived potential
   using the layer thickness. Reject a non-positive thickness.
3. Take the binding ceiling as the smaller of the field-derived
   potential and the differential-surface-potential ceiling, and record
   which of the two bound it.
4. Divide by the mission safety-factor (never below unity) and then
   apply any mission override by taking the smaller of the two. Record
   the override when it binds.
5. Compute the internal-field the predicted worst-case potential
   actually produces, and compare both the potential against the
   permitted ceiling and the field against the breakdown ceiling.
6. Grade the ratio of predicted potential to permitted potential into
   compliant, marginal or discharge-onset, and report the margin left.
   Reject a surface with no predicted potential on record: an ungraded
   surface is an open finding, not a pass.
7. Aggregate over the surface set; report the binding constraint mix
   and the worst surface, and hold the set non-compliant until every
   surface is graded and inside its ceiling.

## Pitfalls

- Applying only the field ceiling. A thick dielectric can sit far below
  its breakdown-field and still exceed the critical-potential at which
  a surface discharge starts, because that mechanism is driven by the
  potential difference along the surface, not by the bulk field.
- Applying only the potential ceiling. A very thin layer reaches its
  breakdown-field long before it reaches the material's
  critical-potential, so the field-derived ceiling is the binding one
  and must be computed from the real thickness.
- Reading a mission override as permission to exceed a material
  ceiling. An override can only tighten; taking the larger of the two
  produces a ceiling no material evidence supports.
- Using a safety-factor below unity to recover margin. That is not a
  factor, it is an exceedance with a different name.
- Treating a surface with no predicted potential as compliant because
  nothing exceeded anything. The comparison never ran, so the surface
  is unverified.

## Behavior contract (gate 3)

The material-ceiling lookup, field-derived-potential conversion,
binding-ceiling selection, safety-factor and override handling, and the
discharge-onset grading are exercised by the gate 3 contract test:
scripts/test_e2006_maximum_permitted_surface_voltage.py against
scripts/e2006_maximum_permitted_surface_voltage_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2006_maximum_permitted_surface_voltage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
