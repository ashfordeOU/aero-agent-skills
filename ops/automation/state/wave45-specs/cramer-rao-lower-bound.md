# Wave-45 leaf spec: cramer-rao-lower-bound (gnc-autonomy, estimation-filtering pack)

- Path: skills/gnc-autonomy/estimation-filtering/cramer-rao-lower-bound/
- Pack: estimation-filtering (present siblings alpha-beta-filter,
  complementary-filter, extended-kalman-filter, imu-static-calibration,
  interacting-multiple-model-filter, particle-filter,
  process-noise-discretization, rts-smoother, unscented-kalman-filter;
  adjacent fences in cross-cutting/numerics/fisher-exact-test, whose
  categorical contingency-table test is the only other 'fisher'
  frontmatter owner in the tree, and structures/fem/torsion-shear-flow,
  whose "solved by Cramer's rule" line is a linear-system solver, not
  Cramer-Rao).
- Provenance: wave-45 probe receipt task-6 GO rank 3, gates (a)-(f)
  verbatim anchor: "(d) Published deterministic anchor: Fisher information
  I(theta) = -E[d^2 ln p(x; theta) / d theta^2] and the Cramer-Rao lower
  bound var(theta_hat) >= 1 / I(theta), vector form CRLB = I(theta)^-1,
  with the equality cases (DC level in white Gaussian noise: var >=
  sigma^2 / N). Equation family: log-likelihood second-derivative
  identity, information matrix inversion. Source: Kay, Fundamentals of
  Statistical Signal Processing: Estimation Theory (1993) chapter 3; Van
  Trees, Detection, Estimation, and Modulation Theory, Part I (1968).
  Deterministic offline closed form for the canonical scalar and vector
  cases." Corpus tokens of the leaf (gate f, all hyphenated compounds):
  cramer-rao-lower-bound, fisher-information-matrix, estimator-efficiency,
  best-achievable-variance, bound-achieving-estimator.
- Claim fences (quoted from the sibling frontmatter and body at prep;
  none of them claims the PRE-DATA variance bound, which is a different
  quantity from the recursive, post-hoc, or categorical objects they own):
  - unscented-kalman-filter (this pack) OWNS the post-hoc consistency
    metric of its own filter runs: its body reads "NEES: normalized
    estimation error squared, (x_est - x_true)^T P_est^-1 (x_est -
    x_true). Its expected value is n for a consistent filter; averaged
    over many Monte Carlo runs NEES should sit near n" (SKILL.md lines
    60-63), and its frontmatter description claims "the NEES consistency
    metric that gate a nonlinear estimation assessment". NEES is computed
    AFTER data with the estimated covariance P_est of a run. This leaf
    computes the variance bound BEFORE data from the model alone, never
    touches an estimate, a filter covariance or a Monte Carlo average.
  - extended-kalman-filter, kalman-filter-design (navigation pack),
    alpha-beta-filter, complementary-filter, particle-filter,
    rts-smoother, interacting-multiple-model-filter and
    process-noise-discretization (this pack) own recursive estimator
    machinery (predict-update recursions, covariance recursion, sigma
    points, particles, smoothing passes, van Loan discretization); none
    of them owns a Fisher information matrix or a variance bound.
  - cross-cutting/numerics/fisher-exact-test OWNS Fisher's EXACT
    categorical hypothesis test on a 2x2 contingency table (its w38
    corpus tasks ask for "the exact two-tailed p-value"); that 'fisher'
    is the categorical test, unrelated to Fisher information.
  - structures/fem/torsion-shear-flow owns "solved by Cramer's rule"
    (line 54), a linear-system solver; unrelated to Cramer-Rao.
  Whole-tree greps at prep: cramer-rao-lower-bound and
  fisher-information-matrix return ZERO hits in eval/hit1-corpus.yaml
  (the only fisher task tokens are the w38 fisher-exact-test categorical
  tasks, grep count of cramer 0 across all 1238 tasks), ZERO hits across
  skills/ (fresh grep 'cramer-rao|fisher-information' over all SKILL.md
  files returns 0, and 'cramer|fisher information' returns only the
  torsion-shear-flow Cramer's-rule line; fresh in-pack grep 'cramer|
  fisher information|crlb|variance bound' over
  skills/gnc-autonomy/estimation-filtering returns 0), and ZERO hits in
  the wave45-specs files written so far. GENUINE gnc-autonomy gap (GO 3):
  the filter leaves own recursive estimators and the UKF owns the
  post-hoc NEES check, but no leaf computes the classical pre-data
  Cramer-Rao lower bound from Fisher information.
