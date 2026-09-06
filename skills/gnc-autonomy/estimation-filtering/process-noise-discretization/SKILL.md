---
name: process-noise-discretization
description: "Use when you must discretize the continuous white noise of a linear system into the discrete-time process noise covariance for a Kalman filter with the van-loan method: given the continuous plant matrices F and G and the continuous-spectral-density Qc, compute the discrete-noise-covariance Qd as the exact integral of the propagated noise strength over the filter step and the state transition matrix from the matrix exponential of F times the step. Produces the discrete noise covariance Qd, the exact transition matrix, and the closed forms of the discrete white noise acceleration, random walk and INS velocity random walk models, in SI units, that gate the filter propagation of every estimation-filtering leaf that consumes a given Q. Trigger: van loan discretization, continuous spectral density, process-noise-discretization, discrete noise covariance, continuous white noise to discrete Q, discrete white noise acceleration, velocity random walk."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: estimation-filtering
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: estimation-filtering
  tags: [process-noise-discretization, van-loan-discretization, continuous-spectral-density, discrete-noise-covariance, discrete-white-noise-acceleration, velocity-random-walk, state-transition-matrix]
  version: 0.1.0
  author: Aero Agent Skills
---

# Process Noise Discretization (gnc-autonomy/estimation-filtering/process-noise-discretization)

Use when the task is converting the continuous white-noise spectral
density of a linear plant into the discrete-time process-noise
covariance that a Kalman filter consumes each propagation step: given
the continuous state matrix F, the noise input map G and the continuous
power-spectral-density Qc of the driving white noise, the van Loan
method exponentiates the augmented matrix built from F and the noise
strength W = G*Qc*G^T and reads off the exact state transition matrix
Phi_d = exp(F*dt) and the discrete noise covariance Qd, the exact
integral of the propagated noise strength over the filter step. This
leaf is the producer of the Phi_d and Qd that every
estimation-filtering recursion leaf (extended-kalman-filter,
unscented-kalman-filter, rts-smoother) and the navigation
ins-gnss-integrated-filter consume as given inputs; it implements the
module in pure Python, stdlib only, with scaling-and-squaring matrix
exponentials and the closed forms of the discrete white noise
acceleration, random walk and INS velocity random walk models.

## Domain quick reference

- Continuous model: dx/dt = F*x + G*w with w white noise of power
  spectral density Qc, E[w(t) w(s)^T] = Qc*delta(t - s). F is n x n, G
  is n x m, Qc is m x m symmetric positive semi-definite, all real
  constant matrices; time-varying or nonlinear dynamics are out of
  scope.
- Noise strength in state space: W = G*Qc*G^T, the n x n symmetric
  positive semi-definite matrix the van Loan integral integrates.
- Discrete equivalent over the step dt: x_k = Phi_d*x_(k-1) + w_d with
  Phi_d = exp(F*dt) and Qd = E[w_d w_d^T] = integral_0^dt Phi(tau) W
  Phi(tau)^T d tau.
- van Loan closed form: form the 2n x 2n augmented matrix
  B = [[-F, W],[0, F^T]]*dt and exponentiate to E = exp(B) =
  [[E11, E12],[0, E22]]; then Phi_d = E22^T and Qd = Phi_d*E12. The
  top-right block identity E12 = exp(-F*dt) * integral_0^dt exp(F*tau)
  W exp(F^T*tau) d tau makes Phi_d*E12 exactly the covariance integral;
  Qd is symmetric positive semi-definite, the covariance of the
  equivalent discrete white noise w_d.
- Discrete white noise acceleration (DWA) closed form: for the 2-state
  position/velocity model F = [[0,1],[0,0]], G = [[0],[1]],
  Qc = [[q]], Phi_d = [[1, dt],[0, 1]] and
  Qd = q*[[dt^3/3, dt^2/2],[dt^2/2, dt]].
