---
name: e3301-fluid-lubrication-lubricant-quantity
description: "Compute the fluid lubricant charge a mechanism is filled with under ECSS-E-ST-33-01C clauses 4.7.3.3.1 and 4.7.3.3.2. Use when the task is a high-speed or high-cycle bearing, gear or slip ring lubricated with oil or grease: confirming the duty is in the fluid domain and the fluid covers its temperature range, scaling the reference vacuum mass-loss rate of ECSS-Q-ST-70-02 to the operating temperature, accumulating evaporation, creep, retainer absorption and duty consumption over life, applying the quantity factor, and grading the charge against reservoir capacity and the maximum fill fraction. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-fluid-lubrication, lubricant-quantity-determination, lubricant-evaporation-loss, lubricant-creep-loss, retainer-absorption-loss, bearing-fill-fraction."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-fluid-lubrication-lubricant-quantity, mechanism-fluid-lubrication, lubricant-quantity-determination, lubricant-evaporation-loss, lubricant-creep-loss, retainer-absorption-loss, bearing-fill-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Fluid Lubrication and Lubricant Quantity (space-systems/ecss/e3301-fluid-lubrication-lubricant-quantity)

Use when the task is the clause 4.7.3.3.1 and 4.7.3.3.2 pair of
ECSS-E-ST-33-01C — choosing a fluid lubricant for a duty that is fast
or long in cycles, and working out how much of it the mechanism has to
be filled with so that a film is still there at end of life.

## Domain quick reference

- A fluid is the answer to speed and cycles. A duty that is slow and
  short is better served by a solid film, and a fluid put there
  instead spends its life creeping away from a contact that barely
  moves.
- The quantity question is not the film thickness question. The film
  is what has to be present at the end; the charge is that film plus
  everything the mission takes away, times a design factor.
- Four things take it away. Evaporation from the exposed free surface
  in vacuum, creep along the wetted perimeter, absorption into a
  porous retainer or cage, and consumption through the actuation
  itself. Which one dominates changes with the design, and a charge
  sized on the famous term alone is sized on the wrong one.
- Evaporation is exponential in temperature. A reference vacuum
  mass-loss rate measured at a screening temperature under the
  outgassing standard has to be scaled to the operating temperature
  with an Arrhenius factor; twenty kelvin can multiply it several
  times over.
- Creep is the term a barrier changes. Barrier effectiveness enters as
  a fraction of the creep loss removed, which is why a barrier design
  and a quantity calculation belong in the same review.
- Over-filling is also a defect. Past a fraction of the free volume
  the mechanism churns lubricant instead of running in it: drag goes
  up, heat goes up, and the excess is thrown into places the
  contamination budget accounts for.

## Workflow

1. Grade the duty: sliding speed at or above the fluid floor, or a
   cycle count at or above it, and a fluid whose rated range covers
   the duty temperature range at both ends.
2. Scale the reference vacuum mass-loss rate from its screening
   temperature to the operating temperature with the Arrhenius factor
   for the declared activation energy.
3. Accumulate the four loss terms over the life: evaporation over the
   exposed area, creep along the wetted perimeter reduced by barrier
   effectiveness, absorption as a fraction of retainer mass, and
   consumption per million cycles.
4. Add the operating film requirement and apply the quantity design
   factor to obtain the charge.
5. Compare the charge with the reservoir capacity, and the volume it
   occupies with the maximum fill fraction of the free volume; both
   directions are graded.
6. Name the dominant loss term in the report, because that is where a
   design change buys the most.

## Pitfalls

- Sizing the charge on the operating film alone. The film is the end
  state; the losses over fifteen years are usually several times it.
- Using a reference mass-loss rate at the operating temperature
  without scaling. The screening figure is measured hot or cold of the
  duty and the dependence is exponential, not linear.
- Crediting a barrier without a stated effectiveness. A barrier that
  is assumed perfect removes the creep term entirely and hides the
  loss that most often empties a bearing.
- Filling the free volume because the reservoir allows it. Beyond the
  fill fraction the mechanism churns; capacity is an upper bound, not
  a target.
- Reporting only the total loss. Which term dominates decides whether
  the fix is a labyrinth, a barrier, a different retainer or a larger
  reservoir.

## Behavior contract (gate 3)

The duty indication, Arrhenius scaling, the four loss terms, the loss
budget, the charge with its quantity factor, the fill fraction and the
reservoir and over-fill grading are exercised by the gate 3 contract
test: scripts/test_e3301_fluid_lubrication_lubricant_quantity.py
against scripts/e3301_fluid_lubrication_lubricant_quantity_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_fluid_lubrication_lubricant_quantity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
