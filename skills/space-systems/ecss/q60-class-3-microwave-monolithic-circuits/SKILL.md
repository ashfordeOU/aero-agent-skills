---
name: q60-class-3-microwave-monolithic-circuits
description: "Assess a microwave monolithic integrated circuit for class 3 equipment across the four phases ECSS-Q-ST-60C clause 6.6.5 spans, design, choice, purchase and use: take the gain margin the stage leaves over what the chain asked for, grade the screening pedigree against the weakest class 3 admits and assemble the evidence anything below the top rung obliges, check the lot arrived with a traceability record, then turn the load standing wave ratio into a reflection, take the stress it puts on the output stage, feed the reflected power back into the dissipation and resolve the junction temperature. Use when a class 3 radio frequency chain needs a monolithic stage. Trigger: ecss, q-st-60c-clause-6-6-5, class-3-mmic-phase-chain, class-3-mmic-gain-margin, class-3-mmic-screening-pedigree, class-3-mmic-load-mismatch-stress, class-3-mmic-junction-temperature."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-3-microwave-monolithic-circuits, class-3-mmic-phase-chain, class-3-mmic-gain-margin, class-3-mmic-screening-pedigree, class-3-mmic-load-mismatch-stress, class-3-mmic-junction-temperature]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 3 — Microwave Monolithic Circuits (space-systems/ecss/q60-class-3-microwave-monolithic-circuits)

Use when the task is clause 6.6.5 of ECSS-Q-ST-60C: a class 3 radio-frequency
chain needs a microwave monolithic integrated circuit, and the clause covers
four phases rather than one decision — the design that calls for the part, the
choice of where it is drawn from, the purchase that brings it in, and the
application that then runs it. A part has to survive all four, in that order.

## Domain quick reference

- The phases are a chain, not a checklist. A design with no gain margin is not
  rescued by an excellent purchase, and reporting every phase's problems at
  once buries the one that has to be fixed first. The earliest open phase is
  the answer.
- Gain margin is per function, not per part. A power stage is held to more
  margin than a switch matrix because its gain moves most with temperature,
  drive and ageing, and the chain budget was written at one temperature.
- Class 3 widens the source base as far as a catalogue part and stops there.
  A device whose screening history nobody can state is not the bottom rung of
  the ladder — it is off it, because compensating evidence has to compensate
  for something known.
- Evidence is cumulative down the ladder and additive across the delivery
  form. A catalogue part owes the survey, the equivalence argument, the
  radiation evaluation, the lot acceptance and the upscreening; a bare die
  moves die attach and hermeticity onto the equipment builder on top of
  whatever the pedigree already asked for.
- Traceability is the whole of the purchase phase at class 3. A date code, a
  lot reference and the specification the order was placed against are what
  make a later anomaly investigable; a part with none of them is
  indistinguishable from the one next to it on the reel.
- A mismatched load does two things at once, and only one of them is obvious.
  It puts a voltage stress on the output stage that goes as the square of one
  plus the reflection, and it sends the reflected power back into the die as
  heat that the thermal analysis assumed had left.
- Junction temperature is resolved across two resistances. The die-to-case
  path belongs to the part; the case-to-baseplate path belongs to the
  installation, and it is the one that drifts with a rework, a shim or a
  torque nobody re-checked.

## Workflow

1. Validate the case across all four phases at once: the function, the
   pedigree, the delivery form, both gain figures, the rated and nominal
   output, the supply, the load standing wave ratio, the baseplate
   temperature, both thermal resistances and the traceability record.
2. Design phase: take the gain margin as the plain difference and test it
   against the floor the function carries.
3. Choice phase: grade the pedigree against the weakest one class 3 admits,
   and assemble the compensating evidence the pedigree and the delivery form
   together oblige.
4. Purchase phase: name every traceability field the lot arrived without.
5. Use phase: turn the standing wave ratio into a reflection magnitude, take
   the squared voltage stress against its cap, subtract the reflected power
   from what reaches the load, add it back to the dissipation, resolve the
   junction temperature across the two-stage path and take its margin.
6. Compare every computed value with its limit through a tolerance, because
   both sides are computed and a case sitting on a limit is a real case.
7. Return the first phase that stops the part, the per-phase findings, the
   thermal and mismatch numbers and the compensating evidence the choice
   obliged.

## Pitfalls

- Fixing a late phase while an early one is open. A better lot traceability
  record does not add gain to a stage that never had the margin, and the
  rework order gets written against the wrong phase.
- Reading class 3 as no pedigree requirement. The ladder reaches a catalogue
  part precisely so that the evidence attached to it can be stated; an unknown
  history has nothing for that evidence to attach to.
- Taking the delivered power as the output power. A mismatched load returns
  part of it, and the part that comes back is heat inside the package the
  thermal budget never counted.
- Treating load mismatch as a link budget question. The budget loses the
  reflected power; the die gains it, and the voltage stress on the output
  stage arrives whether or not anybody cared about the throughput.
- Taking the junction temperature from the die thermal resistance alone. The
  interface to the baseplate can add as much again and it is the term that
  moves after the analysis was signed.
- Comparing a computed junction margin or stress factor with its limit by bare
  arithmetic. Every one of them comes out of a division or a square, a case
  landing exactly on a limit is ordinary, and the last place of a float is not
  where that call belongs.

## Behavior contract (gate 3)

The policy merge, four-phase case validation, gain margin and its per-function
floor, pedigree ladder and admissibility, cumulative pedigree and delivery
form evidence, traceability completeness, reflection magnitude, squared
mismatch stress factor, delivered and dissipated power, two-stage junction
temperature and margin, tolerant limit comparison, per-phase findings and the
first blocking phase are exercised by the gate 3 contract test:
scripts/test_q60_class_3_microwave_monolithic_circuits.py against
scripts/q60_class_3_microwave_monolithic_circuits_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_microwave_monolithic_circuits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
