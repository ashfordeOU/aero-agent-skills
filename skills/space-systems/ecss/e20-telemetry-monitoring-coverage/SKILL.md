---
name: e20-telemetry-monitoring-coverage
description: "Use when determine whether the telemetry set of a spacecraft subsystem or payload is sufficient to monitor it in flight under ECSS-E-ST-20C clause 4.1.4: categorize each parameter as housekeeping, discrete status, payload measurement or event diagnostic, compute the sampling rate its observed bandwidth demands and compare it with the rate actually allocated, verify that every parameter feeding an onboard limit check carries an ordered warning and alarm pair inside the sensor range, sum the resulting source bit rate against the downlink allocation, and flag any monitored function left without a parameter. Trigger: ecss, e-st-20-electrical-scope, telemetry-monitoring-coverage, housekeeping-telemetry, telemetry-sampling-rate, limit-checking, downlink-bit-rate, parameter-coverage-gap, onboard-monitoring."
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
  tags: [ecss, e-st-20-electrical-scope, e20-telemetry-monitoring-coverage, housekeeping-telemetry, telemetry-sampling-rate, limit-checking, downlink-bit-rate, onboard-monitoring]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical & Electronic — Telemetry Monitoring Coverage (space-systems/ecss/e20-telemetry-monitoring-coverage)

Use when the task is the flight-operations telemetry sufficiency check
of ECSS-E-ST-20C clause 4.1.4 -- deciding whether the parameters a
subsystem or payload produces are enough, fast enough, bounded enough
and small enough to actually monitor it in flight.

## Domain quick reference

- Clause 4.1.4 asks a coverage question, not a formatting one: for
  every function that has to be monitored during operations, is there
  a parameter that observes it, at a rate that resolves the behaviour,
  with limits that let the onboard monitoring act, and inside the
  downlink that carries it. Four questions, four independent ways to
  fail.
- Parameters fall into four families that carry different sampling
  demands. A housekeeping analog measurement (temperature, voltage,
  current) is slowly varying and is oversampled modestly. A discrete
  status needs the heaviest oversampling of the continuous families,
  because a transition that lands between two samples is invisible. A
  payload measurement is sampled against its own signal bandwidth at
  close to the Nyquist limit, since the data volume is dominated by
  it. An event diagnostic is the highest-rate family: it exists to
  capture a short transient, so it is sampled well above the rate that
  merely reconstructs the waveform.
- The required rate is Nyquist (twice the observed bandwidth) times
  the family's oversampling factor. Comparing the allocated rate
  against the raw bandwidth instead of the required rate is the common
  arithmetic error, and it understates the requirement by at least a
  factor of two.
- A parameter that feeds an onboard limit check has to carry four
  ordered thresholds -- low alarm below low warning below high warning
  below high alarm -- and all four have to sit inside the sensor range
  that produces the parameter. A threshold outside the range can never
  be crossed, so the monitoring silently never fires.
- Source bit rate is bits per sample times sample rate, summed over
  the set, and it competes for a fixed downlink allocation. Raising a
  rate to fix a sampling finding can create a budget finding, so the
  two are assessed together, never one after the other.
- A critical monitored function needs more than a parameter pointed at
  it: at least one of its parameters has to be limit-checked, or the
  function is observable only in replay, not monitored onboard.

## Workflow

1. Categorize every parameter into its family; reject an unrecognized
   family rather than defaulting it into housekeeping.
2. Compute the required sample rate from the observed bandwidth and
   the family oversampling factor, and compare it with the allocated
   rate. Record the ratio so a marginal parameter is visible.
3. For each limit-checked parameter, check the four thresholds are
   strictly ordered and all lie inside the sensor range.
4. Sum bits per sample times sample rate over the set and compare the
   total against the downlink allocation; report the margin as a
   fraction of the allocation, not only a pass or fail.
5. Map parameters onto the monitored functions and flag any function
   with no parameter; for a critical function, also flag the absence
   of any limit-checked parameter among those covering it.
6. Aggregate all four finding families. The set is sufficient only
   when sampling, limits, budget and function coverage are all clear.

## Pitfalls

- Sizing the sample rate against the parameter's bandwidth rather than
  twice it. That is an aliased parameter that looks well sampled in
  the budget table and reconstructs a wrong value in flight.
- Giving a discrete status the same oversampling as a slowly varying
  analog measurement. A relay that changes state and returns between
  two samples leaves no trace at all in the telemetry.
- Declaring limits on a parameter without checking them against the
  sensor range. An alarm threshold beyond full scale is a monitor that
  can never trip, and it reads as configured in every review.
- Closing the sampling findings first and the downlink budget second.
  Each rate increase spends allocation, so a set can pass both checks
  in isolation and fail them together.
- Counting a function as covered because a parameter names it. If none
  of the covering parameters is limit-checked, a critical function has
  observation without onboard monitoring.

## Behavior contract (gate 3)

The parameter categorization, required-rate, limit-ordering,
downlink-budget and function-coverage logic is exercised by the gate 3
contract test: `scripts/test_e20_telemetry_monitoring_coverage.py`
against `scripts/e20_telemetry_monitoring_coverage_logic.py` (stdlib
unittest, offline). Run:
python3 scripts/test_e20_telemetry_monitoring_coverage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
