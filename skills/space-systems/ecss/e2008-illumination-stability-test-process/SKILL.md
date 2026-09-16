---
name: e2008-illumination-stability-test-process
description: "Use when auditing or planning a continuous simulated-sunlight soak. Verify that an illumination stability soak on photovoltaic samples was run the way ECSS-E-ST-20-08C clause 6.4.3.12.2 requires: check the simulator on total irradiance against the solar reference, on plane uniformity and on temporal stability, accumulate illuminated time over every segment, find the longest unbroken stretch once gaps inside the interruption allowance are bridged, confirm each segment held the controlled reference temperature, and refuse a two-day soak assembled from separate days or missing its before or after electrical measurement. Trigger: ecss, e-st-20-08c, clause-6-4-3-12-2, continuous-simulated-sunlight-soak, two-day-illumination-soak-continuity, solar-simulator-plane-uniformity, soak-temperature-control-window, soak-interruption-allowance."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-illumination-stability-test-process, continuous-simulated-sunlight-soak, two-day-illumination-soak-continuity, solar-simulator-plane-uniformity, soak-temperature-control-window, soak-interruption-allowance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Illumination Stability Test Process (space-systems/ecss/e2008-illumination-stability-test-process)

Use when the task is the clause 6.4.3.12.2 test process of ECSS-E-ST-20-08C
-- judging whether samples were actually held under continuous simulated
sunlight at a controlled temperature for two days: under light that is
sunlight rather than merely bright, for a stretch that was unbroken rather
than merely long in total, at the reference temperature, and bracketed by
the electrical measurements that turn a soak into a test.

## Domain quick reference

- A solar simulator is graded on three independent axes: how close its total
  irradiance sits to the reference solar constant, how evenly that
  irradiance falls across the sample plane, and how steadily it holds over
  the soak. A lamp an hour from the end of its life can meet the first and
  fail the third, so one number never settles the light.
- Continuity is the whole point of the requirement. Illuminated segments
  separated by darkness are not one soak: carrier injection stops,
  metastable defects relax and the article partially recovers, so the second
  segment begins from a state the first did not leave it in.
- That makes the arithmetic total the wrong statistic. Two twenty-four hour
  segments a week apart are two one-day soaks; the run is graded on the
  longest unbroken chain, with only gaps inside a declared interruption
  allowance -- a lamp change, a brief trip -- bridged rather than breaking it.
- Temperature control is not chamber housekeeping. Output moves with
  temperature far faster than with illumination history, so a segment that
  drifted off the reference temperature contributes drift that cannot be
  separated afterwards from the light-driven drift being looked for.
- The plane matters as much as the lamp. Irradiance falls off away from the
  optical axis, so samples at the edge of a crowded plane can take a
  materially weaker soak while the record shows one exposure for all of them.
- The stability figure is a ratio. Without the pre-soak reference the
  post-soak output is an absolute number with nothing to divide by, and the
  run produces no stability result at all.

## Workflow

1. Validate the soak policy first: required continuous duration, reference
   irradiance and its band, plane uniformity and temporal stability
   allowances, interruption allowance and the temperature window. An
   irradiance band reaching down to darkness is refused rather than used.
2. Put the segment list in run order and reject an overlap or a segment that
   ends before it starts; an ambiguous timeline cannot be accumulated.
3. Grade the simulator itself -- plane spread and temporal stability -- before
   any duration arithmetic, because both invalidate the whole soak at once.
4. Screen every segment for irradiance against the reference band and for
   temperature against the control window. An off-condition segment is a
   finding even when the accumulated hours are exactly right.
5. Accumulate total illuminated hours, then compute the longest unbroken
   stretch with gaps inside the interruption allowance bridged. Report both:
   the difference between them is the continuity evidence.
6. Compare against the required duration with the tolerance absorbing
   representation error rather than lowering the requirement. A soak landing
   exactly on the required duration is met.
7. Close on one verdict -- soak conditions violated, soak duration shortfall,
   soak not continuous, characterisation incomplete, or illumination soak
   conforms -- reporting every finding raised, not only the deciding one.

## Pitfalls

- Summing segments into a two-day total. The requirement is for an unbroken
  exposure, and a total assembled from separate days hides exactly the dark
  recovery that makes those days separate.
- Accepting the lamp on its rated output. Rated irradiance says nothing
  about the spread across the plane or the drift over forty-eight hours, and
  either can move the result more than the effect being measured.
- Letting the chamber settle wherever it settles. The thermal coefficient
  dominates the light-driven drift, so an uncontrolled segment writes a
  thermal term into the answer that no later analysis can subtract.
- Taking only the post-soak measurement. The stability figure is a ratio and
  a reference taken from a sibling sample is a different article's number.
- Reporting one irradiance for a crowded plane. Edge samples then carry an
  unstated exposure error into every stability figure drawn from them.

## Behavior contract (gate 3)

The policy validation, segment ordering and overlap rejection, illuminated
hour accumulation, interruption gaps and longest continuous stretch, the
simulator plane uniformity and temporal stability checks, the per-segment
irradiance and temperature screening, the characterisation inventory and the
run verdict are exercised by the gate 3 contract test:
scripts/test_e2008_illumination_stability_test_process.py against
scripts/e2008_illumination_stability_test_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_illumination_stability_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
