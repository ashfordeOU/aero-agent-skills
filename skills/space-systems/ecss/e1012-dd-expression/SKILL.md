---
name: e1012-dd-expression
description: "Use when compute the displacement damage (DD) dose for a spacecraft device under ECSS-E-ST-10-12C §8.2: identify all contributing particle types and energy bins from the mission radiation environment, retrieve the Non-Ionizing Energy Loss (NIEL) value for each bin, multiply each bin fluence by its NIEL to obtain the partial DD contribution, sum all partial contributions to obtain the total DD dose in MeV/g, convert to a reference-particle equivalent fluence using the DD equivalence relation (NIEL ratio to the chosen reference), and compare the resulting equivalent fluence against the device displacement damage requirement. Trigger: ecss, e-st-10-system-scope, displacement-damage, niel, damage-factor, equivalent-fluence, radiation-effects, dd-dose, proton-damage."
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
  tags: [ecss, e-st-10-system-scope, displacement-damage, niel, damage-factor, equivalent-fluence, radiation-effects]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Radiation — Displacement Damage Expression (space-systems/ecss/e1012-dd-expression)

Use when the task is to compute the displacement damage dose for a
spacecraft device using the NIEL-based DD expression of
ECSS-E-ST-10-12C §8.2 — enumerating particle-energy bins, weighting
each by its Non-Ionizing Energy Loss value, summing to a total DD dose,
converting to a reference-particle equivalent fluence via the DD
equivalence relation, and checking the result against the device
displacement damage requirement.

## Domain quick reference

- Displacement damage (DD) is caused by energetic particles (protons,
  neutrons, heavy ions, electrons) displacing lattice atoms in
  semiconductor or other crystalline materials.  The primary parameter
  governing the severity is NIEL (Non-Ionizing Energy Loss), which
  quantifies the energy transferred to atomic recoils per unit mass
  traversed.  NIEL is particle-type- and energy-dependent; units are
  MeV·cm²/g.
- DD dose for a device is the integral of particle fluence times NIEL
  over all particle types and energy bins: D_d = Σ_i (Φ_i × NIEL_i),
  with units MeV/g.  Each bin contributes independently; bins with zero
  fluence or negligible NIEL may be dropped after explicit verification
  that the contribution is below the calculation threshold.
- DD equivalence normalises the DD dose — or the partial contributions —
  to a chosen reference condition, commonly the 1-MeV neutron fluence
  in silicon or the 10-MeV proton fluence in gallium arsenide.  The
  equivalence factor for a given bin is NIEL_bin / NIEL_ref.  The total
  reference-equivalent fluence is Φ_eq = Σ_i (Φ_i × NIEL_i / NIEL_ref).
  This converts a multi-particle, multi-energy environment into a single
  scalar that can be compared directly against device test data obtained
  under the reference condition.
- Device DD requirements are expressed as an allowable equivalent fluence
  (particles/cm² at the reference condition) derived from component
  qualification test data.  The assessment is compliant when Φ_eq ≤
  Φ_req with a margin factor ≥ the project-mandated design margin
  (commonly 2×).

## Workflow

1. Assemble the particle-energy bin list for the mission orbit and
   shielding configuration: for each particle type (proton, neutron,
   electron, heavy ion), obtain the omnidirectional fluence per energy
   bin over the mission lifetime.  Record the bin boundaries and fluence
   values in consistent units (particles/cm²).
2. Retrieve the NIEL value for each (particle type, energy) bin from a
   standard tabulation for the device material (silicon, GaAs, etc.).
   NIEL tables are available from SRIM, MULASSIS, and ECSS-E-ST-10-12C
   reference annexes.  Verify each NIEL value is positive and in
   MeV·cm²/g.
3. Compute the partial DD contribution for each bin:
   D_d,i = Φ_i × NIEL_i (MeV/g).
   Sum all partial contributions to obtain the total DD dose D_d.
4. Select the reference condition (reference particle type and energy,
   and the corresponding NIEL_ref for the device material).  Compute the
   damage factor for each bin: K_i = NIEL_i / NIEL_ref.  Apply it to
   obtain the bin equivalent fluence: Φ_eq,i = Φ_i × K_i.
5. Sum Φ_eq,i over all bins to obtain the total reference-equivalent
   fluence Φ_eq.
6. Compare Φ_eq against the device displacement damage requirement
   Φ_req.  Compute the margin factor M = Φ_req / Φ_eq.  Flag a
   failure when Φ_eq > Φ_req (M < 1) and a margin shortfall when
   M < the project design margin.

## Pitfalls

- Using the total DD dose D_d (MeV/g) directly as an equivalent fluence
  without dividing by NIEL_ref — the two quantities have different units
  and cannot be compared against a device test limit expressed in
  particles/cm².
- Selecting different reference conditions for different subsystems on
  the same spacecraft and mixing the resulting equivalent fluences in a
  system-level sum — equivalent fluences from different reference
  conditions are not additive.
- Dropping a particle type from the bin list because its NIEL is lower
  than the dominant species without computing the contribution — for
  high-fluence environments (e.g. trapped electrons) even a low NIEL can
  produce a non-negligible equivalent fluence.
- Applying the DD equivalence conversion only to the dominant bin and
  reading the result as the total — every bin must be converted and
  summed before comparison with the requirement.
- Omitting the design margin check and treating Φ_eq ≤ Φ_req as
  compliant without verifying that the ratio also satisfies the project
  design margin multiplier.

## Behavior contract (gate 3)

The partial DD computation, total DD dose aggregation, damage factor
calculation, equivalent fluence conversion, and budget assessment logic
are exercised by the gate 3 contract test:
scripts/test_e1012_dd_expression.py against
scripts/e1012_dd_expression_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_dd_expression.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