- Standards id: arp4754a (reference-only, present in standards-map.yaml
  at line 38; SAE ARP is proprietary, name + paraphrase only, no
  reproduced text). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Compute the classical Cramer-Rao lower bound (CRLB) on the variance of
unbiased parametric estimators BEFORE any data is observed: form the
Fisher information I(theta) = -E[d^2 ln p(x; theta)/d theta^2], which
under the regularity conditions equals the expected square of the score
E[(d ln p/d theta)^2], for the canonical scalar and vector estimation
problems pinned in the probe receipt: the DC level in white Gaussian
noise (x[n] = A + w[n], w ~ N(0, sigma^2), n = 0..N-1), the scalar
Gaussian mean with known variance, the vector Gaussian mean with known
covariance (information matrix I = n C^-1), the sinusoid phase in white
Gaussian noise (small-error regime of Kay example 3.14), and the Poisson
rate (discrete pmf). Report the scalar bound var(theta_hat) >= 1/I(theta)
or the vector bound Cov(theta_hat) >= I(theta)^-1 in the matrix sense
(CRLB = I^-1 is the information matrix inverse), the closed-form variance
of the bound-achieving maximum-likelihood estimators where one exists
(the sample mean of the Gaussian/DC/Poisson cases is unbiased with
variance exactly equal to the CRLB), and the estimator efficiency
CRLB/var(theta_hat) in (0, 1] that equals 1 exactly when the estimator
attains the bound. Produces the Fisher information (scalar or 2x2
matrix), the CRLB (variance or covariance matrix), the bound-achieving
MLE variance and the efficiency that gate a pre-data estimation accuracy
assessment. Does NOT do: the NEES consistency statistic or any Monte
Carlo average over filter runs (unscented-kalman-filter owns NEES, a
post-data quantity built from estimates and the estimated covariance);
any recursive estimator, predict-update pass, Kalman gain, innovation
covariance, sigma-point or particle propagation (extended-kalman-filter,
unscented-kalman-filter, kalman-filter-design, alpha-beta-filter,
complementary-filter, particle-filter, rts-smoother,
interacting-multiple-model-filter, process-noise-discretization);
estimating parameters from data arrays (no data, no RNG, no Monte
Carlo); the Bayesian posterior Cramer-Rao bound or any prior-dependent
bound (this leaf is the classical pre-data bound of Kay chapter 3 under
the regularity conditions); Fisher's exact categorical hypothesis test
(cross-cutting/numerics/fisher-exact-test); or solving linear systems by
Cramer's rule (structures/fem/torsion-shear-flow). Deterministic,
offline, stdlib math only: explicit scalar arithmetic, no numpy, no
scipy, no RNG, no external processes.

## Model (implement exactly)

Pure stdlib, math only. No numpy, no scipy, no RNG, no external
processes, no external solvers. Deterministic: plain explicit scalar
arithmetic in the pinned order below. Module name
cramer_rao_lower_bound.

Module constants (pin exactly; the worked scenario):
- N_DC = 100 (samples of the DC level in WGN), SIGMA2_DC = 4.0 (noise
  variance, sigma = 2.0).
- SIGMA2_GAUSS = 9.0 (known variance of the scalar Gaussian, single
  sample canonical).
- N_VEC = 50 (iid samples of the vector Gaussian),
  COV_VEC = [[1.0, 0.6], [0.6, 4.0]] (known 2x2 covariance; sx = 1.0,
  sy = 2.0, correlation rho = 0.3, det C = 3.64).
