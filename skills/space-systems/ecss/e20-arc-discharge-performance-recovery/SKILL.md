---
name: e20-arc-discharge-performance-recovery
description: "Use when judge whether a spacecraft function interrupted by an electrostatic arc returns to its specified performance under ECSS-E-ST-20C clause 6.3.4.3: categorize the event as a self-extinguishing primary discharge or a power-fed sustained secondary arc, derive the outage from arc onset to restored service and check it against the allowance the function holds, compare every post-arc parameter against its specified level in the correct direction of merit, quantify the residual shortfall that never comes back, and reject a recovery that depends on a ground loop slower than the permitted outage. Trigger: ecss, e-st-20c-clause-6-3-4-3, arc-discharge-recovery, electrostatic-discharge-outage, sustained-secondary-arc, post-arc-performance-recovery, autonomous-recovery-latency, residual-performance-shortfall."
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
  tags: [ecss, e-st-20-electrical-scope, e20-arc-discharge-performance-recovery, arc-discharge-recovery, electrostatic-discharge-outage, sustained-secondary-arc, post-arc-performance-recovery, autonomous-recovery-latency, residual-performance-shortfall]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Arc Discharge Performance Recovery (space-systems/ecss/e20-arc-discharge-performance-recovery)

Use when the task is the clause 6.3.4.3 allowance of ECSS-E-ST-20C --
deciding whether a function that drops out while an electrostatic
discharge is happening is acceptable, on the strength of how short the
interruption was and whether the specified performance actually came
back once the event passed.

## Domain quick reference

- The allowance applies to one family of event only. A primary
  discharge -- surface dielectric blowoff, a triple-junction event,
  internal dielectric breakdown, harness flashover -- releases stored
  charge and extinguishes itself; it is the transient the clause
  tolerates. A sustained secondary arc is different in kind: the power
  system keeps feeding it after the stored charge is gone, so it does
  not end on its own and cannot be reasoned about as a brief outage at
  all. Categorizing the event first is what keeps a design finding from
  being processed as a recovery case.
- The outage is the interval between arc onset and the moment service
  is back, both read on one mission clock, and it is compared against
  the allowance the function's specification grants. The allowance is
  per function, not per spacecraft: a telemetry channel and an attitude
  actuator do not carry the same tolerance for the same event.
- Coming back means every performance parameter meets its specified
  level again, and the comparison has to respect the direction of
  merit. Radiated power, pointing accuracy and data rate improve
  upward; ripple, noise floor and error rate improve downward. Working
  in a ratio oriented so that one means the specification is met makes
  the two directions comparable and makes any shortfall a single
  percentage.
- A shortfall that survives the event is residual degradation -- the
  arc left permanent damage rather than a transient upset. The
  programme may grant a residual allowance, but the default position is
  that nothing is left behind, and any shortfall past the allowance is
  a finding against the event.
- How the function comes back matters as much as whether it does. An
  autonomous recovery closes inside the spacecraft. A ground-commanded
  recovery only satisfies the clause if the whole ground loop --
  detection, decision, uplink -- closes inside the same outage the
  function is allowed, which for a sub-second allowance it never does.

## Workflow

1. Categorize the arc event; a sustained secondary arc is reported
   immediately and is not assessed as a brief outage.
2. Derive the outage as restored-service time less arc-onset time on
   one clock; reject a restoration timestamped before the onset.
3. Compare the outage against the allowance the function holds and
   flag an interruption longer than permitted.
4. For each post-arc parameter, build the recovery ratio oriented by
   its direction of merit so a value of one means the specified level
   is met.
5. Convert any ratio below one into a residual shortfall in percent
   and flag a shortfall past the residual allowance, defaulting the
   allowance to nothing left behind.
6. Check the recovery mode: an autonomous recovery passes, a
   ground-commanded recovery passes only when the ground response
   latency fits inside the outage allowance.
7. Aggregate the arc-family, outage, performance and autonomy
   findings; the event is acceptable only when all four lists are
   empty.

## Pitfalls

- Processing a sustained secondary arc through the outage allowance.
  The event never ends on its own, so the arithmetic produces a number
  and the number is meaningless; the finding is the arc itself.
- Comparing a lower-is-better parameter as though more were better. A
  ripple figure that doubled after the arc reads as a ratio above one
  under the wrong orientation and a damaged unit is reported as fully
  recovered.
- Reading "service restored" from the first telemetry frame that
  arrives rather than from the moment specified performance is met
  again. The link can be back long before the parameter is, and the
  clause asks about performance, not about signal presence.
- Accepting a recovery that needs a ground command without checking
  the loop time. A sub-second allowance and a ground loop measured in
  minutes are not reconcilable, and no amount of procedure closes that
  gap.
- Treating a small residual shortfall as noise. The default allowance
  is zero; a residual is permanent damage and belongs on the record
  even when it is small, unless a residual allowance was actually
  granted.
- Letting clock arithmetic decide a boundary case. An outage that
  physically equals its allowance is a difference of two timestamps
  and can land a few representation units above it, so the equality is
  absorbed in the comparison rather than by relaxing the allowance.

## Behavior contract (gate 3)

The arc categorization, outage derivation, allowance comparison,
oriented recovery ratio, residual shortfall and recovery-autonomy logic
is exercised by the gate 3 contract test:
scripts/test_e20_arc_discharge_performance_recovery.py against
scripts/e20_arc_discharge_performance_recovery_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_arc_discharge_performance_recovery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
