---
name: ramberg-osgood
description: "Use when you must build the elastic-plastic stress-strain response of a metallic material with the Ramberg-Osgood three-parameter model: compute the total strain at a given stress with strain = stress/E + 0.002*(stress/sigma_0.2)^n, invert the implicit equation by bisection for the stress at a required total strain, and derive the plastic strain, secant modulus, and tangent modulus along the curve. Produces the stress-strain curve points and stiffness values used in metallic structural analysis beyond the yield point. Trigger: ramberg-osgood, stress-strain-curve, plastic-strain, secant-modulus, tangent-modulus, offset-yield-strength, strain-hardening, elastic-plastic."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tn-902
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: materials
  tags: [ramberg-osgood, stress-strain-curve, plastic-strain, secant-modulus, tangent-modulus, offset-yield-strength, strain-hardening, elastic-plastic]
  version: 0.1.0
  author: Aero Agent Skills
---

# Ramberg-Osgood Stress-Strain (structures/materials/ramberg-osgood)

Use when the task is the elastic-plastic stress-strain response of a
metallic material: total strain from a stress, stress by inversion of
the implicit Ramberg-Osgood equation, plastic strain, secant modulus,
and tangent modulus for metallic structural analysis beyond the yield
point.

## Domain quick reference

- Ramberg-Osgood three-parameter model (NACA TN 902):
  epsilon = sigma / E + 0.002 * (sigma / sigma_0.2) ** n, with stress
  sigma and elastic modulus E in MPa, sigma_0.2 the 0.2 percent offset
  yield strength in MPa, and n the strain hardening exponent (typically
  3 to 30 for aerospace metals). Strain is dimensionless.
- Elastic strain: epsilon_e = sigma / E.
- Plastic strain: epsilon_p = 0.002 * (sigma / sigma_0.2) ** n; the
  total strain is the sum epsilon_e + epsilon_p.
- Stress at a given total strain: the equation is implicit in sigma, so
  solve by bisection on the monotonic residual
  f(sigma) = sigma / E + 0.002 * (sigma / sigma_0.2) ** n - epsilon,
  bracketed on [0, E * epsilon] because sigma / E never exceeds the
  total strain.
- Secant modulus: E_s = sigma / epsilon (chord slope from the origin).
- Tangent modulus: E_t = 1 / (1 / E + 0.002 * n * sigma ** (n - 1) /
  sigma_0.2 ** n); at sigma = 0 the tangent modulus equals E, and it
  falls toward the plastic plateau as the stress rises.
- The model is common engineering methodology; the source paper is NACA
  TN 902 (US government work, public domain).

## Workflow

1. Collect the material elastic modulus E, the 0.2 percent offset yield
   strength sigma_0.2, and the strain hardening exponent n.
2. Compute the total strain at a stress with strain, or the elastic and
   plastic parts with elastic_strain and plastic_strain.
3. For a required total strain, invert the model with stress_for_strain
   (bisection; the stress lies between 0 and E * epsilon).
4. Derive the secant modulus with secant_modulus and the tangent
   modulus with tangent_modulus along the curve.
5. Build the curve as a table of stress, strain, plastic strain, secant
   modulus, and tangent modulus points for the structural analysis.

## Pitfalls

- Using only the elastic term sigma / E above the yield point: the
  plastic term 0.002 * (sigma / sigma_0.2) ** n dominates once sigma
  exceeds sigma_0.2, and a purely elastic estimate understates the
  strain badly.
- Treating the exponent n as a count: it is the strain hardening
  exponent, not a number of terms; values below 1 break the model
  monotonicity and the bisection bracket.
- Mixing units: E and sigma_0.2 must share the unit of sigma (MPa);
  mixing MPa and ksi shifts the plastic term by powers of 10.
- Expecting stress_for_strain to be a closed form: the equation is
  implicit in sigma and needs the bisection solve; the elastic
  extrapolation E * epsilon is an upper bound on the stress, not the
  answer.
- Calling secant_modulus at zero strain: the chord slope is undefined
  at epsilon = 0; use the tangent modulus E there.
- Ignoring the plastic strain sign: plastic_strain raises on an
  inconsistent input where sigma / E already exceeds the total strain.

## Behavior contract (gate 3)

The Ramberg-Osgood strain, inversion, and modulus logic is exercised by
the gate 3 contract test: scripts/test_ramberg_osgood.py against
scripts/ramberg_osgood_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_ramberg_osgood.py

## Compliance

- Standards referenced, not reproduced: NACA TN 902 is US government
  work (public domain); the Ramberg-Osgood equation and its secant and
  tangent modulus derivatives are common materials-engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
