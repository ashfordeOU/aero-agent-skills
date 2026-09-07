# WAVE-45 CROSS-CUTTING EXTENSION PROBE RECEIPT (task-11, whole-family FRESH)

- Repo: the local AeroSkills repo at git HEAD 5cc8fef33ffa3bd5530847040ef891299dde107d (verified via git rev-parse).
- Scope: ENTIRE cross-cutting family, 55 leaves, probed fresh. Read-only except this receipt file.
- Extension context: wave-44 extension probe yielded 1 GO (bandpass-bandstop-filter-design) with 13 declines; this probe re-runs the whole family FRESH at wave-45 HEAD per the brief extension rule (smaller families exhausted, wave45-brief lines 74-91).
- Standards map: 30 ids in standards-map.yaml, all candidate ids grep-verified below.
- Corpus baseline: eval/hit1-corpus.yaml (1019 tasks parsed by regex in this probe; 1238 with fragments per wave-45 close).

## Family census (55 leaves enumerated, find skills/cross-cutting -mindepth 3 -name SKILL.md)

data-sources (1): aeronautical-data-sources
documentation (2): engineering-margins, engineering-report
export-control (1): export-control-awareness
numerics (37): bandpass-bandstop-filter-design, chi-square-goodness-of-fit,
complex-number-algebra, confidence-interval-estimation, convergence-verification,
cross-correlation-analysis, descriptive-statistics, digital-filter-design,
eigenvalue-decomposition, exact-binomial-test, fast-fourier-transform,
finite-difference-derivatives, fir-filter-design, fisher-exact-test,
grubbs-outlier-test, hypothesis-testing, information-entropy, interpolation,
kruskal-wallis-test, least-squares-regression, matrix-operations,
monte-carlo-sampling, multiple-linear-regression, numerical-integration,
ode-solvers, optimization-algorithms, poisson-confidence-interval, power-analysis,
power-spectral-density, probability-distributions, proportion-confidence-interval,
quaternion-algebra, rank-based-hypothesis-testing, root-finding, runs-test,
singular-value-decomposition, uncertainty-propagation
sep2640 (3): skill-authoring, skill-delivery, skill-evaluation
tolerancing (5): datum-reference-frames, fastener-position-tolerance-calc,
gdandt-basics, position-tolerance-calc, tolerance-stackup
units-atmos (6): airspeed-conversion, density-altitude, dimensional-analysis,
isa-atmosphere, temperature-conversion, unit-conversion
Total 1+2+1+37+3+5+6 = 55. Router parity: cross-cutting/SKILL.md rows match leaves (no orphan rows, no missing rows).

## Verdict

1 ranked GO candidate: cross-cutting/numerics/fir-bandpass-bandstop-filter-design
(windowed-sinc linear-phase FIR highpass/bandpass/bandstop by spectral inversion
and cosine frequency translation of the lowpass prototype). It is the missing
fourth cell of the digital-filter 2x2 grid that the family itself documents:
IIR LP/HP = digital-filter-design, IIR BP/BS = bandpass-bandstop-filter-design,
FIR LP = fir-filter-design, FIR HP/BP/BS = EMPTY. Wave-44 filled the IIR BP/BS
cell under the extension probe; this probe finds the FIR band cell still open
with zero owners, real sibling fences, a published closed-form anchor, and the
same live filter-task corpus vein that made the wave-44 cell a GO. All other
candidate seams in numerics/statistics/signal decline below with receipts.

## Ranked GO candidate

### 1. cross-cutting/numerics/fir-bandpass-bandstop-filter-design (GO, rank 1)

Linear-phase FIR highpass, bandpass, and bandstop tap sets from a windowed-sinc
lowpass prototype: highpass by spectral inversion h_hp[n] = delta[n-M] - h_lp[n],
bandpass by cosine frequency translation h_bp[n] = 2*h_lp[n]*cos(w0*(n-M)) of the
prototype, bandstop by spectral inversion of the translated bandpass, each with
the rectangular/Hann/Hamming/Blackman window weights, unity passband gain
normalization, real cosine-sum magnitude response in dB, constant group delay
(N-1)/2, and direct-form convolution filtering. Every tap from closed-form
sine/cosine and window algebra, none looked up, no iteration: deterministic,
offline, pure Python stdlib, the same family shape as the three sibling filter
leaves. Today a router query asking for an FIR highpass or bandpass or bandstop
can only land on fir-filter-design, whose logic hardwires a single lowpass
cutoff geometry (functions are ideal_lowpass_taps/design_lowpass only).

