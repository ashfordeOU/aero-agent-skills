# Wave-44 leaf spec: bandpass-bandstop-filter-design (cross-cutting,
# numerics pack)

- Path: skills/cross-cutting/numerics/bandpass-bandstop-filter-design/
- Pack: numerics (present siblings digital-filter-design, fir-filter-design,
  fast-fourier-transform, power-spectral-density,
  finite-difference-derivatives, numerical-integration,
  cross-correlation-analysis; the design-owner fences quoted below).
- Provenance: wave-44 leaf-plan lines 136-143 (extension probe task-2 GO):
  "Butterworth IIR bandpass/bandstop via the z-domain LP->BP / LP->BS
  digital frequency transformation (Oppenheim & Schafer/Proakis class),
  coefficients computed not looked up, both band edges verifiable at
  -3.0103 dB like the sibling prewarp anchors; digital-filter-design is
  LP/HP only with a hard ftype fence (quoted), fir-filter-design FIR
  lowpass only; naca-tr-824 numerics convention". Extension receipt
  (wave44-recon/task-9-10-11-receipt.md, task-2 extract): 0 design owners,
  13 declined candidates, bandpass-bandstop-filter-design the single GO.
- Corpus tokens of the leaf: bandpass-filter-design,
  bandstop-filter-design, butterworth-bandpass,
  digital-frequency-transformation.
- Claim fences (quoted from the sibling frontmatter and bodies at prep;
  none of them designs a frequency-selective filter that passes or rejects
  a band of frequencies between two band edges):
  - digital-filter-design (this pack; the immediate sibling) designs a
    digital Butterworth IIR LOWPASS or HIGHPASS only: its description
    reads "Use when you must compute the coefficients of a digital
    Butterworth IIR lowpass or highpass frequency-selective filter from a
    cutoff frequency, sample rate, and order: prewarp the analog cutoff,
    map the normalized Butterworth poles through the bilinear transform,
    build the b and a coefficients with unity DC or Nyquist gain ..." and
    its body reads "This leaf designs frequency-selective filters only".
    The ftype fence is a HARD gate, not a soft preference: its own
    contract test raises ValueError on any non-LP/HP type, including the
    line filter_design_checks(b, a, FS, FC, "bandpass") inside
    test_checks_valueerrors, and its tags carry only iir-lowpass,
    highpass-filter, cutoff-frequency. A bandpass or bandstop request
    cannot be satisfied by that leaf; the new leaf claims the band member
    of the family its hard fence leaves open.
  - fir-filter-design (this pack): its description reads "Use when you
    must design a linear-phase finite-impulse-response lowpass filter
    with the windowed-sinc method: build the ideal lowpass impulse
    response from the cutoff frequency and the sample rate, apply a
    selected window ...". FIR lowpass by windowed-sinc only; no IIR band
    filters, no poles, no recursive difference equation.
  - fast-fourier-transform (this pack): frequency content analysis of a
    signal, not band filtering of it.
  - power-spectral-density (this pack): Welch averaged periodogram of a
    measured time history, spectral estimation of data, no filter
    coefficients.
  - finite-difference-derivatives (this pack): differentiating a signal
    with controlled step-size error, no filtering.
  - limit-cycle-oscillation (flight-test-operations/flutter): its body
    consumes "accelerometer, gyro, or strain data band-passed at the mode
    frequency" as a TEST-APPLICATION input step of the LCO flight test
    workflow; it applies someone else's band-passed data, it does not
    design the band filter, and the whole-tree grep for bandpass|bandstop
    hits only that application phrase plus this leaf's own plan entry.
  Whole-tree greps at prep: bandpass, bandstop, band-pass, band-stop,
  bandpass-filter-design, bandstop-filter-design, butterworth-bandpass
  and digital-frequency-transformation each return ZERO hits in
  eval/hit1-corpus.yaml; in skills/ the only hits are the LCO
  band-passed application phrase above and the sibling's own ftype
  ValueError probe for "bandpass". GENUINE numerics gap (fresh probe,
  GO): no leaf designs a Butterworth IIR filter that passes or stops a
  band between two specified band edges.
- Standards id: naca-tr-824 (reference-only, present in standards-map.yaml
  line 171). Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Design a digital Butterworth IIR bandpass or bandstop filter from its two
