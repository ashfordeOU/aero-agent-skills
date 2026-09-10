---
name: e1004-trapped-leo
description: "Use when computing the trapped radiation electron environment for a LEO spacecraft per ECSS-E-ST-10-04C 9.2.1.2: apply AE-8/AE-9-class flux tables indexed by McIlwain L-shell and B-L (B/B0) coordinates, include the South Atlantic Anomaly dose contribution, and produce the differential and integral electron flux inputs for total-dose and internal-charging assessments of the spacecraft. Trigger: trapped electrons, LEO radiation environment, AE-8, AE-9, McIlwain L-shell, B-L coordinates, South Atlantic Anomaly, electron flux, e-st-10-04, ecss."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-10-04c, trapped-radiation, ae-8, ae-9, leo, south-atlantic-anomaly, mcllwain-l-shell]
  version: 0.1.0
  author: Aero Agent Skills
---

# E1004 Trapped LEO Electron Environment

## Overview

ECSS-E-ST-10-04C clause 9.2.1.2 requires that the trapped radiation electron
environment encountered by a Low Earth Orbit (LEO) spacecraft be categorized
using an AE-8- or AE-9-class model, expressed in McIlwain **L-shell** and
**B-L** (local field strength `B` versus `L`) coordinates rather than raw
geographic position. Most of a LEO orbit sits below the trapped belts, but
the offset and tilted geomagnetic dipole pulls the inner electron belt down
to spacecraft altitude over the South Atlantic — the **South Atlantic
Anomaly (SAA)** — so a correctly-built LEO mission dose budget must resolve
flux along the *entire* ground track, not just at apogee-like "belt" L-shells.

This leaf computes:
1. The dipole **B-L coordinate pair** for a satellite position (geodetic
   altitude, geomagnetic latitude/longitude).
2. The **AE-8/AE-9-class omnidirectional electron flux** (differential and
   integral, vs. energy) at that B-L point, via table lookup + interpolation.
3. An **orbit-averaged flux/fluence** for a full LEO ground track, so the
   SAA electron dose contribution is captured for shielding and SEE/TID
   analysis inputs downstream.

## When to invoke this skill

- Building or reviewing a radiation environment specification for a
  LEO mission (typically altitude 300–2000 km).
- Populating the trapped-electron input to a TID/displacement-damage or
  shielding (sectoring) analysis for LEO hardware.
- Cross-checking a vendor-supplied AE-8/AE-9 run (e.g. from SPENVIS or
  OMERE) against an independent order-of-magnitude estimate.

Not for GEO (`e1004-geo-ige`), MEO (`e1004-meo-meov2`), other/HEO trapped
environments (`e1004-trapped-other`), or worst-case trapped protons
(`e1004-trapped-proton-wc`) — those are separate leaves.

## Data provenance and fidelity notice

The flux coefficients embedded in `scripts/e1004_trapped_leo_logic.py`
(`AE_ELECTRON_TABLE`) are **representative, order-of-magnitude
engineering placeholders** calibrated to the published shape of AE-8
MIN/MAX omnidirectional electron flux vs. L-shell and energy — they are
**not** a transcription of the original NASA AE-8/AE-9 coefficient
files. For mission-grade, traceable analysis, replace `AE_ELECTRON_TABLE`
with vetted coefficients exported from SPENVIS, OMERE, or the AE9/AP9
(IRENE) tool, keeping the same lookup interface
(`flux_differential`, `flux_integral`). The interpolation, B-L geometry,
and orbit-averaging logic are model-independent and do not need to
change when the table is swapped.

## Steps

1. **Define the orbit.** Supply semi-major axis (or altitude) and
   inclination; the logic module propagates a simplified circular ground
   track (dipole-field approximation, no perturbations — adequate for an
   environment-categorization estimate, not for precision orbit
   determination).
2. **Compute B-L per ground-track sample.** `geodetic_to_bl()` converts
   each sampled position to centered-dipole `(B, L)` coordinates.
3. **Look up flux at each sample.** `flux_differential(energy_mev, l, b_b0)`
   and `flux_integral(energy_mev, l, b_b0)` interpolate the table across
   `L`, the `B/B0` attenuation ratio, and electron energy.
4. **Aggregate over the orbit.** `orbit_average_flux()` time-weights the
   per-sample flux across one full orbit (equal-time ground-track
   sampling), returning the mean flux spectrum and the samples where SAA
   dip dominates (`l < 2.0`) flagged separately so their contribution is
   auditable.
5. **Report.** Output units are `cm^-2 s^-1` (differential: `cm^-2 s^-1
   MeV^-1`) for flux, consistent with the source-standard convention for
   9.2.1.2 flux tables.

## Script reference

- `scripts/e1004_trapped_leo_logic.py` — B-L geometry, AE-8/AE-9-class
  table lookup, orbit averaging.
- `scripts/test_e1004_trapped_leo.py` — unit tests for the geometry,
  interpolation monotonicity/bounds, and SAA-dominance flagging.
