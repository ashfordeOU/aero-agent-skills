---
name: bandpass-bandstop-filter-design
description: "Use when you must design a digital Butterworth IIR bandpass or bandstop filter from its two band-edge frequencies, sample rate, and order by the z-domain LP-to-BP / LP-to-BS digital frequency transformation: map a digital Butterworth prototype into the band so both edges land at exactly -3.0103 dB on the magnitude response, then filter a sampled signal. Produces the bandpass or bandstop coefficient vectors, substitution parameters, center frequency, band-edge gain checks, filtered output, and stability evidence; all coefficients computed, none looked up. Trigger: bandpass filter design, bandstop filter design, Butterworth bandpass, Butterworth bandstop, digital frequency transformation, band edge frequencies, notch filter, band-limited channel."
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
  tags: [bandpass-filter-design, bandstop-filter-design, butterworth-bandpass, butterworth-bandstop, digital-frequency-transformation, band-edge-gain]
  version: 0.1.0
  author: AeroSkills
---

# Butterworth IIR Bandpass and Bandstop Filter Design (cross-cutting/numerics/bandpass-bandstop-filter-design)

Use when you must design a digital Butterworth IIR filter that passes or
rejects a band of frequencies between two specified band edges: a
bandpass or bandstop coefficient pair (b, a) computed from the lower and
upper band edge frequencies, the sample rate, and the prototype order by
the z-domain LP-to-BP / LP-to-BS digital frequency transformation
(Oppenheim and Schafer / Proakis class substitution algebra), with both
band edges verifiable at exactly -3.0103 dB on the magnitude response,
the same prewarp-grade guarantee the lowpass/highpass sibling
digital-filter-design delivers at a single cutoff. Every coefficient is
computed from the closed-form substitution, none looked up. It pairs
with cross-cutting/numerics/digital-filter-design, which owns the
lowpass and highpass members of the family with a hard ftype fence, and
with cross-cutting/numerics/fir-filter-design, which designs FIR
lowpass filters only. This leaf is pure Python stdlib (math and cmath),
deterministic and offline.

## Domain quick reference

- Digital frequencies of the band edges and the prototype 3 dB point:
  wl = 2*pi*low_cutoff_hz/fs, wu = 2*pi*high_cutoff_hz/fs and
  wc = 2*pi*prototype_cutoff_hz/fs, with 0 < wl < wu < pi.
- Shared substitution parameter alpha = cos((wl + wu)/2) /
  cos((wu - wl)/2); it places the transformed center frequency (image
  of the prototype DC, where the bandpass peaks and the bandstop nulls)
  at w0 = arccos(alpha), so center_frequency_hz = fs*arccos(alpha)/
  (2*pi).
- LP-to-BP: kappa = cot((wu - wl)/2)*tan(wc/2), c1 = 2*alpha*kappa/
  (kappa + 1), c2 = (kappa - 1)/(kappa + 1), substitution sign s = -1.
- LP-to-BS: kappa = tan((wu - wl)/2)*tan(wc/2), c1 = 2*alpha/(kappa +
  1), c2 = (1 - kappa)/(1 + kappa), substitution sign s = +1.
- The substitution u' = s*(u^2 - c1*u + c2)/(c2*u^2 - c1*u + 1) maps
  the unit circle onto itself. The roles of N(u) = u^2 - c1*u + c2
  (constant c2) and D(u) = c2*u^2 - c1*u + 1 (constant 1) must be kept:
  swapping them gives an identical magnitude response on the unit circle
  but mirrors every pole to the reciprocal location, outside the unit
  circle, with a divergent direct-form recursion.
- Composition into the prototype coefficient lists: numerator =
  sum_k b[k]*s^k*N^k*D^(n-k) and denominator = sum_k
  a[k]*s^k*N^k*D^(n-k), both degree 2n in u, then normalized so a[0] =
  1. The binomial prototype numerator collapses to K*(D - N)^n for the
  bandpass (n-fold exact zeros at u = +-1: nulls at DC and Nyquist) and
  K*(N + D)^n for the bandstop (n-fold zeros on the unit circle at the
  notch center; DC and Nyquist pass with gain 1).
