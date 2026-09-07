---
name: fir-bandpass-bandstop-filter-design
description: "Use when you must design a linear-phase finite-impulse-response highpass, bandpass, or bandstop filter by the windowed-sinc method with spectral inversion and cosine frequency translation of a lowpass prototype: build the windowed prototype at the cutoff, the half bandwidth for bands, form the highpass as the windowed unit sample minus the prototype, the bandpass as twice the prototype times the center cosine, and the bandstop as spectral inversion of the translated bandpass, under the rectangular, Hann, Hamming, or Blackman windows, with unity passband gain at Nyquist, center, or DC, with the requested edges at the -6.020599913 dB midpoint. Produces the tap vector, band-edge gain checks, the magnitude response in dB as the real cosine sum, the group delay, and the filtered signal. Trigger: fir-highpass-filter-design, fir-bandpass-filter-design, fir-bandstop-filter-design, spectral-inversion-method, frequency-translation-method, windowed-sinc-band-filter, linear-phase-band-filter."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: numerics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [fir-highpass-filter-design, fir-bandpass-filter-design, fir-bandstop-filter-design, spectral-inversion-method, frequency-translation-method, windowed-sinc-band-filter, linear-phase-band-filter]
  version: 0.1.0
  author: AeroSkills
---

# FIR Highpass, Bandpass and Bandstop Filter Design (cross-cutting/numerics/fir-bandpass-bandstop-filter-design)

Use when you must design a linear-phase finite-impulse-response filter that
passes or rejects frequencies above a cutoff (highpass) or inside or outside
a band between two specified edges (bandpass, bandstop), by the windowed-sinc
method: build the windowed ideal lowpass prototype at the cutoff (the half
bandwidth for the band types), then form the requested tap set by spectral
inversion (highpass: windowed unit sample minus the prototype), cosine
frequency translation (bandpass: twice the prototype times the center
cosine), or spectral inversion of the translated bandpass (bandstop). Every
tap is computed from closed-form sine, cosine and window algebra, none looked
up, no iteration and no search: deterministic, offline, pure Python stdlib
(math only). It pairs with cross-cutting/numerics/digital-filter-design,
which owns the Butterworth IIR lowpass and highpass members with a hard ftype
fence, with cross-cutting/numerics/bandpass-bandstop-filter-design, which
owns the Butterworth IIR bandpass and bandstop members by the z-domain
frequency transformation (both its edges at exactly -3.0103 dB), and with
cross-cutting/numerics/fir-filter-design, which designs FIR lowpass filters
only. This leaf is the FIR highpass/bandpass/bandstop cell of the digital
filter 2x2 grid; standalone lowpass FIR design with unity DC normalization
stays with fir-filter-design (this leaf uses the prototype only as internal
translation material and exposes no lowpass design function).

## Domain quick reference

- Window weights w[n], n = 0..num_taps - 1, denominator num_taps - 1:
  rectangular all 1.0; hann 0.5 - 0.5*cos(2*pi*n/(num_taps - 1)); hamming
  0.54 - 0.46*cos(2*pi*n/(num_taps - 1)); blackman
  0.42 - 0.5*cos(2*pi*n/(num_taps - 1)) + 0.08*cos(4*pi*n/(num_taps - 1)).
  Every window is symmetric about the integer center M = (num_taps - 1)/2 and
  evaluates to exactly 1.0 at the center tap (cos(pi) = -1), so windowed taps
  stay symmetric (linear phase). num_taps = 1 is the degenerate case: the
  window is [1.0] and every design normalizes to the single tap [1.0].
- Ideal lowpass prototype, center M:
  h_lp[n] = sin(wc*(n - M))/(pi*(n - M)) for n != M, center limit
  h_lp[M] = wc/pi = 2*fc_proto/fs. Windowed prototype p[n] = w[n]*h_lp[n]
  (NOT DC-normalized; its DC gain is only approximately 1, which limits the
  spectral-inversion null depth).
