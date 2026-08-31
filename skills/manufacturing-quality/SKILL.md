---
name: manufacturing-quality
description: "Use when a task concerns aerospace manufacturing and quality management: guide the router to the manufacturing-quality pack, whose AS9100 quality, nonconformance-control, supplier-control, counterfeit-prevention, and calibration-control sub-skills cover QMS scoping, disposition, supplier risk, counterfeit scoring, and test-equipment calibration, first-article-inspection and delta-fai cover AS9102 FAI Forms 1-3, and ndt-method-selection and ultrasonic-inspection cover NDT method selection and pulse-echo ultrasonic execution. This pack is the production and quality assurance counterpart of the design certification spine. Trigger: manufacturing quality, AS9100, AS9102, first article inspection, QMS, audit evidence, corrective action, FAI, counterfeit prevention, nonconformance, disposition, MRB, supplier control, delegated verification, calibration, test accuracy ratio, NDT, radiography, ultrasonic, eddy current, penetrant, magnetic particle, pulse echo, discontinuity, ballooning."
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
| manufacturing-quality/as9102/first-article-inspection | First article inspection | FAI Forms 1-3, characteristic accountability, delta FAI |
| manufacturing-quality/as9102/delta-fai | AS9102 delta FAI | change classification, full vs delta FAI, forms scope |
| manufacturing-quality/as9102/ballooning | Ballooning | balloon numbers, characteristic numbering, D-list, accountability matrix, verification method code |
| manufacturing-quality/ndt/ndt-method-selection | NDT method selection | defect class, ferromagnetic/conductive material, radiography, ultrasonic, eddy current, penetrant, magnetic particle |
| manufacturing-quality/ndt/ultrasonic-inspection | Ultrasonic inspection | pulse-echo, time of flight to depth, wavelength, near field, discontinuity sizing |
| manufacturing-quality/ndt/radiographic-inspection | Radiographic inspection | radiography, X-ray, gamma ray, geometric unsharpness, IQI, penetrameter, film density, porosity |

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
- First article and production-approval questions (forms,
  accountability, delta FAI) route to the AS9102 sub-skill.
- Change-classification and delta-FAI-scope questions (full vs delta
  after a production change) route to the as9102 delta-fai sub-skill.
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

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
