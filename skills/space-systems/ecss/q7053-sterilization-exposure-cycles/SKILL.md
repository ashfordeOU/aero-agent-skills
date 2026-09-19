---
name: q7053-sterilization-exposure-cycles
description: "Compute what a sterilization exposure campaign actually delivered to its specimens, cycle by cycle, out of the logged time-temperature and dose-rate records. Use when specimens have been through repeated dry-heat, radiation or chemical cycles and each cycle must be shown to have met its defined set-point window before the accumulated exposure is credited to the qualification. Integrates dwell above the set-point with the ramp excluded, forms the thermal lethality equivalent at the reference temperature, accumulates delivered dose, and flags an excursion past the material limit, an under-dwell cycle, or a cumulative exposure beyond what the specimen is qualified for. Trigger: ecss, q-st-70-53, sterilization-exposure-cycle, dry-heat-dwell-time, thermal-lethality-equivalent, accumulated-radiation-dose, cycle-setpoint-window, material-temperature-excursion."
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
  tags: [ecss, q-st-70-53-sterilization-compatibility-scope, q7053-sterilization-exposure-cycles, sterilization-exposure-cycle, dry-heat-dwell-time, thermal-lethality-equivalent, accumulated-radiation-dose, material-temperature-excursion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Sterilization Compatibility — Exposure Cycle Execution (space-systems/ecss/q7053-sterilization-exposure-cycles)

Use when the task is the procedure step of a sterilization compatibility
campaign: turning the chamber logs of the exposure cycles into the
statement that each cycle was the cycle the plan defined, and that the
accumulated exposure the specimens carry is the accumulated exposure
that was intended.

## Domain quick reference

- The dwell that counts is the time the specimen was at or above the
  set-point, not the time the door was shut. Ramp up, ramp down and any
  dip below the set-point are excluded, and the crossings are
  interpolated between log samples rather than snapped to the nearest
  sample, or a slow ramp on a coarse log silently buys dwell that never
  happened.
- Time above a set-point is not the whole story for dry heat. Time at a
  higher temperature is worth disproportionately more, and the
  equivalent time at the reference temperature is what compares two
  differently shaped cycles. The equivalence follows the declared
  thermal resistance parameter of the process, which is an input rather
  than a constant of nature.
- A radiation cycle accumulates dose as rate times time, and the
  campaign total is what the material capability is compared against.
  Dose delivered in more cycles than planned is still dose: the
  material sees the sum.
- A cycle that overshoots is not a conservative cycle. An excursion
  above the material temperature limit damages the specimen by a
  mechanism the campaign was not testing, so the excursion is a finding
  even when the dwell requirement was comfortably met.
- Cycle count and cumulative exposure are separate limits. A campaign
  can meet its cycle count while sitting over the qualified cumulative
  dose, and it can sit under the cumulative limit while short of the
  cycles the plan required.

## Workflow

1. Validate each cycle: an identifier, a log of time and temperature
   samples with strictly increasing time, a set-point, a required
   dwell, and for a radiation cycle a non-negative dose rate and
   duration. A log with fewer than two samples cannot carry a dwell.
2. Integrate the dwell at or above the set-point, interpolating each
   crossing linearly between the bracketing samples.
3. Form the thermal lethality equivalent at the reference temperature
   over the whole log, using the declared thermal resistance parameter,
   so cycles of different shapes can be added.
4. Accumulate the delivered dose for the cycle as rate times duration.
5. Compare the cycle against its window: dwell at or above the
   required dwell, peak temperature at or below the material limit,
   absorbing an equality at either bound with the named tolerance.
6. Sum across the campaign: total dwell, total lethality equivalent,
   total dose and the count of conforming cycles.
7. Report per-cycle records, campaign totals and every finding: an
   under-dwell cycle, an excursion above the material limit, fewer
   conforming cycles than required, or a cumulative dose above the
   qualified value.

## Pitfalls

- Crediting the whole chamber cycle as dwell. The ramp is not exposure
  at the set-point, and on a long ramp the difference is most of the
  cycle.
- Snapping a set-point crossing to the nearest logged sample. On a
  one-sample-per-minute log that is a minute of dwell per crossing,
  invented in the direction the operator wanted.
- Adding raw dwell times across cycles run at different temperatures.
  Ten minutes at a high temperature and ten at a low one are not twenty
  equivalent minutes, and only the lethality equivalent is additive.
- Treating an over-temperature excursion as margin. It is an
  uncontrolled stressor applied to the specimen, and the property
  change it causes is attributed to the process by every later reader
  of the report.
- Crediting a repeated cycle because the plan allowed that many cycles.
  The cycle count and the cumulative dose are checked separately, and
  the material sees the sum whatever the count says.

## Behavior contract (gate 3)

The log validation, interpolated dwell integration, lethality
equivalence, dose accumulation, per-cycle conformance and campaign
totals are exercised by the gate 3 contract test:
scripts/test_q7053_sterilization_exposure_cycles.py against
scripts/q7053_sterilization_exposure_cycles_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7053_sterilization_exposure_cycles.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
