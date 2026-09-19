---
name: q20-coc-example
description: "Draft and grade a certificate of conformity against the worked example of ECSS-Q-ST-20C Annex H, taken as the standard sheet format: hold the printed block order, name every mandatory block left blank as one finding, parse each serial range into a prefix, a first and a last serial at one padded width, refuse a mixed prefix or a backwards range, report two ranges covering the same serial, reconcile the serials covered with the declared quantity, rebuild the certificate number from the contract reference and the sheet sequence, and refuse a sheet dated after the day it is presented. Use when a certificate is raised or checked on receipt. Trigger: ecss, q-st-20c-annex-h, certificate-of-conformity-format, coc-block-order, coc-serial-range-arithmetic, coc-number-pattern, coc-issue-date-check."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-coc-example, certificate-of-conformity-sheet-format, coc-block-order, coc-serial-range-arithmetic, coc-number-pattern, coc-issue-date-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Certificate Of Conformity Sheet Format (space-systems/ecss/q20-coc-example)

Use when the task is the Annex H worked certificate of ECSS-Q-ST-20C taken
as the standard sheet format: a certificate is being raised for a delivery
or opened on receipt, and the question is whether the sheet in front of you
is laid out, numbered and dated the way every other one is.

## Domain quick reference

- Format is not cosmetic on a certificate. A receiving organisation reads
  hundreds of these and finds each block by position, so a sheet that
  reorders or renames its blocks costs reading time on every delivery and
  hides an omission in the noise.
- The blanks are reported together. One finding naming every mandatory
  block left empty is actionable; one finding per block buries the sheet
  under a list nobody triages.
- Serial ranges are arithmetic and the quantity is a second statement of
  the same arithmetic. Six serials printed as a range and a quantity of
  five is a delivery where somebody pulled an item and forgot the sheet,
  and summing the ranges is the only thing that catches it.
- A range has one prefix and one padded width. A range printed across two
  prefixes, or padded to two widths, or running backwards, does not
  identify a set of items at all, and guessing what was meant is how the
  wrong hardware travels under the right paperwork.
- Two ranges covering one serial is a different defect from a quantity
  mismatch, and the two can cancel. A sheet whose overlapping ranges add up
  to the declared quantity passes a count check and still certifies one
  item twice.
- The certificate number is derived, not typed. Building it from the
  contract reference and the sheet sequence and comparing it with what is
  printed catches the sheet that was copied from the previous delivery.
- A sheet cannot be dated after the day it is presented. That is the
  cheapest date check on the page and the one that catches a template
  carrying somebody else's date.

## Workflow

1. Normalise the sheet block by block in the fixed order, collecting the
   mandatory ones left blank rather than failing at the first.
2. Validate the quantity as a positive integer and the issue date as an ISO
   calendar day, leap years included.
3. Parse each declared serial range into prefix, first, last and padded
   width, refusing a mixed prefix, an inconsistent padding or an inverted
   range.
4. Report ranges of the same prefix that cover a serial twice.
5. Sum the serials covered and compare with the declared quantity; where no
   range is printed, report a declared quantity above one.
6. Rebuild the certificate number from the contract reference and the sheet
   sequence and compare it with the printed number.
7. Compare the issue date with the presentation day, render the sheet in
   block order and return the verdict.

## Pitfalls

- Reading the quantity without the ranges. The pair is the check; either
  number alone is a figure somebody typed.
- Accepting a range because it looks like one. A mixed prefix or a mixed
  padding width is an identification failure, not a typographic one.
- Counting serials without checking for an overlap. Overlapping ranges can
  sum to exactly the declared quantity and still certify an item twice.
- Trusting the printed certificate number. It is derivable from the
  contract reference and the sequence, so it is checked rather than read.
- Failing at the first blank block. The useful output is every blank at
  once, because the sheet goes back to its author exactly once.

## Behavior contract (gate 3)

The block-order normalisation, the blanks collection, the ISO day parsing,
the serial-range parsing with its prefix, padding and direction rules, the
overlap detection, the quantity reconciliation, the certificate-number
rebuild and the issue-date comparison are exercised by the gate 3 contract
test: scripts/test_q20_coc_example.py against
scripts/q20_coc_example_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_coc_example.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
