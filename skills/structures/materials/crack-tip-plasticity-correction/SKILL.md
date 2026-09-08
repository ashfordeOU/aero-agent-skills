---
name: crack-tip-plasticity-correction
description: "Use when you must compute the crack-tip-plasticity-correction for a crack in metallic structure: evaluate the Irwin plastic-zone radius in plane stress r_p = (1/pi)*(K/sigma_ys)^2 and the reduced plane-strain zone (1/(3*pi))*(K/sigma_ys)^2, form the effective-crack-length a_eff = a + r_p from the uncorrected elastic K, compute the corrected stress intensity K_eff = Y*sigma*sqrt(pi*a_eff), and judge the LEFM-validity verdict from the zone-to-crack ratio against the 2.5*(K/sigma_ys)^2 size rule. Applies the dugdale-strip-yield model to a center crack: the strip-yield zone rho = a*(sec(pi*sigma/(2*sigma_0)) - 1), its small-scale-yielding asymptote (pi/8)*(K/sigma_0)^2, and the k-eff to elastic-K ratio beyond that limit. Produces the plastic-zone radius, effective crack length, corrected stress intensity, k-eff ratio and validity verdict gating elastic fracture results. Trigger: plastic zone, effective crack length, small-scale yielding, Dugdale strip yield, Irwin zone, K_eff correction."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mmpsd
    reference-only: true
gated: false
domain: structures
pack: materials
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: materials
  tags: [crack-tip-plasticity-correction, irwin-plastic-zone, effective-crack-length, dugdale-strip-yield-model, small-scale-yielding-check, k-eff-correction, plastic-zone-radius]
  version: 0.1.0
  author: AeroSkills
---

# Crack-Tip Plasticity Correction (structures/materials/crack-tip-plasticity-correction)

Use when the task is the small-scale-yielding correction to a linear-
elastic crack-tip stress field: the classical Irwin single-pass
plastic-zone radius in plane stress and plane strain, the effective
crack length that the correction implies, the corrected stress
intensity K_eff at that effective crack, the exact Dugdale strip-yield
zone for a center crack and its small-scale-yielding asymptote, and the
size-rule verdict that judges when the underlying linear-elastic result
still applies. It pairs with structures/materials/fracture-toughness
for the K_IC frame this correction feeds and with
structures/damage-tolerance/crack-growth and
structures/damage-tolerance/walker-forman-crack-growth, whose rate laws
assume small-scale yielding and use this leaf when that assumption is
in question.

## Domain quick reference

- Elastic stress intensity (shared LEFM input): K = Y*sigma*sqrt(pi*a),
  with sigma the remote stress in MPa, a the crack size in meters, and
  Y the dimensionless geometry factor.
- Irwin plastic-zone radius: plane stress r_p = (1/pi)*(K/sigma_ys)^2;
  plane strain r_p = (1/(3*pi))*(K/sigma_ys)^2, exactly one third of
  the plane-stress zone at equal K and sigma_ys, reflecting the
  triaxial constraint at the crack tip in a thick section.
- Single-pass effective crack: a_eff = a + r_p, with r_p evaluated from
  the uncorrected elastic K (classical Irwin treatment, one pass, no
  iteration).
- Corrected stress intensity: K_eff = Y*sigma*sqrt(pi*a_eff); the
  k-eff-correction ratio is exactly K_eff/K = sqrt(a_eff/a) at fixed
  Y*sigma.
- Dugdale strip-yield zone (exact, infinite-sheet center crack):
  rho = a*(sec(pi*sigma/(2*sigma_0)) - 1), with sigma_0 the strip
  (flow) stress; the zone diverges as sigma approaches sigma_0. Its
  small-scale-yielding asymptote is rho_ssy = (pi/8)*(K/sigma_0)^2, and
  the zone coefficient ratio rho_ssy over the Irwin plane-stress
  coefficient is exactly pi^2/8.
- LEFM-validity size rule (applied-K arithmetic): the elastic result is
  valid when a is at least 2.5*(K/sigma_ys)^2, equivalently when the
  plane-stress zone fraction r_p/a is at or below 1/(2.5*pi), about
  0.1273.
- Units: sigma, sigma_ys, sigma_0 in MPa; a, r_p, rho, a_eff in meters;
  K, K_eff in MPa*sqrt(m). Scope: mode I crack, single crack size, no
  iteration on the Irwin pass; the Dugdale arm applies to a center
  crack with Y = 1 and applied stress below the strip stress.

