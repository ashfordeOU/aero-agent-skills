# Wave-42 leaf spec: gnss-carrier-smoothing (gnc-autonomy, navigation pack)

- Path: skills/gnc-autonomy/navigation/gnss-carrier-smoothing/
- Pack: navigation (present siblings navigation-frames, inertial-navigation,
  dilution-of-precision, kalman-filter-design, gnss-pseudorange-positioning,
  gnss-raim-fde, ins-gnss-integrated-filter; adjacent fences read at prep
  from the gnss-pseudorange-positioning, gnss-raim-fde and
  kalman-filter-design SKILL.md frontmatter and bodies).
- Claim fences (quoted from the sibling frontmatter/body at prep; none owns
  temporal code-carrier smoothing of a pseudorange stream):
  - gnss-pseudorange-positioning (this pack) is a SINGLE-EPOCH snapshot: its
    description reads "compute a GNSS receiver position fix from pseudorange
    measurements: given satellite positions in ECEF and their pseudoranges
    (geometric range plus receiver clock bias), solve the four-unknown
    navigation equations for x, y, z and clock bias with an iterated
    least-squares adjustment and 4x4 normal equation solves", and its body
    states "The leaf is a snapshot solution: no smoothing, no dynamics model,
    and the geodetic conversion uses a spherical Earth approximation only."
    It consumes raw code pseudoranges at one epoch and smooths no range over
    time.
  - gnss-raim-fde (this pack) guards that snapshot set: its description reads
    "run receiver autonomous integrity monitoring (RAIM) fault detection and
    exclusion on an overdetermined GNSS pseudorange measurement set: build
    the geometry matrix H from satellite line-of-sight unit vectors...",
    and its body frames the convention "following the RTCA DO-229 MOPS
    protection level concepts in paraphrased summary form". It operates per
    measurement epoch on the raw residual set and performs no carrier-phase
    smoothing and no divergence estimation.
  - kalman-filter-design (this pack) is scalar discrete-time state
    estimation: its description reads "design or run a discrete-time Kalman
    filter for single-axis state estimation in SI units: predict the state
    and its error covariance through the dynamics model, compute the
    innovation and innovation variance, calculate the Kalman gain, and
    correct the state and covariance from a noisy measurement." Its recursion
    carries a dynamics model f and process noise q; the Hatch recursion is a
    measurement-domain low-pass with no dynamics model and no q/r covariance
    tuning.
  Whole-tree greps at prep: "carrier-phase smoothing|code-carrier|hatch"
  hit only manufacturing-quality/additive (LPBF laser hatch spacing and
  overlap - material processing, disjoint domain, bare-token noise); exact
  re-grep "carrier[- ]phase smoothing|code[- ]carrier|carrier[- ]code
  divergence" = 0 files in skills/. GENUINE gnc-autonomy gap (fresh probe):
  no leaf runs the first-order Hatch recursion on a code pseudorange stream,
  states its steady-state noise closed form, or runs the code-carrier
  ionospheric divergence monitor.
- Standards id: rtca-do-229 (reference-only, present in standards-map.yaml;
  DO-229 MOPS is the GNSS airborne equipment standard whose carrier-smoothing
  and divergence-monitoring concepts this leaf paraphrases in summary form,
  never reproducing MOPS text). Ledger Standard: rtca-do-229.
- Family: gnc-autonomy

## Claim

