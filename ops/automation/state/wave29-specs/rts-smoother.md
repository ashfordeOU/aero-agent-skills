# Wave-29 leaf spec: rts-smoother (gnc-autonomy, estimation-filtering pack)

- Path: skills/gnc-autonomy/estimation-filtering/rts-smoother/
- Pack: estimation-filtering (existing siblings: alpha-beta-filter,
  complementary-filter, extended-kalman-filter, particle-filter,
  unscented-kalman-filter)
- Standards ids: arp4754a (reference-only; the GNC control and
  estimation leaves use this convention). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Run the fixed-interval Rauch-Tung-Striebel (RTS) smoother over a stored
sequence of forward Kalman-filter outputs to produce the optimal
smoothed state estimate that uses all measurements, past and future.
The leaf implements the linear Kalman forward pass for a discrete
constant-velocity model, stores the predicted and filtered means and
covariances at every step, then runs the backward recursion with the
smoother gain to produce the smoothed mean and covariance. Produces the
smoothed state history, the smoother gains, and the covariance
reduction verdict that gate offline trajectory reconstruction and
post-processing of navigation data.

Does NOT do: design or run a real-time filter (kalman-filter-design
owns the single-axis discrete Kalman filter); handle nonlinear models
(extended-kalman-filter and unscented-kalman-filter own nonlinear
filtering); estimate with alpha-beta or complementary filters (sibling
leaves own those); smooth raw flight-test traces with moving averages
(flight-test-operations flight-test-data-reduction owns that). This
leaf is the offline backward-pass complement to any forward Kalman
filter: fixed-interval smoothing for batch post-processing.

## Model (implement exactly)

State x = [position, velocity]. Constant-velocity model with time step
dt (s). Process noise q is the continuous acceleration noise intensity;
discrete Q = q * [[dt^4/4, dt^3/2], [dt^3/2, dt^2]].
F = [[1, dt], [0, 1]]; H = [[1, 0]]; measurement noise variance r.

Functions (pure stdlib; small 2x2 helpers mat_mul, mat_add, mat_sub,
mat_scale, transpose, mat_vec, inv_2x2 with ValueError on singular):
- forward_kalman(measurements, dt, q, r, x0, P0) -> list of dicts:
  for each measurement k run predict (x_pred = F x, P_pred = F P F^T +
  Q) then update (innovation, S = H P_pred H^T + r, gain K = P_pred
  H^T / S as a 2x1, x_filt = x_pred + K innovation, P_filt = (I - K H)
  P_pred (I - K H)^T + K r K^T). Store per step:
  {x_pred, P_pred, x_filt, P_filt, innovation, innovation_variance}.
  measurements is a list of scalars. ValueError if dt <= 0, q < 0,
  r <= 0, fewer than 2 measurements, x0 not length 2, P0 not 2x2.
- rts_smooth(fwd_results) -> (smoothed_states, smoothed_covs, gains):
  initialize at the final step with the last filtered mean and
  covariance; for k = n-2 down to 0: gain K_k = P_filt[k] F^T
  (P_pred[k+1])^-1 (2x2 inverse); x_s[k] = x_filt[k] + K_k (x_s[k+1] -
  x_pred[k+1]); P_s[k] = P_filt[k] + K_k (P_s[k+1] - P_pred[k+1])
  K_k^T. Returns lists of length n. Requires fwd_results to be a
  forward_kalman output (list of dicts with the stored keys).
- smoother_reduction(fwd_results, smoothed_covs) -> dict: for each k
  compare P_s[k][0][0] against P_filt[k][0][0]; returns
  {max_reduction: largest relative drop in position variance,
  all_reduced: bool (every step P_s <= P_filt within 1e-12),
  boundary_matches: bool (smoothed at last step equals filtered at
  last step within 1e-12)}.

## Worked example

dt = 1 s; q = 0.1 (m2/s3); r = 25 (m2); x0 = [0.0, 5.0]; P0 =
[[100, 0], [0, 10]]. Measurements (10 samples):
[2.1, 6.8, 11.9, 16.4, 21.2, 26.5, 30.9, 36.2, 41.4, 45.8].

Deterministic anchors (compute with the exact formulas; assert within
the stated tolerances):
- Forward filtered at k=9 (last): position 45.8108 (within 0.01),
  velocity 4.8570 (within 0.01).
- Filtered position variance at k=9: P00 = 8.8487 (within 0.01);
  velocity variance P11 = 0.5941 (within 0.01).
- Smoothed at k=0: position 2.2080 (within 0.01), velocity 4.8275
  (within 0.01).
- Smoothed at k=4: position 21.5444 (within 0.01), velocity 4.8439
  (within 0.01).
- Smoothed covariance at k=4: P00 = 2.7726 (within 0.01), P11 =
  0.3326 (within 0.01); both strictly below the filtered values at k=4
  (filtered P00 at k=4 around 12.3, P11 around 0.95; assert P_s < P_f
  elementwise on the diagonal).
- Boundary identity: smoothed state at the last step equals the
  filtered state at the last step exactly (within 1e-12); smoother
  gain at k=0 is about [0.9983, 0.0034]^T (within 1e-3).
- all_reduced True, max_reduction positive, boundary_matches True.
- Structural: smoothing a perfectly noiseless constant-velocity ramp
  (measurements = 5*k for k = 0..9) returns smoothed velocities within
  1e-9 of 5.0 at every step.
- ValueErrors: dt 0, q -1, r 0, one measurement, bad x0 length.

Keep at least 18 test methods: forward predict/update shapes, filter
anchor at k=9, smoothing anchors k=0 and k=4, covariance reduction,
boundary identity, noiseless ramp identity, smoother gain anchor,
innovation variance at k=0 (38.697, within 0.01), ValueErrors. Test
runs offline in under 20 s.

## Corpus tasks (ids w29-rts-smoother-1/2)

Distinctive tokens: RTS smoother, Rauch-Tung-Striebel, fixed-interval
smoothing, backward pass, smoothed state, offline trajectory
reconstruction, post-processing navigation data. Avoid: Kalman gain and
innovation for a live filter (kalman-filter-design); EKF linearization,
unscented transform, sigma points (the nonlinear filter siblings);
moving-average smoothing of flight-test traces
(flight-test-data-reduction).

1. "smooth a stored Kalman filter output with the Rauch-Tung-Striebel
   fixed-interval recursion: run the backward pass and report the
   smoothed position and velocity history with the reduced covariance"
2. "post-process a recorded GNSS/INS track offline with an RTS smoother
   so the trajectory estimate uses all measurements forward and
   backward"

## SKILL body notes

Pair with kalman-filter-design (the forward filter whose stored outputs
feed the smoother), extended-kalman-filter (nonlinear forward filtering
that an RTS linearization would extend), alpha-beta-filter (cheap
online tracking). State the boundary: this is batch smoothing, not
real-time filtering; it never touches the live navigation state until
post-processing. arp4754a is referenced for the development-assurance
context of navigation estimation software, reference-only. Mirror the
estimation-filtering pack SKILL body style (SI units, stdlib only,
deterministic offline).
