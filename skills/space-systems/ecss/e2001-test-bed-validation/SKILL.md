---
name: e2001-test-bed-validation
description: "Use when execute the two-step validation an ECSS-E-ST-20-01C clause 8.3 multipactor test bed passes before the article is mounted: in step one drive the bed with a multipactor-free reference through-line across the whole applied-power sweep, confirm no detection channel registers an event, and check the bed onset-power headroom in decibels above the maximum applied-power; in step two install a reference sample of certified onset-power and confirm the measured onset sits inside the tolerance band and that every required detection channel registers it. Then verify the validation is still current, inside its validity window and not superseded by a later bed reconfiguration. Trigger: ecss, e-st-20-01c, test-bed-validation, two-step-validation, reference-through-line, reference-sample-onset, detection-channel-agreement, onset-power-headroom, validation-validity-window."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-test-bed-validation, two-step-validation, reference-through-line, reference-sample-onset, onset-power-headroom, detection-channel-agreement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor -- Two-Step Test Bed Validation (space-systems/ecss/e2001-test-bed-validation)

Use when the task is proving a multipactor test bed is fit to carry a verdict
under ECSS-E-ST-20-01C clause 8.3 -- a negative step that shows the bed itself
stays quiet over the whole applied-power sweep, and a positive step that shows
the bed detects a certified reference onset where it is known to be -- before
the article under investigation is installed.

## Domain quick reference

- The two steps answer two different failure modes and neither substitutes for
  the other. Step one is the negative control: it rules out a false positive,
  where a connector, window, bend or load inside the bed discharges and the
  event is attributed to the article. Step two is the positive control: it
  rules out a false negative, where the bed is blind and a genuine discharge
  passes unrecorded.
- Step one is run with a reference through-line whose own onset-power is far
  above the range of interest. The pass condition has two parts: no detection
  channel registers an event anywhere at or below the maximum applied-power,
  and the bed onset-power sits a required headroom in decibels above that
  maximum. A bed that is quiet only because the sweep stopped early has not
  demonstrated headroom.
- Step two is run with a reference sample whose onset-power is certified from a
  previous characterization. The measured onset must fall inside a symmetric
  tolerance band around the certified value, expressed in decibels because the
  quantity is a ratio, and every detection channel the procedure requires must
  register the event. One channel firing while a second stays silent is a
  sensitivity finding against that channel, not a pass by majority.
- Order is part of the requirement. Running the positive step first can seed a
  bed surface with the reference sample outgassing products and change what the
  negative step then measures, so a record whose steps are out of order is
  rejected rather than scored.
- A validation is a perishable result. It holds for a stated validity window
  from the date it was performed, and any reconfiguration of the bed after that
  date -- a changed amplifier, a re-made waveguide joint, a moved probe --
  supersedes it regardless of how much of the window remains.

## Workflow

1. Check the step record contains exactly the two steps and that the negative
   step precedes the positive one. Reject a record that is missing a step,
   duplicates one, or has them reversed.
2. Step one: walk the sweep points of the reference through-line run. Any
   detection channel registering an event at or below the maximum applied-power
   is a finding naming the channel and the point at which it fired.
3. Step one headroom: convert the ratio of the bed onset-power to the maximum
   applied-power into decibels and compare against the required headroom. A
   ratio that lands on the requirement within numerical tolerance passes; a
   bed onset-power that was never established is itself a finding.
4. Step two: convert the ratio of the measured onset-power to the certified
   reference onset-power into decibels and take its magnitude. Inside the
   tolerance band, including the band edge, the bed is sensitive; outside it,
   report the signed deviation so the direction (early or late detection) is
   visible.
5. Step two channels: confirm every required detection channel registered the
   reference event. Name each silent channel individually.
6. Currency: confirm the run date falls inside the validity window measured
   from the validation date, and that no bed reconfiguration is recorded after
   the validation date.
7. Aggregate. The bed is validated only when the step order, both steps and
   the currency check all return empty; otherwise report which of the two
   control directions failed so the repair is targeted.

## Pitfalls

- Reading a quiet step one as sufficient -- silence with no established bed
  onset-power proves only that the sweep found nothing, not that the bed has
  margin above the range the article will see.
- Averaging detection channels in step two -- a channel that stays silent on a
  certified reference event will stay silent on the article, and the aggregate
  hides exactly the blindness the positive step exists to find.
- Comparing onset powers as a difference in watt against a tolerance in
  decibel -- the tolerance band is a ratio and must be applied in the
  logarithmic domain before any comparison.
- Reusing a validation after a bed change because the validity window has not
  run out -- the window bounds drift, not reconfiguration; any hardware change
  after the validation date voids it immediately.
- Running the positive step first for convenience -- the reference sample can
  leave the bed in a different state, and the negative step then measures a
  bed that no longer exists.

## Behavior contract (gate 3)

The step-order, negative-step, headroom, reference-sample deviation,
detection-channel and validation-currency logic is exercised by the gate 3
contract test: scripts/test_e2001_test_bed_validation.py against
scripts/e2001_test_bed_validation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e2001_test_bed_validation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