(a) Zero-owner grep across the WHOLE skills/ tree plus eval/:

```
$ grep -rin -E "spectral[- ]inversion|frequency[- ]translation|fir[- ]band|fir (high|band|band-stop)|high[- ]pass fir|band[- ]pass fir" skills/ eval/ 2>/dev/null | grep -v __pycache__; echo EXIT=$?
EXIT=1
```

Per-token SKILL.md counts across the whole tree (script /tmp/w45_scan.py and
direct greps): spectral inversion: 0 hits; frequency translation: 0 hits;
fir highpass / fir bandpass / fir bandstop / fir-band: 0 hits; windowed-sinc
outside fir-filter-design: 0 hits. The only filter leaves anywhere in the tree
are the three numerics siblings and gnc complementary-filter (a first-order LP
sensor-fusion complementary split, no FIR band machinery). No owner in any
family, no router row for any FIR band/highpass cell in skills/cross-cutting/
SKILL.md.

(b) Quoted sibling fences:

bandpass-bandstop-filter-design (skills/cross-cutting/numerics/bandpass-
bandstop-filter-design/SKILL.md lines 32-36):

"It pairs with cross-cutting/numerics/digital-filter-design, which owns the
lowpass and highpass members of the family with a hard ftype fence, and with
cross-cutting/numerics/fir-filter-design, which designs FIR lowpass filters
only. This leaf is pure Python stdlib (math and cmath), deterministic and
offline."

fir-filter-design frontmatter description (its own scope statement):

"Use when you must design a linear-phase finite-impulse-response lowpass filter
with the windowed-sinc method: build the ideal lowpass impulse response from
the cutoff frequency and the sample rate, apply a selected window (rectangular,
Hann, Hamming, or Blackman), normalize the coefficient vector to unity DC gain,
evaluate the magnitude response in dB at any frequency as the real cosine sum
of the symmetric tap set, return the group delay of the taps, and filter a
sampled signal by direct convolution."

fir-filter-design logic confirms structural LP-only (no ftype concept exists):

```
$ grep -c -i -E "ftype|bandpass|highpass|bandstop" scripts/fir_filter_design_logic.py
0
$ grep -n "^def \|^    def " scripts/fir_filter_design_logic.py
_require_num_taps / _require_window / _require_response_inputs /
window_coefficients / ideal_lowpass_taps / design_lowpass / gain_at /
magnitude_response_db / group_delay_samples / filter_signal / design_check
```

digital-filter-design frontmatter description (IIR side of the grid, quoted for
contrast): "...compute the coefficients of a digital Butterworth IIR lowpass or
highpass frequency-selective filter from a cutoff frequency, sample rate, and
order: prewarp the analog cutoff, map the normalized Butterworth poles through
the bilinear transform..." and its logic raises ValueError("ftype must be
'lowpass' or 'highpass'") (digital_filter_design_logic.py lines 294-295), with
the bandpass rejection exercised in its contract test (test line 328). Router
(skills/cross-cutting/SKILL.md lines 164, 200): "FIR lowpass filter questions
(windowed-sinc, finite impulse response taps, linear phase, group delay,
Hamming window) route to the numerics fir-filter-design sub-skill" and
"Bandpass and bandstop digital-filter questions (Butterworth IIR bandpass/
bandstop by the z-domain frequency transformation, band-edge verification)
route to the numerics bandpass-bandstop-filter-design sub-skill; lowpass and
highpass questions stay with digital-filter-design." No FIR band cell exists in
the router; the new leaf is the additive sibling the router line needs next.

(c) Standards-map id exists (grep-verified) or numerics convention:

```
$ grep -n "id: naca-tr-824" standards-map.yaml
171:  - id: naca-tr-824
```

naca-tr-824 (NACA Report 824, reference-data, public domain) is the numerics
convention used by every sibling; fir-filter-design compliance states it: "NACA
TR-824 anchors the numerics-pack public-domain reference set; windowed-sinc FIR
design and its windows are classical digital filter methodology (Hamming,
Oppenheim and Schafer style summaries), paraphrase-only per standards-map.yaml."
The new leaf keys the same reference-only naca-tr-824 id.