- Prototype cutoff: for the highpass fc_proto = cutoff_hz; for the band types
  fc_proto = (high_cutoff_hz - low_cutoff_hz)/2, the half bandwidth, so the
  requested edges are the images of the prototype cutoff wc at w0 - wc and
  w0 + wc with center frequency w0 = 2*pi*center_frequency_hz/fs and
  center_frequency_hz = (low_cutoff_hz + high_cutoff_hz)/2 (the arithmetic
  mean of the requested edges, where the bandpass gain is normalized to
  exactly 1).
- Constructions (Oppenheim and Schafer Section 8.4 / Proakis and Manolakis
  Chapter 10 closed forms): highpass by spectral inversion
  b_raw[n] = w[n]*delta[n - M] - p[n]; bandpass by cosine frequency
  translation b_raw[n] = 2*p[n]*cos(w0*(n - M)); bandstop by spectral
  inversion of the translated bandpass
  b_raw[n] = w[n]*delta[n - M] - 2*p[n]*cos(w0*(n - M)). The constructions
  are per-sample additions and scalings, so raw bandstop plus raw bandpass
  equals the windowed unit sample w[n]*delta[n - M] elementwise (the
  complement identity the contract test recomputes).
- Unity passband gain normalization: b[n] = b_raw[n]/G with G the passband
  reference scale, |cosine sum of the raw taps at the reference|: Nyquist
  fs/2 for the highpass, the center frequency for the bandpass, DC for the
  bandstop. After normalization the passband gain is exactly 1 to float
  precision at the reference.
- Magnitude response of the symmetric tap set: H(f) = sum_n b[n]*
  cos(2*pi*f/fs*(n - M)) (the linear phase term dropped); gain_at returns
  |H(f)| and magnitude_response_db returns 20*log10(|H(f)|). Cosine sums
  accumulate row by row in index order, deterministic and bitwise
  reproducible, no RNG.
- Band-edge geometry: the requested edges carry the windowed-sinc transition
  midpoint. The prototype response at its own cutoff is the gain-0.5
  midpoint, so measured edge gains sit on the -6.020599913279624 dB
  (20*log10(0.5)) band-edge geometry within window ripple and image leakage
  (worked Hamming anchors -5.995505518 to -6.073441862 dB). The
  -3.010299956639813 dB level (20*log10(1/sqrt(2))) is the Butterworth
  prototype-3 dB-point convention of the IIR siblings; for these FIR filters
  it is crossed strictly INSIDE the nominal passband (bandpass at 215.960 and
  784.004 Hz inside 200 to 800 Hz), at the bandstop notch shoulders (183.781
  and 816.188 Hz), or above the highpass cutoff (103.994 Hz above 100 Hz),
  never at the requested edges.
- Group delay of the symmetric tap set: (num_taps - 1)/2 samples, constant
  for every frequency because the phase is exactly linear. All taps real and
  symmetric, all-zero transfer function: unconditionally stable, no feedback
  path. Direct-form convolution filter y[n] = sum_k b[k]*x[n - k] with the
  input zero outside its range and the output the same length as the input.
  Units are SI throughout: Hz for frequencies, samples per second for fs.

## Workflow

1. Fix the design inputs and choose the prototype (the design-input fixing
   step): the sample rate fs, the requested edges (a single cutoff for the
   highpass; low and high edges for the band types, 0 < low < high < fs/2),
   an odd num_taps >= 1, and the window (rectangular, hann, hamming,
   blackman). The prototype lowpass cutoff is the cutoff itself for the
   highpass and the half bandwidth (high - low)/2 for the band types.
   Nonphysical inputs raise ValueError; even tap counts are rejected because
   the center index M must stay integer for symmetric linear-phase taps.
2. Build the windowed ideal lowpass prototype (the windowed prototype build
   step): window_coefficients(window, num_taps) returns w[n] and
   ideal_lowpass_taps(cutoff_hz, sample_rate_hz, num_taps) returns
   h_lp[n] = sin(wc*(n - M))/(pi*(n - M)) with the center limit 2*fc/fs;
   the module helper _windowed_prototype multiplies them into
   p[n] = w[n]*h_lp[n].
