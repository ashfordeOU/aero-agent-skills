---
name: q60-class-3-screening-requirements
description: "Assess the screening a Class 3 lot owes before it is fitted to flight standard hardware. Use when a Class 3 lot is screened or its screening record is reviewed: decide from the destination whether flight screening is owed at all and whether a non-flight lot carries its marking, take the owed screen set from the package family, credit a manufacturer standard flow only where an evidence reference is actually cited and leave the rest owed to the project, name every screen still uncovered, confirm each stress precedes the measurement that judges it, convert a burn-in held off its reference temperature into equivalent hours, and compare the percent defective produced against the allowable. Trigger: ecss, ecss-q-st-60c-clause-6-3-3, class-3-screening-requirements, class-3-manufacturer-flow-credit, class-3-screening-sequence-order, class-3-burn-in-equivalent-hours, class-3-percent-defective-allowable, class-3-non-flight-lot-marking."
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
  tags: [ecss, q-st-60c-eee-parts-scope, q60-class-3-screening-requirements, ecss-q-st-60c-clause-6-3-3, class-3-screening-requirements, class-3-manufacturer-flow-credit, class-3-screening-sequence-order, class-3-burn-in-equivalent-hours, class-3-percent-defective-allowable, class-3-non-flight-lot-marking]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 3 EEE Parts — Screening Requirements (space-systems/ecss/q60-class-3-screening-requirements)

Use when the task is the screening duty of ECSS-Q-ST-60C clause 6.3.3 — the
screening regime a Class 3 part owes before it is fitted to flight standard
hardware, and what a lot going anywhere else owes instead.

## Domain quick reference

- The destination decides whether screening is owed at all. A lot going to
  ground support equipment, an engineering model or a breadboard owes the
  flight regime nothing — but it owes a marking, because an unmarked
  unscreened lot is exactly how such a part reaches flight hardware later.
- What is owed comes from the package family, because the failure mechanisms a
  screen addresses are properties of the package. A hermetic family owes a
  seal test; a plastic one has no seal to test and owes none.
- Much of the regime at this assurance category already sits inside the
  manufacturer's standard flow, and crediting it is legitimate. Credit is
  earned by an evidence reference, not by a claim. A claim citing nothing
  leaves the screen owed to the project, and it is reported twice over: once
  as an unsupported claim to chase, once as a screen still uncovered.
- Those two findings are deliberately separate. Chasing the evidence and
  running the screen are different repairs and cost different amounts.
- Each stress has to precede the electrical measurement that judges it. A
  measurement taken before the stress measured nothing about it, and the
  record ends with the final measurement or it ends nowhere.
- A burn-in held off its reference temperature is converted through an
  Arrhenius acceleration factor before it is compared with the reduced
  duration this category allows. A short hot run can be sufficient; a long
  cool one can fail. The comparison is on equivalent hours, never on the
  hours the oven log happens to show.
- A run landing exactly on the allowed duration is sufficient, absorbed with a
  named tolerance rather than by moving the bound.
- The percent defective the screening produced is compared with the allowable,
  and a lot on the bound is accepted.

## Workflow

1. Read the lot: identifier, declared assurance category, destination and
   package family.
2. Settle the destination first. A non-flight lot is checked only for its
   marking and the verdict says so.
3. Take the owed screen set from the package family.
4. Walk the screening record, crediting a manufacturer standard flow entry
   only where it cites an evidence reference, and naming every entry that
   does not.
5. Subtract what was credited from what is owed and name each remaining
   screen separately.
6. Check the record's order against the precedence, naming each pair that
   occurs the wrong way round.
7. Where burn-in is owed and credited, convert the run to equivalent hours
   through the Arrhenius factor and compare with the reduced duration.
8. Form the percent defective from the screened and rejected counts and
   compare it with the allowable.
9. Return a status per lot and a campaign-level verdict, with the accepted
   fraction taken over the flight lots only.

## Pitfalls

- Screening a lot that is not going to flight hardware, and leaving the lot
  that is going nowhere unmarked. The second is the one that hurts later.
- Crediting a manufacturer standard flow on the strength of a sentence in a
  quotation. Without an evidence reference nothing was shown.
- Collapsing an unsupported credit claim and an uncovered screen into one
  finding. They are chased and closed by different people.
- Taking the owed screen set from the part rather than the package, and so
  demanding a seal test of a plastic-encapsulated part.
- Reading the screening record as a set when it is a sequence. A measurement
  taken before its stress judged nothing.
- Comparing burn-in on the hours in the oven log rather than on equivalent
  hours at the reference temperature.
- Failing a run that lands exactly on the allowed duration because the
  comparison was written as a strict inequality against a converted float.
- Rejecting a lot that lands exactly on the allowable percent defective.
- Taking the accepted fraction over every lot, so non-flight lots that were
  never screened drag the campaign figure down.

## Behavior contract (gate 3)

The destination gate and non-flight marking, package-family screen sets,
manufacturer flow credit and the unsupported-claim finding, uncovered screen
set, precedence ordering, Arrhenius conversion to equivalent hours with its
tolerance, percent defective against the allowable, and the campaign verdict
are exercised by the gate 3 contract test:
scripts/test_q60_class_3_screening_requirements.py against
scripts/q60_class_3_screening_requirements_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q60_class_3_screening_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
