---
name: q6005-category-two-non-approved-manufacturer
description: "Evaluate a non-approved hybrid maker against the less preferred category two route of ECSS-Q-ST-60-05 clause 5.2.2: test the customer justification for the elements that make it admissible, refuse one that steps past an available approved source without a stated reason, and grade the compensating conditions - audit currency, an agreed validation programme, baselined process documentation, current quality certification, added lot testing - that make such a maker acceptable. Use when a hybrid has only a non-approved source, when a justification goes to the customer, or when an audit ages out. Reports admissibility, unmet conditions and weighted coverage. Trigger: ecss, q-st-60-05c-clause-5-2-2, category-two-hybrid-manufacturer, non-approved-hybrid-source, hybrid-customer-justification, hybrid-compensating-conditions, hybrid-manufacturer-audit-validity."
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
  tags: [ecss, q-st-60-eee-scope, q6005-category-two-non-approved-manufacturer, category-two-hybrid-manufacturer, non-approved-hybrid-source, hybrid-customer-justification, hybrid-compensating-conditions, hybrid-manufacturer-audit-validity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Procurement — Category Two Non-Approved Manufacturer (space-systems/ecss/q6005-category-two-non-approved-manufacturer)

Use when the task is the clause 5.2.2 source decision of ECSS-Q-ST-60-05:
the hybrid maker on the table holds no line approval, so the preferred
route of clause 5.2.1 is not open. This route stays available, but it is
the less preferred one, and it is bought with two things — a justification
the customer agrees to, and a set of conditions that puts back the
assurance an approved line would have carried on its own.

## Domain quick reference

- The route is less preferred, not forbidden. A programme can use a maker
  with no approved line; what it cannot do is arrive there silently. The
  justification is the record of why the preferred route was not taken.
- A justification is admissible only with its whole element set: the
  statement that no approved source serves, what makes this maker
  technically necessary, the programme consequence of not using it, the
  risk assessment behind it, and the customer's agreement. Four of five is
  not a weaker justification; it is an incomplete one.
- Preference has teeth. An approved source that was actually available and
  was passed over with no stated exclusion reason invalidates the
  justification however well the rest of it reads — that is the whole
  content of calling one route preferred. An approved source excluded for
  a named reason, such as a package outside its approval scope, is not a
  bypass.
- The compensating conditions are what make such a maker acceptable: a
  manufacturer audit still inside its validity window with no open major
  findings, a validation programme agreed with the customer, baselined
  process documentation, a quality-system certification still in force,
  and the added lot-level testing that substitutes for line approval. They
  carry different shares of the assurance, so coverage is weighted, not a
  count.
- An audit is dated evidence. Past its validity window it no longer
  describes the line running today, and an audit dated after the
  assessment day is not evidence of anything yet.
- A near miss is reported as a near miss. With an admissible
  justification and coverage at or above the provisional share, the source
  is usable while the remaining condition is closed out; below it, the
  answer is no.

## Workflow

1. Validate the proposal and audit the justification element by element,
   returning the gap set and a completeness figure rather than a verdict.
2. Test the approved-source list for a bypass: any source flagged
   available with no stated exclusion reason is named, and one name is
   enough to make the justification inadmissible.
3. Grade each compensating condition against its own evidence — dates for
   the audit and the certification, an agreement flag for the rest — and
   record why an unmet one is unmet.
4. Sum the weighted coverage of the satisfied conditions. Compare it with
   the provisional share through a named tolerance, because the coverage
   is a sum of binary-represented shares and an exact landing can miss the
   bound by a few units in the last place.
5. Return one of three dispositions — acceptable, acceptable with open
   actions, not acceptable — plus every finding, so the supplier gets the
   whole list at once.

## Pitfalls

- Treating the justification as a formality to be attached after the
  order. It is the admissibility test; an element missing from it stops
  the route no matter how complete the conditions are.
- Letting a strong condition set outvote a bypassed approved source. The
  preference between the two routes is not a scoring input, and a
  bypassed available source blocks the proposal at full coverage.
- Counting conditions instead of weighting them. Closing the two lightest
  conditions and leaving the audit open is not the same assurance as the
  reverse, and a plain count hides that.
- Accepting an audit on its existence. Age against the validity window and
  the count of open major findings both decide it, and an audit dated
  after the assessment day decides nothing.
- Moving the provisional share to let a proposal through. An exact landing
  on the bound is a representation question, handled by the tolerance
  inside the comparison; the share itself stays as set.
- Reading a certification that expires on the assessment day as expired.
  The comparison is on whole days and zero days remaining is in force.

## Behavior contract (gate 3)

The justification audit, the approved-source bypass test, the per-condition
grading, the weighted coverage and the three-way disposition are exercised
by the gate 3 contract test:
scripts/test_q6005_category_two_non_approved_manufacturer.py against
scripts/q6005_category_two_non_approved_manufacturer_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_category_two_non_approved_manufacturer.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
