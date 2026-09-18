---
name: q7002-specimen-representativeness
description: "Assess the test item offered to an outgassing screening run. Use when coupons are on the balance bench under ECSS-Q-ST-70-02C and the question is whether they still stand for the flight material: hold each piece inside the per-specimen mass window, require the replicate count the screening needs, compare exposed area per unit mass with the flight part instead of accepting a thinner slice, name every process attribute that drifted from the flight build, and refuse a preconditioning soak whose hours, temperature or humidity left the declared band. Trigger: ecss, q-st-70-02c, outgassing-specimen-representativeness, outgassing-specimen-mass-window, outgassing-specimen-specific-surface-area, outgassing-specimen-preconditioning, outgassing-flight-material-state-deviation, outgassing-replicate-count."
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
  tags: [ecss, q-st-70-02-outgassing-scope, q7002-specimen-representativeness, outgassing-specimen-mass-window, outgassing-specimen-specific-surface-area, outgassing-specimen-preconditioning, outgassing-flight-material-state-deviation, outgassing-replicate-count]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening -- Test-Item Representativeness (space-systems/ecss/q7002-specimen-representativeness)

Use when the task is the test-item step of a thermal-vacuum outgassing
screening under ECSS-Q-ST-70-02C: coupons have been cut for a material and
the question is whether the pieces about to be weighed in represent the
material in the state it will fly in, and what has to be raised before they
are accepted.

## Domain quick reference

- The per-specimen mass window is not a convenience. It keeps the loaded
  compartment inside the effusion behaviour the collector geometry was built
  around, so a piece below or above the window changes what the collector
  sees, not just how much of it.
- A screening result belongs to a replicate set. One coupon reports one
  coupon; the replicate minimum is what turns a reading into a statement
  about a material, and a short set is a finding about the set rather than
  about any piece in it.
- Outgassing scales with exposed area, not with mass. Comparing exposed area
  per unit mass against the flight part is what catches a thin slice cut for
  convenience: same material, same lot, different specimen.
- Cure schedule, cleaning process, surface treatment and material lot each
  fix part of the flight state, so each is reported on its own. A run carries
  the state it was given, and an uncured or freshly solvent-wiped coupon
  reports that state rather than the one intended.
- The preconditioning soak sets what the initial weighing means. Hours,
  temperature and humidity are all part of it, and a soak outside any one of
  them leaves an unknown amount of absorbed water inside the initial mass.

## Workflow

1. Validate each coupon record and refuse a blank identifier, a non-positive
   mass or a non-positive exposed area rather than carrying it into the set.
2. Compare each mass with the method window, reporting a light piece and a
   heavy piece as different findings so the cut can be corrected in the right
   direction.
3. Form exposed area per unit mass for the coupon and for the flight part,
   take the signed relative departure, and raise a geometry finding only when
   it passes the declared allowance.
4. Compare the four process attributes against the flight build, matching
   values without regard to case or spacing, and name each attribute that
   moved instead of issuing one build verdict.
5. Grade the preconditioning soak on hours, temperature and humidity
   separately, so three departures give three findings.
6. Count the coupons against the replicate minimum, flag a repeated
   identifier, and accept the sample only when no coupon and no set-level
   check raised anything.

## Pitfalls

- Accepting a thin slice because the material and the lot are right. Exposed
  area per unit mass is what the run measures against, and a slice at twice
  the flight ratio outgasses like a different specimen.
- Reading the mass window as a target. A piece at the window edge is inside
  it; the finding is for a piece that left it, and the tolerance question at
  the edge is representation error, not an engineering allowance.
- Issuing one build verdict. Cure schedule, cleaning process, surface
  treatment and material lot answer different questions, and the
  nonconformance needs the one that actually moved.
- Weighing in after a short soak and correcting later. Absorbed water inside
  the initial mass cannot be separated from the material afterwards, so a
  short soak is refused before the weighing, not adjusted after it.
- Stopping at the first failing coupon. The bench is set up once, so every
  coupon and every set-level check is reported in one pass.

## Behavior contract (gate 3)

The mass window, specific surface area comparison, process-attribute
deviations, preconditioning soak grading, replicate count and the sample
acceptance decision are exercised by the gate 3 contract test:
scripts/test_q7002_specimen_representativeness.py against
scripts/q7002_specimen_representativeness_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7002_specimen_representativeness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
