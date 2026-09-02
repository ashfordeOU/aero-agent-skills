---
name: observer-design
description: "Use when you must design a full-order Luenberger state observer for a linear time-invariant system whose states are not all directly measurable: build the observability matrix and check observability, compute the estimator gain matrix by pole placement with the Ackermann formula so the observer error dynamics eigenvalues sit at the desired locations, verify the error dynamics are Hurwitz stable with the characteristic polynomial, confirm the separation principle so observer poles and controller poles combine by union in the closed loop, and size the convergence with the settling time. Produces the observer gain, the error dynamics matrix and characteristic polynomial, the stability verdict, and the separation check that gate an output feedback design. Trigger: observer design, luenberger, estimator gain, pole placement, separation principle, error dynamics, observability, ackermann, settling time, output feedback."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
  - id: do-178c
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: control
  tags: [observer, luenberger, estimator, ackermann, pole, placement, unmeasured, settling, hurwitz, feedback, principle, error, observer-design, full-order-observer, luenberger-observer, estimator-gain, separation-principle, error-dynamics, routh-hurwitz]
  version: 0.1.0
  author: Aero Agent Skills
---

# Observer Design (gnc-autonomy/control/observer-design)

Use when the task is deterministic full-order state estimation for
feedback control: the Luenberger observer gain, the placement of the
observer error dynamics eigenvalues, the stability of those error
dynamics, and the separation principle that joins them with a
controller gain.

## Domain quick reference

- Plant: the continuous-time linear time-invariant system
  x_dot = A x + B u with measured output y = C x, x in R^n. The
  full-order observer is
  x_hat_dot = A x_hat + B u + L (y - C x_hat) with the estimation
  error e = x - x_hat obeying e_dot = (A - L C) e.
- Observability: the observability matrix
  O = [C; C A; ...; C A^(n-1)] has full column rank n exactly when the
  pair (A, C) is observable; a rank-deficient O means some state
  direction never reaches the output and no observer can reconstruct
  it.
- Ackermann formula: with the desired characteristic polynomial
  phi(s) = prod_i (s - p_i) built from the observer poles p_i, the
  estimator gain is L = phi(A) O^{-1} e_n, where e_n is the last unit
  vector and O must be square (single measured output row). The error
  dynamics eigenvalues are then exactly the chosen p_i.
- Worked, double integrator: A = [[0, 1], [0, 0]] (position, velocity)
  with C = [[1, 0]] (position measured only). O = I2, so the pair is
  observable. Choosing observer poles -4 and -5 rad/s gives
  phi(s) = s^2 + 9s + 20 and L = [9, 20]; then
  A - L C = [[-9, 1], [-20, 0]] with characteristic polynomial
  s^2 + 9s + 20, so the error decays as e^(-4t) and e^(-5t).
- Complex poles: choosing -2 +/- 3j rad/s gives phi(s) = s^2 + 4s + 13
  and L = [4, 13] on the same plant; the gain stays real because the
  poles form a conjugate pair.
- Worked, three states: A = [[-1, 0, 1], [0, -2, 0], [0, 1, -3]] with
  C = [[1, 0, 0]] and poles -10, -11, -12 rad/s gives L = [27, 720,
  216] and error dynamics polynomial
  s^3 + 33 s^2 + 362 s + 1320 = (s+10)(s+11)(s+12), stable by the
  Routh array.
- Settling time: for the 2% band t_s = 4 / sigma, where
  sigma = min_i |Re(p_i)| is the distance of the slowest error pole
  from the imaginary axis. The worked double integrator gives
  t_s = 1.0 s; the complex pair -2 +/- 3j gives t_s = 2.0 s.
- Separation principle: with output feedback u = -K x_hat the closed
  loop is x_dot = (A - B K) x + B K e, e_dot = (A - L C) e, a block
  upper triangular system whose characteristic polynomial factors into
  the controller polynomial det(sI - (A - B K)) and the observer
  polynomial det(sI - (A - L C)). Controller and observer poles can be
  designed independently. Worked: K = [1, 1] on the double integrator
  gives controller polynomial s^2 + s + 1 and observer polynomial
  s^2 + 9s + 20, whose product s^4 + 10 s^3 + 30 s^2 + 29 s + 20 is
  the closed-loop polynomial.
