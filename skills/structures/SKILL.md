---
name: structures
description: "Use when a task concerns aerospace structures and materials: guide the router to the structures pack: calculix-linear linear FEA, calculix-nonlinear Newton-Raphson and load stepping, modal-analysis natural frequencies, residual-strength fracture, crack-growth crack propagation, widespread-fatigue-damage MSD/MED, miner-damage cumulative damage, goodman-diagram mean-stress corrections, load-spectrum-counting rainflow, laminate-stiffness CLT/ABD, composite-bolted-joints bearing and bypass, sandwich-panels core shear and wrinkling, failure-criteria Tsai-Wu, mmpsd-allowables A-/B-basis, material-selection property indices, ramberg-osgood elastic-plastic stress-strain. Trigger: structures, FEM, stress analysis, margin of safety, CalculiX, nonlinear, modal, fatigue, crack growth, widespread fatigue damage, MSD, MED, Miner, Goodman, rainflow, laminate, Tsai-Wu, bolted joint, sandwich panel, allowables, MMPDS, material selection, Ramberg-Osgood, plastic strain, plate buckling, panel buckling, shear buckling."
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
  author: Aero Agent Skills
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
| structures/fem/plate-buckling | Plate buckling | flat plate and skin panel buckling, buckling coefficient, compression and shear buckling stress, spar web, effective width |
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
| structures/composites/adhesive-bonded-joints | Adhesive bonded joints | adhesive bonded joint, single lap joint, shear lag parameter, adhesive shear stress, overlap length, Volkersen shear distribution, bondline peak stress, adhesive allowable |
| structures/composites/sandwich-panels | Sandwich panels | face stress, core shear, wrinkling, bending stiffness, core selection |
| structures/composites/failure-criteria | Composite failure criteria | Tsai-Wu, Tsai-Hill, max-stress, lamina failure index |
| structures/materials/mmpsd-allowables | MMPDS allowables | A-/B-basis, k-factors, metallic design values |
| structures/materials/material-selection | Material selection | material families, stiffness/weight and strength/weight indices, cost, corrosion, temperature limits |
| structures/materials/ramberg-osgood | Ramberg-Osgood stress-strain | Ramberg-Osgood, elastic-plastic stress-strain, plastic strain, secant modulus, tangent modulus, stress from strain |
| structures/materials/fracture-toughness | Fracture toughness | K_IC plane strain fracture toughness, stress intensity factor, critical crack size, geometry factor, plane strain validity |
| structures/damage-tolerance/bird-strike | Bird strike | impact energy, soft body impact, leading edge, FAR 25.631, residual strength |
| structures/thermal-structures/thermal-stress-analysis | Thermal stress analysis | thermal stress, coefficient of thermal expansion, temperature change, bimetallic strip, thermal strain, constrained member |
| structures/composites/cmh17-allowables | CMH-17 composite allowables | CMH-17 allowables, composite allowables, A-basis, B-basis, tolerance k-factors, pooling, laminate allowables, knockdown factors, environmental conditioning, open hole |
| structures/fem/contact-analysis | Contact analysis | contact analysis, penalty method, Lagrange, contact stiffness, penetration, friction, stick slip, master slave |
| structures/loads/gust-maneuver-loads | Gust Maneuver Loads | gust loads, maneuver loads, gust load factor, V-n diagram, flight envelope, FAR 25.341, FAR 25.337, discrete gust, 1-cosine gust, gust alleviation factor, mass ratio, load factor, corner point, maneuvering speed, VA VB VC VD, margin check. |
| structures/loads/random-vibration-analysis | Random vibration analysis | random vibration, PSD response, Miles equation, transmissibility, base excitation, g-rms |
| structures/loads/shock-response-spectrum | Shock response spectrum | shock response spectrum, SRS, transient shock response, half sine pulse, base acceleration, pseudo acceleration, oscillator peak response, shock qualification, amplified frequency |
| structures/fatigue/strain-life-fatigue | Strain-life fatigue | strain life, Coffin-Manson, low-cycle fatigue, reversals to failure, Neuber local strain, transition life |
| structures/materials/creep-rupture | Creep rupture | creep, creep rate, Norton law, Larson-Miller, rupture life, stress rupture, Monkman-Grant, accumulated creep strain, time to 1 percent creep, elevated temperature |
| structures/fem/beam-frame-analysis | Beam frame analysis | beam frame analysis, rigid jointed frame, Euler Bernoulli beam element, rotation degree of freedom, bending moment recovery, portal frame |
| structures/composites/delamination-growth | Delamination growth | delamination growth, strain energy release rate, DCB double cantilever beam, ENF end notched flexure, mixed mode fracture, Benzeggagh Kenane criterion |
| structures/composites/composite-repair | Composite repair | composite repair, scarf repair, scarf length, adhesive shear stress, required scarf angle, stiffness matched patch |
| structures/thermal-structures/thermal-buckling | Thermal buckling | thermal buckling, critical temperature rise, restrained thermal expansion, buckling margin, hot structure panel |
| structures/loads/landing-ground-loads | Landing ground loads | landing ground loads, ground reactions, level landing, tail down condition, one wheel load, braked roll |

