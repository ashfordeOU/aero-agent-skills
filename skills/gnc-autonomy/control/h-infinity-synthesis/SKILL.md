---
name: h-infinity-synthesis
description: "Use when you must synthesize the state-space h-infinity controller of the generalized plant with the dgkf two-Riccati method: given the state matrices and the performance and control channels, iterate the gamma level while the x-infinity and y-infinity algebraic Riccati equations admit stabilizing positive-semidefinite solutions and the spectral-radius coupling stays below gamma squared, then form the central h-infinity controller state matrices from the state-feedback gain and the observer gain. Produces the infimum feasible gamma level from the bisection, the two stabilizing Riccati solutions with the coupling check, the central controller state matrices at the working suboptimal level, and the closed-loop stability check with the disturbance-to-output peak below that level. Trigger: h infinity synthesis, dgkf two riccati, gamma level iteration, spectral radius coupling, central h infinity controller, x infinity y infinity riccati, state feedback gain, observer gain."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: control
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: control
  tags: [h-infinity-synthesis, dgkf-two-riccati, gamma-level-iteration, spectral-radius-coupling, central-h-infinity-controller, state-space-h-infinity-synthesis, algebraic-riccati-synthesis]
  version: 0.1.0
  author: AeroSkills
---

# H-infinity Synthesis (gnc-autonomy/control/h-infinity-synthesis)

Use when the task is the DGKF two-Riccati state-space H-infinity
synthesis of the generalized plant: given the state matrices A, B1, B2,
C1, C2 of the two-state normalized standard problem (D11 = 0, D22 = 0,
D12' D12 = I, D21 D21' = I, D12' C1 = 0, B1 D21' = 0), this leaf
iterates the gamma level while the two algebraic Riccati equations admit
stabilizing positive-semidefinite solutions and the spectral-radius
coupling rho(X_inf Y_inf) < gamma^2 holds, then forms the central
H-infinity controller state matrices from the stabilizing solutions at a
declared working level. The output of the leaf IS the controller,
produced by closed-form algebraic Riccati solutions and the gamma-level
bisection, never by tuning, placing, reviewing or recovering a given
pair. The plant state matrices and the performance and control channels
are given inputs; the controller is never reviewed, tuned or placed.

This leaf is the synthesis member of the control pack's robust vein and
the load-bearing fence against the pack's norm-analysis leaf. Where
gnc-autonomy/control/h-infinity-control rates a supplied plant-controller
pair, this leaf takes only the generalized plant and produces the
controller; the S/KS mixed-sensitivity review, the weighted-sensitivity
norms and the worst-case-peak-gain verdicts of a given loop belong to
h-infinity-control, whose pitfalls renounce the synthesis identity this
leaf owns, verbatim: "Reading this leaf as an H-infinity controller
synthesis: no controller is ever synthesized, tuned, placed or recovered
here, and no algebraic Riccati equation solver lives in the leaf; the
plant, the candidate controller and the weight parameters are all given
inputs, and the review verdict only rates the supplied pair." The seam:
h-infinity-control takes the plant AND the candidate controller as given
and rates the supplied pair; this leaf takes only the generalized plant
and produces the controller. Pure Python, stdlib only (math), deterministic
and offline.

## Domain quick reference

- Generalized plant (normalized standard problem, n = 2): xdot = A x +
  B1 w + B2 u, z = C1 x + D12 u, y = C2 x + D21 w, with w the
  two-channel exogenous input (disturbance channel 1, measurement noise
  channel 2), z the two-channel performance output (scalar performance
  channel stacked over the control channel), u the scalar control, y the
  scalar measurement. Standing normalization: D11 = 0, D22 = 0,
  D12 = [0; 1], D21 = [0 1], which hold by construction of the inputs.
- X ARE (regulator side): A'X + XA + X S_X X + C1' C1 = 0 with S_X =
  g^-2 B1 B1' - B2 B2'; X_inf is the stabilizing positive-semidefinite
  solution, that is A + S_X X_inf has both eigenvalues in the open left
  half plane. Solved by are_x_inf(A, B1, B2, C1, gamma).
