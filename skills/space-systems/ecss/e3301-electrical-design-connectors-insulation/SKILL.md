---
name: e3301-electrical-design-connectors-insulation
description: "Design the electrical circuits of a spacecraft mechanism and verify them against ECSS-E-ST-33-01C clauses 4.7.7.1 to 4.7.7.3 and 4.7.7.5. Use when the task is choosing connectors that cannot be cross-mated, keeping power, signal and pyrotechnic families out of one shell, derating contact current for shell occupancy, reserving spare contacts, grading measured insulation resistance at the voltage the requirement is written at, and confirming the dielectric withstand voltage and leakage current a circuit's operating voltage calls for. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-connector-cross-mating, contact-current-occupancy-derating, mechanism-insulation-resistance, dielectric-withstand-voltage, circuit-family-connector-separation, mechanism-harness-leakage-current."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-electrical-design-connectors-insulation, mechanism-connector-cross-mating, contact-current-occupancy-derating, mechanism-insulation-resistance, dielectric-withstand-voltage, circuit-family-connector-separation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Electrical Design: Connectors, Insulation, Dielectric Strength (space-systems/ecss/e3301-electrical-design-connectors-insulation)

Use when the task is the mechanism electrical-design step of
ECSS-E-ST-33-01C clauses 4.7.7.1 to 4.7.7.3 and 4.7.7.5 -- picking the
connectors a mechanism presents to the platform harness, and showing
that the insulation between its conductors and its structure holds at
the stress the mission applies.

## Domain quick reference

- Connector selection is a mis-mating problem before it is an electrical
  one. Two connectors on one unit that share shell size, insert
  arrangement and keying can be swapped during integration, and the
  first evidence is usually a damaged motor. The defence is a difference
  in the mating hardware itself, not a label or a procedure step.
- Circuit families are kept in separate shells. A pyrotechnic firing
  line beside a resolver return puts a firing-level transient onto a
  low-level circuit; a power return beside a signal puts motor
  commutation noise onto it. Screen returns are the exception: they
  belong with the circuits whose screens they terminate.
- A contact's current rating is a single-contact, free-air figure. A
  populated shell cannot shed the heat of every contact at rating, so
  the usable fraction falls with occupancy. Grading a fully loaded
  connector against the catalogue rating overstates its capability by
  roughly a factor of two.
- Spare contacts are design margin, not waste. A contact that fails
  continuity at integration and a late-added telemetry line both need
  somewhere to go, and adding a connector afterwards is a structural and
  thermal change, not a wiring one.
- Insulation resistance is a function of the voltage it is measured at.
  A reading taken at a lower stress than the requirement is written at
  is optimistic, because the leakage paths that matter do not conduct
  until the stress reaches them. The measurement voltage is therefore
  part of the evidence, not an instrument setting.
- Dielectric withstand is a proof test at a voltage derived from the
  circuit's operating voltage -- conventionally twice it plus a fixed
  offset -- and it is graded on two numbers: that the right voltage was
  applied, and that the leakage current under it stayed inside its
  limit.

## Workflow

1. Validate each connector record: identifier, shell, insert
   arrangement, keying, total contacts, and the circuits it carries with
   their class, current, contact rating, operating voltage and contact
   occupancy. An allocation exceeding the shell is an input error.
2. Compare every connector pair for shared shell, insert and keying, and
   raise a cross-mating finding for each match.
3. For each connector, raise a separation finding for every forbidden
   pair of circuit families present in the same shell.
4. Compute the occupancy derating factor, apply it to each contact
   rating, and grade the fractional margin over the circuit current
   against the required margin. Grade the spare-contact count
   separately.
5. Grade each insulation measurement against the required minimum, and
   raise a second finding when the measurement voltage is below the
   voltage the requirement is written at.
6. Derive the required withstand voltage from each circuit's operating
   voltage, grade the applied voltage against it and the measured
   leakage against its limit.
7. Report per-connector and per-measurement records plus the aggregated
   finding list; the design is compliant only when the list is empty.

## Pitfalls

- Relying on a connector-savers procedure or a coloured label to prevent
  cross-mating. Integration happens under schedule pressure with the
  harness partly installed; the keying difference is the only control
  that survives that.
- Grading contact current against the catalogue rating. The rating is a
  single-contact figure and a full shell runs far below it, so a design
  that passes on the catalogue number can still run hot in flight.
- Reading an insulation resistance at a convenient bench voltage and
  comparing it with a requirement written at a higher one. The number
  will pass and the insulation may not.
- Reporting a dielectric test as passed on the leakage current alone.
  If the applied voltage was below what the circuit calls for, the test
  proved nothing about the stress the mission applies.
- Filling every contact in the shell because the circuits happen to fit.
  The next change then costs a connector, a bracket and a thermal
  re-analysis.
- Widening a required margin to make an exact-equality case pass. An
  equality at the limit is a representation question, absorbed by the
  named tolerance inside the comparison; the required value stays as
  specified.

## Behavior contract (gate 3)

The connector validation, cross-mating detection, circuit-family
separation, occupancy derating and contact-current margin, insulation
resistance grading and dielectric withstand grading are exercised by the
gate 3 contract test:
scripts/test_e3301_electrical_design_connectors_insulation.py against
scripts/e3301_electrical_design_connectors_insulation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3301_electrical_design_connectors_insulation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
