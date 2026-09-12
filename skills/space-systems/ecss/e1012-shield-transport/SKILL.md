---
name: e1012-shield-transport
description: "Use when run detailed 1-D, 2-D, or 3-D radiation transport calculations
  for spacecraft shielding analysis per ECSS-E-ST-10-12C clause 6.2.4: select a transport
  method (Monte Carlo or deterministic Sn/Pn code), specify geometry dimension and
  material composition, compute transmitted dose or fluence behind each shielding
  layer with buildup correction, and verify the result against the subsystem
  total-ionising-dose limit. For 1-D slab geometry, apply photon exponential
  attenuation and proton range-stopping to determine residual penetration or blocked
  contribution. Flag dimension mismatches, unsupported materials, invalid parameters,
  or dose-limit exceedances before accepting a shield design as adequate.
  Trigger: ecss, e-st-10c, e-st-10-12c, shield-transport, radiation-transport,
  monte-carlo, deterministic-sn, shielding, dose-limit, proton-range, fluence."
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
  tags: [ecss, e-st-10c, e-st-10-12c, shield-transport, radiation-transport, monte-carlo, deterministic-sn, shielding, dose-limit, proton-range]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Radiation Shield Transport (space-systems/ecss/e1012-shield-transport)

Use when the task is the detailed radiation transport calculation required by
ECSS-E-ST-10-12C clause 6.2.4 to verify that a spacecraft shielding design
holds the transmitted dose below each subsystem's total-ionising-dose (TID)
limit across the specified mission lifetime.

## Domain quick reference

- Clause 6.2.4 requires that shielding adequacy be demonstrated through a
  transport calculation — not just a fluence estimate — using either a Monte
  Carlo code (stochastic sampling of particle histories) or a deterministic
  code (Sn or Pn discrete-ordinates or spherical-harmonics solver).
  Both method families must produce a transmitted dose or fluence behind the
  shield; the choice of method is recorded in the analysis report.
- Geometry dimension drives the fidelity: 1-D (infinite slab or concentric
  sphere) is the standard bounding approximation; 2-D and 3-D models are
  required when local geometry effects (corners, gaps, penetrations) deviate
  significantly from the 1-D bound.
- For photon and secondary bremsstrahlung radiation, the primary transport
  mechanism through a homogeneous slab is exponential attenuation modified by
  a buildup factor that accounts for scattered photons re-entering the dose
  field. The linear attenuation coefficient is the product of the material's
  mass attenuation coefficient and its density.
- For protons, the dominant energy-loss mechanism is Coulomb stopping. Range
  calculations using power-law fits (Bragg–Kleeman scaling from proton data in
  the material) determine whether a proton of given incident energy penetrates
  a slab of given areal thickness.
- Each material in the shield stack must be drawn from the validated material
  database; an unrecognised material must be flagged before transport proceeds.
- The dose margin is defined as (dose limit − transmitted dose) / dose limit;
  a non-negative margin is required for the component to be compliant.

## Workflow

1. Confirm the transport method from the analysis plan: Monte Carlo or
   deterministic (Sn or Pn). Record the method category — stochastic vs.
   deterministic — in the analysis report header.
2. Confirm the geometry dimension (1, 2, or 3). For 1-D slab geometry, the
   module computes a direct bounding estimate. For 2-D or 3-D, the module
   applies the 1-D slab as a conservative bound and flags that a
   multi-dimensional external code is required for the full result.
3. For each shielding layer, identify the material and thickness. Reject any
   material not in the validated database before proceeding.
4. For each particle type of interest:
   a. Photon — compute the linear attenuation coefficient, estimate the
      buildup factor using Berger's approximation (B = 1 + μ_lin · t, capped
      where mean-free-path count is small), then apply the exponential
      attenuation formula to the incident dose rate to obtain the transmitted
      dose rate, and multiply by the exposure duration.
   b. Proton — compute the range in the material using the power-law
      fit R = a · E^b (areal thickness in g/cm²); if the shield areal
      thickness exceeds the proton range, the contribution is zero; otherwise
      the proton penetrates and its dose contribution is non-zero.
   c. Electron — apply a simplified half-value-layer approximation using an
      effective attenuation coefficient.
5. Compare the total transmitted dose against the subsystem TID limit.
   Compute the dose margin; a negative margin is a finding.
6. Aggregate findings: dose-limit exceedances, multi-D geometry caveats,
   missing material entries. The shield is adequate only when the finding
   list is empty and the dose margin is non-negative.

## Pitfalls

- Applying the incident dose rate directly as the transmitted dose —
  attenuation is always present; even a thin slab reduces the photon dose
  rate by a calculable factor.
- Omitting the buildup factor for photon transport through thick shields —
  scattered photons add to the transmitted dose and can drive the estimate
  below the actual value.
- Treating a stopped proton as contributing a small residual dose — once the
  shield areal thickness exceeds the proton range, the direct proton
  contribution is zero; dose from secondary particles (neutrons, pions) is
  tracked separately by a full Monte Carlo calculation outside this module.
- Accepting a 1-D slab result as sufficient for a component behind a
  structural corner, a cable feedthrough, or any geometry where the 1-D
  assumption breaks down — clause 6.2.4 requires the transport model to
  match the geometry; document the limitation and escalate to a 3-D code.
- Using an unvalidated material attenuation coefficient — always draw from
  the module's material database and flag any material not in the database
  rather than using an estimated value.

## Behavior contract (gate 3)

The transport setup validation, photon attenuation, proton range-stopping,
dose margin, and full analysis pipeline logic are exercised by the gate 3
contract test: scripts/test_e1012_shield_transport.py against
scripts/e1012_shield_transport_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_shield_transport.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
