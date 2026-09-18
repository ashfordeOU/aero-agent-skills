---
name: q7003-dyeing-process-requirements
description: "Evaluate the inorganic dyeing of an anodic coating to a black finish under the ECSS-Q-ST-70-03C process clause. Use when the two-bath dye sequence, its chemistry, its immersion time or its colour result has to be set or defended before a lot is released: confirm the salt-loading bath, the intermediate rinse and the pigment-precipitation bath appear in that order, place each bath concentration, pH and temperature inside its window, bound the wait between the anodizing rinse and the dye, scale the immersion time to the coating depth, and accept the colour on its mean, its weakest point and its spread. Trigger: ecss, q-st-70-03-black-anodizing-scope, inorganic-black-dye-sequence, dye-bath-concentration-window, dye-immersion-time-scaling, anodize-to-dye-hold-time, black-finish-absorptance-uniformity."
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
  tags: [ecss, q-st-70-03-black-anodizing-scope, q7003-dyeing-process-requirements, inorganic-black-dye-sequence, dye-bath-concentration-window, dye-immersion-time-scaling, anodize-to-dye-hold-time, black-finish-absorptance-uniformity, dye-pore-loading-depth]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Black Anodizing — Dyeing Process Requirements (space-systems/ecss/q7003-dyeing-process-requirements)

Use when the task is the dyeing step of the ECSS-Q-ST-70-03C process
clause -- the inorganic route to a black anodic finish, where the
colour is precipitated inside the pores of the coating rather than
adsorbed onto its surface, and where the acceptance is a measurement
rather than an opinion about the shade.

## Domain quick reference

- An inorganic black is made in two baths, not one. The coating is
  first loaded with a metal salt that soaks into the pores, and the
  pigment is then precipitated in place in a second bath. The colour
  that results is a solid sitting inside the coating, which is why it
  survives vacuum and temperature where an organic dye does not.
- The rinse between the two baths is a process step, not housekeeping.
  Salt carried on the surface into the second bath precipitates in the
  tank instead of in the pore, and what it leaves on the part is a
  loose smut that rubs off as a grey smear.
- A freshly anodized coating is the only one that dyes evenly. The
  pores start to close as the coating ages and dries, so the window
  from the anodizing rinse to the first dye bath is bounded, and it is
  the parameter most often left off a process sheet entirely.
- Immersion time follows the coating depth. A thicker coating is a
  deeper pore to load, so the time scales with the thickness above a
  floor that covers the surface itself. A fixed dip time set for a
  thin coating leaves a thick one loaded only near the mouth of each
  pore, where the first handling scuff takes the colour off.
- The colour is graded three ways at once because it fails three ways.
  The mean solar absorptance says the finish is black on average, the
  weakest single reading says no corner of the part is grey, and the
  spread between readings says the part is one colour rather than a
  gradient. A lot accepted on the mean alone passes with a pale edge.
- Bath chemistry moves the colour before it moves anything visible in
  the tank. Concentration, pH and temperature each carry their own
  window in each of the two baths, and a bath drifting out of one of
  them produces a dye that looks the same going in and comes out a
  shade short.

## Workflow

1. Validate the run record and reject an unknown bath or step rather
   than treating it as an extra.
2. Confirm the three dye steps are present and in order, because the
   intermediate rinse in the wrong place is a smut mechanism rather
   than a scheduling detail.
3. Place each declared bath inside its concentration, pH and
   temperature windows, and report a missing bath record as a finding
   rather than as a clean bath.
4. Bound the hold between the anodizing rinse and the first dye bath.
5. Derive the immersion time the coating depth needs and compare it
   with the declared time, treating a declared time that lands exactly
   on the requirement as acceptable.
6. Reduce the absorptance readings to a mean, a minimum and a spread,
   and grade all three against acceptance; report an absent
   measurement set as a finding of its own.
7. Report the required immersion time, the colour statistics, the
   findings and one verdict per run, and name the failing runs across
   a batch.

## Pitfalls

- Accepting the lot on the mean absorptance. A part that reads black
  at three points and grey at the fourth has the same mean as a part
  that is evenly slightly-dark, and only the spread and the minimum
  tell the two apart.
- Dyeing on a fixed dip time. The time that loads a thin coating fully
  loads a thick one only at the pore mouth, and the difference shows
  up as colour that wipes off rather than as a shade that is visibly
  wrong at inspection.
- Parking anodized parts until the dye line is free. The pores close
  while they wait, so the same dye bath that worked an hour ago
  produces a lighter, patchier finish, and nothing in the dye record
  explains why.
- Skipping the intermediate rinse to save a tank position. The pigment
  then forms in the second bath instead of in the coating, which
  simultaneously wastes the chemistry and leaves loose solid on every
  part in the load.
- Treating pH as a slow variable. It moves with drag-in from the
  previous rinse, and a bath a full point off its window will dye to a
  visibly different black while its concentration titration still
  reads perfect.

## Behavior contract (gate 3)

The dye-step ordering, per-bath windows, hold bound, depth-scaled
immersion time, absorptance statistics, three-way colour acceptance
and run verdict are exercised by the gate 3 contract test:
scripts/test_q7003_dyeing_process_requirements.py against
scripts/q7003_dyeing_process_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7003_dyeing_process_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
