---
name: lqr-design
description: "Use when you must design an LQR state-feedback gain matrix for a scalar-input two-state system such as spacecraft attitude control: solve the algebraic Riccati equation for the cost weights, compute the gain matrix, verify closed-loop stability of the regulated system, and assess the Q over R weighting trade. Produces the Riccati solution, the gain vector, and the stability verdict that feed the control-law design. Trigger: lqr, linear quadratic regulator, riccati equation, gain matrix, state feedback, closed loop stability, control effort, spacecraft attitude control."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: optimal-control
  tags: [lqr-design, linear-quadratic-regulator, riccati, gain-matrix, state-feedback, closed-loop-stability, control-effort, spacecraft-attitude-control]
  version: 0.1.0
  author: AeroSkills
---

# LQR Design (gnc-autonomy/optimal-control/lqr-design)

Use when the task is LQR state-feedback design for a scalar-input
two-state system: solving the Riccati equation, computing the gain
matrix, and verifying closed-loop stability.

## Domain quick reference

- LQR minimizes the quadratic cost J = integral(x'Qx + u'Ru) over the
  linear system x' = A x + B u; the optimal state feedback is u = -K x.
- The gain is K = R^-1 B' P with P the stabilizing solution of the
  algebraic Riccati equation A'P + PA - P B R^-1 B' P + Q = 0.
- For the canonical scalar-input two-state form A = [[0,1],[0,-a]],
  B = [0,1] (a damped double integrator), the Riccati equation reduces
  to a small closed-form system solved directly from q1, q2, r, and a.
- A 2x2 closed-loop matrix A - B K is stable exactly when its trace is
  negative and its determinant positive; the pole pair follows from the
  quadratic formula.
- Q penalizes state error and R penalizes control effort; their ratio
  sets the gain magnitude and the settling speed of the regulated
  system.
- ARP4754A (reference-only) frames development assurance for aircraft
  systems; the Riccati mathematics here is common control-theory
  knowledge.

## Workflow

1. Put the plant in canonical form: A = [[0,1],[0,-a]] with damping
   a >= 0, input B = [0,1], and pick cost weights Q = diag(q1, q2),
   R = r in one consistent SI convention (for an attitude plant: q1 in
   1/rad^2, q2 in 1/(rad/s)^2, r in 1/(N m)^2).
2. Solve the Riccati equation with riccati_gain for the symmetric
   matrix P.
3. Compute the gain with gain_matrix: K = R^-1 B' P, returned as
   [k1, k2].
4. Verify the closed loop with closed_loop_stable: eigenvalues of
   A - B K, reported as a stability verdict plus the pole pair.
5. Assess the weights with cost_weight_guide and re-tune q1, q2, r
   when the gains are too aggressive or too weak.

## Pitfalls

- Iterating the Riccati equation with the policy-iteration map
  P <- A'P + PA - P B R^-1 B' P + Q; that map is not a contraction and
  need not converge. Solve the ARE directly instead.
- Applying the closed form outside the canonical family: a general A
  and B need a general Riccati solver, not this leaf's equations.
- Mixing weight conventions (rad with deg, torque in N m with weights
  scaled for a different unit); the gain and the closed-loop poles
  change with the convention.
- Checking stability from the determinant alone; a 2x2 closed loop
  needs trace < 0 AND determinant > 0.
- Accepting negative q or nonpositive r; the module raises ValueError
  on impossible weights.

## Behavior contract (gate 3)

The Riccati solve, gain computation, closed-loop stability verdict,
and cost-weight guidance are exercised by the gate 3 contract test:
scripts/test_lqr_design_logic.py against scripts/lqr_design_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_lqr_design_logic.py

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.
