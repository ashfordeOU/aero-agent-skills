---
name: e1004-b3-meov2
description: "Use when implementing the ONERA MEOv2 trapped-electron flux model for GNSS/navigation-orbit (MEO) radiation analyses under ECSS-E-ST-10-04C Annex B.3: represent the model's flux-versus-energy spectral form as a function of McIlwain L-shell, interpolate the model's L-shell reference grid to an arbitrary L-shell (including along a full mission orbit's L-shell trace), and compute per-energy, orbit-averaged, and worst-case-L-shell flux outputs for the orbit. Trigger: MEOv2, ONERA, GNSS orbit radiation, MEO electron flux, McIlwain L-shell, spectral flux model, orbit interpolation, e-st-10-04c annex b.3, ecss, space environment, trapped radiation."
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
  tags: [ecss, e-st-10-04c, meov2, onera, meo, gnss, trapped-electron, l-shell, spectral-model, orbit-interpolation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS ONERA MEOv2 Flux Model (space-systems/ecss/e1004-b3-meov2)

Use when the task is implementing the internal spectral-form and
L-shell-interpolation logic of the ONERA MEOv2 trapped-electron model
under ECSS-E-ST-10-04C Annex B.3, for medium-Earth-orbit
(GNSS/navigation-orbit-class) radiation analyses.

## Domain quick reference

- MEOv2 is an ONERA trapped-electron model built specifically for the
  medium-Earth-orbit (MEO) region occupied by GNSS constellations
  (e.g. GPS-, GLONASS-, Galileo-, BeiDou-class orbits), a region the
  older long-term-average belt models (AE-family) and the GEO-specific
  IGE-2006 model do not cover well.
- The model expresses differential electron flux as a function of
  particle energy and McIlwain L-shell: at a fixed L-shell the flux
  falls off with increasing energy following a smooth spectral form
  (an exponential roll-off characterized by a reference flux level and
  a characteristic e-folding energy), and both the reference flux
  level and the e-folding energy vary with L-shell.
- Because the underlying model data is only defined at a discrete grid
  of L-shell reference points, applying MEOv2 to an actual mission
  orbit requires interpolating the grid's spectral parameters to the
  L-shell values the orbit actually passes through, rather than
  reading off the nearest grid point.
- An eccentric or inclined MEO/GNSS-class orbit typically transits a
  range of L-shell values over one revolution, not a single value, so
  a representative orbit result needs the flux evaluated along an
  L-shell trace and then combined (e.g. dwell-time-weighted average,
  and separately the peak/worst-case L-shell) rather than evaluated at
  one point alone.
- This leaf implements the model-internal spectral form and L-shell
  interpolation only. Deriving the L-shell trace of a given orbit from
  its ephemeris is the sibling e1004-geomag leaf (§5.2); selecting
  MEOv2 for a GNSS-orbit analysis and consuming its output in the
  broader trapped-radiation workflow is the sibling e1004-meo-meov2
  leaf (§9.2.1.2.2 + Annex B.3); rolling the result into the mission
  radiation environment specification is the sibling e1004-rad-env-spec
  leaf (§9.3).
- The reference L-shell grid and spectral parameters used here are
  illustrative placeholders that exercise the model's interpolation
  and spectral-evaluation procedure; they are not a reproduction of
  the ECSS Annex B.3 data tables, which must be sourced from the
  standard itself when performing a real analysis.

## Workflow

1. Obtain the mission orbit's McIlwain L-shell trace as a list of
   L-shell samples (and, optionally, the dwell-time fraction the orbit
   spends at each sample); this leaf takes the trace as an input and
   does not compute it from orbital position.
2. Validate every L-shell sample against MEOv2's valid range; flag a
   sample outside the range rather than silently extrapolating the
   model beyond its defined domain.
3. For each valid L-shell sample, interpolate the model's L-shell
   reference grid to obtain the local spectral parameters (reference
   differential flux and characteristic e-folding energy) using linear
   interpolation between the two bracketing grid nodes.
4. Evaluate the model's spectral form at each energy of interest using
   the interpolated parameters, producing the differential flux, and
   the integral flux above a threshold energy when that is what the
   analysis needs.
5. Combine the per-sample results into orbit-level outputs at each
   energy of interest: the dwell-time-weighted orbit-average flux
   (equal weighting when no dwell fractions are supplied) and the
   worst-case (peak-flux) L-shell sample.
6. Mark a case invalid, rather than reporting an extrapolated result,
   when any of its L-shell samples fall outside the model's valid
   range; roll every case into the assessment record and do not close
   the radiation environment specification while any case remains
   invalid.

## Pitfalls

- Extrapolating MEOv2 outside its valid L-shell range (e.g. applying
  it to LEO or GEO L-shells) instead of switching to the correct
  sibling model (the trapped-LEO belt models or IGE-2006).
- Evaluating the model at a single L-shell point (e.g. only at orbit
  perigee or apogee) instead of across the orbit's full L-shell trace,
  which misses the flux accumulated while transiting the rest of the
  orbit's L-shell range.
- Treating the orbit-average flux as automatically the worst case: a
  peak-dose-rate or margin analysis may need the worst-case L-shell's
  flux instead of the average, and this leaf reports both rather than
  picking one for the caller.
- Confusing this leaf's model-internal spectral-form and
  L-shell-interpolation logic with the higher-level GNSS-orbit
  application workflow in the sibling e1004-meo-meov2 leaf, which is
  responsible for model selection and for consuming this leaf's
  output.

## Behavior contract (gate 3)

The L-shell validation, grid interpolation, spectral-form evaluation,
and orbit-combination logic is exercised by the gate 3 contract test:
scripts/test_e1004_b3_meov2.py against scripts/e1004_b3_meov2_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1004_b3_meov2.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
