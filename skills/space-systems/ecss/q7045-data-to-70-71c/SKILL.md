---
name: q7045-data-to-70-71c
description: "Convert mechanical test results generated on metallic materials into entries the ECSS-Q-ST-70-71C materials data set will accept. Use when a laboratory batch has to be delivered into the programme data set: validate the metadata the data set keys on, bring ksi, gigapascal, Fahrenheit and percent readings onto one scale, bucket the test temperature so two measurements a fraction of a degree apart stay one population, group the entries by what actually makes them comparable, and report a group too thin to carry a design value. Trigger: ecss, q-st-70-45-metallic-mechanical-testing, materials-data-set-delivery, q-st-70-71c-data-interface, mechanical-property-unit-normalisation, test-temperature-bucketing, data-set-population-grouping."
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
  tags: [ecss, q-st-70-45-metallic-mechanical-testing, q7045-data-to-70-71c, materials-data-set-delivery, q-st-70-71c-data-interface, mechanical-property-unit-normalisation, test-temperature-bucketing, data-set-population-grouping]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Metallic Mechanical Testing — Data Delivery into 70-71C (space-systems/ecss/q7045-data-to-70-71c)

Use when the task is the data-set interface of ECSS-Q-ST-70-45: taking
mechanical property results off a laboratory batch and delivering them
into the materials data set of ECSS-Q-ST-70-71C in a form the data set
can actually group and use.

## Domain quick reference

- The data set keys on metadata, not on the number. A value with no
  material designation, product form, heat, condition, orientation and
  test temperature behind it cannot be compared with anything, so the
  metadata is mandatory and its absence is a rejection rather than a
  warning.
- Laboratories report in the units their machines print. A batch can
  carry MPa, N/mm2, GPa, ksi and psi for the same property, and degrees
  Celsius, Fahrenheit and kelvin for the same test temperature. The data
  set holds one scale, so conversion happens at the boundary and once.
- Elongation and reduction of area are strains, not stresses. Delivering
  them as percent into a field the data set reads as a ratio moves every
  value by two orders of magnitude and nothing downstream notices.
- Temperature enters the key through a bucket. Two pieces tested at 293
  and 294 K describe the same condition; keying on the raw value splits
  one population into two, and two thin populations support far less
  than one adequate one.
- The heat is carried on the entry and kept out of the key. Entries from
  different heats belong in the same population — that is what makes the
  population represent the material rather than one melt — while the
  heat still has to be recoverable for traceability.
- A group below the minimum entry count is delivered, not dropped. It is
  real data that has to reach the data set; what it is not yet is a
  population anything can be derived from, and saying so is the finding.
- One bad entry does not fail a batch. It is rejected with the reason
  that rejected it, the rest of the batch is delivered, and the batch
  verdict names both.

## Workflow

1. Check each entry against the mandatory metadata field set before
   looking at its value at all.
2. Take the quantity kind from the property, so a stress converts
   through the stress table and a strain through the strain table, and
   refuse a property the data set does not carry.
3. Convert the value into the data set unit and the test temperature
   into kelvin, refusing a temperature at or below absolute zero.
4. Bucket the temperature at the declared width and build the key from
   designation, form, condition, orientation, property and bucket.
5. Group the accepted entries by that key; record the distinct heats and
   the group mean, computed after conversion.
6. Report every group below the minimum entry count and every rejected
   entry with its reason, and mark the batch deliverable only when
   neither list has anything in it.

## Pitfalls

- Converting the value and leaving the temperature. A batch reported in
  MPa at 70 degrees Fahrenheit looks half-converted and keys into a
  bucket no other entry will ever land in.
- Keying on the raw temperature. It is the quietest way to turn one
  usable population into several unusable ones, and the group counts
  look plausible the whole time.
- Putting the heat in the key. Every heat then forms its own population,
  and a data set built from three heats reports three groups of one
  instead of one group of three.
- Delivering elongation in percent into a ratio field. Both numbers are
  dimensionless, so no unit check catches it and the value is simply
  wrong by a hundred.
- Raising on the first malformed entry. The batch is then delivered in
  pieces across several attempts, and nobody can tell which entries
  already landed.
- Suppressing a thin group to keep the batch clean. The data is owed to
  the data set regardless; what the finding controls is whether anything
  may yet be derived from it.

## Behavior contract (gate 3)

The mandatory metadata check, the stress, strain and temperature
conversions, the absolute-zero refusal, the temperature bucketing, the
key construction that keeps the heat out, the grouping with its
post-conversion mean and the per-entry rejection with batch-level
findings are exercised by the gate 3 contract test:
scripts/test_q7045_data_to_70_71c.py against
scripts/q7045_data_to_70_71c_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7045_data_to_70_71c.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
