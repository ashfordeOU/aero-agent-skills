# Wave-45 leaf spec: fir-bandpass-bandstop-filter-design (cross-cutting,
# numerics pack)

- Path: skills/cross-cutting/numerics/fir-bandpass-bandstop-filter-design/
- Pack: numerics (present siblings digital-filter-design, fir-filter-design,
  bandpass-bandstop-filter-design, fast-fourier-transform,
  power-spectral-density, finite-difference-derivatives,
  cross-correlation-analysis; the design-owner fences quoted below).
- Provenance: wave-45 extension probe (ops/automation/state/
  wave45-recon/task-11-receipt.md), ranked GO candidate 1: the leaf is the
  missing fourth cell of the digital-filter 2x2 grid that the family itself
  documents: IIR LP/HP = digital-filter-design, IIR BP/BS =
  bandpass-bandstop-filter-design, FIR LP = fir-filter-design, FIR
  HP/BP/BS = EMPTY at prep. Receipt evidence: zero-owner greps for
  spectral-inversion, frequency-translation, fir-band, fir (high|band|
  band-stop), high-pass fir, band-pass fir across the whole skills/ tree
  plus eval/ each return EXIT=1 (0 hits); per-token SKILL.md counts across
  the whole tree: spectral inversion 0, frequency translation 0, fir
  highpass / fir bandpass / fir bandstop / fir-band 0, windowed-sinc
  outside fir-filter-design 0; no router row exists for any FIR
  band/highpass cell in skills/cross-cutting/SKILL.md. Wave-44 filled the
  IIR BP/BS cell under the extension probe; this probe finds the FIR band
  cell still open with zero owners, real sibling fences, a published
  closed-form anchor and the same live filter-task corpus vein that made
  the wave-44 cell a GO.
- Corpus tokens of the leaf: fir-highpass-filter-design,
  fir-bandpass-filter-design, fir-bandstop-filter-design,
  spectral-inversion-method, frequency-translation-method,
  windowed-sinc-band-filter, linear-phase-band-filter.
- Claim fences (quoted from the sibling frontmatter and bodies at prep;
  none of them designs a highpass, bandpass, or bandstop FIR tap set):
  - bandpass-bandstop-filter-design (this pack; the IIR band sibling): its
    body reads "It pairs with cross-cutting/numerics/digital-filter-design,
    which owns the lowpass and highpass members of the family with a hard
    ftype fence, and with cross-cutting/numerics/fir-filter-design, which
    designs FIR lowpass filters only. This leaf is pure Python stdlib
    (math and cmath), deterministic and offline." Its tags carry only
    bandpass-filter-design, bandstop-filter-design, butterworth-bandpass,
    butterworth-bandstop, digital-frequency-transformation, band-edge-gain:
    the Butterworth IIR z-domain-transformation band cell, whose -3.0103 dB
    edge guarantee is a prototype-3 dB-point property no windowed-sinc FIR
    tap set can share (measured evidence in the Worked example below).
  - fir-filter-design (this pack; the FIR lowpass sibling): its description
    reads "Use when you must design a linear-phase finite-impulse-response
    lowpass filter with the windowed-sinc method: build the ideal lowpass
    impulse response from the cutoff frequency and the sample rate, apply a
    selected window (rectangular, Hann, Hamming, or Blackman), normalize
    the coefficient vector to unity DC gain, evaluate the magnitude
    response in dB at any frequency as the real cosine sum of the symmetric
    tap set, return the group delay of the taps, and filter a sampled
    signal by direct convolution." Its logic is structurally LP-only, no
    ftype concept exists: grep -c -i -E
    "ftype|bandpass|highpass|bandstop" on its logic script returns 0, and
    its public functions are window_coefficients, ideal_lowpass_taps,
    design_lowpass, gain_at, magnitude_response_db, group_delay_samples,
    filter_signal, design_check. A router query asking for an FIR highpass,
    bandpass, or bandstop can only land there today, where the design
    functions are ideal_lowpass_taps and design_lowpass with a single
    lowpass cutoff geometry.
  - digital-filter-design (this pack; the IIR LP/HP sibling, quoted for
    contrast): its description reads "Use when you must compute the
    coefficients of a digital Butterworth IIR lowpass or highpass
    frequency-selective filter from a cutoff frequency, sample rate, and
    order: prewarp the analog cutoff, map the normalized Butterworth poles
    through the bilinear transform, build the b and a coefficients with
    unity DC or Nyquist gain ...", and its logic raises
    ValueError("ftype must be 'lowpass' or 'highpass'"), with the bandpass
    rejection exercised in its contract test.
  - Router lines (skills/cross-cutting/SKILL.md, verified at prep): "FIR
    lowpass filter questions (windowed-sinc, finite impulse response taps,
    linear phase, group delay, Hamming window) route to the numerics
    fir-filter-design sub-skill" and "Bandpass and bandstop digital-filter
    questions (Butterworth IIR bandpass/bandstop by the z-domain frequency
    transformation, band-edge verification) route to the numerics
    bandpass-bandstop-filter-design sub-skill; lowpass and highpass
    questions stay with digital-filter-design." No FIR band cell exists in
    the router; the new leaf is the additive sibling the router line needs
    next. Whole-tree greps at prep confirm the only filter leaves anywhere
    are the three numerics siblings plus gnc complementary-filter (a
    first-order LP sensor-fusion split, no FIR band machinery).
- Standards id: naca-tr-824 (reference-only, present in standards-map.yaml
  line 171, grep-verified). Ledger Standard: naca-tr-824. fir-filter-design
  compliance states the numerics convention: "NACA TR-824 anchors the
  numerics-pack public-domain reference set; windowed-sinc FIR design and
  its windows are classical digital filter methodology (Hamming,
  Oppenheim and Schafer style summaries), paraphrase-only per
  standards-map.yaml." The new leaf keys the same reference-only id and
  the same standard engineering methodology (Oppenheim and Schafer,
  Discrete-Time Signal Processing, 3rd ed., Section 8.4, FIR design by
  windowing, with the highpass prototype from spectral inversion of the
  lowpass response and the bandpass/bandstop prototypes from cosine
  modulation or frequency translation; identical closed forms in Proakis
  and Manolakis, Digital Signal Processing, 4th ed., Chapter 10, and
  Hamming, Digital Filters).
