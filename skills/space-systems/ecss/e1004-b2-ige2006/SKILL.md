---
name: e1004-b2-ige2006
description: "Use when implementing the IGE-2006 geostationary trapped-electron flux model under ECSS-E-ST-10-04C Annex B.2: look up the differential electron flux at a requested energy and L-shell by log-linear interpolation between the model's tabulated energy and L-shell nodes, resolve the requested confidence level (mean or a worst-case percentile) to its flux scale factor, assemble a full energy-spectrum table for a request, and flag any energy or L-shell query that falls outside the tabulated node range as an extrapolation rather than silently returning a boundary value. Trigger: IGE-2006, geostationary electron model, GEO electron flux, trapped electron spectrum, L-shell interpolation, confidence level, worst-case percentile, Annex B.2, e-st-10-04, ecss, space environment."
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
  tags: [ecss, e-st-10-04c, annex-b2, ige-2006, geostationary, trapped-electrons, l-shell, energy-spectrum, radiation-environment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS IGE-2006 GEO Electron Flux Model (space-systems/ecss/e1004-b2-ige2006)

Use when the task is implementing the internal mechanics of the
IGE-2006 geostationary trapped-electron flux model under
ECSS-E-ST-10-04C Annex B.2: the model's energy-spectrum table,
L-shell handling, and confidence-level (worst-case percentile)
scaling that the sibling e1004-geo-ige leaf (clause 9.2.1.2.1) calls
when it decides to compute a mission's long-term GEO electron flux.

## Domain quick reference

- IGE-2006 (International Geostationary Electron model, 2006) is the
  ECSS reference model for the long-term-average and worst-case
  trapped energetic-electron environment near geostationary orbit
  (GEO) and nearby geosynchronous orbits (drift orbits, inclined
  near-GEO orbits, extended dwell in transfer orbit).
- The model characterizes electron differential flux as a function of
  two independent inputs: electron energy (spanning tens of keV to a
  few MeV) and L-shell (a band centered on the nominal GEO L-shell,
  not a single fixed value), so it covers orbits that sit near but not
  exactly at equatorial GEO.
- The model also reports flux at multiple confidence levels: a
  long-term mean spectrum plus one or more worst-case percentile
  spectra, so a mission can pick the design margin appropriate to its
  duration and risk posture. Deciding which confidence level a mission
  needs, and whether IGE-2006 is the right model to invoke at all, is
  the sibling e1004-geo-ige leaf's job (§9.2.1.2.1); this leaf
  implements the model's internal spectral/tabular mechanics that
  leaf calls into.
- Because the model is defined on a discrete grid of energy and
  L-shell nodes, evaluating it away from a tabulated node requires
  interpolation: log-linear in flux over energy (the spectrum spans
  many decades of flux), linear in the L-shell scale factor (a much
  smaller dynamic range). A request outside the tabulated node range
  is an extrapolation, not a validated model output, and must be
  flagged rather than silently clamped to the nearest boundary value.

## Workflow

1. For each electron-flux table request, record its id, the list of
   requested electron energies (MeV), the requested L-shell, and the
   requested confidence level (mean or a named worst-case percentile).
2. For each requested energy, look up the differential flux by
   log-linear interpolation between the model's tabulated energy
   nodes; if the requested energy falls outside the tabulated node
   range, flag that energy as an extrapolation instead of returning
   the nearest boundary value.
3. Look up the model's L-shell scale factor by linear interpolation
   between the model's tabulated L-shell nodes -- this captures that
   the trapped-electron population is centered on the geostationary
   L-shell and falls off toward the ends of the tabulated band; flag
   a requested L-shell outside the tabulated node range as an
   extrapolation.
4. Resolve the requested confidence level to its flux scale factor:
   the mean spectrum has a scale factor of 1.0, and each worst-case
   percentile scales the mean flux upward, more so for a higher
   percentile.
5. Combine the energy, L-shell, and confidence-level factors into the
   differential flux at each requested energy, and assemble the full
   requested-energy list into the spectrum table for the request.
6. Mark a request compliant only when none of its energy or L-shell
   lookups needed extrapolation; roll every request's compliance into
   the assessment record and do not accept a request's spectrum table
   into the radiation environment specification while it remains
   flagged as extrapolated without a documented engineering waiver.

## Pitfalls

- Evaluating the model only at the nominal GEO L-shell when the
  mission's actual orbit (drift orbit, inclined near-GEO orbit,
  extended transfer-orbit dwell) spans a range of L-shells that the
  tabulated grid exists to cover.
- Silently returning the nearest tabulated boundary value for an
  out-of-range energy or L-shell query instead of flagging it as an
  extrapolation needing engineering judgment before it feeds the
  radiation environment specification.
- Selecting the mean (long-term-average) spectrum for a long-duration
  or risk-averse mission that actually needs a worst-case percentile
  spectrum for adequate design margin.
- Confusing this leaf's model-internal table, spectrum, and L-shell
  mechanics with the sibling e1004-geo-ige leaf's separate job of
  deciding when and how to invoke the model for a mission's GEO flux
  specification.

## Behavior contract (gate 3)

The energy-spectrum interpolation, L-shell scale-factor interpolation,
confidence-level scaling, spectrum-table assembly, and
extrapolation/compliance logic are exercised by the gate 3 contract
test: scripts/test_e1004_b2_ige2006.py against
scripts/e1004_b2_ige2006_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_b2_ige2006.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
