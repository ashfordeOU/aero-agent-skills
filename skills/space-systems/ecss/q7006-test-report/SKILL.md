---
name: q7006-test-report
description: "Document the environment, exposure, results and uncertainties of a particle or UV radiation test under ECSS-Q-ST-70-06C, or grade a report already issued. Use when a run is finished and the record has to state what the specimen was in, how much it received, what the properties did and how well any of it is known. Checks identification and dosimetry traceability, requires every exposure as planned and achieved, grades the relative deviation and pairs an out-of-tolerance value with a note, reports the dose-rate acceleration against the mission, holds ultraviolet irradiance and chamber pressure to their ceilings, and combines uncertainty components in quadrature. Trigger: ecss, q-st-70-06, radiation-test-report, dosimetry-traceability, planned-versus-achieved-exposure, dose-rate-acceleration-factor, uv-equivalent-sun-hours, radiation-uncertainty-budget."
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
  tags: [ecss, q-st-70-06-particle-uv-radiation-testing-scope, q7006-test-report, radiation-test-report, dosimetry-traceability, planned-versus-achieved-exposure, dose-rate-acceleration-factor, uv-equivalent-sun-hours]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle and UV Radiation Testing — Test Report (space-systems/ecss/q7006-test-report)

Use when the task is the reporting step of an ECSS-Q-ST-70-06C particle
or UV exposure — writing, or grading, the record of the environment the
specimen sat in, the exposure it actually received, the property values
that came out and the uncertainty attached to them.

## Domain quick reference

- The report has four blocks and all four are load-bearing. Environment
  without exposure cannot be reproduced; exposure without results is a
  beam log; results without uncertainties cannot be compared with
  anybody else's results, including the same lab's next run.
- The environment is the beam and the chamber together: particle species
  and energy, flux, ultraviolet band and irradiance, pressure and
  specimen temperature. Temperature belongs in the environment because
  annealing competes with damage while the beam is on.
- A fluence with no dosimetry traceability behind it is a controller
  setpoint. Naming what the monitor was calibrated against is what turns
  the number into a measurement.
- Exposure is reported twice — as planned and as achieved — because the
  relative deviation between them is what a later reader needs. An
  achieved value standing alone cannot say whether the run met its plan
  or quietly redefined it.
- Radiation testing is accelerated testing. The ratio of test flux to
  mission flux, and the ultraviolet irradiance in suns, belong in the
  report: degradation measured far above the mission rate can
  under-report damage that anneals, and over-report damage that
  saturates.
- Uncertainty components combine in quadrature and expand by the
  declared coverage factor. Both the components and the factor belong in
  the report, because an expanded number alone cannot be recombined.

## Workflow

1. Check identification and the dosimetry traceability statement; a
   blank field counts as missing.
2. Confirm the environment block carries every text and numeric field.
3. Confirm each exposure quantity carries both a planned and an achieved
   value, and refuse a block that reports only one side.
4. Compute the relative deviation for each exposure and grade it against
   the reporting tolerance.
5. Read the recorded notes, each naming a quantity and carrying a
   justification, and pair them with the out-of-tolerance exposures; an
   unpaired one is its own finding.
6. Form the dose-rate acceleration against the mission flux and grade
   it, and grade the ultraviolet irradiance and the chamber pressure
   against their ceilings.
7. Combine the uncertainty components in quadrature, expand by the
   declared coverage factor, and compare the result with the measured
   change and the reporting step.
8. Emit the rounded values, the deviations, the acceleration and every
   finding; the report is reportable only when no finding stands.

## Pitfalls

- Reporting the achieved exposure only. Without the planned value the
  reader cannot tell a run that hit its target from one that stopped
  where the beam time ran out.
- Leaving the mission flux out. The acceleration factor is the single
  number that says how far the test sits from the environment it stands
  for, and it cannot be recovered later.
- Quoting the ultraviolet dose in hours rather than equivalent sun
  hours. Hours of an unspecified lamp are not a dose.
- Recording the chamber pressure at pump-down rather than during the
  run. Outgassing under the beam is exactly when it rises.
- Publishing an expanded uncertainty with no components and no coverage
  factor. Every later budget then has to re-derive it or guess.

## Behavior contract (gate 3)

The completeness checks, exposure deviation and tolerance grading,
deviation-note pairing, acceleration factor, irradiance and pressure
ceilings, quadrature combination, coverage-factor expansion, resolution
matching and report aggregation are exercised by the gate 3 contract
test: scripts/test_q7006_test_report.py against
scripts/q7006_test_report_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7006_test_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
