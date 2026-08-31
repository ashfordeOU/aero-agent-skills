---
name: structures
description: "Use when a task concerns aerospace structures and materials: guide the router to the structures pack, whose sub-skills cover linear finite element stress analysis (CalculiX, margins of safety, unit discipline) and statistically based metallic material allowables (MMPDS A-basis and B-basis with k-factors). This pack is the structural analysis and materials layer of the library. Trigger: structures, finite element, FEM, stress analysis, margin of safety, CalculiX, allowables, A-basis, B-basis, MMPDS, metallic materials."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: mmpsd
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; router/entry point for the structures domain pack"
metadata:
  domain: structures
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Structures and materials domain pack (router)

Route here when the task is structural stress analysis, margins of
safety, or metallic material design values.

## Domain

Structures and materials: linear static finite element analysis
(CalculiX), stress and margin-of-safety discipline, and statistical
metallic allowables (MMPDS A-/B-basis, k-factors).

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| structures/fem/calculix-linear | CalculiX linear FEM | static stress, margin of safety, unit discipline, von Mises |
| structures/materials/mmpsd-allowables | MMPDS allowables | A-/B-basis, k-factors, metallic design values |

## Routing guidance

- FEM and margin-of-safety questions route to the calculix-linear
  sub-skill.
- Allowable and statistical design-value questions route to the
  mmpsd-allowables sub-skill.
- Airframe loads and certification questions route to the avionics
  far-cs25 sub-skill.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
