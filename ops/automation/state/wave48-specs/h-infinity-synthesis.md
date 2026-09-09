# Wave-48 leaf spec: h-infinity-synthesis (gnc-autonomy, control pack)

- Path: skills/gnc-autonomy/control/h-infinity-synthesis/
- Pack: control (present siblings adaptive-control, control-allocation,
  deadbeat-control, digital-control-design, frequency-response-design,
  gain-scheduling, h-infinity-control, l1-adaptive-control,
  lead-lag-compensation, observer-design, pid-control-design,
  python-control-design, root-locus-design, smith-predictor,
  state-space-analysis; adjacent optimal-control pack lqr-design,
  lqg-design, loop-transfer-recovery, model-predictive-control).
  Zero-owner greps re-verified at spec time at HEAD 3a0931f6:
  `rg -i -l 'dgkf|hinfsyn|two-riccati|h-infinity-synthesis' skills/ -g
  'SKILL.md'` returns ZERO hits (exit 1) and the same tokens return 0 of
  1306 matching tasks in eval/hit1-corpus.yaml (exit 1): no leaf anywhere
  in the tree owns the DGKF two-Riccati state-space H-infinity synthesis,
  which is the exact gap this leaf closes. The only 'h-infinity' text
  tree-wide is gnc-autonomy/control/h-infinity-control plus the family
  router; the only 'riccati' text tree-wide sits in single-ARE contexts
  (lqr-design, lqg-design, loop-transfer-recovery, model-predictive-
  control, ilqr-ddp) and in h-infinity-control itself, which names Riccati
  equations only to renounce them (verbatim quotes under Claim fences).
- Provenance: wave-48 recon receipt task-3 GO rank 1, lines 96-174,
  verdict strong with no conditional gate. The one-line why from the
  receipt: wave-47's own GO4 identity (the DGKF two-Riccati state-space
  H-infinity synthesis) was never built; the h-infinity-control leaf that
  landed is a S/KS norm-analysis leaf that explicitly renounces synthesis
  and Riccati equations, so the two-ARE gamma-level-iteration synthesis is
  still zero-owner tree-wide, zero in the 1306-task corpus, and both
  wordable Hit@1 queries route to the candidate with 17.5+ point margins
  and zero theft (receipt gate (e), sim-verified at probe HEAD 92d84a48:
  Q1 HIT1 at 35.5 vs 11.0 (gnc-autonomy/control/h-infinity-control); Q2
  HIT1 at 27.5 vs 10.0 (gnc-autonomy/control/observer-design); theft audit
  0 of 1306 tasks reroute). GATE PASSED. The receipt's gate (e) query
  wording is copied verbatim under Corpus fragment below and the gate (f)
  tag set is copied verbatim under Description/tag guidance.
- Published deterministic anchor, receipt gate (d) (summary-only): the
  receipt summarized Doyle, Glover, Khargonekar and Francis,
  "State-Space Solutions to Standard H2 and H-infinity Control Problems",
  IEEE Transactions on Automatic Control 34(8):831-847, 1989: given the
  generalized plant with its state matrices and the performance and
  control channels, the suboptimal controller at level gamma exists iff
  two algebraic Riccati equations (X_inf for the regulator side, Y_inf for
  the estimator side) admit positive-semidefinite stabilizing solutions
  with the spectral-radius coupling rho(X_inf Y_inf) < gamma^2; the
  central controller is a closed form in X_inf, Y_inf, F_inf and H_inf
  (the state-feedback and observer gains) with the D11-feedthrough
  correction. Deterministic offline computation: bisect gamma between the
  spectral-radius lower bound and the stabilizing upper bound, solve both
  AREs, form the central controller state matrices. Textbook treatment:
  Skogestad and Postlethwaite, Multivariable Feedback Control (Wiley,
  2005), chapter 9, the same works the sibling cites. SCOPE NOTE (recorded
  assumption): the receipt's gate (d) anchor fixes the DGKF method but
  fixes NO numeric plant; the worked example below is a standard textbook
  two-state example of the normalized standard problem constructed at spec
  time (damped second-order plant, scalar control, scalar measurement,
  scalar performance channel stacked over the control channel), with the
  D11 = 0, D22 = 0 normalization that reduces the D11-feedthrough
  correction to the plain central-controller formulas. The module is
  pinned to the two-state normalized problem (n = 2), which is the
  smallest order at which the two-ARE coupling identity is nontrivial and
  which the pure-stdlib deterministic Riccati solver (Hamiltonian stable-
  invariant-subspace method, closed form for the small fixed order)
  supports without a general-purpose eigensolver package.