## Workflow

1. Fix the crack scenario: remote stress sigma, crack size a, geometry
   factor Y, and the material yield strength sigma_ys, and compute the
   uncorrected elastic K with stress_intensity.
2. Evaluate the irwin-plastic-zone radius in both constraint states
   with irwin_plastic_zone, using K from step 1: the plane-stress zone
   and the reduced plane-strain zone.
3. Form the effective-crack-length with effective_crack_length
   (a_eff = a + r_p) and the corrected stress intensity K_eff with
   irwin_effective_correction, which returns k, r_p, a_eff, k_eff and
   the k-eff-correction ratio k_eff_over_k in one call for a chosen
   constraint state.
4. Run the small-scale-yielding-check with sxy_validity at the elastic
   K: it returns the required crack size from the size rule, the
   a-over-required margin, both zone-to-crack fractions and the
   LEFM-validity verdict.
5. For a center crack, apply the dugdale-strip-yield-model with
   dugdale_strip_zone for the exact secant zone, dugdale_ssy_zone for
   its small-scale-yielding asymptote, and
   dugdale_effective_correction for the full effective-crack chain
   (k, rho, a_eff, k_eff, k_eff_over_k) in one call.
6. Compare the exact Dugdale zone against its asymptote to judge how
   far the load sits beyond the small-scale-yielding limit; confirm
   the deterministic checks with the contract test
   scripts/test_crack_tip_plasticity_correction.py.

## Worked example

7075-T6 aluminium, sigma_ys = 503 MPa (an MMPDS-typical published
value, referenced not reproduced).

Case 1: 5 mm edge crack, Y = 1.12, sigma = 180 MPa, a = 0.005 m.
- K = 1.12*180*sqrt(pi*0.005) = 25.266813 MPa*sqrt(m).
- Plane-stress zone r_p = 8.031841e-04 m (0.803 mm); plane-strain zone
  2.677280e-04 m (0.268 mm), exactly one third.
- Plane-stress correction: a_eff = 5.803184 mm, K_eff = 27.220659
  MPa*sqrt(m), k_eff_over_k = 1.077329 (elastic K under-predicts by
  7.7 percent). Plane-strain correction: a_eff = 5.267728 mm, K_eff =
  25.934456 MPa*sqrt(m), k_eff_over_k = 1.026424 (2.6 percent).
- Small-scale-yielding verdict: required_a = 6.308193 mm against the
  5 mm crack, a_over_required = 0.792620, so the verdict is LIMIT
  EXCEEDED: the plane-stress zone fraction 0.160637 exceeds the 0.1273
  bound.
- Companion at sigma = 120 MPa (same crack): K = 16.844542 MPa*sqrt(m),
  k_eff_over_k = 1.035082 (3.5 percent), required_a = 2.803641 mm,
  verdict VALID: the textbook small-correction band.

Case 2: Dugdale strip-yield on a center crack at 90 percent of the flow
stress, Y = 1.0, a = 0.010 m, sigma_0 = 503 MPa, sigma = 452.7 MPa.
- K = 452.7*sqrt(pi*0.010) = 80.238986 MPa*sqrt(m).
- Exact strip-yield zone rho = 5.392453e-02 m (53.925 mm), 5.4 times
  the half-crack; effective crack a_eff = 63.924532 mm, K_eff =
  202.870645 MPa*sqrt(m), k_eff_over_k = 2.528330 (2.53 times the
  elastic K).
- SSY asymptote rho_ssy = 9.992974e-03 m (9.993 mm); the exact zone is
  5.396 times the asymptote, so the asymptote under-predicts badly at
  90 percent of the flow stress and the small-scale-yielding limit is
  far exceeded.

## Verification

- Confirm irwin_plastic_zone at the case 1 K in plane strain equals
  the plane-stress value divided by exactly 3.
- Confirm irwin_effective_correction's k_eff_over_k equals
  sqrt(a_eff/a) to roundoff for both constraint states, and that at
  sigma_ys = 1e9 MPa the ratio collapses to 1 within 1e-12 (the
  small-scale-yielding limit recovery).
- Confirm dugdale_ssy_zone over irwin_plastic_zone (plane stress) at
  equal K equals pi^2/8 exactly to roundoff.
- Confirm dugdale_strip_zone grows without bound as sigma approaches
  sigma_0 (the 0.999*sigma_0 zone exceeds the 0.9*sigma_0 zone by more
  than 10x) and raises ValueError at and above sigma_0.