band-edge frequencies, the sample rate, and the order, by the z-domain
LP-to-BP and LP-to-BS digital frequency transformation of a digital
Butterworth lowpass prototype (Oppenheim & Schafer / Proakis class
substitution algebra, closed form, no coefficient search): with digital
frequencies wl = 2*pi*low_cutoff_hz/fs and wu = 2*pi*high_cutoff_hz/fs
and the prototype's 3 dB point at wc = 2*pi*prototype_cutoff_hz/fs, form
the substitution parameters alpha = cos((wl+wu)/2)/cos((wu-wl)/2),
kappa_bp = cot((wu-wl)/2)*tan(wc/2) for the bandpass and kappa_bs =
tan((wu-wl)/2)*tan(wc/2) for the bandstop, build the substitution
u' = s*(u^2 - c1*u + c2)/(c2*u^2 - c1*u + 1) with u = z^-1, s = -1 for
the bandpass and +1 for the bandstop, c1, c2 the closed forms below, and
compose it into the prototype numerator and denominator polynomials, so
the transformed order-2n filter has both band edges sitting at exactly
-3.010299957 dB on the magnitude response, the same prewarp-grade
guarantee the LP/HP sibling delivers at a single cutoff. Produces the
bandpass or bandstop coefficient vectors (b and a, len = 2*order + 1,
a[0] = 1, unity peak gain for the bandpass at the center frequency
fs*arccos(alpha)/(2*pi), unity DC and Nyquist gain for the bandstop), the
closed-form substitution parameters, the center frequency, band-edge
gain checks at both edges, the magnitude response in dB at any probe
frequency, and the filtered output of a sampled signal by the
direct-form difference equation, with all coefficients computed and none
looked up. Does NOT do: lowpass or highpass coefficient design
(digital-filter-design owns both, with its ftype fence raising ValueError
for any other type); FIR windowed-sinc coefficient design
(fir-filter-design, FIR lowpass only); spectral analysis of a signal by
the FFT (fast-fourier-transform); Welch spectral estimation of a measured
time history (power-spectral-density); differentiating a signal
(finite-difference-derivatives); or the flutter LCO workflow that
consumes band-passed test data (limit-cycle-oscillation). Band edges
must satisfy 0 < low_cutoff_hz < high_cutoff_hz < fs/2, the prototype
order 1..8, the prototype cutoff defaults to fs/4, the bilinear image of
the classical unit-cutoff analog prototype; nonphysical inputs raise
ValueError.

## Model (implement exactly)

Pure stdlib, math and cmath only. No numpy, no scipy, no external
processes. Deterministic: plain row-by-row accumulation in polynomial
multiply, no generator-sum float reassociation, no RNG. Module name
bandpass_bandstop_filter_design. All response probes evaluate the
transfer function on the unit circle with u = exp(-j*2*pi*f/fs), complex
Horner on the ascending coefficient lists, dB = 20*log10(|B(u)/A(u)|).
A coefficient convention note for implementers: the two substitution
polynomials N(u) = u^2 - c1*u + c2 (constant c2) and
D(u) = c2*u^2 - c1*u + 1 (constant 1) must keep those roles. Swapping
them produces a filter with an IDENTICAL magnitude response on the unit
circle (the reciprocal polynomial pair agrees there) but with every pole
mirrored to the reciprocal location, z-plane poles outside the unit
circle, and a divergent direct-form recursion. The denominator's
constant term stays 1 so the composed u-plane poles land strictly
outside the unit circle and the filter is stable.

Defining relations (pin these exactly; every function below derives
from them):
- Prototype lowpass: digital Butterworth of order n with its 3 dB point
  at prototype_cutoff_hz, built by the bilinear map of the prewarped
  analog poles (the sibling's own algebra): prewarped analog cutoff
  Omega_a = 2*fs*tan(pi*prototype_cutoff_hz/fs), normalized left-half-
  plane unit-circle poles s_k = Omega_a*exp(j*pi*(2k+n-1)/(2n)),
  k = 1..n, bilinear pole map z_k = (2*fs + s_k)/(2*fs - s_k),
  denominator A(u) = prod_k (1 - z_k*u), numerator
  B(u) = K*(1+u)^n with K = sum(a)/2^n for unity DC gain. At the default
  prototype cutoff fs/4 the prewarp is exactly Omega_a = 2*fs (tan of
  pi/4 is 1) and the order-2 prototype takes the closed form
  B(u) = 0.292893218813*(1+u)^2, A(u) = 1 + 0.171572875254*u^2 with
  z-plane poles at +-j*0.414213562 (u-plane poles at +-j*2.414213562).
  The prototype's magnitude identity is |H(e^jw)|^2 = 1/(1 +
  (tan(w/2)/tan(wc/2))^(2n)), the closed form the edge-gain checks use.
