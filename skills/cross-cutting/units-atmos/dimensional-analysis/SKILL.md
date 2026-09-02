---
name: dimensional-analysis
description: "Use when you must run dimensional analysis on an engineering relation: check whether equation terms are dimensionally homogeneous, apply the Buckingham Pi theorem to form the dimensionless Pi groups, compute the Reynolds number and Mach number for a wind tunnel model, the required model speed to match full-scale Reynolds number under dynamic similarity, the Froude number, and the full-scale force from a model measurement. Produces the homogeneity verdict, the Pi group set, and the scaled test conditions. Trigger: dimensional analysis, buckingham pi, pi groups, dimensionless, reynolds number, mach number, froude number, dynamic similarity, wind tunnel model, model scale, similarity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: sep-2640
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: units-atmos
  tags: [dimensional-analysis, buckingham-pi, pi-groups, dimensionless-numbers, homogeneity-check, reynolds-number, mach-number, froude-number, dynamic-similarity, wind-tunnel-model, model-scale, similarity-scaling]
  version: 0.1.0
  author: Aero Agent Skills
---

# Dimensional Analysis (cross-cutting/units-atmos/dimensional-analysis)

Use when the task is dimensional analysis of an engineering relation:
the dimensional homogeneity of an equation, the dimensionless groups
of a problem from the Buckingham Pi theorem, the similarity numbers
(Reynolds, Mach, Froude) at a test or flight condition, and the
scaling of wind tunnel model test results to full scale under dynamic
similarity.

## Domain quick reference

Dimensional analysis works with dimension exponent vectors over the
SI base dimensions, in the order mass M, length L, time T, temperature
Theta, electric current I, amount of substance N, luminous intensity J.
Most aerospace relations only need M, L, T.

- Homogeneity check: every term of a valid equation carries the same
  dimension vector. Bernoulli's equation terms p, 0.5 rho v^2, and
  rho g h all carry M L^-1 T^-2, so check_homogeneity returns True;
  a term such as rho v (M L^-2 T^-1) breaks the equation. Worked:
  check_homogeneity([("p", (1, -1, -2)), ("0.5 rho v^2", (1, -1, -2)),
  ("rho g h", (1, -1, -2))]) returns (True, (1.0, -1.0, -2.0)).
- Buckingham Pi theorem: with n variables and a dimension matrix of
  rank r, exactly n - r independent dimensionless groups exist. The
  rank is the number of dimensionally independent variables, found by
  Gaussian elimination of the dimension matrix; each Pi group is a
  null-space vector of that matrix. Worked: sphere drag with F, D,
  rho, V, mu over M, L, T (5 variables, rank 3) gives n_pi = 2, and
  the group set spans Re = rho V D / mu (exponents 0, 1, 1, 1, -1)
  and the drag coefficient F / (rho V^2 D^2) (exponents 1, -2, -1,
  -2, 0).
- Similarity numbers (SI inputs, all positive): Reynolds
  Re = rho v l / mu with rho in kg/m3, v in m/s, l in m, mu in Pa.s;
  Mach M = v / a; Froude Fr = v / sqrt(g l) for free-surface flows.
  Worked: rho 1.225 kg/m3, v 80 m/s, chord 2.0 m, mu 1.781e-5 Pa.s
  gives Re = 1.10e7; the same v with a = 340.3 m/s gives M = 0.235;
  v 5 m/s over l 2.5 m gives Fr = 1.01.
- Dynamic similarity: matching a dimensionless group between model and
  full scale keeps the corresponding physical effect proportional.
  For Reynolds matching, V_model = V_proto * (L_proto / L_model) *
  (nu_model / nu_proto). Worked: a 1:10 model (scale_ratio 10) in the
  same fluid needs V_model = 10 * 80 = 800 m/s to match a full-scale
  80 m/s condition, which is usually impractical; the same fluid and
  Mach constraint force partial similarity, so tunnels raise density
  (pressurized or cryogenic operation) to raise Re at acceptable
  speed. Force scaling with the same dimensionless force coefficient:
  F_proto = F_model * (L_proto / L_model)^2 * (rho_proto / rho_model)
  * (V_proto / V_model)^2. Worked: a 12.5 N model drag at Re-matched
  conditions in the same fluid scales to F_proto = 12.5 * 100 * 1.0 *
  (1/10)^2 = 12.5 N full scale.

