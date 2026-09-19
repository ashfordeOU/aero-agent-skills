---
name: e3102-cdl-lhp-performance-verification
description: "Verify the performance evidence behind a capillary driven two-phase loop or loop heat pipe under ECSS-E-ST-31-02C clause 5.5.5.2d. Use when the task is grading a start-up demonstration against the minimum start heat load with the qualification thermal mass attached, fitting how that start load moves with added evaporator mass, checking evaporator-inlet subcooling, closing the capillary pressure budget against liquid, vapour and groove losses plus the adverse tilt head, grading the unpowered heat leak, and confirming the reservoir set-point regulation method was demonstrated over its band. Trigger: ecss, e-st-31-02c, cdl-start-up-minimum-heat-load, evaporator-attached-thermal-mass-sensitivity, loop-heat-pipe-inlet-subcooling, capillary-adverse-tilt-head-margin, loop-off-mode-heat-leak, reservoir-set-point-regulation-method."
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
  tags: [ecss, e-st-31-02-two-phase-heat-transport-scope, e3102-cdl-lhp-performance-verification, cdl-start-up-minimum-heat-load, evaporator-attached-thermal-mass-sensitivity, loop-heat-pipe-inlet-subcooling, capillary-adverse-tilt-head-margin, loop-off-mode-heat-leak]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Capillary Loop Performance Verification (space-systems/ecss/e3102-cdl-lhp-performance-verification)

Use when the task is the performance verification of a capillary driven
loop or loop heat pipe under ECSS-E-ST-31-02C clause 5.5.5.2d -- deciding
whether the six things that decide whether the loop works in flight were
actually demonstrated, and demonstrated at the worst case rather than at
a convenient bench condition.

## Domain quick reference

- Start-up is the hardest thing a capillary loop does and the easiest
  thing to demonstrate dishonestly. The loop has to prime a flooded wick
  from cold at the lowest heat load it is specified to start on. A
  demonstration that started at more power than the declared minimum has
  not shown the requirement; a demonstration that started at the right
  power on a bare evaporator has not shown it either, because the mass
  bolted to the evaporator is what the start-up has to heat.
- Minimum start heat load therefore rises with attached thermal mass,
  roughly linearly over the span a loop is actually started at. A
  sensitivity series gives a slope in W per (J/K); it is used to check
  the flight mass, not to extrapolate to a mass no unit ever started at.
  A series in which the start load falls as mass rises is an instrument
  or procedure problem, not a favourable result.
- Subcooling at the evaporator inlet is the margin against vapour
  reaching the wick. It is the difference between the loop saturation
  temperature and the liquid inlet temperature; when it goes negative
  the liquid line is already flashing and the loop deprimes regardless
  of how good the transport numbers look.
- Adverse tilt is a pressure budget, not a pass/fail orientation. The
  capillary limit of the wick has to cover the liquid-line, vapour-line
  and groove losses plus rho*g*h for the verified adverse elevation. A
  favourable elevation contributes a negative head and relieves the
  budget, which is exactly why a ground test at a favourable tilt proves
  nothing about the adverse case.
- Off-mode heat leak is measured with the evaporator unpowered: the loop
  is a conduction path even when it is not transporting, and that
  parasitic into the cold side is what a survival heater has to cover.
- Regulation is a declared method plus a demonstrated band. Reservoir or
  compensation-chamber set-point control by an active heater, a
  cold-biased reservoir, a thermoelectric element or a passive two-phase
  reservoir are recognised; a method demonstrated over a narrower band
  than the loop is regulated across has not been verified.

## Workflow

1. Validate the start-up record: demonstrated start power, declared
   minimum start heat load, attached thermal mass and the qualification
   mass. Grade power and mass as two separate conditions, both required.
2. Fit the thermal-mass sensitivity series to a slope and intercept, and
   report a non-monotonic series as a finding instead of fitting it
   silently. Interpolate the flight mass inside the tested span only;
   refuse a mass outside it.
3. Compute evaporator-inlet subcooling and grade it against the required
   value, raising the vapour-ingestion finding separately when the inlet
   sits above saturation.
4. Form the adverse static head from liquid density, the verified
   elevation and local gravity, add it to the liquid, vapour and groove
   losses, and grade the sum against the capillary limit. Report both
   the margin in Pa and the limit-to-demand ratio.
5. Grade the unpowered off-mode heat leak against its allowance.
6. Check the regulation method against the recognised set and grade the
   demonstrated band against the required one.
7. Roll the six checks into one verdict, name every failed check, and
   absorb exact-equality cases with a named tolerance rather than by
   relaxing any limit.

## Pitfalls

- Reporting a start-up as passed because the loop started. The pass
  condition is starting at or below the declared minimum heat load with
  the qualification mass attached; either half missing is a finding.
- Extrapolating the thermal-mass sensitivity past the tested span. Start-
  up stops being linear once the evaporator mass leaves the range the
  loop was actually started at, so the correct response is more test
  points, not a longer straight line.
- Verifying tilt at a favourable elevation and calling the orientation
  covered. A favourable head subtracts from the demand and can make a
  marginal wick look comfortable; only the adverse elevation is evidence.
- Treating subcooling as a temperature reading rather than a difference.
  The number that matters is saturation minus inlet, and the saturation
  temperature moves with the reservoir set point during the same test.
- Folding the off-mode heat leak into the transport performance number.
  They are measured in different states; adding them hides an unpowered
  parasitic behind a powered margin.
- Widening a required band or allowance so an exact-equality case reads
  as a pass. Equality at a limit is a representation question, handled
  by the tolerance inside the comparison, not by moving the limit.

## Behavior contract (gate 3)

The start-up grading, thermal-mass sensitivity fit and interpolation,
subcooling assessment, adverse-tilt capillary pressure budget, off-mode
heat-leak grading, regulation-method check and the rolled-up verdict are
exercised by the gate 3 contract test:
scripts/test_e3102_cdl_lhp_performance_verification.py against
scripts/e3102_cdl_lhp_performance_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3102_cdl_lhp_performance_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