| structures/composites/laminate-hygrothermal-response | Laminate hygrothermal response | hygrothermal response, laminate CTE, moisture swell strain, cure cooldown strain, hygral strain, laminate moisture content |
| structures/fem/cylindrical-shell-buckling | Cylindrical shell buckling | cylindrical shell buckling, SP-8007 knockdown, shell axial compression, external shell bending, cross section ovalization, shell plasticity correction |
| structures/composites/laminate-first-ply-failure | Laminate first-ply failure | first ply failure, Tsai-Wu failure index, critical ply, reserve factor, midplane strain recovery, laminate failure envelope |
| structures/fem/pressure-bulkhead | Pressure bulkhead | pressure bulkhead, membrane theory dome, bulkhead dome stress, ellipsoidal bulkhead, junction ring load, dome margin |
| structures/fem/beam-vibration | Beam vibration | beam vibration, Euler-Bernoulli beam, characteristic equation roots, cantilever beam, pinned pinned beam, Rayleigh quotient |
| structures/fem/lug-joint-analysis | Lug joint analysis | lug joint analysis, pin loaded lug, lug bearing stress, lug net section tension, lug tearout shear, lug edge distance ratio, round end lug |


## Routing guidance

- FEM and margin-of-safety questions route to the calculix-linear
  sub-skill; nonlinear state-dependent stiffness and convergence
  questions route to the fem calculix-nonlinear sub-skill.
- Modal questions (natural frequencies, mode shapes, reson- Gust loads questions route to the loads gust-maneuver-loads sub-skill.
ance) route
  to the fem modal-analysis sub-skill.
- Truss questions (element stiffness matrices, global stiffness
  assembly, nodal displacements by Gaussian elimination, member
  forces, support reactions) route to the fem truss-analysis
  sub-skill.
- Column instability and Euler buckling questions (critical buckling
  load, slenderness ratio, effective length factor, end conditions,
  buckling stress, radius of gyration, cantilever columns) route to
  the fem buckling-analysis sub-skill.
- Flat plate and skin panel stability questions (plate buckling
  coefficient, compression or shear buckling of a skin panel or spar
  web, combined compression-shear interaction, effective width) route
  to the fem plate-buckling sub-skill; column and strut Euler
  buckling questions route to the fem buckling-analysis sub-skill.
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
- Bird strike impact energy, soft body impact, leading edge resistance, and FAR 25.631 compliance questions route to the damage-tolerance bird-strike sub-skill.
- Thermal stress, coefficient of thermal expansion, temperature change, bimetallic strip, and constrained member questions route to the thermal-structures thermal-stress-analysis sub-skill.
- Composite material A-basis and B-basis allowables from coupon data, batch pooling, and laminate knockdown factors route to the composites cmh17-allowables sub-skill.
- Finite element contact analysis, penalty and Lagrange methods, contact stiffness and penetration, friction and stick-slip, and master-slave formulation questions route to the fem contact-analysis sub-skill.
- Creep rate, Norton law, Larson-Miller and Monkman-Grant rupture life, and accumulated creep strain questions route to the materials creep-rupture sub-skill.
- Beam frame analysis questions (beam frame analysis, rigid jointed frame, euler bernoulli beam element, rotation degree of freedom, bending moment recovery, portal frame) route to the beam-frame-analysis sub-skill.
- Delamination growth questions (delamination growth, strain energy release rate, dcb double cantilever beam, enf end notched flexure, mixed mode fracture, benzeggagh kenane criterion) route to the delamination-growth sub-skill.
- Bonded scarf composite repair questions (scarf repair, scarf length, adhesive shear stress, required scarf angle, stiffness matched patch) route to the composites composite-repair sub-skill.
- Thermal buckling questions (critical temperature rise, restrained thermal expansion, hot structure buckling margin) route to the thermal-structures thermal-buckling sub-skill.
- Landing and ground-handling reaction questions (level landing, tail down condition, one wheel load, braked roll deceleration) route to the loads landing-ground-loads sub-skill.

- Laminate hygrothermal response questions (laminate CTE, moisture swell strain, cure cooldown strain, hygral strain) route to the composites laminate-hygrothermal-response sub-skill.
- Curved cylindrical shell buckling questions (SP-8007 knockdown, shell axial compression, shell bending, cross-section ovalization) route to the fem cylindrical-shell-buckling sub-skill.

- Laminate first-ply-failure questions (Tsai-Wu per-ply failure index, critical ply, reserve factor, FPF load) route to the composites laminate-first-ply-failure sub-skill.
- Fuselage pressure-bulkhead questions (dome membrane stresses, junction ring load, dome margin, ellipsoidal bulkhead) route to the fem pressure-bulkhead sub-skill.
- Continuous-beam vibration questions (Euler-Bernoulli natural frequencies, characteristic equation roots, Rayleigh quotient) route to the fem beam-vibration sub-skill.

- Metallic pin-loaded lug analysis questions (bearing, net-section tension and tearout stresses and margins, governing mode, capacity over the edge-distance ratio) route to the fem lug-joint-analysis sub-skill.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
- Random vibration PSD and Miles response questions route to the loads random-vibration-analysis sub-skill.
- Coffin-Manson strain-life and Neuber local-strain questions route to the fatigue strain-life-fatigue sub-skill.
- Shock response spectrum and transient half-sine or decaying-sine base acceleration questions route to the loads shock-response-spectrum sub-skill.
- Single-lap adhesive bondline shear stress, shear-lag peak stress, and joint margin questions route to the composites adhesive-bonded-joints sub-skill.
