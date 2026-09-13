---
name: e2007-external-unit-shielding
description: "Use when verify that every unit and cable run mounted outside the main-structure envelope carries its own individual shield under ECSS-E-ST-20-07C clause 4.2.12.2: categorize each inventory item by mounting-location and kind, derive the attenuation it needs from the local field-strength and its own field-susceptibility threshold, read the declared shield's measured attenuation-versus-frequency curve at the assessment frequency, derate that curve for braid-optical-coverage and for shield-termination technique (circumferential-backshell, partial-backshell, pigtail, unterminated), compare provided against required, and flag a shield-identifier credited to two externally-mounted items. Trigger: ecss, e-st-20-07c, externally-mounted-unit, external-cable-run, individual-shield, shielding-effectiveness-derate, braid-optical-coverage, shield-termination, pigtail-derate, main-structure-envelope."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-external-unit-shielding, externally-mounted-unit, external-cable-run, individual-shield, shielding-effectiveness-derate, shield-termination]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — External Unit Shielding (space-systems/ecss/e2007-external-unit-shielding)

Use when the task is the individual-shield check of ECSS-E-ST-20-07C
clause 4.2.12.2 -- confirming that each unit and each cable run
carried outside the main-structure envelope has its own shield, and
that the shield attenuates enough at the assessment frequency once the
braid-optical-coverage and shield-termination derates are taken.

## Domain quick reference

- The clause is scoped by mounting location. Hardware inside the
  main-structure envelope is already enclosed by the primary structure
  and its conductive skin, so it is out of scope here; hardware
  outside that envelope -- an externally mounted unit, a cable run
  crossing an appendage, a boom-mounted sensor -- sits directly in the
  incident field and must bring its own shield. Categorizing by
  location first is what keeps the assessment honest: an item is
  either an external-unit, an external-cable-run, or out of scope.
- Required attenuation is not a fixed number, it is the gap between
  the local field-strength and the item's own field-susceptibility
  threshold, expressed in decibels as twenty times the base-ten
  logarithm of their ratio. An item whose threshold already exceeds
  the incident field needs no attenuation, and the requirement floors
  at zero rather than going negative.
- Provided attenuation starts from the shield's measured
  attenuation-versus-frequency curve, read at the assessment
  frequency. A measured curve is a handful of points, so the value in
  between is interpolated linearly against the base-ten logarithm of
  frequency, and outside the measured span the nearest endpoint is
  held rather than extrapolated.
- Two derates then reduce that measured value. Braid-optical-coverage
  below the reference value leaks through the braid apertures and
  costs a penalty linear in the coverage gap. The shield-termination
  technique costs more: a circumferential backshell keeps the measured
  performance, a partial backshell costs a fixed penalty, a pigtail
  costs a large one because the pigtail wire puts an inductance in the
  return path, and an unterminated shield is credited with nothing at
  all.
- "Individual" is a real requirement, not a wording flourish. One
  shield identifier credited to two externally mounted items means the
  two share a return path and an aperture set; the clause asks for a
  shield per item, so a shared identifier is a finding regardless of
  how much attenuation it provides.

## Workflow

1. Inventory every unit and cable run in the electromagnetic-effects
   baseline with its mounting location, its kind, and its
   field-susceptibility threshold. Reject an unknown location or an
   unknown kind before it enters the assessment.
2. Categorize each item. Drop the items inside the main-structure
   envelope from the numeric check and count them as out of scope;
   keep the external-unit and external-cable-run items.
3. For each in-scope item, compute the required attenuation from the
   local field-strength and the item's threshold.
4. For each in-scope item, read the declared shield's measured curve
   at the assessment frequency, subtract the braid-optical-coverage
   derate and the shield-termination derate, and floor the result at
   zero. An item with no declared shield is a finding on its own and
   needs no further arithmetic.
5. Record the margin as provided minus required. Treat a margin that
   is negative only by the decibel-subtraction representation error as
   satisfied -- the named tolerance absorbs it, the engineering limit
   is never widened.
6. Cross-check shield identifiers across the in-scope items and flag
   every item whose shield is shared. The inventory is compliant only
   when no item carries a shortfall, a missing shield, or a shared
   shield.

## Pitfalls

- Crediting the primary structure to an externally mounted unit --
  the item sits outside that enclosure, which is the whole reason the
  clause exists; only the item's own shield counts.
- Reading the measured curve at the wrong frequency, or extrapolating
  past the measured span. A shield curve outside its measured range is
  unknown, and holding the endpoint is the defensible reading.
- Taking the braid-optical-coverage derate and forgetting the
  shield-termination derate. Termination usually dominates: a superb
  braid ended in a pigtail performs far worse than a modest braid on
  a circumferential backshell.
- Reading a large attenuation figure as compliance when the shield is
  shared between two externally mounted items -- individuality is a
  separate finding, and a shared shield fails even with margin to
  spare.
- Letting an unterminated shield inherit its measured attenuation. An
  open-ended shield is a conductor, not an enclosure, and must be
  credited with zero until it is terminated.

## Behavior contract (gate 3)

The item-categorization, curve-interpolation, coverage and termination
derate, required-attenuation, margin and shield-individuality logic is
exercised by the gate 3 contract test:
scripts/test_e2007_external_unit_shielding.py against
scripts/e2007_external_unit_shielding_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2007_external_unit_shielding.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
