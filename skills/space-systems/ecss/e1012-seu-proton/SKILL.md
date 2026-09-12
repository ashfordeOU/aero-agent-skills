---
name: e1012-seu-proton
description: "Use when predict proton- and neutron-induced single-event upset (SEU) and multiple-cell upset (MCU) rates for space electronic devices under ECSS-E-ST-10C §9.4.1.3: identify the direct-ionization and nuclear-reaction transport paths, apply the Weibull cross-section model over the trapped-proton and free-proton/neutron flux spectra for each path, sum the path contributions to derive the total SEU rate, compute expected upsets over mission duration, compute MCU rate from the MCU fraction, and compare predicted rates against the device SEU budget. Trigger: ecss, e-st-10-system-scope, seu, mcu, proton-induced-seu, neutron-induced-seu, single-event-upset, weibull-cross-section, nuclear-reaction, radiation-hardness."
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
  tags: [ecss, e-st-10-system-scope, seu, mcu, proton-induced-seu, neutron-induced-seu, single-event-upset, weibull-cross-section, nuclear-reaction, radiation-hardness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Proton/Neutron SEU and MCU Rate Prediction (space-systems/ecss/e1012-seu-proton)

Use when the task is to predict proton- and neutron-induced single-event upset
(SEU) and multiple-cell upset (MCU) rates for a space electronic device, covering
both the direct-ionization path and the nuclear-reaction (spallation) path, per
ECSS-E-ST-10C §9.4.1.3.

## Domain quick reference

- **Direct-ionization path**: protons with sufficient energy deposit charge
  directly along their track through the sensitive volume of a memory cell.
  The threshold energy for direct proton ionization is typically in the range
  of tens of MeV; below the threshold the cell sees no direct-ionization upset.
  Neutrons carry no charge and do not contribute to this path.
- **Nuclear-reaction path**: both protons and neutrons undergo spallation
  reactions with silicon nuclei, producing short-range heavy secondary ions
  (protons, alpha particles, recoiling silicon atoms). These secondaries have
  high linear energy transfer and readily upset memory cells. This path
  operates at lower primary-particle energies than direct ionization and
  dominates the neutron SEU mechanism entirely.
- **Weibull cross-section model**: the device-level SEU cross-section σ(E)
  is parameterized by four values: saturation cross-section σ_sat (cm²/bit),
  threshold energy E_th (MeV), width W (MeV), and shape exponent s. The
  model returns zero below E_th and rises smoothly toward σ_sat above it.
  Separate Weibull parameter sets may be used for the direct and nuclear paths.
- **SEU rate**: numerically integrated as Σ σ(E_i) × Φ_i × ΔE_i over the
  differential flux spectrum, scaled by a path efficiency factor (1.0 for the
  direct path; typically ~0.87 for the nuclear-reaction path to account for the
  geometric and energy-dependent reaction probability).
- **MCU**: a single particle event that upsets more than one bit. The MCU rate
  is derived from the total SEU rate multiplied by the device's MCU fraction,
  which must be measured or conservatively estimated from device characterization.
- **Mission SEU count**: rate × bit-count × mission-duration gives the total
  expected upsets over the spacecraft's operational life.

## Workflow

1. Obtain the differential proton and neutron flux spectra for the orbit:
   trapped-proton flux (AP-8/AP-9 or similar) for the direct-ionization path,
   and both proton and neutron spectra for the nuclear-reaction path. Verify
   that the spectra cover the device's relevant energy range up to saturation.
2. Retrieve the device Weibull SEU parameters (σ_sat, E_th, W, s) for the
   direct-ionization path and, separately, for the nuclear-reaction path.
   If only a combined cross-section dataset is available, document the assumption
   and apply it to both paths with a path efficiency factor.
3. For the direct-ionization path, integrate σ_direct(E) over the proton flux
   spectrum using the rectangle method (or higher-order quadrature), multiplied
   by the direct-path efficiency (1.0).
4. For the nuclear-reaction path, integrate σ_nuclear(E) over the proton and
   neutron flux spectra separately and sum the contributions, multiplied by the
   nuclear-reaction path efficiency factor.
5. Sum the direct and nuclear path contributions to obtain the total SEU rate
   in upsets per bit per second.
6. Compute the MCU rate: multiply the total SEU rate by the device MCU fraction.
7. Compute the expected mission SEU count: SEU rate × memory bit-count ×
   mission duration in seconds.
8. Compare the total SEU rate and mission count against the device SEU budget
   (allowable upsets per bit per second and allowable total count). Flag any
   exceedance. Flag when no budget is on record — an unset budget is itself a
   finding, not a pass.
9. Report direct-path contribution, nuclear-path contribution, total rate, MCU
   rate, mission count, and compliance verdict with all findings listed.

## Pitfalls

- Applying only the direct-ionization model for proton SEU and omitting the
  nuclear-reaction path — the spallation contribution is significant at proton
  energies below the direct threshold and can dominate at low-to-moderate
  energies typical of trapped belts.
- Treating the nuclear-reaction path efficiency as 1.0 (the same as direct
  ionization) — this overstates the nuclear contribution; the correct factor
  accounts for the geometric cross-section and energy-dependent reaction
  probability.
- Using a single set of Weibull parameters for both paths when the device
  datasheet distinguishes them — the threshold and saturation values differ
  between direct ionization and nuclear-reaction mechanisms.
- Computing SEU rate with fluence (time-integrated flux) instead of differential
  flux — the rate integral requires flux in particles/(cm² · s · MeV), not
  fluence; confusing the two produces a rate in upsets/bit rather than
  upsets/bit/s.
- Ignoring MCU when the device specification is stated per-bit — in ECC-protected
  memories, MCU events that span multiple corrected words can defeat error
  correction even when single-bit upsets are handled.
- Reading "no budget entry" as zero violations — the absence of a budget record
  means the requirement was never captured and must be flagged as an open item.

## Behavior contract (gate 3)

The Weibull cross-section model, direct-path integration, nuclear-path
integration, combined-rate summation, MCU rate, mission count, and compliance
check logic is exercised by the gate 3 contract test:
scripts/test_e1012_seu_proton.py against scripts/e1012_seu_proton_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1012_seu_proton.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
