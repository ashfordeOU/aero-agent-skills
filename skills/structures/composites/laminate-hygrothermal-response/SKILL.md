---
name: laminate-hygrothermal-response
description: "Use when you must compute the hygrothermal response of a composite laminate: equilibrium moisture content from relative humidity with a linear isotherm, stiffness-weighted laminate CTE and CME assembled by classical lamination theory from ply-level properties, hygrothermal laminate strain from temperature and moisture changes, and residual strain from the cure-cooldown drop. Produces the moisture content, laminate CTE and CME in raw SI with a parts-per-million helper, and the hygrothermal and cure-cooldown strains that gate a laminate hygrothermal assessment. Trigger: hygrothermal response, laminate cte, laminate cme, moisture swelling, equilibrium moisture content, hygral strain, cure cooldown strain, laminate moisture content."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: composites
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [laminate-hygrothermal-response, hygrothermal-response, laminate-cte, moisture-swell-strain, cure-cooldown-strain, hygral-strain, laminate-moisture-content]
  version: 0.1.0
  author: AeroSkills
---

# Laminate Hygrothermal Response (structures/composites/laminate-hygrothermal-response)

Use when the task is the hygrothermal response of a composite laminate:
equilibrium moisture content from the ambient relative humidity,
stiffness-weighted laminate thermal and moisture expansion coefficients
by classical lamination theory (CLT), the hygrothermal strain from a
temperature change plus a moisture change, and the residual strain from
the cure-cooldown temperature drop. This leaf implements the exact CLT
free-expansion solution in pure Python, stdlib only, deterministic and
offline. Material properties (ply stiffness, ply expansion
coefficients, saturation moisture content) are inputs with documented
typical bounds; the code path is exact CLT arithmetic with no empirical
fits. It pairs with structures/composites/laminate-stiffness, whose
Qbar assembly this leaf reuses for the thermal and moisture weighting.

## Domain quick reference

- Linear isotherm: equilibrium moisture content M = m_sat * rh, where
  m_sat is the saturation mass fraction (default 0.015, published CFRP
  magnitudes 0.01-0.02) and rh the ambient relative humidity fraction.
- Plane-stress reduced stiffness: q11 = e1/d, q22 = e2/d,
  q12 = nu12*e2/d = nu21*e1/d, q66 = g12, with nu21 = nu12*e2/e1 and
  d = 1 - nu12*nu21.
- Qbar rotation with m = cos(theta), n = sin(theta):
  qbar11 = q11*m^4 + 2*(q12 + 2*q66)*m^2*n^2 + q22*n^4,
  qbar22 = q11*n^4 + 2*(q12 + 2*q66)*m^2*n^2 + q22*m^4,
  qbar12 = (q11 + q22 - 4*q66)*m^2*n^2 + q12*(m^4 + n^4),
  qbar66 = (q11 + q22 - 2*q12 - 2*q66)*m^2*n^2 + q66*(m^4 + n^4),
  qbar16 = (q11 - q12 - 2*q66)*m^3*n + (q12 - q22 + 2*q66)*m*n^3,
  qbar26 = (q11 - q12 - 2*q66)*m*n^3 + (q12 - q22 + 2*q66)*m^3*n.
- Free-expansion CLT for a symmetric balanced laminate: assemble the 2x2
  in-plane stiffness A = sum_k Qbar_k * t_k (rows qbar11, qbar12;
  qbar12, qbar22; shear row dropped) and the thermal force resultant per
  unit temperature Nth = sum_k Qbar_k * [alpha_x_k, alpha_y_k]^T * t_k,
  then solve A * [alpha_x, alpha_y]^T = Nth by the 2x2 determinant
  inversion. The moisture vector uses [beta_x_k, beta_y_k] the same way
  with the moisture force resultant Nm.
- The exact 2x2 inversion is REQUIRED: the simplified stiffness-weighted
  scalar ratio (Nth_x/A11 alone) returns 1.65 ppm for the worked
  [0/90]s, a wrong value, and fails the unidirectional identity. Only
  the full inversion returns alpha_1 exactly for a 0-deg unidirectional
  laminate.
