---
name: stress-spectrum-derivation
description: "Use when derive the stress spectrum at the fatigue-critical location from a load event sequence per ECSS-E-ST-32C clauses 7.2.3–7.2.4: convert each load event in the load spectrum to a stress at the section of interest using cross-sectional area and stress concentration factor, apply rainflow cycle counting to extract stress amplitude and mean pairs, optionally apply a Goodman mean-stress correction to produce a fully-reversed equivalent amplitude spectrum, and aggregate cycle counts by stress amplitude bin ready for fatigue damage summation. Trigger: ecss, e-st-32-structures-scope, stress-spectrum, load-spectrum-counting, fatigue-critical-location, rainflow-counting, goodman-correction, cycle-counting."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-32-structures-scope, stress-spectrum, load-spectrum-counting, fatigue-critical-location, rainflow-counting, goodman-correction, cycle-counting]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Stress Spectrum Derivation (space-systems/ecss/stress-spectrum-derivation)

Use when the task is deriving the stress spectrum at the fatigue-critical
location from the load spectrum per ECSS-E-ST-32C clauses 7.2.3–7.2.4 —
converting load events to stresses, counting cycles by the rainflow method,
applying mean-stress correction where required, and producing the amplitude
spectrum for fatigue damage summation.

## Domain quick reference

- The load spectrum (a sequence of load events from the mission profile) is
  first converted to a stress history at the critical cross-section by
  dividing each load by the net section area and multiplying by the stress
  concentration factor Kt (>= 1.0). A location with the highest peak stress
  magnitude across all events is the fatigue-critical location.
- Cycle counting transforms the stress history (a series of peaks and
  troughs) into discrete cycles, each described by a stress amplitude
  (half the peak-to-trough range) and a mean stress. The rainflow method
  per ECSS-E-ST-32C clause 7.2.4 is the required technique; it pairs
  ranges hierarchically so that large cycles are counted before the
  smaller residual cycles nested inside them.
- Mean stress has a first-order effect on fatigue life. When the
  ultimate tensile strength is known, the Goodman correction converts
  each amplitude–mean pair into a fully-reversed equivalent amplitude,
  allowing the resulting spectrum to be used directly against a
  fully-reversed S–N curve. A positive mean stress reduces the allowable
  amplitude; a zero mean leaves the amplitude unchanged.
- The stress spectrum is the aggregated table of (stress amplitude,
  mean stress, cycle count) bins sorted by descending amplitude. Each
  row drives one term in the Miner linear damage summation of subsequent
  fatigue analysis steps.

## Workflow

1. Identify the fatigue-critical location: evaluate the peak stress
   magnitude at each candidate cross-section across all load events and
   select the location with the highest value. Record the section area
   and the stress concentration factor Kt; if Kt is unavailable default
   to 1.0 and flag the assumption.
2. Convert the load spectrum to a stress history: for each load event
   compute stress = load / area × Kt. Preserve the ordering of events —
   the sequence matters for cycle counting.
3. Extract turning points from the stress history (local maxima and
   minima) to reduce the time series to its cycle-counting skeleton,
   retaining the start and end values.
4. Apply rainflow cycle counting to the turning-point sequence: scan the
   stack of three consecutive points; when the inner range is smaller
   than or equal to the outer range, close a full cycle with that inner
   range; otherwise advance. Process remaining stack points as half-cycles
   at the end.
5. For each cycle compute the stress amplitude (half the range) and mean
   stress (midpoint of the range).
6. If the ultimate tensile strength is available, apply the Goodman
   correction to each amplitude–mean pair to obtain the fully-reversed
   equivalent amplitude. Reject any pair where the mean stress magnitude
   equals or exceeds the ultimate strength — that pair represents static
   failure, not fatigue.
7. Aggregate cycles into the stress spectrum table by binning identical
   amplitude–mean pairs and summing their counts. Sort the table by
   descending stress amplitude.
8. Verify the spectrum: confirm at least one cycle was extracted, confirm
   no bin has a negative count, and confirm all amplitudes are non-negative.

## Pitfalls

- Skipping the turning-point extraction and applying rainflow to the raw
  time series directly — flat segments between identical values create
  spurious zero-range cycles that inflate the total cycle count without
  contributing to damage.
- Applying a stress concentration factor below 1.0 — Kt represents a
  stress raiser and cannot reduce the nominal stress; a value below 1.0
  indicates a geometry or data error and must be rejected.
- Treating a Goodman mean stress equal to the ultimate strength as a
  valid fatigue cycle — the Goodman denominator reaches zero at that
  point, implying static fracture rather than a finite fatigue life.
- Confusing cycle amplitude with cycle range — the amplitude is half the
  range; feeding the full range into an S–N curve calibrated for
  amplitude overstates damage by a factor of two.
- Omitting half-cycles from the residual stack — they carry 0.5 cycle
  weight each and must be included in the Miner summation; dropping them
  unconservatively understates cumulative damage.

## Behavior contract (gate 3)

The stress conversion, turning-point extraction, rainflow cycle counting,
Goodman correction, spectrum aggregation, and critical-location selection
logic is exercised by the gate 3 contract test:
scripts/test_stress_spectrum_derivation.py against
scripts/stress_spectrum_derivation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_stress_spectrum_derivation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
