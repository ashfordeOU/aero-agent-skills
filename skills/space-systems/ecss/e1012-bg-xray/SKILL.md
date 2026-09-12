---
name: e1012-bg-xray
description: "Use when compute the fluorescent X-ray interaction background for
  a space detector or instrument per ECSS-E-ST-10-12C §10.4.5: enumerate
  structural and shielding materials in the detector field of view, check
  whether each material's K-shell absorption edge is below the primary
  radiation energy, compute the K-shell photoelectric cross-section and
  fluorescent photon yield per emission line (K-alpha and K-beta) from
  incident fluence, element areal density, fluorescence yield, and detector
  solid angle, then sum all material contributions to form the predicted
  background spectrum and flag any line whose count exceeds the instrument
  background tolerance. Trigger: ecss, e-st-10-system-scope, x-ray-fluorescence,
  xrf, fluorescence-yield, characteristic-x-rays, detector-background,
  photoelectric-cross-section, radiation-background."
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
  tags: [ecss, e-st-10-system-scope, x-ray-fluorescence, xrf, fluorescence-yield, characteristic-x-rays, detector-background, photoelectric-cross-section, radiation-background]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Fluorescent X-ray Interactions Background (space-systems/ecss/e1012-bg-xray)

Use when the task is to compute the fluorescent X-ray interaction background
for a space detector or instrument per ECSS-E-ST-10-12C §10.4.5 — checking
each structural and shielding material against the primary radiation energy,
computing per-line photon yields, and comparing the total background spectrum
against the detector's tolerance threshold.

## Domain quick reference

- **K-shell fluorescence mechanism**: when primary radiation (photons,
  electrons, protons) irradiates a material with energy exceeding the
  element's K-shell absorption edge, inner electrons are ejected. As
  higher-shell electrons fill the vacancy, characteristic X-ray photons are
  emitted at fixed energies (K-alpha, K-beta) unique to that element. These
  secondary photons reach the detector as a non-astrophysical background.
- **Excitation threshold**: a material produces K-shell fluorescence only when
  the primary photon energy is strictly above its K-shell absorption edge
  energy. Materials with edges above the primary energy contribute zero
  fluorescent background for that radiation component.
- **Fluorescence yield (ω_K)**: the fraction of K-shell vacancies that produce
  an X-ray photon rather than an Auger electron. ω_K increases with atomic
  number Z; it is small for light elements (Al: ≈0.04) and substantial for
  heavier structural metals (Fe: ≈0.34, Cu: ≈0.44).
- **Line branching**: the K-alpha line carries approximately 85–88% of the
  K-shell fluorescent emission; K-beta carries the remainder. Both must be
  accounted for in a full background spectrum.
- **Photoelectric cross-section scaling**: above the K-edge, the K-shell
  photoelectric cross-section falls approximately as (E_edge/E)³. Doubling
  the primary energy reduces the cross-section by roughly an order of
  magnitude, so broadband primary spectra must not be collapsed to a single
  worst-case energy.
- **Background count at detector**: the predicted photon count is proportional
  to primary fluence × cross-section × areal density × fluorescence yield ×
  line fraction × (Ω/4π), where Ω is the solid angle subtended by the detector
  active area.

## Workflow

1. **Enumerate materials**: list every structural and shielding material
   in the instrument irradiation geometry. For each material record the
   element symbol and areal density (g/cm²). Accept only elements with
   known K-shell data; reject unrecognized symbols before they enter the
   calculation.
2. **Characterize primary radiation**: specify the primary photon energy (keV)
   and fluence (ph/cm²) integrated over the exposure interval. For broadband
   spectra, sample representative energies spanning the range.
3. **Check excitation per material**: for each material, compare the primary
   energy against the K-shell absorption edge. If the primary energy is at or
   below the edge, the material contributes no K-shell fluorescence at that
   energy — drop the pair from the yield calculation.
4. **Compute photoelectric cross-section**: for excited materials, evaluate
   σ_K(E) = σ_K,edge × (E_edge/E)³ where σ_K,edge is the tabulated
   cross-section just above the K-edge. Units: cm²/g.
5. **Compute per-line fluorescent yield**: for the K-alpha line:
   N_α = Φ × σ_K(E) × ρt × ω_K × f_α × (Ω/4π),
   and for the K-beta line substitute f_β = 1 − f_α. Here Φ is fluence
   (ph/cm²), ρt is areal density (g/cm²), ω_K is the fluorescence yield,
   and Ω is the detector solid angle (sr).
6. **Aggregate background spectrum**: sum K-alpha and K-beta yields across
   all excited materials. Each contributing material adds two line entries
   (energy in keV, predicted count) to the background spectrum.
7. **Flag dominant lines**: compare each line's total yield against the
   detector's background tolerance (expressed as a photon count threshold).
   Flag any line that exceeds the threshold. A detector with at least one
   flagged line requires mitigation — shielding redesign, atomic-number
   grading, or a narrower energy-band exclusion window.

## Pitfalls

- **Omitting the excitation check**: including a material whose K-edge
  exceeds the primary energy overstates the background. The cross-section
  formula is only valid above the edge; applying it below the edge is
  unphysical and must be prevented.
- **Collapsing K-alpha and K-beta to one line**: the two lines differ in
  energy and intensity. Merging them produces incorrect spectral positions
  and misestimates the count rate at each energy, which matters when the
  background assessment feeds a spectral fitting pipeline.
- **Assuming a flat cross-section**: the E⁻³ energy dependence is strong.
  Using the edge value at all primary energies overestimates the background
  for high-energy primaries and underestimates it near the edge.
- **Neglecting solid angle**: a large material areal density with a very
  small detector solid angle fraction may contribute negligible detected
  photons. Recording only the total yield without the solid angle factor
  prevents meaningful comparison to the detector tolerance budget.
- **Unset background tolerance treated as a pass**: if the instrument
  tolerance threshold has not been specified, a zero-flagged result is
  meaningless. The absence of a tolerance value is itself a finding, not
  an indication of compliance.

## Behavior contract (gate 3)

The element-lookup, excitation-check, cross-section, per-line yield,
background-spectrum aggregation, and dominant-line flagging logic is
exercised by the gate 3 contract test: scripts/test_e1012_bg_xray.py
against scripts/e1012_bg_xray_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_bg_xray.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
