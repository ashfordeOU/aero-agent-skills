---
name: e20-equipment-interchangeability-requirements
description: "Use when determine whether one space equipment item may replace another under ECSS-E-ST-20C clause 4.2.6: confirm both units carry the same part number and a revision declared form-fit-function neutral, categorize every recorded attribute as form, fit or function, grade numeric attributes against the declared interchangeability tolerance and discrete attributes on exact equality, report an attribute whose tolerance was never declared instead of passing it, check the candidate's qualification status ranks at or above the status the slot requires, reject a unit that drops in only after matched-set pairing or on-installation trimming, and screen a fleet down to the acceptable spares. Trigger: ecss, e-st-20-electrical-scope, equipment-interchangeability, form-fit-function-equivalence, part-number-identity, qualification-status-ranking, interchangeability-tolerance, matched-set-pairing, flight-spare-screening."
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
  tags: [ecss, e-st-20-electrical-scope, e20-equipment-interchangeability-requirements, form-fit-function-equivalence, part-number-identity, qualification-status-ranking, interchangeability-tolerance, matched-set-pairing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Equipment Interchangeability Requirements (space-systems/ecss/e20-equipment-interchangeability-requirements)

Use when the task is the interchangeability review of ECSS-E-ST-20C
clause 4.2.6 -- deciding whether a candidate equipment item can be
installed in the slot of another item of the same part number with no
selection, rework or re-adjustment, on the strength of form, fit and
function equivalence plus a qualification status that meets what the
slot demands.

## Domain quick reference

- Interchangeability is claimed within one part number. Two units with
  different part numbers are not interchangeable under this clause
  whatever their attributes say, and the comparison stops there. A
  different revision of the same part number is a narrower case: it
  passes only when the configuration record declares that revision
  form-fit-function neutral, otherwise the change is unassessed and the
  claim fails.
- The attributes split into three dimensions. Form is the physical
  article -- mass, envelope, centre-of-gravity offset. Fit is how it
  installs -- mounting hole pattern, mounting plane flatness, connector
  type and pinout, thermal interface finish, pigtail length. Function
  is what it does once installed -- electrical interface, consumption,
  output voltage, data protocol, firmware baseline. Sorting each
  attribute into its dimension is what makes a finding actionable: a
  fit finding goes to the mechanical interface, a function finding to
  the electrical one.
- Attributes compare in two different ways. A measurement is graded
  against a declared tolerance in percent of the reference value; a
  label -- pinout, protocol, connector type, firmware baseline -- is
  graded on exact equality and no tolerance applies to it. The case
  that hides is the numeric attribute with no declared tolerance: it
  has not been shown equivalent, only assumed equivalent, so the
  missing tolerance is itself a finding rather than a silent pass.
- Qualification status is ordered, not binary. A candidate fills a slot
  only when its status ranks at or above the status the slot requires,
  so an engineering model never fills a flight slot while a flight
  model can stand in for a lower requirement.
- Interchangeability is also an installation property. A unit that
  needs matched-set pairing with its neighbour, an on-installation trim,
  or a unit-specific calibration file loaded into the system is not
  interchangeable even when every attribute agrees -- the clause is
  about dropping a unit in, not about being able to make it work.

## Workflow

1. Record both units the same way: part number, revision and any
   neutrality declaration, qualification status, the attribute set, and
   the installation constraint flags. Record the tolerance declared for
   each numeric attribute and the qualification status the slot
   requires.
2. Compare configuration identity first. A part number difference ends
   the assessment as not interchangeable; a revision difference
   survives only against an explicit form-fit-function neutrality
   declaration.
3. Categorize every attribute on the reference unit as form, fit or
   function, and reject an attribute that fits none of the three rather
   than dropping it from the comparison.
4. For each attribute: flag it if the candidate does not record it at
   all; compare a label attribute for exact equality; compare a
   measurement against its declared tolerance and flag the deviation
   with its percentage; and flag a measurement whose tolerance was
   never declared.
5. Rank the candidate's qualification status against the slot
   requirement and flag a candidate that ranks below it.
6. Flag any installation constraint -- matched-set pairing,
   on-installation adjustment, unit-specific calibration data.
7. Aggregate the six groups. The candidate is interchangeable only when
   all of them are empty; screening a fleet of spares is the same test
   applied per unit, keeping exactly those that come back clean.

## Pitfalls

- Comparing attributes across part numbers and reporting "equivalent".
  The clause scopes interchangeability to one part number; an
  attribute-level match between two part numbers is a similarity
  statement, not an interchangeability verdict.
- Reading an absent tolerance as an unconstrained pass. Silence in the
  specification means the attribute was never shown equivalent, and
  reporting it is the only way the gap ever reaches the specification
  owner.
- Applying a percentage tolerance to a pinout, protocol or firmware
  baseline. Label attributes have no metric, and a numeric comparison
  on them either raises or, worse, passes on coincidence.
- Treating qualification status as a boolean qualified/not. The status
  is ordered and the comparison is against the slot's requirement, so
  both "engineering model in a flight slot" and its converse have to be
  answerable from the same ranking.
- Closing the claim on attribute equivalence while the unit still needs
  matched-set pairing or an on-installation trim. Those constraints are
  exactly what interchangeability excludes, and no attribute comparison
  will surface them.
- Letting a candidate that raises on a bad record quietly shrink the
  interchangeable set during a fleet screen -- a malformed unit is an
  error to fix, not a spare to discard.

## Behavior contract (gate 3)

The attribute categorization, relative-deviation and tolerance grading,
discrete-attribute matching, part-number and revision identity,
qualification-status ranking, installation screening, aggregated review
and fleet screen logic is exercised by the gate 3 contract test:
scripts/test_e20_equipment_interchangeability_requirements.py against
scripts/e20_equipment_interchangeability_requirements_logic.py (stdlib
unittest, offline). Run:
`python3 scripts/test_e20_equipment_interchangeability_requirements.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
