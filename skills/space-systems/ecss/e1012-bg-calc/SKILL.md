---
name: e1012-bg-calc
description: "Use when run radiation background calculations for a spacecraft instrument or detector under ECSS-E-ST-10C §10.4.9: compute the energy-deposition spectrum by applying linear energy transfer to the ambient particle flux in each energy bin, determine the absorbed dose for each particle species, derive nuclear interaction rates from the particle flux, nuclear cross-section, and target areal density, apply Beer-Lambert attenuation to propagate the radiation environment through shielding material, and compare the integrated dose against the mission allowable budget, flagging any exceedance. Trigger: ecss, e-st-10-system-scope, radiation-background, energy-deposition-spectrum, nuclear-interaction-rate, linear-energy-transfer, shielding-attenuation, dose-budget."
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
  tags: [ecss, e-st-10-system-scope, radiation-background, energy-deposition-spectrum, nuclear-interaction-rate, linear-energy-transfer, shielding-attenuation, dose-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Radiation Background Calculations (space-systems/ecss/e1012-bg-calc)

Use when the task is to run radiation background calculations for a spacecraft
instrument or detector per ECSS-E-ST-10C §10.4.9 — constructing the
energy-deposition spectrum, deriving nuclear interaction rates, propagating the
environment through shielding, and checking the result against the dose budget.

## Domain quick reference

- §10.4.9 requires the analyst to characterise the radiation background in a
  detector or sensitive volume by (a) convolving the particle flux spectrum with
  the linear energy transfer (LET) of the detector material to produce an
  energy-deposition spectrum, and (b) computing the nuclear interaction rate
  from the particle fluence, nuclear cross-section, and target areal density.
  Both outputs feed detector-level background noise and SEE margin assessments.
- Linear energy transfer (LET, MeV·cm²/g) quantifies the energy a charged
  particle deposits per unit of areal density traversed. The absorbed dose in a
  slab of thickness t (g/cm²) from a monoenergetic fluence Φ (cm⁻²) is
  dose = LET × Φ (MeV/g), converted to Gy via 1 Gy = 6.241 × 10⁹ MeV/g.
- Nuclear interaction rate (reactions/cm³/s) = flux × σ × n, where σ is the
  per-atom cross-section (cm²) and n = ρ × N_A / A is the atomic number
  density (cm⁻³). Integrating through thickness gives the rate per unit area.
- Shielding attenuation follows Beer-Lambert: the transmitted flux behind a
  shield of thickness d and mean free path λ is Φ_t = Φ_0 × exp(−d/λ).
  Particle species (proton, electron, alpha, heavy ion, neutron, photon) must
  be identified before cross-section or LET values are assigned.

## Workflow

1. Identify every radiation species that contributes to background in the
   detector (proton, electron, alpha particle, heavy ion, neutron, photon).
   Reject any unrecognised species before it enters the calculation; log the
   rejection as a data-quality finding.
2. For each species, retrieve or measure the LET in the detector material at
   the relevant particle energies; if a single representative energy is used,
   document the approximation and its conservatism direction.
3. For each energy bin in the input flux spectrum, compute the bin fluence
   (differential flux × bin width × exposure time), the energy deposited in
   that bin (LET × areal density × bin fluence), and the bin dose. Sum across
   bins to obtain the integrated dose per species.
4. Compute the nuclear interaction rate for each species: look up or estimate
   the nuclear cross-section, compute the atomic number density of the target
   from its mass density and atomic mass, and multiply flux × σ × n. Integrate
   through the material thickness to get the areal interaction rate.
5. Apply shielding attenuation: for each additional intervening mass layer,
   reduce the incident flux by exp(−thickness / mean_free_path) before passing
   it to step 3.
6. Sum the total dose from all species and compare it against the detector's
   allowable dose budget (from the system radiation design margin allocation).
   Flag any exceedance as a non-compliance finding; flag a missing budget as an
   incomplete requirement, not a pass.
7. Compile the spectrum (per-bin dose), the nuclear interaction rates, and the
   budget comparison into the radiation background calculation report.

## Pitfalls

- Applying a single-energy LET to a broad flux spectrum without binning
  overstates or understates the deposited energy depending on the spectrum
  slope; use differential spectra and sum over bins.
- Omitting the nuclear interaction calculation and reporting only the ionising
  dose — §10.4.9 requires both the energy-deposition spectrum and the
  interaction rate; the latter drives displacement damage and secondary-particle
  background.
- Treating a missing dose budget as zero exceedance instead of an open
  requirement: an unset budget means the radiation design margin was never
  allocated, which is itself a finding.
- Stacking shielding layers multiplicatively without verifying that Beer-Lambert
  attenuation applies to the particle type — it is valid for neutral particles
  and photons but is an approximation for charged particles where range straggling
  and secondary production matter; document the approximation when used.

## Behavior contract (gate 3)

The energy-deposition, nuclear-interaction-rate, shielding-attenuation, and
dose-budget logic is exercised by the gate 3 contract test:
scripts/test_e1012_bg_calc.py against scripts/e1012_bg_calc_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1012_bg_calc.py

## Compliance

- ECSS standards are freely downloadable from ESA; cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
