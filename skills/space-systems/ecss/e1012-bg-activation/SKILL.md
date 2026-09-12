---
name: e1012-bg-activation
description: "Use when compute background radiation from induced radioactive activation of spacecraft materials under ECSS-E-ST-10C §10.4.4: identify target isotopes in the material stack, compute saturation activity from particle flux and activation cross-section, derive build-up activity at end-of-irradiation, apply radioactive decay for the post-irradiation cooling interval, convert activity to background count rate or absorbed dose rate using detector solid angle and efficiency, and aggregate contributions across all activation products to obtain the total activation background estimate. Suitable for shielding material surveys, instrument dead-time budgets, and in-flight background predictions after passage through trapped-radiation belts or solar energetic particle events. Trigger: ecss, e-st-10-system-scope, activation background, induced radioactivity, saturation activity, activation cross-section, radioactive decay, detector background, dose rate."
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
  tags: [ecss, e-st-10-system-scope, activation-background, induced-radioactivity, saturation-activity, activation-cross-section, radioactive-decay, detector-background, dose-rate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Radiation — Activation Background (space-systems/ecss/e1012-bg-activation)

Use when the task is to compute the radiation background contribution from
induced radioactive activation, as required by ECSS-E-ST-10C §10.4.4.
This leaf covers the full chain from target irradiation through activity
build-up, radioactive decay, and final background estimate at the detector.

## Domain quick reference

- **Activation** occurs when particles (protons, neutrons, heavier ions)
  strike a structural or shielding material and trigger a nuclear reaction
  that leaves the product nucleus in an unstable state. The product then
  decays, emitting gamma rays, beta particles, or conversion electrons that
  contribute to the instrument background.
- **Saturation activity** A_sat = Φ · σ · N is the asymptotic activity
  reached after irradiation much longer than the product's half-life, where
  Φ [cm⁻² s⁻¹] is the incident particle flux, σ [cm²] is the
  reaction cross-section for the target isotope, and N is the number of
  target atoms.
- **Build-up** during irradiation of duration t_irr follows
  A(t_irr) = A_sat × (1 − exp(−λ · t_irr)), where λ = ln 2 / T½.
  Short irradiations compared to T½ produce far less than saturation.
- **Decay** after irradiation (cooling time t_cool) reduces the end-of-
  irradiation activity as A(t_cool) = A(t_irr) × exp(−λ · t_cool).
- **Background count rate** at the detector is
  CR = A · (Ω / 4π) · ε, where Ω is the detector solid angle and ε is
  detection efficiency. **Dose rate** from a gamma emitter is
  D˙ = A · E_γ · 1.602 × 10⁻¹³ / m_kg [Gy/s], with optional geometry
  factor for attenuation or build-up.
- Multiple activation products in the same material are handled
  independently and their contributions summed.

## Workflow

1. List every material layer that can be activated by the incident particle
   field. For each, identify the dominant target isotope (highest
   reaction-cross-section isotope for the relevant particle type).
   Reject any target with an unrecognized isotope identifier before it
   enters the calculation.
2. For each target isotope, retrieve or estimate: particle flux Φ, reaction
   cross-section σ (from evaluated nuclear data or experiment), and number
   of target atoms N (from material mass and atomic mass via Avogadro's
   number). Raise an error if any of these parameters is non-physical
   (negative flux, zero or negative cross-section or atom count).
3. Compute saturation activity A_sat = Φ · σ · N.
4. Compute end-of-irradiation activity using the build-up formula with
   the known or planned irradiation duration t_irr. If t_irr is zero,
   activity is zero.
5. Apply radioactive decay over the cooling interval t_cool between end of
   irradiation and the measurement epoch. If t_cool equals zero, the
   end-of-irradiation activity is carried forward unchanged.
6. Convert the residual activity for each product to the detector background
   contribution: background count rate via solid angle and efficiency, or
   absorbed dose rate via gamma energy and detector mass.
7. Sum contributions from all activation products. Report the total
   activation background alongside per-product breakdown. Flag any product
   whose individual contribution exceeds 10 % of the total (dominant-source
   indicator) to direct shielding or material-selection trades.

## Pitfalls

- Applying saturation activity directly without accounting for irradiation
  duration: short exposures relative to T½ deliver much less than A_sat;
  using A_sat overstates the background by orders of magnitude for short
  irradiations.
- Ignoring the cooling period: activation background after a radiation-belt
  pass or SEP event continues to decay; failing to propagate the cooling
  time overestimates the background at observation time.
- Treating all activation products as pure gamma emitters: some products
  emit primarily beta particles or conversion electrons that deposit locally
  and do not reach a remote detector; including their energy in a remote-
  detector dose-rate estimate overestimates the background.
- Using an uncorrected cross-section for off-energy particle spectra:
  cross-sections are strongly energy-dependent; using a thermal-neutron
  value for a proton-dominated field produces incorrect saturation activity.
- Omitting short-lived products: a product with T½ much shorter than the
  irradiation duration quickly reaches saturation and can dominate the
  in-flight background even if its cross-section is modest.

## Behavior contract (gate 3)

The activation-background logic — saturation activity, build-up, decay,
count-rate conversion, and multi-product aggregation — is exercised by the
gate 3 contract test: scripts/test_e1012_bg_activation.py against
scripts/e1012_bg_activation_logic.py (stdlib unittest, offline). Run:

    python3 scripts/test_e1012_bg_activation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
