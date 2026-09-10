---
name: e1004-geo-ige
description: "Use when computing GEO trapped energetic-electron flux and mission fluence for a geostationary spacecraft per ECSS-E-ST-10-04C Annex B.2: interpolate an IGE-2006-style local-time and energy spectral model at fixed L ~= 6.6, apply local-time sector weighting, and produce the differential and integral electron fluence inputs for internal charging and dose analysis. Trigger: GEO trapped electrons, IGE-2006, geostationary, L-shell 6.6, local-time spectrum, electron fluence, internal charging, e-st-10-04, ecss."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-10-04c, geo, ige-2006, trapped-electrons, geostationary, l-shell-6.6, annex-b2]
  version: 0.1.0
  author: Aero Agent Skills
---

# E-ST-10-04C Annex B.2 — GEO Trapped Environment via IGE-2006

## Overview

ECSS-E-ST-10-04C (Space environment) Annex B.2 references IGE-2006 as the
recommended model for the trapped energetic-electron environment at
Geostationary Earth Orbit (GEO). Unlike LEO or MEO, a GEO spacecraft's
McIlwain L-shell is essentially fixed near **L ~= 6.6** — it does not
sweep across L-shells the way a LEO or MEO ground track does — so a
single-L lookup is representative for the whole mission. What instead
varies strongly is the spacecraft's **magnetic local time (MLT)**:
substorm-injected electrons peak in the post-midnight/dawn sector and
are suppressed on the magnetopause-compressed dayside, and a
geostationary satellite sits at a nearly constant local time over a
single day (drifting only slowly, e.g. across longitude relocations or
the sidereal/solar-day precession over a year), so its fixed park
position determines the environment it actually sees.

This skill computes the local-time/energy differential flux spectrum
at fixed GEO L-shell, scales it by a storm-time statistical percentile
(mean through worst-case p99), integrates dwell-weighted mission
fluence across one or more local-time park segments, and categorizes
the local-time sector and the resulting fluence severity for
first-pass screening.

## When to use

Invoke this skill when a task requires:
- The trapped energetic-electron flux spectrum for a spacecraft parked
  at (or relocated between) GEO local-time position(s), where L is
  fixed near 6.6 and local-time dependence dominates the environment.
- An orbit-averaged or mission-integrated electron fluence figure to
  feed into total-ionizing-dose, deep-dielectric-charging, or surface-
  charging design margin calculations.
- A quick, defensible severity categorization of a GEO trapped
  electron environment before commissioning a full SPENVIS/OMERE run.
- A worst-case (percentile-based) bounding spectrum for a GEO mission
  rather than a single mean-flux estimate.

Do not use this skill for LEO or MEO trapped environments, where the
L-shell itself varies significantly over an orbit (see the dedicated
`e1004-trapped-leo` and `e1004-meo-meov2` leaves), nor for trapped
protons at any orbit (see `e1004-trapped-proton-wc`), nor for solar
particle events (see the `e1004-sep-direction`, `e1004-b6-esp`, and
`e1004-b7-solar-ions` leaves).

## Inputs

- `l_shell`: the orbit's McIlwain L-shell, validated against the fixed
  GEO value (`validate_geo_l_shell`) before applying this model.
- A list of `LocalTimeDwell(local_time_hours, dwell_seconds)` segments
  describing how long the mission dwells at each local-time park
  position (a single segment for a satellite that never relocates).
- `energy_mev`: kinetic energy (or list of energies) of interest.
- `percentile`: `"mean"`, `"p90"`, `"p95"`, or `"p99"` — the storm-time
  statistical bound the analysis needs.

## Outputs

- `validate_geo_l_shell(...)`: raises if the supplied L-shell is not
  consistent with GEO — a guard against misapplying this leaf's
  local-time model to an orbit that actually sweeps across L-shells.
- `classify_local_time_sector(...)`: categorizes a local time into
  `"midnight"`, `"dawn"`, `"noon"`, or `"dusk"` for reporting; this is
  a category label for engineering triage, not a security
  classification.
- `interpolate_flux(...)`: differential flux [#/cm²/s/MeV] at a single
  (local time, energy, percentile) point.
- `local_time_averaged_spectrum(...)`: dwell-time-weighted differential
  flux spectrum across an energy grid.
- `integrate_fluence(...)`: mission-integrated fluence [#/cm²/MeV] at a
  given energy, summed across local-time dwell segments.
- `categorize_severity(...)`: qualitative band (`"benign"`, `"elevated"`,
  `"severe"`) for the computed fluence. Screening aid only.

## Usage

```python
from e1004_geo_ige_logic import (
    LocalTimeDwell,
    validate_geo_l_shell,
    classify_local_time_sector,
    local_time_averaged_spectrum,
    integrate_fluence,
    categorize_severity,
)

validate_geo_l_shell(6.6)  # raises if the orbit isn't actually GEO

dwells = [
    LocalTimeDwell(local_time_hours=3.5, dwell_seconds=15 * 365.25 * 86400),
]

sector = classify_local_time_sector(3.5)  # "dawn"
spectrum = local_time_averaged_spectrum(dwells, percentile="p95")
fluence_1mev = integrate_fluence(dwells, energy_mev=1.0, percentile="p95")
band = categorize_severity(fluence_1mev)
```

## Limitations

- The embedded flux tables are illustrative order-of-magnitude figures
  reproducing the well-known IGE-2006 qualitative pattern (post-
  midnight/dawn peak, dayside minimum). They are **not** digitized
  ONERA IGE-2006 coefficients — that dataset is proprietary and
  distributed only through licensed SPENVIS/OMERE tooling. Replace
  `ELECTRON_LOG_FLUX` with licensed IGE-2006 output before using
  results for a compliance verdict.
- Percentile scale factors are illustrative multipliers approximating
  storm-time statistical skew, not digitized IGE-2006 percentile
  coefficients.
- Interpolation is circular-linear in local time and log-log in
  energy; it does not model solar-cycle or individual-storm dynamics.
- Severity bands are screening thresholds for engineering triage, not
  an ECSS pass/fail criterion.

## References

- ECSS-E-ST-10-04C, Space environment, Annex B.2 (GEO trapped
  environment, IGE-2006).