- Digital frequency transformation parameters, band edges wl < wu and
  prototype cutoff wc all in (0, pi):
  alpha = cos((wl + wu)/2)/cos((wu - wl)/2), the shared substitution
  parameter that places the transformed filter's center frequency (image
  of the prototype DC, where the bandpass peaks and the bandstop nulls)
  at w0 = arccos(alpha), i.e. center_frequency_hz =
  fs*arccos(alpha)/(2*pi).
  LP-to-BP: kappa = cot((wu - wl)/2)*tan(wc/2), c1 = 2*alpha*kappa/
  (kappa + 1), c2 = (kappa - 1)/(kappa + 1), substitution
  u' = -(u^2 - c1*u + c2)/(c2*u^2 - c1*u + 1).
  LP-to-BS: kappa = tan((wu - wl)/2)*tan(wc/2), c1 = 2*alpha/(kappa + 1),
  c2 = (1 - kappa)/(1 + kappa), substitution
  u' = +(u^2 - c1*u + c2)/(c2*u^2 - c1*u + 1).
  Each substitution maps the unit circle onto itself (|u'| = 1 for
  |u| = 1), so |H_new(e^jW)| = |H_lp(e^jw'(W))| with the prototype cutoff
  wc reached at both target band edges: the -3.0103 dB points of the
  transformed filter sit at exactly wl and wu. At the canonical
  prototype cutoff wc = pi/2 (fs/4), tan(wc/2) = 1, the two kappa values
  are reciprocals, and the two substitutions coincide: c1 and c2 are
  identical for the bandpass and the bandstop (real anchor, equal to
  1e-12), which is why the bandstop at the same edges shares the
  bandpass denominator whenever the prototype has no odd-power terms
  (every even order, including order 2).
- Composition: with prototype coefficient lists b_k and a_k and the
  substitution u' = s*N(u)/D(u), s = +-1, multiply through by D(u)^n:
  numerator = sum_k b_k*s^k*N(u)^k*D(u)^(n-k),
  denominator = sum_k a_k*s^k*N(u)^k*D(u)^(n-k),
  both degree 2n in u. For the binomial prototype numerator
  B(u) = K*(1+u)^n the bandpass numerator collapses to K*(D - N)^n with
  D - N = (1 - c2)*(1 - u^2): n-fold exact zeros at u = +-1, so the
  bandpass nulls DC and Nyquist exactly; the bandstop numerator
  collapses to K*(N + D)^n with N + D = (1 + c2)*u^2 - 2*c1*u + (1 + c2):
  n-fold zeros on the unit circle at the notch center frequency, so the
  bandstop nulls its center exactly while passing DC and Nyquist with
  gain 1 (the substitution evaluates to the prototype DC at u = +-1).
- Normalization: divide numerator and denominator by the denominator
  constant term so a[0] = 1, then for the bandpass scale the numerator
  so the gain at the center frequency w0 = arccos(alpha) is exactly 1
  (the peak, image of the prototype DC where the prototype gain is 1;
  the scale is 1 to float noise), and for the bandstop scale the
  numerator so the DC gain at u = 1 is exactly 1.
- Stability: the prototype u-plane poles p_k (roots of A_lp, |p_k| > 1)
  map to the transformed u-plane poles, the roots of
  s*(u^2 - c1*u + c2) - p_k*(c2*u^2 - c1*u + 1) = 0, two per prototype
  pole from the quadratic formula (cmath). All 2n roots lie strictly
  outside the unit circle (equivalently all z-plane poles z = 1/u
  strictly inside), the closed-form stability evidence the checks use.

Functions (public API, 7):
- bandpass_design(fs, low_cutoff_hz, high_cutoff_hz, order,
  prototype_cutoff_hz=None) -> (b, a) lists of floats, len 2*order + 1,
  a[0] == 1, unity peak gain. order is the PROTOTYPE order; the filter
  has 2*order poles. prototype_cutoff_hz defaults to fs/4.
  ValueError set: fs <= 0; low_cutoff_hz <= 0; low_cutoff_hz >=
  high_cutoff_hz; high_cutoff_hz >= fs/2; order outside 1..8;
  prototype_cutoff_hz outside (0, fs/2).
- bandstop_design(fs, low_cutoff_hz, high_cutoff_hz, order,
  prototype_cutoff_hz=None) -> (b, a), same contract, unity DC gain.
  Same ValueError set.
- band_transform_parameters(low_cutoff_hz, high_cutoff_hz,
  prototype_cutoff_hz, fs) -> (alpha, kappa_bp, kappa_bs), the closed
  forms above. Same ValueError set.
- center_frequency_hz(low_cutoff_hz, high_cutoff_hz, fs) -> float, the
  bandpass peak and bandstop notch center at the canonical fs/4
  prototype, fs*arccos(alpha)/(2*pi) with alpha from
  band_transform_parameters. Same ValueError set.
- frequency_response_db(b, a, freq_hz, fs) -> float, the magnitude
  response in dB at any probe frequency in (0, fs/2]. ValueError if
  fs <= 0 or the probe lies outside (0, fs/2] (the exact unit-circle
  points are allowed: the bandstop unity Nyquist gain and the bandpass
  exact null floor are probed at fs/2 itself).
- apply_filter(b, a, samples) -> list of floats, the direct-form
  difference equation y[n] = (sum_k b[k]*x[n-k] - sum_{k>=1}
  a[k]*y[n-k])/a[0] with zero initial conditions, output length equals
  input length. ValueError if b and a are empty or unequal length, the
  sample list is empty, or any sample is non-finite.
- band_edge_checks(b, a, fs, low_cutoff_hz, high_cutoff_hz, ftype) ->
  dict {low_edge_db, high_edge_db, target_db, low_edge_ok, high_edge_ok,
  passband_ok, extra, verdict}: both edge gains within 0.02 dB of
  -3.010299956639812 dB; for ftype "bandpass" the center gain within
  0.02 dB of 0 dB (extra holds it); for ftype "bandstop" the near-DC and
  near-Nyquist gains within 0.02 dB of 0 dB (extra holds the pair);
  verdict "PASS" only if all hold. ValueError for unknown ftype.
Private helpers (module-internal, documented for the contract test):
_poly_mul (plain accumulated product), _poly_pow, _lowpass_prototype
(order, prototype_cutoff_hz, fs) -> (b, a) as above, _compose(b, a, c1,
c2, sign) -> (num, den) as above, _response_mag(b, a, w) complex Horner
magnitude, _uplane_poles(fs, low_cutoff_hz, high_cutoff_hz, order,
ftype) -> list of the 2n u-plane pole magnitudes from the quadratic
preimages above. ValueErrors on nonphysical inputs are part of the
contract; the edge checks and stability asserts are tolerance-based
(isclose/delta style), never exact float equality on computed sums.

Identities to test (tolerance-based asserts only, real anchor values
cited below):
- Prototype: the order-2 prototype at 250 Hz on fs = 1000 gives
  b = [0.292893218813, 0.585786437627, 0.292893218813],
  a = [1.0, 0.0, 0.171572875254] (the u-plane poles at +-j*2.414213562
  exactly, nilpotent-free closed form), the 250 Hz gain is
  -3.010299957 dB and the 1 Hz gain 0.000000000 dB, and the closed-form
  magnitude identity holds at 250 Hz: 1/(1 + tan^4(pi/4)) = 1/2.
- Band edges: for the canonical design below, both band-edge gains are
  -3.010299957 dB for the bandpass AND the bandstop, equal to
  20*log10(1/sqrt(2)) = -3.010299956640 dB within 1e-9 dB.
- Center: center_frequency_hz = 221.911501 Hz equals
  fs*arccos(alpha)/(2*pi) with alpha = 0.175570504585 within 1e-9.
- Shared denominator: a_bs equals a_bp to within 1e-12 at the canonical
  prototype (even prototype order, zero linear coefficient); the
  bandstop numerator differs (zeros on the unit circle at the notch
  center instead of at DC and Nyquist).
- Stability: all four u-plane poles of both filters lie outside the
  unit circle (magnitudes 1.354030645 and 1.415518434, pairs each), so
  the z-plane poles (0.738535722 and 0.706454947, pairs) lie inside;
  the reciprocal-convention filter (substitution lists swapped) has the
  same |H(e^jw)| but z-plane poles at 1.354030645 and 1.415518434,
  outside the unit circle: the contract test MUST reject it by the
  preimage pole test or by an unbounded constant-input recursion.
- Signal identity: for the 2000-sample three-tone record below, the
  measured per-tone gain of apply_filter output equals the designed
  magnitude response |H| at that tone to a relative difference below
  1e-12 (real anchors 0.000e+00 to 1.587e-13).
- Exact structure: bandpass numerator coefficient pattern
  [s, 0, -2s, 0, s] (order 2, zeros at DC and Nyquist, interior
  coefficients below 1e-12 in magnitude); bandstop numerator symmetric
  [t, -m, u, -m, t] with zeros on the unit circle.
- Determinism: two identical design calls bitwise identical; no imports
  beyond math and cmath; no RNG.

## Worked example

Parameters: fs = 1000 Hz, band edges low = 150 Hz (wl = 0.3*pi =
0.942477796077 rad), high = 300 Hz (wu = 0.6*pi = 1.884955592154 rad),
prototype order n = 2 with the canonical prototype cutoff fs/4 = 250 Hz
(wc = pi/2). All values below are REAL outputs of the prep anchor
/tmp/w44spec/anchor_band.py (stdlib math and cmath only, exit 0, all
checks passed):

- Prototype (order 2, 250 Hz): prewarp 2*fs*tan(pi/4) = 2*fs =
  2000.000000000000 (the module value 1999.9999999999998, one ULP of
  tan(pi/4) in float); b = [0.29289321881345, 0.5857864376269,
  0.29289321881345], a = [1.0, -0.0, 0.17157287525381]; z-plane poles at
  +-j*0.414213562 (u-plane poles at +-j*2.414213562); the prototype 3 dB
  point at 250 Hz measured -3.010299957 dB, unity DC gain 0.000000000 dB.
- Substitution parameters: alpha = 0.175570504585 = cos(0.45*pi)/
  cos(0.15*pi); kappa_bp = 1.962610505505 = cot(0.15*pi)*tan(pi/4);
  kappa_bs = 0.509525449494 = tan(0.15*pi)*tan(pi/4), the exact
  reciprocal of kappa_bp; c1 = 2*alpha*kappa/(kappa+1) =
  0.232616819602 for the bandpass and 2*alpha/(kappa_bs+1) =
  0.232616819602 for the bandstop; c2 = 0.324919696233 both directions.
  The two substitutions coincide at the fs/4 prototype (structural
  anchor: equal to 1e-12 both coefficients).
- Bandpass (order-2 prototype -> 4-pole filter): b_bp =
  [0.131106439917, 0.0, -0.262212879833, 0.0, 0.131106439917] (the
  (1-u^2)^2 pattern: exact nulls at DC and Nyquist), a_bp = [1.0,
  -0.482430732520, 0.810055809342, -0.226875551364, 0.272214937925];
  lower edge 150 Hz gain -3.010299957 dB, upper edge 300 Hz gain
  -3.010299957 dB (target -3.010299956640 dB, deviation below 1e-9 dB);
  center (peak) frequency 221.911501 Hz = fs*arccos(alpha)/(2*pi) with
  gain 0.000000000 dB; the 1 Hz probe reads -96.432009245 dB and the
  500 Hz (Nyquist) probe reads -665.052919111 dB, the float floor of the
  exact null at u = -1. band_edge_checks verdict PASS.
- Bandstop (same edges, same prototype order): b_bs = [0.505001029046,
  -0.354653141942, 1.072268689175, -0.354653141942, 0.505001029046],
  a_bs = a_bp (shared denominator to 1e-12, the even-order zero-linear
  prototype); stopband edges 150 Hz and 300 Hz both -3.010299957 dB;
  DC and Nyquist gains 0.000000000 dB; the notch center null at
  221.911501 Hz measures -317.064274 dB, the float floor of the exact
  on-circle zero pair. band_edge_checks verdict PASS.
- Prototype-cutoff invariance (design family): with the edges fixed at
  150/300 Hz, prototype cutoffs of 200 Hz and 125 Hz give band-edge
  gains of -3.010300 / -3.010300 dB for both the bandpass and the
  bandstop, while the coefficient vectors differ from the canonical
  design (the family probe: the -3.0103 dB edge property holds across
  the choice, the fs/4 member is the canonical bilinear image of the
  unit-cutoff analog prototype).
- Stability: prototype u-plane poles +-j*2.414213562 map to four
  u-plane poles outside the unit circle (magnitudes 1.354030645 pair
  and 1.415518434 pair), z-plane poles at 0.738535722 pair and
  0.706454947 pair, all strictly inside, identical for the bandpass and
  the bandstop.
- Deterministic signal test: x[n] = sum of three unit-amplitude sines
  at 50, 220 and 470 Hz with phases 0.3, 1.1 and 2.2 rad, n = 0..1999,
  through apply_filter; per-tone gains measured by quadrature projection
  over the settled tail samples 1000..1999 (1 s window, integer cycles
  for every integer-Hz tone, no leakage). Bandpass: 50 Hz measured
  0.041188867 vs |H| 0.041188867 (relative difference 1.196e-14,
  -27.704403 dB); 220 Hz measured 0.999999845 vs |H| 0.999999845
  (relative difference 0.000e+00, -0.000001 dB); 470 Hz measured
  0.006799295 vs |H| 0.006799295 (relative difference 1.587e-13,
  -43.350723 dB). Bandstop: 50 Hz measured 0.999151379 vs |H|
  0.999151379 (relative difference 5.778e-15, -0.007374 dB); 220 Hz
  measured 0.000556866 vs |H| 0.000556866 (relative difference
  7.718e-12, -65.084990 dB, the in-notch rejection); 470 Hz measured
  0.999976885 vs |H| 0.999976885 (relative difference 2.220e-15,
  -0.000201 dB). The measured gains reproduce the designed magnitude
  response to float precision, validating the difference equation
  against the response probes.
- Structural signal checks: a constant input through the bandpass
  settles to a tail RMS of 8.667e-17 (exact DC null) and an alternating
  (+1/-1) input to 0.000e+00 (exact Nyquist null); the same inputs
  through the bandstop settle to tail mean 1.000000000000 (unity DC
  gain) and tail RMS 1.000000000000 (unity Nyquist gain).
- Determinism and sanity: two identical bandpass design calls are
  bitwise identical; an order-1 bandpass (2 poles, len 3) also lands
  both edges at -3.010299957 dB.
- ValueError set probed and confirmed: fs negative; low_cutoff_hz = 0;
  low >= high; high at fs/2; order 0 and 9; prototype_cutoff_hz at
  -5.0 and 600.0; probe frequencies 0.0 and 600.0 Hz; empty and
  non-finite sample lists; ftype "notch".
Run your module and take the real outputs as assert targets
(tolerance-based); the anchors above are real prep outputs of
/tmp/w44spec/anchor_band.py (stdlib math and cmath, exit 0, all checks
passed).

## Validation list (contract test must include)

- bandpass_design(1000.0, 150.0, 300.0, 2) returns len-5 b and a with
  a[0] == 1; b matches [0.131106439917, 0.0, -0.262212879833, 0.0,
  0.131106439917] within 1e-9 absolute (interior coefficients below
  1e-12) and a matches [1.0, -0.482430732520, 0.810055809342,
  -0.226875551364, 0.272214937925] within 1e-9; bandstop_design on the
  same arguments returns b within 1e-9 of [0.505001029046,
  -0.354653141942, 1.072268689175, -0.354653141942, 0.505001029046] and
  a within 1e-12 of the bandpass a.
- Both edge gains equal -3.010299956640 dB within 1e-6 dB (anchor
  -3.010299957 dB for bandpass and bandstop), and the bandpass center
  gain at center_frequency_hz = 221.911501 Hz is 0.000000000 dB within
  1e-6 dB.
- center_frequency_hz(150.0, 300.0, 1000.0) = 221.911501 within 1e-6 and
  equals fs*arccos(alpha)/(2*pi) with alpha = 0.175570504585 within
  1e-6.
- band_transform_parameters(150.0, 300.0, 250.0, 1000.0) returns alpha
  0.175570504585, kappa_bp 1.962610505505, kappa_bs 0.509525449494,
  each within 1e-9; kappa_bp*kappa_bs = 1 within 1e-9; the bandpass and
  bandstop c1 and c2 agree within 1e-12.
- Bandstop DC and Nyquist unity: gains at 1e-9 Hz and fs/2 - 1e-9 Hz
  within 0.001 dB of 0 (anchor 0.000000000 dB); the notch center null at
  221.911501 Hz measured below -200 dB (anchor -317.064274 dB).
- Stability: all four u-plane pole magnitudes from the quadratic
  preimages exceed 1 + 1e-9 (anchor magnitudes 1.354030645 and
  1.415518434, pairs), equivalently the z-plane pole magnitudes
  0.738535722 and 0.706454947 all lie below 1 - 1e-9; the
  reciprocal-convention denominator (N and D coefficient lists swapped,
  which has the identical |H(e^jw)|) MUST fail this test, with z-plane
  poles at 1.354030645 and 1.415518434.
- Signal test: the 2000-sample three-tone record (50, 220, 470 Hz,
  phases 0.3, 1.1, 2.2 rad) through apply_filter reproduces the designed
  |H| at each tone within 1e-9 relative on the tail projection (anchors
  0.000e+00 to 1.587e-13), with the 220 Hz bandpass gain above -1 dB,
  the 50 Hz and 470 Hz bandpass gains below -15 dB, the 220 Hz bandstop
  gain below -40 dB (anchor -65.084990 dB), and the 50 Hz and 470 Hz
  bandstop gains above -0.1 dB.
- Constant and alternating inputs: bandpass tail RMS below 1e-9 for both
  (anchors 8.667e-17 and 0.000e+00); bandstop tail mean and RMS equal
  1.0 within 1e-9 (anchors 1.000000000000).
- Prototype invariance probe: with prototype_cutoff_hz = 200.0 and
  125.0 the band-edge gains stay within 1e-6 dB of -3.010299957 dB for
  bandpass and bandstop while the coefficient vectors differ from the
  canonical fs/4 design.
- Order-1 sanity: bandpass_design(1000.0, 150.0, 300.0, 1) returns
  len-3 vectors with both edge gains at -3.010299957 dB.
- Determinism: repeated design calls bitwise identical; no imports
  beyond math and cmath; no RNG.
- ValueErrors: bandpass_design and bandstop_design on fs = -1000,
  low_cutoff_hz = 0, low == high, high == fs/2, order 0 and 9, and
  prototype_cutoff_hz = -5.0 and 600.0; frequency_response_db at 0.0 and
  600.0 Hz on fs = 1000; apply_filter on an empty list and on a list
  containing nan; band_edge_checks on ftype "notch".
- Run the contract test under both python3 (3.9.x) and the pyenv 3.13
  hook interpreter; all asserts above are tolerance-based and must hold
  on both.

## Corpus fragment (eval/hit1-wave44-bandpass-bandstop-filter-design.yaml)

Query 1 (copy verbatim):
  "apply the bandpass-filter-design to a sampled channel by the
  digital-frequency-transformation: given the lower and upper band edge
  frequencies, the sample rate and the prototype order, compute the
  butterworth-bandpass coefficients from a digital Butterworth prototype
  and verify that both band edges sit at minus 3.0103 dB on the
  magnitude response"
  intent: "cross-cutting; Butterworth IIR bandpass design by the z-domain
  digital frequency transformation with both band edges verified at
  -3.0103 dB on the magnitude response"
  expected_skill: "cross-cutting/numerics/bandpass-bandstop-filter-design"
Query 2 (copy verbatim):
  "run the bandstop-filter-design to notch out a narrow band: compute
  the bandstop coefficients by the z-domain LP-to-BS
  digital-frequency-transformation, check the stopband edge gains at
  minus 3.0103 dB and the notch center null, and filter a deterministic
  test signal containing a tone inside the notch"
  intent: "cross-cutting; Butterworth IIR bandstop design by the z-domain
  LP-to-BS digital frequency transformation with stopband edge checks,
  notch center null and filtered test signal"
  expected_skill: "cross-cutting/numerics/bandpass-bandstop-filter-design"
Task ids: w44-bandpass-bandstop-filter-design-1 and -2. Prep grep:
bandpass, bandstop, band-pass, band-stop, bandpass-filter-design,
bandstop-filter-design, butterworth-bandpass and
digital-frequency-transformation appear in NO existing eval/hit1-corpus
task (each grep count 0) and in no skill file except the flutter LCO
application phrase "data band-passed at the mode frequency"
(skills/flight-test-operations/flutter/limit-cycle-oscillation/SKILL.md
line 75, a consumed-input step of the LCO workflow, not a design owner);
the w28-digital-filter-design tasks route on prewarping a single cutoff,
the LP/HP coefficient vectors and the 3 dB point at that one cutoff
("check the 3 dB point at the cutoff", "magnitude response near
Nyquist"), w31-fir-filter-design routes on the windowed-sinc taps,
hamming window and group delay of a linear-phase FIR, and the ftype
fence of digital-filter-design raises ValueError for "bandpass", so the
queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design a digital Butterworth
IIR bandpass or bandstop filter from its two band-edge frequencies,
sample rate, and order by the z-domain LP-to-BP / LP-to-BS digital
frequency transformation:" (wave-44 leaf plan direction: MED, lead with
bandpass/bandstop/digital-frequency-transformation tokens) and include
the outputs in the Claim order. First tag: bandpass-filter-design.
Additional tags ONLY: bandstop-filter-design, butterworth-bandpass,
butterworth-bandstop, digital-frequency-transformation, band-edge-gain.
NEVER single generic words (filter, band, frequency, design, dB alone)
and NEVER the sibling-owned routing tokens: iir-lowpass, highpass-filter,
cutoff-frequency, prewarping, filter-coefficients, windowed-sinc,
finite-impulse-response, filter-taps (digital-filter-design and
fir-filter-design own those; a bandpass request must never route on the
bare phrase "digital filter design" or a single-cutoff "3 dB point"
either). 50-150 words, <=1000 chars, no em dash, no content-policy sweep
term, action verb present. Recommended wording (outputs in Claim order):
"Use when you must design a digital Butterworth IIR bandpass or bandstop
filter from its two band-edge frequencies, sample rate, and order by the
z-domain LP-to-BP / LP-to-BS digital frequency transformation: map a
digital Butterworth prototype into the band with the closed-form
substitution algebra so that both band edges land at exactly -3.0103 dB
on the magnitude response, and apply the filter to a sampled signal.
Produces the bandpass or bandstop coefficient vectors, the substitution
parameters, the center frequency, band-edge gain checks, the filtered
output of a deterministic test signal, and the stability evidence, with
all coefficients computed and none looked up. Trigger: bandpass filter
design, bandstop filter design, Butterworth bandpass, Butterworth
bandstop, digital frequency transformation, band edge frequencies,
notch filter, band-limited channel." The sibling phrases "IIR lowpass",
"highpass filter" and "cutoff frequency" must not appear as trigger
keywords.

FORBIDDEN TOKENS (belong to siblings): lowpass coefficient design,
highpass coefficient design, unity DC gain normalization, unity Nyquist
gain normalization, prewarping, the tag cutoff-frequency, the tag
filter-coefficients (digital-filter-design, whose contract test raises
ValueError for the ftype "bandpass"); windowed-sinc, hamming window,
ideal lowpass impulse response, group delay, linear-phase taps, FIR
lowpass (fir-filter-design); welch periodogram, measured time history
(power-spectral-density); fft bins, spectral content of a signal
(fast-fourier-transform); flutter mode damping, band-passed flight test
data reduction (limit-cycle-oscillation); differentiation of the
filtered signal (finite-difference-derivatives); filter tuning
heuristics or choosing band edges from a measured spectrum (no owner,
out of scope).