## Workflow

1. Name the physical relation and list the variables with their
   dimension exponent vectors over the base dims in use (usually
   M, L, T).
2. Run check_homogeneity(terms) on the equation terms; a False
   verdict means a term has the wrong dimensions, fix the equation
   before any further computation.
3. Build the variables dict and call buckingham_pi(variables,
   base_dims=("M", "L", "T")); read rank, n_pi, and the pi_groups,
   then name each group from its exponents (Re, a drag coefficient,
   a lift coefficient, and so on).
4. Compute the similarity numbers for the model and full-scale
   conditions with reynolds_number(rho, v, l, mu), mach_number(v,
   speed_of_sound), and froude_number(v, l, g) where relevant.
5. For a model test, find the required model speed with
   required_model_speed(scale_ratio, prototype_speed,
   kinematic_viscosity_ratio) and check it against the tunnel
   capability; then convert a measured model load to full scale with
   force_scaling(force_model, scale_ratio, density_ratio,
   velocity_ratio).
6. Record the Pi groups and the matched (and unmatched) similarity
   parameters in the test plan; a result is only similarity-valid for
   the parameters that were actually matched.

## Pitfalls

- Routing to unit-conversion instead: converting a value between unit
  systems (psi to Pa, kt to m/s, speed to Mach) routes to
  cross-cutting/units-atmos/unit-conversion; that leaf never checks
  dimensional consistency and never forms Pi groups. If the question
  is "is my equation homogeneous" or "what are the dimensionless
  groups", route here.
- Routing to temperature-conversion or isa-atmosphere: scale
  conversion (K, C, F, R) is temperature-conversion; atmosphere
  properties (rho, T, mu, speed of sound) come from isa-atmosphere.
  This leaf consumes those values but does not produce them.
- Routing to the numerics leaves: regression, integration, root
  finding, and the other numerics leaves operate on numbers without
  tracking dimensions; a pure data-fitting task routes to
  least-squares-regression, not here.
- Repeating variables that are not dimensionally independent: the
  repeating set must span the rank of the dimension matrix, otherwise
  the Pi groups are not independent and the theorem undercounts.
- Wrong characteristic length: Re uses the length scale of the flow
  (chord for a wing, diameter for a sphere); swapping them changes Re
  by the length ratio and mis-states the flow regime.
- Sign errors in group exponents: mu enters Re with exponent -1;
  a flipped sign makes the group dimensionful.
- Matching Re alone in compressible flow: when Mach is significant
  both Re and M must match, which one fluid cannot usually satisfy
  with a geometric scale model; state which parameter is unmatched.
- Reversing the scale ratio: scale_ratio is L_proto / L_model, so a
  1:10 model has scale_ratio 10, not 0.1.
- Assuming same-fluid force scaling: the velocity and density ratios
  must be carried explicitly; the 12.5 N result above is special to
  Re-matched, same-fluid tests.

## Behavior contract (gate 3)

The homogeneity check, Buckingham Pi group formation, similarity
numbers, and dynamic similarity scaling are exercised by the gate 3
contract test: scripts/test_dimensional_analysis.py against
scripts/dimensional_analysis_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_dimensional_analysis.py

## Compliance

- Standards referenced, not reproduced: SEP-2640 frames the skill
  packaging and delivery practice only. Dimensional analysis itself
  is fundamental mathematics (the Buckingham Pi theorem, similarity
  parameters) and is not governed by a certification standard; the
  worked cases are textbook engineering calculations, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
