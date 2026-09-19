---
name: e3301-release-locking-devices-incl-pyrotechnics
description: "Design a spacecraft release or locking device and verify it against ECSS-E-ST-33-01C clauses 4.7.5.4.12 and 4.7.6. Use when the task is choosing between pyrotechnic and non-explosive actuation, showing that no single initiator or firing path leaves an appendage restrained, grading the induced separation shock at each neighbouring unit against its qualified level, confirming the lock carries the worst-case launch preload positively rather than by friction, and allocating released particulate and gas against the sensitive-surface budget. Trigger: ecss, e-st-33-01-mechanisms-scope, hold-down-release-redundancy, pyrotechnic-separation-shock-margin, release-device-contamination-allocation, locking-device-preload-margin, non-explosive-actuator-selection, release-single-point-failure."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-release-locking-devices-incl-pyrotechnics, hold-down-release-redundancy, pyrotechnic-separation-shock-margin, release-device-contamination-allocation, locking-device-preload-margin, non-explosive-actuator-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Release and Locking Devices, Pyrotechnic and Non-Explosive (space-systems/ecss/e3301-release-locking-devices-incl-pyrotechnics)

Use when the task is the release-and-locking design step of
ECSS-E-ST-33-01C clauses 4.7.5.4.12 and 4.7.6 -- deciding how a
mechanism is held through launch, how it is let go on command, and
showing that the letting-go neither fails silently nor damages the
neighbourhood it fires into.

## Domain quick reference

- The release function and the locking function are separate duties that
  the same hardware often performs. The lock has to survive a launch
  environment that lasts minutes at high load; the release has to work
  once, on command, years later. A design graded only on one of the two
  is graded on half its job.
- Redundancy is asked of the energetic element and of the circuit that
  reaches it, not of one or the other. Two initiators sharing one firing
  path still fail together when the path opens; two paths into one
  initiator still fail together when the initiator misfires. Each
  redundant leg is also required to release on its own, so a pair that
  only works together is one device, not two.
- A release is not a demonstrated release until something confirms it.
  Without a confirmation signal a failed release and a slow one look
  identical from the ground, and the recovery timeline then rests on
  guesswork.
- Firing a one-shot energetic device puts a high-frequency transient
  into the structure. The level reaching a neighbouring unit falls with
  distance and with every structural joint on the path, so shock
  compatibility is a per-unit comparison of the level that actually
  arrives against the level that unit was qualified to, carried with
  margin in dB.
- Non-explosive means -- thermal knife, shape-memory element, paraffin
  actuator, split spool, motorised nut -- trade the shock and
  contamination problem for a slower, power-hungry and often
  temperature-sensitive release. They do not trade away the redundancy
  requirement.
- Contamination is a budget, not a property of one device. Particulate
  and gaseous release from every device on the vehicle is summed and
  compared with what the sensitive surfaces -- optics, radiators, solar
  cells -- can tolerate.

## Workflow

1. Validate each device record: identifier, actuation means, initiator
   count, independent firing-path count, held preload, worst-case launch
   load. An unrecognised actuation means is an input error, because its
   failure modes are not the ones this assessment grades.
2. Grade redundancy for every mission-critical device: at least two
   initiators, at least two independent firing paths, and a declared
   release confirmation. A device explicitly marked non-critical is
   exempt and is recorded as exempt rather than silently skipped.
3. For each neighbouring unit, propagate the source level through the
   declared distance and joint count, then compare the arriving level
   with that unit's qualified level as a margin in dB against the
   required value.
4. Grade the lock: the fractional margin of held preload over worst-case
   load against the required margin, plus an explicit positive-lock
   declaration. A friction grip without a positive feature is a finding
   even when its numerical margin passes.
5. Sum particulate and outgassed release across the device set and
   compare with the sensitive-surface budget.
6. Report per-device records and the aggregated finding list; the design
   is compliant only when the list is empty.

## Pitfalls

- Counting two initiators as redundancy when they sit on one firing
  circuit. The circuit is then the single-point failure, and the
  initiator count says nothing about it.
- Grading separation shock against the source level instead of the level
  that arrives. Distance and intervening joints can take an order of
  magnitude out of the transient, and grading at the source both hides
  real exceedances near the device and invents false ones far from it.
- Treating a non-explosive actuator as inherently redundant because it
  is resettable. Resettability is a ground-test convenience; in flight a
  single heater circuit is still a single-point failure.
- Letting the preload margin stand in for the lock quality. A high
  preload held only by friction still walks loose under a vibration
  environment, so the positive-lock feature is graded separately.
- Budgeting contamination per device. One device inside its own
  allocation says nothing about a set of eight, and the sensitive
  surface sees the sum.
- Widening the required margin to make an exact-equality case pass. An
  equality at the limit is a representation question, absorbed by the
  named tolerance inside the comparison; the required value stays as
  specified.

## Behavior contract (gate 3)

The device validation, redundancy grading, shock propagation and margin
comparison, locking-preload grading and contamination summation are
exercised by the gate 3 contract test:
scripts/test_e3301_release_locking_devices_incl_pyrotechnics.py against
scripts/e3301_release_locking_devices_incl_pyrotechnics_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_release_locking_devices_incl_pyrotechnics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
