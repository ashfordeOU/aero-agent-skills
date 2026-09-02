---
name: structural-coupling-test
description: "Use when you must assess the structural coupling of the flight control system with the airframe structural modes from measured frequency response data: compute the gain margin from the amplitude response at the phase crossing and the phase margin from the phase response at the gain crossing, plan the frequency response testing of the closed-loop control system with swept sine, chirp, or impulse excitation across the flight envelope, and judge the margins against the typical 6 dB gain margin and 45 degree phase margin criteria of the flutter and coupling guidance. Produces the gain margin, the phase margin, the PASS or FAIL margin verdict, and the excitation test point set that gate the structural-coupling-test assessment. Trigger: structural-coupling-test, structural-coupling, gain-margin, phase-margin, frequency-response, swept sine, chirp, impulse excitation, airframe modes, flight envelope test points."
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
  subdomain: envelope
  tags: [structural-coupling-test, structural-coupling, gain-margin, phase-margin, frequency-response, swept-sine, chirp, impulse-excitation, closed-loop-control, airframe-structural-modes, margin-criteria, flight-envelope, test-points, flight-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# Structural Coupling Test (flight-test-operations/envelope/structural-coupling-test)

Use when the task is the structural coupling test (SCT) of a flight
control system: measuring the closed-loop frequency response of the
control system over the band that brackets the airframe structural
modes, computing the gain margin and the phase margin from the
measured amplitude and phase response, and judging the margins against
the typical criteria of the flutter and coupling guidance. The output
is the margin verdict and the excitation sweep plan, not the flutter
clearance itself or the ground vibration modal data.

## Domain quick reference

- Structural coupling is the closed-loop coupling of the flight
  control system with the airframe structural modes: the control
  surface motion excites a structural mode and the sensor feedback
  reinforces it. The SCT demonstrates that the coupled loop stays
  stable with the required stability margins at every test point.
- Frequency response testing: measure the amplitude and phase response
  of the control loop over the frequency band of interest, normally
  up to several times the first elastic mode frequency. Excitation
  methods: swept sine (slow continuous sine sweep with dwell near the
  resonances for coherence), chirp (fast linear or logarithmic sweep
  over the band), and impulse (broadband excitation with low energy
  density, best for on-line checks).
- Gain margin: from the amplitude response at the frequency where the
  open-loop phase crosses -180 degrees, gain margin in dB = -(amplitude
  in dB at that crossing). A negative amplitude there means the gain
  can grow by that amount before the loop goes unstable.
- Phase margin: from the phase response at the frequency where the
  amplitude crosses 0 dB (unity gain), phase margin in degrees =
  180 + phase at that crossing.
- Typical margin criteria: 6 dB gain margin and 45 degrees phase
  margin, per the flutter and coupling guidance; a margin at or above
  the criterion passes, anything below fails. Worked example:
  amplitude -9 dB at the phase crossing gives a 9 dB gain margin PASS,
  phase -135 degrees at the gain crossing gives a 45 degree phase
  margin PASS.
- Test points across the flight envelope: cover the altitude, speed,
  weight, center of gravity, and configuration range, plus the flight
  control system states that change the loop dynamics (control law
  gains, feel system, gain scheduling); the critical points are the
  conditions with the least damped structural modes or the highest
  control gains.

## Workflow

1. Define the frequency band and the test points across the flight
   envelope: bracket the airframe structural modes of interest and
   cover the altitude, speed, weight, cg, and configuration range.
2. Excite the closed-loop control system with swept sine, chirp, or
   impulse excitation and measure the amplitude and phase response
   over the band; check coherence before trusting the points.
3. Find the phase crossing frequency with
   phase_crossing_frequency(freqs, phase_deg) and interpolate the
   amplitude there with interpolate_response, or get the margin
   directly with gain_margin_from_response(freqs, mag_db, phase_deg).
4. Find the gain crossing frequency with
   gain_crossing_frequency(freqs, mag_db) and interpolate the phase
   there, or get the margin directly with
   phase_margin_from_response(freqs, mag_db, phase_deg).
5. Judge the margins with margin_verdict(gain_db, phase_deg) against
   the default 6 dB and 45 degree criteria; PASS requires both margins
   at or above their criteria.
6. Plan the excitation sweep with
   excitation_frequencies(f_min, f_max, points_per_decade) so the
   sweep covers the band with enough points per decade, and repeat the
   margin computation at every envelope test point.

## Pitfalls

- Routing flutter stability questions here: the required flutter speed
  from the design dive speed factor, the damping trend extrapolation,
  and the frequency separation check belong to flutter-testing; the
  SCT covers the servo-elastic closed-loop coupling with the flight
  control system, not the aeroelastic divergence analysis.
- Routing ground vibration questions here: modal damping from the
  half-power bandwidth, mode candidates from FRF peaks, and shaker or
  impact hammer mode extraction belong to ground-vibration-testing;
  the SCT works from the in-flight closed-loop frequency response.
- Routing generic flight test planning here: the build-up test point
  ordering, instrumentation coverage, and go/no-go gates belong to
  flight-test-planning and test-point-matrix-design.
- Routing controller design margins here: gain and phase margins from
  a designed open-loop transfer function belong to the control design
  leaves in gnc-autonomy; the SCT measures the installed closed-loop
  response from flight test data.
- Swapping the crossings: the gain margin uses the amplitude at the
  phase crossing (-180 degrees) and the phase margin uses the phase at
  the gain crossing (0 dB); mixing the two gives meaningless margins.
- Extrapolating past the measured band: interpolate only inside the
  band, the interpolation helpers raise ValueError outside it; a
  missing crossing (no -180 degree phase crossing or no 0 dB gain
  crossing in the measured band) returns None and must be reviewed
  before claiming a margin.
- Trusting low coherence data: a fast chirp or an impulse can give low
  coherence near the resonances; dwell with the swept sine or repeat
  the runs before computing the margins.
- Checking only one flight condition: the loop margins change with
  altitude, speed, weight, and control gains, so the verdict must be
  repeated across the flight envelope test points, not taken from a
  single condition.

## Behavior contract (gate 3)

The gain margin, phase margin, margin verdict, frequency response
interpolation and crossing helpers, the response-derived margins, and
the excitation frequency sweep logic is exercised by the gate 3
contract test: scripts/test_structural_coupling_test_logic.py against
scripts/structural_coupling_test_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_structural_coupling_test_logic.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 frame the
  stability clearance context for the aeroplane including the flight
  control system and the structural coupling; the 6 dB gain margin and
  45 degree phase margin criteria are common certification practice in
  the flutter and coupling guidance, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
