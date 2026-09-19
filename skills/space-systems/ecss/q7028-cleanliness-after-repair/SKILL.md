---
name: q7028-cleanliness-after-repair
description: "Verify that a repaired printed circuit board assembly was cleaned and then shown to be clean under ECSS-Q-ST-70-28C, against the levels the contamination-control standard ECSS-Q-ST-70-01C holds: match the cleaning agent to the flux that was actually used, size the wetted area and the extract volume, take the system blank off the reading, convert net conductivity into a sodium-chloride-equivalent surface density, grade it as a utilisation of the category limit, and grade the visual state, the drying and the delay before measurement. Use when signing off a repair, auditing a cleanliness record or arguing a marginal extract. Trigger: ecss, q-st-70-28c, post-repair-ionic-cleanliness, repair-flux-residue-removal, ionic-extract-blank-subtraction, nacl-equivalent-surface-density, post-repair-cleanliness-utilisation."
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
  tags: [ecss, q-st-70-28c-pcb-repair-and-modification, q-st-70-28c, q7028-cleanliness-after-repair, post-repair-ionic-cleanliness, repair-flux-residue-removal, ionic-extract-blank-subtraction, nacl-equivalent-surface-density, post-repair-cleanliness-utilisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS PCB Repair — Cleanliness After Repair (space-systems/ecss/q7028-cleanliness-after-repair)

Use when the task is the verification clause of ECSS-Q-ST-70-28C: the cleaning
that follows a repair or modification of a printed circuit board assembly, and
the ionic cleanliness measurement that has to demonstrate the residues the
repair introduced are gone. The levels themselves belong to the contamination
and cleanliness control standard, ECSS-Q-ST-70-01C, which this clause defers
to rather than restating.

## Domain quick reference

- A repair puts contamination onto a board that was already accepted as clean.
  Flux, solder spatter, abraded coating and handling salts all arrive with the
  work, so the cleanliness evidence the board carried before the repair says
  nothing about the board after it.
- The cleaning agent has to match the flux. A water-soluble flux is not
  removed by a solvent that never dissolved it, and a rosin residue survives
  water indefinitely. Getting this pairing wrong produces a board that looks
  cleaned and measures dirty, and the reflex is to re-run the measurement.
- A no-clean residue stops being a no-clean residue once a soldering iron has
  been through it. The encapsulating film the formulation relied on is broken
  and the activator underneath is exposed, so the repair area is cleaned even
  though the original assembly process left it alone.
- The reported figure is a mass per unit area, so both the area and the
  extract volume are part of the measurement. A starved extract that does not
  wet the whole item reports a low number for the wrong reason, and a wetted
  area taken as one face of a double-sided board halves the denominator.
- The system blank is subtracted, not ignored. The solvent, the vessel and the
  cell all contribute conductivity, and an extract reading below the blank is
  an instrument fault rather than an exceptionally clean board.
- The measurement cannot see what did not dissolve. A visible residue, an
  entrapped droplet under a part or a loose solder ball in the repair area is
  a finding in its own right, whatever the extract said.
- Time matters at both ends. Solvent trapped under a part goes on evolving
  residue, and a board measured days after cleaning is evidence about its
  handling since, not about the cleaning.

## Workflow

1. Take the cleanliness category the item is held to and read its limit; treat
   an unknown category as an error, never as the default.
2. Compute the wetted area from the board dimensions, the number of faces
   cleaned and any declared extra area.
3. Check the extract volume against the area, and report an extraction too
   small to wet what it is measuring.
4. Subtract the system blank from the extract conductivity and convert the net
   reading into a sodium-chloride-equivalent surface density.
5. Divide by the category limit to get a utilisation, treating a value sitting
   exactly on the limit as compliant through a named tolerance.
6. Check the cleaning agent against the flux category that was used.
7. Record every residue still visible in the repair area, and grade the drying
   time and the delay between cleaning and verification.
8. Return the density, the utilisation, the margin, the governing criterion and
   every finding; verified only when there are none.

## Pitfalls

- Reusing the pre-repair cleanliness evidence. The repair is the contamination
  event, and the certificate that predates it cannot cover it.
- Cleaning a water-soluble flux with alcohol because alcohol is on the bench.
  The residue is left in place and the ionic figure climbs for a reason nobody
  connects back to the solvent choice.
- Leaving the repair area alone because the flux was a no-clean grade. The
  iron broke the film that made it a no-clean grade in the first place.
- Halving the area by counting one face of a double-sided assembly. The
  density is a quotient, and an understated denominator understates the
  residue by the same factor.
- Dropping the blank subtraction when the blank is small. A small blank over a
  small net reading is a large fraction of the result, and that is exactly the
  regime where a board is near its limit.
- Re-running the extract until a number comes out low. The variation being
  sampled is the extraction, not the board, and the lowest of several runs is
  not the cleanest estimate of anything.
- Treating a clean extract as a clean board. Entrapped solvent and loose
  solder balls do not conduct in a beaker they never reached.

## Behavior contract (gate 3)

The category limits, wetted-area and extract-volume sizing, blank subtraction
and the conductivity conversion, utilisation against the limit, agent-to-flux
pairing, visual observations and the drying and delay windows are exercised by
the gate 3 contract test:
scripts/test_q7028_cleanliness_after_repair.py against
scripts/q7028_cleanliness_after_repair_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7028_cleanliness_after_repair.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
