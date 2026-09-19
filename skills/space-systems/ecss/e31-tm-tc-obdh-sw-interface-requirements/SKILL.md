---
name: e31-tm-tc-obdh-sw-interface-requirements
description: "Define the thermal telemetry, commanding and on-board software interface requirements of ECSS-E-ST-31C clauses 4.3.5 and 4.3.6. Use when thermistor channels and software heater loops have to be specified against the data handling subsystem: turn span and converter width into a quantisation step, combine it root-sum-square with sensor and chain error into the temperature knowledge a channel delivers, grade sampling against the item thermal time constant, sum the channel bit rates against the telemetry allocation, order alarm and setpoint limits, and size the control deadband clear of measurement noise. Trigger: ecss, e-st-31c, thermal-telemetry-channel-budget, thermistor-quantisation-step, temperature-knowledge-budget, heater-commanding-interface, thermal-monitor-limit-ordering, heater-deadband-chatter, tcs-obdh-data-exchange."
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
  tags: [ecss, e-st-31-thermal-scope, e31-tm-tc-obdh-sw-interface-requirements, thermal-telemetry-channel-budget, thermistor-quantisation-step, temperature-knowledge-budget, heater-commanding-interface, thermal-monitor-limit-ordering, heater-deadband-chatter, tcs-obdh-data-exchange]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Telemetry, Commanding and Software Interface Requirements (space-systems/ecss/e31-tm-tc-obdh-sw-interface-requirements)

Use when the task is specifying what the thermal control subsystem needs
from the data handling subsystem and from on-board software under
ECSS-E-ST-31C clauses 4.3.5 and 4.3.6 — which temperatures are telemetered
and how well, how often they are sampled, what bandwidth that costs, and
how the software commands and protects each heater line.

## Domain quick reference

- A telemetry channel delivers knowledge, not a reading. The acquisition
  chain contributes a quantisation step span / (2^n - 1), the sensor
  contributes its tolerance, and the conditioning chain contributes its
  residual error. Half the step and the two errors combine root-sum-square
  into the temperature knowledge; that number, not the display resolution,
  is what a requirement is graded against.
- Sampling is set by the item, not by the housekeeping cycle. A channel
  used to follow a transient or to close a control loop needs several
  samples inside the item thermal time constant; one sample per time
  constant reconstructs nothing and leaves the loop switching on stale
  data.
- Bandwidth is the price of both. Each channel costs bits per sample over
  the sampling period, and the thermal contribution to the housekeeping
  rate is the sum over channels. Raising a converter width or halving a
  period to fix a knowledge or a sampling finding spends bandwidth that has
  to come from the allocation.
- A software heater loop is four ordered numbers: low alarm, switch-on,
  switch-off, high alarm. Their order is the invariant — the setpoints
  inside the alarm band, switch-off above switch-on — and an inverted pair
  is a defect to refuse rather than a configuration to grade.
- The deadband between the setpoints has to stand clear of the channel
  knowledge, otherwise the loop toggles on measurement noise instead of on
  temperature. The same deadband, divided by the heating and cooling rates,
  predicts the cycle period and therefore the switch cycle count the
  relay or solid-state switch has to survive.

## Workflow

1. Validate every channel record: positive span, an integer converter width
   between two and thirty-two bits, non-negative sensor and chain errors, a
   positive sampling period, a required knowledge and an item time constant.
2. Compute the quantisation step, the root-sum-square knowledge and the
   samples per time constant; grade both against their requirements with a
   named tolerance at the boundary.
3. Compute each channel bit rate and sum them into the thermal telemetry
   bandwidth; compare with the data handling allocation.
4. For every software-owned heater line, confirm a command identifier, a
   status telemetry identifier and the four limits are all declared, and
   that the limits strictly increase.
5. Take the deadband as the setpoint difference, confirm it stands clear of
   the knowledge of the channel the line reads, and predict the cycle period
   from the heating and cooling rates.
6. Refuse a control line that reads a channel the telemetry list does not
   declare, and refuse two channels sharing a name.
7. Report channel records, control line records, the bandwidth roll-up and
   every finding: knowledge shortfall, undersampling, bandwidth overrun or
   a deadband that will chatter.

## Pitfalls

- Quoting the quantisation step as the measurement accuracy. The step is
  one of three terms; a sixteen-bit converter in front of a one-kelvin
  thermistor still delivers one-kelvin knowledge.
- Setting the sampling period from the housekeeping cycle. The item time
  constant sets it, and a low-mass line heater with a short time constant
  needs a faster channel than the platform cycle provides.
- Fixing a knowledge finding by widening the converter without checking the
  bandwidth. Bits per sample and samples per second both feed the
  allocation, and the fix can push the subsystem over it.
- Declaring switch-on and switch-off without checking them against the
  alarm limits. A setpoint outside the alarm band means the loop commands
  the heater into a region the monitoring already treats as a failure.
- Choosing a deadband on control quality alone. A deadband narrower than
  twice the channel knowledge makes the loop switch on noise, and the cycle
  count that follows is what wears the switch out.

## Behavior contract (gate 3)

Channel validation, quantisation step, root-sum-square knowledge, samples
per time constant, per-channel and summed bit rate, monitor and setpoint
limit ordering, deadband adequacy, predicted cycle period, control-line
completeness and the aggregate assessment are exercised by the gate 3
contract test: scripts/test_e31_tm_tc_obdh_sw_interface_requirements.py
against scripts/e31_tm_tc_obdh_sw_interface_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e31_tm_tc_obdh_sw_interface_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