- Rule of thumb: place observer poles 4 to 10 times faster than the
  controller poles (in real part) so the estimates settle before the
  controlled response, without amplifying measurement noise too much.
- Characteristic polynomial: computed by the Faddeev-LeVerrier
  algorithm from the matrix trace recursion; Hurwitz verdict by the
  Routh array, which needs every first-column entry strictly positive
  (marginal roots on the imaginary axis are not stable).
- Units: SI. Pole locations in rad/s, settling time in seconds.

## Workflow

1. Write the state-space model A, B, C of the plant with the state x,
   the input u, and the measured output y; the Ackermann gain needs a
   single output row, C is 1 x n.
2. Compute observability_matrix(A, C) and confirm is_observable(A, C)
   returns True; a rank-deficient O means the observer task is
   ill-posed for this measurement set.
3. Choose the observer poles p_i: strictly negative real parts, real
   values or conjugate pairs, typically 4 to 10 times faster than the
   controller poles.
4. Compute the estimator gain with observer_gain_ackermann(A, C,
   poles); the function raises ValueError when the system is not
   observable, the pole count is wrong, a pole is unstable, or a
   non-conjugate complex pole set would give a complex gain.
5. Verify the design with error_dynamics(A, C, L): the returned error
   matrix A - L C, its characteristic polynomial, and the Hurwitz
   stability verdict; the polynomial coefficients must match the
   desired phi(s).
6. Size the convergence with settling_time(poles); 4 / sigma seconds
   to reach the 2% error band.
7. When a controller gain K exists (for example from lqr-design or
   root-locus-design), run separation_closed_loop(A, B, C, K, L) and
   confirm factorizes is True, so the closed-loop polynomial is the
   product of the controller and observer polynomials.
8. Implement the observer as flight software: x_hat_dot integration
   with the injected output error L (y - C x_hat), u = -K x_hat as the
   feedback path.

## Pitfalls

- Routing stochastic estimation here: Kalman gain, innovation, process
  and measurement noise covariances, and the covariance recursion
  belong to gnc-autonomy/navigation/kalman-filter-design; observer
  design is deterministic pole placement with no noise statistics.
- Routing analysis here: controllability and observability verdicts,
  the state transition matrix, eigenvalue stability, and canonical
  forms belong to gnc-autonomy/control/state-space-analysis; this leaf
  synthesizes the estimator gain that the verdict enables, it does not
  repeat the rank tests as an end in themselves.
- Routing controller gain design here: the feedback gain K from
  quadratic cost belongs to gnc-autonomy/optimal-control/lqr-design,
  and pole-placement controller design belongs to
  gnc-autonomy/control/root-locus-design; this leaf designs the
  estimator side L, and u = -K x_hat combines both through the
  separation principle.
- Forgetting the sign convention: the gain enters the observer as
  +L (y - C x_hat) and the error dynamics are A - L C; a sign flip in
  either place moves the error poles into the right half plane.
- Designing unstable or marginal observer poles: the error dynamics
  must be strictly Hurwitz, poles on the imaginary axis never decay.
- Making the observer too fast: 100x faster poles amplify measurement
  noise through L; 4 to 10x the controller bandwidth is the practical
  band.
- Applying Ackermann to a multi-output measurement: the formula needs
  a square observability matrix, that is a single measured output row;
  multi-output estimation needs a different gain synthesis.
- Reading the Routh array wrong: all polynomial coefficients must be
  positive and every first-column entry strictly positive; a zero
  first-column entry means marginal or unstable roots, not a pass.
- Ignoring observability: placing poles on an unobservable pair is
  silently ineffective for the unobservable state direction, check
  rank(O) = n first.
- Confusing settling time with the time constant: t_s = 4 / sigma is
  the 2% band, the time constant is 1 / sigma.

## Behavior contract (gate 3)

The observability matrix and rank verdict, the Ackermann estimator
gain, the characteristic polynomial, the Hurwitz stability verdict,
the separation principle factorization, and the settling time are
exercised by the gate 3 contract test:
scripts/test_observer_design.py against
scripts/observer_design_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_observer_design.py

## Compliance

- Standards referenced, not reproduced: ARP4754A frames development
  assurance for aircraft systems and DO-178C frames the flight
  software that hosts the observer implementation; the observer design
  equations are common control-theory knowledge, summary-only per
  standards-map.yaml, both reference-only: true.
- compliance: STANDARDS-REF, gated: false.
