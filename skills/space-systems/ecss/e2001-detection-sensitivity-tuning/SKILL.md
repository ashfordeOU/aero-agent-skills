---
name: e2001-detection-sensitivity-tuning
description: "Use when calibrate and schedule the phase-nulling tuning that holds multipactor global-detection at its sharpest under ECSS-E-ST-20-01C clause 7.3.2: turn the residual carrier leaking past the nulling bridge into a null-depth, derive that null-depth from the residual phase-error and amplitude-imbalance of the cancellation arm, propagate both along their drift rates until the null-depth sinks under the detection floor the verification-plan asks for, size the longest admissible re-tuning interval from that crossing, and grade a recorded tuning schedule for gaps that left the global-detection chain desensitised while radio-frequency-power was applied. Trigger: ecss, e-st-20-01c, detection-sensitivity-tuning, phase-nulling-bridge, null-depth-drift, amplitude-imbalance, re-tuning-interval, global-detection-floor."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-detection-sensitivity-tuning, detection-sensitivity-tuning, phase-nulling-bridge, null-depth-drift, amplitude-imbalance, re-tuning-interval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor Design and Test — Detection Sensitivity Tuning (space-systems/ecss/e2001-detection-sensitivity-tuning)

Use when the task is the phase-nulling tuning duty of ECSS-E-ST-20-01C
clause 7.3.2 -- keeping a global multipactor detection chain at its
sharpest by re-nulling it often enough that the residual carrier never
climbs far enough to hide the perturbation a discharge produces.

## Domain quick reference

- A phase-nulling global detector cancels the forward carrier against a
  reference arm and watches what survives. The surviving residual sets
  the detection floor: the deeper the null, the smaller the discharge
  perturbation that rises above it. Null-depth is therefore the single
  number that expresses detection sensitivity for this method, and it
  is read as the ratio of incident to residual carrier expressed in dB.
- Null-depth is not a free parameter. It is fixed by how closely the two
  arms match, in phase-error (radians of residual phase mismatch) and in
  amplitude-imbalance (dB of residual level mismatch). For a two-arm
  cancellation the residual fraction is 1 + a^2 - 2a cos(phi), with
  a the linear amplitude ratio and phi the phase-error; a perfect match
  drives that fraction to zero and the null-depth to unbounded. A tenth
  of a dB of imbalance, or a hundredth of a radian of phase-error, is
  already enough to cap the null in the high-thirties dB.
- Both mismatches drift while the run is powered: chamber temperature
  moves cable electrical length, radio-frequency-power heats the
  cancellation arm, mechanical settling moves connectors. Treating the
  drift rates as magnitudes per second makes null-depth a monotonically
  decreasing function of the elapsed time since the last tuning, so the
  moment it crosses the required floor is unique and can be solved for.
- That crossing is the longest admissible re-tuning interval. A schedule
  whose gaps all sit at or under it kept the detector at full
  sensitivity for the whole powered run; a schedule with one longer gap
  ran desensitised across that gap, and any discharge inside it was
  observed with a detector that no longer met its own floor.
- The floor itself comes from the verification-plan, not from this leaf:
  it is the null-depth the plan committed the global-detection method to
  hold. A run with no floor on record is a finding, not a pass.

## Workflow

1. Establish the null-depth actually achieved at the last tuning, either
   from the measured incident and residual carrier levels or from the
   residual phase-error and amplitude-imbalance of the cancellation arm.
   Reject a residual that exceeds the incident carrier.
2. Compare that fresh null-depth against the floor the verification-plan
   set. A chain that cannot meet its floor even immediately after tuning
   is a hardware finding -- re-tuning cadence cannot repair it, and the
   interval calculation is meaningless until it is fixed.
3. Propagate the phase-error and amplitude-imbalance forward along their
   drift rates and solve for the elapsed time at which the null-depth
   reaches the floor. With both drift rates zero the null holds
   indefinitely and no cadence is imposed.
4. Categorise which mismatch drives the decay over that interval -- phase
   dominated, amplitude dominated, or balanced -- so the corrective
   action lands on the right hardware (line length and thermal lagging
   versus attenuator and coupler stability).
5. Grade the recorded tuning schedule against the interval: a tuning at
   run start, every successive gap at or under the interval, and a final
   gap from the last tuning to the end of the powered run also at or
   under it.
6. Aggregate the findings. The detection chain is sensitivity-compliant
   for the run only when the fresh null-depth met the floor and the
   schedule left no uncovered gap.

## Pitfalls

- Reading a deep null once at set-up and treating it as valid for the
  whole run. Null-depth is a decaying quantity; the number that matters
  is the worst value reached inside each gap, which is the value at the
  end of the gap, not the value at its start.
- Averaging phase-error and amplitude-imbalance into one "mismatch"
  figure. They enter the residual through different terms -- one through
  cos(phi), the other through the linear ratio -- so the mix decides
  which hardware to stabilise, and collapsing them hides that.
- Widening the floor because a gap came out a few milliseconds long. The
  floor is a verification-plan commitment; absorb representation error in
  the comparison, never in the engineering limit.
- Scheduling tuning by clock convenience (every hour, at each break)
  rather than from the drift-derived interval, then reporting the run as
  fully monitored. A convenient cadence that is longer than the crossing
  leaves every gap partly blind.
- Treating a missing floor as "no requirement, therefore compliant". An
  absent detection floor means the verification-plan commitment was never
  captured, which is itself the finding.

## Behavior contract (gate 3)

The null-depth, imbalance-drift, re-tuning-interval and schedule-grading
logic is exercised by the gate 3 contract test:
scripts/test_e2001_detection_sensitivity_tuning.py against
scripts/e2001_detection_sensitivity_tuning_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_detection_sensitivity_tuning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
