# Wave-29 leaf spec: gnss-raim-fde (gnc-autonomy, navigation pack)

- Path: skills/gnc-autonomy/navigation/gnss-raim-fde/
- Pack: navigation (existing siblings: dilution-of-precision,
  gnss-pseudorange-positioning, inertial-navigation, kalman-filter-design,
  navigation-frames)
- Standards ids: rtca-do-229 (reference-only; new id added to
  standards-map.yaml at wave-29 prep). Ledger Standard: rtca-do-229.
- Family: gnc-autonomy

## Claim

Detect and exclude a faulty GNSS satellite from an overdetermined
pseudorange position fix with receiver autonomous integrity monitoring
(RAIM). The leaf builds the geometry matrix H from satellite line of
sight unit vectors, solves the overdetermined least-squares navigation
solution, computes the residual test statistic, compares it against a
chi-square threshold at a chosen false-alarm probability, computes the
horizontal protection level (HPL) from the worst-case satellite slope,
and identifies the faulty satellite for exclusion by the largest
normalized residual. Produces the detection verdict, the HPL, and the
excluded-satellite recommendation that gate an integrity assessment.

Does NOT do: compute the raw position fix and clock bias
(gnss-pseudorange-positioning owns the 4x4 iterated least-squares fix);
compute dilution of precision or elevation-mask subset selection
(dilution-of-precision owns GDOP/PDOP/HDOP and the best-subset search);
estimate vehicle state with a filter over time (kalman-filter-design and
the estimation-filtering leaves own filters); classify GNSS accuracy
from geometry alone. This leaf runs integrity monitoring: detection,
protection level, and fault exclusion on an already-computed
overdetermined geometry.

## Model (implement exactly)

Module constants:
- PFA = 1e-5 (false-alarm probability used for the chi-square threshold).
- SIGMA0 = 6.0 (m, pseudorange 1-sigma noise; also a function argument default).
- G0 = 9.80665 unused here.
All vectors are lists; matrices are lists of lists; all math stdlib.

Functions (pure stdlib, floats):
- geometry_matrix(sat_dirs) -> H: sat_dirs is a list of n unit
  line-of-sight direction vectors (list of [x,y,z]); returns n x 4
  matrix with rows [ux, uy, uz, 1.0]. ValueError if fewer than 5 sats,
  or any vector not length 3, or any vector norm outside 0.999..1.001
  (renormalize internally before use).
- lsq_solve(H, y) -> (x_hat, residuals, sse): solve the n x 4
  overdetermined system by normal equations: N = H^T H (4x4), rhs = H^T
  y, x_hat = N^-1 rhs via Gaussian elimination with partial pivoting
  (implement a small 4x4 solver; do not import numpy). residuals r =
  y - H x_hat (length n); sse = sum r_i^2.
- normal_quantile(p) -> z: standard normal quantile with the Acklam
  rational approximation (piecewise: p < 0.02425 lower tail, middle
  rational, upper tail mirrored). ValueError on p outside (0,1).
- chi2_quantile(df, p) -> x: Wilson-Hilferty approximation
  x = df * (1 - 2/(9 df) + z*sqrt(2/(9 df)))^3 with z =
  normal_quantile(p). ValueError if df < 1.
- fault_detect(sse, n, sigma, pfa=PFA) -> dict: T = sse / sigma^2;
  T_crit = chi2_quantile(n - 4, 1 - pfa); returns {test_statistic: T,
  threshold: T_crit, detected: T > T_crit}. ValueError if n < 5.
- residual_sensitivity(H) -> S: S = I - H (H^T H)^-1 H^T (n x n).
- raim_hpl(H, sigma, pfa=PFA) -> float: A = (H^T H)^-1 H^T (4 x n);
  S = residual_sensitivity(H); for each sat j compute
  slope_j = sqrt(A[0][j]^2 + A[1][j]^2) / sqrt(S[j][j]); HPL =
  max_j(slope_j) * sigma * sqrt(chi2_quantile(n-4, 1-pfa)). ValueError
  if any S[j][j] <= 1e-12.
