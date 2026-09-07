---
name: sears-function-gust-lift
description: "Use when you must compute the frequency-domain gust response of a rigid thin airfoil to a convected sinusoidal vertical gust: evaluate the complex sears-function S(k) from the Bessel series with the Theodorsen lift-deficiency function, the gust gain and the phase lag of the gust load, and the unsteady gust-load amplitude against the quasi-steady 2*pi*rho*V*b*w_g reference, with the |S| = 1 quasi-steady limit at zero reduced frequency, the monotone gain roll-off, and the reduced frequency where the gust load falls to half the quasi-steady value. Produces the complex sears function, gain and phase tables versus reduced frequency, and the unsteady gust-load amplitudes that gate sinusoidal-gust load estimates and unsteady thin-airfoil coursework. Trigger: sears function, sinusoidal gust, gust transfer function, unsteady gust load, gust reduced frequency sweep."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: aerodynamics
pack: aeroelasticity
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: aeroelasticity
  tags: [sears-function, sinusoidal-gust, unsteady-gust-load, gust-transfer-function, reduced-frequency-gust]
  version: 0.1.0
  author: AeroSkills
---

# Sears Function Gust Lift (aerodynamics/aeroelasticity/sears-function-gust-lift)

Use when the task is the frequency-domain unsteady lift response of a
rigid thin airfoil to a convected sinusoidal vertical gust (the Sears
problem, Sears 1941, JAS 8(3); Bisplinghoff, Ashley and Halfman,
Aeroelasticity, the unsteady incompressible gust chapter; Fung, An
Introduction to the Theory of Aeroelasticity): the complex sears
function S(k) evaluated from the Bessel series with the Theodorsen
lift-deficiency function C(k), the gust gain and the phase lag, and the
unsteady gust-load amplitude against the quasi-steady
2*pi*rho*V*b*w_g_amp reference. This leaf is the section aerodynamics
transfer function of the rigid airfoil, the frequency-domain complement
of the flexible-section time-domain discrete-gust response sibling
aerodynamics/aeroelasticity/aeroelastic-gust-response (whose
quasi-steady reference L_qs = 2*pi*rho*V*b*w_g is exactly the k = 0
amplitude this leaf's gain is normalized against), and it evaluates the
same published C(k) expression, built on the same Bessel machinery, that
aerodynamics/aeroelasticity/flutter-speed-prediction documents for the
V-g stability problem. It produces no stability content, no structural
degrees of freedom and no vehicle load factor: the gust response of a
flexible typical section, static divergence, added-mass coefficient
estimation and the discrete-gust certification load-factor method all
belong to their own leaves.

## Domain quick reference

- Sears problem: rigid thin airfoil of semi-chord b = c/2 in
  incompressible flow at speed V encounters a frozen sinusoidal vertical
  gust with the gust vertical velocity field w_g(x, t) = w_g_amp *
  Re{e^(i*(omega*t - k*x/b))}, x measured downstream from the leading
  edge, so the gust front crosses the leading edge at t = 0. Time
  dependence e^(+i*omega*t); physical quantities are the real part.
  Reduced frequency k = omega*b/V = 2*pi*f*b/V.
- Complex lift amplitude per unit span: L_hat = 2*pi*rho*V*b*w_g_amp *
  S(k) with L(t) = Re{L_hat*e^(i*omega*t)}. The quasi-steady reference
  amplitude L_qs = 2*pi*rho*V*b*w_g_amp is the k = 0 value, identical to
  the reference the discrete-gust sibling documents.
- Bessel series (Abramowitz and Stegun 9.1.10 to 9.1.11, the same
  published series family the flutter sibling cites for C(k)): J0(x) =
  sum_m (-1)^m (x/2)^(2m)/(m!)^2, J1(x) = (x/2)*sum_m (-1)^m
  (x/2)^(2m)/(m!(m+1)!), and the log-harmonic Y0 and Y1 forms with the
  Euler-Mascheroni constant in the ln(x/2) + gamma terms. Each series
  runs until its term magnitude falls below SERIES_TOL times the running
  sum, with SERIES_TERMS_MAX as the safety cap.
- Hankel functions of the second kind: H0^(2)(k) = J0(k) - i*Y0(k),
  H1^(2)(k) = J1(k) - i*Y1(k). Theodorsen function C(k) =
  H1^(2)(k)/(H1^(2)(k) + i*H0^(2)(k)): C = 1 at k = 0 exactly (steady
  flow) and |C| falls toward the high-reduced-frequency limit 1/2.
- Sears function, leading-edge reference: S(k) = [C(k)*(J0(k) -
  i*J1(k)) + i*J1(k)]*e^(-i*k), S(0) = 1 + 0i exactly. The classical
  mid-chord-referenced printed expression S_mid(k) = C(k)*(J0(k) - i*J1(k)) +
  i*J1(k) is the exact identity S_mid(k) = S(k)*e^(+i*k), with |S_mid| =
  |S|; the module pins the leading-edge reference, the convention whose
  phase lag grows monotonically from zero.
- Gust gain and phase lag: gain |S(k)| is the unsteady-load amplitude
  ratio to the quasi-steady reference, monotone decreasing from |S(0)| =
  1; the phase lag phi(k) = -arg S(k) in radians is the time by which
  the lift peak lags the gust peak at the leading edge, monotone
  increasing from zero. The half-amplitude reduced frequency where
  |S(k)| = 0.5 sits near k = 0.567.
- Wronskian gain identity (from the Bessel Wronskian J1*Y0 - J0*Y1 =
  2/(pi*k)): |S(k)| = (2/(pi*k))/|H1^(2)(k) + i*H0^(2)(k)| for k > 0,
  exact to machine precision over the whole sweep of this leaf.
- Scope: single-frequency frozen sinusoidal gust, incompressible
  thin-airfoil theory, small gust amplitudes (linear), two-dimensional
  section per unit span, rigid airfoil with no motion degrees of freedom
  and no added-mass coefficient catalog. Loads are N/m per unit span.
  FAR 25 and CS 25 gust-load rules frame the certification context by
  name only (standards-map.yaml far-25 and cs-25, reference-only),
  never reproduced.

## Workflow

1. Gather the gust encounter inputs: air density rho, flight speed V,
   semi-chord b = c/2, gust vertical velocity amplitude w_g_amp, and the
   reduced frequency k of the sinusoidal gust, either chosen directly for
   a target gust wavelength or converted from the gust frequency f with
   reduced_frequency (k = 2*pi*f*b/V). The module rejects non-positive
   rho, V, b and f and negative or non-finite amplitudes with ValueError.
2. Confirm the Bessel machinery: bessel_j0, bessel_j1, bessel_y0 and
   bessel_y1 at x = 0.5, 1.0 and 2.0 reproduce the published Abramowitz
   and Stegun constants to about 1e-15, so the series are accurate far
   beyond the 0.1 to 2.0 reduced-frequency sweep of this leaf.
3. Evaluate the complex sears function: theodorsen_c builds C(k) from
   the Hankel ratio of the Bessel functions, then sears_function combines
   C(k) with the J0, J1 terms into S(k) on the leading-edge gust
   reference. S(0) returns exactly 1 + 0j, the quasi-steady limit |S| =
   1 that the gain is normalized against.
4. Sweep the gust gain and the phase lag: sears_gain and
   sears_phase_lag over the reduced-frequency sweep show the monotone
   gain roll-off from 1 and the monotone phase-lag growth, the signature
   of the convected sinusoidal gust response.
5. Compute the gust-load amplitudes: quasi_steady_gust_lift gives the
   reference L_qs = 2*pi*rho*V*b*w_g_amp (the k = 0 amplitude) and
   unsteady_gust_load gives the rigid-section load estimate L_hat =
   L_qs*|S(k)| in N/m per unit span.
6. Locate the half-amplitude reduced frequency:
   half_gain_reduced_frequency bisects deterministically on |S(k)| = 0.5
   over [BISECT_LO, BISECT_HI] = [0.1, 2.0], the reduced frequency where
   the unsteady gust-load amplitude falls to half the quasi-steady value.
   A reversed or non-straddling bracket raises ValueError.
7. Verify with the Wronskian gain identity |S(k)| =
   (2/(pi*k))/|H1^(2)(k) + i*H0^(2)(k)| and run the contract test
   scripts/test_sears_function_gust_lift.py under python3.

## Worked example

Rigid thin section of chord c = 2 m (semi-chord b = 1 m) at V = 80 m/s
in standard sea-level air rho = 1.225 kg/m^3, encountering a sinusoidal
vertical gust of amplitude w_g_amp = 5 m/s at reduced frequency k = 0.5.
Gust frequency f = k*V/(2*pi*b) = 6.366197723675814 Hz, gust wavelength
lambda = V/f = 12.56637061435917 m = 6.283185307179586 chord lengths.
All values are the module's real outputs, matching the wave-45 spec
anchors.

- Quasi-steady reference: L_qs = 2*pi*rho*V*b*w_g_amp =
  3078.760800517998 N/m, the amplitude the same gust would produce at
  k = 0.
- Complex sears function: S(0.5) = 0.4392999993899336 -
  0.2901613576384412i (leading-edge gust reference). Gust gain |S(0.5)|
  = 0.5264770678107253, so the unsteady gust load retains 52.65 percent
  of the quasi-steady amplitude at this reduced frequency.
- Phase lag: phi(0.5) = 0.5837270902719581 rad = 33.44509866003521 deg,
  the lift peak following the gust peak at the leading edge by phi/omega
  = 0.014593 s (omega = k*V/b = 40 rad/s at the worked point).
- Unsteady gust-load amplitude: L_hat = L_qs*|S(0.5)| =
  1620.896958747317 N/m per unit span, the amplitude a rigid-section
  sinusoidal-gust load estimate would carry into a structural check.
- Half-amplitude reduced frequency: |S(k)| = 0.5 at k_half =
  0.5672427076304547, where L_hat = 1539.380400258999 N/m =
  0.5000000000000001*L_qs exactly: a gust only about half a semi-chord
  shorter than the k = 0.5 case halves the rigid-section load.
- Gain table read-off: |S(0.1)| = 0.8373543986997829, |S(0.5)| =
  0.5264770678107253, |S(1.0)| = 0.3895689126581746, |S(2.0)| =
  0.2801153775512997 shows the monotone roll-off; even a gust a full
  6.28 chords long (k = 0.5) loads the section at about half the
  quasi-steady amplitude, and the phase lag grows from 0 to 41.52 deg
  (0.7247005314150557 rad at k = 2.0) across the sweep, the signature of
  the convected-gust response.

## Verification

- Confirm the Bessel machinery: bessel_j0/j1/y0/y1 at x = 0.5, 1.0 and
  2.0 match the published constants within 1e-12 (real anchor worst
  error 9.44e-16).
- Confirm the Theodorsen values C(0.5) = 0.597936064250132 -
  0.1507095031626353i, C(1.0) = 0.5394348710777939 -
  0.1002729028641078i and C(2.0) = 0.5129548124291317 -
  0.05769128342167992i within 1e-9 on each part (the classic published
  values the flutter sibling's own machinery reproduces), with C(0)
  exactly 1 + 0j and |C(2.0)| above the 0.5 high-k limit.
- Confirm the sears function values at k = 0.1, 0.25, 0.5, 1.0, 2.0, the
  gain read-off values, the phase-lag values in radians and degrees, and
  S(0) exactly 1 + 0j with gain exactly 1.0 (the quasi-steady limit).
- Confirm the Wronskian gain identity |S(k)| = (2/(pi*k))/|H1^(2)(k) +
  i*H0^(2)(k)| at every 0.1 step of k in [0.1, 2.0] (real anchor max
  residual 2.22e-16, test bound 1e-12).
- Confirm the monotonicity: gain strictly decreasing and phase lag
  strictly increasing at every 0.05 step of the sweep, so the
  half-amplitude crossing is unique.
- Confirm the worked-example loads and geometry (L_qs, L_hat, their
  ratio, the reduced-frequency round trip, the gust wavelength in meters
  and chord lengths, and the half-amplitude load).
- Confirm ValueError rejection of every non-physical input class: zero
  or negative Bessel arguments, negative or non-finite k, non-positive
  rho/V/b/freq, zero frequency, negative or non-finite gust amplitude,
  and reversed or non-straddling half-gain brackets.
- Confirm determinism: two identical full sweeps return identical bits;
  the logic module imports only math and has no RNG.
- Run the contract test offline under both interpreters: python3
  scripts/test_sears_function_gust_lift.py and the pyenv 3.13.12
  python3 (32 tests, deterministic, well under 1 s).

## Related leaves

- aerodynamics/aeroelasticity/flutter-speed-prediction: the V-g flutter
  stability owner of the same typical section; its published C(k)
  convention, built on the same Bessel series family, is evaluated
  inside S(k) here with no stability content.
- aerodynamics/aeroelasticity/aeroelastic-gust-response: the
  flexible-section time-domain discrete-gust sibling whose quasi-steady
  peak reference L_qs = 2*pi*rho*V*b*w_g is the k = 0 limit this leaf's
  gain is normalized against.
- aerodynamics/aeroelasticity/divergence-speed: the static torsional
  instability of the same section geometry.
- aerodynamics/aeroelasticity/added-mass-coefficients-potential-flow:
  the added-mass coefficient catalog of accelerating bodies; this rigid
  airfoil has no acceleration degree of freedom.
- aerodynamics/high-speed/wave-drag-area-rule: the Sears-Haack
  minimum-drag body and area-rule leaf, the owner of the transonic
  sears-haack token, distinct from the sears-function gust response.
- structures/loads/gust-maneuver-loads: the rigid-aircraft discrete-gust
  certification load-factor method (FAR 25.341 context); this leaf is
  the section aerodynamics transfer function, no vehicle inertia or load
  factor.
- structures/loads/random-vibration-analysis: the PSD machinery home of
  continuous-turbulence spectral gust content; this leaf is
  single-frequency, not spectral.

## Pitfalls

- Confusing the gust-load amplitude with the quasi-steady value: at the
  worked k = 0.5 point L_hat = 1620.896958747317 N/m is only
  0.5264770678107253 of L_qs = 3078.760800517998 N/m because the
  unsteady gain rolls off with reduced frequency; run the gain, do not
  substitute the quasi-steady anchor for a finite-frequency gust.
- Mixing the leading-edge and mid-chord gust references: S_mid(k) =
  S(k)*e^(+i*k) differ by the propagation phase over the semi-chord, so
  the phase lag only grows monotonically from zero on the leading-edge
  reference this module pins; |S| is identical in either reference.
- Reading the phase lag with the wrong sign convention: with the
  e^(+i*omega*t) convention the lag is phi(k) = -arg S(k) = atan2(-Im S,
  Re S), positive for all k > 0 here; flipping the time convention
  flips the sign.
- Pushing the Bessel series past their sweep: the series forms are
  double-precision accurate across the 0.1 to 2.0 reduced-frequency
  range documented here; the flutter sibling's C(k) machinery covers the
  same family for its own k range.
- Treating the Sears response as a structural or spectral result: the
  rigid-airfoil load of this leaf has no inertia weighting, no load
  factor and no PSD content; the discrete-gust certification method and
  the continuous-turbulence spectra live in the structures loads leaves.
- Forgetting the certification context is reference-only: FAR 25 and CS
  25 gust-load rules are named as the context, never reproduced; the
  Sears relations are standard engineering methodology, summary-only.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_sears_function_gust_lift.py

The test covers the Bessel reference constants and the worst series error
bound, the Theodorsen values and limits, the exact S(0) quasi-steady
limit, the complex sears function values, the gain and phase-lag read-off
values, the monotone gain roll-off and phase-lag growth over the sweep,
the Wronskian gain identity, the half-amplitude reduced frequency and
its bracket sanity, the worked-example loads, frequencies, wavelengths
and the half-amplitude load, the zero-amplitude gust case, ValueError
rejection of every non-physical input class, sweep determinism, and the
stdlib-only purity of the logic module. It passes under both /usr/bin/
python3 (3.9.6) and the pyenv 3.13.12 interpreter.

## Compliance

- The Sears gust response is public-domain textbook methodology (Sears
  1941; Bisplinghoff, Ashley and Halfman, Aeroelasticity; Fung, An
  Introduction to the Theory of Aeroelasticity); the airworthiness
  context is FAR 25 and CS 25 gust-load rules, referenced by name only,
  summary-only per standards-map.yaml (both reference-only).
- compliance: STANDARDS-REF, gated: false.