Smooth GNSS code pseudorange measurements with carrier-phase delta ranges as
a measurement preprocessor for navigation: run the first-order Hatch
recursion s_k = alpha*c_k + (1 - alpha)*(s_(k-1) + (phi_k - phi_(k-1))) at
the smoothing time constant alpha = T/tau over a code pseudorange stream
carried between epochs by the precise carrier delta range; close the
steady-state code-noise reduction with the exact closed form
sigma_smoothed = sigma_code*sqrt(alpha/(2 - alpha)), identify the textbook
sigma_code/sqrt(2*tau/T) form as its small-alpha limit (exact identity
approx = exact*sqrt((2 - alpha)/2)), and add the carrier delta-range noise
term (1 - alpha)*sigma_carrier/sqrt(alpha*(2 - alpha)) for the total
smoothed-noise verdict; and run the code-carrier ionospheric divergence
monitor, which fits the least-squares slope of the code-carrier difference
over a trailing window, predicts the steady-state smoothed-minus-code bias
-rate*(tau - T) that a linear ionospheric divergence rate induces, and
alarms when that bias exceeds the threshold. Produces the smoothed range
time series, the noise-reduction verdict (code-only std, quoted limit,
carrier term, total std, improvement factor) and the divergence alarm that
gate a smoothed pseudorange before it feeds positioning. Does NOT do: the
single-epoch position fix and receiver clock bias (gnss-pseudorange-
positioning, snapshot, explicitly "no smoothing"); RAIM detection, fault
detection and exclusion, or protection levels on the raw measurement set
(gnss-raim-fde); scalar Kalman predict/correct with a dynamics model,
process noise and innovation variance (kalman-filter-design); DOP geometry
quality reads (dilution-of-precision). Continuous carrier phase between
epochs is assumed; cycle-slip repair and integer ambiguity resolution are
out of scope.

## Model (implement exactly)

Pure stdlib, math only, deterministic recursion, closed-form noise and
slope fits. Defaults: tau = 100.0 s (smoothing time constant), T = 1.0 s
(update interval), sigma_code = 0.3 m, sigma_carrier = 0.003 m, divergence
window 60 epochs, alarm threshold 1.0 m.

Defining relations (pin these exactly; every function derives from them):
- Hatch gain: alpha = T/tau in (0, 1), so the recursion pole (1 - alpha)
  lies in (0, 1) and the variance relaxation e-folding is about tau/2.
- Hatch recursion: s_0 = c_0; for k >= 1,
  s_k = alpha*c_k + (1 - alpha)*(s_(k-1) + (phi_k - phi_(k-1))). The code
  measurement is low-pass filtered while the carrier delta range bridges
  epochs, so a code bias (ionosphere, noise) is smoothed out over tau while
  the fast, precise carrier motion is followed.
- Steady-state noise closed form (IIR variance: an input fed with weight w
  to the pole-(1-alpha) recursion contributes w^2/(1 - (1-alpha)^2) =
  w^2/(alpha*(2 - alpha)) times its variance):
  - code term: alpha^2/(alpha*(2-alpha))*sigma_code^2, so the exact
    code-only std is sigma_code*sqrt(alpha/(2 - alpha));
  - the textbook sigma_code/sqrt(2*tau/T) equals sigma_code*sqrt(alpha/2),
    the tau >> T limit, and the exact identity
    approx = exact*sqrt((2 - alpha)/2) holds, with relative gap
    (exact - approx)/exact = alpha/4 + alpha^2/32 + alpha^3/128 + ...
    (from 1 - sqrt(1 - alpha/2)), about alpha/4 = 0.0025 at alpha = 0.01;
  - carrier term: (1 - alpha)^2*sigma_carrier^2/(alpha*(2 - alpha)), std
    (1 - alpha)*sigma_carrier/sqrt(alpha*(2 - alpha));
  - total std = sqrt(code-term variance + carrier-term variance); the two
    noise inputs are independent per epoch.
- Ionospheric divergence: the code is delayed by +I while the carrier is
  advanced by -I, so the code-carrier difference D_k = code_k - phi_k =
  2*I_k and its rate dD/dt = 2*dI/dt. A first-order Hatch filter lags a
  linear ramp: solving the recursion at steady state under I_k = v*k*T
  gives the smoothed-minus-code error -2*v*(tau - T) = -rate*(tau - T)
  exactly (rate = dD/dt); the classic 2*dI/dt*tau result is the tau >> T
  form of the same relation.

Functions:
- alpha_from_time_constant(tau=100.0, T=1.0) -> float, T/tau.
  ValueError if tau or T is non-finite, tau <= 0, T <= 0, or T >= tau
  (alpha >= 1 means no smoothing).
- hatch_update(prev_smoothed, code, carrier_delta_range, alpha) -> float,
  alpha*code + (1 - alpha)*(prev_smoothed + carrier_delta_range).
  ValueError if alpha is outside (0, 1) or any argument is non-finite.
