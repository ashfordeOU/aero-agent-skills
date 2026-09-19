---
name: e3311-verification-general-inspection
description: "Define the verification strategy and the inspection coverage for explosive hardware under ECSS-E-ST-33-11C clauses 4.14.1 and 4.14.2. Use when the task is deciding how each requirement on a one-shot device is closed: choosing test, analysis, review of design or inspection from the requirement kind and whether the demonstration destroys the article, moving a destructive function test onto a lot sample, sizing that sample from the lot, grading inspection coverage with no exemption for a critical characteristic, and screening a verification matrix for open evidence. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-hardware-verification-method-selection, one-shot-device-lot-sampling, explosive-lot-acceptance-sample-size, explosive-hardware-inspection-coverage, verification-matrix-completeness-screen."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-verification-general-inspection, explosive-hardware-verification-method-selection, one-shot-device-lot-sampling, explosive-lot-acceptance-sample-size, explosive-hardware-inspection-coverage, verification-matrix-completeness-screen]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Verification Strategy and Inspection (space-systems/ecss/e3311-verification-general-inspection)

Use when the task is the verification requirement of ECSS-E-ST-33-11C
clause 4.14.1 and the inspection requirement of clause 4.14.2 --
choosing how each requirement on an explosive item is actually closed
when the demonstration that would prove it destroys the article, and
deciding what the flight unit itself still owes once the evidence has
moved onto a lot sample.

## Domain quick reference

- Explosive hardware breaks the usual verification chain. The test
  that proves an initiator fires consumes it, so the article that flies
  is never the article that was tested, and the strategy has to say
  explicitly which article each piece of evidence came from.
- Method selection follows the requirement kind and the destructiveness
  of the demonstration, not preference. A function requirement on a
  one-shot device goes to test on a lot sample; a workmanship,
  interface or marking requirement goes to inspection on the flight
  article; a material requirement goes to analysis, with review of
  design carrying part of the load where qualified heritage exists.
- When a test moves onto a lot sample, the flight article does not
  become evidence-free. It inherits a companion inspection, because
  the only thing that still connects the fired sample to the unit that
  flies is that they came from one lot built one way.
- Sample size is a property of the lot. A fraction of the lot with a
  floor and a ceiling keeps a small lot from being sampled trivially
  and a large lot from being consumed, and a sample that would take the
  whole lot is a contradiction rather than a conservative choice.
- Inspection coverage is graded with an exemption only for
  non-critical characteristics. A critical characteristic left
  uninspected is an open finding regardless of how high the overall
  coverage reads, because coverage is an average and the average hides
  the one that matters.
- A verification matrix closes only when every requirement carries a
  method, an article and evidence. A row with a method and no evidence
  is an open item, and reporting a method count as a completion figure
  is how an unverified requirement reaches flight.

## Workflow

1. Declare each requirement: its kind, whether the demonstration is
   destructive, whether the item is a one-shot device, and whether
   qualified heritage exists. Reject a requirement kind that is not one
   of the declared set.
2. Select the method and the article it applies to. Where the
   demonstration is destructive or the device is one-shot, move the
   test onto a lot sample and attach the companion inspection the
   flight article now owes.
3. Size the lot sample from the lot: take the policy fraction, round
   up, and clamp between the floor and the ceiling. Reject a sample
   that would consume the entire lot.
4. Grade inspection coverage over the declared characteristics,
   separating the critical ones, and report every uninspected critical
   characteristic individually rather than as a coverage number.
5. Screen the verification matrix: every row needs a method, an article
   and evidence, and rows missing evidence are reported as open items
   with the requirement they leave unclosed.
6. Combine the method selection, the sampling, the coverage and the
   open items into one verdict, so a matrix that is fully populated but
   short on critical inspection does not read as closed.

## Pitfalls

- Recording a fired sample as evidence against the flight article. The
  two are different units, and the strategy has to name the article
  each result belongs to or the traceability is lost the moment the
  sample is consumed.
- Dropping the flight article's inspection once the test moved to a
  sample. Lot identity is the only remaining link between the two, and
  it is inspection on the flight unit that confirms it.
- Sizing a lot sample by a fixed number. A fixed count over-samples a
  small lot to the point of consuming it and under-samples a large one,
  which is why the size is a fraction with a floor and a ceiling.
- Reading a high overall inspection coverage as a pass. Coverage is an
  average over characteristics, and a single uninspected critical
  characteristic sits invisibly inside a coverage figure above ninety
  per cent.
- Counting populated matrix rows as verification progress. A row with a
  method and no evidence has decided how the requirement will be
  closed, not closed it.
- Comparing a coverage fraction with its threshold by bare arithmetic.
  The fraction is a quotient of counts, so a case that sits exactly on
  the threshold can land a few units in the last place below it; the
  comparison absorbs that while the threshold stays untouched.

## Behavior contract (gate 3)

The method selection, lot-sample sizing, inspection coverage grading,
critical-characteristic screen and verification-matrix completeness
verdict are exercised by the gate 3 contract test:
scripts/test_e3311_verification_general_inspection.py against
scripts/e3311_verification_general_inspection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3311_verification_general_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
