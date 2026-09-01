---
name: manufacturing-quality
description: "Use when a task concerns aerospace manufacturing and quality management: guide the router to the manufacturing-quality pack. AS9100 quality, nonconformance-control, supplier-control, counterfeit-prevention, calibration-control, corrective-action, document-control, and statistical-process-control cover QMS scoping, disposition, supplier risk, counterfeit scoring, calibration, CAPA closure, controlled documents, and SPC; first-article-inspection, delta-fai, and fai-revalidation cover AS9102 FAI; ndt-method-selection, ultrasonic-inspection, eddy-current-inspection, and radiographic-inspection cover NDT. Trigger: manufacturing quality, AS9100, AS9102, first article inspection, QMS, corrective action, CAPA, 8D, five whys, document control, FAI, revalidation, counterfeit prevention, nonconformance, disposition, MRB, supplier control, calibration, test accuracy ratio, statistical process control, SPC, Cpk, NDT, radiography, ultrasonic, eddy current, depth of penetration."
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
counterfeit prevention, calibration control, first article inspection
(AS9102 Forms 1-3, delta FAI), and non-destructive testing (method
selection and ultrasonic inspection).

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| manufacturing-quality/as9100/quality | AS9100 quality | QMS clause scoping, audit evidence, corrective-action closure |
| manufacturing-quality/as9100/nonconformance-control | Nonconformance control | disposition of nonconforming product, rework/repair/scrap/use-as-is, MRB routing |
| manufacturing-quality/as9100/supplier-control | Supplier control | supplier risk classification, required controls, delegated verification, external providers |
| manufacturing-quality/as9100/counterfeit-prevention | Counterfeit prevention | counterfeit parts risk scoring, prevention planning, procurement controls |
| manufacturing-quality/as9100/calibration-control | Calibration control | calibration system, traceability, intervals, TAR 4:1, out-of-tolerance handling, recall |
| manufacturing-quality/as9100/corrective-action | Corrective action | CAPA record, 8D workflow, five whys, root cause, containment, effectiveness verification |
| manufacturing-quality/as9100/document-control | Document control | master list, controlled documents, current revision, obsolete revision disposition |
| manufacturing-quality/as9102/first-article-inspection | First article inspection | FAI Forms 1-3, characteristic accountability, delta FAI |
| manufacturing-quality/as9102/delta-fai | AS9102 delta FAI | change classification, full vs delta FAI, forms scope |
| manufacturing-quality/as9102/fai-revalidation | FAI revalidation | revalidation due date, interval, change-driven revalidation, re-verification scope |
| manufacturing-quality/as9102/ballooning | Ballooning | balloon numbers, characteristic numbering, D-list, accountability matrix, verification method code |
| manufacturing-quality/ndt/ndt-method-selection | NDT method selection | defect class, ferromagnetic/conductive material, radiography, ultrasonic, eddy current, penetrant, magnetic particle |
| manufacturing-quality/ndt/ultrasonic-inspection | Ultrasonic inspection | pulse-echo, time of flight to depth, wavelength, near field, discontinuity sizing |
| manufacturing-quality/ndt/radiographic-inspection | Radiographic inspection | radiography, X-ray, gamma ray, geometric unsharpness, IQI, penetrameter, film density, porosity |
| manufacturing-quality/as9100/statistical-process-control | Statistical process control | X-bar chart, R chart, control limits, Cp/Cpk, process capability, Western Electric rules |
| manufacturing-quality/ndt/eddy-current-inspection | Eddy current inspection | eddy current, depth of penetration, impedance plane, frequency selection, conductivity, subsurface flaw |
| manufacturing-quality/ndt/liquid-penetrant-inspection | Liquid penetrant inspection | penetrant testing, capillary rise, washburn penetration depth, dwell time, developer time, bleed-out, indication sizing |
| manufacturing-quality/ndt/magnetic-particle-inspection | Magnetic particle inspection | magnetization current, circular and longitudinal magnetization, field strength band, coverage overlap, particle sensitivity, indication acceptance |

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
- Calibration questions (traceability, intervals, test accuracy
  ratio, out-of-tolerance) route to the calibration-control
  sub-skill.
- CAPA and root cause questions (8D, five whys, containment,
  effectiveness) route to the corrective-action sub-skill.
- Document questions (master list, current revision, obsolete
  disposition) route to the document-control sub-skill.
- First article and production-approval questions (forms,
  accountability, delta FAI) route to the AS9102 sub-skill.
- Change-classification and delta-FAI-scope questions (full vs delta
  after a production change) route to the as9102 delta-fai sub-skill.
- Revalidation and FAI currency questions (due date, interval,
  change-driven) route to the as9102 fai-revalidation sub-skill.
- Non-destructive testing method questions (defect class, material,
  method sensitivity) route to the ndt ndt-method-selection
  sub-skill; pulse-echo ultrasonic execution questions route to the
  ultrasonic-inspection sub-skill.
- Ballooning and characteristic-numbering questions (balloon numbers,
  D-list, accountability matrix, verification method codes) route to
  the as9102 ballooning sub-skill.
- Radiographic inspection questions (unsharpness, IQI sensitivity,
  film density, discontinuity interpretation) route to the ndt
  radiographic-inspection sub-skill.
- Design and certification questions route to the avionics or
  systems-engineering-safety packs.

- SPC, control chart, and process capability questions route to the AS9100 statistical-process-control sub-skill.
- Eddy current, depth of penetration, and frequency-selection questions route to the ndt eddy-current-inspection sub-skill.
- Liquid penetrant inspection questions (capillary action, washburn penetration, dwell time, developer time, bleed-out, indication sizing) route to the ndt liquid-penetrant-inspection sub-skill.
- Magnetic particle inspection questions (magnetization current, circular and longitudinal magnetization, field strength band, coverage overlap, particle sensitivity, indication acceptance, residual field) route to the ndt magnetic-particle-inspection sub-skill.
## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
