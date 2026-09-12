---
name: e1012-dd-assessment
description: "Use when assess displacement damage (DD) parameters for a spacecraft device under ECSS-E-ST-10-12C §8.5: determine the total non-ionizing dose (TNID) by summing NIEL-weighted fluence contributions across all particle species and energy bins for the mission environment, convert TNID to the displacement damage equivalent fluence (DDEF) referenced to a standard particle, apply the project radiation design margin (RDM) factor to the DDEF, and compare the margin-adjusted DDEF against the device displacement damage limit to determine compliance. Trigger: ecss, e-st-10-system-scope, displacement-damage, dd-assessment, tnid, ddef, niel, rdm, radiation-design-margin."
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
  tags: [ecss, e-st-10-system-scope, displacement-damage, dd-assessment, tnid, ddef, niel, rdm]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Radiation — Displacement Damage Assessment (space-systems/ecss/e1012-dd-assessment)

Use when the task is the displacement damage assessment of a spacecraft
device per ECSS-E-ST-10-12C §8.5 — computing the named damage parameters
TNID (Total Non-Ionizing Dose) and DDEF (Displacement Damage Equivalent
Fluence), applying the radiation design margin, and delivering a
compliance verdict against the device displacement damage limit.

## Domain quick reference

- §8.5.1 defines the two damage characterisation quantities used in DD
  assessment.  TNID (Total Non-Ionizing Dose) is the integral of particle
  fluence times NIEL (Non-Ionizing Energy Loss) over all contributing
  particle species and energy bins for the mission environment; its unit
  is MeV/g.  DDEF (Displacement Damage Equivalent Fluence) normalises
  that dose to a chosen reference condition so it can be compared directly
  against device test data; its unit is reference-particle cm⁻².
  DDEF = TNID / NIEL_ref, where NIEL_ref is the NIEL of the reference
  particle in the device material at the reference energy.
- Common reference conditions: 10 MeV proton in silicon
  (NIEL_ref ≈ 5.55 × 10⁻⁴ MeV·cm²/g) and 1 MeV neutron in silicon
  (NIEL_ref ≈ 9.5 × 10⁻³ MeV·cm²/g).  The reference condition must be
  the same one used in the device qualification test that produced the DD
  limit; mixing reference conditions between environment and limit
  invalidates the assessment.
- §8.5.2.x specifies the calculation methods.  The assessed DDEF
  incorporates the project-mandated radiation design margin (RDM):
  DDEF_assessed = DDEF × RDM.  Compliance requires
  DDEF_assessed ≤ DDEF_limit.  ECSS typically requires RDM ≥ 2.

## Workflow

1. Assemble the particle-energy bin list for the mission orbit,
   shielding level, and mission duration.  Each bin records: particle
   species (proton, electron, neutron, heavy ion), energy (MeV),
   omnidirectional fluence (particles/cm²) over the mission lifetime, and
   NIEL value for the device material at that energy (MeV·cm²/g).
   Reject any bin with a non-positive NIEL or a negative fluence before
   it enters the sum.
2. Compute TNID by summing NIEL × fluence across every bin:
   TNID = Σ_i (NIEL_i × Φ_i)  [MeV/g].
   Record each bin's partial TNID contribution for traceability.
3. Select the reference condition and verify it matches the reference
   used for the device's DD qualification limit.  Compute DDEF:
   DDEF = TNID / NIEL_ref  [cm⁻²].
4. Retrieve the project RDM factor for displacement damage (typically
   ≥ 2 per ECSS-E-ST-10-12C Table 8-x).  Compute the assessed DDEF:
   DDEF_assessed = DDEF × RDM.
5. Compare DDEF_assessed against the device DD limit DDEF_limit.
   Record the margin ratio M = DDEF_limit / DDEF_assessed.  The device
   is compliant when M ≥ 1.  Flag a shortfall when M < 1, and record a
   warning when M is below the project minimum margin threshold.
6. Repeat steps 1–5 for every device in the itemised device list.
   Produce a per-device summary table: species list, TNID, DDEF,
   DDEF_assessed, DDEF_limit, margin M, and compliance status.

## Pitfalls

- Omitting the RDM multiplication and comparing bare DDEF against the
  limit — the ECSS §8.5 assessment always applies the RDM factor before
  the comparison; skipping it produces an unconservative result.
- Using a different reference condition for the environment DDEF than the
  one used in the device's qualification test — DDEF values from different
  reference conditions carry different units conceptually and cannot be
  compared directly.
- Including particles with fluence below the calculation threshold but
  treating the summed TNID as exact — each dropped bin is a deliberate
  decision that must be documented with its contribution relative to the
  total, not silently omitted.
- Applying a single NIEL_ref across devices made of different materials —
  each device material (Si, GaAs, InGaAs, Ge) has its own NIEL table;
  the reference NIEL must be from the same material as the device under
  assessment.
- Recording only the total DDEF without per-bin TNID contributions —
  traceability requires that each contributing bin be recorded so the
  dominant damage source can be identified and tested if the margin
  is marginal.

## Behavior contract (gate 3)

The TNID accumulation, DDEF conversion, RDM application, and compliance
verdict logic are exercised by the gate 3 contract test:
scripts/test_e1012_dd_assessment.py against
scripts/e1012_dd_assessment_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_dd_assessment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
