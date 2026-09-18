---
name: q6005-standard-marking-requirements
description: "Verify the information a delivered hybrid microcircuit carries on its package body and the durability its lettering has to keep, under ECSS-Q-ST-60-05 clause 10.2.1. Use when a body mark is graded against the standard content set: test every mandatory field for presence and for form, validate the lot date code and the serial number, size the character height against the body area, compute the mark-to-body contrast, weigh the solvent-resistance evidence and the legibility left after it, and return the marking-completeness index with one verdict. Trigger: ecss, q-st-60-05, hybrid-body-marking-fields, hybrid-lot-date-code-format, hybrid-marking-character-height, hybrid-marking-contrast-ratio, hybrid-marking-solvent-resistance, post-test-marking-legibility, hybrid-body-marking-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-standard-marking-requirements, hybrid-body-marking-fields, hybrid-lot-date-code-format, hybrid-marking-character-height, hybrid-marking-contrast-ratio, hybrid-marking-solvent-resistance, hybrid-body-marking-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Standard Marking Requirements (space-systems/ecss/q6005-standard-marking-requirements)

Use when the task is clause 10.2.1 of ECSS-Q-ST-60-05: the standard marking
requirements — what the body of a delivered hybrid actually carries, and how
hard-wearing that lettering has to be. The scheme that chose the method and
the placement is graded separately, under the general marking provisions.

## Domain quick reference

- The body mark is a fixed set of fields, not free text. A field that is
  absent and a field that is present in the wrong form are different failures:
  the first leaves the unit unidentified, the second leaves it identified as
  something else — and only the second is read and believed.
- The lot date code and the serial number carry the traceability, so their
  form is checked and not only their presence. A date code whose week does not
  exist points at no lot, and a serial built from characters that read alike
  by eye is a transcription error waiting in every incoming inspection.
- Character height is set by the body that has to carry it. A small package is
  allowed smaller lettering, but there is a height no package goes below, and
  a mark readable only under magnification is an open action even when it sits
  above that floor.
- Contrast is part of legibility. Lettering the same shade as the package is
  invisible whatever its height, so the mark-to-body reflectance ratio is
  judged alongside the geometry rather than left to the inspector's eye.
- Durability is demonstrated, not asserted. The evidence is an immersion of at
  least the required dwell in each of the required solutions, each followed by
  a legibility reading. Fewer exposures than required is an incomplete test,
  not a weaker pass; lettering lost after an exposure is a failure of the
  marking and not of the test.
- Fields beyond the mandatory set are graded only when the delivery calls for
  them. One the procurement never asked for is not a finding; one it did ask
  for and did not get is.

## Workflow

1. Name the unit and collect its body mark field by field, plus the fields
   beyond the mandatory set this particular delivery calls for.
2. Refuse a field the body mark has no place for, rather than grading an
   invented one alongside the standard set.
3. Grade each field in the applicable set: absent, present with a form
   finding, or present and valid — and keep the absent and malformed cases
   apart, because they fail the mark in different ways.
4. Validate the forms that carry the traceability: the four-figure date code
   and its week, the serial number's length and its look-alike characters, the
   manufacturer code and the part number character sets.
5. Take the minimum character height from the body area, compare the lettering
   with it under a named tolerance, and raise the magnification case as an
   open action rather than a failure.
6. Compute the mark-to-body reflectance ratio and compare it with the minimum
   contrast, absorbing the bound with the same tolerance.
7. Weigh the solvent-resistance evidence: one immersion of at least the
   required dwell in each required solution, and the legibility reading after
   each — short or missing exposures leave the test incomplete.
8. Take weighted credit over total weight as the marking-completeness index
   and name the verdict — incomplete while a mandatory field is absent or the
   durability test is short, not meeting requirements on a malformed mandatory
   field, lettering under the height floor, insufficient contrast, lost
   legibility or a low index, meeting them with open actions when findings
   remain, meeting them only when none do.

## Pitfalls

- Checking the mark for presence and stopping there. A complete mark in the
  wrong form is the one that gets transcribed into a build record, and the
  error is not found until the unit is traced back.
- Reading a date code as a number. It is a year and a week, and a week past
  the end of the calendar is a marking error however plausible the figures.
- Allowing look-alike characters in a serial because the printer supports
  them. The serial is read by eye at incoming inspection; the pair that reads
  alike is the pair that produces two histories for one unit.
- Sizing the lettering from the drawing rather than the body. The minimum
  height follows the area available, and a small package earns a smaller
  minimum, never an exemption from one.
- Judging legibility by height alone. Lettering the shade of the package fails
  at any height, which is why the contrast is measured and not assumed.
- Reading a short solvent test as a mild pass. A test missing a solution or an
  immersion has not demonstrated anything, and grading it as a weak result
  turns an untested mark into an accepted one.
- Treating a mark lost after solvent exposure as a test artefact. The unit
  will meet that solvent again in the assembly it is going into.

## Behavior contract (gate 3)

The applicable-field set, the field presence and form grading, the date-code
and serial validators, the character-height minimum, the contrast ratio, the
solvent-resistance durability assessment, the marking-completeness index and
the body-mark verdict are exercised by the gate 3 contract test:
scripts/test_q6005_standard_marking_requirements.py against
scripts/q6005_standard_marking_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_standard_marking_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
