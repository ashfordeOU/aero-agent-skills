---
name: structures
description: "Use when a task concerns aerospace structures and materials: guide the router to the structures pack, whose calculix-linear sub-skill covers linear finite element stress analysis, modal-analysis covers natural frequencies and mode shapes, residual-strength covers fracture and critical crack length, crack-growth covers fatigue crack propagation, miner-damage covers cumulative fatigue damage, laminate-stiffness covers composite lamina and laminate stiffness, failure-criteria covers Tsai-Wu and related composite criteria, mmpsd-allowables covers statistically based metallic allowables, load-spectrum-counting covers rainflow counting and fatigue load spectra, and material-selection covers property-based material indices. This pack is the structural analysis and materials layer of the library. Trigger: structures, finite element, FEM, stress analysis, margin of safety, CalculiX, modal analysis, natural frequency, residual strength, crack growth, fatigue, rainflow, Miner, laminate stiffness, Tsai-Wu, failure criteria, allowables, A-basis, B-basis, MMPDS, metallic materials, material selection, property index."
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

Route here when the task is structural stress analysis, fatigue,
margins of safety, composites, or metallic material design values.

## Domain

Structures and materials: linear static finite element analysis
(CalculiX), stress and margin-of-safety discipline, modal analysis,
damage tolerance (residual strength, crack growth), fatigue (Miner,
load spectra), composites (laminate stiffness, failure criteria),
statistical metallic allowables (MMPDS A-/B-basis, k-factors), and
material selection.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| structures/fem/calculix-linear | CalculiX linear FEM | static stress, margin of safety, unit discipline, von Mises |
| structures/fem/modal-analysis | Modal analysis | natural frequencies, mode shapes, resonance check |
| structures/damage-tolerance/residual-strength | Residual strength | fracture toughness, critical crack length, limit-load margin |
| structures/damage-tolerance/crack-growth | Crack growth | fatigue crack propagation, Paris law, growth life, inspection intervals |
| structures/fatigue/miner-damage | Miner damage | cumulative fatigue damage, Palmgren-Miner sum, fatigue life |
| structures/fatigue/load-spectrum-counting | Load spectrum counting | rainflow counting, level crossing, exceedance spectra, mission load spectra, spectrum truncation |
| structures/composites/laminate-stiffness | Laminate stiffness | CLT, lamina stiffness, laminate ABD matrix, ply layup |
| structures/composites/failure-criteria | Composite failure criteria | Tsai-Wu, Tsai-Hill, max-stress, lamina failure index |
| structures/materials/mmpsd-allowables | MMPDS allowables | A-/B-basis, k-factors, metallic design values |
| structures/materials/material-selection | Material selection | material families, stiffness/weight and strength/weight indices, cost, corrosion, temperature limits |

## Routing guidance

- FEM and margin-of-safety questions route to the calculix-linear
  sub-skill.
- Modal questions (natural frequencies, mode shapes, resonance) route
  to the fem modal-analysis sub-skill.
- Damage-tolerance residual-strength questions (Kc, critical crack
  length, margin) route to the damage-tolerance residual-strength
  sub-skill.
- Fatigue crack growth and inspection interval questions route to the
  damage-tolerance crack-growth sub-skill.
- Cumulative damage and fatigue life questions route to the fatigue
  miner-damage sub-skill.
- Rainflow counting and load spectrum questions route to the fatigue
  load-spectrum-counting sub-skill.
- Lamina and laminate stiffness questions (CLT, ABD) route to the
  composites laminate-stiffness sub-skill.
- Composite lamina failure questions (Tsai-Wu, Tsai-Hill, max-stress)
  route to the composites failure-criteria sub-skill.
- Allowable and statistical design-value questions route to the
  materials mmpsd-allowables sub-skill.
- Material family and property-index questions route to the materials
  material-selection sub-skill.
- Airframe loads and certification questions route to the avionics
  far-cs25 sub-skill.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
