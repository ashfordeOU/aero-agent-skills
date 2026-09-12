---
name: e1012-bg-scint
description: "Use when estimate scintillation and Cerenkov background count rates
  in photomultiplier tubes (PMTs) and microchannel plates (MCPs) exposed to a space
  radiation environment under ECSS-E-ST-10-12C §10.4.6: identify the incident particle
  species, kinetic energy, and fluence rate; verify whether each particle exceeds the
  Cerenkov threshold in the detector window or substrate material; compute the Cerenkov
  photon yield per unit path length using the Frank-Tamm visible-band integral; add
  the ionisation-driven scintillation contribution; derive the total spurious background
  count rate; and compare the result against the detector dark-count budget to determine
  compliance. Trigger: ecss, e-st-10-system-scope, scintillation, cerenkov, pmt, mcp,
  background-rate, photon-detector, radiation-background."
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
  tags: [ecss, e-st-10-system-scope, scintillation, cerenkov, pmt, mcp, background-rate, photon-detector, radiation-background]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Scintillation/Cerenkov Background in PMTs and MCPs
# (space-systems/ecss/e1012-bg-scint)

Use when the task is to estimate the spurious photon background count rate
induced by scintillation and Cerenkov emission in photomultiplier tube (PMT)
or microchannel plate (MCP) detectors operating in a space radiation
environment, following the ECSS-E-ST-10-12C §10.4.6 assessment procedure.
The leaf covers the complete path from particle species and energy through
photon yield to compliance against a stated dark-count budget.

## Domain quick reference

- **Cerenkov emission** occurs when a charged particle travels through a
  dielectric medium (PMT window, MCP substrate glass) faster than the phase
  velocity of light in that medium. The threshold condition is β > 1/n, where
  β = v/c and n is the material refractive index. Photon yield per unit path
  length in the visible band (≈200–700 nm) scales as z²sin²θ_C, where z is
  the particle charge number and sin²θ_C = 1 − 1/(β²n²). The coefficient is
  approximately 490 photons cm⁻¹ for z = 1 in the fully relativistic limit.

- **Scintillation emission** results from the ionisation energy deposited by
  the particle along its track in the material. The deposited energy per unit
  path length (dE/dx) scales roughly as z² at fixed velocity (Bethe-Bloch
  approximation); each material converts a fixed number of photons per MeV
  deposited. Scintillation is non-zero for all particle energies, including
  those below the Cerenkov threshold.

- **Detector sensitivity**: PMTs detect single photons via the photoelectric
  effect on the photocathode followed by dynode multiplication. MCPs use
  secondary-electron emission in an array of glass capillaries. Both devices
  register spurious counts whenever a background photon (Cerenkov or
  scintillation) falls on the sensitive area within the coincidence window.
  The combined background raises the effective dark-count rate.

- **Key materials**: borosilicate glass (n ≈ 1.47), fused silica (n ≈ 1.46),
  BK7 optical glass (n ≈ 1.52), MgF₂ (n ≈ 1.38). Lower refractive index
  raises the Cerenkov threshold — MgF₂ windows suppress Cerenkov emission
  from electrons that would produce it in glass.

- **Particle environment**: trapped radiation belt electrons (typically
  0.1–10 MeV) are the dominant Cerenkov source in low Earth and medium Earth
  orbits. Protons and heavier ions contribute primarily through scintillation
  and, at sufficiently high energy, Cerenkov emission.

## Workflow

1. **Identify the detector and material.** Record the detector type (PMT or
   MCP), the window/substrate material, the detector sensitive area, and the
   effective mean particle path length through the active volume.

2. **Inventory the incident particle environment.** For each particle species
   (electron, proton, heavy ion), record the representative kinetic energy and
   the omni-directional flux at the detector location. Use the orbit-and-shielding
   analysis outputs from the broader E-ST-10-12C assessment.

3. **Check the Cerenkov threshold.** For each particle species and material,
   compute β_min = 1/n and the corresponding threshold kinetic energy:
   E_thr = m₀c²(γ_min − 1) where γ_min = 1/√(1 − β_min²). Particles below
   the threshold produce no Cerenkov emission; retain only those above it for
   the Cerenkov yield step.

4. **Compute Cerenkov photon yield per unit path length.** For each
   above-threshold species: calculate β from the kinetic energy and rest mass,
   derive sin²θ_C = 1 − 1/(β²n²), and apply the Frank-Tamm visible-band
   result: dN/dx = 490 z² sin²θ_C  [photons cm⁻¹].

5. **Compute scintillation photon yield per unit path length.** For each
   species: apply dE/dx ≈ (dE/dx)_MIP × z² and multiply by the material's
   photon yield per MeV deposited.

6. **Derive the total background count rate.** For each species: multiply
   the flux [particles cm⁻²s⁻¹] by the sensitive area [cm²] to get the
   particle rate, then by (Cerenkov yield + scintillation yield) × path
   length to get photons s⁻¹. Sum over all species.

7. **Compare against the dark-count budget.** Retrieve the detector's
   allowable dark-count rate from its requirement. Compute the margin
   (budget − rate) and the ratio (rate / budget). Declare pass if rate ≤
   budget; flag as an exceedance otherwise. Also flag a detector whose
   budget has never been set — an unset budget is a missing requirement, not
   an implicit pass.

8. **Record findings.** Document the dominant contributor (Cerenkov vs.
   scintillation, dominant species), margin value, and any exceedance.
   Feed results into the instrument noise budget and the system-level
   background apportionment.

## Pitfalls

- **Applying Cerenkov yield below threshold.** A particle below β_min
  produces zero Cerenkov photons; treating the Frank-Tamm formula as valid
  below threshold overstates the background and can drive unnecessary
  design changes.

- **Conflating Cerenkov and scintillation.** Scintillation is present at all
  energies; Cerenkov switches on at threshold. For low-energy protons, the
  entire background is scintillation-only — do not report zero background
  because the Cerenkov term is zero.

- **Ignoring z² scaling.** Heavy ions (z = 2 for alpha) produce 4× the
  Cerenkov photons and 4× the scintillation yield of a same-velocity proton
  (z = 1). Using proton cross-sections for all ions will underestimate heavy-
  ion background by a factor of z².

- **Using area without path length.** The background scales as particle flux
  × area × path length. A thin window and a thick window at the same flux
  give very different backgrounds; path length must be taken from the actual
  detector geometry.

- **Reading an unset budget as a pass.** If no dark-count budget has been
  allocated to the detector, the §10.4.6 check cannot be completed. Flag the
  missing requirement rather than reporting compliance.

- **Neglecting orbit-dependent flux.** The particle flux at the detector
  depends on the orbit, shielding thickness, and solar activity; use the
  environment file computed for the specific mission profile, not a generic
  handbook value.

## Behavior contract (gate 3)

The Cerenkov threshold, photon yield, background rate, and compliance
assessment logic is exercised by the gate 3 contract test:
  scripts/test_e1012_bg_scint.py against scripts/e1012_bg_scint_logic.py
  (stdlib unittest, offline, deterministic).
Run:
  python3 scripts/test_e1012_bg_scint.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Anchor clause: ECSS-E-ST-10-12C §10.4.6.