- exclude_faulty(H, y) -> dict: normalized residual
  nr_i = |r_i| / (sigma * sqrt(S[i][i])); worst index = argmax;
  returns {worst_sat: index, normalized_residuals: list,
  recommended_exclusion: True}. ValueError if n < 6 (need >= 1 spare
  sat after exclusion).
- availability_verdict(hpl, hal) -> str: "available" if hpl <= hal else
  "unavailable".

## Worked example

Six satellites with unit directions (rows of H are these plus the 1.0
clock column):
  u1 = [0.4082, 0.8165, 0.4082]
  u2 = [-0.4082, 0.8165, 0.4082]
  u3 = [0.0, -0.7071, 0.7071]
  u4 = [0.7071, 0.0, 0.7071]
  u5 = [-0.7071, 0.0, 0.7071]
  u6 = [0.0, 0.7071, -0.7071]
True user state x_true = [10.0, -20.0, 30.0, 0.0] m (position offset and
clock bias). Measurement vector y = H x_true + noise + bias, where the
noise is fixed (seed 42, sigma 6.0: [4.0, -7.7, 2.1, -5.5, 6.3, -3.9]
whatever your own seeded draw gives; reproduce by drawing with
random.seed(42) in the module test) and a single-satellite bias of 200 m
is added to sat 1 (index 0).

Deterministic anchors (compute with the exact formulas above; assert
within the stated tolerances):
- chi2_quantile(2, 0.99999) = 24.669 (assert within 0.01).
- chi2_quantile(6, 0.99999) = 34.052 (assert within 0.05).
- normal_quantile(0.99999) = 4.2649 (assert within 1e-3).
- Clean case (no bias): T = 0.143 (assert within 0.01), detected False.
- Bias case (200 m on sat 1): T = 495.2 (assert within 0.5),
  detected True; HPL = 44.5 m (assert within 0.3); worst_sat = 0 with
  normalized residual ~22.3, the largest normalized residual is on the
  biased satellite (margin > 10% over the second-largest ~19.3).
- After excluding sat 0 and re-solving with the remaining 5 sats:
  T = 0.013 (assert within 0.01), detected False.
- availability_verdict(44.5, 556) = "available"; (44.5, 30.0) =
  "unavailable".
- ValueErrors: fewer than 5 sats, non-unit direction vectors, pfa out
  of range, df < 1 in chi2_quantile.

Keep at least 18 test methods: geometry_matrix shape and clock column,
norm rejection, lsq_solve on a small exact system (round-trip), clean
case, bias case detection, HPL anchor, worst-sat identification on the
bias case, exclusion rerun clean, threshold monotonicity in pfa,
chi2_quantile special case df 1 (returns positive), availability
verdicts, ValueErrors. The test must not rely on scipy: the module
implements its own normal and chi-square quantiles.

## Corpus tasks (ids w29-gnss-raim-fde-1/2)

Distinctive tokens: RAIM, receiver autonomous integrity monitoring,
fault detection and exclusion, horizontal protection level, chi-square
threshold, normalized residual, GNSS integrity. Avoid: pseudorange
position fix, iterated least squares fix, receiver clock bias solution
(gnss-pseudorange-positioning); GDOP, PDOP, HDOP, elevation mask,
satellite subset selection (dilution-of-precision); Kalman, filter
state, process noise (kalman-filter-design).

1. "run RAIM fault detection and exclusion on a 6 satellite pseudorange
   set: compute the horizontal protection level and the chi-square
   test statistic at 1e-5 false alarm, then identify the faulty
   satellite by normalized residual"
2. "check GNSS integrity availability: is the horizontal protection
   level below the 556 m non-precision approach alert limit when one
   satellite carries a 200 m bias?"

## SKILL body notes

Pair with gnss-pseudorange-positioning (the fix the monitor guards),
dilution-of-precision (geometry quality), kalman-filter-design
(filtering the protected position). State the DO-229 MOPS boundary:
RAIM protection levels and thresholds are paraphrased, never reproduced
verbatim (gated: true in standards-map.yaml). Mirror the navigation
pack SKILL body style (SI units, stdlib only, deterministic offline).
