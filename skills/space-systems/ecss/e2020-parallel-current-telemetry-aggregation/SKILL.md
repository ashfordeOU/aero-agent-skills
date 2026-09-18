---
name: e2020-parallel-current-telemetry-aggregation
description: "Verify that the current telemetry of a paralleled limiter group reports the total current the group is passing, per clause 5.2.12.5.1 of ECSS-E-ST-20-20C. Use when one reading has to stand for several limiters at once: sum every member into the group total, name a member the aggregation was never told about, decide whether a full scale sized for a single member now saturates on the group, combine the member sensing errors into the error on the reported total, and keep a saturated range apart from an accuracy shortfall because the two are different design decisions. Trigger: ecss, e-st-20-20c-clause-5-2-12-5-1, paralleled-limiter-current-telemetry, group-total-current-reporting, telemetry-full-scale-saturation, limiter-group-telemetry-accuracy, omitted-member-current-contribution."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-12-5-1, e2020-parallel-current-telemetry-aggregation, paralleled-limiter-current-telemetry, group-total-current-reporting, telemetry-full-scale-saturation, limiter-group-telemetry-accuracy, omitted-member-current-contribution]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution -- Paralleled Limiter Current Telemetry Aggregation (space-systems/ecss/e2020-parallel-current-telemetry-aggregation)

Use when the task is clause 5.2.12.5.1 of ECSS-E-ST-20-20C: the current
telemetry of limiters placed in parallel reports the total current
flowing through the group. One number has to stand for several limiters
at once, and this leaf grades the three separate ways that number stops
standing for the group -- coverage, range and accuracy -- rather than
reading a single pass or fail off the channel.

## Domain quick reference

- Coverage is the first question and it is not an accuracy question. A
  member the aggregation was never told about contributes its whole
  current to what the group passes and nothing to what the channel
  reports. That is a fixed under-report no sensor budget covers, so it
  outranks every other finding on the channel.
- Paralleling raises the current one reading has to span. A channel
  whose full scale was inherited from a single member stops moving with
  the group and holds at the top of its range, and a held reading looks
  perfectly healthy in a limit check because it never moves.
- A reading exactly at full scale is not yet saturated. Saturation
  begins where the group total goes past the scale, so the comparison at
  that boundary is an equality question and is handled with a tolerance,
  not by trimming the range.
- Independent member errors combine root-sum-square, so the fractional
  error on the group total comes out below the worst member's own. A
  project that combines worst case instead is making a correlation
  assumption, and the rule it picked belongs in the policy where a
  reviewer can see it.
- Range margin is not the same question as saturation. A channel that
  clears the group total by a hair reports correctly today and runs off
  scale on the first transient, so the margin floor is graded on its
  own, below the shortfalls that are already wrong.

## Workflow

1. Validate the policy: the error budget is a fraction below one, the
   range margin floor is not negative, and the error combination rule is
   one the project recognises.
2. Read each member into its current, its sensing accuracy and whether
   the aggregation includes it; refuse a duplicate member, a negative
   current and a set too small to be a parallel group.
3. Sum the members twice -- every member for the group total, the
   included members for what the channel aggregates -- and name the
   difference by member rather than reporting it as an error.
4. Hold the aggregate at full scale to get the reported number, and mark
   the channel saturated only where the aggregate goes past the scale,
   absorbing representation error at that boundary with a named
   tolerance.
5. Compute the reported error against the group total, the range margin
   above it and the combined sensing accuracy under the declared rule.
6. Rank the channel at its worst standing: an omitted member first, then
   a saturated range, then an accuracy shortfall, then a thin range
   margin, then the group total reported.
7. Report both sums, the reported number, the margin, the combined
   accuracy and every finding, naming the members involved.

## Pitfalls

- Folding an omitted member into the accuracy budget. Leaving a limiter
  out is a missing term, not a wider error bar, and no improvement in
  the remaining sensors ever recovers it.
- Carrying the single-limiter full scale into the paralleled design. The
  group passes the sum, and a channel that saturates reports a steady,
  plausible number that no longer follows the hardware.
- Reading a saturated channel as an accuracy problem. The first is
  solved by re-ranging the measurement and the second by a better
  sensor, and merging them sends the work to the wrong place.
- Taking the worst member's accuracy as the accuracy of the total.
  Independent errors combine root-sum-square over a larger total, so the
  aggregate is better than its worst member, and assuming otherwise buys
  sensors the design did not need.
- Treating a full scale that sits exactly on the group total as a pass.
  Nothing is clipped at that point, but nothing is left either, and the
  first transient on one member runs the reading off scale.
- Widening the error budget to absorb an exact-equality case. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the budget stays as specified.

## Behavior contract (gate 3)

The policy validation, the member normalization, the two sums that
separate the group total from what the channel aggregates, the omitted
members named individually, the full-scale hold and its boundary, the
range margin, the root-sum-square and worst-case error combinations and
the worst-standing channel verdict are exercised by the gate 3 contract
test:
scripts/test_e2020_parallel_current_telemetry_aggregation.py against
scripts/e2020_parallel_current_telemetry_aggregation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_parallel_current_telemetry_aggregation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
