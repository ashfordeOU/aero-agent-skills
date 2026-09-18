---
name: q6005-category-two-validation-general-rules
description: "Determine whether a category two validation of a hybrid supplier with no approved production line may proceed, and what range its result covers, under ECSS-Q-ST-60-05 clause 6.3.1. Use when the admissibility, scope and validity of an unapproved line must be decided rather than assumed: grade each entry condition on its own, refuse a line changed inside its stability window, bound the envelope to the families and package types actually examined, require all three validation elements to be planned, and return the readiness index with one verdict. Trigger: ecss, q-st-60-05, category-two-validation, unapproved-production-line, validation-entry-conditions, validation-scope-envelope, line-stability-window, category-two-validation-validity, category-two-validation-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-category-two-validation-general-rules, category-two-validation, unapproved-production-line, validation-entry-conditions, validation-scope-envelope, line-stability-window, category-two-validation-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Category Two Validation, General Rules (space-systems/ecss/q6005-category-two-validation-general-rules)

Use when the task is clause 6.3.1 of ECSS-Q-ST-60-05: the overarching
conditions and the scope that apply when a supplier holding no approved
production line is put through a validation — the part of the route that
decides whether the exercise may start at all and what its result is allowed
to say afterwards.

## Domain quick reference

- This route exists precisely because nothing about the line has been accepted
  in advance. That makes the entry conditions the whole of the admissibility
  argument rather than paperwork in front of it, and the conditions the route
  exists to check cannot be traded against the softer ones.
- The line has to have run unchanged for a declared stability window before
  the validation starts. A line changed inside that window is a different line
  from the one the evidence would describe, so the correct answer is that the
  validation is not admissible yet, not that it is admissible with a caveat.
- Scope is bounded by what was examined, never by what was declared. A
  technology family or a package type the supplier listed but the validation
  never looked at sits outside the envelope, and the envelope travels with the
  verdict so no later procurement reads the result as covering the catalogue.
- An examined item nobody declared is reported too. The result then speaks for
  material the procurement never asked about, which is a scope question in its
  own right rather than a bonus.
- Three elements make up the validation and they are planned together: the
  teardown construction analysis of sample units, the on-site quality and
  technical audit, and the evaluation testing. An element nobody planned makes
  the preconditions incomplete at any readiness index.
- The readiness index ranks what is outstanding. The validity period starts
  from the full term and is cut for each condition carried with a reservation,
  because a reservation is evidence the line moved once and may move again.

## Workflow

1. Name the supplier, the declared technology family and the product range the
   validation is meant to speak for, and reject a family this route does not
   cover.
2. Validate the entry-condition records: a condition appears once, an unknown
   condition name or state is an input error, and a condition nobody mentioned
   is graded as not assessed rather than quietly dropped.
3. Grade every condition against the full published set, marking the mandatory
   ones that came back unmet or unassessed.
4. Test line stability against the window, absorbing the boundary with a named
   tolerance instead of relaxing the window.
5. Split the declared range against the examined range into what sits inside
   the envelope, what was declared and never examined, and what was examined
   and never declared.
6. Check all three validation elements are planned; a missing one is an
   incompleteness, not a weighting.
7. Take the weighted credit over total weight as the readiness index, cut the
   validity term for each reservation, and name the verdict — preconditions
   incomplete while a mandatory condition or an element is short, not
   admissible on an unstable line, an out-of-route family, a low index or a
   term under the floor, admissible with reservations when findings remain,
   admissible only when none do.

## Pitfalls

- Reading the entry conditions as a cover sheet. On an unapproved line they
  are the argument; a validation that starts with one of them unmet has
  nothing underneath it.
- Letting a strong index carry an unstable line. The index averages across
  conditions, and line stability is a separate question the index cannot see.
- Issuing the result against the supplier's declared catalogue rather than the
  examined range. That is how a validation of two package types becomes a
  claim about a whole product family.
- Treating an examined item nobody declared as free coverage. It widens what
  the result says beyond what was asked for, and it is reported on its own.
- Planning two of the three elements and starting anyway. The teardown, the
  audit and the evaluation testing each answer a question the other two do
  not, so two of three is incomplete rather than partial.
- Carrying reservations forward at the full validity term. Each reservation is
  a reason the line may move again, and the term is what absorbs that.
- Re-using a validity term across a supplier's line move. The move is exactly
  the event the stability window and the term exist to catch.

## Behavior contract (gate 3)

The technology-family check, entry-condition grading, mandatory-condition
rule, readiness index, line-stability window, scope envelope, element coverage
and validity term are exercised by the gate 3 contract test:
scripts/test_q6005_category_two_validation_general_rules.py against
scripts/q6005_category_two_validation_general_rules_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_category_two_validation_general_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
