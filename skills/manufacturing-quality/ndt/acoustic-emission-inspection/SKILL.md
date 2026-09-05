---
name: acoustic-emission-inspection
description: "Use when the task is acoustic emission testing, AE monitoring, source location, hit thresholding, or Kaiser/Felicity assessment. Compute acoustic emission inspection parameters for aerospace parts and structures: determine which recorded signals cross the amplitude threshold, group the hits into events with the hit definition time window, compute signal energy, locate the emission source by linear and planar triangulation from sensor arrival times, and evaluate the Kaiser effect and Felicity ratio to judge damage progression in composites and pressure vessels during load and proof testing. Produce the hit list, the event groups, the located source coordinates, and the Kaiser/Felicity verdict with the qualification context of NAS-410 personnel certification and AS9100 special process control. Trigger: acoustic emission, ae monitoring, source location, kaiser effect, felicity ratio, hit threshold, planar triangulation."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
  - id: nas-410
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: ndt
  tags: [acoustic-emission, ae-monitoring, source-location, kaiser-effect, felicity-ratio, hit-threshold, planar-triangulation, ndt]
  version: 0.1.0
  author: Aero Agent Skills
---

# Acoustic Emission Inspection (manufacturing-quality/ndt/acoustic-emission-inspection)

Use when the task is passive acoustic emission testing of aerospace
parts and structures: thresholding recorded hits, grouping hits into
events, computing signal energy, locating emission sources from sensor
arrival times, and judging damage progression with the Kaiser effect
and Felicity ratio. This leaf is the passive-listening counterpart of
ultrasonic-inspection (which sends pulses and reads echoes) and
complements ndt-method-selection, which picks among the NDT methods
before any instrument is deployed.

## Domain quick reference

- AE sources: sudden localized deformation releases elastic waves;
  typical aerospace sources are crack growth, fiber breakage,
  delamination, matrix cracking, and fretting.
- Sensors: resonant piezoelectric transducers are the common pick,
  with typical bands of 100-500 kHz (a 150 kHz resonant sensor is a
  common default); broadband sensors are used when spectral content
  matters. Couplant, mounting, and sensor spacing set the coverage.
- Hit vs event: a hit is one sensor channel crossing the amplitude
  threshold; an event is the emission of one source, assembled from
  hits whose arrival times fall inside the hit definition time (HDT)
  window.
- Threshold and energy: a fixed amplitude threshold in dB (40 dB is a
  common start) separates signal from noise; amplitude is reported in
  dBae; signal energy is the measured area under the rectified signal
  envelope (MARSE-style) or the deterministic proxy dt * sum of
  squared amplitudes.
- Kaiser effect: on reload, no emission is expected until the previous
  maximum load is exceeded. Felicity ratio = load at which emission
  resumes / previous maximum load. A ratio at or above 1 means the
  Kaiser effect holds and damage is stable; a ratio below 1 (0.95 is a
  common threshold for composites) signals the Felicity effect and
  progressing damage.
- Source location: linear location uses two sensors on a line and the
  arrival-time difference; planar location triangulates from three or
  more sensors by solving the hyperbolic time-difference system with
  an iterative least-squares scheme. Sources far outside the array are
  unreliable and are rejected.
- Applications: composite damage assessment, pressure vessel hydro and
  proof testing, structural load monitoring. Personnel qualification
  follows NAS-410 (and the SNT-TC-1A context) level certification;
  AS9100 frames NDT as a special process. Standards are referenced by
  name only per standards-map.yaml.

## Workflow

1. Set the amplitude threshold and filter the record with
   hit_threshold_check to get the hits and counts.
2. Group the hits into events with group_hits_to_events using the HDT
   window.
3. Compute the energy of each hit or event with signal_energy.
4. For a sensor pair on a line, call source_location_linear with the
   gauge distance, the two arrival times, and the wave speed.
5. For an array, call source_location_planar with the sensor
   positions, the arrival times, and the wave speed; the function
   raises ValueError on impossible times, inconsistent time sets, and
   out-of-array solutions.
6. On reload data, call felicity_ratio and kaiser_effect_check to get
   the ratio and the damage verdict.
7. Confirm the deterministic behavior with the contract test
   scripts/test_acoustic_emission_inspection.py.

## Worked example: planar source location

A square array at (0, 0), (1, 0), (0, 1), (1, 1) meters on a composite
panel with wave speed 3000 m/s. A source near (0.4, 0.6) m gives
arrival times of about 240.4, 282.8, 188.6, and 240.4 microseconds at
the four sensors. source_location_planar returns the source at (0.4,
0.6) m within 1e-6 m with a near-zero residual; the same call with a
corrupted arrival time raises ValueError instead of reporting a wrong
point.

## Related leaves

- ndt-method-selection: picks among NDT methods by defect and material
  class before the AE system is deployed.
- ultrasonic-inspection: active echo-based cousin of passive AE
  listening.
- thermography: surface and near-surface thermal technique for the
  same defect classes.
- visual-inspection: baseline surface screening that precedes
  instrumented NDT.

## Pitfalls

- Reading the Felicity ratio backwards: a ratio at or above 1 means
  the Kaiser effect holds and damage is stable, while a ratio below 1
  (0.95 is the common composites threshold) signals the Felicity
  effect and progressing damage - treating a sub-1 ratio as a pass
  misses the very damage progression AE is deployed to catch.
- Counting hits as events: a hit is one sensor channel crossing the
  amplitude threshold, and hits only become one source event when
  their arrival times fall inside the HDT window - grouping must run
  before hit counts are quoted as emissions.
- Trusting a located source without checking the array geometry:
  sources far outside the array are unreliable, and the planar solver
  raises ValueError on impossible arrival times, inconsistent time
  sets and out-of-array solutions instead of returning a wrong point.
- Mixing dB scales: amplitudes are reported in dBae against a fixed
  dB threshold (40 dB is a common start), so thresholds and hit
  amplitudes from different scales cannot be compared directly.
- Ignoring the coverage chain: couplant, mounting and sensor spacing
  set the coverage, and resonant sensors are band-limited (typical
  100-500 kHz), so a gap in coupling or an out-of-band emission
  silently produces no hits.
- Treating AE as a general inspection without the qualification
  context: personnel certification follows NAS-410 (SNT-TC-1A
  context) level certification and AS9100 frames NDT as a special
  process, so an AE verdict outside that qualification frame has no
  disposition standing.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_acoustic_emission_inspection.py

The test covers threshold crossing including a zero threshold, event
grouping with the HDT window, energy weighting, linear location
including impossible arrival times, planar location including
inconsistent time sets and out-of-grid sources, and the Kaiser/Felicity
verdicts.

## Compliance

- Standards referenced, not reproduced: as9100 and nas-410 resolve in
  standards-map.yaml, both reference-only; the method content is common
  AE methodology, summarized only.
- compliance: STANDARDS-REF, gated: false.