(d) Published deterministic anchor: the window method for FIR filters with the
classic prototype-extension relations in Oppenheim and Schafer, Discrete-Time
Signal Processing (3rd ed., 2010), Section 8.4 (FIR design by windowing), where
the highpass prototype follows from spectral inversion of the lowpass impulse
response and the bandpass/bandstop prototypes from cosine modulation (frequency
translation) of the lowpass response; identical closed forms in Proakis and
Manolakis, Digital Signal Processing (4th ed.), Chapter 10, and Hamming, Digital
Filters. The relations are single-pass closed-form tap algebra with the same
window weights the FIR lowpass sibling already implements; no iterative design,
no coefficient tables, no proprietary text. The -6 dB band-edge geometry and
the window sidelobe floors follow the sibling leaf anchors.

(e) Two wordable Hit@1 corpus queries with distinctive hyphenated tokens (draft
wordings for the build-time corpus merge, adversarially checked against every
existing tag set; no butterworth/bilinear/iir tokens, so the two IIR leaves do
not score; no lowpass geometry, so fir-filter-design does not score):

1. "design a linear-phase FIR bandpass filter by the windowed-sinc frequency-
   translation method: build the 101-tap bandpass tap set for the 200 to 800
   hertz passband at a 4000 hertz sample rate with the hamming window, verify
   the center-band gain and the band-edge gains, and filter the 400 hertz test
   tone" (distinctive hyphenated tokens: fir-bandpass-filter-design,
   windowed-sinc, frequency-translation-method, linear-phase-band-filter).
2. "strip the accelerometer bias drift with an FIR highpass filter built by
   spectral inversion of the windowed-sinc lowpass prototype: 51 taps, hamming
   window, 0.5 hertz cutoff at 100 hertz sample rate, and report the low-
   frequency rejection in dB at 0.1 hertz" (distinctive hyphenated tokens:
   fir-highpass-filter-design, spectral-inversion-method; digital-filter-design
   cannot win it: the query carries no butterworth/bilinear/second-order tokens
   and that leaf has no windowed-sinc or spectral-inversion vocabulary).
3. backup wordable variant: "notch the 400 hertz ac-mains tone out of the
   telemetry channel with a linear-phase windowed-sinc FIR bandstop filter
   built by spectral inversion of the translated bandpass tap set and check
   the notch-center null depth in dB" (token: fir-bandstop-filter-design).

(f) Tag plan with no generic single-word overlap: metadata tags are hyphenated
compounds only and none duplicates any existing tag: [fir-highpass-filter-design,
fir-bandpass-filter-design, fir-bandstop-filter-design, spectral-inversion-
method, frequency-translation-method, windowed-sinc-band-filter,
linear-phase-band-filter]. No single-word tags (no fir, no filter, no window,
no highpass, no notch), no hamming-window tag (owned by fir-filter-design), so
the LP leaf keeps w31-fir-filter-design-1/2 and the IIR leaves keep
w28-digital-filter-design-1/2 and w44-bandpass-bandstop-filter-design-1/2.

## Declines table (one line each)