- Prototype lowpass: digital Butterworth of order n with its 3 dB point
  at prototype_cutoff_hz (default fs/4), built by the bilinear map of
  the prewarped analog poles: Omega_a = 2*fs*tan(pi*fc/fs), poles
  s_k = Omega_a*exp(j*pi*(2k + n - 1)/(2n)), z_k = (2*fs + s_k)/(2*fs -
  s_k), denominator A(u) = prod_k (1 - z_k*u), numerator K*(1 + u)^n
  with K = sum(a)/2^n for unity DC gain. At the fs/4 default the order-2
  prototype takes the closed form b = [0.292893218813, 0.585786437627,
  0.292893218813], a = [1.0, 0.0, 0.171572875254], and its magnitude
  identity is |H(e^jw)|^2 = 1/(1 + (tan(w/2)/tan(wc/2))^(2n)).
- The transformed order-2n filter has both band edges at exactly
  -3.010299957 dB, the -3 dB point of the prototype reached at wl and
  wu; the edge checks also probe the bandpass center gain (0 dB peak)
  or the bandstop near-DC / near-Nyquist gains (0 dB passband).

## Workflow

1. Fix the design inputs: sample rate fs, lower band edge
   low_cutoff_hz, upper band edge high_cutoff_hz, the prototype order
   (the filter then has 2*order poles), and the prototype cutoff
   prototype_cutoff_hz (defaults to fs/4). Band edges must satisfy
   0 < low < high < fs/2 and the order lie in 1..8.
2. Compute the substitution parameters with
   band_transform_parameters(low_cutoff_hz, high_cutoff_hz,
   prototype_cutoff_hz, fs), which returns (alpha, kappa_bp, kappa_bs),
   and the center frequency with center_frequency_hz(low_cutoff_hz,
   high_cutoff_hz, fs): the bandpass peak and bandstop notch center,
   fs*arccos(alpha)/(2*pi).
3. Build the digital Butterworth lowpass prototype: the module
   constructs it internally from the bilinear map of the prewarped
   analog poles (helper _lowpass_prototype, documented for the contract
   test); its 3 dB point sits at prototype_cutoff_hz and its closed-form
   magnitude identity holds there.
4. Run the band design: bandpass_design(fs, low_cutoff_hz,
   high_cutoff_hz, order, prototype_cutoff_hz=None) or
   bandstop_design(...) with the same signature. Each returns (b, a),
   lists of floats of length 2*order + 1 with a[0] == 1: the bandpass
   has unity peak gain at the center frequency, the bandstop unity DC
   gain, and the composition, normalization and numerator scaling are
   internal to the module.
5. Verify the design: band_edge_checks(b, a, fs, low_cutoff_hz,
   high_cutoff_hz, ftype) returns the dict {low_edge_db, high_edge_db,
   target_db, low_edge_ok, high_edge_ok, passband_ok, extra, verdict}
   with both edge gains within 0.02 dB of -3.010299956639812 dB and the
   verdict 'PASS' only if all checks hold; the stability evidence comes
   from the u-plane pole preimages (helper _uplane_poles): all 2*order
   u-plane poles lie strictly outside the unit circle, equivalently all
   z-plane poles strictly inside.
6. Probe the magnitude response anywhere with frequency_response_db(b,
   a, freq_hz, fs), 20*log10(|H|) in dB on the unit circle; probes in
   (0, fs/2] are valid, including the exact null floors at the bandstop
   notch center and the bandpass Nyquist point.
7. Filter a sampled signal with apply_filter(b, a, samples): the
   direct-form difference equation y[n] = (sum_k b[k]*x[n-k] -
   sum_{k>=1} a[k]*y[n-k])/a[0] with zero initial conditions, output
   length equal to the input length. The deterministic checks are in
   the contract test scripts/test_bandpass_bandstop_filter_design.py.

## Worked example

fs = 1000 Hz, band edges low = 150 Hz (wl = 0.3*pi) and high = 300 Hz
(wu = 0.6*pi), prototype order n = 2 with the canonical prototype
cutoff fs/4 = 250 Hz (wc = pi/2). All values below are REAL outputs of
scripts/bandpass_bandstop_filter_design.py.

- Prototype (order 2, 250 Hz): b = [0.292893218813, 0.585786437627,
  0.292893218813], a = [1.0, 0.0, 0.171572875254]; the 250 Hz gain is
  -3.010299957 dB and the 1 Hz gain 0.000000000 dB; the magnitude
  identity |H|^2 = 1/(1 + tan^4(pi/4)) = 1/2 holds at the cutoff.
