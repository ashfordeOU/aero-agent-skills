---
name: e2006-charging-protection-programme
description: "Use when plan the spacecraft-charging protection programme required by ECSS-E-ST-20-06C clause 5: score an early charging-hazard assessment for each item from its orbital-environment severity, its surface-exposure kind and its exposed area, categorize the electrostatic-discharge risk into a band, derive the mitigation measures and the verification-method set that band demands, compare the planned project-review milestone against the latest acceptable one, and report every item with no plan entry, an uncovered measure or a late milestone. Trigger: ecss, e-st-20-06c, charging-hazard-assessment, charging-mitigation-plan, verification-method-assignment, electrostatic-discharge-risk, protection-programme-milestones, spacecraft-charging-protection."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-charging-protection-programme, e-st-20-06c, charging-hazard-assessment, charging-mitigation-plan, verification-method-assignment, electrostatic-discharge-risk, protection-programme-milestones]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Protection Programme (space-systems/ecss/e2006-charging-protection-programme)

Use when the task is clause 5 of ECSS-E-ST-20-06C: standing up the
charging protection programme — an early hazard assessment per item, a
mitigation plan that follows from it, and closure of that plan through
measurement, inspection, testing and analysis booked against the right
project review.

## Domain quick reference

- The hazard of an item is not a property of the orbit alone. Three
  inputs combine: how energetic the charging drivers of the orbital
  environment are, how exposed the item is to the accumulating surface
  charge, and how much area is exposed. A geostationary orbit is the
  severe end of the first axis, an equatorial low orbit the benign end;
  an exposed dielectric is the severe end of the second, a shielded
  internal harness the benign end. The area contribution saturates:
  past roughly one square metre a larger surface adds little, while a
  very small patch pulls the index down markedly.
- The index is banded — negligible, low, significant, severe — and the
  band, not the raw number, drives the programme. A band edge is
  inclusive: an index that lands exactly on it belongs to the higher
  band, and an index a few units in the last place below the edge is
  still the higher band, because that difference is representation
  error and not engineering margin.
- Each band demands a set of mitigation measures and a set of
  verification methods. The severe band demands conductive surface
  treatment, grounding and bonding, and shielding or filtering, closed
  by all four verification methods including physical measurement. The
  negligible band demands no mitigation measure and closes by analysis
  alone. Extra measures beyond the demanded set are allowed; missing
  ones are findings.
- Timing is part of the requirement, not a project convenience. The
  hazard assessment is an early activity — for a severe item it is due
  at the first system review, so that the mitigation it drives can
  still change the design; the mitigation plan follows one review
  later, and verification closure lands by qualification or acceptance
  depending on the band. A milestone planned later than the latest
  acceptable one is a finding even when the activity is otherwise
  complete.

## Workflow

1. Inventory every item with an external or partially exposed surface.
   Capture its orbital environment, its exposure kind and its exposed
   area. Reject an unrecognized environment or exposure kind rather
   than defaulting it.
2. Score the hazard index for each item and categorize it into a risk
   band. Report the index alongside the band so a borderline item is
   visible.
3. Look the item up in the protection plan. An item with a non-
   negligible risk and no plan entry is a finding on its own — absence
   of an entry is not evidence of absence of hazard.
4. Compare the declared mitigation measures against the set the band
   demands and report the gap by name.
5. Compare the declared verification methods against the set the band
   demands. A severe item that closes on analysis alone, with no
   physical measurement, is the characteristic gap.
6. For each programme activity — hazard assessment, mitigation plan,
   verification closure — compare the planned project review against
   the latest acceptable one for that band. An unplanned activity and
   a late activity are both findings.
7. The programme is compliant only when every list is empty.

## Pitfalls

- Scoring the hazard from the orbit alone. Two items in the same orbit
  differ by an order of magnitude in exposure, and a blanket orbital
  categorization drags shielded internal hardware into the severe band
  while it hides a small exposed dielectric.
- Widening a band edge to make a borderline item pass. The edge is the
  engineering limit; the only thing the comparison absorbs is the
  floating-point error of the arithmetic that produced the index.
- Closing a severe item on analysis alone. The band demands physical
  evidence — measurement and inspection as well as testing — and a
  plan that lists only the desk method has not closed it.
- Booking the hazard assessment late. Its whole value is that it lands
  before the design is frozen; an assessment presented at the critical
  review can no longer drive the mitigation it recommends.
- Reading an item that is absent from the plan as unaffected. An
  unlisted item is an unassessed item and appears in the findings with
  its scored risk attached.

## Behavior contract (gate 3)

The hazard index, risk bands and their edges, mitigation and
verification coverage, milestone schedule check and aggregate
programme report are exercised by the gate 3 contract test:
scripts/test_e2006_charging_protection_programme.py against
scripts/e2006_charging_protection_programme_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_charging_protection_programme.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
