---
name: q6013-class-1-programmable-devices
description: "Assess the programming and post-programming control of a programmable device procured to the highest assurance class under ECSS-Q-ST-60-13C clause 4.6.4: categorize the programming site as component-manufacturer, approved programming-centre or uncontrolled, test the programmer against its calibration interval, grade the post-programming readback against the zero-mismatch rule, build the screen plan for the storage technology, size the destructive-sample screens, and convert the data-retention requirement into a bake duration through an Arrhenius acceleration factor before returning an accept, accept-with-deviation or reject disposition. Use when a Class 1 lot of antifuse, one-time-programmable, EEPROM or flash parts needs its programming evidence judged. Trigger: ecss, q-st-60-13c, class-1-programmable-device, programming-site-control, post-programming-readback, retention-bake-duration, antifuse-fpga-programming, otp-prom-pattern-verification, programming-equipment-calibration."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-programmable-devices, class-1-programmable-device, programming-site-control, post-programming-readback, retention-bake-duration, programming-equipment-calibration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 Programmable Devices — Programming Control (space-systems/ecss/q6013-class-1-programmable-devices)

Use when the task is the programming and post-programming control of a
programmable device bought under the highest assurance class of
ECSS-Q-ST-60-13C clause 4.6.4 — deciding whether the pattern was written
under procurement control, whether the write was proven, and what has to
be run on the parts afterwards before the lot can be accepted.

## Domain quick reference

- The highest assurance class does not treat programming as a user
  operation. The site that writes the pattern is part of the
  procurement: the component manufacturer, an approved programming
  centre or an approved user facility are inside the control envelope; a
  facility with no approval is outside it, and a lot programmed there
  has no evidence chain no matter how clean the readback looks.
- Programming equipment carries a calibration interval. Equipment run
  past that interval does not automatically condemn the lot, but it
  moves the write from evidence to claim: the pattern has to be read
  back on calibrated equipment before the lot can be dispositioned, and
  the result is a deviation rather than a straight acceptance.
- The readback acceptance rule at this class is zero mismatched bits.
  A mismatch fraction is useful for reporting the size of the problem,
  never for arguing that a small fraction is tolerable.
- The post-programming screen plan follows the storage technology, not
  the package. Antifuse and fuse-link parts take thermal cycling because
  the concern is the integrity of the formed link; floating-gate, EEPROM
  and flash parts take a retention bake because the concern is stored
  charge. Flash takes both.
- A retention bake is an accelerated demonstration, so its duration is
  derived, not quoted: an Arrhenius acceleration factor between the use
  temperature and the bake temperature at the technology's activation
  energy turns the required retention hours into bake hours. Changing
  the bake temperature changes the duration; it does not change the
  requirement.
- A retention bake consumes the parts it is run on, so it is sampled
  from the delivered lot with a floor, while readback, thermal cycling
  and the electrical endpoint run on every delivered part.
- Traceability is a disposition input in its own right. A lot with no
  lot identifier and no programming record cannot be accepted even when
  every measured result is clean.

## Workflow

1. Categorize the programming site and stop the acceptance path if the
   pattern was written outside the procurement control envelope.
2. Check the programming equipment against its calibration interval;
   an exactly-expiring interval is still valid, and an expired one needs
   a re-verification record to become a deviation instead of a refusal.
3. Grade the readback: any mismatched bit is a refusal, and the mismatch
   fraction is reported alongside it for the failure analysis.
4. Build the screen plan from the storage technology and append a
   radiation lot sample only when the procurement calls for one.
5. Size each screen against the delivered lot, sampling the destructive
   screens with a floor and covering the lot for the rest.
6. Derive the bake duration from the retention requirement, the use and
   bake temperatures and the activation energy; compare it with the bake
   actually performed, absorbing representation error at the boundary
   with a named tolerance rather than by shortening the requirement.
7. Confirm the lot identifier and programming record, then return the
   disposition — accept, accept-with-deviation or reject — with every
   finding that drove it.

## Pitfalls

- Accepting a clean readback from an uncontrolled facility. The readback
  proves the bits, not the provenance; the site category is a separate
  and blocking input.
- Treating a small mismatch fraction as a yield figure. At this class the
  rule is zero mismatched bits; a fraction is a report field, not a
  threshold to argue against.
- Quoting a fixed bake duration from another programme. The duration
  belongs to a temperature pair and an activation energy; reusing hours
  derived at a different bake temperature silently changes the retention
  actually demonstrated.
- Running the retention bake on the whole delivered lot. It is
  destructive, so it is sampled; running it on everything leaves nothing
  to deliver and is not what the sampling rule asks for.
- Letting an expired calibration pass silently because the parts work.
  Expired equipment converts the write into an unproven claim, and the
  only route back is a re-verification record and a deviation.
- Dispositioning on measurements alone. A missing lot identifier or
  programming record is a refusal even when every screen is clean.

## Behavior contract (gate 3)

The site categorization, calibration check, readback grading, screen-plan
construction, sample sizing, Arrhenius bake derivation and disposition
are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_programmable_devices.py against
scripts/q6013_class_1_programmable_devices_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_programmable_devices.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
