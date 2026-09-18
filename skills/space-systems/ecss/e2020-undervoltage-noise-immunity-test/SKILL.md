---
name: e2020-undervoltage-noise-immunity-test
description: "Validate a noise immunity test that applies a defined voltage step to show an undervoltage trip does not react to bus noise, per clause 5.4.3.4.1 of ECSS-E-ST-20-20C. Use when a test specification has to be shown to demonstrate immunity rather than merely avoid a trip. Size the step from the declared noise and ripple envelope, check that the level before and after it both stay clear of the trip band so the step is a disturbance and not a genuine undervoltage, require a dwell that outlasts the detection chain so a pass is immunity and not an unfinished measurement, check the edge is as fast as the disturbance it stands for, and grade the recorded runs. Trigger: ecss, e-st-20-20c-clause-5-4-3-4-1, undervoltage-noise-immunity-test, undervoltage-trip-step-stimulus, noise-immunity-step-amplitude-sizing, undervoltage-test-dwell-adequacy, undervoltage-spurious-trip-immunity, undervoltage-step-edge-rate."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e-st-20-20c-clause-5-4-3-4-1, e2020-undervoltage-noise-immunity-test, undervoltage-trip-step-stimulus, noise-immunity-step-amplitude-sizing, undervoltage-test-dwell-adequacy, undervoltage-spurious-trip-immunity, undervoltage-step-edge-rate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Undervoltage Noise Immunity Test (space-systems/ecss/e2020-undervoltage-noise-immunity-test)

Use when the task is clause 5.4.3.4.1 of ECSS-E-ST-20-20C: a voltage step of
defined size is applied to show the undervoltage protection does not react to
noise. This leaf reads one stimulus definition, one disturbance envelope and
one detection chain, and decides whether a no-trip result from that test would
actually be evidence of immunity.

## Domain quick reference

- The step stands in for something. It represents the disturbance envelope the
  bus really carries — broadband noise plus ripple — so its size is derived
  from that envelope with a coverage factor, not chosen for convenience. A
  step smaller than the envelope demonstrates immunity to a gentler world than
  the one the unit flies in.
- Ripple is declared peak to peak and the step is one-sided. Only half the
  ripple figure belongs on the same side of the operating point as the step,
  and adding the whole of it oversizes the stimulus by the ripple amplitude.
- Both levels have to stay clear of the trip band. A step that reaches the
  threshold is not a noise stimulus at all; it is a genuine undervoltage, and
  a protection that trips on it is behaving correctly. The trip band starts at
  the threshold plus the sensing uncertainty, not at the threshold.
- Amplitude and clearance pull against each other, and that tension is the
  useful output. The largest step that still clears the band is fixed by how
  far the operating point sits above the threshold, so when the envelope
  demands more than that headroom the finding belongs to where the threshold
  was placed, not to the test.
- A dwell shorter than the detection chain's own response makes a no-trip
  result meaningless. The chain was still settling when the step was released,
  so the test recorded an unfinished measurement rather than an immune one.
  This is the confound that makes a badly written immunity test always pass.
- The edge rate matters as much as the amplitude. The sensing chain is a
  filter, and a step ramped in slowly is attenuated by exactly the element the
  test exists to stress, so the edge has to be at least as fast as the
  disturbance it represents.
- Immunity is a repeated result. A single application says nothing about a
  marginal comparator, and one trip anywhere across the set is enough to
  withdraw the claim.

## Workflow

1. Validate the threshold, the disturbance envelope, the stimulus and the
   detection chain response; reject a step that would take the bus to or below
   zero and a repetition count that is not a positive integer.
2. Build the trip band as the threshold plus the sensing uncertainty.
3. Size the required step from the noise envelope plus half the peak-to-peak
   ripple, inflated by the coverage factor.
4. Compute the headroom: how far the starting level sits above the trip band,
   which is the largest step that can still clear it.
5. Place the applied step: report the upper and lower levels, and record a
   finding when either sits inside the trip band.
6. Compare the applied amplitude with the required one, and compare the
   required one with the headroom — when the second comparison fails, no step
   satisfies both and the threshold placement is the finding.
7. Compare the dwell with the detection chain response times the dwell factor,
   and the edge slew with the disturbance slew.
8. Grade the recorded runs: at least as many as were declared, and none
   tripped. Return the verdict, the design soundness flag and the findings.

## Pitfalls

- Reading a no-trip result as immunity without checking the dwell. A step
  released before the sensing filter has settled cannot produce a trip
  whatever the comparator does, so the test passes by construction.
- Sizing the step to just miss the threshold. That makes the stimulus a
  function of where the threshold sits rather than of the noise the bus
  carries, and the resulting test gets weaker every time the threshold is
  raised.
- Forgetting the sensing uncertainty when placing the lower level. A step that
  ends a hair above the nominal threshold is inside the band as the hardware
  realises it, and the resulting trip reads as a protection defect.
- Adding the whole peak-to-peak ripple to the one-sided envelope. The step
  goes one way; half the ripple figure is what sits on that side.
- Applying the step once. A marginal comparator is marginal intermittently,
  and a single clean application is exactly the evidence that hides it.
- Blaming the test when the envelope exceeds the available headroom. That
  result is telling you the threshold sits too close to the operating point
  for the required immunity to be demonstrable at all, and rewriting the test
  to fit only buries the finding.

## Behavior contract (gate 3)

The threshold, envelope, stimulus and run validation, required amplitude from
the envelope and half the ripple, step level placement against the trip band,
headroom versus required amplitude, dwell against the detection chain, edge
slew against the disturbance slew, repetition minimum, run grading and the
verdict are exercised by the gate 3 contract test:
scripts/test_e2020_undervoltage_noise_immunity_test.py against
scripts/e2020_undervoltage_noise_immunity_test_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2020_undervoltage_noise_immunity_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
