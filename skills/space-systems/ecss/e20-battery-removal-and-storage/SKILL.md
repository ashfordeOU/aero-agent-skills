---
name: e20-battery-removal-and-storage
description: "Use when plan, verify and record the pre-launch removal, replacement or storage of a spacecraft battery module under ECSS-E-ST-20C clause 5.6.4: categorize the module access path (direct-hatch-access, panel-removal, harness-demate, stack-teardown or non-removable), project the open-circuit state of charge a stored module reaches from its temperature-corrected self-discharge rate, screen the storage envelope for temperature excursion, deep-discharge, shelf-life and humidity breaches, derive the delta re-verification task set the operation triggers, and decide whether the module keeps its acceptance status or has to re-establish it. Trigger: ecss, e-st-20-electrical-scope, battery-module-removal, pre-launch-battery-replacement, battery-storage-envelope, open-circuit-self-discharge, maintenance-charge-interval, delta-reverification-scope, acceptance-status-retention."
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
  tags: [ecss, e-st-20-electrical-scope, e20-battery-removal-and-storage, battery-module-removal, battery-storage-envelope, open-circuit-self-discharge, delta-reverification-scope, acceptance-status-retention]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Battery Removal and Storage (space-systems/ecss/e20-battery-removal-and-storage)

Use when the task is the ECSS-E-ST-20C clause 5.6.4 case: a battery
module must be removable or replaceable on the integrated spacecraft
before launch, and the removal plus the storage interval that follows
must not quietly destroy the acceptance status the module already
holds.

## Domain quick reference

- Clause 5.6.4 is a design-for-access requirement with a verification
  consequence. The design side asks whether the module can be taken
  out at all; the verification side asks what has to be re-done
  afterwards. A module that is physically reachable but whose removal
  forces a full re-acceptance has not satisfied the intent.
- The access path is the driver. Five paths are distinguished, ordered
  by how much qualified hardware they disturb: direct-hatch-access and
  panel-removal reach the module without breaking a qualified
  electrical interface; harness-demate breaks the connector interface
  and therefore pulls in continuity and bonding checks; stack-teardown
  disturbs the mechanical load path as well and pulls in a capacity
  retest and a workmanship vibration retest; non-removable means the
  clause is not met at all, whatever the storage plan says.
- Storage is a second, independent way to lose acceptance status. A
  removed module sits on open circuit and self-discharges. The rate is
  strongly temperature dependent -- take it as doubling for every 10 K
  above a 20 degC reference and halving for every 10 K below -- so the
  state of charge reached after a storage interval is a computed
  number, not a stated one. Four envelope parameters are screened:
  storage temperature band, the deep-discharge floor the cells must
  never drop below, the shelf-life limit, and the humidity limit.
- The maintenance charge interval falls out of the same model: the
  days of open-circuit storage before the module drifts from its
  as-stored state of charge down to its floor. It is the schedule
  constraint the storage procedure has to respect, and it shortens by
  a factor of four for every 20 K of extra storage temperature.
- Acceptance status resolves to one of three states: preserved subject
  to a delta re-verification, invalidated because the required tasks
  exceed the delta allowance agreed for the programme, or invalidated
  because the module was never removable. The first is the only
  passing outcome, and only when the storage envelope is also clean.

## Workflow

1. Validate the module record: identifier, access path, state of
   charge and rate figures, the storage band, the shelf-life limit and
   the humidity limit. Reject an unknown access path, a percentage
   outside 0..100, an inverted temperature band, or a starting state
   of charge that is already at or below the floor.
2. Categorize the access path and read off two things: whether the
   module is removable at all, and which qualified interfaces the
   removal breaks.
3. Compute the temperature-corrected self-discharge rate, project the
   state of charge at the end of the storage interval, and compute the
   maintenance charge interval from the same rate.
4. Screen the storage envelope for the four breach types -- temperature
   excursion, deep discharge below the floor, shelf-life exceeded,
   humidity limit exceeded. A value exactly at a limit is inside it.
5. Build the delta re-verification task set: the tasks the access path
   forces, plus one task per storage breach, de-duplicated and kept in
   a stable order.
6. Compare that set against the programme's delta re-verification
   allowance and resolve the acceptance state. The module is compliant
   only when the state is preserved and no storage breach was raised.

## Pitfalls

- Reading "the module can be removed" as clause satisfaction and
  stopping there. Removability is necessary, not sufficient; the
  question the clause actually asks is whether acceptance status
  survives, and that is decided by the re-verification task set, not
  by the geometry.
- Treating the stored state of charge as the as-removed state of
  charge. Open-circuit self-discharge over a multi-month storage
  interval is the normal way a module arrives at re-installation
  already below its floor, and a warm store makes it far faster than a
  room-temperature figure suggests.
- Applying a single self-discharge rate regardless of store
  temperature. A module held at 40 degC drains four times as fast as
  the same module at 20 degC, so a maintenance charge interval derived
  at the reference temperature is optimistic by the same factor.
- Letting a storage breach be "closed" by noting it and moving on. A
  deep-discharge excursion or an exceeded shelf life adds a
  re-verification task, and that task then has to fit inside the delta
  allowance like any other -- a breach can be what pushes the module
  from preserved into invalidated.
- Allowing a task the programme never agreed to as a delta activity to
  be silently absorbed into the allowance. The allowance is an input
  to the assessment, not something the assessment gets to widen.

## Behavior contract (gate 3)

The module validation, access-path categorization, self-discharge and
storage-projection arithmetic, envelope screening, task-set derivation
and acceptance-state resolution are exercised by the gate 3 contract
test: test_e20_battery_removal_and_storage.py against
e20_battery_removal_and_storage_logic.py (stdlib unittest, offline,
deterministic). Run: `python3 scripts/test_e20_battery_removal_and_storage.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
