---
name: q7005-ir-analysis-of-extract
description: "Determine the areal mass of organic surface contamination from the indirect solvent-extract route of ECSS-Q-ST-70-05C. Use when a known area has been rinsed or wiped, the extract concentrated and an aliquot cast as a film on an infrared window, and the recorded band absorbance has to become a defensible microgram-per-square-centimetre figure. Subtracts the solvent blank, refuses a net absorbance under the quantification floor, restores the aliquot and recovery factors the cast film hides, and matches band positions against reference spectra, reporting an ambiguous identification instead of picking the higher score. Trigger: ecss, q-st-70-05, indirect-extract-ir-analysis, cast-film-infrared-window, solvent-extract-blank, reference-spectra-band-match, extraction-recovery-fraction, contamination-areal-mass."
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
  tags: [ecss, q-st-70-contamination-infrared-scope, q7005-ir-analysis-of-extract, indirect-extract-ir-analysis, cast-film-infrared-window, solvent-extract-blank, reference-spectra-band-match, extraction-recovery-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Organic Contamination by IR — Indirect Extract Analysis (space-systems/ecss/q7005-ir-analysis-of-extract)

Use when the task is the indirect arm of ECSS-Q-ST-70-05C — a surface of
known area is sampled with solvent, the extract is cast as a film on an
infrared window, and the spectrum of that film has to yield both the
identity of the contaminant and the mass per unit area it came from.

## Domain quick reference

- The indirect route measures the film on the window, not the surface.
  Everything between the two is a chain of factors: the fraction of the
  contaminant the solvent actually lifted, the fraction of the extract
  volume that was cast, and the area that was sampled. Losing any one of
  them shifts the reported figure by that whole factor, and the figure
  still looks plausible.
- The quantitative signal is the net band absorbance: the band height or
  area above a local baseline, less the same band measured on a solvent
  blank carried through the identical evaporation. A blank that is a
  large share of the gross reading means the number is reporting the
  solvent, not the hardware.
- Identification is a band-position exercise. A candidate is supported
  when the characteristic positions of a reference spectrum are present
  within the instrument resolution; it is not supported by a single
  carbonyl or C-H stretch, which almost every organic contaminant has.
- Two candidates whose band sets are both well covered are an ambiguous
  result, not a close call to be settled by the higher score. Silicones,
  hydrocarbon oils and plasticisers overlap enough that the honest output
  is the pair plus a request for a discriminating band.
- The response of the window-plus-instrument combination is a calibration
  input, in absorbance per microgram of deposit. It belongs to the
  method and the band, not to the sample, and a figure produced without
  one is an index, not a mass.

## Workflow

1. Validate the sampling record: sampled area, solvent volume, cast
   aliquot volume no larger than the extract, and a recovery fraction in
   the open-to-unity range. A missing recovery is an input error, not an
   implied unity.
2. Form the net absorbance from the gross band reading, its local
   baseline and the blank. Refuse a negative net beyond the noise; hold a
   net under the quantification floor as a bounded below-floor statement
   rather than a small positive mass.
3. Convert the net absorbance to the mass of deposit on the window
   through the method response for that band.
4. Restore the dilution factor — extract volume over cast aliquot volume
   — to recover the mass in the whole extract.
5. Divide by the recovery fraction to recover the mass that was on the
   surface, then by the sampled area to obtain the areal mass.
6. Score every reference spectrum in the library by the share of its
   characteristic bands found within the matching tolerance, and flag the
   result ambiguous when the two best scores sit inside the separation
   margin.
7. Report the areal mass, the identification, the blank share and every
   finding raised, so a reviewer can see which factor carried the number.

## Pitfalls

- Reporting the cast-film mass as the surface mass. The aliquot is
  typically a small share of the extract, so the two differ by the
  dilution factor and the error is always in the optimistic direction.
- Taking recovery as unity because it was not measured. A wipe on a
  textured surface can leave most of the deposit behind; an unmeasured
  recovery is a gap in the method, and the assessment should say so.
- Quantifying on a band the solvent blank also shows. The blank share is
  part of the result, and a blank contributing a large fraction of the
  gross reading invalidates the quantification on that band.
- Identifying on one band. A single strong absorption is shared by whole
  families of contaminants; identification needs the characteristic set,
  and the unmatched observed bands matter as much as the matched ones.
- Settling an ambiguous pair on the score. When two references are both
  covered inside the separation margin, the method has not discriminated
  them and reporting the winner manufactures a certainty the spectrum
  does not hold.

## Behavior contract (gate 3)

The sampling-record validation, blank-corrected net absorbance, cast-film
mass conversion, dilution and recovery restoration, areal-mass reduction
and the reference-spectra matching with its ambiguity rule are exercised
by the gate 3 contract test:
scripts/test_q7005_ir_analysis_of_extract.py against
scripts/q7005_ir_analysis_of_extract_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7005_ir_analysis_of_extract.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
