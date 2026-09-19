---
name: q7001-cleaning-process-selection
description: "Determine which cleaning process a piece of flight hardware can actually take, and which of the admissible ones reaches the level it needs. Use when solvent wipe, aqueous immersion, plasma and carbon-dioxide snow are all on the table and the item carries material, geometry and sensitivity constraints that rule some of them out. Screens each candidate for material attack, trapped-liquid geometry, optical and electrostatic sensitivity and residue the item cannot carry, keeps only the survivors, ranks them on removal of the contaminant actually present against the level reachable, and refuses to name a winner when every candidate was excluded. Trigger: ecss, q-st-70-01, cleaning-process-compatibility, solvent-wipe-cleaning, aqueous-immersion-cleaning, plasma-cleaning-selection, co2-snow-cleaning, cleaning-residue-risk."
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
  tags: [ecss, q-st-70-01-cleanliness-contamination-control, q7001-cleaning-process-selection, cleaning-process-compatibility, solvent-wipe-cleaning, aqueous-immersion-cleaning, plasma-cleaning-selection, co2-snow-cleaning, cleaning-residue-risk]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Contamination Control — Cleaning Process Selection (space-systems/ecss/q7001-cleaning-process-selection)

Use when the task is the cleaning-operations step of ECSS-Q-ST-70-01 — picking
the process a specific hardware item will be cleaned by. This leaf decides
which process to run; the post-cleaning verification leaf decides whether the
run worked.

## Domain quick reference

- A cleaning process is a mechanism, and each mechanism removes one kind of
  contaminant well and another badly. Carbon-dioxide snow is a momentum
  transfer and takes particles off; plasma is a chemical attack and takes
  organic films off; an aqueous bath dissolves ionic salts nothing dry will
  touch; a solvent wipe lifts oils. The contaminant present, not habit, picks
  the mechanism.
- Admissibility comes before effectiveness. The most effective process on paper
  is worth nothing if it attacks a material of the item, cannot reach the
  surface, threatens a sensitive one, or leaves a residue the item cannot
  carry. Screen first, then rank what survived.
- Geometry decides more than material does. A blind cavity, a honeycomb core or
  an open-cell foam holds whatever liquid enters it, so a wet process on a
  trapping geometry is not slow drying, it is a permanent reservoir. Only a
  process whose medium leaves under its own vapour pressure reaches into those.
- Sensitivity is per-mechanism, not a single number. An optical surface objects
  to an abrasive wet wipe; an electrostatic-sensitive assembly objects to the
  charge a snow jet deposits; neither objection transfers to the other process.
- A residue is admissible when the flow that follows removes it. A residue-free
  finish blocks every residue-leaving process unless a rinse or dry step is
  actually declared — assuming one is how a water spot reaches an optic.
- When nothing is admissible, that is the answer. There is no default process
  to fall back on: the item is re-designed, re-sequenced or dispositioned.

## Workflow

1. Validate the hardware description: item, materials, the contaminant type
   present, the cleanliness level rank it must reach, and its constraint flags.
2. Screen every candidate process on four independent tests — material attack,
   geometry and facility, mechanism sensitivity, residue — and collect the
   reasons rather than stopping at the first one.
3. Take the admissible set. If it is empty, refuse and say so; do not relax a
   screen to produce a recommendation.
4. Score each survivor: removal effectiveness for the contaminant actually
   present, scaled by whether the process reaches the required level, less the
   penalty for a wet process and for an abrasive one on a soft surface.
5. Rank the scores best first, resolving a score tie on name order through a
   named tolerance so a float sum cannot decide it silently.
6. Return the recommendation, the full ranking, every rejected candidate with
   its reasons, and a finding when the winner cannot reach the level alone or
   when it tied with the runner-up.

## Pitfalls

- Ranking on removal effectiveness alone. A process that removes 95 % of the
  contaminant and attacks the substrate is not the best candidate, it is not a
  candidate; the screens are not weights.
- Putting a honeycomb or foam part in a bath because the material list looked
  metallic. The core traps the liquid whatever the skin is made of, and the
  part outgasses it for the rest of the programme.
- Treating "sensitive" as one flag. Refusing a snow jet on an optic because it
  is sensitive, while letting an abrasive wipe through, is the exact inversion
  of what the two mechanisms do.
- Assuming a rinse step that is not in the flow. A residue-free requirement is
  met by a declared step, not by the expectation that someone will wipe it.
- Defaulting to a solvent wipe when the screens leave nothing. An inadmissible
  process is not made admissible by having no alternative.
- Deciding a tie on whichever score the float sum made larger. Two equal
  candidates are an engineering decision, and the tie is reported as one.

## Behavior contract (gate 3)

The process profiles, hardware validation, the four admissibility screens,
removal and level-capability scoring, the ranking tie-break and the refusal
when no candidate survives are exercised by the gate 3 contract test:
scripts/test_q7001_cleaning_process_selection.py against
scripts/q7001_cleaning_process_selection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7001_cleaning_process_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
