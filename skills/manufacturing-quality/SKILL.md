---
name: manufacturing-quality
description: "Use when a task concerns aerospace manufacturing and quality management: guide the router to the manufacturing-quality pack, whose AS9100 quality sub-skill covers QMS clause scoping and corrective action, nonconformance-control covers disposition of nonconforming product and MRB routing, supplier-control covers supplier classification and delegated verification, counterfeit-prevention covers counterfeit parts risk scoring, first-article-inspection covers FAI Forms 1-3, delta-fai covers full versus delta FAI scope, and ndt-method-selection covers NDT method selection by defect class. This pack is the production and quality assurance counterpart of the design certification spine. Trigger: manufacturing quality, AS9100, AS9102, first article inspection, QMS, audit evidence, corrective action, FAI, counterfeit prevention, nonconformance, disposition, rework, repair, scrap, use as is, MRB, supplier control, delegated verification, NDT, radiography, ultrasonic, eddy current, penetrant, magnetic particle."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
  - id: as9102
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; router/entry point for the manufacturing-quality domain pack"
metadata:
  domain: manufacturing-quality
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Manufacturing and quality domain pack (router)

Route here when the task is aerospace production and quality
management.

## Domain

Manufacturing and quality: aerospace quality management systems
(AS9100, ISO 9001:2015 plus aerospace clauses), audit evidence,
corrective action, nonconformance control, supplier control,
counterfeit prevention, first article inspection (AS9102 Forms 1-3,
delta FAI), and non-destructive testing method selection.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| manufacturing-quality/as9100/quality | AS9100 quality | QMS clause scoping, audit evidence, corrective-action closure |
| manufacturing-quality/as9100/nonconformance-control | Nonconformance control | disposition of nonconforming product, rework/repair/scrap/use-as-is, MRB routing |
| manufacturing-quality/as9100/supplier-control | Supplier control | supplier risk classification, required controls, delegated verification, external providers |
| manufacturing-quality/as9100/counterfeit-prevention | Counterfeit prevention | counterfeit parts risk scoring, prevention planning, procurement controls |
| manufacturing-quality/as9102/first-article-inspection | First article inspection | FAI Forms 1-3, characteristic accountability, delta FAI |
| manufacturing-quality/as9102/delta-fai | AS9102 delta FAI | change classification, full vs delta FAI, forms scope |
| manufacturing-quality/ndt/ndt-method-selection | NDT method selection | defect class, ferromagnetic/conductive material, radiography, ultrasonic, eddy current, penetrant, magnetic particle |

## Routing guidance

- Quality management questions (audits, clause scope, evidence,
  corrective action) route to the AS9100 sub-skill.
- Nonconforming product questions (disposition, rework, repair,
  scrap, use-as-is, MRB) route to the nonconformance-control
  sub-skill.
- External provider and supplier questions (classification, controls,
  delegated verification) route to the supplier-control sub-skill.
- Counterfeit risk and prevention questions route to the
  counterfeit-prevention sub-skill.
- First article and production-approval questions (forms,
  accountability, delta FAI) route to the AS9102 sub-skill.
- Change-classification and delta-FAI-scope questions (full vs delta
  after a production change) route to the as9102 delta-fai sub-skill.
- Non-destructive testing method questions (defect class, material,
  method sensitivity) route to the ndt ndt-method-selection
  sub-skill.
- Design and certification questions route to the avionics or
  systems-engineering-safety packs.
