---
name: q6005-active-chip-bondability-test
description: "Verify wire-attachment strength on the bond pads of active dies before they are released into assembly. Use when a die lot's bondability evidence has to be graded: interpolate the minimum pull force the wire diameter earns from the strength schedule, hold every individual reading against that floor at the exact boundary, hold the lot mean against its own higher floor, disposition each recorded separation mode so a pad-lift or cratering event fails the lot whatever force it took, confirm the tested bond count meets the sampling floor, and call the lot bondable only when no finding remains. Trigger: ecss, q-st-60-05, active-chip-bondability, active-die-wire-bond-pull-force, bond-pad-lift, die-cratering, pull-strength-schedule, active-chip-bondability-sample-size, pre-assembly-die-acceptance."
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
  tags: [ecss, q-st-60-electronic-components-scope, q6005-active-chip-bondability-test, active-chip-bondability, active-die-wire-bond-pull-force, bond-pad-lift, die-cratering, pull-strength-schedule, active-chip-bondability-sample-size, pre-assembly-die-acceptance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Generic Procurement of Active Chips — Active Chip Bondability Test (space-systems/ecss/q6005-active-chip-bondability-test)

Use when the task is the bondability demonstration of ECSS-Q-ST-60-05
clause 8.3.2 -- showing, on sample dies drawn from a lot and before any
of that lot reaches an assembly, that a wire attached to the bond pads
actually holds.

## Domain quick reference

- The demonstration is destructive and it happens upstream of assembly.
  A lot that is already mounted cannot be made bondable retroactively;
  the evidence has to exist before the dies are released.
- A pull reading is only meaningful against the floor its own wire
  diameter earns. A thin wire reaching 3 gf and a thick wire reaching
  3 gf are not the same result, so the floor comes from a strength
  schedule indexed by nominal diameter and is interpolated between
  tabulated anchors. A diameter outside the tabulated span has no floor
  and must not silently borrow a neighbouring one.
- Because an interpolated floor is a float expression, a reading that
  sits exactly on its floor can evaluate a few ULPs low. The comparison
  absorbs that representation error; the schedule floor itself is never
  relaxed to make a lot pass.
- Force alone does not decide the reading. Where the separation
  happened decides it. A break inside the wire -- at the heel, the neck
  or mid-span -- means the attachment outlived the wire, so the number
  grades bond strength. A separation at the pad interface -- bond lift,
  pad lift, cratering, metallization peel -- means the attachment or
  the die metallization gave way, and no amount of force redeems it.
- The lot mean carries a margin over the individual floor. A lot whose
  mean sits on the individual floor has roughly half its population
  below that floor, so the mean is held against the worst per-reading
  floor multiplied by the margin factor.
- A bondability statement needs a population behind it. Below the
  sampling floor the readings describe a handful of bonds, not the lot,
  and the sample size is itself a finding.

## Workflow

1. Normalize every pull record: pad identifier, nominal wire diameter,
   pull force and the recorded separation mode. Reject a missing pad
   identifier, a non-numeric or negative force, an unrecognised
   separation mode and a duplicate record for one pad.
2. Derive each reading's floor from the strength schedule, exact at a
   tabulated anchor and linearly interpolated between two of them.
3. Compare each reading with its floor under the boundary tolerance and
   record the shortfall in grams-force where it falls short.
4. Group each separation mode as structural or interface. An interface
   separation makes the reading non-conforming whatever force it
   reached, and its pad is listed separately.
5. Compute the lot mean and sample standard deviation of the readings,
   then hold the mean against the worst per-reading floor times the
   margin factor.
6. Compare the tested bond count with the sampling floor and raise it
   as a finding in its own right when the count falls short.
7. The lot is bondable only when no reading is short, no separation
   happened at an interface, the mean clears its floor and the sample
   size is adequate.

## Pitfalls

- Grading every reading against one number because the lot uses "the
  same wire" -- a mixed-diameter lot has mixed floors, and one shared
  floor either passes a thin wire that failed or fails a thick wire
  that passed.
- Recording the force and discarding the separation mode -- a pad-lift
  at 40 gf reads as the strongest bond in the set and is in fact the
  only unsound one.
- Reading a healthy lot mean as a verdict and never checking the
  individual readings -- a mean comfortably above the floor hides the
  low tail that will fail in flight.
- Lowering the schedule floor because a reading lands exactly on it --
  the shortfall is interpolation representation error and belongs in
  the comparison tolerance, not in the schedule.
- Quoting a bondability result from three or four bonds pulled during a
  process set-up -- the sampling floor exists so the statement
  describes the lot rather than the set-up.
- Running the pull test after the dies are mounted, because it is
  easier to get at them there -- the clause places the demonstration
  before assembly release, and a destructive test on mounted dies
  proves nothing about the ones already attached.

## Behavior contract (gate 3)

The schedule interpolation, boundary tolerance, separation-mode
grouping, record normalization, lot statistics and sampling-floor logic
is exercised by the gate 3 contract test:
scripts/test_q6005_active_chip_bondability_test.py against
scripts/q6005_active_chip_bondability_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_active_chip_bondability_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
