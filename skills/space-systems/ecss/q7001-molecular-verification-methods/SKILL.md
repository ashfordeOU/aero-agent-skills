---
name: q7001-molecular-verification-methods
description: "Derive a non-volatile residue surface density from a molecular cleanliness measurement. Use when a solvent rinse reduced gravimetrically or by infrared absorbance, or a witness plate standing in for an unrinsable surface, has come back under ECSS-Q-ST-70-01C: subtract the solvent blank, divide by the aliquot fraction taken for evaporation, turn an absorbance into a mass through path length and absorptivity, scale up for the residue the rinse left behind, transfer a plate reading onto the hardware through declared view-factor and exposure ratios, and report anything under the balance-driven floor as a non-detect. Trigger: ecss, q-st-70-01c, non-volatile-residue-density, solvent-rinse-gravimetric-aliquot, solvent-rinse-infrared-absorptivity, molecular-witness-plate-transfer, nvr-detection-floor, rinse-recovery-fraction."
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
  tags: [ecss, q-st-70-01-cleanliness-scope, q7001-molecular-verification-methods, non-volatile-residue-density, solvent-rinse-gravimetric-aliquot, solvent-rinse-infrared-absorptivity, molecular-witness-plate-transfer, nvr-detection-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness -- Molecular Measurement Methods (space-systems/ecss/q7001-molecular-verification-methods)

Use when the task is the molecular measurement step of cleanliness
verification under ECSS-Q-ST-70-01C: a solvent rinse has been weighed or
read on an infrared spectrometer, or a witness plate has been recovered,
and the reading has to become a non-volatile residue surface density the
cleanliness requirement can be graded against.

## Domain quick reference

- The weighed number is not the residue. A rinse is caught in a volume,
  an aliquot of that volume is evaporated, and the mass on the dish
  belongs to the aliquot; recovering the whole rinse means dividing by
  the fraction taken.
- The solvent carries its own residue. A blank of the same lot, taken
  through the same evaporation, is subtracted first, and a blank at or
  above the sample leaves nothing attributable to the surface.
- An infrared reading is a concentration, not a mass. Beer-Lambert turns
  absorbance into grams per litre through the cell path length and the
  absorptivity of the compound the calibration was built on, and the
  rinse volume turns that into a mass.
- A rinse lifts a fraction of what is there. The recovery fraction for
  that solvent, technique and surface scales the density up; leaving it
  out reports a lower bound as if it were the value.
- A witness plate measures the plate. Transferring its density to the
  hardware needs the ratio of the view factors to the contaminating
  source and the ratio of the exposure times, and an undeclared ratio
  cannot be assumed to be unity.
- The detection floor moves with the setup. Balance readability, the
  aliquot fraction and the recovery all divide into it, so the same
  balance gives a different floor on a small rinsed area than on a
  large one.

## Workflow

1. Validate the geometry and fractions: positive rinsed area, aliquot
   and recovery fractions inside the unit interval, non-negative masses
   and absorbances.
2. Reduce the gravimetric route: subtract the blank from the weighed
   residue and divide by the aliquot fraction to recover the whole
   rinse.
3. Reduce the infrared route: convert absorbance to a concentration
   through path length and absorptivity, multiply by the rinse volume
   for a mass, then subtract the blank and recover the aliquot.
4. Divide the mass by the rinsed area for a density, then scale up by
   the rinse recovery fraction.
5. For a witness plate, form the transfer ratio from the view factors
   and exposure hours and apply it, recording in the findings that the
   number stands in for the surface rather than measuring it.
6. Compute the detection floor from balance readability, area, aliquot
   and recovery; report a density at or below it as a non-detect, and a
   floor above the allowed density as a method that cannot substantiate
   the requirement.
7. Grade the density against the allowed value with a named relative
   tolerance at the boundary.

## Pitfalls

- Reporting the aliquot mass as the rinse mass. A quarter aliquot
  under-reports by a factor of four, and the error is invisible in the
  number itself.
- Assuming unity recovery because the recovery fraction was never
  measured. The reduction then produces a confident value that is a
  lower bound, and a marginal surface reads as compliant.
- Using an absorptivity from a different compound than the contaminant.
  Beer-Lambert is exact; the absorptivity is the assumption, and the
  mass inherits its error directly.
- Treating a witness plate density as the hardware density. The plate
  sees its own view factor for its own exposure, and both ratios move
  the number, often in the same direction.
- Quoting a value below the detection floor. A balance reading at its
  own readability is a non-detect, and printing it as a density invites
  a comparison the instrument cannot support.
- Grading against a limit the method cannot reach. A floor above the
  allowed density makes a compliant-looking result meaningless, which
  is a finding about the method rather than about the surface.

## Behavior contract (gate 3)

The blank subtraction, aliquot recovery, Beer-Lambert reduction, rinse
recovery scaling, witness-plate transfer ratio, detection-floor and
non-detect handling and the boundary-tolerant grading are exercised by
the gate 3 contract test:
scripts/test_q7001_molecular_verification_methods.py against
scripts/q7001_molecular_verification_methods_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_molecular_verification_methods.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