- Confirm sxy_validity's required_a_m equals 2.5*pi*r_p_ps (plane
  stress) to roundoff, and that the case 1 / case 1b / case 2 verdicts
  match the worked example (False, True, False).
- Confirm every non-positive stress, crack size, geometry factor, yield
  strength, strip stress, and every unrecognized constraint string
  raises ValueError.
- Run the contract test offline: python3
  scripts/test_crack_tip_plasticity_correction.py (34 tests,
  deterministic).

## Pitfalls

- Iterating the Irwin correction: this leaf is the classical
  single-pass treatment, r_p from the uncorrected elastic K, a_eff =
  a + r_p once. An iterative effective-crack loop is a stated
  extension, not this contract, and will not match the worked-example
  values above.
- Reading the plane-stress zone where the section is thick: the
  plane-strain zone is exactly one third of the plane-stress zone at
  equal K and sigma_ys; using the plane-stress value in a
  thick-section, constrained geometry overstates the correction by 3x.
- Treating the Dugdale small-scale-yielding asymptote as exact near the
  flow stress: rho_ssy under-predicts the exact secant zone by a
  growing factor as sigma approaches sigma_0 (5.4x at 90 percent of
  the flow stress in case 2); use dugdale_strip_zone directly once the
  load leaves the small-scale-yielding band.
- Confusing this leaf's size-rule arithmetic with the K_IC test-
  specimen validity check (structures/materials/fracture-toughness):
  the 2.5*(K/sigma_ys)^2 form here judges whether an applied-K elastic
  result is trustworthy at a given crack size and load; the sibling
  leaf uses the same arithmetic on K_IC and specimen thickness to judge
  whether a fracture-toughness test is a valid plane-strain
  measurement. They share arithmetic, not a claim.
- Feeding the Dugdale strip stress the yield strength without checking
  the model: the strip (flow) stress sigma_0 is typically taken near
  the yield strength but is a model choice; dugdale_strip_zone raises
  ValueError once sigma reaches or exceeds sigma_0, since the zone is
  undefined at and beyond full-strip yield.
- Reporting Y*sigma*sqrt(pi*a) as the delivered result: this leaf uses
  the elastic K only as the input to the zone and effective-crack
  chain; the rate-law leaves (crack-growth, walker-forman-crack-growth)
  own the Paris-law and stress-ratio projections that consume K
  directly.

## Related leaves

- structures/materials/fracture-toughness: owns the K_IC frame, the
  K >= K_IC failure criterion and the ASTM E399 test-specimen
  plane-strain validity check; this leaf reuses only the applied-K
  small-scale-yielding size rule as a distinct verdict.
- structures/damage-tolerance/crack-growth: the R = 0 Paris-law growth
  rate that assumes linear-elastic small-scale-yielding conditions this
  leaf's verdict gates.
- structures/damage-tolerance/walker-forman-crack-growth: the stress-
  ratio and K_c-limited growth rates that carry the same small-scale-
  yielding scope this leaf checks.
- structures/materials/ramberg-osgood: the elastic-plastic stress-
  strain curve for the material, a separate constitutive model from the
  crack-tip zone geometry here.

## Behavior contract (gate 3)

The contract test scripts/test_crack_tip_plasticity_correction.py (34
methods, stdlib unittest, offline, deterministic) verifies: the case 1,
case 1b and case 2 worked-example values for stress_intensity,
irwin_plastic_zone, effective_crack_length, irwin_effective_correction,
dugdale_strip_zone, dugdale_ssy_zone, dugdale_effective_correction and
sxy_validity within tolerance; the plane-strain-over-plane-stress one-
third identity and the Dugdale SSY-over-Irwin plane-stress zone
coefficient pi^2/8 to roundoff; the k-eff-correction sqrt(a_eff/a)
identity on both chains; the small-scale-yielding limit recovery at
sigma_ys = 1e9 MPa; the size-rule identity required_a_m = 2.5*pi*r_p_ps;
the Dugdale zone divergence guard and asymptote collapse at 1 percent of
the flow stress; the monotonic correction growth with load ratio; and
ValueError rejection of every non-physical input across the module. The
test passes under both /usr/bin/python3 and the pyenv 3.13 interpreter;
no exact-float equality is asserted on computed sums.

## Compliance

- Standards referenced, not reproduced: MMPDS is the source of the
  7075-T6 yield strength used in the worked example; the Irwin and
  Dugdale plastic-zone relations above are standard fracture-mechanics
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
