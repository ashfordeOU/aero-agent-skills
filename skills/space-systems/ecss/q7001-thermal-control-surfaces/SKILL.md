---
name: q7001-thermal-control-surfaces
description: "Evaluate how a molecular film and particulate fallout degrade a thermal-control surface and whether the radiator still closes. Use when a radiator, multi-layer-insulation outer layer or thermal coating carries a cleanliness requirement and the thermal budget has to carry the end-of-life solar absorptance rise, the emittance drop, the shifted alpha-over-epsilon ratio, the degraded radiative equilibrium against the sink and the extra radiator area that degradation costs, rather than one beginning-of-life property pair. Trigger: ecss, q-st-70-01c, thermal-control-surface-contamination, radiator-absorptance-degradation, mli-outer-layer-cleanliness, coating-alpha-over-epsilon-shift, particulate-percent-area-coverage, radiator-area-margin-end-of-life, sensitive-thermal-surface-cleanliness."
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
  tags: [ecss, q-st-70-cleanliness-scope, q7001-thermal-control-surfaces, radiator-absorptance-degradation, mli-outer-layer-cleanliness, coating-alpha-over-epsilon-shift, particulate-percent-area-coverage, radiator-area-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Thermal-Control Surfaces (space-systems/ecss/q7001-thermal-control-surfaces)

Use when the task is the sensitive-hardware branch of ECSS-Q-ST-70-01C that
protects thermal-control surfaces — radiators, the outer layer of
multi-layer insulation, and white or second-surface coatings — by turning a
declared molecular deposition and particulate fallout into an end-of-life
absorptance and emittance, and then into a temperature and an area margin.

## Domain quick reference

- A thermal-control surface is chosen for a low solar absorptance next to a
  high infrared emittance. Contamination attacks the two asymmetrically: a
  condensed organic film absorbs strongly in the solar band and barely at
  all in the infrared, so absorptance climbs while emittance hardly moves.
  The ratio, not either property alone, is what the equilibrium follows.
- The two mechanisms are additive but not alike. A molecular film darkens
  the whole surface towards a saturation value, so its effect flattens with
  further deposition. Particulate fallout instead replaces area: a percent
  area coverage swaps that fraction of the clean surface for the optical
  properties of the particles, and grows linearly with coverage.
- The consequence is a temperature, not a property. Solving the radiative
  balance of the degraded surface against its sink and absorbed solar load
  gives the end-of-life temperature; the difference from the clean case is
  the rise the equipment behind the surface has to survive.
- The other consequence is area. Holding the surface at its allowable
  temperature, a degraded surface rejects less per square metre and absorbs
  more sun, so the area needed to carry the same heat load grows. A sunlit
  radiator can reach a point where no finite area closes.
- Beginning-of-life properties are a procurement acceptance value, not a
  design case. Sizing on them is what leaves a radiator with no margin the
  first time the deposition prediction is revised upward.

## Workflow

1. Validate the surface: clean absorptance and emittance, heat load,
   installed area, sink temperature, allowable temperature, incident solar
   flux, predicted deposition and predicted percent area coverage.
2. Degrade the absorptance in two steps — blend the clean value with the
   particle value over the obscured area fraction, then add the saturating
   molecular rise — and cap the result at unity.
3. Degrade the emittance with the same saturating model and a much smaller
   saturation drop. Refuse a model that would drive emittance to zero: that
   is outside the model's validity, not a case to clamp.
4. Solve the radiative equilibrium at beginning of life and at end of life
   using the internal flux implied by the heat load over the installed area,
   and report the rise between them.
5. At the allowable temperature, compute what the degraded surface can still
   reject per square metre net of the absorbed solar load, and turn the heat
   load into a required area. A non-positive net rejection means no finite
   area closes, and is reported as such rather than as a huge number.
6. Compare the end-of-life temperature with the allowable value and the
   required area with the installed area, absorbing representation error at
   either boundary with a named tolerance.

## Pitfalls

- Tracking absorptance only. Emittance moves too, and the alpha-over-epsilon
  ratio is what sets the equilibrium; reporting a darkened surface without
  the ratio understates how much the temperature actually shifts.
- Adding particulate coverage as an absorptance increment. Coverage replaces
  area, so its effect depends on how dark the clean surface already is — the
  same coverage costs an optical solar reflector far more than a black one.
- Sizing the radiator at beginning of life and adding a flat percentage.
  The degradation is not a flat percentage: it saturates with deposition and
  grows linearly with coverage, and on a sunlit radiator it can diverge.
- Clamping a degraded emittance at zero to keep a case running. An emittance
  driven that far is a signal the degradation model has left its validity
  range; the correct response is to refuse the input.
- Treating a sunlit radiator that no longer closes as a large-area problem.
  It is a different problem: the surface absorbs at least what it can reject
  at the allowable temperature, and only a shading, pointing or coating
  change fixes it.

## Behavior contract (gate 3)

The surface validation, obscuration conversion, saturating molecular and
particulate degradation models, emittance validity refusal, radiative
equilibrium solution, net rejection and required-area computation, and the
temperature and area comparisons are exercised by the gate 3 contract test:
scripts/test_q7001_thermal_control_surfaces.py against
scripts/q7001_thermal_control_surfaces_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7001_thermal_control_surfaces.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
