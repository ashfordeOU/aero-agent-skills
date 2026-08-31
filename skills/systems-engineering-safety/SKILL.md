---
name: systems-engineering-safety
description: "Use when a task concerns aircraft or system-level engineering and safety assurance: guide the router to the systems-engineering-safety pack, covering ARP4754A systems planning and requirements traceability and validation, the ARP4761A safety assessment process and fault tree and FMEA analyses, common cause analysis and particular risk analysis, and model-based systems engineering with SysML modeling and digital-thread traceability. This pack is the systems-level spine above item-level software and hardware assurance. Trigger: systems engineering, systems safety, ARP4754A, ARP4761A, safety assessment, fault tree, FMEA, common cause, particular risk, rotor burst, traceability, validation, MBSE, SysML, FDAL, IDAL, FHA, PSSA, SSA."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; router/entry point for the systems-engineering-safety domain pack"
metadata:
  domain: systems-engineering-safety
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Systems engineering and safety domain pack (router)

Route here when the task is aircraft or system-level engineering,
safety assessment, or model-based systems engineering.

## Domain

Systems engineering and safety: development planning and development
assurance (ARP4754A), requirements traceability and validation, the
safety assessment process (ARP4761A) with fault tree and FMEA
analyses, common cause analysis, particular risk analysis, and
model-based systems engineering (SysML, digital thread).

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| systems-engineering-safety/arp4754a/systems-planning | ARP4754A systems planning | FDAL/IDAL allocation, certification and development plans |
| systems-engineering-safety/arp4754a/requirements-traceability | ARP4754A requirements traceability | SRATS to HLR to LLR to code to tests, closure matrix |
| systems-engineering-safety/arp4754a/validation | ARP4754A validation | validation methods, requirements confirmation, validation scenarios |
| systems-engineering-safety/arp4761a/safety-assessment | ARP4761A safety assessment | FHA/PSSA/SSA sequence, analysis set selection |
| systems-engineering-safety/arp4761a/fta-fmea | FTA and FMEA | fault trees, minimal cut sets, failure modes, common cause |
| systems-engineering-safety/arp4761a/common-cause-analysis | Common cause analysis | common mode failures, zonal analysis, separation, independence |
| systems-engineering-safety/arp4761a/particular-risk-analysis | Particular risk analysis | single-event risks, rotor burst, bird strike, conditional probability, containment |
| systems-engineering-safety/mbse/systems-engineering | MBSE systems engineering | SysML modeling, function allocation, traceability closure |
| systems-engineering-safety/mbse/sysml-modeling | SysML modeling | diagram kinds, BDD/IBD, requirement and parametric diagrams, viewpoints, governance |

## Routing guidance

- Development assurance and planning questions route to the ARP4754A
  systems-planning sub-skill.
- Traceability and closure questions route to the ARP4754A
  requirements-traceability sub-skill; validation methods and
  confirmation questions route to the validation sub-skill.
- Safety assessment questions (severity, FHA/PSSA/SSA, analysis set)
  route to the ARP4761A safety-assessment sub-skill.
- Fault tree, FMEA, and cut-set questions route to the fta-fmea
  sub-skill; common mode and zonal independence questions route to
  the common-cause-analysis sub-skill.
- Single-event hazard questions (rotor burst, bird strike, tire
  burst, fire, conditional probability, containment) route to the
  particular-risk-analysis sub-skill.
- Modeling and digital-thread questions route to the MBSE
  sub-skills: system-level engineering to systems-engineering,
  diagram-specific modeling to sysml-modeling.
- Item-level software or hardware questions route to the avionics pack.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
