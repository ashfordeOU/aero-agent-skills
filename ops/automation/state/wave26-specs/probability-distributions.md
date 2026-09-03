# Wave-26 leaf spec: probability-distributions (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/probability-distributions/
- Pack: numerics (existing siblings include monte-carlo-sampling,
  uncertainty-propagation, least-squares-regression, root-finding,
  numerical-integration)
- Standards ids: naca-tr-824  (Ledger Standard: naca-tr-824)
- Family: cross-cutting

## Claim

Fit and characterize the standard probability distributions used in
aerospace engineering data analysis: estimate parameters for the
normal, lognormal, exponential, and Weibull distributions from a
sample, compute pdf, cdf, quantile, reliability, and hazard functions,
assess the fit with the chi-square and Kolmogorov-Smirnov statistics,
and report percentiles and reliability quantities at a target time.
Produces the fitted parameter dict, the fit-quality verdict, and the
quantile/reliability values that gate the statistical characterization
of scatter data (loads, life, failure times, tolerances).

Does NOT do: draw random samples or histogram a Monte Carlo study
(cross-cutting monte-carlo-sampling owns sampling and histograms),
propagate measurement uncertainties with the GUM law
(uncertainty-propagation), fit a straight line to paired measurements
(least-squares-regression owns linear regression), or build process
control charts (manufacturing-quality as9100 statistical-process-
control owns SPC). This leaf is the distribution-model layer: fit a
named distribution to a univariate sample and evaluate it.

## Model (implement exactly)

Distribution parameter functions (module constants where noted):
- normal: mu = mean(x), sigma = sample std (ddof=1).
- lognormal: fit to log(x): mu_ln, sigma_ln = mean/std of ln(x).
- exponential: rate = 1 / mean(x).
- Weibull: MLE shape via the standard fixed-point equation
  k = [ sum(x^k ln x) / sum(x^k) - mean(ln x) ]^-1 solved by bisection
  on k in [0.05, 10] (module constants WEIBULL_K_MIN, WEIBULL_K_MAX,
  WEIBULL_TOL = 1e-8); scale lambda = (mean(x^k))^(1/k).
CDF / PDF / quantile / reliability / hazard (all closed form with
math.erf for the normal):
- normal cdf: 0.5 * (1 + erf((x - mu) / (sigma * sqrt(2)))).
- normal quantile: the standard Acklam rational approximation
  (implement the published coefficients as module constants); assert
  quantile(cdf(x)) ~ x for the test.
- lognormal quantile: exp(normal quantile of the log-space params).
- exponential cdf: 1 - exp(-rate x); quantile: -ln(1 - p) / rate.
- Weibull cdf: 1 - exp(-(x / lambda)^k); quantile:
  lambda * (-ln(1 - p))^(1/k); reliability R(t) = 1 - cdf;
  hazard h(t) = (k / lambda) * (t / lambda)^(k - 1).
Fit functions:
- fit_distribution(data, dist) -> params dict (dist in {normal,
  lognormal, exponential, weibull}); ValueError when len(data) < 3,
  any value <= 0 for lognormal/exponential/weibull, or any non-finite
  value; ValueError when sigma <= 0.
- pdf(x, dist, params), cdf(x, dist, params), quantile(p, dist,
  params), reliability(t, dist, params), hazard(t, dist, params):
  ValueError on p outside [0, 1] and x <= 0 where the domain requires
  it.
Goodness of fit:
- chi2_gof(data, dist, params, bins=8) -> (stat, df, verdict):
  fixed-width bins over the data range with expected counts from the
  fitted cdf; merge bins with expected < 1 (module constant MIN_EXP);
  verdict PASS when the chi-square statistic <= the module critical
  value table (CRIT_CHI2 = {6: 12.59, 7: 14.07, 8: 15.51, 9: 16.92,
  10: 18.31} for alpha 0.05 keyed by df after merging; ValueError when
  df not in the table).
- ks_gof(data, dist, params) -> (D, verdict): D = max |empirical cdf -
  fitted cdf| over the sorted sample; verdict PASS when D <=
  1.358 / sqrt(n) (large-sample 5% critical value, documented as the
  asymptotic approximation; module constant KS_CRIT_COEF = 1.358).
- summarize(data, dist) -> dict {params, n, chi2_stat, chi2_verdict,
  ks_D, ks_verdict, q05, q50, q95, reliability_at_target (input
  target)}.
ValueError on: empty data, non-finite data, unknown dist name,
p outside [0, 1], t <= 0 for reliability of lognormal/exponential/
weibull.

## Worked example

Sample S = [100.0, 200.0, 300.0, 400.0, 500.0] (hours, e.g. time to
event):
- exponential fit: rate = 1 / 300 = 0.0033333; assert quantile(0.5) =
  -ln(0.5) / rate = 207.944 within 1e-6; reliability(300) = exp(-1) =
  0.367879.
- normal fit on S: mu = 300, sigma = 158.1139 (sample std, ddof 1);
  assert cdf(mu) = 0.5 exactly (within 1e-12) and
  quantile(cdf(400)) ~ 400 within 1e-6.
- Weibull fit on S: shape k > 1 (monotone increasing hazard);
  assert lambda and k satisfy cdf(median) ~ 0.5 within 1e-6 (use the
  module output as the anchor: builder runs the module and asserts the
  computed median from quantile(0.5)).
- Lognormal fit on lognormal-sampled fixed data: use the deterministic
  sample exp([0.0, 0.5, 1.0, 1.5, 2.0]) so mu_ln = 1.0, sigma_ln =
  0.790569; assert quantile(0.5) = exp(1.0) = 2.71828 within 1e-6.
- ks_gof on S against the fitted normal returns a D value and a PASS
  verdict for this small consistent sample (builder asserts the real
  module output).
- chi2_gof on S with bins=8: assert the df and verdict from the real
  module output.
- ValueError on a zero value in a weibull fit and on p = 1.05.
Keep at least 18 test methods (per-distribution fit, pdf/cdf/quantile
round trips, reliability and hazard values, chi2 and KS verdicts,
ValueErrors).

## Corpus tasks (ids w26-probability-distributions-1/2)

Distinctive tokens: probability distribution fitting, weibull fit,
lognormal, exponential fit, goodness of fit, kolmogorov smirnov,
chi-square fit test, quantile estimation, reliability at time, hazard
function, parameter estimation. Avoid: monte carlo sampling, histogram
(mc sibling), linear regression / least squares (sibling), uncertainty
propagation / GUM (sibling), control chart (manufacturing SPC).

1. "fit a weibull distribution to the 1000 hour fatigue life scatter
   data, run the kolmogorov smirnov goodness of fit check, and report
   the reliability at 800 hours with the hazard function"
2. "characterize the measured tolerance scatter with the normal and
   lognormal distributions: estimate the parameters, compute the 5 and
   95 percent quantiles, and score the chi-square fit test verdict"

## SKILL body notes

Pair with monte-carlo-sampling (sample from the fitted distributions
for a study), uncertainty-propagation (input distributions for the GUM
sensitivity analysis), and manufacturing statistical-process-control
(the process side). Worked example uses the module outputs as anchors.
Compliance: naca-tr-824 referenced by name only (reference-only);
no reproduced tables.