- N_PH = 64 (samples of the sinusoid), AMP_PH = 1.0 (amplitude),
  F0_PH = 0.25 (digital frequency in cycles/sample, strictly inside
  (0, 0.5) so the Kay small-error regime applies), PHI0_PH = 0.0 (true
  phase), SIGMA2_PH = 0.1 (noise variance).
- N_POI = 25 (iid Poisson observations), LAM_POI = 4.0 (rate).

Defining relations (pin exactly; every function derives from these):
- Log-likelihood of the DC level in WGN: x[n] = A + w[n], n = 0..N-1,
  w ~ N(0, sigma^2). ln p(x; A) = -(1/(2 sigma^2)) sum (x[n] - A)^2 -
  (N/2) ln(2 pi sigma^2). d ln p/dA = (1/sigma^2) sum (x[n] - A); the
  second derivative d^2 ln p/dA^2 = -N/sigma^2 is a constant, so
  I(A) = -E[d^2 ln p/dA^2] = N/sigma^2 and the CRLB is
  var(A_hat) >= sigma^2/N. The score identity holds exactly:
  E[(d ln p/dA)^2] = Var((1/sigma^2) sum w[n]) = N sigma^2 / sigma^4 =
  N/sigma^2 = I(A).
- Scalar Gaussian mean: x ~ N(mu, sigma^2) with KNOWN variance, n iid
  samples. Same structure as the DC case: I(mu) = n/sigma^2,
  CRLB = sigma^2/n. The single-sample canonical (n = 1): I = 1/sigma^2,
  CRLB = sigma^2; the maximum-likelihood estimator is the sample mean,
  unbiased with variance sigma^2/n = CRLB (bound-achieving).
- Vector Gaussian mean: x ~ N(mu, C) with KNOWN covariance C (pinned
  2x2), n iid samples. Per-sample ln p = -(1/2)(x - mu)^T C^-1 (x - mu)
  + const, so the p x p information matrix is I = n C^-1 and the CRLB is
  the covariance bound Cov(mu_hat) >= I^-1 = C/n in the matrix (PSD)
  sense. The sample-mean vector estimator has covariance exactly C/n:
  bound-achieving componentwise. The 2x2 inverse is analytic:
  C^-1 = (1/det) [[d, -b], [-c, a]] for C = [[a, b], [c, d]].
- Sinusoid phase: x[n] = A cos(2 pi f0 n + phi) + w[n], A and f0 known,
  phi unknown; the mean m[n](phi) has derivative -A sin(2 pi f0 n + phi),
  so the exact Fisher information evaluated at the true phase phi0 is
  I(phi0) = (A^2/sigma^2) sum_{n=0}^{N-1} sin^2(2 pi f0 n + phi0) (Kay
  example 3.14, small-error regime, f0 away from 0 and 0.5, enforced as
  0 < f0 < 0.5). For N even at f0 = 0.25 and phi0 = 0 the sum is exactly
  N/2 (sin^2(pi n/2) is 1 on the N/2 odd indices and 0 on the N/2 even
  indices), so the published bound var(phi_hat) >= 2 sigma^2/(N A^2)
  equals 1/I(phi0) exactly at the worked point. The phase case is a
  bound only: no simple closed-form unbiased estimator variance is
  computed, the bound is approached in the high-SNR regime.
- Poisson rate: pmf p(x; lam) = lam^x e^-lam / x!. d ln p/dlam = x/lam -
  1 (zero mean, variance 1/lam per observation); d^2 ln p/dlam^2 =
  -x/lam^2 with E[x] = lam, so I(lam) = -E[d^2 ln p/dlam^2] =
  E[(d ln p/dlam)^2] = 1/lam per observation and n/lam for n iid
  observations; CRLB = lam/n. The sample-mean MLE is unbiased with
  variance lam/n = CRLB (bound-achieving).
- Efficiency: for an unbiased estimator with variance v,
  efficiency = CRLB/v lies in (0, 1] and equals 1 exactly if and only if
  the estimator is bound-achieving, which holds when the score can be
  written d ln p/dtheta = I(theta) (g(x) - theta) for some statistic g
  (exponential-family MLE case, Kay chapter 3).