- Substitution parameters: alpha = 0.175570504585 = cos(0.45*pi)/
  cos(0.15*pi); kappa_bp = 1.962610505505 = cot(0.15*pi)*tan(pi/4);
  kappa_bs = 0.509525449494, the exact reciprocal; c1 =
  0.232616819602 and c2 = 0.324919696233 identically for the bandpass
  and the bandstop (the two substitutions coincide at the fs/4
  prototype). Center frequency 221.911501 Hz = fs*arccos(alpha)/(2*pi).
- Bandpass (4-pole filter): b = [0.131106439917, 0.0, -0.262212879833,
  0.0, 0.131106439917] (the exact (1-u^2)^2 pattern: nulls at DC and
  Nyquist, interior coefficients below 1e-12), a = [1.0,
  -0.482430732520, 0.810055809342, -0.226875551364, 0.272214937925].
  Edge gains -3.010299957 dB at 150 Hz and 300 Hz (target
  -3.010299956640 dB), center gain 0.000000000 dB at 221.911501 Hz; the
  1 Hz probe reads -96.432009245 dB and the 500 Hz Nyquist probe reads
  -665.052919111 dB, the float floor of the exact null at u = -1.
  band_edge_checks verdict PASS.
- Bandstop (same edges, same prototype order): b = [0.505001029046,
  -0.354653141942, 1.072268689175, -0.354653141942, 0.505001029046], a
  identical to the bandpass denominator (shared to 1e-12). Stopband
  edges both -3.010299957 dB; DC and Nyquist gains 0.000000000 dB; the
  notch center null at 221.911501 Hz measures -317.064274 dB, the float
  floor of the exact on-circle zero pair. band_edge_checks verdict PASS.
- Prototype-cutoff invariance: with the edges fixed at 150/300 Hz,
  prototype cutoffs of 200 Hz and 125 Hz give band-edge gains of
  -3.010300 dB for both the bandpass and the bandstop while the
  coefficient vectors differ from the canonical design.
- Stability: the prototype u-plane poles at +-j*2.414213562 map to four
  u-plane poles outside the unit circle (magnitudes 1.354030645 pair
  and 1.415518434 pair), z-plane poles at 0.738535722 pair and
  0.706454947 pair, identical for the bandpass and the bandstop.
- Deterministic signal test: x[n] = sum of unit-amplitude sines at 50,
  220 and 470 Hz with phases 0.3, 1.1 and 2.2 rad, n = 0..1999, through
  apply_filter; per-tone gains measured by quadrature projection over
  the settled tail samples 1000..1999 reproduce the designed magnitude
  response to float precision (relative difference below 1.6e-13).
  Bandpass: 50 Hz -27.704403 dB, 220 Hz -0.000001 dB, 470 Hz
  -43.350723 dB. Bandstop: 50 Hz -0.007374 dB, 220 Hz -65.084990 dB
  (the in-notch rejection), 470 Hz -0.000201 dB.
- Structural signal checks: a constant input through the bandpass
  settles to a tail RMS of 8e-17 (exact DC null) and an alternating
  (+1/-1) input to below 1e-130 (exact Nyquist null); the same inputs
  through the bandstop settle to tail mean and RMS 1.000000000000
  (unity DC and Nyquist gain).
- Determinism and sanity: two identical bandpass design calls are
  bitwise identical; an order-1 bandpass (2 poles, len-3 vectors) also
  lands both edges at -3.010299957 dB.

## Verification

- bandpass_design(1000.0, 150.0, 300.0, 2) returns the len-5 b and a
  above with a[0] == 1, and bandstop_design on the same arguments
  returns the bandstop b above with a shared denominator.
- Both edge gains equal -3.010299956640 dB within 1e-6 dB for the
  bandpass and the bandstop, and the bandpass center gain at 221.911501
  Hz is 0 dB within 1e-6 dB.
- center_frequency_hz(150.0, 300.0, 1000.0) equals 221.911501 Hz and
  equals fs*arccos(alpha)/(2*pi) with alpha = 0.175570504585, each
  within 1e-6.
- band_transform_parameters(150.0, 300.0, 250.0, 1000.0) returns alpha
  0.175570504585, kappa_bp 1.962610505505 and kappa_bs 0.509525449494
  within 1e-9, with kappa_bp*kappa_bs = 1 within 1e-9.
- The bandstop DC and Nyquist gains stay within 0.001 dB of 0 at 1e-9
  Hz and fs/2 - 1e-9 Hz, and the notch center null reads below -200 dB.
- Stability: all four u-plane pole magnitudes exceed 1 + 1e-9 (anchors
  1.354030645 and 1.415518434, pairs); the reciprocal-convention filter
  (substitution lists swapped, identical |H(e^jw)|) fails the check and
  its constant-input recursion diverges.
