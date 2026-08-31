---
name: aerodynamics
description: "Use when a task concerns aerodynamics and airfoil analysis: guide the router to the aerodynamics pack, whose XFOIL analysis sub-skill covers airfoil polar generation, viscous analysis at a fixed Reynolds number, lift and drag coefficient extraction, and validation against reference data (NACA 0012 at Re=6M). This pack is the aerodynamic design and validation layer of the library. Trigger: aerodynamics, airfoil, XFOIL, polar, lift coefficient, drag coefficient, NACA, viscous analysis, Reynolds number, transition."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; router/entry point for the aerodynamics domain pack"
metadata:
  domain: aerodynamics
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Aerodynamics domain pack (router)

Route here when the task is aerodynamic analysis, airfoil polars, or
validation of section data.

## Domain

Aerodynamics and CFD: airfoil section analysis with XFOIL, polar
generation, viscous-inviscid modeling, and validation against classic
reference data.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| aerodynamics/airfoil/xfoil-analysis | XFOIL airfoil analysis | polar generation, viscous analysis, lift/drag coefficients, validation bands |

## Routing guidance

- Airfoil and polar questions (XFOIL runs, NACA sections, validation
  against reference data) route to the xfoil-analysis sub-skill.
- CFD, wing-level, and stability-derivative questions are future
  sub-skills of this pack.
- Structural, control, and certification questions route to their
  domain packs (structures, gnc-autonomy, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
