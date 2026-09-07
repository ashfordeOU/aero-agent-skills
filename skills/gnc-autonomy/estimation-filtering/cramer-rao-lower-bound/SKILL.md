---
name: cramer-rao-lower-bound
description: "Use when you must compute the cramer-rao-lower-bound on the variance of an unbiased parametric estimator before data arrives: build the fisher-information-matrix as the negative expected second derivative of the log-likelihood for the scalar dc level in white gaussian noise, the gaussian mean with known variance, the vector gaussian mean with known covariance, the sinusoid phase in noise, or the poisson rate, and invert the information matrix to report the best achievable variance. Produces the fisher information, the scalar variance bound var(theta_hat) >= 1/I(theta) or the covariance bound CRLB = I(theta)^-1, the closed-form variance of the bound-achieving maximum-likelihood estimators, and the estimator efficiency that gate a pre-data estimation accuracy assessment. Trigger: cramer rao lower bound, fisher information matrix, best achievable variance, estimator efficiency, bound achieving estimator."
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
  subdomain: estimation-filtering
  tags: [cramer-rao-lower-bound, fisher-information-matrix, estimator-efficiency, best-achievable-variance, bound-achieving-estimator]
  version: 0.1.0
  author: AeroSkills
---

# Cramer-Rao Lower Bound (gnc-autonomy/estimation-filtering/cramer-rao-lower-bound)

Use when the task is a pre-data accuracy bound for an unbiased
parametric estimator: form the Fisher information as the negative
expected second derivative of the log-likelihood (equivalently the
expected square of the score under the regularity conditions), invert
it to the Cramer-Rao lower bound on estimator variance, and rate a
candidate estimator by its efficiency against that bound.

The CRLB is the classical estimation-theory limit of Kay,
Fundamentals of Statistical Signal Processing: Estimation Theory
(1993), chapter 3, and Van Trees, Detection, Estimation, and
Modulation Theory, Part I (1968). It is the pre-data counterpart of
the recursive filters in this pack: the filter leaves (alpha-beta,
complementary, extended and unscented Kalman, particle, RTS) own the
post-data estimator machinery, and unscented-kalman-filter owns the
post-hoc consistency check of its own filter runs; this leaf bounds the
variance achievable by ANY unbiased estimator from the model alone,
before any data or any estimate exists.

## Domain quick reference

- Log-likelihood and information: for a parametric model p(x; theta)
  the Fisher information is I(theta) = -E[d^2 ln p(x; theta)/d
  theta^2], which under the regularity conditions equals the expected
  score square E[(d ln p/d theta)^2].
- Scalar bound: var(theta_hat) >= 1/I(theta) for any unbiased
  estimator theta_hat. Vector bound: Cov(theta_hat) >= I(theta)^-1 in
  the matrix (PSD) sense, with CRLB = I(theta)^-1 the information
  matrix inverse.
- DC level in white Gaussian noise, x[n] = A + w[n], w ~ N(0, sigma^2),
  n = 0..N-1: the second derivative d^2 ln p/dA^2 = -N/sigma^2 is a
  constant, so I(A) = N/sigma^2 and var(A_hat) >= sigma^2/N. The score
  identity closes exactly: E[(d ln p/dA)^2] = Var((1/sigma^2) sum w[n])
  = N/sigma^2 = I(A).
- Scalar Gaussian mean with KNOWN variance: identical structure,
  I(mu) = n/sigma^2, CRLB = sigma^2/n (the n = 1 model coincides with
  the DC model at n = 1).
- Vector Gaussian mean with KNOWN covariance C, n iid samples:
  I = n C^-1 and Cov(mu_hat) >= I^-1 = C/n in the PSD sense. The 2x2
  inverse is analytic: C^-1 = (1/det) [[d, -b], [-c, a]] for C = [[a,
  b], [c, d]].
- Sinusoid phase, x[n] = A cos(2 pi f0 n + phi) + w[n], A and f0
  known: the exact information at the true phase is I(phi0) =
  (A^2/sigma^2) sum_{n=0}^{N-1} sin^2(2 pi f0 n + phi0) (Kay example
  3.14, small-error regime, 0 < f0 < 0.5). At f0 = 0.25, phi0 = 0 and
  even N the sine-square sum is exactly N/2 (sin^2(pi n/2) is 1 on the
  odd indices and 0 on the even indices), giving the published bound
  var(phi_hat) >= 2 sigma^2/(N A^2). The phase case is a bound only:
  it is approached in the high-SNR regime, no closed-form unbiased
  estimator variance is computed.
