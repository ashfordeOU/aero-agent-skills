---
name: e1012-bg-nuclear
description: "Use when determine the background count rate produced by nuclear interactions in spacecraft shielding materials under ECSS-E-ST-10-12C §10.4.3: for each shielding layer, compute the nuclear interaction probability from material type and areal density using the nuclear interaction length, estimate the secondary particle yield per interaction as a function of incident particle energy, compute the interaction rate for a given incident flux and detector area, scale by the fraction of secondaries depositing energy in the sensitive detector volume, and compare the resulting background rate against the instrument background budget to verify compliance. Trigger: ecss, e-st-10-12c, nuclear-background, spallation, secondary-particles, nuclear-interaction-length, detector-background, background-budget, ionisation."
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
  tags: [ecss, e-st-10-12c, nuclear-background, spallation, secondary-particles, nuclear-interaction-length, detector-background, background-budget, ionisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation — Background from Nuclear Interactions (space-systems/ecss/e1012-bg-nuclear)

Use when the task is predicting the detector background count rate arising
from nuclear interactions in spacecraft shielding under ECSS-E-ST-10-12C
§10.4.3 — computing nuclear interaction probability per shielding layer,
estimating secondary particle yield, and checking the result against the
instrument background budget.

## Domain quick reference

- §10.4.3 requires the analyst to account for background signal produced when
  energetic charged particles (primarily galactic cosmic rays and solar
  energetic protons) undergo nuclear inelastic reactions inside spacecraft
  structural or shielding materials. Each reaction produces secondary
  particles — neutrons, gamma rays, and nuclear recoils — that can deposit
  energy in a sensitive detector volume even when the primary particle does
  not reach it directly.
- The probability that an incident particle undergoes at least one nuclear
  interaction while traversing a material slab is governed by the nuclear
  interaction length λ_I (g/cm²), a material-specific constant that quantifies
  how far, on average, a particle travels before reacting. The interaction
  probability across a slab of areal density x is P = 1 − exp(−x / λ_I).
  Representative values: aluminium 106.4, copper 134.9, iron 131.9,
  polyethylene 77.1 g/cm² (from published nuclear-physics references;
  ECSS §10.4.3 cites these as input data).
- Secondary particle yield per interaction depends primarily on the incident
  particle's kinetic energy. Below roughly 20 MeV, spallation is suppressed
  and neutron production is negligible. Above that threshold the average
  neutron multiplicity rises approximately logarithmically with energy.
- The background rate reaching a detector is the product of the incident flux,
  the detector acceptance area, the interaction probability in the shielding
  stack, the secondary yield per interaction, and the fraction of secondaries
  that deposit detectable energy in the sensitive volume. This last factor
  accounts for detector geometry and threshold.
- Each detector or instrument carries an allowable background budget in Hz.
  The computed rate is compared against this budget; a ratio above 1 is a
  non-compliance finding.

## Workflow

1. Identify every shielding layer between the radiation environment and the
   sensitive detector: record material name, geometric thickness (cm), and
   bulk density (g/cm³) to obtain areal density (g/cm²).
2. For each layer, retrieve the nuclear interaction length λ_I for its
   material. Reject any unrecognised material before the calculation proceeds.
3. Compute the interaction probability for the layer: P = 1 − exp(−x / λ_I).
   Flag layers where P exceeds 0.1 — such layers are thin relative to λ_I
   and indicate that shielding provides less than one interaction length of
   margin.
4. Determine the incident particle's kinetic energy in MeV. If it falls below
   20 MeV, assign a secondary neutron yield of zero (spallation threshold not
   reached). Above 20 MeV, use the parameterised yield model
   n̄ = 0.5 × log₁₀(E / 20 MeV).
5. Compute the background rate:
   R = Φ × A_det × P × n̄ × f_dep
   where Φ is the incident flux (particles/cm²/s), A_det is the detector area
   (cm²), P is the interaction probability from step 3, n̄ is the secondary
   yield from step 4, and f_dep is the deposited-secondary fraction (0–1,
   instrument-specific).
6. Compare R against the instrument's background budget B (Hz). Record the
   ratio R/B and the margin in dB (−10 × log₁₀(R/B)). A ratio ≤ 1.0 is
   compliant; a ratio > 1.0 is a non-compliance finding requiring shielding
   redesign or instrument budget revision.

## Pitfalls

- Omitting the deposited-secondary fraction f_dep and treating all secondaries
  as depositing in the detector — this overstates background; the fraction
  depends on detector geometry and energy threshold and must be provided as
  an instrument requirement, not assumed to be 1.0.
- Using the electromagnetic radiation length X₀ instead of the nuclear
  interaction length λ_I — X₀ governs photon and electron cascades and is
  numerically shorter for heavy materials, leading to a large overestimate of
  nuclear background.
- Applying the yield model below 20 MeV and computing a non-zero yield —
  spallation neutron production requires sufficient energy transfer to
  overcome nuclear binding; using the log formula below threshold
  underestimates the threshold and overstates background.
- Treating a high-interaction-probability flag (P > 0.1) as acceptable without
  reviewing the shielding stack — thin shielding relative to λ_I means most
  primaries pass through unreacted, but the ones that do react produce a
  background contribution; the flag is a design review trigger, not a
  pass/fail criterion by itself.

## Behavior contract (gate 3)

The nuclear interaction length lookup, interaction probability, secondary
yield, background rate, and budget compliance logic are exercised by the
gate 3 contract test: scripts/test_e1012_bg_nuclear.py against
scripts/e1012_bg_nuclear_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_bg_nuclear.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
