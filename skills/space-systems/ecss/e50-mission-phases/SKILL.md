---
name: e50-mission-phases
description: "Verify that a mission states its communication requirements phase by phase, as ECSS-E-ST-50C Rev.2 clause 5.6.7 asks, rather than once for the whole mission. Use when early operations, transfer and routine phases need different links and services from the same hardware: check the phases abut with no uncovered interval and no two phases claiming the same hours, that every service is allocated to a link the phase actually has, and that a phase marked critical still carries essential telemetry and an emergency command path. Trigger: ecss, e-st-50c-clause-5-6-7, per-phase-communication-requirements, mission-phase-timeline-contiguity, phase-service-link-allocation, critical-phase-emergency-command, leop-communication-services."
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
  tags: [ecss, e-st-50-communications-scope, e50-mission-phases, e-st-50c-clause-5-6-7, per-phase-communication-requirements, mission-phase-timeline-contiguity, phase-service-link-allocation, critical-phase-emergency-command, leop-communication-services]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Mission Phases (space-systems/ecss/e50-mission-phases)

Use when the task is clause 5.6.7 of ECSS-E-ST-50C Rev.2: stating what the
communication system has to do in each phase of the mission, and checking
that the phases together describe the whole of it.

## Domain quick reference

- One averaged requirement describes no phase. A spacecraft needing an
  omnidirectional emergency path in early operations and a high gain science
  downlink later is two communication systems in one set of hardware, and
  the average is a system that serves neither well.
- An uncovered interval is not a quiet period. It is a stretch of mission
  for which nobody wrote a communication requirement, so nothing sizes the
  link during it and nothing is verified against it.
- An overlap is the same defect wearing the other face. Two phases claiming
  the same hours usually name different links for them, and which one
  operations follows is decided on the day.
- Allocation is to a link the phase has, not to a link the mission has. A
  service pointed at a high gain antenna during a phase that only has the
  omni reads as allocated on the page and is unavailable in flight.
- Criticality changes what a phase owes. A phase marked critical has to be
  recoverable from, which means essential telemetry and an emergency command
  path on whatever link it does have — not on the best link the mission
  owns.
- Phases are written to abut exactly, so the contiguity test carries a
  relative tolerance. Deciding whether one phase ends where the next begins
  by the last bit of a float makes the verdict depend on the machine.
- Coverage and contiguity are different numbers. Overlapping phases can
  cover the whole span while still both claiming the same hours, so the
  covered duration counts an overlap once and the gaps are reported apart
  from it.

## Workflow

1. Normalise each phase: a name, a start and an end with the end strictly
   later, a boolean criticality, the links it has and the services it
   allocates to them.
2. Order the phases by start time with the name as a tie-break, and refuse a
   repeated phase name rather than silently keeping one.
3. Walk consecutive pairs and report every gap with its length and every
   overlap with the hours both phases claim, comparing with a relative
   tolerance so exact abutment is contiguous.
4. Take the mission span from the first start to the last end, and the
   covered duration as the union of the phases, so an overlap is counted
   once.
5. For each phase, report a phase with no link and a phase with no service
   as declaration gaps in their own right.
6. Difference each phase's allocated links against the links it has, and
   name every service left pointing at a link the phase does not carry.
7. For a phase marked critical, check the recovery services are present, and
   close with a ranked disposition: a timeline defect first, a declaration
   gap second, compliant only when neither stands.

## Pitfalls

- Writing one communication requirement for the mission. It sizes the link
  for an average that no phase flies, and the phase that needed the margin
  is the one that does not get it.
- Reading a gap in the timeline as a period with nothing to do. Something is
  happening; what is missing is the requirement, and the gap is where a
  spacecraft goes quiet with nobody having agreed it would.
- Treating overlapping phases as harmless because the span is covered. Both
  phases specify that interval, usually differently, and operations has to
  pick one without a rule.
- Allocating a service to a link from the mission inventory. The phase is
  the scope; a link that deploys later is not available now, however real it
  is in the drawing.
- Giving a critical phase the recovery services on the wrong link. The point
  of essential telemetry is that it works when the pointing does not, so
  allocating it to a steerable antenna defeats it.
- Deciding contiguity with a bare comparison. Phase boundaries are written
  to meet exactly, and an exact comparison on floating point turns a correct
  timeline into a gap on some hosts and not others.

## Behavior contract (gate 3)

Phase validation including the strict end-after-start rule and the boolean
criticality, timeline ordering with its tie-break and duplicate refusal, gap
and overlap detection at exact abutment, the union-based covered duration and
coverage fraction, stranded service detection, the critical phase recovery
set and the ranked disposition are exercised by the gate 3 contract test:
scripts/test_e50_mission_phases.py against
scripts/e50_mission_phases_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e50_mission_phases.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
