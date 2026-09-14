---
name: e2008-bare-cell-cracks-and-fingerprints
description: "Assess whether a bare solar cell may be accepted under ECSS-E-ST-20-08C clause 7.5.1.4.3, which admits no crack and no fingerprint: derive the crack detection floor from the working distance and any magnification, withhold an acceptance the illuminance cannot support, reject a confirmed crack at any length, send an indication recorded below the floor back for its provenance, clean a removable print but reject one on a contact area or on a cell out of cleaning cycles, and roll the lot up with its yield. Use when a bare-cell visual record has to become an acceptance verdict. Trigger: ecss, e-st-20-08c-clause-7-5-1-4-3, bare-solar-cell-acceptance, cell-crack-indication-disposition, cell-fingerprint-contamination, crack-detection-floor, bare-cell-lot-yield-rollup."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-cracks-and-fingerprints, bare-solar-cell-acceptance, cell-crack-indication-disposition, cell-fingerprint-contamination, crack-detection-floor, bare-cell-lot-yield-rollup, solar-cell-handling-contamination]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Bare Cell Cracks and Fingerprints (space-systems/ecss/e2008-bare-cell-cracks-and-fingerprints)

Use when the task is the bare-cell acceptance of ECSS-E-ST-20-08C clause
7.5.1.4.3 -- a cell is acceptable only when it carries no crack and no
fingerprint, and the record in hand has to be turned into that verdict
together with the bound the examination can actually support.

## Domain quick reference

- Both halves of the clause are absolutes. There is no permitted crack
  length and no permitted print, so neither half has a band to grade
  against; what a measurement buys is the confidence that the examination
  could have found the thing it says it did not find.
- A crack has no cosmetic size because the mechanism is not the fracture as
  found. It is the fracture after the thermal cycles the cell has not seen
  yet, and a 0.2 mm fracture propagates on the same physics as a 20 mm one.
  A confirmed crack is therefore a rejection at any length.
- What a length does answer is whether the examination could resolve it. The
  eye subtends roughly one arc minute, which at 300 mm is about 0.09 mm, so
  a cell called crack free is crack free down to that floor and silent below
  it. The floor is reported with the verdict rather than left implicit.
- The floor scales with the working distance and divides by any
  magnification. Two records that both say crack free can be worth several
  times as much detection as each other.
- Magnification runs one way here. Because no crack is admissible, a more
  sensitive instrument can only add rejections and can never withdraw one,
  so an aided finding stands while an aided acceptance is a stronger
  statement than the unaided one the clause has in mind.
- An indication recorded below the floor of the examination that supposedly
  produced it did not come from that examination. It is more likely a
  transcription from a different look, so it goes to review rather than
  being credited either way.
- A fingerprint separates on whether it can be taken off and where it sits.
  A removable print on a bare area is cleaned and looked at again. A print
  on a contact area is a rejection: the ionic residue ends up inside a weld
  zone and the cleaning that would lift it attacks the metallisation.
- Cleaning cycles are finite. A cell that has already spent its allowance
  has no cleaning route left, so the same print that was a cleaning ticket
  on a fresh cell is a rejection on that one.
- A positive finding survives a poor examination and an acceptance does
  not. A crack seen under bad light was still seen; a clean sheet produced
  under bad light is the expected result of looking in the dark.

## Workflow

1. Take the declared face count and the examination conditions for each
   cell. Reject a record claiming more faces than were declared, and report
   the shortfall when it claims fewer.
2. Derive the detection floor from the working distance, the acuity and any
   magnification, and keep the unaided floor beside it.
3. Check the conditions: working distance inside its limit and illuminance
   at or above the floor. A condition not met withholds acceptances without
   touching rejections.
4. Disposition every crack indication -- confirmed rejects, unconfirmed goes
   to review, and unconfirmed below the floor goes to review carrying a
   provenance question.
5. Disposition every print against its location, its removability and the
   cleaning cycles the cell has left.
6. Roll up: the governing disposition by severity rather than record order,
   then across the lot the accepted and rejected fractions, the cells not
   accepted and the largest detection floor -- which is the size the whole
   crack-free statement is bounded at.

## Pitfalls

- Grading a crack on length. There is no band; the length only tells you
  whether the look could have found it.
- Reporting crack free with no floor attached. The examination did not look
  for anything shorter than its floor, so the bare phrase overstates what is
  in hand.
- Treating a magnified record as interchangeable with an unaided one. It has
  a different threshold, and folding it in silently moves the acceptance
  criteria without anyone deciding to.
- Accepting a cell examined under bad light because nothing was found.
- Letting a poor examination overturn a rejection. The finding is positive
  evidence and it does not need good conditions to stay true.
- Cleaning a print off a contact area. The residue is inside the weld zone
  and the cleaning agent is on the metallisation.
- Sending a cell for a third clean because the print was small. The cycle
  allowance is spent, and the handling itself is what put prints on it.
- Taking the last disposition in the record as the cell verdict instead of
  the most severe one.
- Comparing a length with a derived floor by bare arithmetic. The floor
  comes out of a trigonometric conversion, so a length exactly on it can
  evaluate a few units in the last place below it; the comparison absorbs
  that representation error while the floor stays untouched.

## Behavior contract (gate 3)

The detection floor derivation, the condition checks, the crack and print
dispositioning, the below-floor provenance rule, the cleaning cycle
allowance, the severity rollup and the lot yield are exercised by the gate 3
contract test:
scripts/test_e2008_bare_cell_cracks_and_fingerprints.py against
scripts/e2008_bare_cell_cracks_and_fingerprints_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_cracks_and_fingerprints.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
