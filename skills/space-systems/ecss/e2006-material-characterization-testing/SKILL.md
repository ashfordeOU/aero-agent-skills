---
name: e2006-material-characterization-testing
description: "Use when determine whether individual material-characterization testing of a spacecraft-charging material may be waived because an assembly-level-qualification test already bounds it, under ECSS-E-ST-20-06C clause 6.6.2: categorize every charging-relevant material parameter, confirm the material sits inside the assembly in its as-flown-configuration, check that the assembly test-envelope bounds the worst-case flight exposure in electron-energy, particle-flux, temperature and exposure-duration, verify the assembly instrumentation actually observes each required parameter, and emit the residual-characterization matrix for every parameter the assembly evidence cannot supply. Trigger: ecss, e-st-20-electrical-scope, e-st-20-06c, material-characterization-waiver, assembly-level-qualification, test-envelope-coverage, bulk-resistivity, secondary-electron-yield, as-flown-configuration, residual-characterization-matrix."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-electrical-scope, e2006-material-characterization-testing, e-st-20-06c, material-characterization-waiver, assembly-level-qualification, test-envelope-coverage, bulk-resistivity, secondary-electron-yield, as-flown-configuration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Material-Characterization Waiver by Assembly Evidence (space-systems/ecss/e2006-material-characterization-testing)

Use when the task is the clause 6.6.2 decision of ECSS-E-ST-20-06C:
an individual material would normally be characterized on coupons for
its charging-relevant electrical parameters, and the question is
whether that coupon campaign may be dropped because an
assembly-level-qualification test already exercises the same material,
in the same as-flown-configuration, under an environment that bounds
its flight exposure.

## Domain quick reference

- The charging-relevant parameters of a dielectric or coating are the
  ones that set its equilibrium potential and its stored-charge
  behaviour: bulk-resistivity, surface-resistivity,
  radiation-induced-conductivity, relative-permittivity,
  dielectric-strength, secondary-electron-yield and
  photoemission-yield. Each parameter is only obtainable from a given
  campaign if that campaign carries the matching instrumentation
  channel; an assembly run without a through-thickness current monitor
  yields no bulk-resistivity, however representative it otherwise is.
- Assembly evidence substitutes for coupon evidence on four
  independent conditions, all of which must hold: the assembly
  campaign is qualification-level (a development or engineering run is
  not qualification evidence); the material is present in the assembly
  in its as-flown-configuration (same thickness within the build
  tolerance, same surface-treatment, same material family); the
  assembly environment envelope bounds the material's worst-case
  flight exposure on every axis; and the assembly instrumentation
  observes every parameter the coupon campaign would have delivered.
- The environment envelope is compared axis by axis: electron-energy,
  particle-flux, exposure-duration and applied-bias must each reach or
  exceed the flight value, while the temperature band of the assembly
  run must contain the flight temperature band on both ends. A
  shortfall on any single axis breaks the waiver for every parameter,
  because the material response outside the tested envelope is
  unmeasured, not bounded.
- A material used in more than one place is only waived where the
  assembly evidence reaches. A part of the same material exposed
  outside the tested assembly — a second unit, an externally mounted
  patch — keeps its own characterization obligation regardless of the
  assembly result.
- The output of the decision is not a single yes/no: it is a residual
  matrix listing, per material, the parameters still owed to the
  programme. An empty residual matrix is the only state in which the
  coupon campaign disappears entirely.

## Workflow

1. Normalize the assembly campaign record: reject a campaign whose
   level is not recognized, whose environment is incomplete, or whose
   instrumentation list is empty — an uninstrumented run cannot
   discharge any characterization obligation.
2. Normalize each material record: canonical parameter tokens, a
   positive thickness, a declared surface-treatment, and a flag saying
   whether the material is also exposed outside the tested assembly.
   Reject an unrecognized parameter token before it enters the
   assessment; reject duplicate material identifiers.
3. Compare configuration: the material thickness in the assembly must
   match the flight thickness within the declared build tolerance, and
   the surface-treatment must be identical. A geometric or treatment
   mismatch downgrades the assembly to a supporting datum, not
   qualification evidence.
4. Compare envelopes axis by axis and record the margin on each axis.
   Treat an exact match as covered — the comparison runs on stored
   floating-point values, so an equality case is absorbed by a named
   tolerance rather than by relaxing the engineering limit.
5. Map each required parameter onto the instrumentation channel that
   would deliver it, and split the required set into observed and
   unobserved.
6. Grant the waiver for a material only when the campaign level,
   configuration match, envelope coverage and instrumentation coverage
   all hold and the material is confined to the tested assembly.
   Otherwise carry the uncovered parameters into the residual matrix.
7. Aggregate: the characterization programme is complete when the
   residual matrix is empty across every material; otherwise it lists
   exactly the coupon tests still to be run.

## Pitfalls

- Reading "the assembly passed" as evidence for every material inside
  it — a pass is a system-level outcome, and a parameter with no
  instrumentation channel behind it was never measured at all.
- Accepting a development or engineering-model run as the waiver
  basis; only a qualification-level campaign carries that weight.
- Waiving on a bounding environment while ignoring the temperature
  band: resistivity of a dielectric moves strongly with temperature,
  so an assembly run warmer than the cold flight case does not bound
  the cold-case behaviour even if every other axis is exceeded.
- Waiving a material globally after testing one installation, when the
  same material also sits on an externally exposed part outside the
  assembly boundary.
- Treating a partial instrumentation match as a partial waiver for the
  whole material — the waiver is granted per parameter, and the
  parameters left unobserved stay on the residual matrix.

## Behavior contract (gate 3)

The campaign normalization, configuration match, envelope-coverage,
instrumentation-coverage and residual-matrix logic is exercised by the
gate 3 contract test:
`scripts/test_e2006_material_characterization_testing.py` against
`scripts/e2006_material_characterization_testing_logic.py` (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_material_characterization_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