3. Translate or invert to the raw band taps (the raw-construction
   translate-invert step): the helper _translate_invert builds the raw
   (unnormalized) tap set from the defining relation of the requested type,
   spectral inversion w[n]*delta[n - M] - p[n] for the highpass, cosine
   frequency translation 2*p[n]*cos(w0*(n - M)) for the bandpass, and
   spectral inversion of the translated bandpass for the bandstop. The three
   public design functions call it: design_highpass(cutoff_hz,
   sample_rate_hz, num_taps, window), design_bandpass(low_cutoff_hz,
   high_cutoff_hz, sample_rate_hz, num_taps, window) and
   design_bandstop(...) with the same signature.
4. Normalize to unity passband gain (the unity passband gain normalization
   step): divide the raw taps by the passband reference cosine sum G (Nyquist
   for the highpass, the center frequency for the bandpass, DC for the
   bandstop), so the returned dicts carry nyquist_gain, center_gain and
   dc_gain equal to 1.0 within 1e-12. The highpass is then also near-unity
   away from DC, the bandstop near-unity at DC and Nyquist away from the
   notch, because the notch complement is not perfect.
5. Verify the band edges (the band-edge verification step):
   band_edge_checks(coefficients, ftype, sample_rate_hz, low_cutoff_hz,
   high_cutoff_hz=None) probes the magnitude response at the requested edges
   and returns {low_edge_db, high_edge_db, target_db, low_edge_ok,
   high_edge_ok, passband_ok, extra, verdict} with target_db the module
   constant -6.020599913279624; each measured edge must sit within 0.1 dB of
   the midpoint target and the passband reference gain within 0.1 dB of 0 dB
   for a PASS verdict.
6. Probe, read the group delay and filter (the probe-filter step):
   gain_at and magnitude_response_db evaluate the real cosine sum at any
   probe in [0, fs/2] (0 Hz and fs/2 are valid probes), group_delay_samples
   returns the constant (num_taps - 1)/2, and filter_signal applies the
   direct-form convolution to a sampled record, output the same length as the
   input with the first (num_taps - 1) samples carrying the transient. The
   deterministic checks are in the contract test
   scripts/test_fir_bandpass_bandstop_filter_design.py.

## Worked example

Primary geometry (band types): fs = 4000 Hz, band edges low = 200 Hz and
high = 800 Hz, num_taps = 101, Hamming window; the prototype lowpass cutoff
is the half bandwidth fc_proto = 300 Hz (wc = 0.15*pi) and the translation
center w0 = 0.25*pi, center_frequency_hz = 500 Hz. Highpass geometry:
fs = 1000 Hz, cutoff 100 Hz (wc = 0.2*pi), num_taps = 101, Hamming. All
values below are REAL outputs of
scripts/fir_bandpass_bandstop_filter_design_logic.py (pure stdlib math,
deterministic; the contract test exits 0 with all checks passed):

- Highpass design_highpass(100, 1000, 101, "hamming"): group delay 50.0
  samples, nyquist_gain 1.000000000000000, symmetry error 1.4e-17. Center
  tap b[50] = 0.800131546113 (the windowed unit sample minus the prototype
  center, scaled by the Nyquist normalization), neighbors b[49] = b[51] =
  -0.186958764181, b[48] = b[52] = -0.150841106810, outer taps b[1] =
  0.000308982598, b[2] = 0.000527514464, b[0] = 0.000000000000 (float floor
  of the sine at an integer multiple of pi). Edge gain at the requested 100 Hz
  cutoff: -6.013188638 dB, 0.007411 dB from the -6.020599913 dB midpoint
  target; DC gain -56.644897249 dB (the spectral-inversion null floor); 50 Hz
  probe -55.337139253 dB; passband +0.009876223 dB at 150 Hz, -0.000850773 dB
  at 300 Hz, -0.000006122 dB at 480 Hz. The -3.010299956640 dB level is
  crossed at 103.994 Hz, above the requested cutoff.
