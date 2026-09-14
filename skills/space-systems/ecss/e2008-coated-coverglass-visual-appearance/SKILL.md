---
name: e2008-coated-coverglass-visual-appearance
description: "Use when coated coverglasses have been examined and each needs a disposition. Assess the coated face of a solar-cell coverglass for an even coating and for pinholes, voids and spatter, under ECSS-E-ST-20-08C clause 8.7.1.3.1: reduce the sampled appearance readings to a non-uniformity spread, size and place every point defect, hold back what falls in the declared edge exclusion band, take the defect density and the obscured area over the active aperture rather than the whole face, and roll the lot up with unread faces left open. Trigger: ecss, e-st-20-08c, clause-8-7-1-3-1, coverglass-coating-visual-appearance, coating-pinhole-and-void-screen, coating-spatter-defect-count, coated-area-evenness-spread, coverglass-obscured-aperture-fraction."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coated-coverglass-visual-appearance, coverglass-coating-visual-appearance, coating-pinhole-and-void-screen, coating-spatter-defect-count, coated-area-evenness-spread, coverglass-obscured-aperture-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coated Coverglass Visual Appearance (space-systems/ecss/e2008-coated-coverglass-visual-appearance)

Use when the task is the coated-appearance inspection of ECSS-E-ST-20-08C
clause 8.7.1.3.1 -- the deposited face of a solar-cell coverglass examined
for whether the coating looks even and for whether it carries pinholes,
voids or spatter.

## Domain quick reference

- Two different kinds of question are asked of the same face. Evenness is
  a property of the whole coated field and shows up only when the face is
  read in several places; pinholes, voids and spatter are individual
  features with a size and a position. A face can pass one and fail the
  other, so neither answer substitutes for the other.
- Evenness is a spread, not a level. A coating that reads uniformly low
  is even; one that reads high in the middle and low at the ends is not,
  at the same mean. Reducing the sample to its average throws away the
  only thing the clause asked about.
- One reading is not a field. A single spot measurement is a level with
  no spread at all, so a face read once will always look perfectly even
  and the check quietly becomes a formality.
- Where a defect sits decides whether it counts. A pinhole inside the
  declared edge exclusion band is not in the optical path, so it is
  reported rather than graded; a pinhole a millimetre further in is
  graded in full.
- Density belongs to the aperture, not the face. Taking a count over the
  whole coated rectangle when the band is excluded divides by an area
  that was never graded, and every density comes out flattering.
- Three separate things can take a face out and they fail independently:
  one oversize blob, a crowd of small ones, and an obscured area that no
  single defect would have reached. A face where every defect is
  individually acceptable can still be losing too much aperture.
- Spatter is not cosmetic. Ejected coating material sits proud of the
  stack, scatters into the cell beneath it and is where delamination
  starts, so it is counted beside pinholes and voids rather than waved
  through as an appearance matter.
- A face with no appearance record is not an even face. It is an ungraded
  face, and the lot stays open until it is read.

## Workflow

1. Validate the appearance allowance set and the coated-area definition:
   coated width and height, the edge exclusion band a side, and the
   minimum number of appearance readings a face needs to be graded at
   all.
2. Reduce the coated face to its active aperture -- the coated rectangle
   less the exclusion band on every side -- and refuse a band that leaves
   no aperture behind.
3. Check each coverglass names the coating the aperture and allowances
   were written for; a face graded against another coating's definition
   is refused.
4. Reduce the sampled appearance readings to a non-uniformity spread, the
   range over the mean, and place it against the evenness allowance and
   its rework margin.
5. Size each point defect as a projected circle, take its distance from
   the edge, and hold back everything inside the exclusion band as
   reported rather than graded.
6. Grade the graded set three ways: the largest defect against the size
   allowance, the count over the aperture against the density allowance,
   and the summed projected area against the obscured-area allowance.
7. Roll the lot up: how many faces carry a finding, how much of the lot
   allowance is left, which faces were never read and which carry no
   record at all.
8. Report the worst disposition, the faces not accepted, the remaining
   allowance and the completeness flag.

## Pitfalls

- Averaging the appearance readings and comparing the average with a
  target. The average is the level; the clause asked about the spread.
- Grading a face read in one place. It reads perfectly even by
  construction, which is why a minimum sample size is validated before
  any spread is taken.
- Counting defects that sit in the edge exclusion band. They are outside
  the optical path, and folding them in condemns faces that are fit.
- Taking the defect density over the whole coated rectangle while
  excluding the band from the grading. The denominator then covers area
  that was never inspected.
- Treating spatter as an appearance matter rather than a defect. It sits
  proud of the stack and is where the coating starts to come off.
- Passing a face because no single defect is oversize. Enough acceptable
  defects still obscure more aperture than the allowance permits.
- Closing a lot in which some faces were never read. Omission reads as a
  pass on the only question the clause asks.
- Comparing a spread, a density or an obscured fraction with its limit by
  bare arithmetic. A density is a count over an area converted between
  square millimetres and square centimetres and an obscured fraction is a
  sum of circle areas over a rectangle, so a value that should land
  exactly on its limit lands a few units in the last place either side of
  it and differently on different machines; the comparison absorbs that
  representation error while the limit stays untouched.

## Behavior contract (gate 3)

The allowance and coated-area validation, the active aperture derivation
and its refusal of a band that consumes the face, the non-uniformity
spread with its minimum sample size, the projected area of each point
defect, the edge-band hold-back, the size, density and obscured-area
grading with their rework margins, and the lot allowance with its
remaining budget and completeness rollup are exercised by the gate 3
contract test:
scripts/test_e2008_coated_coverglass_visual_appearance.py against
scripts/e2008_coated_coverglass_visual_appearance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coated_coverglass_visual_appearance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