- The 2000-sample three-tone record reproduces the designed |H| at each
  tone within 1e-9 relative: the bandpass passes 220 Hz above -1 dB and
  rejects 50 Hz and 470 Hz below -15 dB; the bandstop rejects 220 Hz
  below -40 dB and passes 50 Hz and 470 Hz above -0.1 dB.
- Constant and alternating inputs settle through the bandpass to a tail
  RMS below 1e-9 and through the bandstop to tail mean and RMS 1.0
  within 1e-9.
- Non-physical inputs raise ValueError: fs <= 0, low_cutoff_hz <= 0,
  low >= high, high >= fs/2, order outside 1..8, prototype_cutoff_hz
  outside (0, fs/2), probes outside (0, fs/2], empty or non-finite
  sample lists, unequal coefficient vectors, and unknown ftype values
  such as 'notch'.
- Run the contract test offline under both interpreters, exit 0:
  python3 scripts/test_bandpass_bandstop_filter_design.py and the pyenv
  3.13 hook interpreter.

## Related leaves

- cross-cutting/numerics/digital-filter-design: the immediate sibling;
  designs the digital Butterworth IIR lowpass and highpass members with
  a hard ftype fence (its contract test raises ValueError for
  'bandpass'), single-cutoff prewarp anchors.
- cross-cutting/numerics/fir-filter-design: linear-phase FIR lowpass
  taps; no IIR band filters, no poles, no recursive difference equation.
- cross-cutting/numerics/fast-fourier-transform: frequency content
  analysis of a signal, not band filtering of it.
- cross-cutting/numerics/power-spectral-density: Welch averaged
  periodogram estimation of recorded time data; no filter
  coefficients.
- flight-test-operations/flutter/limit-cycle-oscillation: the flutter
  LCO workflow consumes band-passed test data as an application input;
  it does not design the band filter.

## Pitfalls

- Swapping the substitution lists: N(u) = u^2 - c1*u + c2 and D(u) =
  c2*u^2 - c1*u + 1 keep their roles. Swapping them produces an
  IDENTICAL magnitude response on the unit circle but mirrors every
  pole to the reciprocal location, outside the unit circle, and the
  direct-form recursion diverges (verified by the contract test).
- Reading the order as the final filter order: order is the PROTOTYPE
  order; the transformed filter has 2*order poles and coefficient
  vectors of length 2*order + 1 (order 2 gives a 4-pole filter).
- Probing band-edge gains away from the exact edges: the -3.0103 dB
  guarantee holds at exactly wl and wu; probes elsewhere read the
  transition-band rolloff. The exact unit-circle points are valid
  probes, so null floors (bandpass at Nyquist, bandstop at the notch
  center) read out as very large negative dB values, the float floor of
  the structural zeros, and never raise.
- Assuming the shared denominator: the bandstop shares the bandpass
  denominator only at the canonical fs/4 prototype with an even
  prototype order (zero linear coefficient); with other prototype
  cutoffs the two substitutions differ and the denominators differ,
  while the -3.0103 dB edge property still holds.
- Writing exact float equality on computed sums: the module and its
  contract test use tolerance-based asserts only, since accumulated
  rounding differs between interpreters.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_bandpass_bandstop_filter_design.py

It covers the full workflow: the order-2 prototype closed form, its
3 dB point and magnitude identity, the substitution parameters and
center frequency anchors, the bandpass and bandstop coefficient vectors
and the shared denominator, the -3.0103 dB edge gains of both types,
the band-edge checks verdict, the bandstop DC/Nyquist unity and notch
null, the bandpass stopband null floors, the u-plane pole stability
evidence and the reciprocal-convention rejection, prototype-cutoff
invariance, the order-1 sanity design, bitwise determinism with only
math/cmath imports, the three-tone signal gain identity for both
filters, the structural DC/Nyquist behavior, and the full ValueError
set. 33 tests pass in under a second offline under python3 (3.9.x) and
the pyenv 3.13 hook interpreter.

## Compliance

- Standards referenced, not reproduced: naca-tr-824 (NACA Report 824,
  summary of low-speed airfoil data) is cited reference-only per
  standards-map.yaml as the numerics-convention source for the
  library; the filter design relations above are standard engineering
  methodology (Oppenheim and Schafer / Proakis class digital frequency
  transformation), summary-only.
- compliance: STANDARDS-REF, gated: false.
