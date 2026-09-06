# Wave-43 leaf spec: process-noise-discretization (gnc-autonomy,
# estimation-filtering pack)

- Path: skills/gnc-autonomy/estimation-filtering/process-noise-discretization/
- Pack: estimation-filtering (present siblings alpha-beta-filter,
  complementary-filter, extended-kalman-filter,
  interacting-multiple-model-filter, particle-filter, rts-smoother,
  unscented-kalman-filter; adjacent fences in gnc-autonomy/navigation/
  kalman-filter-design and ins-gnss-integrated-filter,
  gnc-autonomy/control/digital-control-design (ZOH plant discretization
  of the deterministic plant), cross-cutting/numerics/
  power-spectral-density (Welch periodogram of a measured time history),
  space-systems/adcs/gyro-allan-variance (Allan variance of a measured
  gyro rate series)).
- Claim fences (quoted from the sibling frontmatter at prep; none of them
  builds the discrete noise covariance from a continuous spectral
  density, they all consume a given Q):
  - kalman-filter-design (navigation pack; the scalar single-axis
    recursion): its description reads "design or run a discrete-time
    Kalman filter for single-axis state estimation in SI units: predict
    the state and its error covariance through the dynamics model,
    compute the innovation and innovation variance, calculate the Kalman
    gain, and correct the state and covariance from a noisy measurement"
    and its trigger contains the GENERIC tokens "kalman filter", "process
    noise", "measurement noise". Its body fixes the model as "dynamics f,
    measurement h, process noise q" with q a GIVEN scalar that must be
    >= 0 (pitfall line "Using negative process noise q to model drift; q
    must be >= 0"), and its tags carry process-noise and error-covariance.
    The recursion consumes the process noise each step; it never derives
    q or Q from continuous white noise. Because its trigger contains the
    phrase "process noise", the new leaf MUST fence with distinctive
    leading tokens (van-loan, spectral-density, continuous-white-noise,
    discrete-noise-covariance) and never route on the generic phrase.
  - extended-kalman-filter (this pack): its description reads "linearize
    the nonlinear dynamics and measurement model about the current
    estimate with the state Jacobian F and the measurement Jacobian H,
    run the predict step x_hat = f(x_hat), P = F P F^T + Q, then the
    update step with the innovation y = z - h(x_hat) ...". Q is a GIVEN
    input of the recursion; the model is nonlinear and there is no
    continuous F/G/Qc input.
  - unscented-kalman-filter (this pack): its description reads "generate
    sigma points from the state mean and covariance with the scaled
    unscented transform, propagate each point through the nonlinear
    dynamics, compute the weighted predicted mean and covariance ...".
    Sigma-point propagation of a nonlinear model with Q a given input;
    no continuous plant matrices.
  - ins-gnss-integrated-filter (navigation pack): its description reads
    "assemble the 5-state psi-angle error model of the horizontal INS
    drift from the specific forces, discretize it into the state
    transition matrix, predict the position, velocity and heading error
    states and their covariance between GNSS fixes, and apply the GNSS
    position measurement update ...". Its body uses the first-order
    discretization "Phi = I + F * dt" and a GIVEN Q (worked example
    "Q = diag(0.01, 0.01, 0.01, 0.01, 1e-6)") in the predict step
    P_next = Phi*P*Phi^T + Q. The new leaf is the exact-expm producer of
    the Phi_d and the Qd such error-state filters consume as given
    inputs; it does NOT assemble the psi-angle model or run the GNSS
    update.
  - rts-smoother (this pack): fixed-interval Rauch-Tung-Striebel backward
    recursion over a stored forward Kalman-filter output for a discrete
    constant-velocity model; it consumes the forward-filter covariances,
    never a continuous PSD.
  - power-spectral-density (cross-cutting/numerics): its query reads
    "estimate the power spectral density of a measured acceleration time
    history with a welch averaged periodogram in g squared per hertz" -
    time-history spectral estimation of measurements, not continuous
    noise modeling of a plant.
  - gyro-allan-variance (space-systems/adcs): Allan variance of a
    measured gyro rate series into angle/rate random walk coefficients
    for sensor selection; measurement-characterization domain. Allan
    variance is NOT claimed here.
  - digital-control-design (this pack family, control): "discretize a
    continuous plant with a zero order hold and emulate a lead
    compensator with the Tustin bilinear transform" - deterministic
    plant input/output discretization, no noise covariance.
  Whole-tree greps at prep: the four distinctive tokens
  process-noise-discretization, van-loan, continuous-spectral-density and
  discrete-noise-covariance each return ZERO hits in eval/hit1-corpus.yaml
  and ZERO hits across skills/; "process noise" hits only the
  kalman-filter-design consumer tasks (kf2, "estimate the position state
  recursively from the noisy measurements using the process noise and
  measurement noise covariances") and the generic phrase in its own
  trigger. GENUINE gnc gap (fresh probe #5, GO): no leaf converts the
  continuous white-noise power-spectral-density of a linear plant into
  the discrete-time process-noise covariance consumed by every filter
  leaf.
- Standards id: arp4754a (reference-only, present in standards-map.yaml).
  Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Discretize the continuous white noise of a linear plant into the
discrete-time process-noise covariance for a Kalman filter: given the
continuous system matrices F (n x n), G (n x m) and the continuous
white-noise power-spectral-density Qc (m x m), with noise strength
W = G Qc G^T, compute the state transition matrix Phi_d = exp(F*dt)
(exact matrix exponential, not the first-order I + F*dt truncation) and
the discrete process-noise covariance Qd = integral_0^dt Phi(tau) W
Phi(tau)^T d tau by the van Loan method: form the 2n x 2n augmented
matrix B = [[-F, W],[0, F^T]]*dt, take the matrix exponential
E = exp(B) = [[E11, E12],[0, E22]], then Phi_d = E22^T and Qd =
Phi_d*E12, exact closed form by construction of the matrix exponential;
Qd is symmetric positive semi-definite and equals the covariance of the
equivalent discrete white noise w_d with x_k = Phi_d*x_(k-1) + w_d. Provide
the common closed forms the filter leaves feed on: the discrete
white-noise acceleration (DWA) model Qd = q*[[dt^3/3, dt^2/2],
[dt^2/2, dt]] for the 2-state position/velocity model, the scalar random
walk Qd = q*dt for F = 0, and the per-axis velocity random walk
Qd = q_accel*dt of INS velocity-error states driven by accelerometer
white noise of PSD q_accel, plus the scalar sanity case that reduces the
van Loan integral to the exact q*dt. Produces the discrete state
transition matrix, the discrete noise covariance, the continuous noise
map W = G Qc G^T, and the closed-form identities that verify the
discretization, in SI units, that gate the filter propagation step of
every estimation-filtering leaf that currently consumes a given Q
(extended-kalman-filter, unscented-kalman-filter, ins-gnss-integrated-
filter, rts-smoother). Does NOT do: the filter predict/update recursion,
the gain, or the innovation sequence (kalman-filter-design, scalar
single-axis, and the recursion leaves); estimator tuning heuristics or
how to pick Qc for a given vehicle; psi-angle error-model assembly or the
loosely coupled GNSS measurement update (ins-gnss-integrated-filter);
Allan variance or angle/rate random walk coefficients from measured gyro
rate series (space-systems/adcs/gyro-allan-variance); Welch periodogram
estimation of measured time histories (cross-cutting/numerics/
power-spectral-density); deterministic plant discretization for control
(digital-control-design). F, G and Qc are real constant matrices with
Qc symmetric positive semi-definite; time-varying or nonlinear dynamics
are out of scope.

## Model (implement exactly)

Pure stdlib, math only. No numpy, no scipy, no external processes.
Deterministic: plain row-by-row accumulation in matrix multiply, no
generator-sum float reassociation, no RNG. Module name
process_noise_discretization.

Defining relations (pin these exactly; every function below derives
from them):
- Continuous model: dx/dt = F*x + G*w with w white noise of power
  spectral density Qc, E[w(t) w(s)^T] = Qc*delta(t - s). Noise strength
  in state space: W = G*Qc*G^T (n x n), symmetric PSD.
- Discrete equivalent over the step dt: x_k = Phi_d*x_(k-1) + w_d with
  Phi_d = exp(F*dt) and Qd = E[w_d w_d^T] = integral_0^dt Phi(tau)*W*
  Phi(tau)^T d tau.
- van Loan closed form: with the 2n x 2n augmented matrix
  B = [[-F, W],[0, F^T]]*dt and E = exp(B) = [[E11, E12],[0, E22]],
  Phi_d = E22^T and Qd = Phi_d*E12. The top-right block identity
  E12 = exp(-F*dt)*integral_0^dt exp(F*tau) W exp(F^T*tau) d tau makes
  Phi_d*E12 exactly the integral above (verified in the anchor by the
  DWA and random-walk identities).
- Closed forms supplied by the module: DWA (position/velocity state,
  F = [[0,1],[0,0]], G = [[0],[1]], Qc = [[q]]) gives Phi_d =
  [[1, dt],[0, 1]] and Qd = q*[[dt^3/3, dt^2/2],[dt^2/2, dt]]; scalar
  random walk (F = 0, G = [[1]], Qc = [[q]]) gives Phi_d = 1 and
  Qd = q*dt exactly; INS velocity random walk is the same scalar special
  case per axis with q_accel the accelerometer white-noise PSD, giving a
  per-axis velocity-error variance q_accel*dt.
- Matrix exponential: scaling-and-squaring power series (stdlib only):
  scale A by 2^-s until max-absolute entry <= 0.5, sum the Taylor series
  until the newest term max-absolute entry is below 1e-15 relative to the
  running total (hard cap 80 terms), then square s times. The identity
  matrix for the zero matrix is exact.

Functions (public API, 7):
- mat_exp(a) -> list of lists. exp(a) by scaling and squaring as above.
  ValueError if a is empty or non-square.
- state_transition_matrix(f, dt) -> list of lists. Phi_d = exp(f*dt).
  ValueError if f non-square or dt <= 0.
- continuous_noise_map(g, qc) -> list of lists. W = g*qc*g^T, the
  continuous noise strength the van Loan integral integrates. ValueError
  if g is empty or ragged, qc empty or non-square, g row length != qc
  order, qc not symmetric, or qc not positive semi-definite.
- van_loan_discretize(f, g, qc, dt) -> (phi_d, qd) tuple of lists of
  lists. The full discretization above. ValueError set: f non-square,
  g row count != f order, qc failures as continuous_noise_map, dt <= 0.
- discrete_white_noise_acceleration(dt, q) -> 2 x 2 list of lists, the
  DWA closed form q*[[dt^3/3, dt^2/2],[dt^2/2, dt]]. ValueError if
  dt <= 0 or q < 0.
- random_walk_covariance(dt, q) -> float, q*dt. ValueError if dt <= 0 or
  q < 0.
- ins_velocity_random_walk_covariance(dt, q_accel) -> float, q_accel*dt,
  the per-axis velocity-error variance from accelerometer white noise of
  PSD q_accel (INS velocity random walk, F = 0 scalar special case; the
  value an error-state filter enters per velocity axis). Same ValueError
  set as random_walk_covariance.
Private helpers (module-internal): _validate_square, _identity, _matmul
(plain accumulated row-by-row product), _transpose, _maxabs, _det
(Laplace expansion, fine at the orders used), _is_psd_symmetric
(symmetry within 1e-9 plus every principal minor >= -1e-9; principal
minors enumerated by index subsets, determinant by Laplace expansion),
_combinations. ValueErrors on non-square or negative-definite inputs are
part of the contract: Qc with any negative eigenvalue fails the PSD test
(negative definite and indefinite Qc both raise, e.g. [[-1.0]] and
[[1.0, 2.0],[2.0, 1.0]]).

Identities to test (tolerance-based asserts only, no exact float
equality on computed sums):
- DWA: van_loan_discretize on F = [[0,1],[0,0]], G = [[0],[1]],
  Qc = [[0.25]] at dt = 1.0 equals the closed form
  discrete_white_noise_acceleration(1.0, 0.25) to relative difference
  1.665e-16 (real anchor), and Phi_d equals [[1, dt],[0, 1]] exactly
  (nilpotent expm, real anchor relative difference 0.000e+00).
- Random walk: van_loan_discretize([[0.0]], [[1.0]], [[0.01]], 0.1)
  returns Phi_d = [[1]] and Qd = [[0.001]] = q*dt to relative difference
  0.000e+00 (real anchor, exact by construction).
- INS velocity random walk: ins_velocity_random_walk_covariance(dt,
  q_accel) equals the van Loan scalar F = 0 result to relative
  difference 0.000e+00 (real anchor at dt = 0.01, q_accel = 0.01).
- Qd symmetric: |Qd[0][1] - Qd[1][0]| = 0.000e+00 (real anchor); Qd
  positive semi-definite for PSD Qc.
- Small-dt Euler limit: Qd[1][1]/dt -> q as dt -> 0, the continuous
  strength W[1][1] (real anchor 0.25 at dt = 0.1, q = 0.25).
- 2-D planar case (4 states, two independent axes, Qc = diag(qx, qy)):
  Qd block diagonal with per-axis DWA blocks, cross-axis coupling exactly
  0.000e+00, Phi_d the [[1, dt],[0, 1]] block diagonal (real anchor).
- Determinism: two runs of van_loan_discretize bitwise identical.
- ValueErrors across the module: non-square F; non-square Qc; G row
  count mismatch; G column count mismatch; asymmetric Qc; negative
  definite Qc; indefinite Qc; dt at 0 and -0.1; q at -0.25 and -1.0.
- Determinism; no imports beyond math; F, G, Qc real constant matrices.

## Worked example

Parameters: random walk q = 0.01, dt = 0.1 s; DWA q = 0.25
((m/s^2)^2 per Hz, continuous acceleration PSD), dt = 1.0 s and dt =
0.1 s; 2-D planar DWA Qc = diag(0.25, 0.5), dt = 0.1 s; INS velocity
random walk q_accel = 0.01, dt = 0.01 s (100 Hz). All values below are
REAL outputs of the prep anchor /tmp/w43spec/anchor_pnd.py (stdlib
math, exit 0, all checks passed):
- Random walk scalar sanity (F = [[0]], G = [[1]], Qc = [[0.01]],
  dt = 0.1): Phi_d = [[1]]; Qd = [[0.001]]; closed form q*dt = 0.001;
  relative difference 0.000e+00. The exact scalar case: one state, white
  noise of PSD q grows its variance by q*dt per step.
- DWA 2-state (F = [[0,1],[0,0]], G = [[0],[1]], Qc = [[0.25]],
  dt = 1.0 s): Phi_d = [[1, 1],[0, 1]] (relative difference 0.000e+00
  against the nilpotent closed form). Qd by van Loan:
  [[0.08333333333333334, 0.125],[0.125, 0.25]]; closed form
  discrete_white_noise_acceleration(1.0, 0.25):
  [[0.08333333333333333, 0.125],[0.125, 0.25]]; relative difference
  1.665e-16 (one ULP on the [0][0] entry), symmetry |Qd[0][1]-Qd[1][0]|
  = 0.000e+00. q*dt^3/3 = 0.25/3 = 0.0833333, q*dt^2/2 = 0.125,
  q*dt = 0.25.
- DWA at dt = 0.1 s (a 100 ms filter step), same q = 0.25: Qd by van
  Loan: [[8.333333333333334e-05, 0.00125],[0.00125, 0.025]]; closed form
  [[8.333333333333336e-05, 0.00125],[0.00125, 0.025]]; relative
  difference 1.626e-16. Small-dt Euler sanity: Qd[1][1]/dt = 0.25, the
  continuous strength q, so Qd tends to W*dt as dt shrinks.
- 2-D planar DWA (4 states: x position, x velocity, y position, y
  velocity; F = [[0,1,0,0],[0,0,0,0],[0,0,0,1],[0,0,0,0]], G = [[0,0],
  [1,0],[0,0],[0,1]], Qc = diag(0.25, 0.5), dt = 0.1 s): Phi_d =
  [[1, 0.1, 0, 0],[0, 1, 0, 0],[0, 0, 1, 0.1],[0, 0, 0, 1]], relative
  difference 0.000e+00 against the block diagonal. Qd by van Loan:
  [[8.333333333333334e-05, 0.00125, 0, 0],[0.00125, 0.025, 0, 0],
  [0, 0, 0.0001666666666666667, 0.0025],[0, 0, 0.0025, 0.05]]: the x
  block is the q = 0.25 DWA result and the y block the q = 0.5 DWA
  result (q*dt^3/3 = 0.5*1e-3/3 = 0.0001666667, q*dt^2/2 = 0.0025,
  q*dt = 0.05); relative difference 1.626e-16 against the per-axis
  closed-form block diagonal; cross-axis coupling max |Qd[i][j]| =
  0.000e+00 exactly. Independent axes never couple.
- INS velocity random walk per axis (q_accel = 0.01 (m/s^2)^2 per Hz,
  dt = 0.01 s at 100 Hz): Qd per axis = q_accel*dt = 0.0001 (m/s)^2;
  the van Loan scalar F = 0 cross-check returns 0.0001 with relative
  difference 0.000e+00. A 100 Hz INS with accelerometer white noise PSD
  0.01 enters a per-axis velocity-error variance of 1e-4 (m/s)^2 per
  propagation step.
- Determinism: two identical van_loan_discretize(4-state) calls produce
  bitwise identical Qd.
Run your module and take the real outputs as assert targets (tolerance-
based); the anchors above are real prep outputs of /tmp/w43spec/
anchor_pnd.py (stdlib math, scaling-and-squaring expm, exit 0).

## Validation list (contract test must include)

- state_transition_matrix on the DWA F at dt = 1.0 equals [[1, 1],
  [0, 1]] within 1e-12 absolute (anchor relative difference 0.000e+00);
  van_loan_discretize Phi_d equals it as well.
- van_loan_discretize DWA at dt = 1.0, q = 0.25 equals
  discrete_white_noise_acceleration(1.0, 0.25) within 1e-12 relative
  (anchor 1.665e-16; assert with isclose/delta, NEVER exact equality:
  the real values differ by one ULP, 0.08333333333333334 vs
  0.08333333333333333); dt = 0.1 case within 1e-12 relative (anchor
  1.626e-16).
- Random walk: van_loan_discretize([[0.0]], [[1.0]], [[0.01]], 0.1)
  gives Qd = [[0.001]] and Phi_d = [[1]] within 1e-15; equals
  random_walk_covariance(0.1, 0.01) = 0.001.
- ins_velocity_random_walk_covariance(0.01, 0.01) = 0.0001 within 1e-15
  and equals the scalar van Loan F = 0 result (anchor relative
  difference 0.000e+00).
- 2-D planar: Qd block diagonal per axis matches the per-axis closed
  forms within 1e-12 relative (anchor 1.626e-16); cross-axis entries
  zero within 1e-12; Phi_d block diagonal within 1e-12.
- Qd symmetry: |Qd[0][1] - Qd[1][0]| below 1e-12 (anchor 0.000e+00);
  Qd positive semi-definite for PSD Qc.
- Small-dt limit: Qd[1][1]/dt within 1e-6 of q at dt = 0.1, q = 0.25
  (anchor 0.25 exactly).
- ValueErrors: non-square F (e.g. [[1.0, 0.0]] for a 1 x 2 F); dt at 0.0
  and -0.1 on state_transition_matrix and van_loan_discretize; Qc
  non-square; G with the wrong row count for F; G columns not matching
  the Qc order; asymmetric Qc; negative definite Qc [[-1.0]];
  indefinite Qc [[1.0, 2.0],[2.0, 1.0]]; q at -0.25 and -1.0 on the
  closed-form functions.
- Determinism: repeated van_loan_discretize calls bitwise identical; no
  imports beyond math; no RNG.
- Run the contract test under both python3 (3.9.x) and the pyenv 3.13
  hook interpreter; all asserts above are tolerance-based and must hold
  on both.

## Corpus fragment (eval/hit1-wave43-process-noise-discretization.yaml)

Query 1 (copy verbatim):
  "apply the process-noise-discretization to a continuous linear system
  with the van-loan method: given the plant matrices F and G and the
  continuous-spectral-density Qc of the driving white noise, compute the
  discrete-noise-covariance Qd and the state transition matrix exp(F dt)
  for the filter propagation step"
  intent: "gnc-autonomy; van Loan discretization of the continuous
  white-noise spectral density into the discrete process-noise
  covariance Qd with the exact state transition matrix for Kalman filter
  propagation"
  expected_skill: "gnc-autonomy/estimation-filtering/
  process-noise-discretization"
Query 2 (copy verbatim):
  "discretize the continuous process noise of a discrete white noise
  acceleration model with the van-loan method and verify the
  discrete-noise-covariance against the closed form q times dt cubed
  over three from the continuous-spectral-density at the sampling
  interval"
  intent: "gnc-autonomy; discrete white noise acceleration closed-form
  Qd identity against the van Loan discretization of the continuous
  spectral density"
  expected_skill: "gnc-autonomy/estimation-filtering/
  process-noise-discretization"
Task ids: w43-process-noise-discretization-1 and -2. Prep grep:
process-noise-discretization, van-loan, continuous-spectral-density and
discrete-noise-covariance appear in NO existing eval/hit1-corpus.yaml
task (each grep count 0) and in NO skill file; the kalman tasks route on
the single-axis recursion, gain, innovation variance and error
covariance (kf1, kf2 -> kalman-filter-design; ukf/ekf/rts tasks route on
sigma points, Jacobian linearization and the backward pass), the
power-spectral-density tasks route on the Welch periodogram of a measured
time history, the gyro-allan-variance tasks route on the angle random
walk coefficient from a measured rate series, and digital-control-design
routes on ZOH plant discretization with a deterministic input, so the
queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must discretize the continuous white
noise of a linear system into the discrete-time process noise covariance
for a Kalman filter with the van-loan method:" (the wave-43 leaf plan
direction: MED, lead with van-loan/spectral-density tokens) and include
the outputs in the Claim. First tag: process-noise-discretization.
Additional tags ONLY: van-loan-discretization,
continuous-spectral-density, discrete-noise-covariance,
discrete-white-noise-acceleration, velocity-random-walk,
state-transition-matrix. NEVER single generic words (noise, covariance,
discretization, filter, spectral, density alone) and NEVER
kalman-gain, innovation-variance, innovation-covariance, error-covariance
or the bare phrase-trigger "process noise" as a routing keyword, which
kalman-filter-design owns (its trigger literally contains "process
noise"; the hyphenated compounds above are the fence). 50-150 words,
<=1000 chars, no em dash, no content-policy sweep term, action verb
present. Recommended wording (outputs in Claim order): "Use when you
must discretize the continuous white noise of a linear system into the
discrete-time process noise covariance for a Kalman filter with the
van-loan method: given the continuous plant matrices F and G and the
continuous-spectral-density Qc, compute the discrete-noise-covariance Qd
as the exact integral of the propagated noise strength over the filter
step and the state transition matrix from the matrix exponential of
F times the step. Produces the discrete noise covariance Qd, the exact
transition matrix, and the closed forms of the discrete white noise
acceleration, random walk and INS velocity random walk models, in SI
units, that gate the filter propagation of every estimation-filtering
leaf that consumes a given Q. Trigger: van loan discretization,
continuous spectral density, process-noise-discretization, discrete
noise covariance, continuous white noise to discrete Q, discrete white
noise acceleration, velocity random walk." The generic phrases "process
noise" and "kalman filter" must not appear as trigger keywords.

FORBIDDEN TOKENS (belong to siblings): predict-update recursion, kalman
gain, innovation variance, innovation covariance, error covariance,
single-axis estimation, measurement noise variance, the tag process-noise
(kalman-filter-design); sigma points, scaled unscented transform, nees
(unscented-kalman-filter); jacobian linearization, range bearing tracking
(extended-kalman-filter); psi-angle model, loosely coupled integration,
gnss position update, ins drift correction, horizontal specific force,
error-state-filter (ins-gnss-integrated-filter); backward pass, smoothed
state, rauch-tung-striebel (rts-smoother); welch periodogram, measured
time history (power-spectral-density); allan variance, angle random
walk, gyro rate noise, adcs sensor selection (gyro-allan-variance); zero
order hold, tustin bilinear transform (digital-control-design); tuning
heuristics for choosing Qc from vehicle dynamics (no owner, out of
scope).