Functions (public API, 13):
- fisher_info_dc(n, sigma2) -> N/sigma^2 (scalar). ValueError if n is
  not a positive int, or sigma2 non-finite or <= 0.
- crlb_dc(n, sigma2) -> sigma^2/N. Same ValueErrors.
- mle_var_dc(n, sigma2) -> sigma^2/N (variance of the sample-mean MLE
  of the DC level, unbiased). Same ValueErrors.
- fisher_info_gauss(n, sigma2) -> n/sigma^2. Same ValueErrors.
- crlb_gauss(n, sigma2) -> sigma^2/n. Same ValueErrors.
- info_matrix_gaussian(n, cov) -> [[I11, I12], [I21, I22]] = n C^-1.
  ValueError if n not a positive int; cov not finite, not symmetric
  (|cov[0][1] - cov[1][0]| > 1e-12 * max(1, |cov[0][1]|)), or not
  positive definite (det <= 0).
- crlb_matrix_gaussian(n, cov) -> [[c11, c12], [c21, c22]] = C/n (the
  bound covariance matrix). Same ValueErrors as info_matrix_gaussian
  (the inverse is validated but not returned).
- fisher_info_phase(n, amp, f0, phi0, sigma2) ->
  (amp^2/sigma^2) * sum_{k=0}^{n-1} sin^2(2 pi f0 k + phi0), the exact
  information at the true phase. ValueError if n not a positive int;
  amp non-finite or 0; f0 non-finite or outside the open interval
  (0, 0.5); phi0 non-finite; sigma2 non-finite or <= 0.
- crlb_phase(n, amp, sigma2) -> 2 sigma^2/(n amp^2), the small-error
  bound (exact at the pinned f0 = 0.25, phi0 = 0, even n). ValueError
  if n not a positive int; amp non-finite or 0; sigma2 non-finite or
  <= 0.
- fisher_info_poisson(n, lam) -> n/lam. ValueError if n not a positive
  int; lam non-finite or <= 0.
- crlb_poisson(n, lam) -> lam/n. Same ValueErrors.
- mle_var_poisson(n, lam) -> lam/n (variance of the sample-mean MLE of
  the rate, unbiased). Same ValueErrors.
- efficiency(crlb, estimator_var) -> crlb/estimator_var. ValueError if
  either argument non-finite or <= 0.

Private helpers (module-internal): _inv2x2(cov) returning the analytic
2x2 inverse and _matmul2x2(A, B) used only by the worked-example matrix
identity. Every public function validates its inputs and raises
ValueError with the messages above before computing. Explicit scalar
arithmetic throughout; no matrix library.

Identities to test (tolerance-based asserts only, no exact float
equality on computed sums):
- DC level: I(A) = N/sigma^2 = 100/4 = 25.0 and CRLB = sigma^2/N = 0.04
  (real anchor); the CRLB is 1/I(A) to float precision (product 1.0).
- Score identity: E[(d ln p/dA)^2] = N sigma^2/sigma^4 = N/sigma^2 =
  25.0, equal to -E[d^2 ln p/dA^2] = 25.0 (real anchor; exact for the
  Gaussian family, not asymptotic).
- Efficiency semantics: the sample-mean MLE of the DC level is unbiased
  with variance sigma^2/N, so efficiency = 1.0 exactly (real anchor); an
  estimator that keeps only the first sample, x[0], is unbiased with
  variance sigma^2 = 4.0, efficiency = 0.01 = 1/N, above the bound.
- Scalar Gaussian: single sample with sigma^2 = 9 gives I(mu) =
  0.1111111111111111 (= 1/9) and CRLB = 9.0 (real anchor); n = 100 gives
  CRLB = 0.09; crlb_dc(1, sigma^2) equals crlb_gauss(1, sigma^2) for any
  sigma^2 (the DC and Gaussian-mean models coincide at n = 1).
- Vector Gaussian: I = n C^-1 with the analytic inverse; CRLB = C/n
  entrywise; I times CRLB is the identity to within 1e-9 (real anchor
  0.9999999999999999 on the diagonal); the sample-mean vector estimator
  has covariance C/n = CRLB, so both diagonal efficiencies are 1.0.