- Claim fences (quoted from the sibling SKILL.md frontmatter descriptions
  and bodies at spec time, FRESH reads; the nearest owners fence out the
  norm analysis of a given controller pair, single-ARE regulation,
  separation-principle estimation and receding-horizon optimization, none
  of which is the two-ARE gamma-coupled synthesis):
  - h-infinity-control (this pack) is the LOAD-BEARING ANALYSIS fence: it
    is the wave-47 S/KS norm-analysis leaf whose pitfalls lines 223-227
    renounce this leaf's identity verbatim: "Reading this leaf as an
    H-infinity controller synthesis: no controller is ever synthesized,
    tuned, placed or recovered here, and no algebraic Riccati equation
    solver lives in the leaf; the plant, the candidate controller and the
    weight parameters are all given inputs, and the review verdict only
    rates the supplied pair." Its related-leaves lines 211-214 fence the
    ARE vocabulary verbatim: "lqr-design and lqg-design: solve the
    algebraic Riccati equations of optimal regulation and estimation; this
    leaf computes no Riccati solution and no state-feedback or compensator
    gain." Its frontmatter description closes with "The plant, the
    candidate controller and the weight parameters are given inputs; the
    controller is never synthesized, tuned, placed or recovered here," and
    its compliance lines 269-271 name the DGKF paper only "as synthesis
    context". Its corpus tasks w47-h-infinity-control-1/-2 are pure
    analysis wording (weighted-sensitivity, s-over-ks, worst-case-peak-
    gain over the imaginary-axis sweep), so the synthesis corpus slot is
    empty. The seam: h-infinity-control takes the plant AND the candidate
    controller as given and rates the supplied pair; this leaf takes only
    the generalized plant and PRODUCES the controller.
  - lqr-design (optimal-control pack) is the SINGLE-ARE REGULATOR fence:
    its frontmatter description reads "Use when you must design an LQR
    state-feedback gain matrix for a scalar-input two-state system such as
    spacecraft attitude control: solve the algebraic Riccati equation for
    the cost weights, compute the gain matrix, verify closed-loop stability
    of the regulated system, and assess the Q over R weighting trade." Its
    pitfalls lines 66-67 read "Applying the closed form outside the
    canonical family: a general A and B need a general Riccati solver, not
    this leaf's equations." One ARE of a quadratic cost, no gamma level,
    no worst-case attenuation.
  - lqg-design (optimal-control pack) is the SEPARATION fence: its
    frontmatter description reads "Use when you must design a
    linear-quadratic-Gaussian output-feedback compensator for a two-state
    system whose state is not fully measurable: solve the regulator
    algebraic Riccati equation for the symmetric stabilizing P and the gain
    K from the quadratic cost weights, solve the filter (Kalman) algebraic
    Riccati equation for the error covariance S and the estimator gain L
    from the process and measurement noise covariances, assemble the
    dynamic output-feedback compensator state-space realization, and verify
    the separation principle that the closed-loop eigenvalues are the union
    of the regulator and estimator poles." Two AREs of estimation and
    regulation joined by the separation principle, with no gamma level and
    no spectral-radius coupling; it minimizes the H2 cost, never a
    worst-case gain level.
  - loop-transfer-recovery (optimal-control pack) is the RECOVERY fence:
    its frontmatter description reads "Use when you must run
    loop-transfer-recovery on the LQG loop of the two-state plant family:
    inflate the filter process noise weight q on the driven input channel
    through Qw(q) = Qw0 + q^2 B B^T, re-solve the filter Riccati equation
    for the error covariance and the estimator gain at every q, and compare
    the recovered output loop transfer function with the full-state target
    loop on a log-spaced frequency grid until the grid-max mismatch M(q)
    falls at or below the recovery tolerance." LTR reshapes a recovered LQG
    loop; it never iterates a worst-case level.
  - model-predictive-control (optimal-control pack) is the HORIZON fence:
    receding-horizon constrained optimization, no Riccati coupling
    identity.
  - observer-design (this pack) is the ESTIMATOR fence: full-order
    Luenberger observer gain design by pole placement, never a controller
    synthesis.
  - mu-synthesis and D-K iteration are NOT siblings (declined at wave-48
    gate (d): no single deterministic closed form; the receipt recheck
    reminder for future waves states "further robust members mu-synthesis/
    D-K fail gate d as iterative with no closed form; do not re-probe
    without a closed-form anchor"). This leaf owns only the deterministic
    state-space member of the robust vein.
  The new leaf's generalized plant and weights are GIVEN inputs; the
  output of the leaf IS the controller, produced by closed-form ARE
  solutions and the gamma-level bisection, never by tuning, placing,
  reviewing or recovering.
- Standards id: arp4754a (ARP4754A, Development of Civil Aircraft and
  Systems, reference-only and present in standards-map.yaml, grep
  'id: arp4754a' at line 38, re-verified at spec time; the control-pack
  convention shared with the h-infinity-control, smith-predictor and
  deadbeat-control leaves). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Synthesize the state-space H-infinity controller of the generalized plant
with the DGKF two-Riccati method: given the state matrices (A, B1, B2, C1,
C2) of the normalized standard problem (D11 = 0, D22 = 0, D12' D12 = I,
D21 D21' = I, D12' C1 = 0, B1 D21' = 0, two states), iterate the gamma
level while the two algebraic Riccati equations admit
positive-semidefinite stabilizing solutions and the spectral-radius
coupling rho(X_inf Y_inf) < gamma^2 holds, then form the central
H-infinity controller state matrices from the stabilizing solutions. The
two AREs are the regulator-side equation A'X + XA + X(g^-2 B1 B1' - B2 B2')
X + C1' C1 = 0 (solution X_inf) and the estimator-side equation A Y + Y A'
+ Y(g^-2 C1' C1 - C2' C2) Y + B1 B1' = 0 (solution Y_inf), each solved by
the Hamiltonian stable-invariant-subspace method as a closed-form
deterministic computation for the two-state order; the level iteration
bisects gamma between an infeasible lower point and a feasible upper point
(feasibility is monotone: the feasible set is (gamma_inf, infinity)) and
returns the infimum feasible level gamma_inf, at which the coupling is
tight, rho(X_inf Y_inf) approaching gamma_inf^2 from below. The central
controller is formed at a declared working level gamma_work strictly above
gamma_inf (at gamma_inf itself the gain matrix Z_inf = (I - g^-2 Y_inf
X_inf)^-1 is unbounded, the known central-controller singularity at the
optimum) from the state-feedback gain F_inf = -B2' X_inf, the observer
gain H_inf = -Y_inf C2' and Z_inf, by the closed forms A_k = A + g^-2 B1
B1' X_inf + B2 F_inf + Z_inf H_inf C2, B_k = -Z_inf H_inf, C_k = F_inf,
D_k = 0. Produces the infimum feasible gamma level with the two stabilizing
Riccati solutions and the spectral radius there, the central controller
state matrices at the declared suboptimal level with the coupling margin
rho < gamma_work^2, and the achievement check that the closed loop of the
synthesized controller is Hurwitz and the fixed-grid maximum of the
disturbance-to-output response sigma_max Tzw(jw) stays below gamma_work
(peak-to-level ratio 0.93704622311790098 on the worked example). Does NOT
do: norm analysis of a given controller pair, including the S/KS
mixed-sensitivity review, the weighted-sensitivity and weighted-control-
sensitivity norms of a supplied loop, the worst-case-peak-gain search over
the imaginary axis of a weighted channel and every other verdict of
h-infinity-control (that leaf reviews the plant and candidate controller
it is given; this leaf produces the controller from the plant alone and
never rates a supplied pair); controller tuning, pole placement, gain
scheduling or margin fixing of any kind; single-ARE LQR state-feedback
gain design from a quadratic cost (lqr-design); LQG output-feedback
compensator assembly by the separation principle with process and
measurement noise covariances (lqg-design); loop-transfer recovery toward
a full-state target loop (loop-transfer-recovery); receding-horizon
constrained control (model-predictive-control); observer or estimator gain
design (observer-design); mu-synthesis, D-K iteration, structured singular
value or any iterative uncertainty-model scheme (no closed form, declined
at wave-48 gate (d)); linear matrix inequality formulations; computation
of an H-infinity norm as an analysis identity (the module's achievement
check is a fixed geometric-grid maximum of the closed-loop response of the
controller it just synthesized, not a norm search over a supplied loop).
The module covers the two-state normalized standard problem with real
state matrices only; D11 and D22 feedthrough terms are zero by the
normalization and are never claimed.

## Model (implement exactly)

Pure stdlib (math only), deterministic, no RNG. Every matrix is a list of
lists of float coefficients, row major; vectors are single-column or
single-row matrices as declared. Module constants, pin exactly:
- N_STATES = 2: the state dimension of the generalized plant (the module
  solves the fixed small order; every public function rejects inputs whose
  dimensions depart from the pinned shapes below).
- GAMMA_BISECT_ITER = 80: bisection passes of the gamma-level iteration.
- GAMMA_HI_START = 1.0: first level probed for feasibility in the upward
  expansion.
- GAMMA_HI_CEIL = 1e6: expansion ceiling; no feasible level above it.
- GAMMA_FLOOR = 1e-6: search floor; a problem feasible there is rejected.
- PSD_EPS = 1e-9: smallest-eigenvalue tolerance of the
  positive-semidefinite verdicts on X_inf and Y_inf.
- IMAG_AXIS_EPS = 1e-9: |Re lambda| tolerance below which a Hamiltonian
  eigenvalue counts as imaginary-axis (no stabilizing solution).
- DEFECT_EPS = 1e-12: adjugate-norm tolerance; below it the stable
  subspace is defective and the level is rejected.
- COUPLING_REL_EPS = 1e-9: strictness margin of the coupling condition,
  rho * (1 + COUPLING_REL_EPS) < gamma^2.
- PEAK_W_MIN = 1e-3, PEAK_W_MAX = 1e3 rad/s and PEAK_GRID_POINTS = 4001:
  the geometric grid of the achievement scan of the closed-loop response.
  (The gamma-iteration bisection and the peak scan are the only iterative
  searches; both are deterministic with pinned constants.)

Defining relations (pin these exactly; every function derives from them):
- Generalized plant (normalized standard problem, n = 2): xdot = A x +
  B1 w + B2 u, z = C1 x + D12 u, y = C2 x + D21 w, with w the two-channel
  exogenous input (disturbance channel 1, measurement noise channel 2),
  z the two-channel performance output (scalar performance channel stacked
  over the control channel), u the scalar control, y the scalar
  measurement. Standing normalization: D11 = 0, D22 = 0, D12 = [0; 1]
  (D12' D12 = I, D12' C1 = 0 so C1's second row is zero), D21 = [0 1]
  (D21 D21' = I, B1 D21' = 0 so B1's second column is zero). These
  conditions hold by construction of the inputs; the module does not
  verify them beyond the shape checks.
- X ARE (regulator side): A'X + XA + X S_X X + C1' C1 = 0 with S_X =
  g^-2 B1 B1' - B2 B2'; X_inf is the stabilizing positive-semidefinite
  solution, i.e. A + S_X X_inf has both eigenvalues in the open left half
  plane.
- Y ARE (estimator side): A Y + Y A' + Y S_Y Y + B1 B1' = 0 with S_Y =
  g^-2 C1' C1 - C2' C2; Y_inf is the stabilizing positive-semidefinite
  solution, i.e. A' + S_Y Y_inf has both eigenvalues in the open left half
  plane (dual form of the X ARE with M = A').
- Coupling: the level gamma is feasible exactly when both AREs admit their
  stabilizing positive-semidefinite solutions and the spectral-radius
  coupling rho(X_inf Y_inf) < gamma^2 holds with the strictness margin
  COUPLING_REL_EPS. Feasibility is monotone in gamma: the feasible set is
  the open interval (gamma_inf, infinity).
- Gains and central controller (D11 feedthrough zero): F_inf = -B2'
  X_inf, H_inf = -Y_inf C2', Z_inf = (I - g^-2 Y_inf X_inf)^-1,
  A_k = A + g^-2 B1 B1' X_inf + B2 F_inf + Z_inf H_inf C2,
  B_k = -Z_inf H_inf, C_k = F_inf, D_k = 0. The central controller
  transfer function is K(s) = C_k (s I - A_k)^-1 B_k + D_k, strictly
  proper.
- ARE solution method: for the two-state order the stabilizing solution
  of A'X + XA + X S X + Q = 0 is computed deterministically by the
  Hamiltonian stable-invariant-subspace method: form the real 4x4
  Hamiltonian H = [[A, S], [-Q, -A']]; its characteristic polynomial is
  even, det(lambda I - H) = lambda^4 + c[2] lambda^2 + c[4], with the
  coefficients from the Faddeev-LeVerrier recursion on real arithmetic;
  the four eigenvalues are the square roots of the two roots mu of
  mu^2 + c[2] mu + c[4] = 0 (complex square roots by hand, principal
  branch, math only, no cmath import); the two stable eigenvalues
  (Re lambda < -IMAG_AXIS_EPS (1 + |lambda|)) give the stable invariant
  subspace, each eigenvector being the largest-magnitude column of the
  adjugate of H - lambda I (cofactor arithmetic, no linear solver); X =
  U21 U11^-1 assembled in complex arithmetic over the two stable
  eigenvectors (valid for a complex-conjugate pair), real part taken and
  symmetrized. Verdicts: no stabilizing solution when the Hamiltonian
  carries an imaginary-axis eigenvalue, when fewer or more than two stable
  eigenvalues appear, when the stable pair is repeated within 1e-8
  relative (defective subspace), or when the symmetrized solution fails
  the PSD or stabilizing eigenvalue checks.
- Achievement scan: with the central controller at gamma_work, assemble
  the closed-loop state matrices (state x_cl = [x; x_k]):
  A_cl = [[A, B2 C_k], [B_k C2, A_k]], B_cl = [[B1], [B_k D21]],
  C_cl = [[C1, D12 C_k]], D_cl = 0, and evaluate the largest singular
  value of Tzw(jw) = C_cl (jw I - A_cl)^-1 B_cl at each point of the
  geometric grid w in [PEAK_W_MIN, PEAK_W_MAX] (each complex 4x4 solve by
  Gaussian elimination with partial pivoting, sigma_max of the 2x2 value
  by the closed-form Hermitian eigenvalue formula). The scan reports the
  grid maximum and the frequency of the maximum; it is a verification
  scan of the synthesized loop, not an H-infinity norm computation (norm
  searches over supplied loops belong to h-infinity-control).

Functions (signatures, return shapes, rejections):
- are_x_inf(A, B1, B2, C1, gamma) -> list of lists (2x2 X_inf)
  ValueError when gamma <= 0.0 (message "gamma level must be strictly
  positive: received gamma = ...") and when the X ARE has no stabilizing
  PSD solution at gamma (message "no stabilizing PSD solution of the
  X_inf algebraic Riccati equation at gamma = ..."). Shape rejection
  ValueError when the inputs are not the pinned 2x2, 2x1 or 1x2 forms
  (message names the matrix).
- are_y_inf(A, B1, B2, C1, C2, gamma) -> list of lists (2x2 Y_inf)
  Same ValueErrors, message names the Y_inf algebraic Riccati equation.
- spectral_radius(M) -> float
  Spectral radius of a real 2x2 matrix by the closed form: eigenvalues of
  [[a, b], [c, d]] are (a + d)/2 +/- sqrt(((a - d)/2)^2 + b c) with the
  hand complex square root, radius is the larger magnitude. No rejection
  beyond the shape check.
- gamma_feasible(A, B1, B2, C1, C2, gamma) -> dict
  Returns {"feasible": bool, "reason": str, "x": X or None, "y": Y or
  None, "rho": float or None}. Never raises on an infeasible level.
  reason is exactly one of "", "x-are-no-stabilizing-solution",
  "y-are-no-stabilizing-solution", "spectral-radius-coupling-fails".
  Feasible exactly when both stabilizing PSD ARE solutions exist and
  rho * (1 + COUPLING_REL_EPS) < gamma * gamma.
- central_controller(A, B1, B2, C1, C2, gamma) -> dict
  Returns {"x_inf", "y_inf", "rho", "f_inf", "h_inf", "z_inf", "a_k",
  "b_k", "c_k", "d_k", "gamma"} with the matrices of the relations above.
  ValueError when gamma <= 0.0, when either ARE admits no stabilizing PSD
  solution (messages as in are_x_inf/are_y_inf), and when the coupling
  fails, with the real message "spectral-radius coupling condition
  rho(X_inf Y_inf) < gamma^2 fails: rho = ... at gamma = ... (rho *
  gamma^-2 = ...)" (the spectral-radius coupling rejection).
- gamma_iteration(A, B1, B2, C1, C2) -> dict
  The gamma-level bisection. Expands upward from GAMMA_HI_START by
  doubling until gamma_feasible is True (ValueError "no feasible gamma
  level up to the ceiling 1000000: the generalized plant admits no
  suboptimal H-infinity controller" when the ceiling is crossed), walks
  down by halving to an infeasible point above GAMMA_FLOOR (ValueError
  "generalized plant feasible at the gamma floor 1e-06: rescale the
  problem or lower the floor" when still feasible at the floor), then
  runs GAMMA_BISECT_ITER bisection passes keeping the upper endpoint
  feasible and the lower infeasible. Returns {"gamma_inf": feasible upper
  endpoint, "gamma_lo": infeasible lower endpoint, "x_inf": X at
  gamma_inf, "y_inf": Y at gamma_inf, "rho": rho at gamma_inf}. The
  central controller is NOT formed at gamma_inf (Z_inf unbounded there);
  call central_controller at a declared working level strictly above it.
- closed_loop_peak(A, B1, B2, C1, C2, ctrl) -> dict
  ctrl is a central_controller dict. Assembles the closed-loop matrices
  and returns {"peak": grid maximum of sigma_max Tzw(jw), "w_peak":
  frequency of the maximum} over the pinned geometric grid. Raises
  ValueError only on singular 4x4 solves at a grid point (message
  "singular 4x4 solve").

## Identities to test (closed form, exact; checkable without the builder
module)

- Coupling tight at the infimum: from the printed X_inf, Y_inf and
  gamma_inf of the Worked example, recompute XY = X_inf Y_inf and its
  spectral radius by the closed-form 2x2 formula (both eigenvalues of
  X_inf Y_inf are real and nonnegative, so rho = (tr + sqrt(tr^2 - 4
  det))/2): rho = 1.6639494279932627 against gamma_inf^2 =
  1.6639494296572137, difference 1.663951e-9; equivalently rho/gamma_inf^2 =
  0.99999999899999903 and the coupling slack 1 - rho/gamma_inf^2 equals
  1.0e-9 (COUPLING_REL_EPS to three significant figures): the bisection
  endpoint sits at the spectral-radius lower bound of the feasible set.
- PSD verdicts by the closed-form 2x2 eigenvalue formula on the printed
  entries: both eigenvalues of X_inf and of Y_inf at gamma_inf and at
  gamma 1.5 are nonnegative (X_inf at 1.5 has eigenvalues 3.1552 and
  0.1843 from the printed entries, both positive; Y_inf at 1.5 has 1.6937
  and 0.2224).
- ARE residuals from the printed matrices at gamma 1.5: form A'X + XA +
  X(g^-2 B1 B1' - B2 B2') X + C1' C1 and A Y + Y A' + Y(g^-2 C1' C1 - C2'
  C2) Y + B1 B1' entrywise from the printed X_inf, Y_inf and the pinned
  plant matrices: every entry of both residuals is below 1e-12 (the
  Frobenius residuals printed by the anchor are 7.6918507455342553e-16
  and 9.6148134319178191e-16).
- Symmetry: X_inf = X_inf' and Y_inf = Y_inf' exactly on the printed
  entries (anchor symmetry residuals print as 0).
- Coupling at the working level from the printed matrices at gamma 1.5:
  rho(X_inf Y_inf) = 0.96499552430796154 below gamma^2 = 2.25 with ratio
  0.42888689969242733 and margin 1 - rho/gamma^2 = 0.57111310030757267.
- Gain identities: F_inf = -B2' X_inf and H_inf = -Y_inf C2' recomputed
  from the printed X_inf, Y_inf equal the printed F_inf, H_inf entries;
  Z_inf = (I - g^-2 Y_inf X_inf)^-1 by the closed-form 2x2 inverse from
  the printed X_inf, Y_inf equals the printed Z_inf entries (entrywise
  within 1e-9).
- Central controller assembly: A_k = A + g^-2 B1 B1' X_inf + B2 F_inf +
  Z_inf H_inf C2, B_k = -Z_inf H_inf, C_k = F_inf recomputed from the
  printed X_inf, Y_inf, F_inf, H_inf, Z_inf equal the printed A_k, B_k,
  C_k entries (entrywise within 1e-9); D_k = 0.
- Closed-loop stability by classical Routh-Hurwitz on the printed
  closed-loop characteristic polynomial of the worked loop (coefficients
  [1, 4.994194959458258, 15.218307529595396, 22.844450697151888,
  20.179513123717761]): the Routh first column [1, 4.994194959458258,
  10.644106705919519, 13.376260879894057, 20.179513123717758] is strictly
  positive, so the closed loop is Hurwitz (all first-column elements
  positive is the classical test, no module involved).
- Controller dynamics from the printed matrices: the controller DC gain
  K(0) = -C_k A_k^-1 B_k by the closed-form 2x2 inverse equals
  0.14152370536133152 and the controller poles (eigenvalues of A_k by the
  closed-form 2x2 formula) are -1.497097479729129 +/- j 1.7287616223376692,
  both in the open left half plane.
- Feasibility is monotone in the level on the worked example: at gamma
  1.0, 1.24, 1.25, 1.26 and 1.28 the X ARE admits no stabilizing PSD
  solution; at gamma 1.2885 both AREs solve but the coupling fails with
  rho/gamma^2 = 1.0226955372337125 above 1; at gamma 1.29, 1.30, 1.40,
  2.00 and 4.00 the level is feasible, so gamma_inf = 1.2899416380818218
  lies strictly between 1.28 and 1.29 and the feasible set is the open
  interval (gamma_inf, infinity).

## Worked example

All values below are REAL outputs of the prep anchor
/tmp/w48spec/anchor_hinf_synthesis.py (pure stdlib, math only,
deterministic, no RNG, exit 0), run once and quoted as printed; the
anchor reproduces every number here, and a second run under the same
interpreter returns byte-identical output. The output was verified under
/usr/bin/python3 (3.9.6), ~/.pyenv/versions/3.13.12/bin/python3 and the
session python3; the two modern interpreters agree byte-identically and
3.9.6 differs only in last-bit libm roundings at the 16th significant
figure (never more than ~6e-15 relative, far inside the 1e-6 contract
tolerance; no exact-float equality is used anywhere). Worked problem
(recorded assumption: the receipt's gate (d) anchor fixes no numeric
plant, so the standard textbook two-state normalized example below was
constructed at spec time): the normalized disturbance-rejection problem
on the damped second-order plant with A = [[0, 1], [-4, -2]] (poles
-1 +/- j sqrt(3), wn = 2 rad/s, zeta = 0.5), B1 = [[1, 0], [0, 0]]
(process disturbance w1 of unit intensity on the position channel, second
column zero by B1 D21' = 0), B2 = [[0], [1]] (scalar control u on the
acceleration channel), C1 = [[2, 0], [0, 0]] (performance z = [2 x1; u],
second row zero by D12' C1 = 0), C2 = [[1, 0]] (measurement y = x1 + w2
with unit noise channel). Feasibility probes and the gamma iteration:

- Level probes (anchor output, quoted as printed): gamma 1.00, 1.24,
  1.25, 1.26 and 1.28 all report feasible = False with reason
  'x-are-no-stabilizing-solution' and rho = None; gamma 1.29 reports
  feasible = True with rho = 1.6627132282952146; gamma 1.30 rho =
  1.5207128718101464; gamma 1.40 rho = 1.1109308083000942; gamma 2.00
  rho = 0.73205080756887764; gamma 4.00 rho = 0.60910023020016668.
- gamma_iteration(A, B1, B2, C1, C2): gamma_inf = 1.2899416380818218,
  gamma_lo = 1.2899416380818216, relative bracket width 1.72e-16. X_inf
  at gamma_inf = [[4.8550497046046912, 1.8451689460791623],
  [1.8451689460791623, 1.1203305657836022]]; Y_inf at gamma_inf =
  [[0.69782803015344119, -0.84182902900864276], [-0.84182902900864276,
  1.9323890607421939]]. rho(X_inf Y_inf) = 1.6639494279932627 against
  gamma_inf^2 = 1.6639494296572137: rho/gamma_inf^2 =
  0.99999999899999903 and the coupling margin 1 - rho/gamma_inf^2 =
  1e-09, the tight-coupling identity at the spectral-radius lower bound.
- Central controller at the declared working level gamma = 1.5 (16.3%
  above gamma_inf, well conditioned): X_inf = [[2.8767170729927769,
  0.86600457222455551], [0.86600457222455551, 0.46278834694194487]];
  Y_inf = [[0.57859549850415914, -0.63018940312360749],
  [-0.63018940312360749, 1.33760021698791]]; rho = 0.96499552430796154
  below gamma^2 = 2.25 with rho/gamma^2 = 0.42888689969242733 and
  coupling margin 0.57111310030757267.
- ARE residuals at gamma 1.5: Frobenius residual of the X_inf ARE =
  7.6918507455342553e-16, of the Y_inf ARE = 9.6148134319178191e-17;
  symmetry residuals of X_inf and Y_inf both print as 0.
- Stabilizing solutions at gamma 1.5: eigenvalues of A + S_X X_inf =
  -0.5921237128059108 +/- j 1.799860933560131; eigenvalues of A + Y_inf
  S_Y = -0.7749906394706048 +/- j 1.7290168825537666 (both pairs in the
  open left half plane).
- Gains: F_inf = -B2' X_inf = [-0.86600457222455551,
  -0.46278834694194487]; H_inf = -Y_inf C2' = [-0.57859549850415914,
  0.63018940312360749]; Z_inf = [[1.8840094153375413,
  0.18126028353826662], [-0.56649451713616139, 0.97916244503312322]].
- Central controller state matrices at gamma 1.5: A_k = [[-0.53140661251631349,
  1.0], [-3.9211755978858096, -2.4627883469419447]], B_k =
  [0.97585105696075791, -0.94482897433874635], C_k = [-0.86600457222455551,
  -0.46278834694194487], D_k = 0. Controller DC gain K(0) =
  -C_k A_k^-1 B_k = 0.14152370536133152; controller poles =
  -1.497097479729129 +/- j 1.7287616223376692.
- Closed loop (plant plus central controller at gamma 1.5): closed-loop
  characteristic polynomial coefficients (descending) [1,
  4.994194959458258, 15.218307529595396, 22.844450697151888,
  20.179513123717761]; Routh first column [1, 4.994194959458258,
  10.644106705919519, 13.376260879894057, 20.179513123717758]; closed
  loop Hurwitz = True.
- Achievement scan (fixed grid w in [1e-3, 1e3] rad/s, 4001 geometric
  points): peak of sigma_max Tzw(jw) = 1.4055693346768514 at w =
  1.7318090307501135 rad/s; peak/gamma = 0.93704622311790098; peak <
  gamma holds: True. The synthesized controller achieves the declared
  level: the worst disturbance-to-noise gain of the closed loop stays
  below gamma = 1.5.
- Closed-loop DC gains for context: w1 (disturbance) channel T(0) =
  [1.0366786509892463, 0.073357301978492384]; w2 (noise) channel T(0) =
  [0.073357301978492384, 0.14671460395698477].
- Determinism: a second gamma_iteration returns gamma_inf bit-identical.
- ValueErrors with real messages (module output, quoted as printed):
  central_controller at gamma 1.2885 (below gamma_inf) raises
  "spectral-radius coupling condition rho(X_inf Y_inf) < gamma^2 fails:
  rho = 1.6979121128464851 at gamma = 1.2885 (rho * gamma^-2 =
  1.0226955372337125)" (the coupling rejection); at gamma 1.28 raises
  "no stabilizing PSD solution of the X_inf algebraic Riccati equation at
  gamma = 1.28"; at gamma 0.0 raises "gamma level must be strictly
  positive: received gamma = 0.0" and at gamma -2.0 raises "gamma level
  must be strictly positive: received gamma = -2.0".

Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w48spec/anchor_hinf_synthesis.py
(stdlib math only, deterministic, exit 0, no exact-float equality
anywhere). The D11-feedthrough correction of the receipt's gate (d)
summary is the identity in this normalization (D11 = 0), and the module
never claims the D11-nonzero case.

## Validation list (contract test must include)

1. gamma-iteration asserts within 1e-6 relative (module run):
   gamma_iteration(A, B1, B2, C1, C2) on the worked plant returns
   gamma_inf = 1.2899416380818218, gamma_lo = 1.2899416380818216, a
   relative bracket width at most 1e-9, X_inf and Y_inf equal to the
   printed Worked example entries within 1e-6 relative, and rho at
   gamma_inf = 1.6639494279932627 within 1e-6 relative.
2. Tight-coupling identity: rho/gamma_inf^2 = 0.99999999899999903 within
   1e-6 relative and gamma_inf^2 - rho = 1.663951e-9 within 1e-3 relative;
   the coupling slack 1 - rho/gamma_inf^2 equals COUPLING_REL_EPS to
   within 1e-3 relative (the endpoint sits at the spectral-radius lower
   bound).
3. Working-level asserts within 1e-6 relative: central_controller at
   gamma 1.5 returns the printed X_inf, Y_inf, rho = 0.96499552430796154,
   F_inf, H_inf, Z_inf, A_k, B_k, C_k entries and D_k = [[0.0]]; the
   coupling margin 1 - rho/gamma^2 = 0.57111310030757267 within 1e-6
   relative; both X_inf and Y_inf are positive semidefinite (closed-form
   2x2 eigenvalues all above -PSD_EPS).
4. ARE residual asserts at gamma 1.5: Frobenius residual of the X_inf ARE
   below 1e-9 and of the Y_inf ARE below 1e-9 (module recomputes the
   residuals from the returned solutions; the printed values are 7.7e-16
   and 9.6e-17); symmetry residuals of X_inf and Y_inf below 1e-12.
5. Stabilizing-solution asserts: eigenvalues of A + S_X X_inf and of
   A' + S_Y Y_inf (equivalently A + Y_inf S_Y) at gamma 1.5 all have real
   part below -1e-3 (printed -0.5921237128059108 and -0.7749906394706048);
   the module's PSD and stabilizing verdicts hold.
6. Closed-loop asserts within 1e-6 relative: the closed-loop
   characteristic polynomial of the plant plus the central controller at
   gamma 1.5 equals [1, 4.994194959458258, 15.218307529595396,
   22.844450697151888, 20.179513123717761], its Routh first column is
   strictly positive (closed loop Hurwitz), and the controller poles
   equal -1.497097479729129 +/- j 1.7287616223376692 (real part
   negative).
7. Achievement asserts: closed_loop_peak on the gamma 1.5 controller
   returns peak = 1.4055693346768514 within 1e-6 relative at w_peak =
   1.7318090307501135 rad/s, peak is strictly below gamma = 1.5, and
   peak/gamma = 0.93704622311790098 within 1e-6 relative; the controller
   DC gain K(0) = -C_k A_k^-1 B_k = 0.14152370536133152 within 1e-6
   relative.
8. Level-probe asserts: gamma_feasible returns feasible = False with
   reason "x-are-no-stabilizing-solution" at gamma 1.0, 1.24 and 1.28,
   feasible = False with reason "spectral-radius-coupling-fails" at gamma
   1.2885 (rho/gamma^2 = 1.0226955372337125 above 1), and feasible = True
   with reason "" at gamma 1.29, 1.30, 1.40, 2.00 and 4.00; gamma_inf
   lies strictly between 1.28 and 1.29.
9. ValueErrors with the real messages quoted in the Worked example:
   the spectral-radius coupling rejection at gamma 1.2885
   ("spectral-radius coupling condition rho(X_inf Y_inf) < gamma^2
   fails: rho = 1.6979121128464851 at gamma = 1.2885 (rho * gamma^-2 =
   1.0226955372337125)"), the X_inf ARE rejection at gamma 1.28, and the
   strictly-positive gamma rejection at gamma 0.0 and gamma -2.0; each
   names the offending value.
10. Module-independent identity asserts from the printed numbers (pure
    arithmetic, tolerance 1e-6 relative or 1e-9 entrywise as stated in
    Identities): the coupling tightness at gamma_inf, the ARE residuals
    of the printed X_inf and Y_inf at gamma 1.5, the closed-form 2x2
    spectral radius of the printed X_inf Y_inf product, the F_inf/H_inf/
    Z_inf recomputes, the central controller assembly recompute, the
    Routh first column of the printed closed-loop characteristic
    polynomial, and the K(0) and controller-pole closed forms.
11. Determinism: identical outputs run to run under a given interpreter
    (gamma_iteration and central_controller return bit-identical values
    on a repeat run); no randomness anywhere; no imports beyond math; the
    module constants N_STATES = 2, GAMMA_BISECT_ITER = 80,
    GAMMA_HI_START = 1.0, GAMMA_HI_CEIL = 1e6, GAMMA_FLOOR = 1e-6,
    PSD_EPS = 1e-9, IMAG_AXIS_EPS = 1e-9, DEFECT_EPS = 1e-12,
    COUPLING_REL_EPS = 1e-9, PEAK_W_MIN = 1e-3, PEAK_W_MAX = 1e3 and
    PEAK_GRID_POINTS = 4001 fixed as above. No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.
12. Run the deterministic contract test offline (no network); it exits 0.
    Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3). The prep anchor output was
    verified at spec time: byte-identical reruns under the session
    python3 and under 3.13.12, and agreement with the 3.9.6 run to the
    15 significant figures printed (last-bit libm differences only,
    within the 1e-6 tolerance).

## Corpus fragment (eval/hit1-wave48-h-infinity-synthesis.yaml)

Query 1 (copy verbatim, the gate-passing text from the receipt gate (e)):
  "synthesize the state-space h-infinity controller with the
  dgkf-two-riccati method: iterate the gamma-level while the two
  algebraic-riccati equations admit stabilizing-solutions and the
  spectral-radius-coupling stays below gamma-squared, then form the
  central-h-infinity-controller from the stabilizing-solutions"
  intent: "gnc-autonomy/control; h-infinity-synthesis: the DGKF
  two-Riccati state-space H-infinity controller of the generalized plant,
  iterating the gamma level while the two algebraic Riccati equations
  admit stabilizing solutions and the spectral-radius coupling stays below
  gamma squared, then forming the central H-infinity controller from the
  stabilizing solutions"
  expected_skill: "gnc-autonomy/control/h-infinity-synthesis"
Query 2 (copy verbatim):
  "run the h-infinity-synthesis for the generalized-plant: solve the
  x-infinity and y-infinity algebraic-riccati equations under the
  spectral-radius-coupling check and assemble the central-h-infinity-
  controller state matrices from the state-feedback gain and the observer
  gain"
  intent: "gnc-autonomy/control; h-infinity-synthesis: the X_inf and
  Y_inf algebraic Riccati equations of the generalized plant under the
  spectral-radius-coupling check, assembling the central H-infinity
  controller state matrices from the state-feedback gain F_inf and the
  observer gain H_inf"
  expected_skill: "gnc-autonomy/control/h-infinity-synthesis"
Task ids: w48-h-infinity-synthesis-1 and -2. Sim-verified margins at
probe time (deterministic router over the real index plus the candidate):
Q1 HIT1 at 35.5 vs 11.0 (gnc-autonomy/control/h-infinity-control), margin
24.5; Q2 HIT1 at 27.5 vs 10.0 (gnc-autonomy/control/observer-design),
margin 17.5. Theft audit with the candidate added to the index over all
1306 existing corpus tasks: 0 tasks reroute. The sibling corpus tasks
w47-h-infinity-control-1/-2 are pure analysis wording (weighted-
sensitivity, s-over-ks, worst-case-peak-gain, imaginary-axis frequency
sweep) and carry no dgkf, two-riccati, x-infinity, y-infinity,
central-h-infinity-controller, state-feedback-gain or observer-gain token
(re-verified by corpus grep at spec time: 0 of 1306 tasks carry dgkf or
two-riccati); the other sibling tasks route on tuning and margin language
(pid-control-design), bode and gain-margin language (frequency-response-
design), Riccati-and-gain-matrix language (lqr-design), compensator and
separation-principle language (lqg-design), recovery language (loop-
transfer-recovery) and horizon language (model-predictive-control). Add
one fence line to h-infinity-control's related leaves and one router row
to skills/gnc-autonomy/SKILL.md at build time pointing DGKF two-Riccati
synthesis, X_inf/Y_inf Riccati solution and central-controller questions
to the new leaf (the smith-predictor and deadbeat-control precedents).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must synthesize the state-space
h-infinity controller of the generalized plant with the dgkf two-Riccati
method:" and include the outputs in the Claim order (the infimum feasible
gamma level found by the gamma-level bisection over the two algebraic
Riccati equations with the spectral-radius coupling check, the two
stabilizing positive-semidefinite Riccati solutions X_inf and Y_inf, the
central H-infinity controller state matrices formed from the state-
feedback gain F_inf and the observer gain H_inf with the Z_inf correction
at the declared suboptimal level, and the closed-loop achievement check
that the disturbance-to-output peak stays below the level), then close
with the Trigger list. The plant state matrices and the performance and
control channels are given inputs; the controller is the OUTPUT of the
leaf, produced by closed-form Riccati solutions and the gamma-level
iteration, and is never reviewed, tuned or placed; refer to the iteration
as the gamma-level iteration over the Riccati feasibility of the
generalized plant, never as a gamma iteration over the imaginary axis of a
given loop and never as an S/KS or weighted-sensitivity analysis; never
reproduce ARP4754A or any textbook text (reference-only). First tag:
h-infinity-synthesis. Metadata tags EXACTLY the receipt gate (f) set,
nothing else: h-infinity-synthesis, dgkf-two-riccati,
gamma-level-iteration, spectral-radius-coupling,
central-h-infinity-controller, state-space-h-infinity-synthesis,
algebraic-riccati-synthesis. 50-150 words, <=1000 chars, no em dash,
action verb present. Recommended wording (135 words, 983 chars, verified
at spec time):

"Use when you must synthesize the state-space h-infinity controller of the
generalized plant with the dgkf two-Riccati method: given the state matrices
and the performance and control channels, iterate the gamma level while the
x-infinity and y-infinity algebraic Riccati equations admit stabilizing
positive-semidefinite solutions and the spectral-radius coupling stays below
gamma squared, then form the central h-infinity controller state matrices
from the state-feedback gain and the observer gain. Produces the infimum
feasible gamma level from the bisection, the two stabilizing Riccati
solutions with the coupling check, the central controller state matrices at
the working suboptimal level, and the closed-loop stability check with the
disturbance-to-output peak below that level. Trigger: h infinity synthesis,
dgkf two riccati, gamma level iteration, spectral radius coupling, central
h infinity controller, x infinity y infinity riccati, state feedback gain,
observer gain."

FORBIDDEN TOKENS (belong to siblings or out of scope): any S/KS or
mixed-sensitivity ANALYSIS wording of a supplied loop, including
mixed-sensitivity, s-over-ks, weighted-sensitivity,
weighted-control-sensitivity, control-effort-weight, sensitivity-weight,
worst-case-peak-gain of a weighted channel, imaginary-axis-frequency-
response, gamma-iteration over the imaginary axis, norm-analysis,
h-infinity-norm as a review identity, and any claim that the leaf rates,
verdicts or reviews a given plant-controller pair (h-infinity-control owns
the norm analysis of the pair it is given; this leaf owns the synthesis
that h-infinity-control's pitfalls lines 223-227 renounce; in particular
the sibling tag gamma-iteration and the sibling wording "gamma iteration"
must never appear, only gamma-level-iteration over Riccati feasibility);
lqr, linear-quadratic-regulator, regulator-riccati, gain-matrix, q-over-r
and any single-ARE state-feedback claim (lqr-design); linear-quadratic-
gaussian, kalman-filter, separation-principle, filter-riccati-gain,
noise-covariance, compensator-transfer-function and any separation-
principle output-feedback compensator (lqg-design, whose two AREs carry
no gamma level and no coupling); loop-transfer-recovery, full-state-loop-
recovery, recovery-gain, grid-max-mismatch (loop-transfer-recovery);
mpc, receding-horizon, prediction-horizon, quadratic-program
(model-predictive-control); luenberger, estimator-gain, ackermann,
observability (observer-design); mu-synthesis, d-k-iteration,
structured-singular-value and any iterative uncertainty-model scheme
(declined at gate d; no closed form); lmi, linear-matrix-inequality,
semidefinite-program; tuning, pole-placement, gain-scheduling, margin-
fixing of a controller; any claim that the module computes an H-infinity
norm (only the fixed-grid achievement scan of the synthesized loop lives
here) or covers plants beyond the pinned two-state normalized problem or
nonzero D11/D22 feedthrough. Never the bare single words h-infinity,
riccati, coupling, controller, synthesis, gamma, plant, state-feedback,
observer or gain as standalone metadata tags.