- run_hatch_smoother(codes, carrier_phases, tau=100.0, T=1.0) -> list,
  smoothed range series; s_0 seeds with codes[0] and each later epoch uses
  the phase increment carrier_phases[k] - carrier_phases[k-1].
  ValueError if the lists differ in length, are empty, hold non-finite
  values, or tau/T fails alpha_from_time_constant.
- code_noise_std_smoothed(alpha, sigma_code) -> float,
  sigma_code*sqrt(alpha/(2 - alpha)), the exact code-only steady-state std.
  ValueError if alpha is outside (0, 1) or sigma_code is non-finite or
  <= 0.
- noise_reduction_verdict(tau=100.0, T=1.0, sigma_code=0.3,
  sigma_carrier=0.003) -> dict with keys alpha, code_only_std (exact closed
  form), approx_std (sigma_code/sqrt(2*tau/T) limit), carrier_term_std,
  total_std and improvement_factor = sigma_code/total_std. ValueErrors as
  above plus sigma_carrier <= 0 or non-finite.
- iono_divergence_rate(code_carrier_diffs, tau=100.0, T=1.0, window=60)
  -> float, the least-squares slope of the trailing window of the
  code-carrier difference per epoch, divided by T, in m/s. Closed-form
  slope: (n*sum(k*y_k) - sum(k)*sum(y))/(n*sum(k^2) - sum(k)^2) over the
  window. ValueError if window is not an int >= 2, window exceeds the
  available epoch count, tau/T fails, or any difference is non-finite.
- smoothed_iono_bias(rate, tau=100.0, T=1.0) -> float,
  -rate*(tau - T), the steady-state smoothed-minus-code error.
  ValueError if rate is non-finite or tau/T fails.
- divergence_check(code_carrier_diffs, tau=100.0, T=1.0, window=60,
  threshold=1.0) -> dict with keys rate, predicted_bias, threshold and
  alarm = abs(predicted_bias) > threshold. ValueError if threshold is
  non-finite or <= 0, plus all iono_divergence_rate errors.

Identities to test (closed form, exact):
- alpha = T/tau exactly; pole (1 - alpha) in (0, 1); variance relaxation
  e-folding tau/2 = 50 s at the defaults.
- approx_std = exact*sqrt((2 - alpha)/2) within 1e-12 (algebra identity);
  total_std^2 = code term variance + carrier term variance within 1e-15.
- Small-alpha expansion: (exact - approx)/exact = alpha/4 + alpha^2/32 +
  alpha^3/128 within 1e-8.
- Empirical static-noise simulations (Random(42) code-only, Random(7)
  code+carrier, 40000 epochs, first 2000 skipped past the ~50 s
  relaxation): code-only empirical std matches code_only_std within 5%;
  code+carrier empirical std matches total_std within 15% (the smoothed
  output is autocorrelated, effective sample count about
  N/(2*tau/T) ~ 190).
- Noise-free ionospheric ramp at v = 0.02 m/s over 4000 epochs: empirical
  mean smoothed-minus-code over the last 2000 epochs equals
  smoothed_iono_bias(2*v, tau, T) within 0.1%.
- Divergence monitor on noisy diffs (Random(123), code noise 0.3 m):
  quiet case (v = 0.001) stays far below the 1.0 m threshold (no alarm);
  ramp case (v = 0.02) gives a rate estimate near 2*v and alarms.
- ValueErrors across the module: tau <= 0, T <= 0, T >= tau, alpha outside
  (0, 1) (0, 1.0, 1.5), sigma_code and sigma_carrier at 0 and negative,
  window below 2, window above the epoch count, non-finite measurements and
  differences, threshold at 0 and negative, unequal or empty list lengths.

## Worked example

Receiver at fixed range with tau = 100 s, T = 1 s, sigma_code = 0.3 m,
sigma_carrier = 0.003 m, divergence window 60 s, alarm threshold 1.0 m.
All values below are REAL outputs of the prep anchor
/tmp/w42spec/anchor_gnss_carrier_smoothing.py (stdlib math, deterministic;
exit code 0, every algebra assert passed).

- alpha = T/tau = 0.010000; pole 1 - alpha = 0.990000; variance relaxation
  e-folding about tau/2 = 50.0 s.
