# Wave-41 leaf plan (ops manager, from 5 probe receipts at 8eaf728e)

RECEIPTS OVER LISTS: all 16 planned leaves come from probe receipts (zero-owner
greps + sibling fence reads at HEAD), NOT the CEO candidate list. Probe batch
deleg_52bbc467, 5 read-only agents, all completed 2026-09-05 ~16:48 local.

## Planned leaves (16), smallest-family order
1. aerodynamics/high-speed/isentropic-flow-relations      (AERO 40->43)
2. aerodynamics/high-speed/regular-shock-reflection        (AERO)
3. aerodynamics/boundary-layer/stagnation-flow-boundary-layer (AERO)
4. flight-test-operations/performance/fuel-jettison-flight-test (FTO 41->43)
5. flight-test-operations/performance/in-flight-engine-relight-test (FTO)
6. propulsion/axial-compressor/polytropic-efficiency       (PROP 42->43)
7. systems-engineering-safety/arp4761a/event-tree-analysis (SES 42->45)
8. systems-engineering-safety/arp4761a/reliability-growth-analysis (SES)
9. systems-engineering-safety/arp4761a/maintainability-prediction (SES)
10. flight-mechanics/performance/rotorcraft-turn-performance (FM 45->46)
11. structures/fem/beam-column-analysis                     (STRUCT 49->51)
12. structures/fem/curved-beam-analysis                     (STRUCT)
13. space-systems/adcs/environmental-disturbance-torque-budget (SPACE 50->52)
14. space-systems/adcs/reaction-jet-limit-cycle             (SPACE)
15. vehicle-design/sizing/air-cycle-machine-sizing          (VD 52->54)
16. vehicle-design/sizing/v-tail-sizing                     (VD)

Post-wave family counts: aero 43, ftop 43, gnc 42 (unchanged), propulsion 43,
ses 45, flight-mechanics 46, avionics 46 (unchanged), mfg-quality 48
(unchanged), structures 51, space 52, vehicle-design 54, cross-cutting 54
(unchanged; closed - smaller families not exhausted).
Leaves 551->567; SKILL.md 563->579; corpus 1118->1150 (2N=32).

## Declined / closed this wave (receipts)
- GNC: saturated reaffirmed (0 slots; all candidates resolve to owners in
  space-systems/adcs, space-systems/orbit-mechanics, or cross-family).
- AV 46 / MQ 48: saturated reaffirmed (function-level; z-mr narrow, arinc825
  table-heavy).
- CC 54: no clean gap worth a slot (smaller families not exhausted).
- AERO declines stood: turbulent-boundary-layer-integral, whirl-flutter, LFC,
  NLF, SWBLI, real-gas, hypersonic-viscous-interaction, tangent-wedge,
  supersonic-linearized-theory/Ackeret (purpose collides with
  shock-expansion-airfoil).
- PROP: scramjet-cycle CLOSED (no Rayleigh anchor); wave-39 declines stood
  (drag loss, PPT, resistojet, pressurant, ablative,
  turboshaft/engine-matching/axial-stage).
- STRUCT: stringer-crippling not reopened; diagonal-tension variable-angle
  Kuhn not reopened; dimpling/plastic-zone/shear-lag fenced/weak.
- SPACE: gibbs-iod/orbit-determination, phasing, spin/nutation, frozen-orbit
  owned (gnc-autonomy / orbit-mechanics).
- SES: weibull-life-data SKIP (cross-cutting/numerics/probability-distributions
  owns Weibull fit/reliability-at-time); operational/maintenance items fenced.
- FM: stall-speed/cruise-climb/flutter/ground-effect owned cross-family.

## Reserve pool (not planned; swap in if a planned leaf fails at spec/build)
- systems-engineering-safety/arp4761a/reliability-prediction-parts-count
  (med conf; MIL-HDBK-217-style subset must be scoped + sourced, no-verbatim)
- cross-cutting stays closed.

## Standards ids (verify at spec time against standards-map.yaml + siblings)
AERO gas-dynamics: sibling convention (naca-tr-824 reference-only typical).
FTO: far-25. PROP axial: sibling convention. SES: arp4761a.
FM rotorcraft: far-29 or sibling convention. STRUCT: far-25/sibling convention.
SPACE adcs: ecss. VD sizing: far-25.
