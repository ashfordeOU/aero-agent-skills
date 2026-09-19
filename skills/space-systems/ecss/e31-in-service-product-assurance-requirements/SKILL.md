---
name: e31-in-service-product-assurance-requirements
description: "Define the on-orbit thermal monitoring, in-service verification and product assurance interface a thermal control system owes under ECSS-E-ST-31C clauses 4.7 and 4.8. Use when the design is frozen and the question turns to flight: size sensor count and independent acquisition chains, derive the telemetry interval from the thermal time constant, place the alarm limit inside the operational-to-design band and report where in it, compare the flight maximum with the prediction as a signed model drift, and carry each unmitigated severe failure mode out by name. Trigger: ecss, e-st-31-thermal-control, e31-in-service-product-assurance-requirements, on-orbit-thermal-telemetry-interval, thermal-sensor-chain-redundancy, thermal-alarm-limit-band-placement, tcs-fmea-criticality-interface, in-service-thermal-model-drift."
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
  tags: [ecss, e-st-31-thermal-control, e31-in-service-product-assurance-requirements, on-orbit-thermal-telemetry-interval, thermal-sensor-chain-redundancy, thermal-alarm-limit-band-placement, tcs-fmea-criticality-interface, in-service-thermal-model-drift]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — In-Service Monitoring and PA Interface (space-systems/ecss/e31-in-service-product-assurance-requirements)

Use when the task is the in-service step of ECSS-E-ST-31C clauses 4.7 and
4.8 -- what the thermal control system has to be able to show about itself
once it is flying, and what the thermal discipline owes the product
assurance and dependability analyses that sit alongside it.

## Domain quick reference

- Monitoring has two independent dimensions and both are graded: how many
  sensors an item carries, and how many independent acquisition chains
  those sensors sit on. Four sensors on one chain is one failure away from
  a blind item.
- The telemetry interval is not a housekeeping preference, it is derived
  from the thermal time constant of the item. An item with a twenty-minute
  time constant sampled once an hour has telemetry that cannot reconstruct
  the transient that broke it.
- There are three temperature limits and they are different things. The
  operational limit is where the item is meant to live, the design limit is
  what it was built to survive, and the alarm sits between them. Reporting
  where in that band the alarm sits is more useful than a pass: an alarm at
  95 percent of the band leaves no reaction time.
- In-service verification is a comparison, not a reading. The flight
  maximum against the design limit gives the margin still standing; the
  flight maximum against the predicted maximum gives the model drift, and
  the two answer different questions.
- Model drift is two-sided. A model that over-predicts by 20 K is as
  uncorrelated as one that under-predicts by 20 K, and the over-predicting
  one is the more dangerous because it looks conservative and is trusted on
  the next mission.
- The product assurance interface needs three facts per thermal failure
  mode: its severity category, whether telemetry can see it at all, and
  whether it is mitigated. A severe mode with no mitigation is a single
  point failure and has to leave the assessment by name, not as a count.
- A severe mode invisible to telemetry is its own finding, separate from
  mitigation. In-service verification cannot verify what is not measured.
- Margins and intervals are float differences and quotients, so a value
  sitting exactly on its limit is absorbed by a named tolerance far below
  any thermistor's resolution.

## Workflow

1. List the monitored thermal items. For each, record sensor count and
   required count, independent chains and required chains, thermal time
   constant and required samples per time constant, actual telemetry
   interval, the three temperature limits, the predicted and flight maxima,
   and the drift tolerance.
2. Grade the sensor fit and the chain independence as two separate
   findings; refuse a register claiming more chains than sensors.
3. Derive the required telemetry interval from the time constant and the
   sample count, and grade the actual interval against it.
4. Check the alarm sits strictly inside the operational-to-design band, and
   report its placement fraction within that band.
5. Take the in-service margin as design limit minus flight maximum, and the
   model drift as flight maximum minus predicted maximum, signed.
6. Grade the drift against a two-sided tolerance.
7. Score every thermal failure mode: severity rank, plus one for being
   invisible to telemetry, plus one for being unmitigated.
8. Roll up: single point failures by name, the worst criticality mode, the
   item with the tightest margin, and the monitored fraction.

## Pitfalls

- Counting sensors and calling the item monitored. The chain topology is
  the part that survives a single acquisition failure.
- Setting the telemetry interval from the downlink budget rather than the
  thermal time constant, so the fastest-responding item is the worst
  sampled.
- Placing the alarm at the design limit. It trips at the moment the margin
  is already gone, which is an event log, not an alarm.
- Reporting the alarm as compliant without its placement in the band. A
  compliant alarm at 95 percent of the band and one at 40 percent are not
  the same alarm.
- Confusing the margin with the drift. Flight against design says whether
  the item is safe; flight against prediction says whether the model is.
- Treating an over-predicting model as acceptable because it is
  conservative. The drift tolerance is two-sided, and the conservative
  model is the one that gets reused.
- Reporting single point failures as a count. The dependability action
  needs the names, and a count hides which mode carries it.
- Reading a mitigated severe mode as closed when telemetry cannot see it.
  Mitigation and observability are two separate findings.
- Using a strict comparison at a limit or a sampling interval. These are
  float differences and quotients, and a boundary value must read the same
  on every platform.

## Behavior contract (gate 3)

The sensor and chain coverage checks, the time-constant-derived telemetry
interval, the alarm band ordering and placement fraction, the in-service
margin, the signed two-sided model drift, the criticality score with its
detectability and mitigation increments, the single-point-failure rule and
the roll-up by name are exercised by the gate 3 contract test:
scripts/test_e31_in_service_product_assurance_requirements.py against
scripts/e31_in_service_product_assurance_requirements_logic.py (stdlib
unittest, offline). Boundary cases use assertAlmostEqual so a value on its
limit reads the same on every platform.
Run: python3 scripts/test_e31_in_service_product_assurance_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
