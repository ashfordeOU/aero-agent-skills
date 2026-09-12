---
name: e20-charging-protection-programme-applicability
description: "Use when determine whether a spacecraft owes a charging protection programme under ECSS-E-ST-20C clause 6.3.4.1 and whether the one on record is complete and agreed in time: map the mission orbit onto its charging environment regime, collect the drivers that make the programme applicable including bus voltage, exposed external dielectric area, cumulative exposure and any ungrounded conductive element, derive the section list those drivers demand, report every section the programme does not carry, and check that customer approval sits at a project milestone ahead of the preliminary design review with the required calendar lead. Trigger: ecss, e-st-20-electrical-scope, e-st-20c-clause-6-3-4-1, charging-protection-programme, spacecraft-charging-applicability, internal-charging-analysis-section, esd-design-rules, customer-approval-before-pdr, project-milestone-lead-time."
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
  tags: [ecss, e-st-20-electrical-scope, e20-charging-protection-programme-applicability, charging-protection-programme, spacecraft-charging-applicability, internal-charging-analysis-section, esd-design-rules, customer-approval-before-pdr, project-milestone-lead-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Charging Protection Programme Applicability (space-systems/ecss/e20-charging-protection-programme-applicability)

Use when the task is the clause 6.3.4.1 charging protection programme
of ECSS-E-ST-20C -- deciding whether the mission needs one, working
out what has to be inside it, and confirming the customer agreed to it
early enough in the project to still shape the design.

## Domain quick reference

- Applicability is driven, not assumed. The orbit sets a charging
  environment regime: geostationary and transfer orbits see both
  surface and internal charging, medium and belt-crossing orbits are
  internal-charging cases, polar and sun-synchronous orbits are
  auroral surface-charging cases, interplanetary and lunar orbits are
  moderate surface cases, and only a low equatorial orbit is benign.
  An orbit with no regime on record is rejected, because treating an
  unmapped orbit as benign is how a programme goes missing.
- Three further drivers apply on top of the regime. A bus or array
  voltage at or above the array-plasma interaction threshold makes the
  programme applicable in any orbit, including a benign one. A large
  exposed external dielectric fraction and a long cumulative exposure
  are drivers only where the regime is already non-benign -- dielectric
  area in a benign plasma is not a charging case. An ungrounded
  conductive element is a driver on its own, anywhere.
- The section list follows from the drivers. Every applicable mission
  owes the environment definition, surface charging analysis, ESD
  design rules, grounding and bonding scheme, material selection and
  surface treatment, verification and test plan, schedule and
  milestones, and responsibilities and interfaces. An internal-charging
  regime adds the internal charging analysis; the high-voltage driver
  adds the array-plasma interaction analysis. A mission with no driver
  at all still owes a written non-applicability justification -- a
  waiver has to be written down to exist.
- A section that appears as a heading with nothing under it is absent.
  The check treats an unset or empty entry exactly as it treats a
  section that was never listed.
- Approval has two independent parts: where it sits in the project
  review sequence, and how much calendar lead it has. A programme
  agreed at the preliminary design review itself is late, because the
  clause wants it to constrain the design being reviewed; and an
  approval placed at an earlier review but dated three days before it
  gives no time to act on the agreement. Both are checked, and the
  approval is only credited when the customer actually granted it.

## Workflow

1. Map the mission orbit onto its charging environment regime; reject
   an orbit that has none.
2. Collect the applicability drivers: the non-benign regime itself,
   bus or array voltage at or above the interaction threshold, exposed
   dielectric fraction and cumulative exposure in a non-benign regime,
   and any ungrounded conductive element.
3. If no driver stands, require the written non-applicability
   justification and stop -- there is no programme to approve.
4. Build the required section list from the base set plus the
   internal-charging and high-voltage additions the drivers call for.
5. Compare the programme on record against that list and report every
   section that is absent, unset or empty.
6. Place the customer approval milestone in the project review
   sequence and flag an approval at or after the preliminary design
   review.
7. Compute the calendar lead from the approval date to the review and
   flag a lead below the required minimum, then flag an approval that
   was recorded but never granted.
8. Aggregate the section and timing findings; the programme satisfies
   clause 6.3.4.1 only when both lists are empty.

## Pitfalls

- Reading a low-Earth orbit as automatically exempt. A high-voltage
  array or a single ungrounded conductive element makes the programme
  applicable regardless of how benign the ambient plasma is.
- Skipping the justification for a mission with no driver. The clause
  is satisfied by a written statement of non-applicability, not by an
  empty folder, and the absent statement is the finding.
- Counting a listed-but-unwritten section as delivered. An empty
  heading is exactly as useful as a missing one at the review.
- Approving the programme at the preliminary design review. The point
  of the deadline is that the agreed protection approach constrains
  the design that gets reviewed, so approval at the review is approval
  of a design that was never constrained by it.
- Checking only the milestone and not the date. An approval nominally
  at the system requirements review but signed days before the design
  review has the right label and none of the lead time.
- Omitting the internal charging analysis for a medium or belt-
  crossing orbit because no surface charging was expected there. The
  deep-dielectric case is the dominant one in those regimes.

## Behavior contract (gate 3)

The regime mapping, driver collection, required-section derivation,
missing-section, milestone-ordering and approval-lead logic is
exercised by the gate 3 contract test:
scripts/test_e20_charging_protection_programme_applicability.py against
scripts/e20_charging_protection_programme_applicability_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e20_charging_protection_programme_applicability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
