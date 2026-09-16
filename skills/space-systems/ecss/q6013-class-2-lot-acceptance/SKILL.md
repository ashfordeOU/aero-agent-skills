---
name: q6013-class-2-lot-acceptance
description: "Use when a delivery has to become per-date-code verdicts. Determine whether each purchased date code in a commercial EEE delivery passes lot acceptance at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.3.5: split a multi-code delivery into one verdict per code instead of merging them, credit manufacturer data only where it names a document and an issue and says which subgroups it covers, credit a prior acceptance only inside its validity window and only for the same manufacturing site and assembly location, judge purchaser testing on the accept number and the allowance together, and hold a code whose evidence leaves a required subgroup uncovered. Trigger: ecss, q-st-60-13c-clause-5-3-5, class-two-date-code-lot-acceptance, per-date-code-verdict-split, manufacturer-data-issue-credit, prior-acceptance-validity-window, lat-subgroup-evidence-coverage, purchaser-lat-accept-number-and-allowance."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-lot-acceptance, class-two-date-code-lot-acceptance, per-date-code-verdict-split, manufacturer-data-issue-credit, prior-acceptance-validity-window, lat-subgroup-evidence-coverage, purchaser-lat-accept-number-and-allowance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Lot Acceptance (space-systems/ecss/q6013-class-2-lot-acceptance)

Use when the task is the clause 5.3.5 lot acceptance question of
ECSS-Q-ST-60-13C at the intermediate assurance class: a delivery of
commercial parts has arrived carrying one or more purchased date codes,
and the question is which of those codes may be released and which are
held.

## Domain quick reference

- The unit of the decision is the date code, not the delivery and not
  the part number. Units built in different weeks came off different
  material, so a delivery carrying three codes is three lots and takes
  three verdicts. At this class the mixed delivery is not refused for
  being mixed; it is split, and released only when every code passes.
- Each code has to reach evidence for every required subgroup, and this
  class allows three sources to supply it: the purchaser's own testing,
  the manufacturer's data for that code, and an acceptance the same code
  already earned on an earlier programme. The sources are alternatives
  for a subgroup, never a substitute for the subgroup itself.
- Manufacturer data counts only where it names a document, that
  document's issue, and which subgroups it covers. A reference with no
  issue points at whatever the report says today; a report covering two
  subgroups has not covered the third, and reading it as a blanket
  acceptance is the usual way a code arrives uncovered.
- A prior acceptance counts only while it is inside its validity window
  and only for the same manufacturing site and assembly location. Die
  from the same wafer assembled in another plant went through another
  set of hands, so the earlier verdict says nothing about this lot.
- Purchaser testing carries two limits on one sample: the accept number,
  an integer count of failures the subgroup tolerates, and the allowable
  percent defective, a rate applied to the sample size. A small sample
  can meet its accept number while sitting far above the rate, and both
  have to hold.

## Workflow

1. Enumerate the date codes the delivery carries, refuse a malformed
   YYWW code and refuse a delivery listing the same code twice.
2. For each code, take its purchaser test results first and refuse a
   code that tests the same subgroup twice under different samples.
3. Credit the manufacturer data package, naming its missing issue or its
   missing reference as a finding rather than silently dropping it.
4. Age the prior acceptance against the assessment month in whole
   months, and compare its site and assembly location with this lot's.
5. Work out which required subgroups the credited evidence covers, and
   name every subgroup left uncovered.
6. Judge each tested subgroup on the accept number and the allowance
   together, absorbing floating-point representation error at the
   boundary with a named tolerance rather than by widening the rate.
7. Release a code only when nothing is uncovered and nothing rejects,
   release the delivery only when every code is released, and report a
   marginal subgroup that has used up most of its allowance.

## Pitfalls

- Giving a mixed delivery one verdict. A good week carries a bad one
  that way, and the date-code traceability a commercial part is bought
  with exists precisely to stop it.
- Reading a manufacturer report as covering everything. It covers what
  it names; the subgroups it is silent on are uncovered, and an
  uncovered subgroup is a hold, not a gap to be argued over.
- Crediting a reference with no issue. That points at whatever the
  document says today rather than at the evidence that was reviewed.
- Carrying a prior acceptance across an assembly-location change. The
  package and the hands that built it changed, so the earlier verdict
  does not describe this lot at any age.
- Taking the accept number as the whole criterion. The allowable percent
  defective is a second, independent limit on the same sample.

## Behavior contract (gate 3)

The date-code enumeration, whole-month validity arithmetic, manufacturer
data and prior acceptance credit rules, purchaser accept-number and
percent-defective comparisons, subgroup coverage and the per-code and
delivery dispositions are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_lot_acceptance.py against
scripts/q6013_class_2_lot_acceptance_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6013_class_2_lot_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