- Bandpass design_bandpass(200, 800, 4000, 101, "hamming"): center_frequency_hz
  500.000000000 = (200 + 800)/2, group delay 50.0, center_gain
  1.000000000000000, symmetry error 2.8e-17. Center tap b[50] =
  0.299984336175, b[49] = b[51] = 0.204171360832, b[48] = b[52] =
  0.000000000000 (the w0*M = 12.5*pi structural zeros), b[1] = -0.000662242631,
  b[2] = -0.000651902497, b[3] = -0.000132065332, b[0] = 0.000000000000.
  Edge gains: 200 Hz -5.995505518 dB and 800 Hz -6.018418812 dB, within
  0.025094 and 0.002181 dB of the midpoint target; center +0.000000000 dB;
  stopband probes -50.065791442 dB at DC, -62.087519915 dB at 100 Hz,
  -57.420533724 dB at 1000 Hz, -61.325771718 dB at 1200 Hz, -65.756900774 dB
  at 1600 Hz, -66.996568467 dB at Nyquist; passband probe -0.002015073 dB at
  400 Hz. band_edge_checks verdict PASS. The -3.010299956640 dB level is
  crossed at 215.960 and 784.004 Hz, strictly inside the requested passband.
- Bandstop design_bandstop(200, 800, 4000, 101, "hamming"): dc_gain
  0.999999999999999, group delay 50.0, symmetry error 2.8e-17. Center tap
  b[50] = 0.697809868401 (one minus the bandpass center tap to scale),
  b[49] = b[51] = -0.203543185312, b[48] = b[52] = -0.000000000000,
  b[1] = 0.000660205105, b[2] = 0.000649896784, b[3] = 0.000131659006.
  Edge gains: 200 Hz -6.073441862 dB and 800 Hz -6.050454002 dB, within
  0.052842 and 0.029854 dB of the midpoint target; DC gain -0.000000000 dB
  and Nyquist gain -0.031101109 dB (unity passband, small notch-complement
  droop); passband probes -0.020390713 dB at 100 Hz and -0.034678594 dB at
  1200 Hz; in-notch probe -74.933184863 dB at 400 Hz; the notch center null
  at 500 Hz measures -85.671233701 dB, the float floor of the imperfect
  complement. band_edge_checks verdict PASS. The -3.010299956640 dB
  shoulders sit at 183.781 and 816.188 Hz, strictly outside the notch band.
- Window trade at the bandpass geometry (101 taps, 200 to 800 Hz at 4000 Hz),
  edge gains and stopband probes at 900 and 1200 Hz: rectangular low edge
  -5.701966 dB, high edge -5.994135 dB, 900 Hz -46.380 dB, 1200 Hz -38.919
  dB; hann low edge -6.021533 dB, high edge -6.020536 dB, 900 Hz -58.142 dB,
  1200 Hz -85.570 dB; hamming low edge -5.995506 dB, high edge -6.018419 dB,
  900 Hz -62.438 dB, 1200 Hz -61.326 dB; blackman low edge -6.020932 dB, high
  edge -6.020591 dB, 900 Hz -60.091 dB, 1200 Hz -94.916 dB. The midpoint
  geometry holds across all four windows (the rectangular lower edge carries
  the largest image-leakage bias); the stopband floor follows the window with
  Blackman deepest and rectangular shallowest at the 1200 Hz probe.
- Deterministic signal tests: an impulse through the bandpass reproduces the
  coefficient vector exactly (max error 0.0); a constant 5.0 input settles to
  a bandstop tail mean of 5.000000000 (unity DC), a bandpass tail mean of
  -1.569208e-02 (the DC stopband, -50.065791442 dB times 5.0) and a highpass
  tail mean of 7.357413e-03 (the DC null floor); alternating +5/-5 settles
  through the bandpass to a tail RMS of 4.468601e-04 relative to 5.0 (the
  Nyquist stopband) and through the bandstop to 0.996425755 relative (the
  near-unity Nyquist gain); two identical design calls are bitwise identical.