- Hygrothermal strain: eps = alpha*delta_t + beta*delta_m per laminate
  axis. Cure-cooldown strain: alpha_x * (t_rt - t_cure), negative for a
  cooldown with positive alpha.
- Coefficients are raw SI in the module (alpha in 1/K, beta per unit
  moisture mass fraction); cte_ppm(alpha) = alpha * 1e6 is the
  reporting helper.
- Transport aeroplane structural context sits in FAR-25 (reference only;
  the relations above are standard mechanics, summary-only).

## Workflow

1. Gather the ambient relative humidity and the ply material properties:
   e1, e2 (Pa), nu12, g12 (Pa), alpha_1 and alpha_2 (1/K), beta_1 and
   beta_2 (per unit moisture fraction), ply angle theta_deg and ply
   thickness t (m). Use equilibrium_moisture_content for M at the
   given rh with m_sat (default 0.015).
2. Build the plane-stress stiffness of one ply with plane_stress_q and
   rotate it to the laminate axes with qbar.
3. Assemble the symmetric balanced laminate and solve for the laminate
   coefficients with laminate_cte_cme, which returns alpha_x, alpha_y,
   beta_x and beta_y by the exact 2x2 CLT inversion.
4. Apply the temperature and moisture changes with hygrothermal_strain,
   or report the residual cure strain with cure_cooldown_strain from
   the cure temperature and room temperature (21 C default).
5. For a one-call assessment run laminate_hygrothermal_response with
   the ply list, rh_fraction and delta_t_k; delta_m defaults to the
   equilibrium moisture content and t_cure_c adds the cure branch.
6. Report coefficients with cte_ppm where parts per million read better
   than raw 1/K, then confirm the deterministic checks with the
   contract test.

## Worked example

T300/5208-style carbon/epoxy [0/90]s symmetric balanced laminate, ply
t = 0.125e-3 m each: e1 = 181e9 Pa, e2 = 10.3e9 Pa, nu12 = 0.28,
g12 = 7.17e9 Pa, alpha_1 = -0.3e-6/K, alpha_2 = 28.1e-6/K, beta_1 = 0,
beta_2 = 0.6 per unit moisture fraction. Ambient rh = 0.6, m_sat =
0.015, cure 177 C, room 21 C. Real module outputs:

- equilibrium_moisture_content(0.6) = 0.009 (0.015 * 0.6).
- plane_stress_q: q11 = 181.81 GPa, q22 = 10.35 GPa, q12 = 2.90 GPa,
  q66 = 7.17 GPa.
- laminate_cte_cme: alpha_x = alpha_y = 1.59998e-6/K (1.60 ppm, inside
  the 1.55-1.70 ppm band); beta_x = beta_y = 0.04014 per unit moisture
  fraction (the CLT moisture solution for beta_1 = 0, beta_2 = 0.6).
  The simplified q11-only scalar ratio gives 1.65 ppm, outside the
  exact CLT result, and must not be used.
- Cure-cooldown strain: alpha_x * (21 - 177) = -2.496e-4 (about
  -2.50e-4) after the -156 K cooldown.
- Moisture branch: hygrothermal_strain at delta_m = 0.009 gives
  beta_x * 0.009 = 3.613e-4 (about 3.6e-4); published CFRP swelling
  strain at saturation is roughly 0.1-0.7% when beta_2 ~ 0.1-0.6 and
  m_sat ~ 1-2%.
- Combined hygrothermal strain at delta_t = -156 K and delta_m = 0.009:
  alpha_x * delta_t + beta_x * delta_m = -2.496e-4 + 3.613e-4 =
  +1.117e-4. In this laminate the moisture swelling dominates the
  cooldown contraction.
- Identity check: a 0-deg unidirectional laminate of the same ply
  returns alpha_x = alpha_1 = -0.3e-6/K exactly (float-precision
  difference 0.0), which only the full 2x2 inversion achieves.


## Pitfalls

