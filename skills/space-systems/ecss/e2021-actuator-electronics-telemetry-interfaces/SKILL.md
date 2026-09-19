---
name: e2021-actuator-electronics-telemetry-interfaces
description: "Assess whether the housekeeping of both actuator electronics chains really reaches both telemetry acquisition paths under ECSS-E-ST-20-21C clause 5.2.4. Use when the task is finding the measurements that go dark on one acquisition failure: check the arm, select and fire status and the firing current monitor of each chain, name the pairs never declared, separate the channels reaching one path from those reaching both, flag an unbuffered fan out that couples the two paths, then drop each acquisition path in turn and report the chain left with nothing readable. Trigger: ecss, e-st-20-21-actuation-scope, actuator-electronics-telemetry-interfaces, dual-path-housekeeping-routing, actuation-observability-coverage, unbuffered-acquisition-fanout, acquisition-path-loss-blindness."
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
  tags: [ecss, e-st-20-21-actuation-scope, e2021-actuator-electronics-telemetry-interfaces, dual-path-housekeeping-routing, actuation-observability-coverage, unbuffered-acquisition-fanout, acquisition-path-loss-blindness, actuator-arm-fire-status-telemetry]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuation Electronics — Actuator Electronics Telemetry Interfaces (space-systems/ecss/e2021-actuator-electronics-telemetry-interfaces)

Use when the task is the telemetry interface requirement of
ECSS-E-ST-20-21C clause 5.2.4 -- establishing that the housekeeping of
both actuator electronics chains is routed to the nominal and to the
redundant acquisition path, so that losing one acquisition path does
not leave an electronics chain healthy but unreadable.

## Domain quick reference

- The telemetry side fails more quietly than the command side. A
  command that cannot be sent announces itself; housekeeping that
  cannot be read looks like a nominal chain until the moment somebody
  needs to know whether it is armed.
- The routing question is which chain the measurement comes from and
  which acquisition paths it reaches. Both axes matter: a chain whose
  housekeeping goes out on one path only is observable today and dark
  after one acquisition failure, with the chain itself untouched.
- The parameters that carry the duty are the ones the actuation
  sequence turns on. Arm, select and fire status say where the chain
  stands in that sequence; the firing current monitor is the only
  evidence that a commanded pulse was actually delivered rather than
  merely ordered. A chain that reports three of those four cannot be
  operated through a contingency.
- A pairing of chain to acquisition path one to one is the usual
  shape of the defect, and it is invisible in a channel list because
  no channel is missing. Every parameter appears exactly once; it is
  the destination column that collapses the redundancy.
- Fanning one measurement out to two acquisition paths is the fix, and
  it introduces its own duty. An unbuffered fan-out couples the two
  paths through the source, so a short or an overvoltage on one path
  pulls the same measurement down on the other and turns a single
  acquisition failure back into a double one.
- The reportable result is per acquisition path: drop each one and
  name the chain left with no readable housekeeping at all. That case
  is worse than a missing parameter, because the operator has an
  electronics chain whose state cannot be established before
  committing to it.

## Workflow

1. Declare each housekeeping channel with its parameter, its source
   electronics chain, the acquisition paths it reaches and whether the
   fan-out is buffered. Refuse an unknown chain or path, an empty path
   list, a path listed twice and a channel declared twice for the same
   chain.
2. Compare the declared set against the parameters each chain owes and
   name the chain and parameter pairs that are absent, not merely the
   parameters.
3. Categorize the declared channels by the number of acquisition paths
   they reach: one path is a finding, two is the requirement.
4. Check the buffering of every channel that reaches both paths and
   raise a finding on each unbuffered fan-out. A single path channel
   is not a fan-out and does not carry this duty.
5. Remove each acquisition path in turn, list the required channels
   that survive, and name any electronics chain left with nothing
   readable.
6. Close with a verdict, the observability coverage as a fraction, and
   findings naming the chain, the parameter and the path at fault.

## Pitfalls

- Reading a complete channel list as complete routing. Every
  parameter can be present exactly once and the design still pair off
  each chain with one acquisition path; the gap lives in the
  destination column, not the parameter column.
- Counting a parameter without its chain. The requirement is per
  chain, so an arm status present from the nominal electronics and
  absent from the redundant one is a gap even though the parameter
  name appears in the list.
- Leaving the firing current monitor out because the status bits are
  there. The status says what was commanded; only the current monitor
  says what was delivered, and a contingency turns on exactly that
  difference.
- Fanning a measurement out to both acquisition paths with a bare
  wire. The redundancy it adds against an acquisition failure is paid
  back with a coupling that lets a fault on one path take the
  measurement down on both.
- Reporting coverage without the loss case. A coverage fraction says
  how much of the routing is doubled; only dropping each path in turn
  says whether an entire electronics chain goes dark.

## Behavior contract (gate 3)

Channel validation, the required chain and parameter set, absent
channel detection, single and dual path categorization, unbuffered
fan-out detection, observability coverage, the per-path loss report
and the compliance verdict are exercised by the gate 3 contract test:
scripts/test_e2021_actuator_electronics_telemetry_interfaces.py against
scripts/e2021_actuator_electronics_telemetry_interfaces_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2021_actuator_electronics_telemetry_interfaces.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
