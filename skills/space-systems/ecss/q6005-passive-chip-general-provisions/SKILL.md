---
name: q6005-passive-chip-general-provisions
description: "Assess a delivery of bare passive chips against the baseline conditions ECSS-Q-ST-60-05C clause 8.2.1 holds for every purchase, whatever the element type: judge the supply route as an approved manufacturer, an approved distributor with an unbroken traceability chain, or open market; size the visual examination from the lot size through a banded sample plan with a zero accept number; convert the date code and the delivery week into an age against the limit; grade carriage, static protection and the dry pack moisture sensitive parts owe; and confirm the delivery documents arrived. Use when a passive chip lot reaches incoming acceptance. Trigger: ecss, q-st-60-05c, passive-chip-lot-baseline-conditions, passive-chip-visual-sample-size, passive-chip-date-code-age, passive-chip-dry-pack-handling, approved-distributor-traceability-chain."
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
  tags: [ecss, q-st-60-05-hybrid-procurement-scope, q6005-passive-chip-general-provisions, passive-chip-lot-baseline-conditions, passive-chip-visual-sample-size, passive-chip-date-code-age, passive-chip-dry-pack-handling, approved-distributor-traceability-chain]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Procurement — Passive Chip General Provisions (space-systems/ecss/q6005-passive-chip-general-provisions)

Use when the task is the general provisions of ECSS-Q-ST-60-05C clause
8.2.1 — the conditions a delivery of bare passive chips meets whatever the
element on the order line happens to be, decided at incoming acceptance on
the lot in front of you rather than on the part type it contains.

## Domain quick reference

- These conditions sit underneath the type-specific buying rules, not
  beside them. They are what a lot of chip resistors and a lot of chip
  capacitors owe identically, so a delivery can satisfy every rule its
  element type carries and still fail here.
- The supply route is a condition in its own right. A lot from an approved
  manufacturer arrives with its own route back; a lot from an approved
  distributor is only as good as the traceability chain it carries, and a
  chain with a gap in it makes the distributor's approval irrelevant for
  that lot. Open-market supply has no route at all, and no amount of
  incoming inspection builds one.
- Visual examination is sampled from the lot size, not chosen. Small lots
  are examined completely because a sample of a small lot proves almost
  nothing; larger lots move up bands to a capped sample. The accept number
  is zero throughout, so the sample size is the whole of the plan's
  stringency.
- Age is read from the manufacturing date code, which is a year and a week,
  not a date. Converting the gap in weeks into months is the only sound way
  to compare it with an age limit written in months, and a two-digit year
  needs a century rule or a lot made in the nineties reads as unborn.
- Packaging for a bare chip does two separate jobs. Individual cavity
  carriage — waffle pack, tape, gel — stops chips abrading each other and
  their terminations; static protection and, for moisture sensitive
  elements, a dry pack stop damage that leaves no visible trace at all.
  Bulk carriage fails the first job however good the barrier is.
- The delivery documents are the lot's only voice later. A certificate of
  conformity, the lot traceability record and the inspection data are what
  a later investigation reads; absent at acceptance, they are absent
  forever, because nobody can certify a lot after it has been split.
- Findings are not equally recoverable. A short sample, an aged lot and a
  missing document can be answered — examine more, seek a waiver, ask the
  supplier — so the lot is conditional. A bad supply route or damaged
  packaging cannot be answered from the same delivery.

## Workflow

1. Resolve the supply route and, for a distributor, whether the
   traceability chain back to the manufacturer is unbroken; refuse an
   unrecognised route rather than treating it as approved.
2. Size the visual examination from the delivered lot size through the
   banded sample plan, capping the sample at the lot for a small lot, and
   compare the plan with the number of elements actually examined.
3. Parse the manufacturing date code and the delivery week as year-week
   pairs, apply the century rule, convert the week gap to months, and
   compare it with the age limit the delivery carries, absorbing
   representation error at the limit with a named tolerance.
4. Judge the carriage against what a bare chip needs, then the static
   protection, then the dry pack when the elements are moisture sensitive;
   report each fault rather than stopping at the first.
5. Confirm the baseline delivery documents arrived and name the ones that
   did not.
6. Combine the five into a lot disposition — accept, conditional or
   reject — and report the finding that governs it.

## Pitfalls

- Treating an approved distributor as equivalent to an approved
  manufacturer. The approval is of the distributor, not of the lot; without
  an unbroken chain for this lot the approval says nothing about what is in
  the box.
- Taking a fixed sample size across every delivery. A fixed sample is
  wasteful on a small lot and far too weak on a large one, and the banded
  plan exists precisely because the two ends need different numbers.
- Reading a year-week date code as though the second pair were a month.
  Week 40 is not October, and the error runs the wrong way, making old lots
  look younger and passing an age limit that should have caught them.
- Accepting bulk carriage because the antistatic bag was correct. The bag
  and the cavity carrier answer different hazards; chips rubbing against
  each other in a bag damage terminations that the barrier was never going
  to protect.
- Letting a missing certificate through on the promise of a later copy.
  The certificate attaches to the lot as delivered, and once the lot is
  split into assemblies there is nothing left for a certificate to describe.
- Rejecting a lot for a short examination. The examination can be extended
  on the lot in hand, so it is a conditional finding; rejecting it discards
  material a morning's work would have accepted.

## Behavior contract (gate 3)

The supply route judgement, banded sample sizing, date code parsing and age
conversion, packaging assessment, delivery document completeness and the
lot disposition roll-up are exercised by the gate 3 contract test:
scripts/test_q6005_passive_chip_general_provisions.py against
scripts/q6005_passive_chip_general_provisions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_passive_chip_general_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
