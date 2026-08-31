---
name: manufacturing-quality
description: "Use when a task concerns aerospace manufacturing and quality management: guide the router to the manufacturing-quality pack, whose AS9100 quality sub-skill covers aerospace QMS clause scoping, audit evidence, and corrective-action closure. This pack is the production and quality assurance counterpart of the design certification spine. Trigger: manufacturing quality, aerospace quality, AS9100, quality management system, QMS, audit evidence, corrective action, nonconformance."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
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
(AS9100, ISO 9001:2015 plus aerospace clauses), audit evidence, and
corrective action.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| manufacturing-quality/as9100/quality | AS9100 quality | QMS clause scoping, audit evidence, corrective-action closure |

## Routing guidance

- Quality management questions (audits, clause scope, evidence,
  corrective action) route to the AS9100 sub-skill.
- Design and certification questions route to the avionics or
  systems-engineering-safety packs.

## Install

To install only this pack, copy or symlink the leaf folder above into
your host's skills directory (see README Install for per-host commands).
