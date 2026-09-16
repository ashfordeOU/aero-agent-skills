---
name: e2008-diode-contact-uniformity-test
description: "Use when a protection diode contact thickness map has to become a qualification uniformity verdict. Evaluate whether the contact metallisation of a protection diode holds an even thickness right across its land under ECSS-E-ST-20-08C clause 9.6.7: confirm the map reached every zone before a spread is quoted, hold the qualification run against its declared sample, take the spread and the variation against each contact's own mean, apply the local floor that an evenly thin deposit still fails, grade every site as uniform, thin, thick or bare, and leave a diode unsentenced while either polarity carries no map. Trigger: ecss, e-st-20-08c-clause-9-6-7, diode-contact-thickness-uniformity, diode-metallisation-zone-coverage, diode-thickness-spread-fraction, diode-local-thickness-floor, diode-uniformity-qualification-sample."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-diode-contact-uniformity-test, diode-contact-thickness-uniformity, diode-metallisation-zone-coverage, diode-thickness-spread-fraction, diode-local-thickness-floor, diode-uniformity-qualification-sample, diode-contact-thickness-site-map]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Diode Contact Uniformity Test (space-systems/ecss/e2008-diode-contact-uniformity-test)

Use when the task is the qualification check of ECSS-E-ST-20-08C clause
9.6.7 -- the metallisation deposited on a protection diode contact has
to hold an even thickness across the whole land, and a map of readings
has to become a verdict about the land rather than about the sites that
happened to be probed.

## Domain quick reference

- Coverage comes before any spread figure. A land probed three times
  near its middle returns a beautiful spread and describes the middle.
  The zones of the contact are enumerated first, and a contact missing
  a zone closes as not evaluated rather than being sentenced on the
  readings that do exist.
- The site count and the zone list are separate gates. Five readings
  clustered in one corner satisfy a count and fail a coverage, so both
  are checked and the coverage is the one usually missing.
- Uniformity is a spread about the contact's own mean. The absolute
  floor is a different question and is applied per site independently:
  a contact plated thin and plated evenly thin is perfectly uniform and
  still unweldable.
- The over-deposit ceiling sits on the other side for the same reason.
  A nodule is a local excess, and a mean taken over five sites absorbs
  it quietly enough that the spread never notices.
- The spread and the variation coefficient describe different defects
  and are both kept. The spread is driven by the two extreme sites and
  is where one thin corner appears; the variation coefficient describes
  the whole map and is where a land sloping gently across its width
  appears. Reporting only the better of the two is how a sloping
  deposit survives qualification.
- A diode has two contacts, one per polarity, and a verdict needs both.
  A polarity carrying no map is not a uniform polarity.
- The qualification sample has the same shape one level up. A run that
  mapped fewer devices than it declared has not qualified the
  population it speaks for, whatever the maps it did take say.

## Workflow

1. Validate the criteria set first: spread allowance, variation
   allowance, local thickness floor and ceiling, minimum sites per
   contact, required zone list and qualification sample floor. A band
   whose ceiling sits at or under its floor is refused rather than
   used.
2. Normalise each polarity contact and its map, refusing an empty map
   outright -- an empty map is not an even one.
3. Take the mean, the extremes, the spread fraction and the variation
   coefficient for each contact from its own readings.
4. Check the site count and the required zones. Either one short closes
   the contact as not evaluated, and both findings are reported.
5. Grade every site: under the local floor is bare, over the local
   ceiling is thick, otherwise the deviation from the contact mean
   against half the spread allowance. A value landing exactly on a
   bound passes; the comparison tolerance absorbs representation error
   and the bound itself does not move.
6. Apply the contact-level spread and variation allowances, which can
   send a contact to review on a map whose every site passed.
7. Roll up by severity rather than record order: the governing verdict
   per contact, then both polarities, then the run against its declared
   sample. Report every finding, not the first.

## Pitfalls

- Quoting a spread from readings that never reached the edge. The
  number is real and it describes the middle of the land.
- Treating the site count as the coverage check. Five readings in one
  corner pass the count and say nothing about the other four zones.
- Accepting an evenly thin contact because it is even. Uniformity and
  sufficiency are two separate questions and this clause is only one of
  them; the local floor is what keeps the other one asked.
- Letting the mean absorb a nodule. The local ceiling exists because an
  excess at one site averages away against four ordinary ones.
- Reporting the spread alone. A land sloping across its width holds a
  modest spread and a variation the spread never shows.
- Reporting the variation alone. One thin corner barely moves a
  variation taken over a whole map and moves the spread at once.
- Sentencing a diode on its anode map while the cathode was never
  probed.
- Closing a qualification on the devices that were mapped. The devices
  left unmapped have no reading at all, and a sample short of its own
  declaration was never the sample.
- Comparing a spread or a deviation against its allowance by bare
  arithmetic. Both come out of divisions that land a few units in the
  last place either side of a limit on different hosts, so the
  comparison absorbs that error while the allowance stays untouched.

## Behavior contract (gate 3)

The criteria validation, the map statistics, the zone coverage and site
count gates, the per-site grading against the floor, the ceiling and the
contact mean, the spread and variation allowances, the two-polarity
completeness rule and the declared-sample rule are exercised by the gate
3 contract test:
scripts/test_e2008_diode_contact_uniformity_test.py against
scripts/e2008_diode_contact_uniformity_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_diode_contact_uniformity_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
