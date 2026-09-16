---
name: q6013-class-2-procurement-specification
description: "Use when a purchase specification must be judged fit to order against. Evaluate whether a controlled purchase specification holds the content the intermediate assurance class requires under ECSS-Q-ST-60-13C clause 5.3.2: refuse a document with no identifier, issue or approving authority, hold each parameter to a declared acceptance basis, accept a published-data basis only where the citation names a document and an issue, require a test condition and an ordered limit pair on an own-limit parameter, confirm the ordered limits and the ordered temperature range sit inside the published ones under a named tolerance, and allow a manufacturer standard flow only where the flow is named. Trigger: ecss, q-st-60-13c-clause-5-3-2, class-two-purchase-specification-content, parameter-acceptance-basis, published-data-citation-issue, ordered-temperature-range-containment, manufacturer-standard-flow-route."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-procurement-specification, q-st-60-13c-clause-5-3-2, class-two-purchase-specification-content, parameter-acceptance-basis, published-data-citation-issue, ordered-temperature-range-containment, manufacturer-standard-flow-route]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Procurement Specification (space-systems/ecss/q6013-class-2-procurement-specification)

Use when the task is the clause 5.3.2 content question of ECSS-Q-ST-60-13C at
the intermediate assurance class: a purchase specification has been drafted
for commercial electrical, electronic and electromechanical parts, and the
question is whether it holds enough for a purchase order to be placed against
it and a delivery to be dispositioned against it.

## Domain quick reference

- The purchase specification is the document the order invokes, so it has to
  be identifiable: an identifier, an issue and an approving authority. A draft
  with no issue cannot be cited on an order, because nobody can later say
  which text the delivery was bought under.
- Every parameter declares its acceptance basis. Either the specification
  fixes the parameter itself, with the test condition it is measured at and
  the limit pair it is measured against, or it defers to the manufacturer's
  published data. Both are legitimate at this class; which one applies decides
  what the specification has to carry for that parameter.
- The deferral is the content this class adds, and it is the one that is most
  easily faked. A published-data basis counts only where the citation names
  the document and its issue, and where that published data actually fixes a
  limit. A basis pointing at an unissued data sheet points at whatever the
  manufacturer says today, which is not an ordered limit.
- An own-limit parameter carries both halves. A limit with no test condition
  is untestable, a condition with no limit is undispositionable, and either
  alone reaches the delivery review as an argument rather than a verdict.
- The purchase may tighten a published limit; it may never loosen one. Buying
  to a wider window than the manufacturer publishes orders parts the
  manufacturer never claimed, so the ordered bounds are compared against the
  published ones, with equality admissible under a named tolerance.
- Temperature is the same check in the axis that carries every other parameter
  with it. The ordered range has to sit inside the published one at both ends,
  and a range wider at both ends is two findings rather than one, because the
  hot end and the cold end fail for different physical reasons and are
  repaired separately.
- Acceptance needs a declared route, and this class offers three: every device
  screened, a lot acceptance sample whose accept number that sample can carry,
  or the manufacturer's own standard production flow. The third route is the
  class 2 addition and it counts only where the flow is named; an unnamed
  standard flow is whatever the maker was running that quarter.
- Coverage runs in both directions. Every part number on the order needs an
  entry, and an entry naming a part the order does not carry signals that the
  specification and the order have drifted apart.
- The share of parameters resting on published data is reported rather than
  judged. A specification leaning entirely on the data sheet is permitted here
  and is a different risk posture from one that fixes its own limits, and the
  reviewer needs to see which one they are holding.

## Workflow

1. Validate the specification header: identifier, issue and approving
   authority, each non-blank.
2. Validate the ordered part-number list and reject an empty order.
3. For each entry, validate the part number and every parameter: a name, a
   recognised acceptance basis, the test condition, the ordered limit pair,
   any published bounds and, for a deferred parameter, the citation.
4. Raise a finding for an own-limit parameter with no test condition and for
   one with no acceptance limit at all; raise a finding for a published-data
   parameter with no citation and for one whose published data fixes no limit.
5. Compare each ordered bound with its published bound, keeping both findings
   when both sides are loosened, and treating a dropped bound as a finding in
   its own right. Absorb representation error at an equal-limit boundary with
   a named tolerance rather than by relaxing the comparison.
6. Validate the ordered and published temperature ranges and raise a finding
   for each end the ordered range reaches beyond the published one; equality
   at an end is admissible under the same tolerance.
7. Validate the declared acceptance route per part, requiring the flow to be
   named where the manufacturer's standard flow is claimed, and raise a
   finding when no route is declared.
8. Reconcile the covered part numbers against the ordered ones in both
   directions, report the published-data share, and close on a verdict
   carrying every finding.

## Pitfalls

- Accepting an uncontrolled document. A specification with no issue is not
  invocable on an order; whichever revision the supplier happens to hold
  becomes the acceptance basis.
- Citing a data sheet with no issue. The deferral is permitted at this class,
  but the issue is what makes it an ordered limit rather than a pointer at a
  moving document.
- Deferring to published data that fixes no limit for the parameter. The entry
  then reads as covered while the delivery has nothing to be measured
  against.
- Ordering a bound wider than the published one to make an incoming lot pass.
  That buys parts outside anything the manufacturer characterized and cannot
  be recovered at the delivery review.
- Dropping a bound the published data fixes. An unbounded parameter reads as
  covered on the specification while accepting anything on delivery.
- Ordering a temperature range the published data does not cover. Every other
  parameter is stated over that range, so widening it silently invalidates the
  whole parameter set rather than one line of it.
- Claiming the manufacturer's standard flow without naming it. The flow then
  means whatever the maker was running that quarter, and two lots bought a
  year apart were bought against different acceptance.
- Writing a lot acceptance sample whose accept number reaches the sample size.
  Such a plan accepts every lot and only looks like sampling.
- Stopping at the first finding. The specification owner needs the whole list
  to close it in one revision rather than one revision per finding.

## Behavior contract (gate 3)

The header validation, citation validation, acceptance-basis handling, the
ordered limit pair validation, the limit-tightening comparison, the ordered
temperature range containment, the three acceptance routes, the two-way part
coverage, the published-data share and the fit-to-order verdict are exercised
by the gate 3 contract test:
scripts/test_q6013_class_2_procurement_specification.py against
scripts/q6013_class_2_procurement_specification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_procurement_specification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
