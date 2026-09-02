---
name: random-vibration-analysis
description: "Use when you must compute the random vibration response of a structure or equipment item to a base-input acceleration power spectral density: single-degree-of-freedom transmissibility |H(f)|^2 = 1/((1-r^2)^2 + (2*zeta*r)^2), response PSD G_out(f) = |H(f)|^2 * G_in(f), RMS response in g from the Miles equation sigma = sqrt((pi/2)*f_n*Q*G_in(f_n)) with Q = 1/(2*zeta), numerical integration of the response PSD over a supplied spectrum, 3-sigma peak level, and the equivalent static load factor n_eq = 3*sigma for equipment qualification screening. Produces response PSD points, g-rms and 3-sigma response levels, and screening load factors. Trigger: random vibration, PSD response, Miles equation, transmissibility, base excitation, g-rms, power spectral density, vibration qualification."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: loads
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: loads
  tags: [random-vibration-analysis, psd-response, miles-equation, transmissibility, base-excitation, g-rms, power-spectral-density, vibration-qualification, random-vibration, equivalent-static-load-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# Random Vibration Response Analysis (structures/loads/random-vibration-analysis)

Use when a structure or equipment item must be checked against a
random vibration environment described by a base-input acceleration
power spectral density (PSD, in g^2/Hz). The item is modeled as a
single-degree-of-freedom (SDOF) oscillator at its natural frequency
f_n with damping ratio zeta; the analysis computes the response PSD
through the acceleration transmissibility, the RMS response in g
from the Miles equation (flat input at resonance) or by numerical
integration of the response PSD (arbitrary spectrum), the 3-sigma
peak level, and the equivalent static load factor used for equipment
qualification screening. This is the other dynamic loads input
alongside discrete gust and maneuver loads, feeding the same
structural sizing and fatigue flows. The response-level model here is
deliberately confined to SDOF random vibration response; cycle
counting and cumulative fatigue damage of the vibration response are
owned by the fatigue pack.

## Domain quick reference

- SDOF base-excitation model: frequency ratio r = f/f_n and the
  acceleration transmissibility (response to base acceleration)

      |H(f)|^2 = 1 / ((1 - r^2)^2 + (2*zeta*r)^2)

  |H(f)|^2 equals 1 at f = 0 (rigid-body limit) and Q^2 = 1/(2*zeta)^2
  at f = f_n, and rolls off as (f_n/f)^4 well above resonance.
- Response PSD: G_out(f) = |H(f)|^2 * G_in(f), with G_in in g^2/Hz and
  G_out in g^2/Hz. The response PSD peaks near the damped resonance
  f_n*sqrt(1 - 2*zeta^2), which is the dominant response frequency.
- Amplification factor at resonance: Q = 1/(2*zeta) (about 10 at
  zeta = 0.05, about 5 at zeta = 0.10).
- Miles equation (flat, band-limited input at the resonance):

      sigma = sqrt((pi/2) * f_n * Q * G_in(f_n))

  in g_rms, with f_n in Hz. It follows from integrating |H(f)|^2 over
  all frequencies: the integral equals (pi/2)*f_n*Q, so
  sigma^2 = G_in * (pi/2) * f_n * Q.
- Numerical path (input not flat at f_n): sigma^2 = integral of
  G_out(f) df, trapezoidal rule on the supplied spectrum points. The
  grid must resolve the response peak, whose half-power width is about
  2*zeta*f_n (4 Hz at f_n = 40 Hz, zeta = 0.05); a spectrum sampled
  coarser than that underestimates the integral.
- 3-sigma peak and equivalent static load factor: for a narrowband
  Gaussian random response the peak accelerations reach about
  3*sigma, so peak = n_eq = 3*sigma in g. The load factor n_eq is a
  screening value only: it assumes the response at resonance dominates
  and the item behaves as the SDOF oscillator modeled here.
- Units: f, f_n in Hz; zeta dimensionless in (0, 1); G in g^2/Hz;
  sigma in g_rms; peaks and load factors in g.
- Context: transport certification FAR 25.301/25.303 frames the limit
  loads context (reference only); equipment random vibration test
  levels follow MIL-STD-810H (random vibration test method) and
  DO-160G Section 8 (vibration tests of airborne equipment), which
  this analysis converts into item response levels. Standard text is
  named and paraphrased, never reproduced.

## Workflow

1. Gather the item's first natural frequency f_n (Hz) and damping
   ratio zeta, from the modal analysis or a resonance survey, and the
   input base-acceleration PSD spectrum as (f, G_in) points in
   g^2/Hz over the test band.
2. Confirm the amplification factor with quality_factor(zeta):
   Q = 1/(2*zeta). Typical equipment damping runs 2-10% of critical.
3. Get the transmissibility at any frequency with
   transmissibility(f, f_n, zeta) or transmissibility_squared for the
   PSD amplification |H(f)|^2.
4. For a flat band-limited input at resonance, use the Miles closed
   form miles_sigma(f_n, zeta, g_in_at_resonance): sigma =
   sqrt((pi/2)*f_n*Q*G_in(f_n)).
5. For an arbitrary spectrum, build the response PSD with
   response_psd(spectrum, f_n, zeta) and integrate with
   numerical_sigma(spectrum, f_n, zeta) (trapezoidal on the provided
   points; at least two points required). Check the grid resolves the
   response peak (step 1 quick reference).
6. Run the full analysis with random_vibration_analysis(f_n, zeta,
   spectrum): returns sigma_rms_g (numerical), sigma_miles_g (Miles
   value with the input level interpolated at f_n, None when f_n lies
   outside the spectrum coverage), psd_response_points, f_n, q,
   dominant_response_frequency, peak_3sigma_g and n_eq_g.
7. Report the 3-sigma level with peak_three_sigma(sigma) and the
   equivalent static load factor with
   equivalent_static_load_factor(sigma) for the qualification
   screening against the item's test-withstand level.
8. Feed the response levels into the fatigue flow (Miner damage)
   when the vibration environment contributes to the load spectrum;
   cycle counting and damage accumulation live in the fatigue pack,
   not here.

## Worked example

Equipment item at f_n = 40 Hz with zeta = 0.05 (Q = 10) under a flat
base-input PSD of G = 0.01 g^2/Hz over 20-500 Hz.

- Miles: sigma = sqrt((pi/2)*40*10*0.01) = sqrt(6.2831853) =
  2.5066 g_rms; the 3-sigma peak is 3*2.5066 = 7.52 g and the
  equivalent static load factor is n_eq = 7.52 g for screening.
- Response PSD at resonance: G_out(40) = 0.01 * Q^2 = 0.01 * 100 =
  1.0 g^2/Hz; the dominant response frequency is
  40*sqrt(1 - 2*0.05^2) = 39.90 Hz.
- Numerical cross-check: trapezoidal integration of G_out over the
  20-500 Hz band on a 1 Hz grid gives sigma = 2.458 g_rms, about 2%
  below the Miles value (the deficit is the input band truncation
  below 20 Hz, far from the resonance); a 2 Hz grid gives 2.462 g_rms,
  still within a few percent. Both confirm the Miles result when the
  input is flat around resonance.
- An avionics box with f_n = 90 Hz and zeta = 0.03 (Q = 16.7) under
  the same flat 0.01 g^2/Hz input responds at sigma =
  sqrt((pi/2)*90*16.67*0.01) = 4.854 g_rms, a 3-sigma level of
  14.6 g, which would fail a 10 g equipment screening; the case
  demonstrates how strongly the response level scales with f_n and Q.

## Verification

- miles_sigma(40, 0.05, 0.01) returns 2.5066 g_rms and
  peak_three_sigma gives 7.52 g, both within 1% of the hand calc.
- quality_factor(0.05) returns 10 and transmissibility_squared at
  f = f_n returns Q^2 = 100.
- numerical_sigma over the flat 20-500 Hz band (2 Hz grid) returns a
  value within 3% of the Miles sigma (worked example cross-check).
- random_vibration_analysis returns the dict with sigma_rms_g,
  psd_response_points, f_n, q and dominant_response_frequency, and
  reports sigma_miles_g = None when f_n falls outside the input band.
- Every non-physical input raises ValueError: non-positive f_n,
  zeta <= 0 or zeta >= 1, negative PSD ordinates, empty or
  single-point spectra for integration, non-increasing frequencies,
  and negative frequencies.
- Deterministic contract: scripts/test_random_vibration_analysis.py.

## Related leaves

- structures/loads/gust-maneuver-loads: discrete gust and maneuver
  load factors, the other dynamic loads input that joins random
  vibration in the loads pack.
- structures/fem/modal-analysis: natural frequencies and damping used
  as the f_n and zeta inputs of this response analysis.
- structures/fatigue/miner-damage: cumulative damage of the cycles
  implied by the vibration response; this leaf stops at response
  levels, the fatigue pack owns the damage estimate.
- structures/thermal-structures/thermal-stress-analysis: thermal
  environment loads assessed alongside the vibration qualification.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_random_vibration_analysis.py

The test covers the worked example (Miles sigma 2.5066 g_rms and
3-sigma level 7.52 g within 1% of the hand calc), the numerical
cross-check on the flat band within a few percent of Miles, the
Q^2 = 100 response amplification at resonance, the (f_n/f)^4
roll-off, the response PSD construction, sigma scaling with
sqrt(G), sqrt(f_n) and 1/sqrt(zeta), the Miles round-trip that
recovers the input PSD, interpolation of the input level at f_n,
the analysis dict contents, and ValueError rejection of non-positive
f_n, out-of-range zeta, negative ordinates, and empty, single-point
or non-monotonic spectra.

## Compliance

- FAR 25 is US government work (public domain); summary and physics
  values only, per standards-map.yaml. MIL-STD-810H and DO-160G
  Section 8 are named as equipment test-level context and paraphrased,
  never reproduced.
- compliance: STANDARDS-REF, gated: false.
