---
name: q7046-receiving-inspection
description: "Verify a delivered lot of threaded fasteners at goods-in: the paperwork it arrived with, the head marking it carries, the dimensions of a drawn sample, and whether a sample mechanical re-test is owed before the lot is released to stores. Use when a fastener delivery has landed and someone has to give it a disposition: size the sample from the lot and the inspection level, list the certificates the criticality demands, read the marking against the ordered property class, judge every measured feature against its tolerance, and separate a recoverable paperwork hold from a lot that has to go back. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-incoming-inspection, fastener-lot-certificate-check, fastener-head-marking-verification, fastener-dimensional-sample-plan, fastener-lot-quarantine-disposition."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-receiving-inspection, fastener-incoming-inspection, fastener-lot-certificate-check, fastener-head-marking-verification, fastener-dimensional-sample-plan, fastener-lot-quarantine-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Receiving Inspection (space-systems/ecss/q7046-receiving-inspection)

Use when the task is the inspection clause of ECSS-Q-ST-70-46 at
goods-in: a lot of fasteners has arrived and has to be given a
disposition from its paperwork, its marking, a dimensional sample and,
where the evidence is thin, a sample mechanical re-test.

## Domain quick reference

- Receiving inspection is the last point where a wrong or unverifiable
  fastener can be stopped cheaply. Once the lot is in stores and the
  packaging is opened, lot identity is the first thing lost.
- The sample comes from the lot size and the inspection level together.
  A level is a decision about how much the source is trusted — reduced
  for a qualified supplier with a clean history, tightened after a
  non-conformance — and it is not a property of the part.
- Paperwork and hardware fail differently. A missing certificate is a
  recoverable hold: the lot is quarantined and released when the
  document arrives. A wrong head marking is not recoverable, because it
  says the wrong product was shipped.
- The head marking carries the property class and the manufacturer
  identifier, and a traceable lot also carries its lot code. A class
  mark that disagrees with the order is a reject whatever the
  certificate says, because two sources now disagree about what is in
  the box.
- Every feature the drawing tolerances has to be measured on the sample.
  A feature with no reading is not a pass; the sample simply did not
  cover it, and saying so is more useful than a disposition.
- A sample mechanical re-test is owed when the lot is fracture-critical,
  when a required certificate is missing, or when the marking could not
  be read. It is evidence bought to replace evidence that did not
  arrive, not a routine repeat of the supplier's testing.
- The defective allowance is taken from the sample drawn, and it is
  zero on a fracture-critical lot, where one non-conforming part is
  evidence about the process the whole lot shared.

## Workflow

1. Validate the lot size and the inspection level; size the sample from
   the table and cap it at the lot, since a sample cannot exceed what
   arrived.
2. List the documents the criticality demands and compare them against
   what the delivery carried. Report each missing one by name.
3. Read the head marking: the property class must agree with the order,
   the manufacturer identifier must be present, and a fracture-critical
   lot must also carry a lot code.
4. Judge each measured feature against its tolerance band, absorbing
   representation error at the limits with a named tolerance rather
   than by widening the band.
5. Report any toleranced feature the sample never measured as a
   coverage gap, separately from a non-conformance.
6. Count the non-conforming parts against the allowance for the
   criticality, taken from the sample actually drawn.
7. Give one disposition in order of severity: a wrong marking or an
   over-allowance dimensional result rejects; missing paperwork
   quarantines; an owed and unperformed re-test holds; otherwise the
   lot is released.

## Pitfalls

- Sizing the sample on the inspection level alone. The level shifts the
  sample; the lot size sets it, and a flat sample under-covers a large
  delivery and over-samples a small one.
- Treating a missing certificate as a reject. The hardware may be
  perfect and the document may be one email away; quarantine keeps the
  lot recoverable and keeps it out of stores meanwhile.
- Treating a wrong class mark as a paperwork problem. It is a different
  product, and a certificate that disagrees with the part makes the
  identity worse, not better.
- Recording a feature as passed because nobody measured it. An unmeasured
  toleranced feature is a coverage gap and belongs in the report as one.
- Applying a defective allowance to a fracture-critical lot. One
  non-conforming part there is evidence about the whole lot, not an
  outlier to be absorbed.
- Skipping the sample re-test because the supplier is qualified. The
  re-test is triggered by missing evidence, and supplier standing is
  not the evidence that went missing.

## Behavior contract (gate 3)

The sample plan over lot size and inspection level, the document list
per criticality, marking verification, per-feature dimensional
judgement with its coverage gaps, the re-test trigger and the ordered
disposition are exercised by the gate 3 contract test:
scripts/test_q7046_receiving_inspection.py against
scripts/q7046_receiving_inspection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7046_receiving_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