- Sinusoid phase: at f0 = 0.25, phi0 = 0, even N, sum sin^2(pi k/2) =
  N/2 exactly (real anchor 32.0), I(phi0) = (A^2/sigma^2)(N/2) = 320.0
  and CRLB = 2 sigma^2/(N A^2) = 0.003125 = 1/I(phi0) (real anchor).
- Poisson: I(lam) = n/lam = 6.25, CRLB = lam/n = 0.16, MLE variance
  0.16, efficiency 1.0 (real anchor); the single-observation pmf
  identities E[(x/lam - 1)^2] = 1/lam and -E[d^2 ln p/dlam^2] = 1/lam
  both equal 0.25 at lam = 4 (real anchor).
- Scaling: crlb_dc(10, 4.0) = 0.4 = 10 x crlb_dc(100, 4.0) = 0.04: the
  bound tightens by the factor 10 per decade of samples (1/N law).
- Determinism: two identical calls are bitwise identical; no RNG
  anywhere; no imports beyond math.
- ValueErrors across the module: n = 0 and n = 2.5, sigma2 at 0.0, -1.0
  and nan; an indefinite cov [[1.0, 0.6], [0.6, -4.0]] and an asymmetric
  cov [[1.0, 0.6], [0.7, 4.0]] and a singular cov [[1.0, 0.6], [0.6,
  0.0]]; amp at 0.0; f0 at 0.0 and 0.5; phi0 non-finite; lam at 0.0 and
  -4.0; efficiency at (0.0, 1.0) and (1.0, -1.0).

## Worked example

Scenario (all values below are REAL outputs of the prep anchor
/tmp/w45spec/anchor_cramer_rao_lower_bound.py, stdlib math only, exit 0,
all checks passed; the same file runs identically under python3 3.9.6
and the pyenv 3.13.12 interpreter). The five canonical cases at the
module constants:

- DC level in WGN, N = 100 samples, sigma^2 = 4.0: I(A) = 25.0
  (= N/sigma^2 = 100/4), CRLB = 0.04 (= sigma^2/N = 4/100) so ANY
  unbiased estimator of the DC level has variance at least 0.04; the
  sample-mean MLE has variance exactly 0.04 and efficiency 1.0
  (bound-achieving). The score identity closes exactly: E[(d ln p/dA)^2]
  = Var((1/sigma^2) sum w[n]) = 25.0 and -E[d^2 ln p/dA^2] = 25.0, and
  CRLB x I = 1.0. A naive estimator that uses only the first sample,
  g(x) = x[0], is unbiased with variance 4.0, efficiency 0.01 = 1/N: the
  bound is real and the sample mean is 100 x better in variance.
- Scalar Gaussian mean, known variance, single sample sigma^2 = 9.0:
  I(mu) = 0.1111111111111111 (= 1/9), CRLB = 9.0; crlb_dc(1, 9.0) = 9.0
  (the n = 1 DC and Gaussian-mean models coincide). With n = 100 samples
  the bound tightens to crlb_gauss(100, 9.0) = 0.09.
- Vector Gaussian mean, known covariance C = [[1.0, 0.6], [0.6, 4.0]]
  (sx = 1.0, sy = 2.0, rho = 0.3, det C = 3.64), n = 50 iid samples:
  C^-1 = (1/3.64) [[4.0, -0.6], [-0.6, 1.0]] and the information matrix
  I = 50 C^-1 = [[54.945054945054942, -8.2417582417582409],
  [-8.2417582417582409, 13.736263736263735]] (the off-diagonal is
  negative because the correlation couples the two means). CRLB =
  I^-1 = C/50 = [[0.02, 0.012], [0.012, 0.080000000000000002]]: any
  unbiased estimator of the mean vector has covariance at least this in
  the PSD sense. I x CRLB = [[0.9999999999999999, 0.0], [0.0,
  0.9999999999999999]] (the identity to 1e-16), and the sample-mean
  vector estimator attains the bound: its covariance is C/50, diagonal
  efficiencies 1.0 and 1.0.
