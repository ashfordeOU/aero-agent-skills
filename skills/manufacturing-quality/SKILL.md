---
name: manufacturing-quality
description: "Use when a task concerns aerospace manufacturing and quality management: guide the router to the manufacturing-quality pack, whose AS9100 quality sub-skill covers aerospace QMS clause scoping, audit evidence, and corrective-action closure, and whose AS9102 first-article-inspection sub-skill covers FAI Forms 1-3, characteristic accountability, and delta FAI triggers. This pack is the production and quality assurance counterpart of the design certification spine. Trigger: manufacturing quality, aerospace quality, AS9100, AS9102, first article inspection, quality management system, QMS, audit evidence, corrective action, nonconformance, FAI."
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
corrective action, and first article inspection (AS9102 Forms 1-3,
delta FAI).

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| manufacturing-quality/as9100/quality | AS9100 quality | QMS clause scoping, audit evidence, corrective-action closure |
| manufacturing-quality/as9102/first-article-inspection |
| manufacturing-quality/as9102/delta-fai | AS9102 delta FAI | change classification, full vs delta FAI, forms scope | AS9102 first article inspection | FAI Forms 1-3, characteristic accountability, delta FAI |

## Routing guidance

- Quality management questions (audits, clause scope, evidence,
  corrective action) route to the AS9100 sub-skill.
- First article and production-approval questions (forms,
  accountability, delta FAI) route to the AS9102 sub-skill.
- Change-classification and delta-FAI-scope questions (full vs delta
  after a production change) route to the as9102 delta-fai sub-skill.
- Design and certification questions route to the avionics or
  systems-engineering-safety packs.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
