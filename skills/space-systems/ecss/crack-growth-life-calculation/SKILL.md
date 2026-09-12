---
name: crack-growth-life-calculation
description: "Use when calculate crack growth life, margins, and scatter factors for a fracture-critical structural component under ECSS-E-ST-32-01C §7.2.8: determine the critical crack size from fracture toughness and applied stress, integrate the crack growth rate law (Paris, Walker, or Forman) from the initial assumed flaw to the critical size, apply a life scatter factor (x3 with material-specific test data, x5 with handbook data only), and compute the margin of safety on life against the required service life. Trigger: ecss, e-st-32-structures-scope, crack-growth, walker-forman-crack-growth, fracture-mechanics, paris-law, crack-growth-life, scatter-factor, fracture-toughness, stress-intensity."
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
  tags: [ecss, e-st-32-structures-scope, crack-growth, walker-forman-crack-growth, fracture-mechanics, paris-law, scatter-factor, fracture-toughness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Crack Growth Life Calculation (space-systems/ecss/crack-growth-life-calculation)

Use when the task is to calculate the crack growth life of a fracture-critical
structural component per ECSS-E-ST-32-01C §7.2.8: propagate an assumed initial
flaw to the critical crack size, apply the required scatter factor, and verify
the resulting design life against the service requirement.

## Domain quick reference

- Crack growth life is the number of load cycles needed to propagate an assumed
  initial flaw of half-length a_i to the critical half-length a_crit, where
  a_crit is the size at which the applied stress intensity factor K equals the
  material fracture toughness K_Ic.  The stress intensity factor range is
  ΔK = β × Δσ × √(π × a), where β is the geometry correction factor.
- Three crack growth rate laws are in common use under §7.2.8:
  - **Paris law**: da/dN = C × ΔK^m — power law; no stress-ratio dependence;
    admits a closed-form life integral (logarithmic for m = 2, power-law
    otherwise).
  - **Walker law**: da/dN = C × (ΔK / (1−R)^(1−γ))^n — extends Paris for
    mean-stress effects via the stress ratio R = K_min / K_max; numerically
    integrated.
  - **Forman law**: da/dN = C × ΔK^n / ((1−R)×K_c − ΔK) — captures the
    accelerating growth rate as ΔK approaches the fracture toughness limit;
    numerically integrated; denominator becomes zero at the fracture limit and
    must not be evaluated past a_crit.
- Scatter factors account for variability in crack growth rate data.
  Per §7.2.8: apply **x3 on life** when material-specific crack growth rate
  test data underpins the law coefficients; apply **x5 on life** when only
  handbook or generic data is used.  The design life is the computed life
  divided by the scatter factor: N_design = N_computed / SF.
- Margin of safety on life: MS_life = N_design / N_required − 1.
  A non-negative value is required; a negative value is a fracture-control
  finding that must be resolved before the component can be accepted.

## Workflow

1. Obtain the initial crack size a_i from the fracture control plan — either
   the NDE detection threshold or the assumed initial flaw size defined per
   ECSS-E-ST-32-01C §6.  Confirm a_i > 0.
2. Compute the critical crack size from material fracture toughness K_Ic,
   geometry factor β, and maximum applied stress σ_max:
   a_crit = (K_Ic / (β × σ_max))² / π.
   If a_i ≥ a_crit, the structure is already at or beyond its critical state;
   life assessment cannot be completed and the design must be reworked.
3. Select the crack growth rate law (Paris, Walker, or Forman) based on
   available material data.  Collect the corresponding coefficients:
   C and m for Paris; C, n, γ, and R for Walker; C, n, R, and K_c for Forman.
4. Integrate the crack growth rate law from a_i to a_crit to obtain the
   computed life N_computed:
   - Paris: use the analytical closed form — logarithmic for m = 2, power-law
     otherwise — treating m = 2 as an exact special case to avoid division by
     zero in the general formula.
   - Walker / Forman: use midpoint-rule numerical integration with sufficient
     steps (≥ 1000 by default) for accuracy; verify the Forman denominator
     remains positive throughout.
5. Determine the scatter factor: SF = 3 if material-specific test data supports
   the law coefficients; SF = 5 if handbook or generic data is used.
6. Apply the scatter factor: N_design = N_computed / SF.
7. Compute the life margin: MS_life = N_design / N_required − 1.
   Report whether the component passes (MS_life ≥ 0) or fails (MS_life < 0),
   alongside a_crit, N_computed, SF, N_design, and MS_life.

## Pitfalls

- Applying scatter to the crack growth rate rather than the life — §7.2.8
  specifies a factor on life (divide computed life by SF), not a multiplier on
  the growth rate.
- Using a flat scatter factor without checking data quality — the x3 / x5
  selection is a mandatory §7.2.8 requirement; the wrong choice can cause a
  non-compliant component to appear safe.
- Omitting the β geometry factor — treating every geometry as a flat plate
  (β = 1) is nonconservative; β must reflect the actual crack geometry and
  boundary conditions.
- Evaluating the Forman law at or past a_crit — the denominator (1−R)×K_c −
  ΔK approaches zero as the crack approaches the fracture limit; integration
  must stop at a_crit, which is itself the valid upper bound.
- Using the general Paris formula when m = 2 — the exponent (2−m)/2 is zero,
  making the power-law closed form singular; the logarithmic form must be
  used for m = 2.
- Failing to verify a_i < a_crit before integrating — if the initial flaw is
  already critical, no amount of scatter factor adjustment can recover the
  assessment.

## Behavior contract (gate 3)

The critical-crack-size computation, Paris/Walker/Forman integration, scatter
selection, scatter application, and life-margin logic are exercised by the
gate 3 contract test:
scripts/test_crack_growth_life_calculation.py against
scripts/crack_growth_life_calculation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_crack_growth_life_calculation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
