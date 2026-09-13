---
name: e2006-internal-dielectric-field-limits
description: "Use when compute the electric field standing inside a solid insulating material and check it against the internal-dielectric-field cap of ECSS-E-ST-20-06C clause 9.2.3: derive the field from the applied potential and the insulator geometry -- planar wall thickness or coaxial inner and outer radii -- apply the material and temperature derating that the insulator is qualified for, then compare the derated field with the default internal-field cap unless a higher application-specific level is demonstrated by a qualification record naming the same insulating-material, covering the operating temperature and carrying test evidence. Flags missing thickness, unsupported higher levels and field exceedances. Trigger: ecss, e-st-20-electrical-scope, internal-dielectric-field, insulating-material, dielectric-field-cap, coaxial-field-gradient, temperature-derating, qualification-demonstration, internal-electrostatic-discharge."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-internal-dielectric-field-limits, internal-dielectric-field, insulating-material, dielectric-field-cap, coaxial-field-gradient, qualification-demonstration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Design -- Internal Dielectric Field Limits (space-systems/ecss/e2006-internal-dielectric-field-limits)

Use when the task is the clause 9.2.3 check of ECSS-E-ST-20-06C: the
electric field inside a solid insulating material stays under a stated
cap, and any design that wants to run above that cap carries a
qualification demonstration for that specific application rather than an
assertion.

## Domain quick reference

- The cap exists because a field sustained inside a bulk insulator ages
  it. Charge injected by penetrating radiation accumulates in the bulk,
  the internal field adds to the applied field, and the material
  eventually breaks down through its thickness -- an internal
  electrostatic discharge with a conductor on each side of it. Holding
  the applied field low is the design control that keeps the margin.
- The field depends on geometry, not only on voltage. A planar
  insulating wall carries a uniform field equal to the potential
  divided by the wall thickness. A coaxial insulator does not: the
  field peaks at the inner conductor and falls off logarithmically, so
  the governing number is the inner-radius gradient, and a thin inner
  conductor drives that gradient up even when the overall wall looks
  generous.
- Each insulating-material carries its own base cap, and each cap is
  qualified only up to a knee temperature. Above the knee the material
  softens, so the cap derates linearly toward its upper service
  temperature; running the insulator past that service temperature is
  outside the qualified envelope and is an error, not a derated pass.
- A higher application-specific level is allowed, but only against a
  demonstration record. That record has to name the same insulating
  material, cover the operating temperature of the item, carry a test
  evidence reference, and state a level above the derated default --
  a record that merely restates the default buys nothing and a record
  that names a different material or a narrower temperature band does
  not apply to this item.
- Compliance is the derated-or-demonstrated cap versus the computed
  field. The comparison absorbs the representation error of the
  division; a wall that sits exactly on its cap is compliant.

## Workflow

1. Categorize the insulating material against the qualified-material
   table. Reject an unrecognized material rather than assessing it
   against a guessed cap.
2. Compute the internal field from the geometry: potential divided by
   thickness for a planar wall, or the inner-radius gradient for a
   coaxial insulator. Reject a non-positive thickness, a non-positive
   inner radius, an outer radius that does not exceed the inner one,
   and a negative potential.
3. Derive the temperature derating factor for the material at the item
   operating temperature: unity up to the knee, falling linearly to
   the floor factor at the upper service temperature, and an error
   above it.
4. Multiply the material base cap by the derating factor to get the
   derated default cap.
5. If a demonstration record is offered, validate it -- same material,
   temperature covered, evidence reference present, level above the
   derated default -- and adopt its level as the cap; otherwise keep
   the derated default and record the basis as the default.
6. Compare field with cap, compute the utilization ratio and the
   margin, and report the item as compliant only when the field is at
   or below the cap. Roll a set of items up into a campaign verdict.

## Pitfalls

- Applying the planar potential-over-thickness formula to a coaxial
  insulator. The mean field it yields is always lower than the real
  inner-radius gradient, so the item reads compliant while the field
  at the inner conductor is the one that breaks the material down.
- Reading a demonstration record as permission without checking what
  it covers -- a record for a different material, or one whose
  temperature band stops below the item's operating point, does not
  raise the cap for this item and must be rejected outright.
- Taking a demonstrated level that sits at or under the derated
  default as a pass upgrade; it is not a higher level, and quietly
  adopting it hides the fact that the demonstration never supported
  the design point.
- Derating the cap for temperature and then forgetting it when the
  demonstration is applied, or vice versa -- the two paths must both
  start from the same derated baseline so the comparison is honest.
- Treating a field that lands a few units in the last place above the
  cap as an exceedance. The field is a quotient of floats; a wall that
  is physically at its limit stays compliant, and the tolerance sits
  in the comparison, never in the cap value.

## Behavior contract (gate 3)

The material categorization, planar and coaxial field computation,
temperature derating, demonstration-record validation and per-item
verdict logic is exercised by the gate 3 contract test:
scripts/test_e2006_internal_dielectric_field_limits.py against
scripts/e2006_internal_dielectric_field_limits_logic.py (stdlib
unittest, offline, deterministic). Run:
python3 scripts/test_e2006_internal_dielectric_field_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