- Poisson rate, pmf p(x; lam) = lam^x e^-lam / x!: d ln p/dlam =
  x/lam - 1 and d^2 ln p/dlam^2 = -x/lam^2 with E[x] = lam, so
  I(lam) = 1/lam per observation and n/lam for n iid observations;
  CRLB = lam/n.
- Efficiency: for an unbiased estimator with variance v,
  efficiency = CRLB/v lies in (0, 1] and equals 1 exactly if and only
  if the estimator is bound-achieving, which holds when the score
  factorizes d ln p/dtheta = I(theta) (g(x) - theta) (exponential
  family MLE case). The sample-mean MLEs of the Gaussian, DC and
  Poisson cases are unbiased with variance exactly equal to the CRLB.

## Workflow

1. Identify the model and read off the constants: the sample count N,
   the known noise variance sigma^2 or covariance C, and for the
   phase case the amplitude, digital frequency and true phase. Pick
   the module constants when reproducing the worked scenario
   (N_DC = 100, SIGMA2_DC = 4.0, SIGMA2_GAUSS = 9.0, N_VEC = 50,
   COV_VEC = [[1.0, 0.6], [0.6, 4.0]], N_PH = 64, AMP_PH = 1.0,
   F0_PH = 0.25, PHI0_PH = 0.0, SIGMA2_PH = 0.1, N_POI = 25,
   LAM_POI = 4.0).
2. Form the Fisher information with fisher_info_dc(n, sigma2),
   fisher_info_gauss(n, sigma2), info_matrix_gaussian(n, cov),
   fisher_info_phase(n, amp, f0, phi0, sigma2) or
   fisher_info_poisson(n, lam): the negative expected second
   derivative of the log-likelihood, equal to the expected score
   square for these families. Non-physical inputs (n not a positive
   int, sigma2 or lam non-finite or <= 0, amp zero, f0 outside
   (0, 0.5), non-finite phi0, cov indefinite, asymmetric or singular)
   raise ValueError.
3. Invert the information to the bound with crlb_dc, crlb_gauss,
   crlb_matrix_gaussian, crlb_phase or crlb_poisson: the scalar
   var(theta_hat) >= 1/I(theta) or the covariance matrix CRLB = C/n.
4. When a bound-achieving MLE exists (Gaussian, DC, Poisson), compare
   its closed-form variance with mle_var_dc(n, sigma2) or
   mle_var_poisson(n, lam); it must equal the bound.
5. Rate the candidate estimator with efficiency(crlb, estimator_var):
   1.0 exactly for a bound-achieving estimator, below 1 for any other
   unbiased estimator. Do not fabricate an MLE variance where the
   model has none (the phase case reports the bound only).
6. Sanity-check the result against the 1/N law (crlb_dc(10, 4.0) =
   0.4 is 10 x crlb_dc(100, 4.0) = 0.04) and confirm determinism:
   identical calls return bitwise-identical values, no RNG anywhere.

## Worked example

Scenario: the five canonical cases at the module constants. Real
outputs of scripts/cramer_rao_lower_bound_logic.py, stdlib math only,
identical under python3 3.9.6 and the pyenv 3.13.12 interpreter:

- DC level in WGN, N = 100, sigma^2 = 4.0: I(A) = 25.0,
  CRLB = 0.04 = sigma^2/N, so ANY unbiased estimator of the DC level
  has variance at least 0.04. The sample-mean MLE has variance 0.04
  and efficiency 1.0. The score identity closes: E[(d ln p/dA)^2] =
  N sigma^2/sigma^4 = 25.0 and -E[d^2 ln p/dA^2] = 25.0, and CRLB x
  I = 1.0. A first-sample-only estimator g(x) = x[0] is unbiased with
  variance 4.0, efficiency 0.01 = 1/N: 100 x worse than the bound.
- Scalar Gaussian mean, single sample, sigma^2 = 9.0: I(mu) =
  0.1111111111111111 (= 1/9), CRLB = 9.0; crlb_dc(1, 9.0) = 9.0 (the
  n = 1 models coincide). At n = 100 the bound tightens to 0.09.
- Vector Gaussian mean, C = [[1.0, 0.6], [0.6, 4.0]] (det C = 3.64),
  n = 50: I = 50 C^-1 = [[54.945055, -8.241758], [-8.241758,
  13.736264]] (each entry within 1e-6 relative of 50/3.64 scaled);
  CRLB = C/50 = [[0.02, 0.012], [0.012, 0.08]]. I x CRLB is the
  identity to within 1e-9, and the sample-mean vector estimator
  attains the bound with diagonal efficiencies 1.0 and 1.0.