- Recorded low-cutoff pitfall (corpus query-2 geometry): the windowed-sinc
  geometry needs the tap count large enough that the window main lobe
  resolves the cutoff, fc*num_taps/fs roughly 2 or more. At fc = 0.5 Hz,
  fs = 100 Hz, num_taps = 51 (fc*num_taps/fs = 0.255) the highpass is
  degenerate (the -6.0206 dB crossing sits below 0.001 Hz, not at the
  requested 0.5 Hz cutoff; the design cannot realize the cutoff). At
  num_taps = 501 (fc*num_taps/fs = 2.505) the geometry is restored:
  -50.768 dB at 0.1 Hz and the crossing at 0.5004 Hz. No contract anchor
  asserts the degenerate 51-tap numbers; the contract pins the worked
  geometries above.

## Verification

- design_highpass(100, 1000, 101, "hamming") returns the seven documented
  keys with the tap anchors above and nyquist_gain 1.0 within 1e-12;
  design_bandpass and design_bandstop return their nine documented keys with
  center_frequency_hz 500.0 and unity center_gain / dc_gain within 1e-12.
- The measured edge gains sit within 0.1 dB of the -6.020599913279624 dB
  midpoint target (real Hamming anchors -5.995505518 to -6.073441862 dB);
  band_edge_checks returns verdict PASS for all three worked designs, and the
  bandpass and bandstop passband references measure 0.000000000 dB (unity by
  construction).
- The -3.010299956639813 dB Butterworth level is NOT at the requested edges:
  contract crossing measurements lie strictly between the bandpass edges
  (215.960 and 784.004 Hz inside 200 to 800 Hz), strictly outside the bandstop
  notch band (183.781 and 816.188 Hz) and above the highpass cutoff (103.994
  Hz); the requested edge gains differ from -3.010299956640 dB by more than
  1 dB.
- Raw-construction identities: rebuilding the window, the prototype, the raw
  tap sets and the passband scale G with math only gives max
  |b[n]*G - raw[n]| below 1e-9 for every worked design, and the bandstop
  complement identity b_bs_raw[n] + b_bp_raw[n] = w[n]*delta[n - M] holds
  elementwise below 1e-9.
- Symmetry and group delay: max |b[n] - b[num_taps - 1 - n]| below 1e-12 for
  every worked design (real anchors 1.4e-17 highpass, 2.8e-17 bandpass and
  bandstop) and group_delay_samples(101) = 50.0.
- Deterministic signal identities: the multi-tone records through
  filter_signal reproduce the designed |H| at each tone by quadrature
  projection over the settled integer-cycle tail within 1e-9 relative; the
  bandpass impulse round trip is exact; constant and alternating inputs
  settle to the designed DC and Nyquist behavior.
- Nonphysical inputs raise ValueError: fs <= 0, cutoff_hz <= 0 or >= fs/2,
  low_cutoff_hz <= 0 or >= high_cutoff_hz, high_cutoff_hz >= fs/2, even or
  zero num_taps, unknown window names (bartlett), probes outside [0, fs/2],
  empty or non-finite sample and coefficient lists, unknown ftype values, and
  high_cutoff_hz not None with ftype "highpass".
- Run the contract test offline under both interpreters, exit 0:
  python3 scripts/test_fir_bandpass_bandstop_filter_design.py and the pyenv
  3.13 hook interpreter. All numeric asserts are tolerance-based (no exact
  float equality on computed sums), so the suite holds identically on both.

## Related leaves

- cross-cutting/numerics/digital-filter-design: the immediate sibling; owns
  the Butterworth IIR lowpass and highpass members with a hard ftype fence
  (its contract test raises ValueError for any non-LP/HP type), single-cutoff
  prewarp anchors at the -3.0103 dB prototype point.
- cross-cutting/numerics/bandpass-bandstop-filter-design: the Butterworth IIR
  bandpass and bandstop cell by the z-domain frequency transformation, with
  both edges at exactly -3.010299956640 dB; no windowed-sinc taps.
- cross-cutting/numerics/fir-filter-design: linear-phase FIR lowpass taps by
  the windowed-sinc method with unity DC normalization; no band types, no
  spectral inversion, no frequency translation.