- Family: cross-cutting

## Claim

Design a linear-phase finite-impulse-response highpass, bandpass, or
bandstop tap set by the windowed-sinc method with the prototype-extension
relations of the published anchor: build the windowed ideal lowpass
prototype p[n] = w[n]*sin(wc*(n - M))/(pi*(n - M)) with the center limit
wc/pi at the lowpass cutoff wc (for the band types wc is the half
bandwidth (high_cutoff_hz - low_cutoff_hz)/2 and the prototype is
translated to the arithmetic center of the two requested edges,
w0 = 2*pi*((low + high)/2)/fs), then form the highpass taps by spectral
inversion h_hp[n] = w[n]*delta[n - M] - p[n], the bandpass taps by cosine
frequency translation h_bp[n] = 2*p[n]*cos(w0*(n - M)), and the bandstop
taps by spectral inversion of the translated bandpass
h_bs[n] = w[n]*delta[n - M] - 2*p[n]*cos(w0*(n - M)), with the
rectangular, Hann, Hamming, or Blackman window weights, unity passband
gain normalization (exact Nyquist gain 1 for the highpass, exact center
gain 1 for the bandpass, exact DC gain 1 for the bandstop), a real
cosine-sum magnitude response in dB at any probe frequency, a constant
group delay of (N - 1)/2 samples from the symmetric tap set, and
direct-form convolution filtering of a sampled signal. Every tap is
computed from closed-form sine, cosine and window algebra, none looked
up, no iteration and no search: deterministic, offline, pure Python
stdlib (math only), the same family shape as the three sibling filter
leaves. The requested band edges (the single cutoff for the highpass)
carry the windowed-sinc transition midpoint: the prototype response at
its own cutoff is the gain-0.5 midpoint of the transition, so the
measured edge gains sit on the -6 dB band-edge geometry at
-6.020599913279624 dB (20*log10(0.5)), the anchor convention of the FIR
lowpass sibling, within window ripple and image leakage (worked anchors
-5.995505518 to -6.073441862 dB at the Hamming geometry below). The
-3.010299956639813 dB level (20*log10(1/sqrt(2))) is the Butterworth
prototype-3 dB-point convention of the IIR siblings and is reached
strictly INSIDE the nominal passband of these FIR filters, never at the
requested edges: measured crossings 215.960 and 784.004 Hz inside the
200 to 800 Hz passband of the worked bandpass, 183.781 and 816.188 Hz at
the bandstop notch shoulders, 103.994 Hz above the 100 Hz highpass
cutoff. Produces the coefficient vector, the band-edge gain checks
against the -6.020599913 dB midpoint target, the magnitude response in dB
at any probe, the group delay, and the filtered output of a sampled
signal. Does NOT do: IIR coefficient design of any kind, no Butterworth
prototypes, no poles, no bilinear transform, no prewarping, no recursive
difference equation and no filter order parameter: digital-filter-design
owns the Butterworth IIR LP/HP cell with a hard ftype fence (its contract
test raises ValueError for any non-LP/HP type) and
bandpass-bandstop-filter-design owns the Butterworth IIR BP/BS cell by
the z-domain frequency transformation with both edges at exactly
-3.010299956640 dB; standalone FIR lowpass design with unity DC gain
normalization (fir-filter-design owns design_lowpass, this leaf exposes
no lowpass design function and uses the prototype only as internal
translation material); even numbers of taps (rejected, the center index
M must stay integer for symmetric linear-phase taps); spectral analysis
of the filtered signal (fast-fourier-transform); Welch periodogram
estimation of a measured time history (power-spectral-density);
differentiating the filtered signal (finite-difference-derivatives);
delay estimation between two filtered traces
(cross-correlation-analysis); and choosing band edges from a measured
spectrum (no owner, out of scope). Design inputs must satisfy 0 < fc <
fs/2 for the highpass and 0 < low_cutoff_hz < high_cutoff_hz < fs/2 for
the band types, with odd num_taps >= 1; nonphysical inputs raise
ValueError.

## Model (implement exactly)

Pure stdlib, math only. No numpy, no scipy, no cmath, no external
processes. Deterministic: plain row-by-row accumulation of the cosine
sums in index order, no generator-sum float reassociation, no RNG.
Module name fir_bandpass_bandstop_filter_design. All taps are real
floats, symmetric about the integer center M = (num_taps - 1)/2, so the
filter is linear phase with constant group delay (num_taps - 1)/2
samples and its transfer function is all-zero: unconditionally stable,
no feedback path.

Defining relations (pin these exactly; every function below derives from
them):
- Window weights w[n], n = 0..num_taps - 1, denominator num_taps - 1
  (identical formulas to the FIR lowpass sibling): rectangular all 1.0;
  hann 0.5 - 0.5*cos(2*pi*n/(num_taps - 1)); hamming
  0.54 - 0.46*cos(2*pi*n/(num_taps - 1)); blackman
  0.42 - 0.5*cos(2*pi*n/(num_taps - 1)) +
  0.08*cos(4*pi*n/(num_taps - 1)). The windows are symmetric about M, and
  every window evaluates to exactly 1.0 at the center tap n = M
  (cos(pi) = -1), so the windowed taps stay symmetric (linear phase).
  num_taps = 1 is the recorded degenerate case: the window is [1.0] and
  every design normalizes to the single tap [1.0].
- Ideal lowpass prototype, center M:
  h_lp[n] = sin(wc*(n - M))/(pi*(n - M)) for n != M, center limit
  h_lp[M] = wc/pi = 2*fc_proto/fs (the limit of sinc at 0). For the
  highpass fc_proto = cutoff_hz; for the band types
  fc_proto = (high_cutoff_hz - low_cutoff_hz)/2 (the half bandwidth).
