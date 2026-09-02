---
name: design-of-experiments
description: "Use when you must plan a design of experiments (DOE) for an aircraft or spacecraft conceptual design study and analyze the runs: build the coded design matrix with a full factorial, a fractional factorial two-level half-fraction with its defining relation and alias structure, a seeded latin hypercube sample, or a central composite design around the baseline point, then compute the per-factor main effects, the two-factor interaction effects, and the factor screening ranking. Produces the coded design matrix with its run count and the ranked main effects and interaction effects that gate which planform, loading, or configuration factors to carry into multidisciplinary optimization. Trigger: design of experiments, DOE, factorial design, fractional factorial, latin hypercube, central composite, main effects, interaction effects, factor screening, design space exploration."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: mdo
  tags: [design-of-experiments, doe, factorial-design, fractional-factorial, latin-hypercube, central-composite, main-effects, interaction-effects, factor-screening, design-space-exploration]
  version: 0.1.0
  author: Aero Agent Skills
---

# Design of Experiments (vehicle-design/mdo/design-of-experiments)

Use when the task is design of experiments (DOE) for an aircraft or
spacecraft conceptual design study: planning a small structured set of
simulation runs or wind tunnel experiments that maps the design space,
screens the factors, and estimates their effects before optimization.
This leaf builds coded design matrices in pure Python stdlib and
analyzes the responses. It pairs with
vehicle-design/mdo/multidisciplinary-optimization, which consumes the
screened factor set and the baseline point that DOE identifies.

## Domain quick reference

- Coded levels: a two-level factor codes low as -1 and high as +1, so
  contrasts are direct; a factor with m >= 3 settings enumerates the
  levels 0 .. m-1; latin hypercube samples are continuous in [0, 1]^k.
- Full factorial: every combination of the per-factor level counts,
  2^k runs for k two-level factors. Supported up to k = 7 (128 runs).
- Half-fraction 2^(k-1), k = 4..7: built from one defining relation
  word, default I = ABC...K (the first k letters), so the principal
  fraction satisfies product over the word letters = +1 on every run.
  The default word length is k, resolution k. At k = 4 the defining
  relation I = ABCD aliases A with BCD and AB with CD, so all main
  effects stay clear of the two-factor interactions at half the runs
  of the full design.
- Latin hypercube: n samples over k factors, each factor column a
  random permutation of the n strata drawn from a fixed seed, each
  sample at its stratum midpoint (perm + 0.5) / n. Every factor covers
  its strata exactly once and all rows are distinct.
- Central composite: 2^k factorial runs plus 2k axial runs at +-alpha
  on one axis at a time plus center runs at the origin; run count is
  2^k + 2k + center. Rotatable alpha = (2^k)^(1/4) is the default
  ('axial'); alpha = 'faced' puts the axial runs on the cube faces.
- Main effect: mean response at the high level minus the mean at the
  low level, twice the linear regression coefficient of that factor.
  Interaction effect: the same contrast on the product x_i * x_j.
  On y = 2*A + 1.5*B + A*B with A, B coded -1/+1, the main effect of
  A is 4.0, of B is 3.0, and the A-by-B interaction effect is 2.0.
- FAR-25 and CS-25 set the certification context (the design point and
  the loads margins that the screened factors feed); the DOE methods
  are standard statistical design methodology, summary only.

## Workflow

1. Choose the factors and their ranges from the conceptual study
   (wing planform, loading, thrust, configuration settings) and code
   each factor to its low and high level.
2. Screen with full_factorial or fractional_factorial_2k when the run
   budget is tight: a 2^(k-1) half-fraction for k = 4..7 halves the
   runs and keeps the main effects clear of the two-factor
   interactions; verify the principal fraction with
   check_principal_fraction.
3. When the factors are continuous and the budget still exceeds the
   factorial size, spread the runs through the design space with
   latin_hypercube at a fixed seed for a reproducible sample.
4. Around a chosen baseline design point, refine with
   central_composite to fit curvature: factorial plus axial plus
   center runs, rotatable alpha by default.
5. Run the simulation or experiment at every row of the design and
   collect the responses in the same order.
6. Rank the factors with analyze_main_effects and check the pairwise
   coupling with analyze_interactions, then carry the top-ranked
   factors and the baseline point into the MDO loop.
7. Assemble any design through build_design_matrix, which returns the
   coded matrix together with the run count for the budget check.

## Worked example

Screening a wing planform study with two factors, aspect ratio A and
sweep B, each at two levels coded -1/+1. The full factorial has four
runs: (-1, -1), (-1, +1), (+1, -1), (+1, +1). Let the aerodynamic
response follow y = 2*A + 1.5*B + A*B, giving y = -2.5, -1.5, -0.5,
4.5. analyze_main_effects returns the A effect 4.0 (high mean 2.0
minus low mean -2.0), the B effect 3.0, and the ranking ["A", "B"];
analyze_interactions returns the A-by-B effect 2.0. The coded levels
and these exact numbers are asserted in the contract test.

For a space-filling check, latin_hypercube(10, 2, seed=5) returns 10
distinct rows in [0, 1]^2 whose first row is (0.25, 0.45), and each
column covers the 10 strata exactly once. For refinement around the
baseline, central_composite(2, center=1) returns 2^2 + 4 + 1 = 9
runs: the four factorial corners, the axial points at
+-sqrt(2) = 1.4142 on each axis, and one center run at (0, 0).

## Verification

- Deterministic: all random draws come from random.Random with a
  fixed integer seed, so every matrix is reproducible run to run.
- Rejection: ValueError on empty level lists or level counts below 2,
  k outside the supported windows, fractions other than 1 or 2, bad
  generator words, n_samples below 2, k_factors below 1, center runs
  below 1, non-positive alpha, non-two-level analysis designs, and
  response counts that do not match the run count.
- The exact worked-example numbers above are asserted in
  scripts/test_doe_logic.py together with the principal-fraction
  identity, the latin hypercube stratification, the central composite
  run count formula, and every ValueError case.

## Related leaves

- vehicle-design/mdo/multidisciplinary-optimization: consumes the
  screened factor set, the ranked effects, and the baseline point that
  this leaf produces; DOE maps the design space before the optimizer
  closes the coupling loop.
- vehicle-design/cost-estimation/parametric-cost: the design point
  screened here feeds the cost CERs that rank the configurations.
- cross-cutting/numerics/monte-carlo-sampling: draws many random
  samples to estimate output distributions, where this leaf plans few
  structured runs to estimate factor effects.
- cross-cutting/numerics/uncertainty-propagation: propagates input
  uncertainties through the analysis once the influential factors are
  known.

## Contract test

Run: python3 skills/vehicle-design/mdo/design-of-experiments/scripts/test_doe_logic.py
The stdlib unittest contract covers 33 checks: full factorial coding
and run counts, half-fraction construction with the principal-fraction
identity for k = 4..7, latin hypercube uniqueness and stratification
at fixed seeds, central composite layout and run count formula,
the worked-example main effects and interaction effects, dispatch
through build_design_matrix, and ValueError rejection of invalid
inputs. Offline, deterministic, exit 0 in under a second.

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the DOE methods
  (factorial, fractional factorial, latin hypercube, central
  composite, effect estimation) are common statistical design
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
