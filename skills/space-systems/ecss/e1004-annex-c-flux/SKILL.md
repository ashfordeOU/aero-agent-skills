---
name: e1004-annex-c-flux
description: "Use when computing meteoroid background flux and meteor-shower stream enhancement for a space mission per ECSS-E-ST-10-04C Annex C: apply the Grün interplanetary flux model, add meteor-stream enhancement tables for known shower epochs, and apply Earth shielding and gravitational focusing corrections for near-Earth orbits to produce the meteoroid environment input for impact risk assessment. Trigger: meteoroid flux, Grün model, meteor stream, shower enhancement, Earth shielding, gravitational focusing, impact risk, e-st-10-04, ecss."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-10-04c, meteoroid, gruen-model, meteor-stream, shower-enhancement, earth-shielding, gravitational-focusing, annex-c]
  version: 0.1.0
  author: Aero Agent Skills
---

# E1004 Annex C Meteoroid Flux Reference Data

## Overview

ECSS-E-ST-10-04C Annex C provides the meteoroid environment reference data
used to size shielding (Whipple bumpers, MLI, structural walls) and to
estimate impact-risk and penetration probability for spacecraft surfaces.
The environment has two parts that must be categorized and combined
separately:

1. A **sporadic background** flux — the steady, direction-averaged
   interplanetary dust/meteoroid population at 1 AU, described by the
   **Grün et al. (1985)** cumulative flux-vs-mass model. This dominates
   most mission timelines.
2. **Stream enhancements** — short, predictable spikes in flux when a
   spacecraft's orbit crosses a meteor shower's debris trail (e.g.
   Perseids, Leonids). These are categorized by radiant/shower and only
   matter during the shower's active window.

Near a massive body (Earth), two geometric corrections modify the
1 AU flux actually seen by a spacecraft: **shielding** (the planet
occults part of the sky the spacecraft would otherwise see meteoroids
from) and **gravitational focusing** (the planet's gravity bends
trajectories toward it, raising local flux). Both are altitude-dependent
and act in opposite directions, so they must be applied together.

This leaf computes:
1. The 1 AU sporadic background cumulative flux for a given particle
   mass (Grün model).
2. The stream-enhanced flux when a mission timeline includes a known
   shower encounter.
3. The near-Earth-corrected flux at a given orbital altitude (shielding
   × gravitational focusing applied to the 1 AU value).

## When to invoke this skill

- Populating the meteoroid environment input to a shielding/ballistic-limit
  (Whipple-bumper, MLI, wall thickness) analysis.
- Estimating impact probability or penetration risk over a mission
  timeline, including whether a known meteor shower crossing needs to be
  budgeted separately from the background.
- Cross-checking a vendor-supplied environment run (e.g. ESA MASTER,
  NASA MEM) against an independent order-of-magnitude estimate.

Not for orbital debris (a separate, artificial-object environment not
covered by Annex C), and not for trapped-radiation or solar-particle
environments — those are separate leaves in this family
(`e1004-trapped-leo`, `e1004-b6-esp`, `e1004-b7-solar-ions`, etc.).

## Data provenance and fidelity notice

The four-term power-law flux formula in
`scripts/e1004_annex_c_flux_logic.py` (`grun_cumulative_flux`) reproduces
the **shape** of the published Grün (1985) interplanetary flux model —
each term is individually monotonically decreasing in mass, so the sum
is provably monotonically decreasing across the full mass range, matching
the model's defining physical property (bigger particles are rarer).
The coefficients are **representative engineering placeholders**
calibrated to that published shape, not a byte-for-byte transcription of
the standard's Annex C tables. Likewise, `METEOROID_STREAMS` holds
order-of-magnitude peak-enhancement placeholders for major annual
showers, not a transcription of a specific stream-model release. For
mission-grade, traceable analysis, replace the coefficients/table with
vetted output from ESA MASTER, NASA MEM, or the specific Annex C edition
in force, keeping the same function interface
(`grun_cumulative_flux`, `stream_enhancement_factor`). The monotonicity,
shielding/focusing geometry, and combination logic are model-independent
and do not need to change when the data is swapped.

## Steps

1. **Get the background flux.** `grun_cumulative_flux(mass_g)` returns
   the 1 AU cumulative flux (`m^-2 s^-1`, particles of mass ≥ `mass_g`
   grams), valid for `1e-18 g <= mass_g <= 1e2 g`.
   `grun_differential_flux(mass_g)` gives `-dF/dm` at a mass point via
   central-difference numerical differentiation, for spectral-shape
   comparisons.
2. **Apply a stream enhancement, if relevant.** Check whether the
   mission timeline overlaps a known shower window in
   `METEOROID_STREAMS`; `total_cumulative_flux(mass_g, stream_name)`
   multiplies the background by that shower's peak enhancement factor.
   Omit `stream_name` to get the background alone.
3. **Apply near-Earth geometric corrections.** `earth_shielding_factor(altitude_km)`
   and `gravitational_focusing_factor(altitude_km)` return the two
   altitude-dependent correction factors; `near_earth_flux(mass_g,
   altitude_km, stream_name)` applies both to the (optionally
   stream-enhanced) background in one call.
4. **Report.** Output units are `m^-2 s^-1` cumulative flux (particles
   of mass ≥ the queried mass), consistent with the source-standard
   convention for Annex C flux data.

## Script reference

- `scripts/e1004_annex_c_flux_logic.py` — Grün background flux model,
  stream enhancement lookup, Earth shielding/gravitational-focusing
  corrections.
- `scripts/test_e1004_annex_c_flux.py` — unit tests for monotonicity,
  input-range validation, stream lookup, and shielding/focusing bounds.
