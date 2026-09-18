---
name: e2007-lightning-protection-verification
description: "Verify the system-level lightning protection case. Use when ECSS-E-ST-20-07C clause 5.3.4 asks how the required protection against lightning effects is confirmed: place every exposed surface in its attachment zone, derive the current waveform components that zone owes, refuse a closure argued by inspection or review-of-design inside an attachment zone, raise each measured circuit transient by its measurement uncertainty into a transient control level, take the decibel margin of the equipment design level over it, and close the case only when every declared zone is covered and every circuit holds its required margin. Trigger: ecss, e-st-20-07c, e-st-20-electrical-scope, lightning-protection-verification, lightning-attachment-zoning, lightning-transient-control-level, equipment-transient-design-level, lightning-protection-margin-db, direct-and-indirect-lightning-effects."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-lightning-protection-verification, lightning-attachment-zoning, lightning-transient-control-level, equipment-transient-design-level, lightning-protection-margin-db, direct-and-indirect-lightning-effects]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Lightning Protection Verification (space-systems/ecss/e2007-lightning-protection-verification)

Use when the task is the system-level lightning protection verification
of ECSS-E-ST-20-07C clause 5.3.4 — showing that the protection the
system was required to have is the protection it demonstrably has,
across both the direct effects of an arc on a surface and the indirect
transients the same stroke drives into internal circuits.

## Domain quick reference

- Verification starts from zoning, not from hardware. Every exposed
  surface sits in an attachment zone, and the zone fixes which current
  waveform components the surface has to survive: an initial-attachment
  zone owes the first return stroke, a swept-stroke zone does not, and a
  zone with arc dwell owes the full continuing current where a low-dwell
  zone owes only a shortened one. A conduction-only region sees no arc
  root at all and owes conducted current instead.
- The admissible verification method follows the zone, not the
  convenience of the programme. Inside an attachment zone the only
  evidence of arc survival is arc current — a test, or similarity to
  hardware already tested at the same components. Analysis may argue a
  conduction-only region, where the physics is a current path and not an
  arc root. Inspection and review-of-design record configuration; they
  are not evidence of survival and never close a direct-effects
  requirement on their own.
- Indirect effects are verified as a level comparison. The transient
  actually induced on a circuit is measured, then raised by the
  measurement uncertainty of the setup to give the transient control
  level that the design has to be judged against. Applying the raw
  measured value instead quietly spends the uncertainty as margin.
- The margin is the decibel ratio of the equipment transient design
  level to that control level. It runs through a base-ten logarithm,
  which is not correctly rounded and does not round identically on every
  platform, so an exactly compliant circuit can land a unit in the last
  place on the wrong side of the requirement. That is absorbed by a
  named tolerance inside the comparison.
- The system verdict is not an average. One uncovered zone, one surface
  closed by an inadmissible method, or one circuit short of its margin
  keeps the case open, because the vehicle is protected as a whole or
  not at all.

## Workflow

1. Resolve every declared attachment zone and effect kind against the
   recognised sets; refuse an unrecognised zone rather than mapping it
   onto the nearest one.
2. For each exposed surface, derive the waveform components its zone
   owes and the methods admissible for that zone and effect kind.
3. Mark a surface closed only when at least one declared method is
   admissible; record the admissible set alongside the verdict so a
   refusal is auditable.
4. For each victim circuit, raise the measured transient by the
   measurement uncertainty to obtain the transient control level.
5. Compute the decibel margin of the equipment transient design level
   over that control level, and compare it with the required margin
   under an explicit tolerance.
6. Compare the set of zones actually covered by surfaces with the set of
   zones the vehicle declares, and record every zone left unverified.
7. Report the per-surface closures, the per-circuit margins, the worst
   circuit, and the finding list; the protection case closes only when
   that list is empty.

## Pitfalls

- Closing an attachment-zone surface by inspection because the
  protection hardware is visibly installed. Presence is not survival;
  inside an attachment zone the evidence has to be arc current.
- Judging the design against the raw measured transient. The
  measurement uncertainty belongs on the stress side, so omitting it
  moves uncertainty silently into the margin the design is credited
  with.
- Zoning only the obvious extremities. A zone the vehicle declares but
  no surface record covers is unverified, and that gap is a finding in
  its own right rather than an implied pass.
- Deciding an exactly-at-limit margin with a bare inequality. The margin
  is a logarithm of a ratio, so an exactly compliant circuit can fall a
  unit in the last place below the requirement on one platform and not
  on another. Absorb it in the comparison, never by lowering the
  required margin.
- Reporting the mean margin across circuits as the system margin. The
  driving case is the worst circuit; averaging hides exactly the circuit
  the verification exists to find.

## Behavior contract (gate 3)

The attachment zoning, waveform-component derivation, method
admissibility, transient-control-level derivation, decibel-margin
comparison, zone-coverage check and system verdict are exercised by the
gate 3 contract test:
`scripts/test_e2007_lightning_protection_verification.py` against
`scripts/e2007_lightning_protection_verification_logic.py` (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_lightning_protection_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
