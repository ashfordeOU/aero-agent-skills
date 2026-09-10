---
name: e1004-trapped-proton-wc
description: "Use when computing worst-case trapped proton radiation flux spectra for a space mission per ECSS-E-ST-10-04C: apply AP-8/AP-9-class models over solar maximum and solar minimum epochs, build the point-wise maximum envelope across source models and epochs, and categorize which source dominates at each energy to support radiation design margin analysis. Trigger: trapped protons, AP-8, AP-9, solar maximum, solar minimum, worst-case spectrum, point-wise envelope, radiation design margin, e-st-10-04, ecss."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-10-04c, trapped-protons, ap-8, ap-9, solar-maximum, solar-minimum, worst-case]
  version: 0.1.0
  author: Aero Agent Skills
---

# E1004 Trapped Proton Worst-Case Model (ECSS-E-ST-10-04C)

## Overview

Builds the ECSS-E-ST-10-04C worst-case trapped proton environment by combining
AP-8 (solar minimum / solar maximum epoch) spectra, and optionally an AP-9
percentile-class spectrum, into a single conservative envelope spectrum for
use in shielding, TID, and SEE-rate design margin studies.

## When to use this skill

- Categorizing a mission orbit's trapped-proton severity ahead of a PDR/CDR
  radiation design report.
- Combining epoch-specific (solar max/min) AP-8 outputs into one conservative
  bounding spectrum instead of picking a single epoch by hand.
- Deriving a worst-case AP-9 percentile spectrum (e.g. mean, 95th, 99th) for
  margin studies alongside legacy AP-8 outputs.
- Feeding downstream SEE-rate or total-ionizing-dose calculations that need a
  single bounding trapped-proton spectrum rather than separate epoch cases.

## Standard reference

ECSS-E-ST-10-04C, *Space environment* — trapped radiation belts clause,
worst-case trapped proton model (AP-8/AP-9 class spectra). Complements the
orbit-specific trapped models (LEO/GEO/MEO) by providing the epoch-agnostic
conservative bound rather than a single-epoch or orbit-averaged estimate.

## Inputs

- AP-8 MIN spectrum: differential proton flux (protons/cm^2/s/MeV) vs energy
  (MeV), strictly increasing energy grid.
- AP-8 MAX spectrum: same format, solar maximum epoch.
- Optional AP-9 percentile spectrum: same format, for a chosen confidence
  level (e.g. mean, 95th, 99th percentile output of AP-9).
- All flux values must be non-negative and finite; all energies must be
  positive, finite, and strictly increasing within a spectrum.

## Method

1. Validate each input spectrum (non-empty, matching lengths, strictly
   increasing energy grid, non-negative finite flux).
2. Resample all supplied spectra onto a common energy grid (the union of grid
   points within the overlapping energy range) using log-log linear
   interpolation, which is the standard interpolation form for trapped-proton
   differential spectra spanning several decades of flux.
3. Build the worst-case envelope by taking the point-wise maximum flux across
   AP-8 MIN, AP-8 MAX, and (if supplied) the AP-9 percentile spectrum at each
   energy point. Record which source spectrum was the dominant (maximum) one
   at each point for traceability.
4. Integrate the differential worst-case envelope into an integral flux
   spectrum (flux above each energy threshold) via log-safe trapezoidal
   integration, for direct use in shielding/dose calculations.

## Outputs

- Worst-case differential flux spectrum (energy grid + flux array).
- Worst-case integral flux spectrum (flux above each energy threshold).
- Per-point dominant-source labels (`ap8_min`, `ap8_max`, or
  `ap9_percentile`) so the envelope can be traced back to its driving model
  for review.

## Script usage

`scripts/e1004_trapped_proton_wc_logic.py` exposes:

- `make_spectrum(energies_mev, flux)` — build and validate a `ProtonSpectrum`.
- `resample_spectrum(spectrum, energy_grid_mev)` — log-log resample onto a
  new energy grid.
- `build_worst_case_envelope(ap8_min, ap8_max, ap9_percentile=None)` —
  point-wise-max envelope construction plus dominant-source labels.
- `integrate_integral_spectrum(spectrum)` — log-safe trapezoidal integration
  of a differential spectrum into an integral spectrum.
- `compute_worst_case_trapped_proton_spectrum(ap8_min, ap8_max, ap9_percentile=None)`
  — top-level orchestration returning a `WorstCaseTrappedProtonResult`.

Run tests with `pytest scripts/test_e1004_trapped_proton_wc.py`.

## Limitations

- The AP-8/AP-9 envelope combination is a bounding approximation for design
  margin purposes, not a physical time-dependent model of belt dynamics.
- Does not perform SAA (South Atlantic Anomaly) transit weighting or orbit
  averaging — pair with an orbit-specific trapped model (e.g.
  `e1004-trapped-leo`) to get mission-averaged fluence.
- Log-log interpolation and integration require strictly positive energies;
  zero or negative flux values fall back to linear interpolation for that
  segment rather than raising an error.