- Using the simplified scalar ratio instead of the exact inversion:
  the q11-only stiffness-weighted average returns 1.65 ppm for the
  worked [0/90]s where the exact 2x2 CLT inversion gives 1.60 ppm,
  and only the full inversion returns alpha_1 exactly for a 0-deg
  unidirectional laminate.
- Confusing the moisture and thermal branches: the hygrothermal
  strain is alpha * delta_t + beta * delta_m per axis, and in the
  worked laminate the moisture swelling (+3.6e-4) dominates the cure
  cooldown contraction (-2.5e-4); summing them with the wrong sign
  misses the net +1.12e-4.
- Assuming every laminate is 0-deg: the ply angles enter through the
  Qbar rotation, so a 45-deg unidirectional ply must return the
  rotated material coefficient; an angle outside [-90, 90] raises
  ValueError.
- Quoting raw SI where ppm reads better: cte_ppm(alpha) = alpha *
  1e6 is the reporting helper, and mixing 1/K values with ppm values
  in one comparison misreads the coefficient by 1e6.
- Forgetting the moisture content endpoint domain: the isotherm is
  M = m_sat * rh with rh in [0, 1] and m_sat > 0; rh outside the
  unit interval or a non-positive saturation raises ValueError.
- Feeding non-physical ply properties: non-positive moduli,
  nu12*nu21 >= 1, empty ply lists, and non-positive thickness all
  raise ValueError; the code path is exact CLT arithmetic, so the
  material inputs carry the physics.
## Verification

- Confirm laminate_cte_cme on the worked [0/90]s returns alpha_x
  inside 1.55-1.70e-6/K and beta_x inside 0.035-0.045.
- Confirm a 0-deg unidirectional layup returns alpha_1 and beta_1 to
  float precision, and that a 45-deg unidirectional ply returns the
  rotated material coefficient.
- Confirm equilibrium_moisture_content maps rh = 0 to 0 and rh = 1 to
  m_sat, and rejects rh outside [0, 1] and m_sat <= 0 with ValueError.
- Confirm the 1D stiffness-weighted average formula matches a direct
  ply-by-ply sum for the [0/90]s at about 1.23e-6/K (inside 0-5 ppm),
  distinct from the exact 1.60 ppm inversion.
- Confirm the cure-strain sign: cooling (delta_t < 0) with positive
  alpha gives a negative strain.
- Confirm plane_stress_q, qbar and laminate_cte_cme reject non-physical
  inputs (non-positive moduli, nu12*nu21 >= 1, empty ply list,
  non-positive thickness, angle outside [-90, 90]) with ValueError.
- Confirm determinism: the module has no RNG and returns identical
  floats run to run.
- Run the contract test offline: python3
  scripts/test_laminate_hygrothermal_response.py (32 tests,
  deterministic, exits 0).

## Related leaves

- structures/composites/laminate-stiffness: the mechanical CLT sibling
  whose Qbar assembly this leaf reuses for the thermal and moisture
  weighting; it owns the elastic A matrix, this leaf owns expansion.
- structures/composites/cmh17-allowables: hot/wet statistical strength
  knockdown factors that consume the moisture content this leaf
  computes; this leaf computes expansion strain, not strength.
- structures/thermal-structures/thermal-stress-analysis: isotropic
  constrained-member alpha*dT stress and bimetallic strips, the
  homogeneous-material counterpart of this laminate expansion leaf.
- structures/composites/sandwich-panels: honeycomb core selection
  context where core moisture is a caveat, separate from laminate
  hygrothermal strain.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_laminate_hygrothermal_response.py

The test covers the worked [0/90]s example (q11 ~ 181.8 GPa, q22 ~
10.35 GPa, alpha_x ~ 1.60e-6/K, beta_x ~ 0.040, equilibrium moisture
0.009, cure strain ~ -2.50e-4, moisture strain ~ 3.6e-4), the exact 2x2
inversion identity for a 0-deg unidirectional laminate, Qbar rotation
invariants and coupling-term symmetry, equilibrium moisture isotherm
endpoints, cure-cooldown sign, ValueError rejection of non-physical
inputs, determinism, and the one-call convenience dict keys and values.

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain); the CLT hygrothermal relations above are standard
  mechanics methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