- Windowed prototype p[n] = w[n]*h_lp[n] (NOT DC-normalized; the raw
  prototype is the translation material and its DC gain is only
  approximately 1, which is what limits the spectral-inversion null
  depth, see below).
- Band geometry for the band types: center frequency w0 = 2*pi*
  center_frequency_hz/fs with center_frequency_hz = (low_cutoff_hz +
  high_cutoff_hz)/2 (the arithmetic mean of the requested edges, where
  the bandpass gain is normalized to exactly 1); the prototype cutoff is
  the half bandwidth, so the requested edges are the images of the
  prototype cutoff wc = 2*pi*fc_proto/fs at w0 - wc and w0 + wc.
- Constructions (the published anchor relations, Oppenheim and Schafer
  8.4 / Proakis and Manolakis ch. 10):
  highpass (spectral inversion): b_raw[n] = w[n]*delta[n - M] - p[n],
  where delta[n - M] is 1 at n = M and 0 elsewhere; at the center tap the
  raw value is w[M]*(1 - 2*fc_proto/fs) because h_lp[M]*w[M] is
  subtracted from the windowed unit sample.
  bandpass (cosine frequency translation):
  b_raw[n] = 2*p[n]*cos(w0*(n - M)).
  bandstop (spectral inversion of the translated bandpass):
  b_raw[n] = w[n]*delta[n - M] - 2*p[n]*cos(w0*(n - M)).
  Because the constructions are per-sample additions and scalings, they
  commute with the window: the raw bandstop taps plus the raw bandpass
  taps equal the windowed unit sample w[n]*delta[n - M] exactly,
  elementwise (the complement identity the contract test recomputes).
- Unity passband gain normalization: divide the raw taps by the passband
  response scale, G = |cosine sum of the raw taps at the passband
  reference|: for the highpass the Nyquist reference fs/2
  (G = |sum_n b_raw[n]*cos(pi*(n - M))|), for the bandpass the center
  frequency (G = |sum_n b_raw[n]*cos(w0*(n - M))|), for the bandstop DC
  (G = |sum_n b_raw[n]|). After normalization the passband gain is
  exactly 1 to float precision at the reference (real anchors
  1.000000000000000). The bandstop is then also near-unity at Nyquist
  and near DC away from the notch (measured -0.020390713 to
  -0.031101109 dB in the passbands of the worked example), because the
  notch complement is not perfect.
- Magnitude response: the symmetric tap set has the real response
  H(f) = sum_n b[n]*cos(2*pi*f/fs*(n - M)) (the linear phase term
  dropped); gain_at returns |H(f)|, magnitude_response_db returns
  20*log10(|H(f)|). The cosine-sum evaluation is exact on the probe
  grid; the response never equals 0.0 in float at the worked probes
  (the null floors below are small but nonzero), so dB stays finite.