- Y ARE (estimator side): A Y + Y A' + Y S_Y Y + B1 B1' = 0 with S_Y =
  g^-2 C1' C1 - C2' C2; Y_inf is the stabilizing positive-semidefinite
  solution, that is A' + S_Y Y_inf has both eigenvalues in the open left
  half plane. Solved by are_y_inf(A, B1, B2, C1, C2, gamma).
- Coupling: the level gamma is feasible exactly when both AREs admit
  their stabilizing positive-semidefinite solutions and the spectral
  radius rho = spectral_radius(X_inf Y_inf) satisfies rho * (1 +
  COUPLING_REL_EPS) < gamma^2. Feasibility is monotone in gamma: the
  feasible set is the open interval (gamma_inf, infinity).
- Central controller (D11 feedthrough zero): F_inf = -B2' X_inf,
  H_inf = -Y_inf C2', Z_inf = (I - g^-2 Y_inf X_inf)^-1,
  A_k = A + g^-2 B1 B1' X_inf + B2 F_inf + Z_inf H_inf C2,
  B_k = -Z_inf H_inf, C_k = F_inf, D_k = 0; K(s) = C_k (s I - A_k)^-1 B_k
  is strictly proper. Z_inf is unbounded exactly at gamma_inf, so the
  central controller is formed at a declared working level strictly above
  the infimum.
- Module constants, pin exactly: N_STATES = 2, GAMMA_BISECT_ITER = 80,
  GAMMA_HI_START = 1.0, GAMMA_HI_CEIL = 1e6, GAMMA_FLOOR = 1e-6,
  PSD_EPS = 1e-9, IMAG_AXIS_EPS = 1e-9, DEFECT_EPS = 1e-12,
  COUPLING_REL_EPS = 1e-9, PEAK_W_MIN = 1e-3, PEAK_W_MAX = 1e3 and
  PEAK_GRID_POINTS = 4001. Every matrix is a list of lists of float
  coefficients, row major.
