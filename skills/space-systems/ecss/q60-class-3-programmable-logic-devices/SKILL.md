---
name: q60-class-3-programmable-logic-devices
description: "Derive the verification set a programmable logic device owes in class 3 equipment under ECSS-Q-ST-60C clause 6.6.4, then grade the design against it: assemble the base objectives, what the function criticality adds and what the configuration technology adds on top, name the objectives never performed, measure functional and statement coverage against their floors, take the timing margin left standing in the clock period, test the single event mitigation a volatile or critical design owes, and check the design data outlives the mission and a reprogrammable part names its control. Use when a class 3 device is developed, reused or maintained. Trigger: ecss, q-st-60c-clause-6-6-4, class-3-programmable-logic-device, pld-verification-objective-set, pld-coverage-floor-margin, pld-timing-closure-margin, pld-design-data-retention."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-3-programmable-logic-devices, class-3-programmable-logic-device, pld-verification-objective-set, pld-coverage-floor-margin, pld-timing-closure-margin, pld-design-data-retention]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Programmable Logic Devices (space-systems/ecss/q60-class-3-programmable-logic-devices)

Use when the task is the clause 6.6.4 question of ECSS-Q-ST-60C: a
programmable logic device is going into class 3 equipment, and three sets of
rules meet on it — how the design is developed, what a reuse claim has to
carry, and what keeps the design correct and recoverable for as long as the
equipment flies. Class 3 reduces the verification behind that design. It does
not reduce it uniformly, and it does not reduce it to nothing.

## Domain quick reference

- The device is bought as a component and flown as a design. Nothing in the
  component purchase verifies the logic that was loaded into it, so the
  verification set is the only place that work appears.
- The set is assembled from three sources, not chosen from one. A class 3 base
  set applies to every design; the function criticality adds to it; the
  technology holding the configuration adds to it again. A non-critical
  function on a volatile part still owes the configuration work.
- Coverage is a measurement with a floor, not a target to describe. Functional
  and statement coverage are separate numbers with separate floors, and a
  design that reads well in review and measures at sixty percent has been
  reviewed, not verified.
- A margin is more useful than a verdict. Reporting how far a coverage or a
  timing number sits above its floor tells the project where it actually is;
  reporting only pass or fail hides a design sitting a thousandth above the
  line from everyone who would care.
- Timing closure is a share of the period, not a picosecond count. The margin
  is what is left of the required clock period after the achieved one, and it
  is the term that moves when a device is re-placed, re-routed or run at a
  corner nobody simulated.
- Single event mitigation follows two triggers. A critical or important
  function owes a declared approach because of what it does; a volatile part
  owes one because of what it is built from, and an upset in a configuration
  cell rewrites the logic rather than the data.
- Maintenance is a retention question with a date. The design data has to
  outlive the mission plus the margin the project keeps after it, and a
  reprogrammable device additionally has to name who may reprogram it and
  under what procedure. A field-reprogrammable part with no named control is
  an open door, not a feature.

## Workflow

1. Validate the design record: the function criticality, the configuration
   technology, the origin, the objectives performed, both coverage
   measurements, both clock periods, the mitigation declaration and the two
   retention figures.
2. Assemble the required objective set from the base, the criticality and the
   technology, and name every one the record does not claim to have performed.
3. Read the coverage floors the criticality sets, measure both coverages
   against them and report the signed margin in each case.
4. Compute the timing margin as the share of the required clock period left
   standing, and test it against its floor with a tolerance rather than a bare
   comparison of two computed floats.
5. Test the mitigation declaration wherever the criticality or the technology
   demands one.
6. Check the design data retention against the mission plus the policy margin,
   and check a reprogrammable device names its reprogramming control.
7. Route the design: new to the full flow, modified to a delta verification,
   unchanged and complete to a reviewed reuse, unchanged with a gap back to
   the delta flow.
8. Return the flow, the required set, the gaps, the margins and one verdict
   naming the first thing that stops the programme.

## Pitfalls

- Reading class 3 as a licence to skip the verification set. The set shrinks
  by table, and the tables still name four objectives for the mildest design
  there is.
- Taking the objectives from the criticality alone. The technology adds its
  own, and a volatile part on a non-critical function is exactly the case
  where that is forgotten.
- Quoting one coverage number. Functional and statement coverage answer
  different questions, and a design can saturate one while leaving whole
  branches of the other untouched.
- Comparing a computed margin with its floor by bare arithmetic. Both sides
  are computed, a design sitting exactly on its floor is a real case, and the
  last place of a float is not where that decision should be made.
- Declaring mitigation as an architecture statement and leaving it there. The
  declaration is owed as a recorded analysis, and a triple-redundant register
  nobody analysed is a claim about the intent.
- Setting the design data retention to the mission length. The mission is when
  the data is needed in flight; the margin after it is when somebody has to
  answer for an anomaly, and the design that cannot be rebuilt cannot be
  investigated.

## Behavior contract (gate 3)

The policy merge, design record validation, three-source objective assembly,
missing objective detection, completeness share, coverage floors and signed
margins, tolerant floor comparison, timing margin, mitigation requirement
test, retention requirement and reprogramming control check, flow routing and
verdict precedence are exercised by the gate 3 contract test:
scripts/test_q60_class_3_programmable_logic_devices.py against
scripts/q60_class_3_programmable_logic_devices_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_programmable_logic_devices.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
