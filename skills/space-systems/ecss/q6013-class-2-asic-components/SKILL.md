---
name: q6013-class-2-asic-components
description: "Evaluate a proposed tailoring of the dedicated ASIC assurance activities against what the intermediate assurance class of ECSS-Q-ST-60-13C clause 5.6.2 admits: route the declared device kind, refuse any reduction aimed at an activity the class holds mandatory, admit an approval-bearing reduction only where the named customer approval is on record and retain the activity otherwise, then compute the residual assurance coverage from the weights still standing and compare it with the declared floor, treating an exact equality as met. Reports every refused reduction and every outstanding approval. Use when a class 2 programme offers a reduced ASIC assurance scope. Trigger: ecss, q-st-60-13c-clause-5-6-2, class-two-asic-assurance-tailoring, mandatory-asic-activity-reduction-refusal, asic-reduction-customer-approval, residual-asic-assurance-coverage, asic-activity-assurance-weighting, catalogue-device-route-exclusion."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-2-asic-components, class-two-asic-assurance-tailoring, mandatory-asic-activity-reduction-refusal, asic-reduction-customer-approval, residual-asic-assurance-coverage, asic-activity-assurance-weighting, catalogue-device-route-exclusion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 ASIC Components (space-systems/ecss/q6013-class-2-asic-components)

Use when the task is the clause 5.6.2 disposal of ECSS-Q-ST-60-13C at the
intermediate assurance class: an application-specific device sits on a
class 2 parts list, the programme has proposed a lighter assurance scope
for it, and the question is which of those reductions the class actually
admits and what assurance is left standing once the refused ones go back.

## Domain quick reference

- The intermediate class changes the depth of the assurance work, not
  the route. An application-specific device still carries the dedicated
  ASIC assurance rules at class 2; what moves is how much of each
  activity the programme may leave undone, and on whose authority.
- A catalogue part is not reached by this clause at all. A standard
  microcircuit, a discrete or a passive stays on the generic component
  route however complex it is, and offering it a class 2 ASIC tailoring
  is a routing error rather than a lenient reading.
- Every dedicated activity carries one of three dispositions. Some are
  mandatory and no class 2 argument reduces them; some may be reduced
  only against a named customer approval; the rest the programme may
  reduce on its own authority. The disposition, not the saving, decides.
- An approval-bearing reduction with no approval on record is not a
  refusal and not an acceptance. The activity simply stays in scope and
  the missing approval is reported, so the programme can either obtain
  it or plan the work it thought it had dropped.
- Residual coverage is weighted, not counted. Dropping two light
  activities is not the same as dropping one heavy one, so the surviving
  assurance is the share of weight still standing and the floor is set
  against that share.
- A tailoring that clears every individual test can still fail on volume.
  Past the declared allowance the programme is not tailoring a scope, it
  is writing a different one, and the count is reported as its own
  finding rather than folded into the coverage number.

## Workflow

1. Read the declared device kind and route it. An unknown kind is an
   input error, not a device to guess at; a catalogue kind returns with
   the generic route and a note that this clause does not reach it.
2. Normalise the proposed reductions and the customer approvals into
   known activity names, refusing an unknown name and a repeated one,
   and put both lists into the standing report order.
3. Grade each proposed reduction by the disposition of its activity:
   mandatory goes to refused, approval-bearing without its approval goes
   to outstanding and the activity is retained, the rest are admitted.
4. Note any approval on record for an activity no reduction was proposed
   for, so a stale approval does not read as cover for something else.
5. Sum the weights of the admitted reductions, take the residual
   coverage as the share of total weight still standing, and compare it
   with the declared floor with an exact equality treated as met.
6. Compare the admitted reduction count with the declared allowance.
7. Return one verdict -- tailoring accepted, accepted with approvals, or
   refused -- with the refused reductions, the outstanding approvals,
   the retained activities, the residual coverage and every finding.

## Pitfalls

- Reading the intermediate class as a different route. It is the same
  dedicated ASIC assurance rule set at a different depth, so a device
  that would have gone to those rules at class 1 still goes there, and
  only the admissible reductions differ.
- Letting a saving argue for a reduction. The disposition of the
  activity decides whether it can be reduced at all; how much schedule
  or cost the reduction returns is not an input to that question.
- Treating a missing customer approval as a refusal. Refusing it hides
  that the reduction is available, and accepting it takes credit the
  programme has not been granted; the activity stays in scope and the
  approval is named as outstanding.
- Counting reductions instead of weighing them. Three light reductions
  can leave more assurance standing than one heavy one, and a count-only
  floor passes and fails the wrong tailorings.
- Loosening the coverage floor so a tailoring that lands exactly on it
  passes. An exact equality is a representation question the comparison
  already absorbs; a tailoring below the floor is below it.
- Folding the volume check into the coverage number. A tailoring can sit
  above the floor and still drop more activities than the class allows,
  and merging the two hides which of the two actually failed.

## Behavior contract (gate 3)

The kind routing, activity dispositions and weights, reduction grading,
approval handling, residual coverage, floor comparison, allowance cap
and verdict precedence are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_asic_components.py against
scripts/q6013_class_2_asic_components_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_asic_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
