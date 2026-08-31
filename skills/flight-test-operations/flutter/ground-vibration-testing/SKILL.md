---
name: ground-vibration-testing
description: "Use when you must plan or analyze a ground vibration test (GVT) for flutter clearance: estimate modal damping from the half-power bandwidth of the frequency response function (FRF) peak, judge whether an FRF peak qualifies as a mode candidate, compute the FFT frequency resolution for the test setup, and check the detected mode count against the pre-test expectation. Covers excitation methods (shakers, impact hammers, sine sweep, random), mode extraction (peak picking, circle fit, curve fitting), mode shape and mass normalization, test setup (accelerometer placement, suspension), quality checks (reciprocity, coherence), and GVT-to-flight correlation. Produces damping estimates, mode candidate verdicts, frequency resolution, and mode count verdicts that gate GVT data quality before flight clearance. Trigger: ground vibration test, modal damping, half-power bandwidth, frequency response function, mode shapes, accelerometer."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: flutter
  tags: [ground-vibration-testing, ground-vibration-test, modal-damping, half-power-bandwidth, frequency-response-function, mode-shapes, accelerometer, frf, gvt, modal-analysis, flutter, damping]
  version: 0.1.0
  author: AeroSkills
---

# Ground Vibration Testing (flight-test-operations/flutter/ground-vibration-testing)

Use when the task is a ground vibration test (GVT) for flutter
clearance: measuring the structural natural frequencies, mode shapes,
and damping of the aircraft on the ground before flight, and checking
the measured data quality before the results feed the flutter
clearance model.

## Domain quick reference

- Purpose: a GVT measures the structural natural frequencies, mode
  shapes, and damping of the airframe on the ground before flight.
  The measured modes update and validate the structural dynamic model
  that the flutter clearance analysis is built on, so the test data
  quality gates everything downstream.
- Excitation methods: electrodynamic shakers (attached with stingers,
  force gages in line), impact hammers (broadband impulse, light
  structure friendly), sine sweep (slowly swept single sine, high
  signal-to-noise at resonance), and random excitation (broadband,
  fast, low peak force). Each excites the structure at the drive
  point and the response is measured at the accelerometer stations.
- Frequency response function: H(f) = A(f) / F(f), the response
  acceleration spectrum over the excitation force spectrum. The FRF
  magnitude peaks at the natural frequencies and the phase flips
  through the resonance; the FRF is the primary data product of the
  test.
- Frequency resolution: df = sample_rate / n_samples, the FFT line
  spacing in Hz. With typical damping below a few percent, df must be
  fine enough that the half-power band of each mode spans several
  lines, or damping is overestimated.
- Half-power bandwidth damping: zeta = (f2 - f1) / (2 * fn), with fn
  the natural frequency and f1, f2 the frequencies where the FRF
  magnitude has fallen to 1/sqrt(2) of the peak value. Damping is
  dimensionless; zeta below about 0.03 to 0.05 is typical for
  airframe modes.
- Mode extraction: peak picking finds candidate modes from FRF
  magnitude peaks, circle fit fits a circle to the FRF in the Nyquist
  plane for a refined natural frequency and damping, and curve
  fitting (multi-DOF, e.g. rational fraction polynomial) separates
  closely spaced modes that overlap in frequency.
- Mode shapes and mass normalization: the mode shape is the relative
  displacement at each accelerometer station for a given mode; mass
  normalization scales the shape so the generalized mass is unity,
  which lets the measured mode be compared directly with the analysis
  model mode (via the MAC) and used for flutter correlation.
- Test setup: accelerometers placed to capture the expected mode
  shapes (no station at a node line of a mode of interest), the
  structure suspended on soft bungee or air springs so the rigid body
  modes sit well below the first elastic mode and do not contaminate
  the band of interest.
- Quality checks: coherence gamma^2 in [0, 1] near unity (0.9 or
  better) means the response is linearly driven by the input;
  reciprocity H_ij = H_ji within a few percent holds for a linear
  time-invariant structure. Low coherence or broken reciprocity flags
  noise, leakage, nonlinearity, or a bad transducer.
- GVT-to-flight correlation: the mass-normalized measured modes are
  compared with the analysis model (frequency differences typically
  within a few percent, MAC above about 0.9 for well-correlated
  modes); the correlated model then carries the flutter clearance.

## Workflow

1. Plan the setup: choose the excitation method, place the
   accelerometers on the structure, and suspend the aircraft on soft
   supports so the rigid body modes stay below the first elastic
   mode.
2. Check the acquisition band with frequency_resolution(sample_rate,
   n_samples) and confirm the line spacing resolves the expected
   half-power bands.
3. Measure the FRFs and screen every FRF with coherence_verdict
   (coherence) and reciprocity_check(h12, h21); discard or redo data
   that fails.
4. Extract the modes: locate candidate peaks with
   peak_pick_verdict(frf_peak, threshold), then refine each candidate
   with the half-power bandwidth or a curve fit.
5. Estimate the modal damping of each accepted mode with
   half_power_damping(f1, f2, fn) and record the mode shapes from the
   FRF responses at the stations.
6. Mass-normalize the mode shapes and compare the count with the
   analysis model using mode_count_verdict(peaks, expected); a
   mismatch means modes are missed, split, or not in the band.
7. Correlate the measured modes with the model (frequency
   differences, MAC) and feed the correlated model into the flutter
   clearance.

## Pitfalls

- Damping from a too-coarse frequency resolution: if the half-power
  band spans fewer than a few FFT lines the bandwidth is
  overestimated and zeta comes out too high; check
  frequency_resolution before trusting the damping.
- Peak picking on noise: an FRF peak below the threshold is not a
  mode; forcing every peak to be a mode inflates the mode count and
  corrupts the correlation.
- Ignoring coherence and reciprocity: low coherence or broken
  reciprocity means the FRF is not a clean linear measurement; gate
  the data before extracting modes.
- Accelerometer on a node line: a station placed at a node of a mode
  of interest records no response for that mode and the mode shape
  looks wrong; check the analytical node locations when placing the
  stations.
- Rigid body modes in the band: stiff suspension raises the rigid
  body frequencies toward the first elastic mode and contaminates it;
  the supports must keep them well separated.
- Half-power points not bracketing the natural frequency: feeding f1
  and f2 that do not straddle fn (or any non-positive frequency)
  raises ValueError; use the actual 1/sqrt(2) crossings, not
  arbitrary points.
- Confusing found and expected mode counts: the mode count verdict
  compares detected peaks with the model expectation in the test
  band; extra peaks (noise, rigid body) and missing peaks (node
  placement, weak excitation) both fail the check and need
  investigation, not acceptance.

## Behavior contract (gate 3)

The half-power damping, peak picking, frequency resolution, mode
count, reciprocity, and coherence logic is exercised by the gate 3
contract test: scripts/test_ground_vibration_testing.py against
scripts/ground_vibration_testing_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_ground_vibration_testing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the GVT
  methodology (excitation, FRF measurement, mode extraction, half-
  power damping, quality checks, model correlation) sits in the
  flutter clearance context of the FAR 25.629 / CS 25.629
  certification practice as common structural dynamics knowledge,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
