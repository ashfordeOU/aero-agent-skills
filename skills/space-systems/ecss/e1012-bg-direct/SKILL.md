---
name: e1012-bg-direct
description: "Use when predict the sensor background count rate produced by direct ionisation of the active detector volume by charged particles under ECSS-E-ST-10-12C §10.4.2: identify the charged particle populations (trapped protons, trapped electrons, galactic cosmic rays, solar energetic particles) at the target orbit, compute the energy deposited per crossing particle from its linear energy transfer (LET) and sensor geometry, retain only populations whose deposited energy meets or exceeds the detection threshold, accumulate the background event rate across all contributing populations using particle flux and sensor cross-section, and compare the aggregated rate against the sensor background allocation. Trigger: ecss, e-st-10-12c, sensor-background, direct-ionisation, charged-particle, let, deposited-energy, detection-threshold."
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
  tags: [ecss, e-st-10-12c, sensor-background, direct-ionisation, charged-particle, let, deposited-energy, detection-threshold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Radiation — Sensor Background from Direct Ionisation (space-systems/ecss/e1012-bg-direct)

Use when the task is to predict the background count rate in a spaceborne
sensor caused by direct ionisation of its active volume by charged
particles, following ECSS-E-ST-10-12C §10.4.2. The procedure covers
identifying the contributing particle populations, computing the deposited
energy for each population using its linear energy transfer (LET) and the
sensor geometry, filtering out populations that fall below the detection
threshold, and comparing the accumulated rate against the sensor background
allocation.

## Domain quick reference

- **Direct ionisation** is the mechanism by which a charged particle (proton,
  electron, heavy ion) traverses the active detector volume and transfers
  energy to the material through Coulomb interactions with bound electrons.
  In semiconductor sensors this creates free electron-hole pairs; in
  scintillators it produces photons. If the resulting signal exceeds the
  detection threshold the crossing is recorded as a background event.
- **Linear energy transfer (LET)** quantifies the mean energy deposited per
  unit areal density along the particle track, in units of MeV·cm²/mg (or
  equivalently MeV·cm²/g × 10⁻³). The stopping power in MeV/cm equals
  LET × material density (mg/cm³). For a sensor with known thickness and
  material density, the energy deposited per crossing is
  `LET × density_mg_cm3 × path_length_cm`.
- **Particle populations** that contribute to direct-ionisation background
  in typical Earth orbits are: trapped protons, trapped electrons,
  galactic cosmic-ray protons, galactic cosmic-ray heavy ions, and solar
  energetic protons and heavy ions. Each population has a distinct flux
  spectrum and LET range. Each is treated as a separate contributor.
- **Detection threshold**: only crossings that deposit energy at or above
  the threshold produce a recorded background event. Populations whose
  deposited energy falls below the threshold are excluded from the
  background sum.
- **Geometry factor**: for a flat detector illuminated by an isotropic
  omnidirectional flux, only particles arriving from the forward hemisphere
  can traverse the detector face. The effective rate of hits is
  `flux × area × 0.5` (hemisphere factor = 0.5 for isotropic illumination
  of one face).
- **Background allocation**: the total accumulated rate is compared against
  the sensor-level background allocation derived from the instrument
  performance requirement. An exceedance is a finding that requires
  shielding, threshold adjustment, or environmental mitigation.

## Workflow

1. Identify the orbit environment and retrieve the omnidirectional particle
   flux (particles/cm²/s) for each relevant population (trapped protons,
   trapped electrons, GCR protons, GCR heavy ions, SEP protons, SEP heavy
   ions). Each population must be assigned one of the recognised type
   identifiers; an unrecognised type is rejected before it enters the
   calculation.
2. Record the sensor geometry and material: active area (cm²), active
   thickness (cm), material density (g/cm³), and the detection threshold
   (MeV of deposited energy). Reject any sensor spec with non-positive
   dimensions or density.
3. For each particle population, compute the deposited energy per crossing:
   `E_dep [MeV] = LET [MeV·cm²/mg] × density [g/cm³] × 1000 [mg/g] × thickness [cm]`.
   This assumes normal-incidence path length equal to the active thickness;
   a mean chord calculation (4V/S for a convex body) may be substituted for
   a full geometry model.
4. Apply the detection threshold: a population contributes to the background
   only if `E_dep ≥ threshold_mev`. Populations below threshold are recorded
   as sub-threshold contributors but carry zero rate.
5. For each contributing population, compute the hit rate:
   `rate [events/s] = flux [/cm²/s] × area [cm²] × 0.5`.
   The factor 0.5 is the hemisphere factor for isotropic illumination of a
   single flat detector face.
6. Sum the hit rates across all contributing populations to obtain the total
   background rate (events/s).
7. If a background allocation (budget) is on record, compare the total rate
   against it. Flag any exceedance. If no budget is recorded, flag the
   missing allocation as a finding — absence of a budget is not a pass.
8. Report: total background rate, per-population breakdown (deposited energy,
   above/below threshold, individual rate), budget comparison status.

## Pitfalls

- Omitting a particle population because its individual contribution seems
  small — in high-inclination or deep-space orbits, GCR heavy ions can
  dominate background even at low flux because their high LET ensures every
  crossing is above threshold.
- Applying the flux directly as a hit rate without the hemisphere factor —
  an omnidirectional flux already integrates over 4π steradians; dividing
  by two (0.5) for one-sided illumination is mandatory to avoid a factor-of-two
  overestimate.
- Treating a sub-threshold population as a zero-risk population without
  recording it — changes in threshold (e.g. electronics aging) or in the
  LET (e.g. higher-Z particles) can promote a sub-threshold contributor into
  a significant one; the sub-threshold list must be retained in the assessment.
- Using path length equal to the sensor diagonal rather than the mean chord
  or normal-incidence thickness — this inflates deposited energy and can
  cause an over-conservatism that masks real mitigation options.
- Leaving the background allocation unset and interpreting "no exceedance"
  as compliant — a missing allocation means the performance requirement was
  never captured, which is itself a finding.

## Behavior contract (gate 3)

The particle validation, deposited-energy calculation, threshold filtering,
hit-rate accumulation, and budget-comparison logic are exercised by the gate 3
contract test: scripts/test_e1012_bg_direct.py against
scripts/e1012_bg_direct_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_bg_direct.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