- Scalar random walk closed form: for F = 0, G = [[1]], Qc = [[q]],
  Phi_d = 1 and Qd = q*dt exactly, the variance growth of white noise
  of PSD q over one step.
- INS velocity random walk: the per-axis velocity-error state driven by
  accelerometer white noise of PSD q_accel is the same F = 0 scalar
  special case, per-axis variance q_accel*dt, the value an error-state
  filter enters per velocity axis each step.
- Small-dt Euler limit: Qd tends to W*dt as dt shrinks, so for the DWA
  model Qd[1][1]/dt tends to the continuous strength q.
- Matrix exponential: scaling and squaring. Scale the matrix by 2^-s
  until its maximum absolute entry is at most 0.5, sum the Taylor
  series until the newest term is below 1e-15 relative to the running
  total (hard cap 80 terms), then square s times; the identity matrix
  for the zero matrix is exact.
- Units are SI: s, (m/s^2)^2 per Hz for the continuous acceleration
  PSD, (m/s)^2 per step for the discrete velocity variance.

## Workflow

1. Set up the continuous model: the state matrix F (n x n), the noise
   input map G (n x m) and the continuous white-noise
   power-spectral-density Qc (m x m), symmetric positive semi-definite.
   The module rejects non-square F and Qc, ragged or shape-mismatched G,
   and asymmetric, negative definite or indefinite Qc up front
   (continuous_noise_map).
2. Map the white noise into state space: continuous_noise_map computes
   the continuous noise strength W = G*Qc*G^T, the matrix the van Loan
   integral integrates.
3. Take the exact discrete state transition matrix:
   state_transition_matrix evaluates Phi_d = exp(F*dt) by the matrix
   exponential with scaling and squaring, never the first-order
   I + F*dt truncation an error-state filter uses.
4. Run the van Loan discretization: van_loan_discretize forms the
   2n x 2n augmented matrix B = [[-F, W],[0, F^T]]*dt, exponentiates
   it, and reads off phi_d = E22^T and qd = phi_d*E12, the exact
   integral of the propagated noise strength over the filter step.
5. Verify with the closed forms: discrete_white_noise_acceleration for
   the DWA position/velocity model, random_walk_covariance for the
   F = 0 scalar case, and ins_velocity_random_walk_covariance for the
   per-axis INS velocity error state.
6. Hand the discrete pair (Phi_d, Qd) to the consuming
   estimation-filtering leaf, which gates its filter propagation step
   on the given process-noise covariance.
7. Confirm the deterministic checks with the contract test
   scripts/test_process_noise_discretization.py (34 tests, offline).

## Worked example

All values below are real outputs of the module
scripts/process_noise_discretization_logic.py on this leaf.

- Random walk scalar sanity: F = [[0]], G = [[1]], Qc = [[0.01]],
  dt = 0.1 s. Phi_d = [[1]]; Qd = [[0.001]]; closed form q*dt = 0.001;
  relative difference 0.000e+00. One state, white noise of PSD q grows
  its variance by q*dt per step.
- DWA 2-state: F = [[0,1],[0,0]], G = [[0],[1]], Qc = [[0.25]]
  ((m/s^2)^2 per Hz), dt = 1.0 s. Phi_d = [[1, 1],[0, 1]] (relative
  difference 0.000e+00 against the nilpotent closed form). Qd by van
  Loan: [[0.08333333333333334, 0.125],[0.125, 0.25]]; the closed form
  discrete_white_noise_acceleration(1.0, 0.25) gives
  [[0.08333333333333333, 0.125],[0.125, 0.25]]; relative difference
  1.665e-16 (one ULP on the [0][0] entry), symmetry difference
  0.000e+00. The identity terms: q*dt^3/3 = 0.25/3 = 0.0833333,
  q*dt^2/2 = 0.125, q*dt = 0.25.
