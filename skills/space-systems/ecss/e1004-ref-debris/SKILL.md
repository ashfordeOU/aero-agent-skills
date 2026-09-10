---
name: e1004-ref-debris
description: "Use when selecting a meteoroid or orbital-debris flux model for a
  spacecraft environment analysis per ECSS-E-ST-10-04C Annex J: determine
  whether a candidate model (natural meteoroid or catalogued orbital debris)
  is applicable to a case's altitude, epoch, and particle-diameter range,
  compute the model's stated uncertainty band around a nominal flux value,
  and validate a reported flux/model pairing against the model's
  applicability envelope so an out-of-envelope claim is flagged rather than
  accepted at face value. Trigger: ecss, e-st-10-04c, meteoroid flux, orbital
  debris flux, flux model applicability, model uncertainty factor, ORDEM,
  MASTER, Annex J."
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
  tags: [ecss, e-st-10-04c, debris, meteoroid, flux-model, uncertainty, annex-j, orbital-debris]
  version: 0.1.0
  author: Aero Agent Skills
---

# E1004 Annex J Debris/Meteoroid Flux Model Reference Data

## Overview

ECSS-E-ST-10-04C Annex J is an informative annex on the meteoroid and
orbital-debris flux models a mission environment analysis draws on: it
does not mandate a single model, it flags that every published model
(natural meteoroid or catalogued orbital debris) carries an
applicability envelope (altitude range, epoch range, particle-diameter
range) and a stated uncertainty band, and that an analysis is only
traceable if it names the model used and stays inside that envelope.
This is a reference-data leaf: it does not compute an impact risk, it
categorizes candidate flux models against a case's parameters and
supplies the lookup, applicability, and uncertainty-bounding logic a
mission engineer runs before trusting a model's output.

Two model families must be categorized and handled separately:

1. **Meteoroid models** (e.g. a Grün-class interplanetary flux model)
   — natural particles, effectively time-invariant over a mission
   lifetime, applicable across a wide altitude range because the
   population is not orbit-bound.
2. **Orbital-debris models** (e.g. ORDEM-class or MASTER-class
   engineering models) — anthropogenic catalogued and sub-catalogued
   objects, whose flux depends on altitude band and drifts with epoch
   as the debris population grows and decays, so a debris model is only
   valid for the altitude band and epoch window it was built for.

This leaf implements:
1. A reference table of illustrative flux models with their family,
   applicability envelope (altitude, epoch, particle diameter), and
   uncertainty factor.
2. `applicability_gaps` / `is_model_applicable` — check a case's
   parameters against one model's envelope and report which dimensions
   (if any) fall outside it.
3. `applicable_models` / `recommend_model` — list every model whose
   envelope covers a case, and pick the tightest (lowest-uncertainty)
   one among them.
4. `uncertainty_bounds` / `cross_check_reported_flux` — compute the
   low/high bound around a nominal or reported flux value using the
   model's uncertainty factor, and flag a reported flux that cites a
   model outside its own applicability envelope.

## When to invoke this skill

- Choosing which meteoroid or orbital-debris model to run (or cite) for
  a shielding, penetration-risk, or micrometeoroid-and-orbital-debris
  (MMOD) budget analysis at a given orbit and epoch.
- Reviewing a vendor- or tool-supplied flux number and checking whether
  the model it claims to come from actually covers the case's altitude,
  epoch, and particle-size range before the number is used downstream.
- Propagating a flux-model uncertainty band into a risk or probability-
  of-no-penetration calculation instead of treating a model's nominal
  output as exact.

Not for the MMOD penetration/risk calculation itself, hypervelocity-
impact damage equations, or the trapped-radiation environment
(`e1004-trapped-leo` and siblings) — this leaf only selects and bounds
the input flux model.

## Data provenance and fidelity notice