- Noise-reduction verdict:
  - exact code-only std = sigma_code*sqrt(alpha/(2-alpha)) = 0.021266 m;
  - textbook limit sigma_code/sqrt(2*tau/T) = 0.3/sqrt(200) = 0.021213 m,
    with relative gap 0.002503 = alpha/4 + alpha^2/32 + alpha^3/128
    (identity asserted to 1e-8);
  - carrier delta-range term = 0.021054 m (comparable to the code term at
    these sigma values because the recursion integrates many millimeter
    increments);
  - total smoothed std = 0.029925 m (variance is the exact sum of the code
    term and the carrier term, asserted to 1e-15);
  - improvement factor = sigma_code/total_std = 10.025: the smoothed range
    is about ten times quieter than the raw code.
- Empirical confirmation over 38000 settled epochs: code-only simulation
  (Random(42), perfect carrier) gives empirical std 0.021043 m against the
  closed form 0.021266 m (within 5%); code+carrier simulation (Random(7))
  gives 0.027221 m against 0.029925 m (relative difference 0.0904, within
  the 15% autocorrelation budget).
- Ionospheric ramp at v = 0.02 m/s (rate dD/dt = 2*v = 0.04 m/s, noise
  free): closed-form steady-state smoothed-minus-code bias
  smoothed_iono_bias(0.04, 100, 1) = -3.9600 m = -(2v)*(tau - T), and the
  empirical mean over the last 2000 of 4000 epochs is -3.9600 m, matching
  to all printed digits (asserted within 0.1%). The smoothed range lags the
  growing code delay by about 4 m at this time constant - the classic
  code-carrier divergence error, 2*dI/dt*tau in the tau >> T limit.
- Early epochs of that ramp (truth 20000000.000000 m, code = truth + 0.02k,
  carrier delta -0.0200 m per epoch): smoothed 20000000.000000 (seed),
  19999999.980400, 19999999.961196, 19999999.942384, 19999999.923960 m -
  the recursion sinks below the code while the ionosphere climbs.
- Divergence monitor on noisy code-carrier differences (code noise 0.3 m on
  the diffs, Random(123)):
  - quiet ionosphere v = 0.001 m/s: estimated rate -0.0001 m/s, predicted
    smoothed bias +0.0075 m, alarm False (noise floor of the 60 s slope fit
    stays far below the 1.0 m threshold);
  - ramp v = 0.02 m/s: estimated rate 0.0427 m/s (near the true 0.04),
    predicted smoothed bias -4.2256 m, alarm True.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified, computed by running the prep anchor script
/tmp/w42spec/anchor_gnss_carrier_smoothing.py (prep-verified by stdlib
math, exit 0).

## Validation list (contract test must include)

- alpha_from_time_constant(100, 1) = 0.01 exactly; pole 0.99.
- code_noise_std_smoothed(0.01, 0.3) = 0.021266 within 1e-6; the identity
  approx = 0.021213 = exact*sqrt(1.99/2) within 1e-12.
- noise_reduction_verdict(100, 1, 0.3, 0.003): code_only_std 0.021266,
  carrier_term_std 0.021054, total_std 0.029925, all within 1e-6;
  improvement_factor 10.025 within 1e-3; relative gap 0.002503 against
  alpha/4 + alpha^2/32 + alpha^3/128 within 1e-8.
- run_hatch_smoother on the noise-free ramp (codes truth + 0.02k, phases
  truth - 0.02k, truth 20000000.0): first five smoothed values
  20000000.000000, 19999999.980400, 19999999.961196, 19999999.942384,
  19999999.923960 within 1e-6.
- Static-noise replay determinism: Random(42) code-only stream, 40000
  epochs, settled empirical std 0.021043 within 0.002 of code_only_std;
  Random(7) code+carrier stream, settled empirical std 0.027221 within
  15% of total_std.
- smoothed_iono_bias(0.04, 100, 1) = -3.96 within 1e-9; ramp empirical
  mean -3.9600 within 0.1%.
- divergence_check replay (Random(123) diffs, 4000 epochs, window 60,
  threshold 1.0): quiet case rate -0.0001 m/s and alarm False; ramp case
  rate 0.0427 within 0.005 of 0.04, predicted_bias -4.2256 within 0.05,
  alarm True.
