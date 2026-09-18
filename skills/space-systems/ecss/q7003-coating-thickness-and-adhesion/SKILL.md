---
name: q7003-coating-thickness-and-adhesion
description: "Verify an anodized coating against its thickness band, coverage, adhesion and colour uniformity. Use when a batch of anodized aluminium parts has to be graded before acceptance: check every thickness reading against both the minimum and the maximum, size the bare area as a fraction of the graded surface once declared masking is removed, categorize the bend or tape outcome as no-separation, crazing-only, flaking or detachment and read crazing differently on a formed part, measure the colour spread about the reference rather than any single point, then take the worst of the four and name the characteristic that drove it. Trigger: ecss, q-st-70-03-anodizing, anodized-coating-thickness-band, anodize-coverage-fraction, anodize-coating-adhesion-outcome, anodize-colour-uniformity, anodized-batch-acceptance-verdict."
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
  tags: [ecss, q-st-70-03-anodizing, q7003-coating-thickness-and-adhesion, anodized-coating-thickness-band, anodize-coverage-fraction, anodize-coating-adhesion-outcome, anodize-colour-uniformity, anodized-batch-acceptance-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Anodizing — Coating Thickness and Adhesion (space-systems/ecss/q7003-coating-thickness-and-adhesion)

Use when the quality clause of ECSS-Q-ST-70-03 is the task: deciding
whether an anodized coating on a batch of aluminium parts is acceptable
on the four characteristics that are graded at inspection -- thickness,
coverage, adhesion and colour uniformity.

## Domain quick reference

- Thickness is a two-sided requirement, not a floor. A thin coating
  fails on corrosion and wear life; a thick one fails on dimensional
  growth and on brittleness, because the coating grows both outward and
  into the substrate. Grading against the minimum alone passes parts
  that will craze at the first bend.
- Every reading is graded, not the mean. A rack averages well while one
  end of it sat in a cooler, less agitated part of the tank, so a mean
  inside the band hides the points that are outside it.
- Coverage is judged over the graded area, which is the wetted surface
  minus the area that was deliberately masked. Masking is a declared
  feature; anything else that took no coating is bare metal and counts
  against the allowance however small the readings elsewhere were.
- Adhesion outcomes group as no-separation, crazing-only, flaking and
  detachment. Crazing is the expected response of a hard, relatively
  brittle coating to a forming radius, so on a formed part it is a
  review outcome that sends the radius and the thickness back for
  comparison. On a flat or machined part nothing should have crazed, so
  the same outcome points at an over-thick or over-aged coating.
- Colour is a sealed-and-dyed property that varies across a rack with
  dwell, temperature and dye age. The graded quantity is the spread of
  the sample about the declared reference, so a sample that is uniformly
  offset and a sample that is uniformly scattered fail for different
  reasons and both have to be visible in the result.
- The batch verdict is the worst of the four characteristics, and the
  driving characteristic is named. A bare verdict sends the reviewer
  back to the whole line; a named characteristic points at the tank
  step, the rack, the mask or the dye.

## Workflow

1. Grade the thickness readings against the specified minimum and
   maximum. Report the count below, the count above and the count in
   band, together with the extreme reading on each side, so the spread
   of the rack is visible and not just the pass or fail.
2. Resolve the graded area by subtracting the declared masking from the
   total surface, then express the bare area as a fraction of it.
   Reject a masking declaration that consumes the surface and a bare
   area larger than the surface it sits on, because both mean the
   inspection record is inconsistent rather than the part being bad.
3. Categorize the adhesion outcome and apply the part form. A formed
   part earns the conditional reading of crazing; a flat or machined one
   does not.
4. Take the colour sample against the reference, report the worst
   deviation, the mean deviation and the raw spread, and grade the worst
   deviation against the tolerance.
5. Combine the four into a single verdict by taking the worst, list
   every characteristic that sits at that worst level, and prefix each
   finding with the characteristic it came from.
6. Where a reading, a fraction or a deviation should land exactly on its
   limit, grade it with the tolerant comparison rather than bare
   arithmetic, so a unit conversion cannot turn an on-limit part into a
   reject.

## Pitfalls

- Grading the mean thickness instead of each reading. The mean is not a
  requirement; it is a summary that hides the low corner of the rack,
  which is exactly the region that will corrode first.
- Treating the specified thickness as a minimum only. Dimensional growth
  on a close-tolerance feature and crazing at a forming radius are both
  failures of an over-thick coating, and neither shows up in a check
  that only looks downward.
- Counting masked area as a coverage shortfall. Masking is declared and
  intended, so leaving it in the denominator and the numerator both
  understates coverage and hides the real bare spots among it.
- Reading crazing as a pass because the coating is still attached. It is
  a cracked coating, and on a part that was never formed it is evidence
  that the coating is out of condition rather than evidence about the
  geometry.
- Judging colour on a single witness coupon. One point cannot show the
  spread of a rack, so a batch that is visibly two-tone can pass on a
  coupon taken from the middle of it.
- Comparing an on-limit reading by bare arithmetic. A reading that was
  specified to land exactly on the band edge can evaluate a few units in
  the last place below it after a unit conversion, so the comparison has
  to absorb that representation error while the limit stays untouched.

## Behavior contract (gate 3)

The thickness grading, coverage resolution, adhesion categorization,
colour uniformity and the combined batch verdict are exercised by the
gate 3 contract test:
scripts/test_q7003_coating_thickness_and_adhesion.py against
scripts/q7003_coating_thickness_and_adhesion_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7003_coating_thickness_and_adhesion.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