The model registry in `scripts/e1004_ref_debris_logic.py`
(`grun_interplanetary`, `ordem`, `master`) is an **illustrative
reference set** built from widely published, generic descriptions of
the class of meteoroid and orbital-debris engineering models used in
astrodynamics practice (a Grün-class interplanetary meteoroid model,
NASA's ORDEM-class LEO debris engineering model, ESA's MASTER-class
LEO-through-GEO debris model) — it is not a transcription of the
standard's Annex J tables, and the envelope bounds and uncertainty
factors are representative order-of-magnitude values, not the current
released version's exact figures. For mission-grade, traceable
analysis, replace the registry entries with the specific model
version, applicability envelope, and uncertainty figures published by
the model's current release notes, keeping the same function interface
(`applicability_gaps`, `uncertainty_bounds`, `recommend_model`). The
applicability and uncertainty-bounding logic is model-registry-
independent and does not need to change when the entries are updated.

## Steps

1. **Categorize the object family.** `classify_object_family(object_family)`
   accepts `"meteoroid"` or `"debris"`; raises `ValueError` for any
   other value.
2. **Check one model's applicability.** `applicability_gaps(model_name,
   object_family, altitude_km, epoch_year, diameter_m)` returns a dict
   of the dimensions (`family`, `altitude_km`, `epoch_year`,
   `diameter_m`) that fall outside that model's envelope for the case
   (empty dict means fully applicable). `is_model_applicable(gaps)`
   reduces that to a boolean. Raises `ValueError` for an unknown
   `model_name`.
3. **List every applicable model.** `applicable_models(object_family,
   altitude_km, epoch_year, diameter_m)` returns the sorted names of
   every registered model with no gaps for the case; raises
   `ValueError` for an unrecognized `object_family`.
4. **Recommend a model.** `recommend_model(object_family, altitude_km,
   epoch_year, diameter_m)` returns the applicable model with the
   lowest uncertainty factor; raises `ValueError` when no registered
   model covers the case (the case needs a model outside this
   registry, not a silent default).
5. **Bound a flux value.** `uncertainty_bounds(model_name, nominal_flux)`
   returns `(low, high)` using the model's uncertainty factor
   (`nominal_flux / factor`, `nominal_flux * factor`); raises
   `ValueError` for a negative flux or an unknown model.
6. **Cross-check a reported flux/model pairing.**
   `cross_check_reported_flux(model_name, object_family, altitude_km,
   epoch_year, diameter_m, reported_flux)` returns
   `{"issue": "reported_flux_outside_model_envelope", "model": ...,
   "gaps": {...}}` when the pairing is out of envelope, or `{"issue":
   None, "model": ..., "uncertainty_low": ..., "uncertainty_high": ...}`
   when it is applicable. Do not accept a reported flux number until
   `issue` is `None`.

## Pitfalls

- Using a debris model's flux number outside its epoch window (the
  catalogued population changes over time) and treating it as still
  current -- `applicability_gaps` flags an out-of-range `epoch_year`
  for exactly this reason.
- Applying a LEO-scoped debris model's flux at GEO, or vice versa, just
  because it was the model on hand -- check `altitude_km` applicability
  before reuse; a model with no envelope coverage for a case is not the
  best available answer, it is inapplicable.
- Reporting a model's nominal flux as a single number in a risk
  calculation without carrying its uncertainty band -- every registered
  model has a nontrivial `uncertainty_factor`; downstream margin
  calculations must use `uncertainty_bounds`, not just the nominal
  value.
- Picking the first applicable model found instead of the tightest one
  -- `recommend_model` selects the lowest-uncertainty applicable model;
  a wider-envelope, higher-uncertainty model should only be used when
  no tighter model covers the case.

## Behavior contract (gate 3)

The model-applicability, model-selection, and uncertainty-bounding
logic is exercised by the gate 3 contract test:
scripts/test_e1004_ref_debris.py against
scripts/e1004_ref_debris_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_ref_debris.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
