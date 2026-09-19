---
name: q7054-applicability-and-objectives
description: "Determine whether a flight hardware item owes ultracleaning rather than the standard cleaning route under ECSS-Q-ST-70-54C, and what the ultraclean state has to achieve: read the driving function and the exposure of the item, turn the particulate and residue allowances into a required surface cleanliness level and a lettered residue class, compare each against the standard baseline, and return the objective as particulate-driven, molecular-driven or both with the verification that objective implies. Use when a contamination budget, a drawing note or a customer requirement asks whether ordinary cleaning is enough. Trigger: ecss, q-st-70-54c, ultracleaning-applicability, ultraclean-surface-cleanliness-level, particulate-allowance-inversion, non-volatile-residue-class, standard-cleanliness-baseline, ultracleaning-objective."
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
  tags: [ecss, q-st-70-54c-ultracleaning-of-flight-hardware, q-st-70-54c, q7054-applicability-and-objectives, ultracleaning-applicability, ultraclean-surface-cleanliness-level, non-volatile-residue-class, standard-cleanliness-baseline, ultracleaning-objective]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Ultracleaning — Applicability and Objectives (space-systems/ecss/q7054-applicability-and-objectives)

Use when the task is the framework clause of ECSS-Q-ST-70-54C: deciding which
hardware has to reach an ultraclean state at all, and what that state is
supposed to buy, before any method or plan is chosen.

## Domain quick reference

- Ultracleaning is a separate discipline, not cleaning harder. It applies once
  an item has to hold a cleanliness state beyond what the routine cleaning
  route delivers, and everything downstream — method, facility, packaging,
  verification — follows from that single applicability call.
- Two independent ladders describe the state. The particulate ladder quotes a
  surface cleanliness level as the size in micrometre of the largest permitted
  particle; the molecular ladder quotes a non-volatile residue allowance in
  milligram per 0.1 square metre as a lettered class. An item can be far down
  one ladder and ordinary on the other.
- A level is a whole distribution, not one particle. The permitted count at
  every smaller size follows from the level through the log-square law the
  ladder is built on, so an allowance stated as a count at a reference size
  inverts to a level and a level predicts a count at any other size.
- Applicability is a property of the usage. The same bracket owes ultracleaning
  in view of a cryogenic detector and does not owe it buried in a harness run,
  because the function it serves and the surfaces in view of it decide what a
  released particle or a milligram of residue costs.
- An enclosure that cannot deliver released contaminant to the sensitive
  surface relaxes what the item itself must meet. The relaxation is a property
  of the enclosure staying closed, so it collapses the moment the unit is
  opened for access with the sensitive surface exposed.
- The driving ladder fixes the verification. A particulate-driven item is
  verified by particle count or obscuration; a molecular-driven item by a
  solvent rinse and a residue weighing. Verifying the ladder that was not the
  driver returns a clean report about the wrong quantity.
- An item that clears both baselines is finished here. Ultracleaning is
  expensive in facility time and handling risk, so applying it where the
  standard route already meets the allowance buys nothing and adds exposure.

## Workflow

1. Read the usage: the function the item serves, the environment it is exposed
   to, and the contamination-sensitive surfaces in view of it. Reject an
   uncategorized function rather than defaulting it.
2. Take the stated particulate and residue allowances. Where the project has
   not stated them, take the function defaults and record that the numbers owe
   confirmation against the contamination budget rather than presenting them as
   requirements.
3. Apply the enclosure relaxation where the exposure genuinely prevents
   transport to the sensitive surface, and record the relaxation so it can be
   revisited when an access operation is added.
4. Invert the particulate allowance at its reference size into a required
   surface cleanliness level, and round to the tabulated rung at or below it.
   Refuse an allowance of less than one particle per 0.1 square metre: restate
   it at a larger reference size instead.
5. Resolve the residue allowance to the tightest lettered class that meets it,
   and refuse an allowance below the tightest tabulated class.
6. Compare each result with its baseline. Either one beyond the baseline puts
   the item in the ultracleaning population; both beyond it make the objective
   dual.
7. Close with the objective, the two resolved levels, the verification methods
   the objective implies, and the findings — default allowances still to be
   confirmed, a relaxation in force, or a driver the obvious verification would
   miss.

## Pitfalls

- Deciding applicability from the part rather than from its usage. The material
  and the shape say nothing about whether a released particle reaches anything;
  the function and the surfaces in view do.
- Reading a cleanliness level as a single permitted particle. The level is the
  head of a distribution, so an item quoted at a level also carries a permitted
  count at every smaller size, and a count at one size is meaningless without
  the size it was counted at.
- Verifying the ladder that did not drive the requirement. A molecular-driven
  item that passes a particle count has been graded on the quantity that was
  never the problem, and the residue nobody weighed is still on the surface.
- Carrying an enclosure relaxation through an access operation. The relaxation
  is earned by the enclosure remaining closed; an inspection that opens it with
  the sensitive surface in view removes the basis and restores the tighter
  allowance.
- Presenting a function default as a requirement. A default is a starting value
  chosen because nobody stated one, and shipping it as the allowance hides the
  fact that the contamination budget has not yet been apportioned.
- Moving a baseline to make a value that lands exactly on it read as ultraclean.
  The equality is a representation question absorbed by the tolerance inside the
  comparison; the baselines stay as specified.

## Behavior contract (gate 3)

The allowance resolution, enclosure relaxation, particulate allowance
inversion, ladder rounding, residue class resolution, objective selection and
verification mapping are exercised by the gate 3 contract test:
scripts/test_q7054_applicability_and_objectives.py against
scripts/q7054_applicability_and_objectives_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7054_applicability_and_objectives.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
