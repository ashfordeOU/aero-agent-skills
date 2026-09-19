---
name: q7005-applicability-and-methods
description: "Determine whether infrared spectroscopy applies to a surface contamination case and which method family is in scope. Use when the ECSS-Q-ST-70-05C applicability clauses have to become a decision: confirm the contaminant is organic and its diagnostic band falls inside the instrument range, settle whether the flight surface or a witness plate is the sampling object, compute how much of the flight surface a plate actually represents from its exposure, view-factor and accommodation ratios, then admit the direct and indirect method families whose areal detection limit reaches the required cleanliness level. Trigger: ecss, q-st-70-05-ir-contamination-scope, ir-contamination-method-applicability, direct-ir-reflection-absorption, indirect-solvent-extraction-measurement, witness-plate-representativeness, organic-contamination-detection-level."
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
  tags: [ecss, q-st-70-05-ir-contamination-scope, q7005-applicability-and-methods, ir-contamination-method-applicability, direct-ir-reflection-absorption, indirect-solvent-extraction-measurement, witness-plate-representativeness, organic-contamination-detection-level]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS IR Contamination Measurement — Applicability and Methods (space-systems/ecss/q7005-applicability-and-methods)

Use when the task is the applicability and scope side of ECSS-Q-ST-70-05C
— whether infrared spectroscopy addresses this contamination case at all,
what object is actually being sampled, and which of the direct and
indirect method families can reach the cleanliness level the programme
asked for.

## Domain quick reference

- The technique detects organic species through an infrared-active
  diagnostic band. Two things have to be true together: the species is
  organic, and its band falls inside the instrument's spectral range. A
  species that fails either is outside the technique, not a hard case for
  it, and the answer is a different measurement rather than a longer scan.
- An unstated answer to "is it organic" is not a no. The screening refuses
  a contaminant record that does not declare it, because defaulting the
  flag either way produces a confident wrong scope decision.
- The direct family reads the contaminant layer on the surface through a
  reflection-absorption measurement. Its areal detection limit is the
  instrument's absorbance limit divided by the contaminant's specific
  absorbance and by the number of passes the beam makes through the layer,
  so a multiple-reflection geometry buys sensitivity directly.
- The indirect family extracts into a solvent and measures the residue.
  Its areal limit is the cell's mass limit spread back over the area
  actually sampled and corrected for the fraction the extraction
  recovered, so area buys sensitivity the way passes do for the direct
  family. Too small an area puts the residue under the cell limit by
  construction, which is why the sampled area carries a floor.
- Neither family is inherently the more sensitive one. Which limit is
  lower depends on the specific absorbance, the pass count, the sampled
  area and the recovery, and the arithmetic decides it case by case.
- A witness plate is a stand-in and represents the flight surface only to
  the extent its exposure time, its view of the source and its
  accommodation of arriving species match. Those three ratios multiply,
  and the scaling from a plate reading to a flight-surface level is the
  reciprocal of the product. Below a declared fraction the plate cannot be
  scaled at all and a reading from it means nothing about the hardware.

## Workflow

1. Validate the policy: an instrument range with the high edge above the
   low one, a represented-fraction floor, and positive detection limits.
2. Screen the contaminant on both conditions at once and report both
   reasons when both fail, rather than stopping at the first.
3. Settle the sampling object explicitly. A value that is neither the
   flight surface nor a witness plate is an input error.
4. For a witness plate, form the represented fraction from the three
   ratios and the scaling from its reciprocal, and check the fraction
   against the floor.
5. Build the areal detection limit of each family from its own quantities,
   then admit every family whose limit reaches the required level and
   record a reason against every family excluded.
6. Close with the findings and the reporting duties: the scaling actually
   applied, and the diagnostic band the identification rests on.

## Pitfalls

- Treating a non-detection as a clean surface when the species was never
  in scope. An inorganic residue or a band outside the range produces the
  same flat spectrum as a clean coupon.
- Reporting a witness-plate number as a flight-surface level. The plate
  saw a different exposure and a different view of the source; the scaling
  is part of the result, not an optional refinement.
- Assuming the direct family is always the more sensitive one because it
  touches the hardware. Sampled area and recovery can put the indirect
  limit well below it, and the comparison is arithmetic, not doctrine.
- Shrinking the sampled area to make wiping easier. The residue mass falls
  with the area while the cell limit does not, so the areal limit rises
  and the measurement stops being able to see the requirement.
- Comparing a detection limit against the required level with a bare
  strict inequality. A limit built from divisions can land a few units in
  the last place either side of a requirement set equal to it; the
  admissibility comparison absorbs that while the requirement stays fixed.
- Deciding the method before deciding the sampling object. The areal limit
  of the indirect family depends on the area of the object sampled, so the
  two decisions cannot be taken in that order.

## Behavior contract (gate 3)

The policy validation, band-in-range check, contaminant screening, witness
plate representativeness and its scaling, the direct and indirect areal
detection limits and the admissibility decision are exercised by the gate
3 contract test: scripts/test_q7005_applicability_and_methods.py against
scripts/q7005_applicability_and_methods_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7005_applicability_and_methods.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