- Sinusoid phase, A = 1.0, f0 = 0.25, phi0 = 0.0, sigma^2 = 0.1,
  n = 64 (even): sum sin^2(2 pi f0 k + phi0) = 32.0, exactly N/2
  (sin^2(pi k/2) = 1 on the 32 odd indices, 0 on the 32 even), so
  I(phi0) = (A^2/sigma^2) x 32 = 320.0 and CRLB = 2 sigma^2/(n A^2) =
  0.003125, which equals 1/I(phi0) exactly at this point. The phase
  bound is approached, not attained, by any simple estimator in the
  general case; the leaf reports the bound and does not claim a
  closed-form phase estimator variance.
- Poisson rate, n = 25 observations, lam = 4.0: I(lam) = 6.25
  (= n/lam = 25/4), CRLB = 0.16 (= lam/n = 4/25); the sample-mean MLE
  has variance exactly 0.16 and efficiency 1.0 (bound-achieving). The
  single-observation pmf identities both give 1/lam = 0.25: E[(x/lam -
  1)^2] = Var(x)/lam^2 = 1/lam and -E[d^2 ln p/dlam^2] = E[x]/lam^2 =
  1/lam.
- Bound semantics across the cases: CRLB scales as 1/N (crlb_dc(10,
  4.0) = 0.4 vs crlb_dc(100, 4.0) = 0.04, factor 10 per decade of
  samples), every unbiased variance lies at or above its CRLB (0.04 <=
  4.0 in the DC case), and efficiency equals 1.0 exactly for the
  bound-achieving sample-mean estimators of the Gaussian-mean, DC-level
  and Poisson cases (real anchor values).
Run your module and take the real outputs as assert targets
(tolerance-based); the anchors above are real prep outputs of
/tmp/w45spec/anchor_cramer_rao_lower_bound.py (stdlib math, exit 0
under both interpreters).

## Validation list (contract test must include)

- DC level: fisher_info_dc(100, 4.0) = 25.0, crlb_dc(100, 4.0) = 0.04,
  mle_var_dc(100, 4.0) = 0.04, all within 1e-6 relative; efficiency(0.04,
  0.04) = 1.0; crlb_dc(100, 4.0) x fisher_info_dc(100, 4.0) = 1.0 within
  1e-12; the first-sample-only estimator has variance 4.0 and efficiency
  0.01 = 1/N within 1e-6.
- Score identity: the closed-form score variance N sigma^2/sigma^4 =
  25.0 equals -E[d^2 ln p/dA^2] = N/sigma^2 = 25.0 within 1e-9.
- Scalar Gaussian: fisher_info_gauss(1, 9.0) = 0.1111111111111111 within
  1e-6 relative; crlb_gauss(1, 9.0) = 9.0 within 1e-6; crlb_gauss(100,
  9.0) = 0.09 within 1e-6; crlb_dc(1, 9.0) = crlb_gauss(1, 9.0) within
  1e-9.
- Vector Gaussian: info_matrix_gaussian(50, [[1.0, 0.6], [0.6, 4.0]]) =
  [[54.945054945054942, -8.2417582417582409], [-8.2417582417582409,
  13.736263736263735]] within 1e-6 relative per entry;
  crlb_matrix_gaussian(50, ...) = [[0.02, 0.012], [0.012, 0.08]] within
  1e-6 relative; I x CRLB is the identity within 1e-9 per entry; the
  sample-mean vector estimator covariance C/50 gives diagonal
  efficiencies 1.0 within 1e-6.
- Sinusoid phase: fisher_info_phase(64, 1.0, 0.25, 0.0, 0.1) = 320.0
  within 1e-6 relative; the phase sum (I x sigma^2/amp^2) = 32.0 = N/2
  within 1e-6; crlb_phase(64, 1.0, 0.1) = 0.003125 within 1e-6 relative
  and equals 1/I within 1e-9 (isclose, never exact-float equality on the
  summed sine squares).
