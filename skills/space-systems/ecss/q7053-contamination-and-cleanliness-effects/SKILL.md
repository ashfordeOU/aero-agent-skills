---
name: q7053-contamination-and-cleanliness-effects
description: "Evaluate what a sterilization process did to the cleanliness of the hardware it was run on, in the evaluation clauses of ECSS-Q-ST-70-53C. Use when particle counts and non-volatile-residue figures exist for the same surface before and after exposure and the cleanliness budget has to be defended. Converts a particle size distribution into an obscuration percentage over the sampled area, places that figure in the tightest cleanliness band it satisfies, compares the band against the required one, separates the residue the process itself added from the residue already present, and grades that added share against its own allocation. Trigger: ecss, q-st-70-53-sterilization-compatibility-scope, sterilization-cleanliness-effect, particle-obscuration-percentage, product-cleanliness-band, non-volatile-residue-increase, process-attributable-contamination."
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
  tags: [ecss, q-st-70-53-sterilization-compatibility-scope, q7053-contamination-and-cleanliness-effects, sterilization-cleanliness-effect, particle-obscuration-percentage, product-cleanliness-band, non-volatile-residue-increase, process-attributable-contamination]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Sterilization Compatibility — Contamination and Cleanliness Effects (space-systems/ecss/q7053-contamination-and-cleanliness-effects)

Use when the task is the cleanliness half of an ECSS-Q-ST-70-53C
compatibility evaluation — deciding whether the sterilization process
left the hardware within its particulate and molecular cleanliness
requirement, and how much of what is on the surface the process itself
put there.

## Domain quick reference

- Particulate cleanliness is graded on obscuration, an area fraction,
  not on a raw count. One 500 um particle obscures as much surface as
  two thousand five hundred 10 um particles, so a count that ignores
  size cannot be compared with a cleanliness requirement.
- Obscuration is the projected area of the counted particles divided by
  the area actually inspected. Reporting a count without the sampled
  area makes the figure unusable, because the same count over a
  ten-times larger witness plate is a ten-times cleaner surface.
- A cleanliness level is a band, defined by the obscuration ceiling it
  allows. A surface sits in the tightest band whose ceiling it still
  meets; a surface dirtier than the coarsest tabulated band has no
  level, which is a finding rather than a level of its own.
- Molecular cleanliness is a non-volatile-residue surface density. The
  compatibility question is the increase across the exposure, because
  residue already present before the process is the responsibility of
  the preceding cleaning step, not of the sterilization.
- The process-attributable increase is graded against its own
  allocation in the contamination budget, and the total after exposure
  is graded against the surface requirement. Both can fail
  independently: a small increase on an already-loaded surface breaches
  the total while respecting its allocation.

## Workflow

1. Validate the size distribution: every bin a positive finite diameter
   in micrometres with a non-negative integer count, and a positive
   inspected area.
2. Sum the projected area of the bins and divide by the inspected area
   to get the obscuration percentage, before and after exposure.
3. Place each obscuration figure in the tightest band of the declared
   band table whose ceiling it meets, absorbing representation error at
   the ceiling with a named tolerance. Return no band when the figure is
   dirtier than the coarsest ceiling.
4. Compare the post-exposure band with the required level by their
   ceilings; a band whose ceiling is looser than the required ceiling
   does not meet the requirement.
5. Subtract the pre-exposure non-volatile-residue surface density from
   the post-exposure one to get the process-attributable increase; a
   negative difference is reported as zero added residue, not as a
   credit against the allocation.
6. Grade the increase against its allocation and the post-exposure total
   against the surface requirement, separately.
7. Report findings: level not met, no band at all, allocation exceeded,
   total residue over requirement, and a post-exposure obscuration
   coarser than the pre-exposure one by more than the process allowance.

## Pitfalls

- Grading particulate cleanliness on counts. Counts are the raw
  measurement; the requirement is an area fraction, and the conversion
  needs the size of every bin and the area inspected.
- Dropping the inspected area from the record. Without it the
  obscuration cannot be formed at all, and a count quoted alone is
  silently assumed to be over whatever area the reader has in mind.
- Crediting a residue decrease against the allocation. A surface that
  came out cleaner than it went in did not earn budget for another
  process step; the added share floors at zero.
- Checking only the total, or only the increase. They answer different
  questions and an item can pass one while failing the other.
- Inventing a level for a surface dirtier than the coarsest band. The
  correct output is that the surface has no level, which forces a
  re-clean or a budget change rather than a rounded-up label.

## Behavior contract (gate 3)

The distribution validation, obscuration conversion, band placement,
requirement comparison, residue-increase floor and allocation grading
are exercised by the gate 3 contract test:
scripts/test_q7053_contamination_and_cleanliness_effects.py against
scripts/q7053_contamination_and_cleanliness_effects_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7053_contamination_and_cleanliness_effects.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