- DWA at dt = 0.1 s (a 100 ms filter step), same q = 0.25: Qd by van
  Loan: [[8.333333333333334e-05, 0.00125],[0.00125, 0.025]]; closed
  form [[8.333333333333336e-05, 0.00125],[0.00125, 0.025]]; relative
  difference 1.626e-16. Small-dt Euler sanity: Qd[1][1]/dt = 0.25, the
  continuous strength q, so Qd tends to W*dt as dt shrinks.
- 2-D planar DWA: 4 states (x position, x velocity, y position, y
  velocity), F block diagonal with two [[0,1],[0,0]] blocks, G =
  [[0,0],[1,0],[0,0],[0,1]], Qc = diag(0.25, 0.5), dt = 0.1 s. Phi_d =
  [[1, 0.1, 0, 0],[0, 1, 0, 0],[0, 0, 1, 0.1],[0, 0, 0, 1]], relative
  difference 0.000e+00 against the block diagonal. Qd by van Loan:
  [[8.333333333333334e-05, 0.00125, 0, 0],[0.00125, 0.025, 0, 0],
  [0, 0, 0.0001666666666666667, 0.0025],[0, 0, 0.0025, 0.05]]: the x
  block is the q = 0.25 DWA result and the y block the q = 0.5 DWA
  result (q*dt^3/3 = 0.5*1e-3/3 = 0.0001666667, q*dt^2/2 = 0.0025,
  q*dt = 0.05); relative difference 1.626e-16 against the per-axis
  closed-form block diagonal. Cross-axis coupling is 0.000e+00 exactly:
  independent axes never couple.
- INS velocity random walk per axis: q_accel = 0.01 (m/s^2)^2 per Hz,
  dt = 0.01 s (100 Hz). Qd per axis = q_accel*dt = 0.0001 (m/s)^2; the
  van Loan scalar F = 0 cross-check returns 0.0001 with relative
  difference 0.000e+00. A 100 Hz INS with accelerometer white noise PSD
  0.01 enters a per-axis velocity-error variance of 1e-4 (m/s)^2 per
  propagation step.
- Determinism: two identical van_loan_discretize calls on the 4-state
  planar model return bitwise identical Qd.

## Verification

- Confirm state_transition_matrix on the DWA F at dt = 1.0 equals
  [[1, 1],[0, 1]] within 1e-12 absolute, and the van Loan phi_d equals
  it as well.
- Confirm van_loan_discretize on the DWA model at dt = 1.0, q = 0.25
  equals discrete_white_noise_acceleration(1.0, 0.25) within 1e-12
  relative (the real values differ by one ULP, so never assert exact
  equality), and the dt = 0.1 case within 1e-12 relative.
- Confirm the random walk: van_loan_discretize([[0.0]], [[1.0]],
  [[0.01]], 0.1) gives Qd = [[0.001]] and Phi_d = [[1]] within 1e-15,
  equal to random_walk_covariance(0.1, 0.01) = 0.001.
- Confirm ins_velocity_random_walk_covariance(0.01, 0.01) = 0.0001
  within 1e-15 and equals the scalar van Loan F = 0 result.
- Confirm the 2-D planar Qd block diagonal matches the per-axis closed
  forms within 1e-12 relative with zero cross-axis coupling, and the
  Phi_d block diagonal within 1e-12.
- Confirm Qd symmetry |Qd[0][1] - Qd[1][0]| below 1e-12 and Qd
  positive semi-definite for PSD Qc.
- Confirm the small-dt limit: Qd[1][1]/dt within 1e-6 of q at dt = 0.1,
  q = 0.25.
- Confirm ValueError rejection: non-square F, non-square or asymmetric
  or negative definite or indefinite Qc, G with the wrong row count for
  F or wrong column count for the Qc order, ragged or empty G, dt at 0
  and -0.1, and q or q_accel at -0.25 and -1.0 all raise ValueError.
- Confirm determinism: repeated van_loan_discretize calls are bitwise
  identical; the module imports nothing beyond math and uses no RNG.