- Poisson: fisher_info_poisson(25, 4.0) = 6.25, crlb_poisson(25, 4.0) =
  0.16, mle_var_poisson(25, 4.0) = 0.16 within 1e-6 relative; the
  single-observation identities 1/lam = 0.25 on both the score-square
  and the negative-second-derivative forms.
- Bound semantics: crlb_dc(10, 4.0) = 0.4 = 10 x crlb_dc(100, 4.0) =
  0.04 within 1e-6 relative; efficiency of the first-sample-only DC
  estimator (crlb 0.04, variance 4.0) = 0.01.
- Determinism: two identical calls are bitwise identical in every return
  value; no RNG anywhere; no imports beyond math.
- ValueErrors (deterministic): n at 0 and 2.5 on every n-argument
  function; sigma2 at 0.0, -1.0 and nan on the variance-argument
  functions; cov [[1.0, 0.6], [0.6, -4.0]] (indefinite), [[1.0, 0.6],
  [0.7, 4.0]] (asymmetric) and [[1.0, 0.6], [0.6, 0.0]] (singular) on
  the vector functions; amp at 0.0; f0 at 0.0 and 0.5 and sigma2 at 0.0
  on the phase functions; lam at 0.0 and -4.0 on the Poisson functions;
  efficiency at (0.0, 1.0) and (1.0, -1.0). Every case raises
  ValueError.
- Run the contract test under BOTH interpreters, /usr/bin/python3 3.9.6
  and ~/.pyenv/versions/3.13.12/bin/python3 (the prep anchor exits 0
  with identical output on both). All asserts are tolerance-based with
  assertAlmostEqual or math.isclose, NEVER exact float equality on
  computed sums.

## Corpus fragment (eval/hit1-wave45-cramer-rao-lower-bound.yaml)

Query 1 (copy verbatim from the receipt gate (e)):
  "compute the cramer-rao-lower-bound for the scalar dc level in
  gaussian noise: build the fisher-information-matrix and report the
  best achievable variance"
  intent: "gnc-autonomy; cramer-rao-lower-bound on the scalar dc level
  in gaussian noise: build the fisher-information-matrix and report the
  best achievable variance of the estimator"
  expected_skill: "gnc-autonomy/estimation-filtering/cramer-rao-lower-bound"
Query 2 (copy verbatim from the receipt gate (e)):
  "check whether the maximum likelihood estimator reaches the
  cramer-rao-lower-bound: compare the sample covariance to the
  fisher-information-matrix inverse and report the estimator efficiency"
  intent: "gnc-autonomy; cramer-rao-lower-bound attainment check:
  compare the sample covariance of the maximum likelihood estimator to
  the fisher-information-matrix inverse and report the estimator
  efficiency"
  expected_skill: "gnc-autonomy/estimation-filtering/cramer-rao-lower-bound"
