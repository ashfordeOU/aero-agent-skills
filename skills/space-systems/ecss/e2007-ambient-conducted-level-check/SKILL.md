---
name: e2007-ambient-conducted-level-check
description: "Use when verify the ambient conducted-emission background on the power-leads of an EMC setup under ECSS-E-ST-20-07C clause 5.2.2.4: confirm the unit-under-test is disconnected and replaced by a resistive dummy-load drawing a representative bus current at the declared bus voltage, confirm the line-impedance-stabilisation-network and the support-equipment stay in the graded configuration, sweep each power-lead background level against its conducted-emission-limit, categorize every frequency by the headroom it leaves, identify the governing lead and frequency, and reject a baseline whose dummy-load current or receiver bandwidth departs from the declared reference run. Trigger: ecss, e-st-20-07c, ambient-conducted-level, power-lead-noise-floor, dummy-load-substitution, line-impedance-stabilisation-network, conducted-emission-limit-headroom, bus-current-representativeness, emc-facility-baseline."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-ambient-conducted-level-check, ambient-conducted-level, power-lead-noise-floor, dummy-load-substitution, line-impedance-stabilisation-network, conducted-emission-limit-headroom, emc-facility-baseline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC Facility — Ambient Conducted-Level Check (space-systems/ecss/e2007-ambient-conducted-level-check)

Use when the task is the conducted background baseline of
ECSS-E-ST-20-07C clause 5.2.2.4 -- recording and grading the
conducted-emission floor present on the power-leads while the
unit-under-test is removed and a dummy-load stands in its place, so
that a later conducted reading can be attributed to the unit rather
than to the facility supply and the support-equipment.

## Domain quick reference

- The conducted baseline is a substitution measurement, not an
  open-circuit one. Removing the unit and leaving the leads unloaded
  changes the source impedance the
  line-impedance-stabilisation-network sees and suppresses the very
  supply-borne ripple the baseline is meant to capture. A resistive
  dummy-load drawing a representative bus current keeps the supply
  and its regulation loop working in the same region as the graded
  run.
- Representativeness is quantitative: the dummy-load current must sit
  inside a declared fraction of the unit's nominal bus current, and
  the bus voltage must match the graded run. A load drawing a tenth
  of the current gives a supply floor that has nothing to do with the
  configuration being graded.
- The load must be resistive. An inductive or switching load injects
  its own conducted-emission spectrum onto the leads and the recorded
  floor then contains the substitute's noise rather than the
  facility's.
- Every power-lead is graded separately. A primary positive lead and
  its return do not carry the same background, and a secondary bus
  can be quiet while the primary is not; the governing result is the
  worst lead at its worst frequency, not an average.
- Grading is by headroom against the applicable
  conducted-emission-limit at that frequency, with a required
  separation (conventionally 6 dB) between the recorded floor and the
  limit. Headroom at or above the requirement is compliant; positive
  but short of it is a marginal frequency carried as a measurement
  limitation; headroom at or below zero is a background exceedance
  and the frequency cannot be graded until the facility supply is
  cleaned up.
- The receiver bandwidth must match the graded run for the same
  reason it must on the radiated side: a narrower bandwidth lowers
  the apparent floor without lowering the real one.

## Workflow

1. Validate the dummy-load: resistive, positive current draw, bus
   voltage matching the graded run, and current inside the declared
   tolerance fraction of the unit's nominal bus current. Reject the
   baseline rather than grading an unrepresentative substitution.
2. Validate the run configuration: unit disconnected, dummy-load
   installed, line-impedance-stabilisation-network in circuit with a
   recognized impedance, support-equipment powered, receiver
   bandwidth positive and matching the declared reference run.
3. Validate each lead sweep: a recognized lead designation, at least
   one point, strictly increasing positive frequencies, a background
   level and an applicable limit at every point.
4. For each point compute headroom = limit - background and
   categorize it as compliant, marginal or exceedance against the
   required separation. Absorb representation error at the boundary
   with a named decibel tolerance; never lower the required
   separation to make a boundary point pass.
5. Reduce each lead to its worst-case point, then reduce the set of
   leads to the governing lead.
6. Aggregate: per-lead counts, the governing lead and frequency, the
   findings (exceedances) and the limitations (marginal frequencies).
   The baseline is usable only when no lead carries an exceedance.

## Pitfalls

- Measuring the background with the leads open. The supply is then
  unloaded, its ripple collapses, and the baseline understates the
  floor the graded run will meet.
- Substituting any convenient load. A switching or inductive
  substitute contributes its own conducted spectrum, and the recorded
  floor is then a property of the substitute.
- Grading the primary lead only and assuming the return follows. The
  return lead frequently carries the higher background.
- Averaging the leads into a single floor. Clause 5.2.2.4 is governed
  by the worst lead at its worst frequency; an average hides it.
- Recording the baseline at a narrower receiver bandwidth than the
  graded run, or at a different bus voltage, and comparing the two
  anyway.

## Behavior contract (gate 3)

The dummy-load validation, configuration validation, per-lead
headroom categorization, governing-lead reduction and aggregation
logic is exercised by the gate 3 contract test:
scripts/test_e2007_ambient_conducted_level_check.py against
scripts/e2007_ambient_conducted_level_check_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_ambient_conducted_level_check.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
