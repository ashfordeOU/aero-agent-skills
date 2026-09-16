---
name: e2008-blocking-diode-temperature-robustness
description: "Use when a temperature extreme exposure of blocking diodes is planned or read back. Verify that blocking diode devices come through exposure at the temperature extremes of service under ECSS-E-ST-20-08C clause 12.6.10: hold each soak past the service extreme by the declared margin and short of the package storage rating, hold the dwell and the transition rate against their limits, refuse a programme that covers only one end, grade each device on forward drop drift and reverse leakage growth, and take the share that came through. Trigger: ecss, e-st-20-08c-clause-12-6-10, blocking-diode-temperature-extreme-exposure, blocking-diode-soak-margin-beyond-service-extreme, blocking-diode-post-exposure-parameter-drift, blocking-diode-exposure-dwell-and-ramp, blocking-diode-exposure-survivor-fraction."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-temperature-robustness, blocking-diode-temperature-extreme-exposure, blocking-diode-soak-margin-beyond-service-extreme, blocking-diode-post-exposure-parameter-drift, blocking-diode-exposure-dwell-and-ramp, blocking-diode-exposure-survivor-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes -- Temperature Extreme Robustness (space-systems/ecss/e2008-blocking-diode-temperature-robustness)

Use when the task is clause 12.6.10 of ECSS-E-ST-20-08C -- showing that a
blocking diode still works after it has been taken to the ends of its
service environment and held there. This is not the temperature map. A
sweep passes through the cold end on its way somewhere else; an exposure
sits at it long enough for the die attach, the bonds and the encapsulant
to take up the strain, and the device is then measured against what it
was before.

## Domain quick reference

- The soak goes past the extreme, not to it. A soak that stops exactly
  at the coldest temperature the mission predicts demonstrates the
  nominal case and leaves nothing for a prediction that was optimistic.
  The margin is declared and the soak is held against the extreme plus
  that margin.
- It also stops short of the storage rating. A soak driven past what the
  part is rated to store is a destructive test wearing a service name,
  and a device that fails it has said nothing about flight.
- Those two bounds together define the window, and a plan is checked
  against the rating first. A soak that is both too shallow for service
  and past the rating is a rating finding; reporting the margin instead
  sends the bench in the wrong direction.
- Both ends are required. Hot exposure drives diffusion and
  intermetallic growth at the interfaces; cold exposure drives
  differential contraction between materials that shrink at different
  rates. A programme that covers one end has looked at one mechanism.
- Dwell is what separates an exposure from a visit. A device that
  reached the soak temperature and came straight back never gave the
  joints time to take the strain up.
- Transition rate matters for the opposite reason. Ramped fast enough,
  the run stops being an exposure at an extreme and becomes a thermal
  shock, which is a different test with a different acceptance.
- Survival is read from before and after, not from appearance. The
  forward drop is graded as a share of what it was, because a shift of
  a few tens of millivolts means different things on different parts.
- Leakage is graded as a ratio and never as a difference. It spans
  decades across a lot, so a growth that is negligible on a leaky part
  is a total failure on a tight one.
- The sample floor is separate from the survival criterion. Every
  device coming through intact says nothing about the lot when only two
  were exposed.

## Workflow

1. Validate the exposure policy first: the two soak margins, the dwell
   floor, the ramp ceiling, the sample floor, the drift and growth
   limits and the required share. A growth limit below one, which would
   demand the exposure improve the device, is refused.
2. Read the declared service range and the package storage rating,
   refusing an inverted or empty one of either.
3. Read each planned exposure: which end it sits at, its soak
   temperature, its dwell and its transition rate. An extreme that is
   neither the cold nor the hot end is refused.
4. For each exposure take the achieved margin past the service extreme
   and the soak temperature the declared margin asks for.
5. Grade each exposure: against the storage rating first, then the
   service margin, then the dwell floor and the ramp ceiling. Collect
   every finding across every exposure before closing, so the plan is
   not repaired one soak at a time.
6. With the plan sound, check both service extremes are covered and
   close when either is missing.
7. Grade each exposed device on its forward drop drift and its leakage
   growth ratio, refusing a duplicate device identifier, and record the
   reasons behind every degraded verdict.
8. Take the share that came through intact, hold the device count
   against the sample floor before holding that share against its
   requirement, and close on one verdict: exposure plan invalid, service
   extreme not covered, sample below floor, devices degraded, or
   robustness demonstrated.

## Pitfalls

- Soaking to the predicted extreme. The prediction carries its own
  uncertainty, and a soak with no margin over it demonstrates only the
  case that was predicted.
- Reaching for the package rating as the soak temperature. It is the
  ceiling on the test, not its target, and a run at the rating measures
  the limits of the part rather than the margin of the mission.
- Covering the hot end only because it is the easier chamber run. The
  cold end fails through contraction mismatch, which the hot run cannot
  provoke.
- Counting a thermal cycle as an exposure. A cycle that touches the
  extreme and leaves is a different stress with a different dwell, and
  substituting it quietly drops the hold this clause is about.
- Ramping fast to save chamber time. Past the declared rate the run is
  a shock test and its result belongs to a different acceptance.
- Reading survival off a visual inspection. Junction degradation and
  leakage growth are not visible, so the inspection passes devices the
  measurement would have caught.
- Grading leakage by subtraction. A growth of a tenth of a microamp is
  nothing on one part and a tenfold failure on another.
- Reporting a full survivor share from a sample of two. The share is
  only as strong as the count behind it, which is why the floor is
  checked before the share.
- Comparing a margin, a dwell or a ramp against its limit by bare
  arithmetic. All three are differences or quotients of declared
  numbers, so a plan written exactly to a limit can land in the last
  place the wrong side of it; the comparison absorbs that while the
  limit stays as written.

## Behavior contract (gate 3)

The policy validation, the service range and storage rating reading, the
required soak temperature and achieved margin at both ends, the storage
rating bound, the dwell and ramp checks, the two-extreme coverage test,
the forward drift share and leakage growth ratio per device with its
duplicate-identifier refusal, the survivor share against the sample
floor and its requirement, and the single programme verdict are exercised
by the gate 3 contract test:
scripts/test_e2008_blocking_diode_temperature_robustness.py against
scripts/e2008_blocking_diode_temperature_robustness_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_temperature_robustness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
