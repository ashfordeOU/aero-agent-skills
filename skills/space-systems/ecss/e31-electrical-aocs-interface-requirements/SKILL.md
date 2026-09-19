---
name: e31-electrical-aocs-interface-requirements
description: "Derive the thermal-control interface requirements towards the power and attitude-control subsystems under ECSS-E-ST-31C clauses 4.3.3 and 4.3.4. Use when heater power has to be allocated and the attitude side needs thermal disturbance inputs: size every heater circuit at the top of the regulated bus where power and current are worst case, grade switch current against its derated rating, build the peak and duty-weighted orbit-average demands with redundant branches counted only when both can be live, refuse a mission mode carrying no dissipation figure, and turn offset radiator recoil into a disturbance torque against its allocation. Trigger: ecss, e-st-31c, tcs-power-interface, heater-power-allocation, heater-circuit-bus-sizing, heater-switch-derating, tcs-dissipation-data-exchange, radiator-recoil-disturbance-torque, tcs-aocs-disturbance-input."
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
  tags: [ecss, e-st-31-thermal-scope, e31-electrical-aocs-interface-requirements, tcs-power-interface, heater-power-allocation, heater-circuit-bus-sizing, heater-switch-derating, tcs-dissipation-data-exchange, radiator-recoil-disturbance-torque, tcs-aocs-disturbance-input]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Electrical and AOCS Interface Requirements (space-systems/ecss/e31-electrical-aocs-interface-requirements)

Use when the task is stating what the thermal control subsystem needs from,
and owes to, the electrical power subsystem and the attitude and orbit
control subsystem under ECSS-E-ST-31C clauses 4.3.3 and 4.3.4 — heater
power allocation and its control inputs, the dissipation data other
subsystems size against, and the disturbance the thermal design injects
into attitude.

## Domain quick reference

- A heater circuit is sized at the top of the regulated bus range, not at
  nominal. Power goes as V^2/R and current as V/R, so the same circuit that
  draws 6.8 W at the bottom of a 26 to 29 V bus draws 7.0 W and its worst
  current at the top; both the allocation and the switch rating are set
  there.
- The power subsystem allocates against two different numbers. Peak demand
  is what can be switched on simultaneously and sizes the distribution;
  orbit-average demand is duty-weighted and sizes the energy balance. A
  redundant branch belongs in the peak only when the design admits both
  branches live at once, and never in the orbit average.
- Switch and fuse ratings are used derated. The comparison is against
  rating times the derating factor the power subsystem imposes, so a 0.5 A
  switch at 0.8 derating offers 0.4 A, and a circuit at 0.42 A is
  non-compliant even though it sits under the nameplate.
- The dissipation data handed over is a per-mode table, and it has to be
  complete. A declared mission mode with no dissipation entry is unknown,
  not zero, and a map carrying a mode the mission does not declare means
  the two sides are working from different mode lists.
- Thermal control disturbs attitude through photon recoil off an offset
  radiating surface: F = e * sigma * A * T^4 / c, torque F times the moment
  arm to the centre of mass. It is a micronewton-metre effect that scales
  as the fourth power of radiator temperature, so a hot-case radiator is
  the driving condition, and it belongs in the attitude disturbance budget
  alongside solar pressure and aerodynamic terms.

## Workflow

1. Validate the regulated bus range and each heater circuit: positive
   resistance, a duty cycle inside zero to one, a named prime or redundant
   branch, a switch rating and derating factor.
2. Evaluate every circuit at both ends of the bus, keeping the top-of-bus
   power and current as the sizing case, and compute the fractional
   headroom against the derated switch rating.
3. Sum the peak simultaneous demand, counting redundant branches only when
   both branches can credibly be live, and the duty-weighted orbit-average
   demand from prime branches.
4. Compare both demands with their allocations using a named tolerance, so
   a circuit set sized exactly on its allocation is not failed by
   representation error at the boundary.
5. Build the per-mode dissipation table, refusing a declared mode with no
   figure and a figure for a mode the mission does not declare.
6. Sum the recoil disturbance torque of every offset radiating surface at
   its hot-case temperature and compare it with the attitude allocation.
7. Report circuit records, both demands, the dissipation table, the torque
   and every finding: peak overrun, average overrun, switch headroom
   exhausted, or disturbance torque over allocation.

## Pitfalls

- Sizing heaters at nominal bus voltage. The allocation and the switch are
  both worst case at the top of the range, and the few percent difference
  is exactly the band in which a circuit passes on paper and trips in test.
- Putting a redundant heater branch into the orbit-average demand. The
  redundant branch does not run alongside the prime one in normal
  operation; counting it inflates the energy balance and hides a real peak
  problem behind a fictitious average one.
- Comparing current against the nameplate switch rating. The power
  subsystem imposes a derating factor; the compliant limit is the derated
  value, and using the nameplate silently consumes the derating.
- Reading a missing mode dissipation as zero. A survival or transfer mode
  left out of the table is the mode most likely to drive the heater budget,
  and its absence is a data gap to close, not a zero to sum.
- Leaving thermal recoil out of the attitude disturbance budget because it
  looks small. It is steady, it is body-fixed, and on a spacecraft with an
  offset radiator it accumulates momentum in one direction, which is what
  sizes the desaturation interval.

## Behavior contract (gate 3)

Bus range validation, per-circuit power and current at both bus ends,
derated switch headroom, peak and orbit-average demand construction with
redundancy handling, per-mode dissipation completeness, radiator recoil
force and torque, and the aggregate assessment are exercised by the gate 3
contract test: scripts/test_e31_electrical_aocs_interface_requirements.py
against scripts/e31_electrical_aocs_interface_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e31_electrical_aocs_interface_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
