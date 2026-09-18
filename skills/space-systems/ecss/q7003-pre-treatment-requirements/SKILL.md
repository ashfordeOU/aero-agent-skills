---
name: q7003-pre-treatment-requirements
description: "Evaluate a declared pre-treatment line for black anodizing with inorganic dyes against the ECSS-Q-ST-70-03C process clause. Use when the cleaning, etching, deoxidizing and masking sequence ahead of the anodizing tank has to be shown sound before parts are run: confirm the chemical steps hold the order their chemistry forces, find every aqueous pair that meets without a rinse between them, turn the etch rate and immersion time into the metal actually removed, compare it with the minimum that clears the worked layer and the allowance the drawing left, bound the hold between the last rinse and the tank, and grade rinse water and maskant. Trigger: ecss, q-st-70-03-black-anodizing-scope, anodizing-pre-treatment-sequence, alkaline-etch-metal-removal, deoxidize-to-tank-transfer-time, anodizing-maskant-compatibility, cascade-rinse-quality."
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
  tags: [ecss, q-st-70-03-black-anodizing-scope, q7003-pre-treatment-requirements, anodizing-pre-treatment-sequence, alkaline-etch-metal-removal, deoxidize-to-tank-transfer-time, anodizing-maskant-compatibility, cascade-rinse-quality, anodizing-line-rinse-carry-over]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Black Anodizing — Pre-treatment Requirements (space-systems/ecss/q7003-pre-treatment-requirements)

Use when the task is the pre-treatment half of the ECSS-Q-ST-70-03C
process clause -- showing that the cleaning, etching, deoxidizing and
masking a part passes through before the anodizing tank is ordered
correctly, rinsed properly, and bounded in the two places where time
itself is a process parameter.

## Domain quick reference

- Pre-treatment is a sequence, and the order is forced by chemistry
  rather than by convenience. Oils leave first, because an alkaline
  cleaner that meets them saponifies into a film nothing removes
  later. The cleaner runs before the etch, the etch before the
  deoxidizer, and the deoxidizer is the last chemical step the part
  sees before the tank.
- Between two aqueous baths there is always a rinse. Alkaline liquor
  dragged into an acid bath neutralizes both and drops smut back onto
  the surface, and the part that comes out looks clean while carrying
  exactly the film the sequence was meant to remove. A solvent
  degrease is the exception: it drains and evaporates rather than
  dragging liquor forward.
- Rinse water is a process chemical. Either the rinse cascades through
  enough stages that the last one is nearly clean, or a single stage
  is held at a resistivity that says the same thing. One stale stage
  satisfies neither and is the commonest silent defect on a line.
- The etch is a depth, not a dip. Metal loss is the etch rate times
  the immersion time, and it has to clear the minimum that removes the
  worked and rolled-in surface layer while staying inside the
  dimensional allowance the drawing left. Both bounds bite, and a line
  tuned only to appearance usually fails the lower one.
- A deoxidized surface is a reactive surface. It re-oxidizes in air,
  so the time from the last rinse to the tank is bounded; past the
  bound the remedy is another pass through the deoxidizer, not a
  faster walk to the tank.
- Masking goes on after the last chemical attack. A maskant applied
  earlier meets baths that lift it, and the area it was protecting
  ends up coated. Where the line does apply a maskant before a bath,
  the maskant has to be one that survives that specific chemistry.

## Workflow

1. Read the declared line as an ordered step list and reject any step
   the process does not recognize, rather than silently ignoring it.
2. Grade the order of the chemical steps against the forced sequence,
   and confirm the deoxidizer is the last of them.
3. Walk the line for aqueous pairs that meet without a rinse between
   them, and for a missing rinse after the final bath.
4. Grade the rinse arrangement: cascade stages, or resistivity, or a
   finding.
5. Turn the etch rate and immersion time into a metal loss and place
   it between the minimum removal and the drawing allowance, treating
   a value that lands exactly on either bound as acceptable.
6. Bound the transfer time from the last rinse to the anodizing tank.
7. Place the masking step relative to the last chemical attack, and
   where it precedes a bath, confirm the maskant survives that bath.
8. Report the metal loss, the collected findings and one verdict per
   line, and name the failing lines for a batch.

## Pitfalls

- Grading the line by what is in it rather than by the order it is in.
  Every correct step, in the wrong sequence, produces a part that
  looks pre-treated and anodizes badly, and a checklist that only asks
  whether a deoxidizer exists cannot see it.
- Counting rinse tanks instead of rinse quality. A three-stage cascade
  whose stages have all drifted to the same concentration is one
  rinse, not three, and the resistivity is the only measurement that
  tells the two apart.
- Setting the etch by time alone. Rate drifts with bath age,
  temperature and dissolved aluminium, so a fixed immersion time
  silently walks the metal loss up or down until it leaves one of its
  two bounds.
- Treating the transfer as handling rather than as process. The clock
  from the last rinse to the tank is a parameter with a limit, and a
  part parked on a rack while another load finishes has quietly
  changed its own surface.
- Applying the maskant early because it is easier while the part is
  dry. The maskant then has to survive every bath behind it, and the
  one that does not lifts at the edges and leaves a coated shadow
  exactly where the drawing asked for bare metal.

## Behavior contract (gate 3)

The step vocabulary, forced ordering, aqueous rinse rule, rinse-water
grading, etch arithmetic, transfer bound, maskant compatibility and
line verdict are exercised by the gate 3 contract test:
scripts/test_q7003_pre_treatment_requirements.py against
scripts/q7003_pre_treatment_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7003_pre_treatment_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
