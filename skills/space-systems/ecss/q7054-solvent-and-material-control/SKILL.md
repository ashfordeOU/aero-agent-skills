---
name: q7054-solvent-and-material-control
description: "Verify that a solvent or cleaning agent is fit for ultracleaning under ECSS-Q-ST-70-54C before it touches flight hardware: check the batch certificate actually supports the declared purity grade, convert the residue-on-evaporation into the residue the agent will leave per unit area from the drained volume and the wetted area, grade that against the surface allowance, and refuse a pairing the substrate cannot take. Use when qualifying a solvent batch, a detergent or a rinse fluid for precision-cleaned hardware. Trigger: ecss, q-st-70-54c, cleaning-agent-purity-grade, residue-on-evaporation, deposited-non-volatile-residue, solvent-substrate-compatibility, cleaning-agent-batch-certificate."
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
  tags: [ecss, q-st-70-54c-ultracleaning-of-flight-hardware, q-st-70-54c, q7054-solvent-and-material-control, cleaning-agent-purity-grade, residue-on-evaporation, deposited-non-volatile-residue, solvent-substrate-compatibility, cleaning-agent-batch-certificate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Ultracleaning — Solvent and Material Control (space-systems/ecss/q7054-solvent-and-material-control)

Use when the task is the agent-control part of the methods clause of
ECSS-Q-ST-70-54C: deciding whether a particular solvent, detergent or rinse
fluid may be used on a particular part, given what the batch actually carries
and what the substrate can take.

## Domain quick reference

- The agent is the last thing to touch the surface, so whatever it carries is
  what the hardware wears. A cleaning step is only as clean as the fluid that
  closes it, and the cleanest process in the facility cannot undo a dirty
  final rinse.
- A purity grade is a bound, not a measurement. The grade says what the
  supplier undertakes not to exceed; the batch certificate says what this
  drum actually contains, and a certificate above its own grade bound means
  the grade on the label is not evidenced for this batch.
- Concentration alone decides nothing. Residue-on-evaporation is milligram per
  litre of fluid; what lands on the hardware depends on how many litres are
  drained over how much area. The same certified fluid passes on a wide panel
  and fails in a small blind cavity that traps ten times the volume per unit
  area.
- The arithmetic runs both ways and the inverse is the useful one. From the
  surface allowance, the drained volume and the wetted area comes the highest
  concentration that is tolerable, and from that comes the least stringent
  grade that will do — which is the grade to buy, because reaching past it
  costs money for margin nobody asked for.
- Compatibility is a hard screen with three outcomes. Compatible pairings need
  nothing; restricted pairings carry a control into the procedure — an
  inhibited bath, a bounded contact time, a certified low-sulphur batch; and
  prohibited pairings are not traded against cleaning performance at any
  residue level.
- A prohibited pairing is usually about what happens later. Chlorinated
  residue on stressed titanium, solvent absorbed into a composite matrix, a
  loose alkaline corrosion product on magnesium — none of these show up in the
  cleanliness measurement taken on the day.
- Every result belongs to a batch and a geometry together. A new drum, a
  different drain path or a redesigned cavity re-opens the question, because
  two of the three inputs to the deposition have changed.

## Workflow

1. Take the agent declaration: family, declared purity grade, and the
   residue-on-evaporation figure from the batch certificate. Reject a
   declaration missing the certificate figure rather than assuming the grade
   bound.
2. Compare the certificate figure with the bound its declared grade carries.
   A figure above the bound is a finding against the declaration, not a
   reason to re-grade the batch downward silently.
3. Take the use: substrate, the volume of agent that will drain over the part,
   the wetted area, and the surface residue allowance the part owes.
4. Compute the deposited residue per 0.1 square metre from the certificate
   figure, the drained volume and the wetted area, and grade it against the
   allowance, treating an exact landing on the allowance as met.
5. Compute the inverse as well — the permissible concentration and the least
   stringent grade that meets it — so a failure comes with the three ways out:
   less volume, more area, purer agent.
6. Resolve the compatibility of the agent family with the substrate. A
   prohibited pairing ends the qualification; a restricted pairing attaches
   its control to the result.
7. Close with one verdict — qualified, qualified with a restriction, or
   rejected — carrying the deposited residue, the permissible concentration,
   the compatibility reason and every finding.

## Pitfalls

- Reading the label grade as the batch property. The grade is a supplier
  undertaking; only the certificate figure describes the drum in the shop, and
  the two disagree often enough that checking is the whole point.
- Qualifying a fluid without a volume and an area. A concentration on its own
  cannot be compared with a surface allowance, so a qualification that never
  names the drained volume has compared two different quantities.
- Assuming a purer grade fixes a deposition failure. It does, but so does
  draining less fluid or spreading it wider, and the purer grade is usually
  the most expensive of the three and the slowest to procure.
- Trading a prohibited pairing against performance. The damage a prohibited
  agent does is mechanical or electrochemical and shows up after delivery, so
  a clean cleanliness measurement on the day is not evidence against it.
- Letting a restriction live in a note. A bounded contact time or an inhibited
  bath only protects the hardware if it is written into the procedure the
  operator follows, not into the qualification record nobody reads at the
  bench.
- Carrying a qualification across a batch or a geometry change. A new drum
  changes the certificate figure and a redesigned cavity changes the volume
  per unit area; either one re-opens the arithmetic.

## Behavior contract (gate 3)

The agent and use validation, grade-bound comparison, deposited residue
arithmetic, the inverse permissible concentration and least stringent grade,
the three-outcome compatibility screen and the combined verdict are exercised
by the gate 3 contract test:
scripts/test_q7054_solvent_and_material_control.py against
scripts/q7054_solvent_and_material_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7054_solvent_and_material_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
