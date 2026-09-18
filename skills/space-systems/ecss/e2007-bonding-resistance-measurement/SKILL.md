---
name: e2007-bonding-resistance-measurement
description: "Verify the bond-resistance evidence behind a spacecraft bonding schedule under ECSS-E-ST-20-07C clause 5.3.10. Use when the task is deciding which bonds owe a four-wire low-resistance measurement, setting aside the paths whose only role is electrostatic-charging control, confirming that a reading came from a current-injection pair and a separate voltage-sense pair inside the injection-current window, computing the bond resistance from the sensed voltage and the injected current, rejecting a two-wire reading whose lead and contact resistance is folded into the result, and grading each measured bond against the limit its purpose carries. Trigger: ecss, e-st-20-07c, four-wire-bond-resistance, kelvin-bond-measurement, charging-control-bond-exemption, bond-purpose-resistance-limit, current-injection-pair, voltage-sense-pair, two-wire-lead-resistance."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-bonding-resistance-measurement, four-wire-bond-resistance, kelvin-bond-measurement, charging-control-bond-exemption, bond-purpose-resistance-limit, current-injection-pair]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Bonding Resistance Measurement (space-systems/ecss/e2007-bonding-resistance-measurement)

Use when the task is the bond-resistance verification of
ECSS-E-ST-20-07C clause 5.3.10 -- deciding which bonds in the schedule
owe a measurement, checking that the measurement was made the only way
that can support a milliohm target, and grading the value it produced.

## Domain quick reference

- The measurement is a four-wire one, and the reason is arithmetic. A
  bond target sits in the low milliohms; the leads and probe contacts
  of an ordinary two-wire set sit in the tens of milliohms. A two-wire
  reading therefore reports its own probe set with the bond buried
  inside it, and no correction recovers the bond from that number.
  Four wires separate the two jobs: one pair injects a known current
  through the joint, a second pair senses the voltage the joint
  develops, and because the sense pair carries no measurable current
  its own resistance drops out of the quotient.
- One bond family is outside the requirement. A path whose only role
  is the control of electrostatic charging is sized by the leakage
  current it has to bleed away, not by a milliohm reference target, so
  a low-resistance measurement grades it against a limit it was never
  designed to meet. The exemption is narrow: the moment that same path
  also serves as a shield termination, a structural reference or any
  other role, it is measured like every other bond.
- The injection current has a window at both ends. Too little current
  and the sensed voltage sinks into the instrument noise; too much and
  the measurement heats the joint it is trying to characterize, so the
  resistance it reports belongs to a joint that no longer exists at
  its flight temperature.
- The limit comes from what the bond is for, not from its size. A path
  that carries current -- a power return, a lightning path -- is held
  tighter than a path that only establishes a reference potential. A
  bond serving two roles takes the tighter of the two limits, because
  the looser one does not stop being wrong.
- Evidence is per bond and the exemptions are listed, not dropped. A
  schedule that silently omits its charge-bleed paths and one that
  deliberately exempts them read identically in a summary count, and
  only one of them is reviewable.

## Workflow

1. Validate each bond record: identifier, purpose, any additional
   purposes, measurement method, sense-pair separation, injection
   current, sensed voltage. Reject an unknown purpose, an unknown
   method, a non-positive injection current or a negative voltage.
2. Decide the status of each bond: exempt when charging control is its
   only role, required otherwise, and record which of the two reasons
   applies so the exemption is auditable.
3. Check the arrangement of every required measurement: a missing
   measurement, a two-wire method, a sense pair shared with the
   injection pair, an injection current outside its window, or a
   missing voltage are each their own finding.
4. Compute the resistance of a valid four-wire reading as the sensed
   voltage over the injected current, and read the limit from the
   tightest of the purposes the bond serves.
5. Compare value against limit. Treat a value exceeding the limit only
   by the quotient representation error as compliant -- the named
   picoohm tolerance is far under any bond-tester resolution and the
   engineering limit itself is never widened.
6. Aggregate: list the exempt bonds and the measured bonds separately,
   and call the schedule compliant only when no bond carries a
   finding.

## Pitfalls

- Accepting a two-wire number because it happens to look small. It is
  small relative to the probe set, not relative to the bond, and the
  bond could be an open joint underneath it.
- Reading the charging-control exemption as covering any bond that
  touches a charge-bleed path. The exemption is for a path with no
  other role; a dual-role path keeps the measurement.
- Treating the injection current as a free parameter. A reading taken
  at a few milliamperes is noise, and one taken at a hundred amperes
  characterizes a joint the measurement itself annealed.
- Applying one resistance limit across the schedule. The limit is a
  property of the bond's purpose, and a power-return path graded
  against a reference-only limit passes while failing.
- Reporting the compliant count without the exempt list. An omitted
  bond and an exempt bond produce the same total, and a reviewer
  cannot tell them apart.

## Behavior contract (gate 3)

The exemption-status, setup-check, four-wire-quotient, purpose-limit,
tolerance and schedule-aggregation logic is exercised by the gate 3
contract test: scripts/test_e2007_bonding_resistance_measurement.py
against scripts/e2007_bonding_resistance_measurement_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_bonding_resistance_measurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
