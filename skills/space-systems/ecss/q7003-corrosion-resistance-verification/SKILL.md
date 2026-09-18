---
name: q7003-corrosion-resistance-verification
description: "Verify the corrosion resistance of a sealed anodized coating from its seal quality and its salt fog result together. Use when a coupon set has come out of neutral salt fog and someone has to say whether the coating is qualified: refer the seal admittance to a common coating thickness before grading it, group the seal as well-sealed, marginally-sealed or unsealed, count attack both as a density over the exposed area and as a largest single site so neither hides the other, and report an exposure that was cut short as inconclusive rather than crediting time the coupon never spent under fog. Trigger: ecss, q-st-70-03-anodizing, anodize-seal-quality-admittance, anodize-salt-fog-exposure, anodize-corrosion-attack-density, sealed-anodize-qualification."
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
  tags: [ecss, q-st-70-03-anodizing, q7003-corrosion-resistance-verification, anodize-seal-quality-admittance, anodize-salt-fog-exposure, anodize-corrosion-attack-density, sealed-anodize-qualification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Anodizing — Corrosion Resistance Verification (space-systems/ecss/q7003-corrosion-resistance-verification)

Use when the task is the corrosion-resistance clause of ECSS-Q-ST-70-03:
deciding whether a sealed anodized coating has demonstrated the
resistance the design relies on, from the seal measurement and the salt
fog exposure taken together rather than from either alone.

## Domain quick reference

- Corrosion resistance is bought by the seal, not by the anodic layer.
  An unsealed layer is porous and takes up chloride as readily as it
  took up dye, so a thickness result says nothing about resistance on
  its own.
- Seal quality is read indirectly as an admittance: the lower the
  residual porosity, the lower the reading. The reading has to be
  referred to a common coating thickness first, because a thicker
  coating presents more sealed pore area and reads high at the same real
  seal quality. Grading raw readings makes thick coatings look worse
  than thin ones for the wrong reason.
- The seal groups into three states rather than two. A marginal seal is
  neither a pass nor a reject; it is a dwell or temperature finding
  against the seal tank that has to be raised while the parts are still
  together.
- Salt fog attack is graded twice over. Density over the exposed area
  catches a fine scatter that a small worst-case size would hide; the
  largest single site catches one deep pit that an acceptable count
  would hide. A coupon has to clear both.
- Density has to be normalised by the exposed area. A raw site count
  means nothing until the area it was counted over is known, and coupon
  areas differ between racks and between programmes.
- An exposure that was cut short is inconclusive, not a partial pass and
  not a failure. The coating is not credited for hours it did not spend
  under fog, and a clean short-run coupon is the easiest way to certify
  a coating that would not have survived the full duration.
- A clean coupon on an unsealed coating is a warning, not a result that
  carries. The coupon is small, flat and freshly made; a production part
  has edges, fasteners and a larger exposed area, so the finding travels
  with the verdict.

## Workflow

1. Refer the measured seal admittance to the reference coating
   thickness, then group the seal as well-sealed, marginally-sealed or
   unsealed against the declared limits. Reject a limit set whose
   marginal bound sits below its sealed bound.
2. Check the exposure duration against the required duration before
   looking at the coupon at all. If it is short, stop and report the run
   as inconclusive with the shortfall named; do not grade attack on a
   run that was not completed.
3. Convert the attack site count into a density over the exposed area,
   and take the largest single site alongside it. Reject a record that
   carries a site size with a zero count, because the two halves of the
   inspection disagree.
4. Grade density and worst-case size separately against their
   allowances, and report both flags so the reviewer can see which of
   the two drove a failure.
5. Combine: the coating passes only when the exposure was complete, the
   attack cleared both allowances, and the seal was not in the unsealed
   group. Carry the marginal-seal finding into a pass rather than
   dropping it.
6. Where a normalised admittance or a density should land exactly on its
   allowance, grade it with the tolerant comparison, so a ratio of two
   measured quantities cannot fail on representation error alone.

## Pitfalls

- Grading the raw admittance reading. It scales with coating thickness,
  so a thick well-sealed coating and a thin poorly sealed one can return
  the same number and be graded identically when they are nothing alike.
- Reading a short salt fog run as a pass because the coupon looked
  clean. The coupon has simply not been asked the question yet, and
  recording it as a pass retires a verification that never happened.
- Counting attack sites without the exposed area. The count is not
  comparable between coupons of different size, and the allowance is a
  density, so a large coupon passes on a count that a small one fails.
- Letting one deep pit through because the overall count was low, or a
  fine scatter through because no single site was large. The two checks
  exist precisely because each one is blind to the other's failure mode.
- Dropping the marginal-seal finding once the coupon passed. The seal
  tank is drifting whether or not this particular rack survived, and the
  finding is the only warning the next batch gets.
- Treating a clean unsealed coupon as qualification for production
  parts. A coupon's geometry and exposed area are not the hardware's,
  and an open coating that survived a flat panel will not survive an
  assembled edge.

## Behavior contract (gate 3)

The admittance normalisation, seal grouping, exposure sufficiency check,
attack density and worst-site grading and the combined verdict are
exercised by the gate 3 contract test:
scripts/test_q7003_corrosion_resistance_verification.py against
scripts/q7003_corrosion_resistance_verification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7003_corrosion_resistance_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
