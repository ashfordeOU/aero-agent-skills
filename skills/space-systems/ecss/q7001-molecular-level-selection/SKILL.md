---
name: q7001-molecular-level-selection
description: "Determine the molecular non-volatile-residue cleanliness level each hardware category must be built and delivered to under ECSS-Q-ST-70-01C. Use when a hardware list carries performance budgets rather than levels, and the residue density a surface may hold has to come out of its own sensitivity. Inverts the degradation budget through that sensitivity, subtracts what the item accumulates after delivery, then takes the least demanding ladder level still inside the remaining allowance, so nothing is driven tighter than its requirement. Refuses an allowance the ladder cannot meet, lets a contractual floor govern, and gives an enclosure the tightest level it encloses. Trigger: ecss, q-st-70-01, molecular-nvr-cleanliness-level, nvr-level-ladder-selection, surface-residue-sensitivity, delivery-residue-allowance, enclosure-inherited-cleanliness-level, contamination-degradation-budget."
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
  tags: [ecss, q-st-70-cleanliness-scope, q7001-molecular-level-selection, molecular-nvr-cleanliness-level, nvr-level-ladder-selection, surface-residue-sensitivity, delivery-residue-allowance, enclosure-inherited-cleanliness-level]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Molecular Level Selection (space-systems/ecss/q7001-molecular-level-selection)

Use when the task is the molecular half of the ECSS-Q-ST-70-01C levels
clause — deciding which non-volatile-residue cleanliness level each
category of hardware has to be built, delivered and maintained to,
given what each surface can tolerate before it stops meeting its
performance requirement.

## Domain quick reference

- A molecular level is an areal residue density, mg of non-volatile
  residue per square metre of surface. Named levels form a ladder, and
  a project works to the ladder it has adopted; the ladder is an input
  to the selection, not something the selection invents.
- The level is a consequence, not a preference. Each surface has a
  sensitivity — the performance change it suffers per mg/m2 of residue
  — and a budget for that change. Dividing the budget by the
  sensitivity gives the residue density the surface may end its life
  carrying; everything else follows from that number.
- A surface with ten times the sensitivity gets a tenth of the
  allowance. That is why a radiator, a baffle and a structure panel
  with the same physical area end up on different levels, and why a
  single project-wide level is either wasteful for most of the hardware
  or insufficient for the one item that drives it.
- Delivery is not end of life. Ground storage, integration, launch and
  on-orbit self-contamination all add residue after the cleanliness
  level is verified, so the delivery allowance is the end-of-life
  allowance minus everything that arrives later. Selecting against the
  end-of-life number hands the whole later accumulation away as an
  overrun.
- The selected level should be the least demanding one that fits.
  Choosing tighter than the requirement is not conservatism, it is
  unbudgeted cost in facilities, handling and verification on every
  item in that category for the life of the programme.
- A contractual or customer-imposed floor can be tighter than what
  performance asks for. It governs when it is, and the reason is
  recorded, because a reviewer seeing only the level cannot tell an
  imposed floor from a sensitivity result.
- An enclosure inherits the tightest level of anything it encloses. A
  bay holding one sensitive instrument is a sensitive bay, whatever the
  rest of its contents are.

## Workflow

1. Validate the project level ladder: named levels, each a positive
   areal residue density, strictly increasing and with no repeated
   name. Two levels sharing a density make the selection ambiguous.
2. For each hardware category, validate its performance degradation
   budget and its sensitivity per unit residue density, then invert one
   through the other to obtain the end-of-life residue allowance.
3. Subtract the residue the category will accumulate after delivery. If
   the later accumulation equals or exceeds the end-of-life allowance
   there is no delivery allowance at all, and that is an input error to
   raise, not a zero to select against.
4. Walk the ladder upward and keep the last level at or under the
   delivery allowance, absorbing an exact landing with a named
   tolerance. If even the tightest level is looser than the allowance,
   refuse: the ladder cannot serve that category and either the ladder
   or the design has to change.
5. Apply any imposed floor. Where the floor is tighter than the
   performance choice, the floor becomes the selected level and the
   substitution is recorded as a finding.
6. Give every enclosure the tightest level among the categories it
   encloses, and identify the single category driving the programme.
7. Report per-category allowance, selected level, unused margin
   fraction, and the rolled-up findings.

## Pitfalls

- Selecting against the end-of-life allowance and treating delivery as
  the same point. Ground and on-orbit accumulation are then spent
  twice, and the first surface to miss its budget is the one that was
  nominally compliant at delivery.
- Applying one project-wide level to every category. It is chosen
  either from the most sensitive item, which prices the whole programme
  at optics cleanliness, or from the average, which leaves the
  sensitive item unprotected.
- Rounding the allowance to the next tighter level "for margin". The
  margin fraction is already reported; tightening the level converts a
  visible number into an invisible and permanent cost.
- Extrapolating the ladder when no level fits. Inventing a level below
  the tightest tabulated one asserts a cleanliness the facilities and
  the verification method may not be able to deliver or measure.
- Letting an enclosure sit at its own level while holding a tighter
  item. Molecular residue redistributes inside a closed volume, so the
  enclosure is held to what it encloses.
- Treating an imposed floor as the selection result. Recording it
  without the performance-derived level loses the information that the
  hardware would have been compliant at a looser level, which is what a
  later waiver case rests on.

## Behavior contract (gate 3)

The ladder validation, budget inversion, delivery-allowance
subtraction, least-demanding level selection, imposed-floor override,
enclosure inheritance and driving-category identification are exercised
by the gate 3 contract test:
scripts/test_q7001_molecular_level_selection.py against
scripts/q7001_molecular_level_selection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_molecular_level_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