- ValueErrors: tau 0.0 and -5.0; T 0.0; T = 100 with tau = 100 (T >= tau);
  alpha 0.0, 1.0 and 1.5 in hatch_update; sigma_code 0.0 and -0.3;
  sigma_carrier 0.0; window 1 and window 4001 on 4000 diffs; non-finite
  code, phase, delta or difference values; threshold 0.0 and -1.0; codes
  and carrier_phases of unequal length; an empty epoch list.
- Determinism; imports limited to math and random (random only to draw the
  documented simulation streams); defaults fixed at tau = 100 s, T = 1 s,
  sigma_code = 0.3 m, sigma_carrier = 0.003 m, window 60, threshold 1.0 m.

## Corpus fragment (eval/hit1-wave42-gnss-carrier-smoothing.yaml)

Query 1 (copy verbatim):
  "smooth the gnss code pseudoranges with carrier-phase delta ranges: run the hatch recursion at a 100 s smoothing time constant, watch the code-carrier divergence monitor, and report the noise reduction verdict against the raw code noise"
  intent: "gnc-autonomy; first-order Hatch code-carrier pseudorange smoothing at a smoothing time constant, code-carrier divergence monitoring, closed-form noise reduction verdict"
  expected_skill: "gnc-autonomy/navigation/gnss-carrier-smoothing"
Query 2 (copy verbatim):
  "apply carrier-phase smoothing to the gnss code pseudoranges, run the ionospheric-divergence check on the code-carrier difference, and compare the smoothed range error with the raw code noise"
  intent: "gnc-autonomy; carrier-phase smoothing of GNSS code pseudoranges with an ionospheric-divergence check and a smoothed-range-noise comparison"
  expected_skill: "gnc-autonomy/navigation/gnss-carrier-smoothing"
Task ids: w42-gnss-carrier-smoothing-1 and -2. Prep grep: none of the
distinctive phrases (carrier-phase-smoothing, code-carrier-smoothing,
hatch-recursion, code-carrier-divergence, ionospheric-divergence-check,
smoothed-range-noise-reduction, "smoothing time constant") appears in any
existing hit1-corpus.yaml task; the wave-41 corpus has no GNSS smoothing
task and the closest navigation tasks route on single-epoch position fixes,
RAIM detection thresholds or Kalman predict/correct wording, so the queries
above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must smooth GNSS code pseudoranges with
carrier-phase delta ranges before positioning:" and include the outputs in
the Claim (smoothed range time series, the noise-reduction verdict with the
closed form sigma_code*sqrt(alpha/(2 - alpha)) and its
sigma_code/sqrt(2*tau/T) limit, and the code-carrier divergence alarm).
First tag: gnss-carrier-smoothing. Additional tags ONLY:
carrier-phase-smoothing, hatch-filter-recursion,
code-carrier-divergence-monitor, ionospheric-divergence-check,
smoothed-range-noise-reduction. NEVER single generic words (smoothing,
carrier, gnss, code, noise, range, filter, monitor, divergence,
ionosphere, hatch). 50-150 words, <=1000 chars, no em dash, no
content-policy sweep term, action verb present.

FORBIDDEN TOKENS (belong to siblings): snapshot-navigation-solution,
single-epoch-fix, receiver-clock-bias, iterated-least-squares-fix,
ecef-position-solution, satellite-pseudorange-residual, geometry-matrix,
normal-equation, residual-rms, position-error-estimate
(gnss-pseudorange-positioning); raim, fault-detection-and-exclusion,
horizontal-protection-level, protection-level, chi-square-threshold,
normalized-residual, gnss-integrity, false-alarm-probability, residual-
sensitivity (gnss-raim-fde); kalman-gain, innovation-variance,
error-covariance, process-noise, measurement-noise, estimator-design,
recursive-least-squares, steady-state-covariance (kalman-filter-design);
dilution-of-precision, gdop, pdop, elevation-mask (dilution-of-precision);
ins-gnss-integrated, inertial-navigation-solution, drift-estimator
(ins-gnss-integrated-filter). Cycle-slip and ambiguity language belongs to
this leaf only as out-of-scope caveats, never as deliverables.