- Sinusoid phase, A = 1.0, f0 = 0.25, phi0 = 0.0, sigma^2 = 0.1,
  N = 64: the sine-square sum is 32.0 = N/2, I(phi0) = 320.0 and
  CRLB = 2 sigma^2/(N A^2) = 0.003125 = 1/I(phi0) to within 1e-9.
- Poisson rate, n = 25, lam = 4.0: I(lam) = 6.25, CRLB = 0.16 =
  lam/n, MLE variance 0.16, efficiency 1.0. The single-observation
  identities both give 1/lam = 0.25: E[(x/lam - 1)^2] = 1/lam and
  -E[d^2 ln p/dlam^2] = 1/lam.

## Verification

- Deterministic offline checks: every return value is a pure function
  of its arguments; two identical calls are bitwise identical; no RNG,
  no numpy, no scipy, no external processes.
- ValueError rejection: n at 0 and 2.5; sigma2 at 0.0, -1.0 and nan;
  cov indefinite, asymmetric or singular; amp 0.0; f0 at 0.0 and 0.5;
  non-finite phi0; lam at 0.0 and -4.0; efficiency inputs at or below
  0. Every case raises ValueError before any arithmetic.
- Bound semantics: CRLB scales as 1/N (factor 10 per decade of
  samples), every unbiased variance lies at or above its CRLB, and
  efficiency equals 1.0 exactly for the bound-achieving sample-mean
  MLEs of the Gaussian-mean, DC-level and Poisson cases.

## Pitfalls

- Confusing the pre-data CRLB with the post-hoc consistency metric of
  unscented-kalman-filter runs: that statistic is built after a run
  from the estimate and the estimated covariance, while this leaf
  never touches an estimate, a filter covariance or an average over
  repeated runs.
- Claiming an attained variance for the phase case: the sinusoid
  phase bound is approached only in the high-SNR regime; report the
  bound, do not fabricate a closed-form MLE variance.
- Expecting the bound to hold without the regularity conditions: the
  classical bound of Kay chapter 3 assumes the support of p(x; theta)
  does not depend on theta and the derivatives exist and are
  integrable; prior-dependent and sequential bounds are out of scope
  for this classical pre-data bound.
- Reading the vector bound entrywise: Cov(theta_hat) >= C/n is a
  matrix (PSD) inequality, not four independent scalar bounds.
- Mixing up the DC and Gaussian-mean models only at n > 1: they
  coincide exactly at n = 1 (crlb_dc(1, sigma^2) = crlb_gauss(1,
  sigma^2)), which the tests pin.
- Using exact float equality on computed sums: the sine-square sum and
  the matrix inverse are float sums; assert with isclose or tolerance,
  never exact equality (see the exact-float lesson of waves 41-42).
- Treating Fisher information as a hypothesis test on a two-by-two
  table (cross-cutting/numerics/fisher-exact-test) or as the
  linear-system solver of structures/fem/torsion-shear-flow: neither
  is related to the Fisher information or the bound computed here.

## Related leaves

- skills/gnc-autonomy/estimation-filtering/unscented-kalman-filter:
  owns the post-hoc consistency metric of its own filter runs.
- skills/gnc-autonomy/estimation-filtering/extended-kalman-filter,
  particle-filter, rts-smoother, alpha-beta-filter,
  complementary-filter, interacting-multiple-model-filter,
  process-noise-discretization, imu-static-calibration: recursive
  estimator machinery.
- skills/gnc-autonomy/navigation/kalman-filter-design: the linear
  Kalman filter with its forward recursion.
- skills/cross-cutting/numerics/fisher-exact-test: hypothesis test on
  a two-by-two table, unrelated to Fisher information.
- skills/structures/fem/torsion-shear-flow: a linear-system solver,
  unrelated to Cramer-Rao bounds.

## Behavior contract (gate 3)

The Fisher information functions, the CRLB functions, the MLE
variance functions, the efficiency rating, the ValueError rejection of
non-physical inputs, the 1/N bound scaling, the score identity, the
matrix identity I x CRLB, the n = 1 DC/Gaussian coincidence and the
determinism guarantees are exercised by the gate 3 contract test:
scripts/test_cramer_rao_lower_bound.py against
scripts/cramer_rao_lower_bound_logic.py (stdlib unittest, offline,
deterministic, no RNG). Run:

python3 scripts/test_cramer_rao_lower_bound.py

The 34 tests pass under both /usr/bin/python3 (3.9.6) and the pyenv
3.13.12 interpreter used by the pre-push hook. All numeric asserts are
tolerance-based (assertAlmostEqual or math.isclose), never exact float
equality on computed sums.

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.
