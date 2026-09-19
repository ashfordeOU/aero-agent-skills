---
name: e2040-preliminary-escc-detail-specification
description: "Assess the preliminary ESCC detail specification a device owes at the close of layout under ECSS-E-ST-20-40C clause 5.6.7. Use when the task is deciding whether a device routed towards formal part evaluation owes an early component specification at all, confirming the draft carries every content block a procurement specification needs, checking each electrical characteristic is stated with a bound, a test condition and a temperature, verifying the recommended operating range sits inside the absolute maximum ratings, and reporting a readiness fraction with the blocks still open. Trigger: ecss, e-st-20-40c, preliminary-escc-detail-specification, device-evaluation-route, escc-content-block-readiness, absolute-maximum-rating-envelope, recommended-operating-condition-range, device-characteristic-test-condition."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-preliminary-escc-detail-specification, preliminary-escc-detail-specification, device-evaluation-route, escc-content-block-readiness, absolute-maximum-rating-envelope, device-characteristic-test-condition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Preliminary ESCC Detail Specification (space-systems/ecss/e2040-preliminary-escc-detail-specification)

Use when the task is the early component specification of
ECSS-E-ST-20-40C clause 5.6.7 -- deciding whether the device being
developed is on a route that owes one, and grading the draft produced
at the end of layout against what a procurement-grade specification has
to contain.

## Domain quick reference

- The obligation is conditional, not universal. A device headed for
  formal evaluation and a catalogue entry owes an early component
  specification; one built for a single application, or delivered as
  soft intellectual property with no package at all, does not. Writing
  the document for a device that never enters evaluation costs a phase;
  omitting it for one that does costs the evaluation slot.
- It is called preliminary because the numbers are layout-extracted
  rather than measured, but its structure is already final. Every block
  a buyer reads -- identification and variants, terminal assignment,
  absolute maximum ratings, recommended operating conditions,
  electrical characteristics, the test and screening list, marking and
  the package outline -- has to be present in the draft, because a
  block added later changes what was evaluated.
- A characteristic without a bound is a description, not a
  specification. Each entry needs a limit and the direction it bounds,
  the condition it was obtained under, and the temperature that
  condition applies at. Any one of the three missing makes the number
  unreproducible by the evaluation house.
- Absolute maximum ratings and recommended operating conditions are
  different envelopes and the second must sit strictly inside the
  first. A recommended range that reaches or crosses an absolute
  maximum specifies normal operation at a destruction limit.
- Readiness is a fraction of the required blocks, reported with the
  open ones named. A page count rises with prose and says nothing about
  whether the buyer can procure against the document.

## Workflow

1. Decide whether the specification is owed: an evaluation-bound,
   packaged device owes one; an application-specific device or a
   delivered-as-source core does not. Record the reason either way so
   the decision is reviewable rather than inferred from absence.
2. When it is not owed, stop and report that, with no readiness
   fraction implied; an absent document that was never owed is not a
   gap.
3. Validate the draft: identifier, device kind, route, and a block map
   naming each required content block as present, drafted or absent.
   Reject an unknown block name rather than counting it.
4. Validate each electrical characteristic: identifier, bound
   direction, limit value, unit, test condition and temperature.
   Reject a non-finite limit, and record a missing condition or
   temperature as a finding rather than a validation error, because the
   draft is expected to be incomplete and has to be reportable.
5. Check the rating envelope: for every parameter with both an absolute
   maximum pair and a recommended operating pair, confirm the operating
   minimum is above the absolute minimum and the operating maximum is
   below the absolute maximum, using a named relative tolerance so an
   exactly coincident bound is reported as coincident rather than as a
   rounding artefact.
6. Compute readiness as present blocks over required blocks and list
   every block that is drafted or absent.
7. Report the owed decision, the readiness fraction, the characteristic
   findings, the envelope findings, and whether the draft is fit to go
   into the layout phase review.

## Pitfalls

- Producing the specification for every device. The trigger is the
  evaluation route, and a document written for an application-specific
  device is a deliverable nobody procures against.
- Treating preliminary as provisional in structure. The numbers move
  before qualification; the block list does not, and a block introduced
  after evaluation invalidates what was evaluated.
- Listing a characteristic with a limit and no test condition. The
  evaluation house cannot reproduce the number, so it cannot confirm
  the limit, and the entry is evidence of nothing.
- Setting a recommended operating maximum equal to the absolute maximum
  rating. The recommended envelope has to sit inside the destruction
  envelope with room in it, and equality is the boundary case that is
  reported rather than passed.
- Reporting document length as progress. Readiness is the fraction of
  required blocks actually present, and prose does not move it.

## Behavior contract (gate 3)

The owed-decision, block-map validation, characteristic completeness,
absolute-maximum envelope check, readiness fraction and draft
aggregation are exercised by the gate 3 contract test:
scripts/test_e2040_preliminary_escc_detail_specification.py against
scripts/e2040_preliminary_escc_detail_specification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_preliminary_escc_detail_specification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