- cross-cutting/numerics/fast-fourier-transform: spectral analysis of a
  signal, not band filtering of it.
- cross-cutting/numerics/power-spectral-density: Welch averaged periodogram
  estimation of recorded time data; no filter coefficients.
- cross-cutting/numerics/finite-difference-derivatives: differentiating the
  filtered signal, not designing the band filter.
- cross-cutting/numerics/cross-correlation-analysis: delay estimation between
  two filtered traces, not band filtering.

## Pitfalls

- Reading the requested edges at -3.0103 dB: the -3.010299956640 dB level is
  the Butterworth prototype-3 dB-point convention of the IIR siblings. A
  windowed-sinc FIR tap set has no such point at its requested edges: the
  prototype response at its own cutoff is the gain-0.5 midpoint of the
  transition, so the band edges sit on the -6.020599913279624 dB midpoint
  within window ripple and image leakage, and the -3.0103 dB level is reached
  strictly inside the passband (bandpass) or at the notch shoulders
  (bandstop). This leaf verifies its edges against the FIR midpoint target
  and says so in its description; the -3.0103 dB phrasing is the physically
  forced deviation from the IIR anchor convention, documented with measured
  crossing evidence in the Worked example.
- Designing below the resolution geometry: the windowed-sinc method needs
  fc*num_taps/fs roughly 2 or more for the window main lobe to resolve the
  cutoff. At fc*num_taps/fs around 0.25 the design is degenerate (measured
  gains near -2.7 dB at the reported rejection point) and no edge anchor
  holds. Use a larger tap count (501 taps restored the 0.5 Hz at 100 Hz
  geometry to -50.768 dB rejection with the crossing at 0.5004 Hz).
- Trusting the far-field window ordering: the classical first-sidelobe
  ordering does not extend to far stopband probes: Hann out-attenuates
  Hamming at the worked 1200 Hz probe (-85.570 dB vs -61.326 dB) because the
  Hamming far sidelobe envelope decays more slowly; report probes as
  measured.
- Reading structural zeros as general claims: at the worked 101-tap geometry
  w0*M = 12.5*pi, so bandpass and bandstop taps at offsets n - M = +-2 mod 4
  are zero to float floor and the outer taps read 0.000000000000; these are
  geometry-specific, not general properties of the construction.
- Writing exact float equality on computed sums: the module and its contract
  test use tolerance-based asserts only, since accumulated rounding differs
  between interpreters (the pre-push hook resolves python3 to pyenv 3.13.12
  while foreground shells use /usr/bin/python3 3.9.6).

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fir_bandpass_bandstop_filter_design.py

It covers the full workflow: the design-input guard rails and ValueError set
of every public function, the window anchor values and symmetry, the
ideal-lowpass center limit, the worked highpass/bandpass/bandstop tap anchors
at both geometries, the unity passband gains, the -6.020599913279624 dB
midpoint edge geometry and PASS verdicts of band_edge_checks, the measured
-3.010299956640 dB crossing locations, the raw-construction recovery and
bandstop complement identities, the stopband and notch null floors, the
four-window trade, the group delay identity, bitwise determinism with math as
the only import, the direct-form impulse round trip, the constant and
alternating settle behavior, and the three-tone quadrature gain identities
for the highpass, bandpass and bandstop. 35 tests pass in under a second
offline under python3 (3.9.6) and the pyenv 3.13 hook interpreter.

## Compliance

- Standards referenced, not reproduced: naca-tr-824 (NACA Report 824, summary
  of low-speed airfoil data) is cited reference-only per standards-map.yaml as
  the numerics-convention anchor for the library; the windowed-sinc FIR design
  relations above are classical digital filter methodology (Oppenheim and
  Schafer, Discrete-Time Signal Processing, Section 8.4, FIR design by
  windowing, with the highpass prototype from spectral inversion of the
  lowpass response and the bandpass/bandstop prototypes from cosine
  modulation or frequency translation; identical closed forms in Proakis and
  Manolakis, Chapter 10, and Hamming, Digital Filters), paraphrase-only.
- compliance: STANDARDS-REF, gated: false.