- Band-edge geometry claim (the recorded assumption and deviation note):
  the receipt anchor line asks to "verify band edges at -3.0103 dB like
  the sibling anchors". That value is the Butterworth prototype 3 dB
  point convention of the IIR siblings (bandpass-bandstop-filter-design
  and digital-filter-design), whose transformed band edges are images of
  the prototype's |H| = 1/sqrt(2) point. A windowed-sinc FIR tap set has
  no such point at its requested edges: the prototype response at its own
  cutoff is the gain-0.5 midpoint of the transition (the FIR lowpass
  sibling's -6 dB cutoff geometry), so the band edges of these FIR
  filters sit on the -6.020599913279624 dB (gain 0.5) midpoint within
  window ripple and image leakage, and the -3.010299956639813 dB level is
  crossed strictly inside the passband (bandpass) or at the notch
  shoulders (bandstop), never at the requested edges. The spec and its
  contract therefore verify the edges against the FIR midpoint target
  -6.020599913279624 dB (measured anchors below), and separately pin the
  measured -3.010299956639813 dB crossings to document where that level
  genuinely sits. This is the standard published windowed-sinc method
  implemented exactly; the deviation from the -3.0103 dB phrasing is the
  physically forced one, with the receipt's own (d) block supporting the
  "-6 dB band-edge geometry".
- Null floors: the highpass spectral-inversion DC null and the bandpass
  stopband nulls are not structural zeros; they are limited by the
  prototype's imperfect finite-window DC gain and by the prototype
  stopband response at the translated image frequencies (real floors
  -50.065791442 to -66.996568467 dB in the worked bandpass, -56.644897249
  dB at the worked highpass DC). The bandstop notch null is limited by
  the prototype response at twice the center frequency (worked null
  -85.671233701 dB at 500 Hz).
- Group delay of the symmetric tap set: (num_taps - 1)/2 samples,
  constant for every frequency because the phase is exactly linear.
- Direct-form convolution filter: y[n] = sum_k b[k]*x[n - k], input
  treated as zero outside its range, output the same length as the
  input; with the worked 101-tap sets the first 50 output samples carry
  the filter transient, and steady-state amplitudes are read after the
  group delay.
- Units are SI throughout: Hz for frequencies, samples per second for fs.

Functions (public API, 10):
- window_coefficients(window, num_taps) -> list of float, len num_taps.
  ValueError if num_taps < 1 or the window name is not one of
  rectangular, hann, hamming, blackman. num_taps = 1 returns [1.0].
- ideal_lowpass_taps(cutoff_hz, sample_rate_hz, num_taps) -> list of
  float, len num_taps, the ideal lowpass impulse response with the
  center limit 2*fc/fs. ValueError if fs <= 0, cutoff_hz <= 0,
  cutoff_hz >= fs/2, or num_taps < 1.
- design_highpass(cutoff_hz, sample_rate_hz, num_taps, window) -> dict
  with EXACTLY the keys coefficients, num_taps, cutoff_hz,
  sample_rate_hz, window, group_delay_samples, nyquist_gain: the
  spectral-inversion tap set normalized to unity Nyquist gain
  (nyquist_gain = 1.0 within 1e-12). ValueError set: fs <= 0;
  cutoff_hz <= 0; cutoff_hz >= fs/2; num_taps < 1 or even num_taps;
  unknown window name.
- design_bandpass(low_cutoff_hz, high_cutoff_hz, sample_rate_hz,
  num_taps, window) -> dict with EXACTLY the keys coefficients,
  num_taps, low_cutoff_hz, high_cutoff_hz, center_frequency_hz,
  sample_rate_hz, window, group_delay_samples, center_gain: the
  cosine-translated tap set normalized to unity gain at the center
  frequency (center_gain = 1.0 within 1e-12; center_frequency_hz =
  (low_cutoff_hz + high_cutoff_hz)/2). ValueError set: fs <= 0;
  low_cutoff_hz <= 0; low_cutoff_hz >= high_cutoff_hz;
  high_cutoff_hz >= fs/2; num_taps < 1 or even num_taps; unknown
  window name.
- design_bandstop(low_cutoff_hz, high_cutoff_hz, sample_rate_hz,
  num_taps, window) -> dict with EXACTLY the keys coefficients,
  num_taps, low_cutoff_hz, high_cutoff_hz, center_frequency_hz,
  sample_rate_hz, window, group_delay_samples, dc_gain: spectral
  inversion of the translated bandpass, normalized to unity DC gain
  (dc_gain = 1.0 within 1e-12). Same ValueError set as
  design_bandpass.
- gain_at(coefficients, freq_hz, sample_rate_hz) -> float, the linear
  magnitude |H(freq_hz)| of the real cosine sum. ValueError if the
  coefficient list is empty, fs <= 0, or the probe lies outside
  [0, fs/2] (0 Hz and fs/2 are valid probes: the DC and Nyquist gains of
  the worked designs are probed there).
- magnitude_response_db(coefficients, freq_hz, sample_rate_hz) -> float,
  20*log10(gain_at(...)) in dB. Same ValueError set.
- group_delay_samples(num_taps) -> float (num_taps - 1)/2. ValueError if
  num_taps < 1.
- filter_signal(coefficients, samples) -> list of float, same length as
  the input, the direct-form convolution with zero-padded boundaries.
  ValueError if the coefficient list or the sample list is empty, or any
  entry is non-finite.
- band_edge_checks(coefficients, ftype, sample_rate_hz, low_cutoff_hz,
  high_cutoff_hz=None) -> dict {low_edge_db, high_edge_db, target_db,
  low_edge_ok, high_edge_ok, passband_ok, extra, verdict}: ftype in
  highpass, bandpass, bandstop. For ftype "highpass" the single edge is
  low_cutoff_hz and high_cutoff_hz must be None (ValueError otherwise).
  target_db = -6.020599913279624 (the module constant 20*log10(0.5), the
  FIR midpoint band-edge target). low_edge_db and high_edge_db are the
  measured magnitude responses at the requested edges (for the highpass
  high_edge_db is None and high_edge_ok is True). low_edge_ok and
  high_edge_ok are True when the measured edge sits within 0.1 dB of
  target_db. passband_ok: for the highpass the Nyquist gain within 0.1 dB
  of 0 dB; for the bandpass the center gain within 0.1 dB of 0 dB; for
  the bandstop the DC gain within 0.1 dB of 0 dB and the Nyquist gain
  within 0.1 dB of 0 dB. extra carries the measured passband reference
  gain(s) in dB (a float for highpass/bandpass, a (dc_db, nyquist_db)
  pair for bandstop). verdict is "PASS" only if low_edge_ok,
  high_edge_ok and passband_ok all hold. ValueError for unknown ftype,
  fs <= 0, invalid edges, or high_cutoff_hz not None with ftype
  "highpass".
Private helpers (module-internal, documented for the contract test):
_require_window, _require_num_taps (odd, >= 1), _require_design_inputs
(per-type physical range checks), _windowed_prototype(cutoff_hz,
sample_rate_hz, num_taps, window) -> (p, m), _translate_invert(ftype,
... ) -> (raw taps, m, w0 or None) implementing the three constructions,
_cos_sum_response(taps, m, freq_hz, sample_rate_hz) returning the real
sum. ValueErrors on nonphysical inputs are part of the contract; every
assert is tolerance-based (isclose/delta style), never exact float
equality on computed sums.

Identities to test (closed-form checks verifiable WITHOUT the builder's
module, tolerance-based asserts only, real anchor values cited below):
- Symmetry: max |b[n] - b[num_taps - 1 - n]| below 1e-12 for every
  design (real anchors 1.388e-17 highpass, 2.776e-17 bandpass and
  bandstop at the worked geometry); the group delay identity
  (num_taps - 1)/2 = 50.0 at 101 taps.
- Raw-construction recovery: with math only, rebuild the window w[n],
  the prototype p[n] = w[n]*sin(wc*(n - M))/(pi*(n - M)) at the worked
  geometry, the raw tap sets from the three defining relations, and the
  scale G as the passband cosine sum of the raw taps; then
  b[n]*G equals the raw tap at every n to float precision (real anchors:
  bandpass 0.000e+00, bandstop 1.926e-34, highpass 0.000e+00), and the
  bandstop complement identity b_bs_raw[n] + b_bp_raw[n] =
  w[n]*delta[n - M] holds to 0.000e+00.
- Edge midpoint geometry: the measured edge gains sit within 0.1 dB of
  -6.020599913279624 dB at the worked geometry (real anchors
  -5.995505518 and -6.018418812 dB for the bandpass, -6.013188638 dB for
  the highpass, -6.073441862 and -6.050454002 dB for the bandstop), and
  the bandpass and bandstop passband references measure 0.000000000 dB
  (unity by construction).
- Where -3.010299956639813 dB sits (the Butterworth edge convention is
  NOT at the FIR edges): measured crossings at the worked geometry:
  bandpass 215.960 and 784.004 Hz, strictly inside the requested 200 to
  800 Hz passband; bandstop notch shoulders 183.781 and 816.188 Hz,
  strictly outside the notch band; highpass 103.994 Hz, strictly above
  the requested 100 Hz cutoff.
- Unity passband gain: nyquist_gain, center_gain and dc_gain of the
  three worked designs equal 1.0 within 1e-12 (real anchors
  1.000000000000000).
- dB consistency: magnitude_response_db equals 20*log10(gain_at) at
  every probe (real difference 0.000000000000e+00 at 400 Hz).
- Cosine-sum structure at the worked geometry: because w0*M = 12.5*pi at
  101 taps, the bandpass and bandstop taps at offsets n - M = +-2 mod 4
  are exactly 0 (real b[48] = b[52] = 0.000000000000) and the outer
  taps b[0] and b[100] are 0.000000000000; these are geometry-specific
  structural zeros of the worked example, not general claims.
- Filtering identity: the output of filter_signal on a multi-tone record
  reproduces the designed |H| at each tone by quadrature projection over
  a settled integer-cycle tail, relative difference below 2e-11 (real
  anchors 0.000e+00 to 1.265e-11).
- Impulse round trip: filter_signal(b, delta) reproduces b exactly
  (real max error 0.000e+00).
- Determinism: two identical design calls are bitwise identical; no
  imports beyond math; no RNG.
- Stopband floors: the worked bandpass probes measure -62.087519915 dB
  at 100 Hz, -61.325771718 dB at 1200 Hz, -65.756900774 dB at 1600 Hz
  and -66.996568467 dB at Nyquist (Hamming, window floor territory); the
  four-window trade at the 1200 Hz probe runs from -38.919 dB
  (rectangular) through -61.326 dB (Hamming) and -85.570 dB (Hann) to
  -94.916 dB (Blackman).

## Worked example

Primary geometry (band types): fs = 4000 Hz, band edges low = 200 Hz,
high = 800 Hz (the corpus query-1 geometry), num_taps = 101, Hamming
window; the prototype lowpass cutoff is the half bandwidth
fc_proto = 300 Hz (wc = 0.15*pi) and the translation center is
w0 = 0.25*pi, center_frequency_hz = 500 Hz. Highpass geometry: fs =
1000 Hz, cutoff fc = 100 Hz (wc = 0.2*pi), num_taps = 101, Hamming. All
values below are REAL outputs of the prep anchor
/tmp/w45spec/anchor_fir_bandpass_bandstop_filter_design.py (stdlib math
only, exit 0, all checks passed):

- Highpass (design_highpass(100, 1000, 101, "hamming")): group delay
  50.0 samples, nyquist_gain 1.000000000000000, symmetry error 1.4e-17.
  Center tap b[50] = 0.800131546113 (the windowed unit sample minus the
  prototype center, w[M]*(1 - 2*fc/fs) = 0.8, scaled by G), neighbors
  b[49] = b[51] = -0.186958764181, b[48] = b[52] = -0.150841106810,
  outer taps b[1] = b[99] = 0.000308982598, b[2] = b[98] =
  0.000527514464, b[0] = b[100] = 0.000000000000 (float floor of the
  sine at an integer multiple of pi). Edge gain at the requested cutoff
  100 Hz: -6.013188638 dB, 0.007411 dB from the midpoint target
  -6.020599913 dB; DC gain -56.644897249 dB (the spectral-inversion null
  floor); fc/2 gain at 50 Hz -55.337139253 dB; passband +0.009876223 dB
  at 150 Hz (transition ripple hump), -0.000850773 dB at 300 Hz,
  -0.000006122 dB at 480 Hz. Tone test (fs = 1000, tail samples
  1000..1999, quadrature projection): a 20 Hz tone measures
  0.001513484842 vs |H| 0.001513484842 (-56.400 dB, relative difference
  1.994e-13) and a 300 Hz tone measures 0.999902055900 vs |H|
  0.999902055900 (relative difference 7.883e-15). The -3.010299956640 dB
  level is crossed at 103.994 Hz, above the requested cutoff.
- Bandpass (design_bandpass(200, 800, 4000, 101, "hamming"), the corpus
  query-1 geometry): center_frequency_hz = 500.000000000 Hz = (200 +
  800)/2, group delay 50.0, center_gain 1.000000000000000, symmetry
  error 2.8e-17. Center tap b[50] = 0.299984336175, b[49] = b[51] =
  0.204171360832, b[48] = b[52] = 0.000000000000 (the w0*M = 12.5*pi
  structural zeros), b[1] = b[99] = -0.000662242631, b[2] = b[98] =
  -0.000651902497, b[3] = b[97] = -0.000132065332, b[0] = b[100] =
  0.000000000000. Edge gains: low edge 200 Hz -5.995505518 dB and high
  edge 800 Hz -6.018418812 dB, within 0.025094 and 0.002181 dB of the
  -6.020599913 dB midpoint target (the lower-edge bias is the prototype
  stopband response at the far image frequency 700 Hz adding
  constructively); center 500 Hz gain +0.000000000 dB; stopband probes
  -50.065791442 dB at DC, -62.087519915 dB at 100 Hz, -57.420533724 dB
  at 1000 Hz, -61.325771718 dB at 1200 Hz, -65.756900774 dB at 1600 Hz,
  -66.996568467 dB at Nyquist (2000 Hz); passband probe 400 Hz
  -0.002015073 dB. band_edge_checks verdict PASS. Tone test (fs = 4000,
  tail samples 1000..4999): 100 Hz measures 0.000786364690 vs |H|
  0.000786364690 (-62.088 dB, relative difference 3.144e-14); the 400 Hz
  test tone measures 0.999768033063 vs |H| 0.999768033063 (relative
  difference 2.776e-15, -0.002 dB); 1200 Hz measures 0.000858442902 vs
  |H| 0.000858442902 (-61.326 dB, relative difference 2.316e-12). The
  -3.010299956640 dB level is crossed at 215.960 and 784.004 Hz,
  strictly inside the requested passband.
- Bandstop (design_bandstop(200, 800, 4000, 101, "hamming"), spectral
  inversion of the translated bandpass): dc_gain 0.999999999999999,
  group delay 50.0, symmetry error 2.8e-17. Center tap b[50] =
  0.697809868401 (1 minus the bandpass center tap to the scale), b[49] =
  b[51] = -0.203543185312, b[48] = b[52] = -0.000000000000, b[1] =
  b[99] = 0.000660205105, b[2] = b[98] = 0.000649896784, b[3] = b[97] =
  0.000131659006. Edge gains: 200 Hz -6.073441862 dB and 800 Hz
  -6.050454002 dB, within 0.052842 and 0.029854 dB of the midpoint
  target; DC gain -0.000000000 dB and Nyquist gain -0.031101109 dB
  (unity passband, small notch-complement droop); passband probes
  -0.020390713 dB at 100 Hz and -0.034678594 dB at 1200 Hz; in-notch
  probe -74.933184863 dB at 400 Hz; the notch center null at 500 Hz
  measures -85.671233701 dB, the float floor of the imperfect complement
  (limited by the prototype response at 2*w0 = 1000 Hz). band_edge_checks
  verdict PASS. Tone test: 100 Hz measures 0.997655185849 vs |H|
  0.997655185849 (relative difference 5.342e-15); the 500 Hz notch tone
  measures 0.000052052107 vs |H| 0.000052052107 (-85.671 dB, relative
  difference 1.265e-11, the in-notch rejection); 1200 Hz measures
  0.996015438849 vs |H| 0.996015438849 (relative difference 5.573e-16).
  The -3.010299956640 dB shoulders sit at 183.781 and 816.188 Hz,
  strictly outside the notch band.
- Window trade at the bandpass geometry (101 taps, 200 to 800 Hz at
  4000 Hz), edge gains and stopband probes at 900 and 1200 Hz:
  rectangular low_edge -5.701966 dB, high_edge -5.994135 dB, 900 Hz
  -46.380 dB, 1200 Hz -38.919 dB; hann low_edge -6.021533 dB, high_edge
  -6.020536 dB, 900 Hz -58.142 dB, 1200 Hz -85.570 dB; hamming
  low_edge -5.995506 dB, high_edge -6.018419 dB, 900 Hz -62.438 dB,
  1200 Hz -61.326 dB; blackman low_edge -6.020932 dB, high_edge
  -6.020591 dB, 900 Hz -60.091 dB, 1200 Hz -94.916 dB. The midpoint
  geometry holds across all four windows (the rectangular lower edge
  carries the largest image-leakage bias, 0.319 dB above the midpoint);
  the stopband floor follows the window with Blackman deepest and
  rectangular shallowest at the 1200 Hz probe. (The far-field ordering
  differs from the classical first-sidelobe ordering: Hann out-attenuates
  Hamming at the 1200 Hz probe because the Hamming far sidelobe envelope
  decays more slowly; the probes are reported as measured.)
- Structural checks: an impulse through the bandpass reproduces the
  coefficient vector exactly (max error 0.000e+00); a constant 5.0 input
  settles through the bandpass to a tail mean of -1.569208e-02 (the DC
  stopband, -50.065791442 dB times 5.0), through the bandstop to
  5.000000000 (unity DC), through the highpass to 7.357413e-03 (the DC
  null floor); an alternating +5/-5 input settles through the bandpass to
  a tail RMS of 4.468601e-04 relative to 5.0 (Nyquist stopband,
  -66.996568467 dB) and through the bandstop to 0.996425755 (Nyquist
  gain). Two identical design calls are bitwise identical.
- Recorded low-cutoff pitfall (corpus query-2 geometry): the windowed-
  sinc geometry needs the tap count large enough that the window main
  lobe resolves the cutoff, fc*num_taps/fs >= about 2. At the query
  geometry fc = 0.5 Hz, fs = 100 Hz, num_taps = 51 (fc*num_taps/fs =
  0.255) the highpass is degenerate: measured gains -2.689832 dB at
  0.1 Hz (the query's reported rejection point), -2.545845 dB at 0.5 Hz,
  -2.696011 dB at DC, and the -6.0206 dB crossing sits below 0.001 Hz,
  not at the requested 0.5 Hz cutoff; the design cannot realize the
  cutoff. At num_taps = 501 (fc*num_taps/fs = 2.505) the geometry is
  restored: -50.768053 dB at 0.1 Hz, -6.041242 dB at 0.5 Hz, crossing at
  0.5004 Hz. The builder must not assert edge anchors at geometries
  below fc*num_taps/fs ~ 1; the contract pins the worked examples above.
- ValueError set probed and confirmed by the anchor checks: fs <= 0;
  cutoff_hz <= 0; cutoff_hz >= fs/2; low_cutoff_hz <= 0; low_cutoff_hz
  >= high_cutoff_hz; high_cutoff_hz >= fs/2; even num_taps; num_taps <
  1; unknown window names; probes outside [0, fs/2]; empty or non-finite
  sample lists; empty coefficient lists; unknown ftype values; and
  high_cutoff_hz not None with ftype "highpass".
Run your module and take the real outputs as assert targets
(tolerance-based); the anchors above are real prep outputs of
/tmp/w45spec/anchor_fir_bandpass_bandstop_filter_design.py (stdlib math
only, exit 0, all checks passed).

## Validation list (contract test must include)

- design_highpass(100, 1000, 101, "hamming") returns a dict with EXACTLY
  the keys coefficients, num_taps, cutoff_hz, sample_rate_hz, window,
  group_delay_samples, nyquist_gain; coefficients[50] within 1e-9 of
  0.800131546113, coefficients[49] within 1e-9 of -0.186958764181,
  coefficients[48] within 1e-9 of -0.150841106810, coefficients[1]
  within 1e-9 of 0.000308982598, coefficients[0] within 1e-9 of 0.0, and
  coefficients[n] == coefficients[100 - n] within 1e-12; nyquist_gain
  within 1e-12 of 1.0; group_delay_samples 50.0.
- design_bandpass(200, 800, 4000, 101, "hamming") returns the dict with
  EXACTLY the keys coefficients, num_taps, low_cutoff_hz,
  high_cutoff_hz, center_frequency_hz, sample_rate_hz, window,
  group_delay_samples, center_gain; center_frequency_hz within 1e-9 of
  500.0; coefficients[50] within 1e-9 of 0.299984336175,
  coefficients[49] within 1e-9 of 0.204171360832, coefficients[48] and
  coefficients[52] within 1e-9 of 0.0, coefficients[1] within 1e-9 of
  -0.000662242631, coefficients[3] within 1e-9 of -0.000132065332,
  coefficients[0] within 1e-9 of 0.0; center_gain within 1e-12 of 1.0.
- design_bandstop(200, 800, 4000, 101, "hamming") returns the dict with
  EXACTLY the keys coefficients, num_taps, low_cutoff_hz,
  high_cutoff_hz, center_frequency_hz, sample_rate_hz, window,
  group_delay_samples, dc_gain; coefficients[50] within 1e-9 of
  0.697809868401, coefficients[49] within 1e-9 of -0.203543185312,
  coefficients[1] within 1e-9 of 0.000660205105; dc_gain within 1e-12 of
  1.0.
- Edge gains at the worked geometry: highpass cutoff gain within 1e-6 dB
  of -6.013188638 dB and within 0.1 dB of -6.020599913279624 dB;
  bandpass edges within 1e-6 dB of -5.995505518 and -6.018418812 dB;
  bandstop edges within 1e-6 dB of -6.073441862 and -6.050454002 dB;
  band_edge_checks returns verdict PASS for all three worked designs,
  with target_db = -6.020599913279624.
- Unity passband gains within 1e-6 dB of 0 at the references: highpass
  at fs/2, bandpass at 500 Hz (anchor +0.000000000 dB), bandstop at DC
  (anchor -0.000000000 dB); bandstop Nyquist gain within 0.1 dB of 0
  (anchor -0.031101109 dB).
- The -3.010299956639813 dB level is NOT at the requested edges: the
  bandpass crossing frequencies measured by the contract lie strictly
  between the edges and the center (real anchors 215.960 and 784.004 Hz
  inside 200 to 800 Hz), the bandstop shoulders lie strictly outside the
  notch band (183.781 and 816.188 Hz), and the highpass crossing lies
  above the cutoff (103.994 Hz); assert the edge gains differ from
  -3.010299956640 dB by more than 1 dB at the requested edges.
- Raw-construction identities: with math only, rebuild the window, the
  prototype, the three raw tap sets and the passband scale G at the
  worked geometry; assert max |b[n]*G - raw[n]| below 1e-9 for the
  highpass, bandpass and bandstop, and assert b_bs_raw[n] +
  b_bp_raw[n] equals w[n]*delta[n - M] elementwise below 1e-9.
- Symmetry: max |b[n] - b[100 - n]| below 1e-12 for all three worked
  designs (real anchors 1.4e-17 and 2.8e-17).
- Signal identity: the three-tone records at the worked geometries
  through filter_signal reproduce the designed |H| at each tone by
  quadrature projection over the settled integer-cycle tail within 1e-9
  relative (real anchors 0.000e+00 to 1.265e-11), with the bandpass
  400 Hz gain above -1 dB, the 100 Hz and 1200 Hz bandpass gains below
  -40 dB (anchors -62.088 and -61.326 dB), the bandstop 500 Hz gain
  below -40 dB (anchor -85.671 dB), and the 100 Hz and 1200 Hz bandstop
  gains above -0.5 dB; the highpass 300 Hz gain above -1 dB and the
  20 Hz gain below -40 dB (anchor -56.400 dB).
- Structural: the bandpass impulse round trip reproduces the
  coefficients exactly (anchor 0.000e+00); a constant 5.0 input settles
  through the bandstop to 5.0 within 1e-6 (anchor 5.000000000) and
  through the bandpass to a tail mean below 0.05 in magnitude (anchor
  -1.569208e-02); the bandpass and highpass DC null floors read below
  -40 dB at 0 Hz (anchors -50.065791442 and -56.644897249 dB) and the
  bandstop notch null below -60 dB at 500 Hz (anchor -85.671233701 dB).
- Window trade: at the bandpass geometry the Hann and Blackman edge
  gains stay within 0.1 dB of -6.020599913 dB and the rectangular lower
  edge within 0.4 dB (anchor -5.701966 dB); the 1200 Hz probe orders
  rectangular -38.919 dB above hamming -61.326 dB above hann -85.570 dB
  above blackman -94.916 dB, each asserted within 0.5 dB of its anchor.
- Determinism: two identical calls to each design function are bitwise
  identical; the module imports nothing beyond math; no RNG anywhere.
- Degenerate sanity: num_taps = 1 returns the single tap [1.0] for all
  three ftypes (window [1.0], center limit normalization); num_taps = 3
  designs run and stay symmetric.
- ValueErrors: all design functions on fs = -1000, fs = 0, cutoff_hz = 0
  and cutoff_hz = 600 on fs = 1000, low_cutoff_hz = 0, low_cutoff_hz ==
  high_cutoff_hz, high_cutoff_hz = 2000 on fs = 4000, even num_taps
  (100 and 2), num_taps = 0, and window "bartlett"; gain_at and
  magnitude_response_db at -1 and 600 Hz on fs = 1000 and on an empty
  coefficient list; filter_signal on an empty sample list and on a list
  containing nan; band_edge_checks on ftype "notch" and on ftype
  "highpass" with high_cutoff_hz = 300.
- Run the contract test under BOTH interpreters (/usr/bin/python3 3.9.6
  and ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
  computed sums; use assertAlmostEqual/math.isclose everywhere. All
  asserts above are tolerance-based and must hold on both.

## Corpus fragment (eval/hit1-wave45-fir-bandpass-bandstop-filter-design.yaml)

Query 1 (copy verbatim):
  "design a linear-phase FIR bandpass filter by the windowed-sinc
  frequency-translation method: build the 101-tap bandpass tap set for
  the 200 to 800 hertz passband at a 4000 hertz sample rate with the
  hamming window, verify the center-band gain and the band-edge gains,
  and filter the 400 hertz test tone"
  intent: "cross-cutting; windowed-sinc FIR bandpass design by cosine
  frequency translation of the windowed-sinc lowpass prototype at the
  101-tap 200 to 800 hertz passband geometry, with center-band and
  band-edge gain verification and a filtered 400 hertz test tone"
  expected_skill: "cross-cutting/numerics/fir-bandpass-bandstop-filter-design"
Query 2 (copy verbatim):
  "strip the accelerometer bias drift with an FIR highpass filter built
  by spectral inversion of the windowed-sinc lowpass prototype: 51
  taps, hamming window, 0.5 hertz cutoff at 100 hertz sample rate, and
  report the low-frequency rejection in dB at 0.1 hertz"
  intent: "cross-cutting; windowed-sinc FIR highpass design by spectral
  inversion of the windowed-sinc lowpass prototype, reporting the
  low-frequency rejection in dB at 0.1 hertz"
  expected_skill: "cross-cutting/numerics/fir-bandpass-bandstop-filter-design"
Task ids: w45-fir-bandpass-bandstop-filter-design-1 and -2. The queries
carry the receipt's distinctive hyphenated tokens only
(fir-bandpass-filter-design, windowed-sinc, frequency-translation-method,
linear-phase-band-filter; fir-highpass-filter-design,
spectral-inversion-method) and were adversarially checked at prep
against every existing tag set: no butterworth, bilinear, or iir tokens
anywhere, so the two IIR leaves (digital-filter-design,
bandpass-bandstop-filter-design) cannot score; no lowpass geometry, no
unity-DC-normalization vocabulary and no design_lowpass surface, so
fir-filter-design cannot score (its logic hardwires a single lowpass
cutoff geometry with ideal_lowpass_taps and design_lowpass as the only
design functions and holds the zero-owner grep at prep: fir-band,
fir highpass, fir bandpass, fir bandstop, spectral inversion and
frequency translation each return 0 hits in eval/hit1-corpus.yaml and in
every skill file). The corpus queries are routing targets only: the
51-tap 0.5 Hz query-2 geometry is the recorded low-cutoff pitfall of the
Worked example, and no contract anchor asserts its degenerate numbers.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design a linear-phase
finite-impulse-response highpass, bandpass, or bandstop filter by the
windowed-sinc method with spectral inversion and cosine frequency
translation of a lowpass prototype:" (wave-45 leaf plan direction: lead
with the three FIR band-type deliverable tokens) and include the outputs
in the Claim order. Metadata tags EXACTLY as the receipt's gate (f)
lists them, in that order: [fir-highpass-filter-design,
fir-bandpass-filter-design, fir-bandstop-filter-design,
spectral-inversion-method, frequency-translation-method,
windowed-sinc-band-filter, linear-phase-band-filter]. All are
hyphenated compounds; NONE duplicates any existing tag, so the LP leaf
keeps w31-fir-filter-design-1/2 (its tags windowed-sinc,
finite-impulse-response, linear-phase-filter, fir-lowpass, filter-taps,
hamming-window are untouched), and the IIR leaves keep
w28-digital-filter-design-1/2 and w44-bandpass-bandstop-filter-design-1/2
(their tags butterworth-bilinear vocabulary and
digital-frequency-transformation are untouched). NEVER single generic
words (fir, filter, band, highpass, lowpass, notch, window, dB alone)
and NEVER the sibling-owned routing tokens: butterworth, bilinear,
prewarping, iir, z-domain frequency transformation, prototype order,
the tag digital-frequency-transformation, the tag cutoff-frequency, the
tag filter-coefficients, the tag hamming-window, the tag windowed-sinc,
the tag filter-taps, the tag finite-impulse-response, the tag
linear-phase-filter, unity DC gain normalization of a standalone
lowpass, and the -3.0103 dB edge claim (the Butterworth convention; the
leaf verifies its edges at the -6.020599913 dB gain-0.5 midpoint and
must say so). Window names may appear only inside the method clause,
never as trigger keywords. 50-150 words, <=1000 chars, no em dash, no
content-policy sweep term, action verb present. Recommended wording
(outputs in Claim order):
"Use when you must design a linear-phase finite-impulse-response
highpass, bandpass, or bandstop filter by the windowed-sinc method with
spectral inversion and cosine frequency translation of a lowpass
prototype: build the windowed prototype at the cutoff, the half
bandwidth for bands, form the highpass as the windowed unit sample minus
the prototype, the bandpass as twice the prototype times the center
cosine, and the bandstop as spectral inversion of the translated
bandpass, under the rectangular, Hann, Hamming, or Blackman windows,
with unity passband gain at Nyquist, center, or DC, with the requested
edges at the -6.020599913 dB midpoint. Produces the tap vector,
band-edge gain checks, the magnitude response in dB as the real cosine
sum, the group delay, and the filtered signal. Trigger:
fir-highpass-filter-design, fir-bandpass-filter-design,
fir-bandstop-filter-design, spectral-inversion-method,
frequency-translation-method, windowed-sinc-band-filter,
linear-phase-band-filter."
The description must not claim a -3.0103 dB edge guarantee, a lowpass
deliverable, a Butterworth or IIR surface, or an order parameter; the
"highpass filter" phrase of digital-filter-design's trigger list must
not appear as a bare trigger keyword (use fir-highpass-filter-design).
