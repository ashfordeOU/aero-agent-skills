---
name: cross-cutting
description: "Use when a task concerns the skill delivery layer, the standard atmosphere, engineering documentation, or numerical verification: guide the router to the cross-cutting pack, whose SEP-2640 skill-delivery sub-skill covers SKILL.md conformance, skill URIs, and MCP resources, isa-atmosphere covers the ISA standard atmosphere, engineering-margins covers margin of safety reporting with allowable versus applied load and limit and ultimate basis, and convergence-verification covers Richardson extrapolation, grid convergence index, and observed order for mesh refinement studies. This pack is the library's meta-layer for distributing skills and the shared cross-cutting analysis layer. Trigger: skill delivery, SEP-2640, skills over MCP, skill URI, standard atmosphere, ISA, margin of safety, engineering report, allowable load, ultimate load, Richardson extrapolation, grid convergence index, observed order, discretization error."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: sep-2640
    reference-only: true
  - id: ecss
    reference-only: true
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; router/entry point for the cross-cutting domain pack"
metadata:
  domain: cross-cutting
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Cross-cutting domain pack (router)

Route here when the task is the skill format, packaging, or delivery
layer, the standard atmosphere, the engineering documentation layer,
or numerical verification.

## Domain

Cross-cutting and foundational: the skill-format and delivery
specification (SEP-2640) that governs how this library packages and
serves skills over MCP, the ISA standard atmosphere for performance
work, the documentation discipline for engineering reports, and the
numerical verification discipline for discretization-error studies.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| cross-cutting/sep2640/skill-delivery | SEP-2640 skill delivery | SKILL.md packaging, skill URIs, MCP resources, server readiness |
| cross-cutting/units-atmos/isa-atmosphere | ISA atmosphere | standard atmosphere, temperature lapse, pressure altitude, density |
| cross-cutting/documentation/engineering-margins | Engineering margins | margin of safety, allowable vs applied load, limit and ultimate basis, report sentence |
| cross-cutting/numerics/convergence-verification | Convergence verification | Richardson extrapolation, GCI, observed order, discretization error, mesh refinement |

## Routing guidance

- Skill packaging and MCP delivery questions route to the SEP-2640
  sub-skill.
- Standard atmosphere questions route to the units-atmos sub-skill.
- Margin of safety and report sentence questions route to the
  documentation engineering-margins sub-skill.
- Mesh refinement, Richardson extrapolation, and discretization
  error questions route to the numerics convergence-verification
  sub-skill.
- Aerospace engineering questions route to their domain pack
  (avionics, space-systems, systems-engineering-safety,
  manufacturing-quality).

## Install

To install only this pack, copy or symlink the leaf folder above into
your host's skills directory (see README Install for per-host commands).