- Run the contract test offline: python3
  scripts/test_process_noise_discretization.py (34 tests,
  deterministic, pure stdlib).

## Related leaves

- gnc-autonomy/estimation-filtering/extended-kalman-filter: consumes a
  given Q in its linearized predict step; this leaf is the producer of
  Q from the continuous spectral density.
- gnc-autonomy/estimation-filtering/unscented-kalman-filter: sigma
  point recursion with a given Q input.
- gnc-autonomy/estimation-filtering/rts-smoother: fixed-interval
  backward recursion over a forward filter on a constant-velocity
  model.
- gnc-autonomy/navigation/ins-gnss-integrated-filter: its predict step
  consumes a given Q with the first-order transition; this leaf is the
  exact-expm producer of that Phi_d and Qd.
- gnc-autonomy/navigation/kalman-filter-design: the scalar single-axis
  recursion that consumes a given scalar process noise q each step.
- gnc-autonomy/control/digital-control-design: deterministic plant
  discretization with a zero order hold, no noise covariance.
- cross-cutting/numerics/power-spectral-density: Welch periodogram
  estimation of a measured time history, the measurement side of
  spectral analysis.
- space-systems/adcs/gyro-allan-variance: Allan variance of a measured
  gyro rate series into random walk coefficients, measurement
  characterization rather than plant noise modeling.

## Pitfalls

- Pairing a truncated transition matrix with a van Loan Qd: some
  error-state filters propagate with Phi = I + F*dt, but the van Loan
  Qd is the exact integral under Phi_d = exp(F*dt); mixing the
  first-order Phi with the exact Qd understates the propagated
  covariance. Take both outputs of van_loan_discretize together.
- Feeding the continuous spectral density as if it were per-step noise:
  Qc has units like (m/s^2)^2 per Hz while Qd is per step; for the DWA
  model the velocity variance per step is q*dt (0.25 per second of
  continuous strength collapsing to 0.025 at a 0.1 s step), so a
  bare Qd = Qc*dt is only the small-dt Euler limit, not the exact
  integral, and it misses the position coupling term q*dt^2/2.
- Using the DWA closed form outside its exact model: the closed form
  assumes F = [[0,1],[0,0]] exactly; a plant with stiffness, damping or
  cross-axis coupling needs the general van Loan integral, which the
  module computes from F, G and Qc directly.
- Passing a Qc that is not positive semi-definite: a negative definite
  or indefinite Qc models imaginary noise and must raise, not silently
  produce a Qd that poisons the filter propagation step.
- Claiming the measured-data neighbors: Allan variance of a gyro rate
  series belongs to space-systems/adcs/gyro-allan-variance and Welch
  periodograms of measured histories to
  cross-cutting/numerics/power-spectral-density; this leaf models the
  plant noise from given continuous matrices, it does not estimate
  spectra from data.
- Reading the DWA position variance as the per-step variance of
  position: the [0][0] entry q*dt^3/3 comes from double integration of
  the white acceleration and is small; the per-step velocity variance
  is q*dt, the entry that dominates at short steps.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_process_noise_discretization.py

The test covers the matrix exponential by scaling and squaring (zero
matrix exact, scalar exp, nilpotent DWA shear, large-norm scaling, full
2x2 series agreement), the exact state transition matrix at the worked
example, the continuous noise map and its validation, the van Loan
discretization against the DWA, scalar random walk and INS velocity
random walk closed forms at the worked-example anchors (dt = 1.0 and
dt = 0.1 s, q = 0.25), Qd symmetry and positive semi-definiteness, the
small-dt Euler limit, the 2-D planar block-diagonal case with zero
cross-axis coupling, bitwise determinism, and ValueError rejection of
non-square F, malformed G, non-square, asymmetric, negative definite or
indefinite Qc, non-positive dt and negative q.

## Compliance

- Standards referenced, not reproduced: SAE ARP4754A frames the
  certification context for the airborne system the filter feeds; the
  discretization relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