- ARE solution method: the stabilizing solution of M'X + XM + XSX + Q = 0
  is computed deterministically by the Hamiltonian stable-invariant-
  subspace method on the real 4x4 Hamiltonian H = [[M, S], [-Q, -M']]:
  the even characteristic polynomial from the Faddeev-LeVerrier
  recursion, the four eigenvalues as square roots of the two roots of the
  quadratic in mu (hand complex square roots, math only, no cmath), the
  two stable eigenvalues with their eigenvectors as the largest-magnitude
  adjugate columns of H - lambda I (cofactor arithmetic, no linear
  solver), and X = U21 U11^-1 assembled in complex arithmetic,
  symmetrized. Verdicts reject imaginary-axis Hamiltonian eigenvalues,
  a wrong count of stable eigenvalues, a repeated stable pair and any
  solution failing the PSD or stabilizing checks.
- Achievement scan: with the central controller at the working level,
  assemble the closed-loop matrices A_cl, B_cl, C_cl, D_cl = 0 and scan
  sigma_max of Tzw(jw) = C_cl (jw I - A_cl)^-1 B_cl over the geometric
  grid w in [1e-3, 1e3] rad/s with 4001 points (each complex 4x4 solve by
  Gaussian elimination with partial pivoting). The scan reports the grid
  maximum peak and its frequency w_peak; it is a verification scan of the
  synthesized loop, not an H-infinity norm computation (norm searches
  over supplied loops belong to h-infinity-control).

## Workflow

1. Fix the generalized plant: the state matrices A, B1, B2, C1, C2 of
   the two-state normalized standard problem are given inputs with the
   pinned shapes (2x2, 2x2, 2x1, 2x2, 1x2), and the module constants
   N_STATES, GAMMA_BISECT_ITER, GAMMA_HI_START, GAMMA_HI_CEIL,
   GAMMA_FLOOR, PSD_EPS, IMAG_AXIS_EPS, DEFECT_EPS, COUPLING_REL_EPS,
   PEAK_W_MIN, PEAK_W_MAX and PEAK_GRID_POINTS are pinned as above.
2. Solve the two stabilizing algebraic Riccati equations at the declared
   level with are_x_inf (the X_inf equation of the regulator side) and
   are_y_inf (the Y_inf equation of the estimator side); both reject a
   non-positive gamma level and a level with no stabilizing PSD solution,
   each naming its equation.
3. Read the gamma-level feasibility verdict with gamma_feasible: the
   dict carries the feasible flag, the exact reason string
   ("x-are-no-stabilizing-solution", "y-are-no-stabilizing-solution" or
   "spectral-radius-coupling-fails"), the two solutions when solved and
   the spectral radius rho of X_inf Y_inf, checked against the coupling
   condition with the COUPLING_REL_EPS strictness margin. The function
   never raises on an infeasible level.
4. Bisect the infimum feasible level with gamma_iteration: expand upward
   from GAMMA_HI_START by doubling to a feasible level (rejecting the
   plant above the ceiling), walk down by halving to an infeasible point
   above GAMMA_FLOOR, then run GAMMA_BISECT_ITER bisection passes keeping
   the upper endpoint feasible. Returns gamma_inf, gamma_lo and the X_inf,
   Y_inf and rho at gamma_inf, where the coupling is tight: rho approaches
   gamma_inf^2 from below.
5. Form the central controller with central_controller at a declared
   working level strictly above gamma_inf: the dict carries x_inf, y_inf,
   rho, f_inf, h_inf, z_inf, a_k, b_k, c_k, d_k and gamma. Calling it at
   or below gamma_inf raises the spectral-radius coupling rejection with
   the real rho and ratio.
6. Run the achievement scan with closed_loop_peak on the central
   controller dict: assemble the closed loop of the synthesized
   controller and return the fixed-grid maximum peak of sigma_max Tzw(jw)
   and its frequency w_peak; the synthesized controller achieves the
   declared level when peak stays below gamma.
7. Confirm the deterministic checks with the contract test
   scripts/test_h-infinity-synthesis.py, offline, under both
   interpreters: stdlib unittest, no imports beyond math, no exact-float
   equality on computed sums.

## Worked example

All values below are real outputs of the contract module run on the
two-state normalized disturbance-rejection problem of the spec: the
damped second-order plant A = [[0, 1], [-4, -2]] (poles -1 +/- j
sqrt(3)), B1 = [[1, 0], [0, 0]] (process disturbance w1 of unit intensity
on the position channel), B2 = [[0], [1]] (scalar control on the
acceleration channel), C1 = [[2, 0], [0, 0]] (performance z = [2 x1; u]),
C2 = [[1, 0]] (measurement y = x1 + w2 with unit noise channel).

- Level probes: gamma 1.00, 1.24, 1.25, 1.26 and 1.28 report feasible =
  False with reason "x-are-no-stabilizing-solution" and rho = None;
  gamma 1.2885 reports feasible = False with reason
  "spectral-radius-coupling-fails" and rho/gamma^2 = 1.0226955372337125
  above 1; gamma 1.29, 1.30, 1.40, 2.00 and 4.00 report feasible = True
  with rho 1.6627132282952146, 1.5207128718101464, 1.1109308083000942,
  0.73205080756887764 and 0.60910023020016668.
- gamma_iteration: gamma_inf = 1.2899416380818218, gamma_lo =
  1.2899416380818216, relative bracket width 1.72e-16. X_inf at gamma_inf
  = [[4.8550497046046912, 1.8451689460791623], [1.8451689460791623,
  1.1203305657836022]]; Y_inf at gamma_inf = [[0.69782803015344119,
  -0.84182902900864276], [-0.84182902900864276, 1.9323890607421939]].
  rho = 1.6639494279932627 against gamma_inf^2 = 1.6639494296572137:
  rho/gamma_inf^2 = 0.99999999899999903 and the coupling margin
  1 - rho/gamma_inf^2 = 1e-9, the tight-coupling identity at the
  spectral-radius lower bound.
- Central controller at the declared working level gamma = 1.5 (16.3%
  above gamma_inf): X_inf = [[2.8767170729927769, 0.86600457222455551],
  [0.86600457222455551, 0.46278834694194487]]; Y_inf =
  [[0.57859549850415914, -0.63018940312360749], [-0.63018940312360749,
  1.33760021698791]]; rho = 0.96499552430796154 below gamma^2 = 2.25 with
  rho/gamma^2 = 0.42888689969242733 and margin 0.57111310030757267.
- ARE residuals at gamma 1.5: Frobenius residual of the X_inf ARE =
  7.6918507455342553e-16 and of the Y_inf ARE = 9.6148134319178191e-17;
  symmetry residuals of both solutions print as 0. Stabilizing solutions:
  eigenvalues of A + S_X X_inf = -0.5921237128059108 +/- j 1.799860933560131
  and of A + Y_inf S_Y = -0.7749906394706048 +/- j 1.7290168825537666.
- Gains: F_inf = [-0.86600457222455551, -0.46278834694194487]; H_inf =
  [-0.57859549850415914, 0.63018940312360749]; Z_inf =
  [[1.8840094153375413, 0.18126028353826662], [-0.56649451713616139,
  0.97916244503312322]].
- Central controller state matrices at gamma 1.5: A_k =
  [[-0.53140661251631349, 1.0], [-3.9211755978858096,
  -2.4627883469419447]], B_k = [0.97585105696075791,
  -0.94482897433874635], C_k = [-0.86600457222455551,
  -0.46278834694194487], D_k = 0. Controller DC gain K(0) =
  -C_k A_k^-1 B_k = 0.14152370536133152; controller poles =
  -1.497097479729129 +/- j 1.7287616223376692.
- Closed loop (plant plus central controller at gamma 1.5): characteristic
  polynomial coefficients (descending) [1, 4.994194959458258,
  15.218307529595396, 22.844450697151888, 20.179513123717761]; Routh
  first column [1, 4.994194959458258, 10.644106705919519,
  13.376260879894057, 20.179513123717758], all strictly positive, so the
  closed loop is Hurwitz.
- Achievement scan (fixed geometric grid w in [1e-3, 1e3] rad/s, 4001
  points): peak of sigma_max Tzw(jw) = 1.4055693346768514 at w =
  1.7318090307501135 rad/s; peak/gamma = 0.93704622311790098; peak <
  gamma holds: True. The synthesized controller achieves the declared
  level.
- Determinism: a second gamma_iteration returns gamma_inf bit-identical;
  the outputs were verified under both the system python3 and the pyenv
  3.13 interpreter, which agree to the printed significant figures
  (last-bit libm roundings only, far inside the 1e-6 contract tolerance).
- ValueErrors with real messages: central_controller at gamma 1.2885
  raises "spectral-radius coupling condition rho(X_inf Y_inf) < gamma^2
  fails: rho = 1.6979121128464851 at gamma = 1.2885 (rho * gamma^-2 =
  1.0226955372337125)"; at gamma 1.28 raises "no stabilizing PSD solution
  of the X_inf algebraic Riccati equation at gamma = 1.28"; at gamma 0.0
  and -2.0 raises "gamma level must be strictly positive: received gamma
  = ..." naming the offending value.

## Verification

- Confirm the gamma-iteration asserts within 1e-6 relative: gamma_inf =
  1.2899416380818218, gamma_lo = 1.2899416380818216, relative bracket
  width at most 1e-9, X_inf and Y_inf equal to the printed entries within
  1e-6 relative, rho at gamma_inf within 1e-6 relative, and the tight-
  coupling identity rho/gamma_inf^2 = 0.99999999899999903 with the
  coupling slack equal to COUPLING_REL_EPS within 1e-3 relative.
- Confirm the working-level asserts within 1e-6 relative: the printed
  X_inf, Y_inf, rho = 0.96499552430796154, F_inf, H_inf, Z_inf, A_k,
  B_k, C_k entries and D_k = [[0.0]]; the coupling margin
  1 - rho/gamma^2 = 0.57111310030757267; both solutions positive
  semidefinite by the closed-form 2x2 eigenvalue formula.
- Confirm the ARE residual asserts at gamma 1.5: Frobenius residuals of
  the X_inf and Y_inf AREs recomputed from the returned solutions below
  1e-9, symmetry residuals below 1e-12.
- Confirm the stabilizing-solution asserts: eigenvalues of A + S_X X_inf
  and of A + Y_inf S_Y at gamma 1.5 all have real part below -1e-3.
- Confirm the closed-loop asserts within 1e-6 relative: the closed-loop
  characteristic polynomial equals the printed coefficients, its Routh
  first column is strictly positive (Hurwitz), the controller poles
  equal -1.497097479729129 +/- j 1.7287616223376692 and the controller DC
  gain equals 0.14152370536133152.
- Confirm the achievement asserts: closed_loop_peak returns peak =
  1.4055693346768514 within 1e-6 relative at w_peak =
  1.7318090307501135 rad/s, peak strictly below gamma = 1.5 and
  peak/gamma = 0.93704622311790098 within 1e-6 relative.
- Confirm the level-probe asserts: the exact reason strings at gamma 1.0,
  1.24, 1.28 and 1.2885 and the feasible verdicts with the printed rho
  values at gamma 1.29, 1.30, 1.40, 2.00 and 4.00, so gamma_inf lies
  strictly between 1.28 and 1.29.
- Confirm the ValueErrors with the real messages quoted in the Worked
  example, each naming the offending value.
- Confirm the module-independent identity asserts from the printed
  numbers: the closed-form 2x2 spectral radius of the printed X_inf Y_inf
  product, the F_inf, H_inf and Z_inf recomputes, the central-controller
  assembly recompute, and the Routh first column of the printed
  closed-loop polynomial.
- Run the contract test offline: python3 scripts/test_h-infinity-synthesis.py
  under both interpreters, deterministic, no imports beyond math, no
  exact-float equality on computed sums, exit 0.

## Related leaves

- gnc-autonomy/control/h-infinity-control: the norm-analysis leaf of the
  pack and this leaf's load-bearing fence. It takes the plant AND the
  candidate controller as given and rates the supplied pair (weighted-
  sensitivity and s-over-ks norms, worst-case-peak-gain search over the
  imaginary axis); its pitfalls renounce synthesis verbatim (quoted in
  the introduction). This leaf takes only the generalized plant and
  PRODUCES the controller by the DGKF two-Riccati synthesis.
- gnc-autonomy/optimal-control/lqr-design: solves the single algebraic
  Riccati equation of LQR state-feedback regulation from a quadratic
  cost; one ARE, no gamma level, no worst-case attenuation, no coupling.
- gnc-autonomy/optimal-control/lqg-design: joins regulator and filter
  AREs by the separation principle to assemble an output-feedback
  compensator; two AREs without a gamma level and without the spectral-
  radius coupling, minimizing the H2 cost.
- gnc-autonomy/optimal-control/loop-transfer-recovery: reshapes a
  recovered LQG loop toward a full-state target loop; it never iterates
  a worst-case level.
- gnc-autonomy/optimal-control/model-predictive-control: receding-horizon
  constrained optimization, no Riccati coupling identity.
- gnc-autonomy/control/observer-design: full-order Luenberger observer
  gain design by pole placement, never a controller synthesis.
- gnc-autonomy/control/state-space-analysis: the state-space toolbox of
  the pack; this leaf works on the fixed two-state normalized problem.
- mu-synthesis and D-K iteration are not siblings: iterative uncertainty-
  model schemes with no deterministic closed form were declined at wave-48
  gate (d); this leaf owns only the deterministic state-space member of
  the robust vein.

## Pitfalls

- Reading this leaf as a norm-analysis review of a supplied plant-
  controller pair: no controller pair is ever given and rated here. The
  S/KS mixed-sensitivity review, the weighted-sensitivity and weighted
  control-sensitivity norms and the worst-case-peak-gain search over the
  imaginary axis of a weighted channel belong to h-infinity-control,
  which renounces this leaf's identity verbatim in its own pitfalls:
  "Reading this leaf as an H-infinity controller synthesis: no controller
  is ever synthesized, tuned, placed or recovered here, and no algebraic
  Riccati equation solver lives in the leaf; the plant, the candidate
  controller and the weight parameters are all given inputs, and the
  review verdict only rates the supplied pair." This leaf owns the
  synthesis that h-infinity-control renounces: the generalized plant is
  the given input and the controller is the output, produced by closed-
  form ARE solutions and the gamma-level iteration.
- Calling central_controller at or below gamma_inf: the gain matrix
  Z_inf = (I - g^-2 Y_inf X_inf)^-1 is unbounded exactly at the optimum,
  the known central-controller singularity; always declare a working
  level strictly above the infimum returned by gamma_iteration.
- Calling the level iteration a gamma iteration over the imaginary axis:
  the gamma-level iteration bisects the Riccati feasibility of the
  generalized plant over the open feasible interval (gamma_inf,
  infinity); it never sweeps the imaginary-axis frequency response of a
  given loop, and that wording and the sibling gamma-iteration tag belong
  to h-infinity-control and must never be used here.
- Expecting plants beyond the pinned two-state normalized problem or
  nonzero D11/D22 feedthrough: the module covers the two-state normalized
  standard problem with real state matrices only, and the D11-feedthrough
  correction of the DGKF formulas reduces to the identity in this
  normalization (D11 = 0); neither the D11-nonzero case nor general
  orders are ever claimed.
- Treating the achievement scan as an H-infinity norm computation: the
  scan is the fixed geometric-grid maximum of the closed-loop response of
  the controller this leaf just synthesized; norm searches over supplied
  loops belong to h-infinity-control.
- Confusing the two-ARE gamma-coupled synthesis with single-ARE or
  uncoupled two-ARE designs: an LQR gain from a quadratic cost has one
  ARE and no gamma level (lqr-design), an LQG compensator joins two AREs
  by the separation principle with no coupling identity (lqg-design),
  and LTR, MPC, observer and mu-synthesis schemes each carry their own
  vocabulary; this leaf iterates the gamma level under the spectral-
  radius coupling only.
- Asserting exact-float equality on computed sums in the contract test:
  use assertAlmostEqual or math.isclose throughout with the 1e-6
  relative contract tolerance; only the pinned literal constants are
  compared exactly.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_h-infinity-synthesis.py

The test covers the pinned module constants of the generalized-plant
fixture (workflow step 1), the are_x_inf and are_y_inf stabilizing
Riccati solutions with their PSD, residual, symmetry and stabilizing-
eigenvalue verdicts (step 2), the gamma_feasible verdict with the exact
reason strings and the spectral-radius-coupling check (step 3), the
gamma_iteration bisection with the tight-coupling identity at gamma_inf
and its determinism (step 4), the central_controller assembly with the
gain and assembly identity recomputes, the controller poles and DC gain
and every ValueError rejection with its real message (step 5), the
closed-loop characteristic polynomial with the Routh-Hurwitz verdict and
the closed_loop_peak achievement scan (step 6), and the module-independent
identity asserts from the printed Worked example numbers, all offline
under both interpreters with exit 0 and no exact-float equality on
computed sums.

## Compliance

- Standards referenced, not reproduced: ARP4754A is a proprietary SAE
  standard (name plus paraphrase only, per standards-map.yaml); the DGKF
  two-Riccati synthesis above is summary-only methodology from Doyle,
  Glover, Khargonekar and Francis, "State-Space Solutions to Standard H2
  and H-infinity Control Problems", IEEE Transactions on Automatic
  Control 34(8):831-847, 1989, with the textbook treatment of Skogestad
  and Postlethwaite, Multivariable Feedback Control (Wiley, 2005,
  chapter 9), the same works the sibling cites.
- compliance: STANDARDS-REF, gated: false.
