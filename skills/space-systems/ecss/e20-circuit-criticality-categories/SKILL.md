---
name: e20-circuit-criticality-categories
description: "Use when assess and group the equipment and subsystem circuits of a spacecraft by functional criticality under ECSS-E-ST-20C clause 6.3.1.1: derive each circuit's category from its hazard, mission-loss and degradation attributes, order the inventory with the safety-critical group first, raise a circuit that couples into a higher-criticality victim to that victim's level for interference control, read the interference margin the category demands from the project ladder, and compare the demonstrated susceptibility-to-emission separation against it. Trigger: ecss, e-st-20-electrical-scope, circuit-criticality-categories, safety-critical-circuit, mission-critical-circuit, criticality-grouping-order, interference-margin-ladder, coupled-victim-escalation."
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
  tags: [ecss, e-st-20-electrical-scope, e20-circuit-criticality-categories, circuit-criticality-categories, safety-critical-circuit, mission-critical-circuit, interference-margin-ladder, coupled-victim-escalation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Circuit Criticality Categories (space-systems/ecss/e20-circuit-criticality-categories)

Use when the task is the clause 6.3.1.1 criticality grouping of
ECSS-E-ST-20C -- sorting the circuits of equipment and of subsystems
into functional criticality groups, with the safety group identified
first, so that electromagnetic interference control effort lands where
loss of a circuit costs the most.

## Domain quick reference

- The ladder has four rungs in a fixed order: safety critical, mission
  critical, essential, non essential. The order is not cosmetic. It is
  the order the grouping is presented in and the order the questions
  are asked in, and the clause is explicit that the safety group comes
  first.
- A circuit's rung follows from its functional attributes, not from
  the subsystem it happens to live in. The hazard question is answered
  before any other: a circuit whose loss or malfunction can produce a
  catastrophic hazard is safety critical however redundant, however
  low powered and however peripheral it looks. Below that, a circuit
  whose loss ends the mission is mission critical when nothing backs
  it up and drops to essential when a redundant path carries the
  function. A circuit that only degrades recoverable performance is
  essential. What is left is non essential.
- Redundancy demotes a mission-loss circuit; it never demotes a hazard
  circuit. Two redundant paths into the same catastrophic outcome are
  two safety critical circuits, because the hazard is a property of
  the consequence, not of the availability.
- Criticality travels along the coupling. An aggressor that can inject
  into a more critical victim, through a shared harness bundle, a
  shared connector or a shared return, has to be controlled at the
  victim's level, because the consequence of the coupling belongs to
  the victim. That raised value is the effective category, and it is
  what the margin demand is read against. The circuit's own category
  is kept alongside it, so the record shows both what the circuit is
  and what it is controlled as.
- Each rung carries an interference margin demand in decibels, widest
  at the safety rung and falling monotonically down the ladder. The
  numbers are project-tailorable; the ordering is not. The non
  essential rung demands nothing, which is why a non essential circuit
  with no demonstrated evidence is not a finding, while a raised one
  is.
- The demonstrated separation is the victim's susceptibility threshold
  less the worst-case emission seen at that victim, in decibels. A
  negative result is a real answer and means the emission sits above
  the threshold; it is a finding, not an input error.

## Workflow

1. Normalize each circuit record: reject an empty identifier, a record
   with no functional attributes, a malformed coupled-victim list, a
   repeated identifier, and any attribute that is absent or not a
   boolean.
2. Derive each circuit's own category by walking the ladder from the
   top: hazard first, then unbacked mission loss, then backed mission
   loss and recoverable degradation, then the remainder.
3. Resolve the coupling: for each circuit, look up the category of
   every victim it names. A victim that is not in the inventory is a
   finding, not a silent skip.
4. Take the effective category as the most critical of the circuit's
   own category and the categories of every resolved victim.
5. Read the required margin for the effective category from the
   project ladder. Skip the evidence and margin checks only where that
   demand is zero.
6. Compute the demonstrated separation from the susceptibility
   threshold and the emission level, and compare it against the
   demand. Report a circuit with a demand and no demonstrated pair as
   an evidence finding, and a circuit below the demand as a margin
   finding naming its effective category.
7. Group and present: every rung is listed, safety first, and the
   inventory is compliant only when the coupling, evidence and margin
   lists are all empty.

## Pitfalls

- Grouping by subsystem or by supplier instead of by function. A
  low-power housekeeping line inside a benign box can still be the
  circuit that arms an ordnance path, and the grouping follows the
  consequence.
- Letting redundancy demote a hazard circuit. Redundancy bears on
  availability, so it can move a mission-loss circuit down a rung; it
  does nothing to the consequence a catastrophic hazard carries.
- Reading a circuit's own category as the level it is controlled at,
  and so applying a small margin demand to an aggressor that shares a
  bundle with a safety critical line. Raise to the victim, then read
  the demand.
- Dropping a named victim that is not in the inventory. That is
  exactly the case where the aggressor's control level is unknown, so
  it is a finding; skipping it silently manufactures a compliant
  result out of an incomplete list.
- Comparing the demonstrated separation against the demand with a bare
  greater-or-equal test. The separation is a difference of two measured
  decibel levels and a case that is exactly on the limit in engineering
  terms can land a few units in the last place below it: subtracting
  27.3 from 33.3 yields 5.9999999999999964, not 6. Absorb that
  representation error in the comparison; never lower the required
  margin to make the case pass.
- Treating a negative separation as bad input. It is a real and
  serious result: the interference already exceeds what the victim
  tolerates.
- Omitting an empty rung from the presented grouping. A reader cannot
  tell an empty safety group from a safety group nobody looked for.

## Behavior contract (gate 3)

The ladder ranking, attribute-driven categorization, coupled-victim
escalation, margin-demand lookup, separation computation, tolerance-
absorbing margin comparison, grouping order and aggregate-review logic
is exercised by the gate 3 contract test:
scripts/test_e20_circuit_criticality_categories.py against
scripts/e20_circuit_criticality_categories_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_circuit_criticality_categories.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
