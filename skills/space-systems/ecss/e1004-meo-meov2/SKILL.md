---
name: e1004-meo-meov2
description: "Use when computing MEO trapped-radiation flux spectra and mission fluence for a medium-Earth-orbit spacecraft per ECSS-E-ST-10-04C Annex B.3: interpolate a MEOv2-style spectral model across the crossed L-shell range, apply orbit-averaging across the radiation belts, and produce differential and integral electron and proton fluence inputs for total-dose and charging analyses. Trigger: MEO trapped radiation, MEOv2 model, L-shell crossing, orbit-averaged spectrum, electron fluence, proton fluence, radiation belts, e-st-10-04, ecss."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-10-04c, meo, meov2, trapped-radiation, radiation-belts, orbit-averaged, annex-b3]
  version: 0.1.0
  author: Aero Agent Skills
---

# E-ST-10-04C Annex B.3 — MEO Trapped Environment via MEOv2

## Overview

ECSS-E-ST-10-04C (Space environment) Annex B.3 references MEOv2 as the
recommended model for trapped electron and proton environments in Medium
Earth Orbit. Unlike LEO or GEO, an MEO spacecraft's ground track sweeps
across a wide range of McIlwain L-shells every revolution (crossing the
slot region, the outer electron belt, and the inner proton belt), so a
single-L flux lookup is not representative — the environment must be
built up by spectral interpolation over both L-shell and energy, then
integrated with the dwell time spent at each L-shell per orbit.

This skill computes that orbit-averaged differential flux spectrum and
the resulting mission fluence, and categorizes the result into a
qualitative severity band for first-pass screening.

## When to use

Invoke this skill when a task requires:
- The trapped electron/proton flux spectrum for an orbit whose L-shell
  varies significantly over one revolution (typical MEO, e.g. GPS/Galileo/
  GLONASS-class semi-synchronous orbits).
- An orbit-averaged or mission-integrated fluence figure to feed into
  total-ionizing-dose or displacement-damage calculations.
- A quick, defensible severity categorization of an MEO trapped
  environment before commissioning a full SPENVIS/OMERE run.

Do not use this skill for LEO-only or GEO-only environments (see the
dedicated `e1004-trapped-leo` and `e1004-geo-ige` leaves), nor for solar
particle events (see the `e1004-sep-direction`, `e1004-b6-esp`, and
`e1004-b7-solar-ions` leaves).

## Inputs

- `species`: `"electron"` or `"proton"`.
- A list of `LShellCrossing(l_shell, dwell_seconds)` segments describing
  how long the orbit dwells at each L-shell bin over one revolution.
- `energy_mev`: kinetic energy (or list of energies) of interest.
- `orbit_period_seconds` and `mission_duration_seconds` for fluence
  integration.

## Outputs

- `interpolate_flux(...)`: differential flux [#/cm²/s/MeV] at a single
  (L-shell, energy) point.
- `orbit_averaged_spectrum(...)`: dwell-time-weighted differential flux
  spectrum across an energy grid.
- `integrate_fluence(...)`: mission-integrated fluence [#/cm²/MeV] at a
  given energy.
- `categorize_severity(...)`: qualitative band (`"benign"`, `"elevated"`,
  `"severe"`) for the computed fluence. This is a screening aid only —
  it is never called "classification"; use "categorized" throughout,
  since the output is a category label, not a security classification.

## Usage

```python
from e1004_meo_meov2_logic import (
    LShellCrossing,
    orbit_averaged_spectrum,
    integrate_fluence,
    categorize_severity,
)

crossings = [
    LShellCrossing(l_shell=1.3, dwell_seconds=1800),
    LShellCrossing(l_shell=3.0, dwell_seconds=2400),
    LShellCrossing(l_shell=5.0, dwell_seconds=3600),
    LShellCrossing(l_shell=6.6, dwell_seconds=1200),
]

spectrum = orbit_averaged_spectrum("electron", crossings)
fluence_1mev = integrate_fluence(
    "electron", crossings, energy_mev=1.0,
    orbit_period_seconds=43200, mission_duration_seconds=5 * 365.25 * 86400,
)
band = categorize_severity("electron", fluence_1mev)
```

## Limitations

- The embedded flux tables are illustrative order-of-magnitude figures
  reproducing the well-known double-peaked electron belt structure and
  the inner-belt proton falloff with L. They are **not** digitized
  ONERA MEOv2 coefficients — that dataset is proprietary and distributed
  only through licensed SPENVIS/OMERE tooling. Replace `ELECTRON_LOG_FLUX`
  / `PROTON_LOG_FLUX` with licensed MEOv2 output before using results for
  a compliance verdict.
- Interpolation is linear in L and log-log in energy; it does not model
  local-time, solar-cycle, or magnetic-storm dependence.
- Severity bands are screening thresholds for engineering triage, not an
  ECSS pass/fail criterion.

## References

- ECSS-E-ST-10-04C, Space environment, Annex B.3 (MEO trapped
  environment, MEOv2).
