---
name: e2021-actuation-output-performance-verification
description: "Verify that the firing current and output voltage an actuator electronics actually delivered meet the limits declared for its interface, per clause 5.5.1 of ECSS-E-ST-20-21C. Use when a measured pulse record has to become a verdict rather than a waveform: take the held plateau of each firing pulse instead of its overshoot or its mean, push the measurement uncertainty in the direction that works against the case rather than the one that flatters it, grade current and voltage against their own floors and ceilings, take the worst channel instead of the average of the set, and name which of the two quantities fell short. Trigger: ecss, e-st-20-21c, actuation-output-performance, delivered-firing-current, output-voltage-limits, firing-pulse-plateau, measurement-uncertainty-direction, worst-channel-verdict."
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
  tags: [ecss, e-st-20-21-actuator-interface-scope, e-st-20-21c-clause-5-5-1, e2021-actuation-output-performance-verification, e-st-20-21c, actuation-output-performance, delivered-firing-current, output-voltage-limits, firing-pulse-plateau, measurement-uncertainty-direction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuator Interface — Actuation Output Performance Verification (space-systems/ecss/e2021-actuation-output-performance-verification)

Use when the task is clause 5.5.1 of ECSS-E-ST-20-21C: the firing current
an actuator electronics delivered and the output voltage it presented
have to be shown against the limits its interface declares. This leaf
reads one measured firing record and returns the verdict with the
uncertainty already applied in the direction that works against it.

## Domain quick reference

- The actuator having moved is not the verification. The clause bounds
  two electrical quantities at the interface, and a firing that
  functioned while the current sat outside its band has demonstrated the
  actuator's tolerance, not the electronics' compliance.
- A firing pulse is a shape, and the limits apply to the held part of it.
  The rise and fall carry values the interface was never specified
  against, so the delivered figure is taken over the plateau: the samples
  at or above a declared fraction of the pulse peak, and enough of them
  that a plateau exists at all.
- A single peak sample is not a plateau. Reading the overshoot as the
  delivered current inflates the figure against a floor and deflates the
  case against a ceiling, which is why a pulse that never holds is
  refused rather than graded on its tallest point.
- Measurement uncertainty has a direction, and the direction depends on
  the limit under test. Against a floor the reading is taken at its
  lowest credible value; against a ceiling at its highest. The same
  reading therefore produces two working values, and a channel is inside
  its band only when both of them are.
- Current and voltage are independent conditions. A channel can deliver
  the required current into a low-resistance actuator while presenting
  an output voltage below its band, which points at the drive stage
  rather than at the load, so the report says which of the two failed and
  by what fraction of its own limit.
- The verdict belongs to the worst channel. A mean over a set of firing
  lines lets a good channel pay for a bad one, and one channel outside
  its limits holds the verification however comfortable the rest are.

## Workflow

1. Validate the declared limits: a current floor below its ceiling, a
   voltage floor below its ceiling, a plateau fraction inside the unit
   interval and a minimum plateau sample count of at least one.
2. Resolve each channel's two readings. Take a directly declared value,
   or reduce a sample set to its plateau, but refuse a channel that
   declares both for the same quantity rather than silently preferring
   one.
3. Form the two working values for each reading by applying the declared
   uncertainty toward the floor and toward the ceiling.
4. Grade the low working value against the floor and the high working
   value against the ceiling, absorbing floating-point representation
   error at an exact match with a named tolerance rather than by
   relaxing either limit.
5. Report the shortfall and the excess in engineering units and as a
   fraction of the limit each was measured against, so a current miss
   and a voltage miss can be compared.
6. Name the dominant shortfall for the channel: the quantity whose
   fractional miss is larger when both fail, and the failing quantity
   when only one does.
7. Grade the set on the channel with the least fractional headroom and
   return the finding list with the verification token.

## Pitfalls

- Reading the pulse peak as the delivered current. An overshoot lasting
  a few microseconds is not what the interface limits bound, and using
  it reports margin against the floor that the actuator never saw.
- Averaging the whole pulse including its rise and fall. That pulls the
  figure below the held value and can fail a channel that met its floor
  throughout the part of the pulse that matters.
- Applying the measurement uncertainty in the flattering direction, or
  not at all. A channel sitting exactly on a limit is then reported as
  compliant on a reading whose true value is as likely to be outside as
  inside.
- Grading only the current. The output voltage is a separate declared
  limit, and a drive stage sagging under load meets the current into a
  low-resistance actuator while presenting a voltage its interface does
  not permit.
- Verifying on the mean of a set of channels. The clause is a per-channel
  condition; a set average conceals the one line whose margin is gone.
- Widening a limit so an exact-equality case passes. An equality at the
  limit is a representation question, handled by the tolerance inside the
  comparison; the declared limit stays as specified.

## Behavior contract (gate 3)

The limit validation, plateau reduction, directional uncertainty,
floor and ceiling grading, dominant-shortfall naming and worst-channel
selection are exercised by the gate 3 contract test:
scripts/test_e2021_actuation_output_performance_verification.py against
scripts/e2021_actuation_output_performance_verification_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2021_actuation_output_performance_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
