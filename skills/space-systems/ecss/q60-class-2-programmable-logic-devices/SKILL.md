---
name: q60-class-2-programmable-logic-devices
description: "Plan the development, reuse and in-service maintenance of a programmable logic device flown in class 2 equipment under ECSS-Q-ST-60C clause 5.6.4: take the archive the declared design baseline has to hold and name what is missing, decide whether the toolchain behind that archive can still be stood up, route the design to a full development, a delta verification or a reviewed reuse, attach the duties the configuration technology carries once the unit has shipped, and count how often each one comes round over the mission. Use when a device is being reused or has to stay correct in orbit. Trigger: ecss, q-st-60c-clause-5-6-4, class-2-programmable-logic-device, pld-maintenance-archive, pld-toolchain-reproducibility, pld-configuration-technology-duties, pld-reuse-routing."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-2-programmable-logic-devices, class-2-programmable-logic-device, pld-maintenance-archive, pld-toolchain-reproducibility, pld-configuration-technology-duties, pld-reuse-routing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Programmable Logic Devices (space-systems/ecss/q60-class-2-programmable-logic-devices)

Use when the task is the clause 5.6.4 question of ECSS-Q-ST-60C: a
programmable logic device is going into class 2 equipment, and the rules that
apply are not only the ones that bought the package. They cover the design
inside it — how it is developed, what a reuse claim has to carry, and what
keeps it correct for as long as the equipment flies.

## Domain quick reference

- The device is two things at once. As a component it is bought against a
  specification and screened like any other. As a design it is something the
  project authored, and nothing in the component flow verifies the logic that
  was loaded into it.
- Maintenance is where class 2 puts its weight, and maintenance is an archive
  question before it is an engineering one. Source, constraints, post-route
  netlist, programming image checksum, verification testbench, toolchain
  version record, programming record and change log: a design missing any of
  the set its baseline demands cannot be touched again without being rebuilt
  from scratch.
- An unchanged reuse holds a smaller set than a new design. It does not need
  a change log, because nothing changed. The moment something does change,
  the set it has to hold is the full one.
- An archive whose toolchain cannot be stood up is a drawer of files. The
  toolchain record is reproducible when the installer was archived, a licence
  is still reachable, and the version is supported far enough ahead to cover
  a rebuild — not merely named in a report.
- Configuration technology fixes the in-service duties, and it fixes them
  independently of the route. A one-time device carries a programming and
  verification record and a control that nothing reconfigures it. A flash or
  EEPROM device carries write protection, reconfiguration control and either
  cycle counting or a retention margin review. A volatile device carries
  configuration memory integrity monitoring, a reload or scrub provision and
  power-up configuration timing control — the shortest intervals in the set,
  because its configuration is not held by the device between power cycles.
- Permitting reconfiguration after delivery adds a duty of its own on a
  device that can accept one, and means nothing at all on a device that
  cannot. Declaring it on a one-time part is a finding about the declaration,
  not about the part.
- Review counts come out of integer ceiling arithmetic against the mission
  length, so a mission landing exactly on an interval is one review, and a
  mission one month longer is two, on every machine.

## Workflow

1. Validate the case: configuration technology, declared design baseline, the
   archive held, the toolchain record and the mission length in months.
2. Validate the archive listing itself. An artefact nobody defined and an
   artefact listed twice are input errors, not gaps to be counted.
3. Take the gaps against what the declared baseline requires, and the share of
   the required set actually held.
4. Validate the toolchain record and decide reproducibility on the installer,
   the licence and the remaining support window against the margin.
5. Route the design: a short archive blocks every route; otherwise a new
   design to full development, a modified reuse to delta verification, an
   unchanged reuse to a reviewed reuse while the toolchain lives and to delta
   verification once it does not.
6. Attach the in-service duties the configuration technology carries, adding
   the reconfiguration duty only where the device can accept one.
7. Flag reconfiguration declared on a one-time programmable device.
8. Turn the duties into a schedule: interval per duty, review count over the
   mission by integer ceiling, and the total. Report the route, the gaps, the
   completeness, the duties, the schedule and every finding.

## Pitfalls

- Treating the component procurement as covering the device. Screening proves
  the silicon was sound; it says nothing about the logic that was loaded.
- Archiving the programming image and calling the design maintainable. The
  image reproduces the part, not the design: without source, constraints and
  the toolchain that built it, the next change starts from nothing.
- Recording the toolchain version and stopping there. A version nobody can
  install, licence or run is a version number, and the archive it stands
  behind is unusable on the day it is needed.
- Attaching duties from the route rather than from the technology. A reviewed
  reuse of a volatile device still needs its integrity monitoring and its
  reload provision; the route never removes them.
- Scheduling a volatile device on the same cadence as a one-time device. Its
  configuration is not held between power cycles, which is exactly why its
  intervals are the shortest in the set.
- Declaring in-flight reconfiguration on a one-time programmable part because
  the operations concept wanted it. The declaration is the defect; the part
  will not take it either way.

## Behavior contract (gate 3)

The policy validation, baseline artefact sets, archive validation, gap and
completeness measures, toolchain record validation and reproducibility test,
configuration technology duties, review interval arithmetic, maintenance
schedule and route selection are exercised by the gate 3 contract test:
scripts/test_q60_class_2_programmable_logic_devices.py against
scripts/q60_class_2_programmable_logic_devices_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_programmable_logic_devices.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
