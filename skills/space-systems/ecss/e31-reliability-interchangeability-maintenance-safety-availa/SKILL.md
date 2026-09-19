---
name: e31-reliability-interchangeability-maintenance-safety-availa
description: "Evaluate the dependability provisions of a thermal control design against ECSS-E-ST-31C clauses 4.4.9 to 4.4.13. Use when the question is whether the heater chain survives a single failure rather than whether it is warm enough: building the mission reliability of redundant heater lines from their element failure rates, comparing a series thermostat stack against a parallel one for the failure that is actually hazardous, grading a spare unit's interface parameters for interchangeability without requalification, sizing the availability of a maintainable item from its repair time, and reporting the fail-safe verdict. Trigger: ecss, e-st-31-thermal-control-scope, redundant-heater-line-reliability, thermostat-series-parallel-topology, thermal-fail-safe-topology, thermal-unit-interchangeability, thermal-control-availability, heater-single-failure-tolerance."
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
  tags: [ecss, e-st-31-thermal-control-scope, e31-reliability-interchangeability-maintenance-safety-availa, redundant-heater-line-reliability, thermostat-series-parallel-topology, thermal-fail-safe-topology, thermal-unit-interchangeability, thermal-control-availability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Reliability, Interchangeability, Maintenance, Safety and Availability (space-systems/ecss/e31-reliability-interchangeability-maintenance-safety-availa)

Use when the task is the dependability side of thermal control design
under ECSS-E-ST-31C clauses 4.4.9 to 4.4.13 — the redundancy in the
heater chain, the topology that makes a thermostat failure safe, the
interchangeability of a spare, the maintenance the design imposes, and
the availability that comes out of the two.

## Domain quick reference

- A heater line is a series chain: element, wiring, switch and the
  control device all have to work for the line to heat. Redundancy is
  applied across whole lines, so line reliability multiplies inside a
  line and combines as a parallel block across lines.
- Redundancy across lines only buys anything when the lines do not share
  a part. A shared switch or a shared temperature sensor sits in series
  with the whole parallel block and caps the redundant reliability at
  its own.
- A thermostat has two failure modes and they are not symmetric. Stuck
  open means no heat; stuck closed means no cut-off. Two thermostats in
  series protect against the stuck-closed runaway and double the
  exposure to stuck-open loss of heating; two in parallel do the exact
  reverse. Picking the topology therefore starts from which outcome is
  the hazardous one for that item, not from a general preference.
- Fail-safe means the credible failure leaves the item in the tolerable
  state. On a propellant line the hazardous outcome is freezing, so the
  heating path is made redundant; on a battery the hazardous outcome is
  runaway, so the cut-off path is.
- Interchangeability is an interface property, not a part number. A
  spare swaps in without requalification when its mounting conductance,
  heater resistance and footprint all sit inside the declared tolerance
  band of the nominal.
- Availability is only defined where repair is possible. Reporting an
  availability figure for an item nobody can reach in flight quietly
  converts a reliability problem into an optimistic ratio.

## Workflow

1. Validate every failure rate as non-negative and the mission duration
   as positive; a zero-hour mission is an input error, not a perfect one.
2. Build each heater line as a series product of its element
   reliabilities over the mission, then combine the lines as a parallel
   block and place any shared element in series with that block.
3. Take the thermostat count and its stuck-open and stuck-closed
   probabilities, form the loss-of-heating and loss-of-cut-off
   probabilities for both the series and the parallel topology, and
   recommend the topology that minimises the probability of the
   hazardous outcome declared for the item.
4. Grade the spare against the nominal parameter by parameter, using a
   relative tolerance, and raise a finding for each parameter outside
   its band.
5. Compute availability only for items declared repairable, from their
   mean time between failures and mean repair time; refuse it for the
   rest rather than reporting an optimistic figure.
6. Report the line reliability, the recommended topology, the
   interchangeability findings, the availability and the overall
   verdict, compliant only when each declared threshold is met.

## Pitfalls

- Multiplying redundant lines instead of combining them in parallel.
  Series arithmetic on a redundant block reports a reliability below the
  single line it replaced.
- Claiming redundancy through a shared part. The common switch, the
  common sensor or the common bus feed caps the block, and the
  parallel figure is fiction until that element is counted in series.
- Choosing the thermostat topology by habit. Series and parallel each
  make one failure mode worse, so the choice is a consequence of which
  outcome is hazardous for that item and has to be re-made per item.
- Treating a redundant heater as covering a stuck-closed thermostat. The
  redundant path adds heat; it does not remove it, and the runaway case
  needs a cut-off, not another line.
- Accepting a spare on the part number. Requalification is avoided by
  the interface parameters sitting inside their tolerance, and a
  mounting conductance out of band changes the temperature the spare
  runs at.
- Quoting availability for an unreachable item. Without a credible
  repair the figure is a reliability number wearing a better ratio.

## Behavior contract (gate 3)

Exponential element reliability, series and parallel combination,
shared-element capping, thermostat topology comparison against the
declared hazardous outcome, interchangeability tolerance grading and
availability with its repairability guard are exercised by the gate 3
contract test:
scripts/test_e31_reliability_interchangeability_maintenance_safety_availa.py
against
scripts/e31_reliability_interchangeability_maintenance_safety_availa_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e31_reliability_interchangeability_maintenance_safety_availa.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
