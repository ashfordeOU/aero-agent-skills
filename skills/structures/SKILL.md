---
name: structures
description: "Use when a task concerns aerospace structures and materials: guide the router to the structures pack: calculix-linear linear FEA, calculix-nonlinear Newton-Raphson and load stepping, modal-analysis natural frequencies, residual-strength fracture, crack-growth crack propagation, widespread-fatigue-damage MSD/MED, miner-damage cumulative damage, goodman-diagram mean-stress corrections, load-spectrum-counting rainflow, laminate-stiffness CLT/ABD, composite-bolted-joints bearing and bypass, sandwich-panels core shear and wrinkling, failure-criteria Tsai-Wu, mmpsd-allowables A-/B-basis, material-selection property indices, ramberg-osgood elastic-plastic stress-strain. Trigger: structures, FEM, stress analysis, margin of safety, CalculiX, nonlinear, modal, fatigue, crack growth, widespread fatigue damage, MSD, MED, Miner, Goodman, rainflow, laminate, Tsai-Wu, bolted joint, sandwich panel, allowables, MMPDS, material selection, Ramberg-Osgood, plastic strain."
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
| structures/fem/calculix-nonlinear | CalculiX nonlinear FEM | Newton-Raphson, load stepping, convergence residual, state-dependent stiffness |
| structures/fem/modal-analysis | Modal analysis | natural frequencies, mode shapes, resonance check |
| structures/fem/truss-analysis | Truss analysis | direct stiffness method, element stiffness matrices, global assembly, nodal displacements, member forces, support reactions |
| structures/fem/buckling-analysis | Buckling analysis | euler critical buckling load, slenderness ratio, effective length factor, end conditions, buckling stress, radius of gyration, column instability |
| structures/damage-tolerance/residual-strength | Residual strength | fracture toughness, critical crack length, limit-load margin |
| structures/damage-tolerance/crack-growth | Crack growth | fatigue crack propagation, Paris law, growth life, inspection intervals |
| structures/damage-tolerance/widespread-fatigue-damage | Widespread fatigue damage | MSD screening, MED classification, supplemental inspection |
| structures/fatigue/miner-damage | Miner damage | cumulative fatigue damage, Palmgren-Miner sum, fatigue life |
| structures/fatigue/goodman-diagram | Goodman diagram | mean-stress correction, Goodman/Gerber/Soderberg, Haigh diagram |
| structures/fatigue/stress-life-curve | Stress-life (S-N) curve | S-N curve construction, Basquin equation fit, endurance limit from runout, fatigue life prediction |
| structures/fatigue/load-spectrum-counting | Load spectrum counting | rainflow counting, level crossing, exceedance spectra, mission load spectra, spectrum truncation |
| structures/fatigue/notch-sensitivity | Notch sensitivity | stress concentration factor Kt, fatigue notch factor Kf, Neuber, Peterson, notch root radius, effective stress amplitude, notched fatigue assessment |
| structures/composites/laminate-stiffness | Laminate stiffness | CLT, lamina stiffness, laminate ABD matrix, ply layup |
| structures/composites/composite-bolted-joints | Composite bolted joints | bearing stress, bypass load, net tension, shear-out, edge distance |
| structures/composites/sandwich-panels | Sandwich panels | face stress, core shear, wrinkling, bending stiffness, core selection |
| structures/composites/failure-criteria | Composite failure criteria | Tsai-Wu, Tsai-Hill, max-stress, lamina failure index |
| structures/materials/mmpsd-allowables | MMPDS allowables | A-/B-basis, k-factors, metallic design values |
| structures/materials/material-selection | Material selection | material families, stiffness/weight and strength/weight indices, cost, corrosion, temperature limits |
| structures/materials/ramberg-osgood | Ramberg-Osgood stress-strain | Ramberg-Osgood, elastic-plastic stress-strain, plastic strain, secant modulus, tangent modulus, stress from strain |
| structures/materials/fracture-toughness | Fracture toughness | K_IC plane strain fracture toughness, stress intensity factor, critical crack size, geometry factor, plane strain validity |

## Routing guidance

- FEM and margin-of-safety questions route to the calculix-linear
  sub-skill; nonlinear state-dependent stiffness and convergence
  questions route to the fem calculix-nonlinear sub-skill.
- Modal questions (natural frequencies, mode shapes, resonance) route
  to the fem modal-analysis sub-skill.
- Truss questions (element stiffness matrices, global stiffness
  assembly, nodal displacements by Gaussian elimination, member
  forces, support reactions) route to the fem truss-analysis
  sub-skill.
- Column instability and Euler buckling questions (critical buckling
  load, slenderness ratio, effective length factor, end conditions,
  buckling stress, radius of gyration, cantilever columns) route to
  the fem buckling-analysis sub-skill.
- Damage-tolerance residual-strength questions (Kc, critical crack
  length, margin) route to the damage-tolerance residual-strength
  sub-skill.
- Fatigue crack growth and inspection interval questions route to the
  damage-tolerance crack-growth sub-skill; MSD/MED and supplemental
  inspection questions route to the damage-tolerance
  widespread-fatigue-damage sub-skill.
- Cumulative damage and fatigue life questions route to the fatigue
  miner-damage sub-skill; mean-stress correction and Haigh diagram
  questions route to the fatigue goodman-diagram sub-skill.
- S-N curve construction, Basquin equation fits, endurance-limit
  determination, and fatigue-life-prediction questions route to the
  fatigue stress-life-curve sub-skill.
- Rainflow counting and load spectrum questions route to the fatigue
  load-spectrum-counting sub-skill.
- Stress concentration, fatigue notch factor, Neuber, Peterson, and
  notch sensitivity questions route to the fatigue notch-sensitivity
  sub-skill.
- Lamina and laminate stiffness questions (CLT, ABD) route to the
  composites laminate-stiffness sub-skill; bolted joint bearing,
  bypass, net-tension and shear-out questions route to the composites
  composite-bolted-joints sub-skill; sandwich panel face/core stress,
  wrinkling, and core selection questions route to the composites
  sandwich-panels sub-skill.
- Composite lamina failure questions (Tsai-Wu, Tsai-Hill, max-stress)
  route to the composites failure-criteria sub-skill.
- Allowable and statistical design-value questions route to the
  materials mmpsd-allowables sub-skill.
- Material family and property-index questions route to the materials
  material-selection sub-skill.
- Elastic-plastic stress-strain, plastic strain, and Ramberg-Osgood
  questions route to the materials ramberg-osgood sub-skill.
- Plane strain fracture toughness, stress intensity factor, critical
  crack size, and geometry factor questions route to the materials
  fracture-toughness sub-skill.
- Airframe loads and certification questions route to the avionics
  far-cs25 sub-skill.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
