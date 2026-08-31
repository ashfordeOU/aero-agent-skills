---
name: state-space-analysis
description: "Use when you must analyze a linear time-invariant system in state space: form the controllability and observability matrices, decide controllability and observability from their ranks, compute the 2x2 eigenvalue stability verdict, build the state transition matrix by the Cayley-Hamilton method, and produce the controller or observer canonical forms. Applies to flight control and GNC state-space models written as x_dot = A x + B u with output y = C x. Produces the controllability and observability verdicts, the stability verdict, the transition matrix at a time t, and the canonical form realizations that feed control law design. Trigger: state space, controllability, observability, state transition matrix, eigenvalues, stability, canonical form, linear system, A matrix, B matrix, C matrix."
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
  subdomain: control
  tags: [state-space-analysis, state-space, controllability, observability, state-transition-matrix, eigenvalues, stability, canonical-form, linear-systems]
  version: 0.1.0
  author: AeroSkills
---

# State Space Analysis (gnc-autonomy/control/state-space-analysis)

Use when the task is analyzing a linear time-invariant state space
model: controllability and observability checks, stability from the
A matrix, the state transition matrix, and canonical form
realizations.

## Domain quick reference

- A linear time-invariant system is x_dot = A x + B u, y = C x with
  n states, m inputs, p outputs.
- Controllability: the pair (A, B) is controllable when the
  controllability matrix [B, AB, ..., A^(n-1)B] has full row rank n.
- Observability: the pair (A, C) is observable when the
  observability matrix [C; CA; ...; CA^(n-1)] has full column rank n.
- Stability: a continuous-time system is stable when every eigenvalue
  of A has a strictly negative real part.
- State transition matrix: Phi(t) = e^(A t) propagates the state as
  x(t) = Phi(t) x(0); for 2x2 systems the Cayley-Hamilton expansion
  gives Phi(t) = alpha0(t) I + alpha1(t) A.
- Controller canonical form realizes the transfer function denominator
  coefficients in the last row of A; observer canonical form places
  them in the last column. Both are similarity transforms of (A, B, C).

## Workflow

1. Check the matrix dimensions (square A, conformable B and C).
2. Compute the controllability and observability matrices and their
   ranks; decide controllability and observability.
3. Compute the eigenvalues of A (2x2 closed form) and the stability
   verdict.
4. Build the state transition matrix at the requested time by the
   Cayley-Hamilton expansion for a 2x2 system.
5. Produce the controller and observer canonical form realizations.
6. Optionally assemble the full analysis report with all verdicts.

## Pitfalls

- Declaring controllability from a matrix whose rank was computed with
  a too-loose tolerance (rank is a numerical decision).
- A transition matrix that does not reduce to I at t = 0.
- Mixing the controller and observer canonical form conventions
  (denominator row vs column placement).
- Applying a continuous-time stability test to a discrete system
  without first mapping the eigenvalues to the unit circle.

## Behavior contract (gate 3)

The state space logic is exercised by the gate 3 contract test:
scripts/test_state_space.py against scripts/state_space_logic.py
(stdlib unittest, offline). Run:

    python3 scripts/test_state_space.py