| Candidate | One-line reason |
|---|---|
| QR/Householder factorization | wave-44 decline stands: singular-value-decomposition owns the pseudoinverse/numerical-rank deliverable |
| Iterative sparse linear solvers (Jacobi/Gauss-Seidel/CG) | wave-44 decline stands: matrix-operations is a direct-method dense fence and no sparse surface exists in the corpus |
| Adaptive quadrature / Romberg / Gauss-Kronrod | wave-44 decline stands: numerical-integration owns the Richardson error-machinery vein and corpus demand is zero |
| Stiff ODE (implicit RK / BDF) | wave-44 decline stands: Newton inner-loop machinery with zero corpus demand beside ode-solvers |
| Shapiro-Wilk normality test | wave-44 decline stands: probability-distributions ks_gof owns the goodness-of-fit verdict vein |
| Constrained optimization / LP / KKT | wave-44 decline stands: routes to vehicle-design mdo |
| Two-way ANOVA / ANCOVA | wave-44 decline stands: manufacturing-quality gage-rr-anova plus DOE own it; one-way ANOVA F is inside hypothesis-testing |
| Bender/Mansoor stackup | wave-44 decline stands: tolerance-stackup extension territory, no canonical published anchor |
| QNH/QFE altimeter conversions | wave-44 decline stands: no standards-map id, flight-test-operations adjacency |
| EVM/CPM/PERT program math | wave-44 decline stands: no map id, program-management out of domain |
| SE/safety math (FTA/FMEA cut-sets) | wave-44 decline stands: systems-engineering-safety owns |
| Test/QA acceptance math | wave-44 decline stands: manufacturing-quality owns |
| Data/format converters | wave-44 decline stands: gnc/FTO/space/avionics families own |
| Chi-square test of independence (r x c) | OWNED: hypothesis-testing tag chi-square-test-of-independence and its description; chi-square-goodness-of-fit explicitly defers two-way tables to it |
| Two-sample KS (Smirnov) | zero corpus demand (both kolmogorov corpus tasks route probability-distributions) and the GOF machinery lives there |
| Spearman / Kendall tau rank correlation | zero corpus demand treewide and zero skills mentions; no gap an engineer routes to |
| Levene / Bartlett robust variance equality | zero corpus demand; hypothesis-testing f-test-for-variances owns the variance-comparison vein |
| Friedman / Cochran Q repeated-measures ranks | zero corpus demand; kruskal-wallis owns the k-sample rank vein and no related-samples surface exists |
| Bootstrap/permutation resampling CI | statistical bootstrap has zero demand (all 6 corpus bootstrap tokens are particle-filter and air-cycle-machine); monte-carlo-sampling and confidence-interval-estimation own the sampling/CI veins |
| Latin hypercube / quasi-MC sampling | OWNED deliverable: mdo design-of-experiments w23 task and surrogate-modeling w26 task already carry latin-hypercube runs; a cross-cutting leaf would steal them |
| Gumbel / extreme-value distribution | zero corpus demand; probability-distributions weibull-fit owns the reliability-tail fitting vein |
| Skewness / kurtosis / higher moments | zero corpus demand (0 corpus, 1 skills hit inside descriptive-statistics text) |
| Dixon Q small-sample outlier | zero corpus demand; grubbs-outlier-test owns the outlier-screening vein (2 tasks) |
| Moving-average / smoothing filters | demand routes domain-inline (level-acceleration-test, alpha-beta, RTS, gnss-carrier-smoothing each implement their own); no cross-cutting gap |
| Savitzky-Golay | zero corpus and zero skills mentions |
| Hilbert transform / analytic-signal envelope | zero corpus and zero skills mentions |
| Standalone convolution of sequences | zero corpus demand; direct-form convolution is already inside fir-filter-design |
| Signal resampling / decimation | resampling tokens all belong to particle-filter bootstrap resampling; zero other demand |
| Goertzel single-bin DFT | zero corpus and zero skills mentions |
| Autoregressive / Yule-Walker / Levinson-Durbin | zero corpus and zero skills mentions; power-spectral-density is the Welch nonparametric owner |
| Cubic / natural splines | OWNED: interpolation tags cubic-spline and natural-cubic-spline |
| Nonlinear single-term model fits (power-law/exponential log-log) | demand routes domain-inline (Basquin in structures stress-life-curve slc1, tire power-law sizing w18); a general leaf would steal both |
| Statistical tolerance intervals | zero corpus demand and the single-word tolerance token collides with the whole tolerancing family |
| Percentile estimation methods on raw samples | descriptive-statistics five-number-summary and probability-distributions quantile-estimation split the vein; demand zero for the method detail |
| Cumulative integration of sampled data arrays | demand routes domain-inline (takeoff ground-roll, PSD g-rms, shear-center all integrate their own vectors); numerical-integration owns function quadrature |

## Closed veins (reaffirmed FRESH at wave-45 HEAD)

- Filter grid: IIR LP/HP (digital-filter-design), IIR BP/BS (bandpass-bandstop-
  filter-design), FIR LP (fir-filter-design) are closed; only the FIR HP/BP/BS
  cell is open and it is the GO above.
- Statistics table: parametric tests, chi-square GOF and independence, exact
  tests, rank tests, runs, Grubbs, power analysis, distributions, CIs and
  proportion CIs all have live owners; nothing else in the table has corpus
  demand.
- Signal vein: FFT/DFT, PSD (Welch), correlation, entropy, filter family
  covered; Hilbert/Goertzel/AR/resampling/Savitzky all demand-zero.
- Numerics machinery: quadrature, ODE, root finding, optimization (uncon-
  strained), eigen/SVD, direct linear solves, finite differences, interpolation
  all closed; iterative/stiff/adaptive/constrained extensions declined at
  wave-44 and re-declined here on demand or ownership.
- wave-44 13-decline set: all 13 re-checked FRESH, none changed premise
  (bandpass-bandstop now exists as the owner of the IIR BP/BS cell, which the
  wave-44 declines already assumed).
- Cross-cutting non-numerics packs (data-sources 1, documentation 2,
  export-control 1, sep2640 3, tolerancing 5, units-atmos 6) hold no clean
  deterministic numerics/math/statistics/signal gaps by their own descriptions;
  out of probe scope per the brief mandate.

Receipt end. No files other than this receipt were written; no git operations
were performed.
