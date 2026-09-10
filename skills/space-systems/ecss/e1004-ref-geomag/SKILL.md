---
name: e1004-ref-geomag
description: "Use when selecting the geomagnetic field model reference data for a mission per ECSS-E-ST-10-04C Annex E: determine whether the internal field alone (IGRF) is sufficient for a given orbit altitude or an external/magnetospheric model must be added, validate an IGRF coefficient generation epoch as definitive, predictive, or stale, select the required spherical-harmonic degree/order truncation for the altitude, choose an external field model tier from the geomagnetic activity (Kp) index, and check a position against the solar-wind-pressure-dependent magnetopause standoff distance. Produces a structured field-model-source determination with explicit error paths for out-of-range inputs. Trigger: ecss, e-st-10-04c, geomagnetic field, igrf, external field model, magnetospheric model, magnetopause, kp index, space environment reference data."
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
  tags: [ecss, e-st-10-04c, geomagnetic-field, igrf, external-field-model, magnetopause, space-environment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Geomagnetic Field Model Reference Data (space-systems/ecss/e1004-ref-geomag)

Use when the task is selecting geomagnetic field model reference data
under ECSS-E-ST-10-04C Annex E (informative) -- deciding whether the
Earth's internal field model alone describes the environment at a
given orbit altitude, or whether an external/magnetospheric model must
be added, validating the age of the internal-field coefficient set,
sizing the spherical-harmonic truncation to the altitude, picking an
external-field model tier from geomagnetic activity, and checking a
position against the magnetopause.

## Domain quick reference

- The internal field (source: electric currents in Earth's core,
  described by the IGRF coefficient set) dominates close to Earth. At
  larger radial distance, external sources (magnetospheric ring
  current, magnetopause current, tail current) become a comparable or
  larger contributor, so a mission's field-model regime is
  altitude-dependent: internal-only near Earth, internal-plus-external
  further out, and beyond the nominal magnetopause standoff distance
  the position must be checked against the magnetopause before an
  internal/external Earth-field model is applied at all.
- The IGRF coefficient set is released in 5-year generations tied to a
  generation epoch. Each generation's coefficients are definitive for
  its own 5-year interval and are extended by predicted secular-
  variation coefficients for one further 5-year interval; beyond that
  second interval the generation is stale and a newer generation
  should be selected.
- Higher spherical-harmonic degree/order terms of the internal field
  decay rapidly with radial distance, so the degree/order needed for
  an accurate field value falls as altitude increases: a low-altitude
  mission needs the full-degree coefficient set, while a
  geostationary-altitude or higher mission can use a low-degree
  truncation without a meaningful accuracy loss.
- External/magnetospheric model selection is driven by geomagnetic
  activity level (commonly indexed by Kp): quiet conditions are
  adequately described by a static average external model, while
  increasing activity requires models that take solar-wind and
  interplanetary-magnetic-field inputs, up to the storm-time tier that
  also needs a ring-current activity index.
- The magnetopause standoff distance (subsolar boundary between the
  magnetosphere and the solar wind) compresses under higher solar-wind
  dynamic pressure and expands under lower pressure; a position at or
  beyond the standoff distance is outside (or at the boundary of) the
  magnetosphere, where the Earth-field models above no longer apply.

## Workflow

1. Convert the mission altitude to radial distance from Earth's
   center and classify the field-model regime: internal-only,
   internal-plus-external, or beyond-the-nominal-magnetopause-limit.
   Reject a negative altitude before classifying.
2. Size the internal-field spherical-harmonic degree/order truncation
   to the altitude -- do not carry the full-degree coefficient set
   into a high-altitude computation where the extra terms are
   negligible, and do not truncate a low-altitude computation where
   the higher-degree terms are significant.
3. Validate the internal-field coefficient generation epoch against
   the evaluation date: definitive (within the generation's own
   5-year interval), predictive (within the following 5-year secular-
   variation interval), or stale (beyond both) -- flag a stale
   generation for update before use.
4. If the regime requires an external/magnetospheric model, select the
   model tier from the geomagnetic activity index and record the
   additional inputs (solar-wind dynamic pressure, interplanetary
   magnetic field components, ring-current index) that tier requires.
5. If the regime is beyond the nominal magnetopause limit, require the
   solar-wind dynamic pressure, compute the standoff distance, and
   classify the position as inside the magnetopause or at/beyond it
   before assuming an Earth-field model applies.
6. Aggregate the regime, degree/order, external-model selection, and
   magnetopause position (when evaluated) into one field-model-source
   determination for the mission.

## Pitfalls

- Applying the full-degree internal-field coefficient set at every
  altitude "to be safe" -- the higher-degree terms are not just
  wasted computation at high altitude, carrying them without also
  carrying their (larger, less certain) coefficient uncertainty
  overstates the model's precision.
- Treating an internal-only regime as complete at higher altitude --
  once the external-field contribution is comparable to the internal
  field, omitting it is a model-completeness gap, not a conservative
  simplification.
- Using a stale IGRF generation without flagging it -- a coefficient
  set beyond its predictive secular-variation window is a documented
  finding requiring an updated generation, not a silent degradation.
- Selecting a quiet-conditions external model tier regardless of
  actual geomagnetic activity -- a storm-time environment needs the
  ring-current-index-dependent tier; using the static quiet-tier model
  understates the external field during activity.
- Assuming a position is inside the magnetosphere without checking the
  magnetopause standoff distance against the actual solar-wind
  pressure -- the standoff distance moves with pressure, so a fixed
  assumed boundary can be wrong in either direction.

## Behavior contract (gate 3)

The regime-classification, degree/order sizing, epoch-validation,
external-model-selection, and magnetopause-position logic is exercised
by the gate 3 contract test: scripts/test_e1004_ref_geomag.py against
scripts/e1004_ref_geomag_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_ref_geomag.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