Task ids: w45-cramer-rao-lower-bound-1 and -2. Prep grep:
cramer-rao-lower-bound, fisher-information-matrix, estimator-efficiency,
best-achievable-variance and bound-achieving-estimator appear in NO
existing eval/hit1-corpus.yaml task (grep count of cramer 0 across all
1238 tasks; the only fisher task tokens are the w38 fisher-exact-test
categorical tasks), in NO skill file (whole-tree 'cramer-rao|fisher-
information' count 0; the sole 'cramer|fisher information' hit is the
torsion-shear-flow Cramer's-rule solver line), and in NO wave45-specs
file written so far; the UKF tasks route on sigma points, the scaled
unscented transform and the NEES consistency metric, the EKF tasks on
Jacobian linearization, the kalman-filter-design tasks on the covariance
recursion, the fisher-exact-test tasks on the 2x2 categorical p-value
and the torsion tasks on shear-flow stress, so the queries above are
collision-free (theft audit in the receipt: 0 of 1238 tasks reroute).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the
cramer-rao-lower-bound on the variance of an unbiased parametric
estimator before data arrives:" and include the outputs in the Claim
(Fisher information, variance or covariance bound, bound-achieving MLE
variance, estimator efficiency). First tag: cramer-rao-lower-bound.
Additional tags ONLY, the exact gate (f) set:
fisher-information-matrix, estimator-efficiency, best-achievable-
variance, bound-achieving-estimator. NEVER single generic words
(estimation, estimator, variance, bound, noise, gaussian, information,
matrix, efficiency, accuracy, filter, data, sample, mean alone) and
NEVER the sibling-owned compounds: unscented-kalman-filter,
sigma-points, scaled-unscented-transform, innovation-covariance,
kalman-gain, nonlinear-estimation, state-prediction, measurement-update,
nees, bearing-range-tracking (unscented-kalman-filter, which owns the
plain nees tag and the NEES post-hoc consistency claim);
extended-kalman-filter, ekf, jacobian-linearization (extended-kalman-
filter); alpha-beta-filter, complementary-filter, mahony-filter,
particle-filter, rts-smoother, interacting-multiple-model,
process-noise-discretization, van-loan, imu-static-calibration (the rest
of the estimation-filtering pack); kalman-filter-design,
covariance-recursion (navigation/kalman-filter-design); fisher-exact-
test, contingency-table, categorical, p-value (cross-cutting/numerics/
fisher-exact-test); cramers-rule, torsion, shear-flow (structures/fem/
torsion-shear-flow). 50-150 words, <=1000 chars, no em dash, no
content-policy sweep term, action verb present. Recommended wording
(outputs in Claim order, measured 125 words and 913 chars, no em dash):
"Use when you must compute the cramer-rao-lower-bound on the variance of
an unbiased parametric estimator before data arrives: build the
fisher-information-matrix as the negative expected second derivative of
the log-likelihood for the scalar dc level in white gaussian noise, the
gaussian mean with known variance, the vector gaussian mean with known
covariance, the sinusoid phase in noise, or the poisson rate, and invert
the information matrix to report the best achievable variance. Produces
the fisher information, the scalar variance bound var(theta_hat) >=
1/I(theta) or the covariance bound CRLB = I(theta)^-1, the closed-form
variance of the bound-achieving maximum-likelihood estimators, and the
estimator efficiency that gate a pre-data estimation accuracy
assessment. Trigger: cramer rao lower bound, fisher information matrix,
best achievable variance, estimator efficiency, bound achieving
estimator." The sibling phrase triggers "NEES", "normalized estimation
error squared", "Monte Carlo", "sigma points", "scaled unscented
transform", "Kalman gain", "innovation covariance", "extended Kalman",
"particle filter", "RTS smoother", "alpha beta filter", "interacting
multiple model", "Cramer's rule", "Fisher's exact test", "posterior
Cramer-Rao" and "Bayesian" must not appear as routing keywords; "Fisher
information" and "Cramer-Rao lower bound" are the leaf's own identity
and must stay, referring only to the classical pre-data bound of Kay
chapter 3, never to a recursive covariance, a posterior bound or a
categorical test.

FORBIDDEN TOKENS (belong to siblings): NEES, normalized estimation
error squared, Monte Carlo, sigma points, scaled unscented transform,
innovation covariance, Kalman gain, state prediction, measurement
update, nonlinear estimation, the tag nees (unscented-kalman-filter);
extended Kalman, Jacobian linearization (extended-kalman-filter);
predict update, covariance recursion, alpha beta, complementary filter,
Mahony, particle filter, RTS smoother, interacting multiple model, van
Loan, IMU calibration (estimation-filtering pack and
navigation/kalman-filter-design); Fisher's exact test, contingency
table, categorical, two-tailed p-value (cross-cutting/numerics/
fisher-exact-test); Cramer's rule, torsion, shear flow (structures/fem/
torsion-shear-flow); posterior Cramer-Rao, Bayesian bound, recursive
bound, sequential estimation (no sibling owns these; they are out of
scope for the classical pre-data bound). The outputs of this leaf are
the Fisher information scalar or matrix, the Cramer-Rao variance or
covariance bound, the closed-form variance of the bound-achieving
maximum-likelihood estimators and the estimator efficiency of the
canonical scalar and vector cases; no output is a NEES statistic, a
filtered estimate, a Monte Carlo average, a Kalman gain, a posterior
bound or a categorical p-value.
