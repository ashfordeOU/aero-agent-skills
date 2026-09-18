---
name: e2020-parallel-limiter-operation-allowance
description: "Assess whether a proposed parallel group of latching and high power limiters sits inside the allowance to wire such limiters in parallel, per clause 5.2.12.1.1 of ECSS-E-ST-20-20C. Use when several limiters feed one load together: hold the group to one limiter family and one part reference, measure how far the member limiting thresholds spread apart, check the members are switched as one and read back individually, refuse a retriggerable or foldback device this allowance never covered, and compare the summed group limit after margin against the declared demand. Trigger: ecss, e-st-20-20c-clause-5-2-12-1-1, parallel-limiter-operation-allowance, paralleled-limiter-group-homogeneity, parallel-limiter-threshold-spread, parallel-group-common-command, parallel-group-limit-margin."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-12-1-1, e2020-parallel-limiter-operation-allowance, paralleled-limiter-group-homogeneity, parallel-limiter-threshold-spread, parallel-group-common-command, parallel-group-limit-margin, parallel-limiter-departure-justification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution -- Parallel Limiter Operation Allowance (space-systems/ecss/e2020-parallel-limiter-operation-allowance)

Use when the task is clause 5.2.12.1.1 of ECSS-E-ST-20-20C: a latching
current limiter and a high power limiter may be operated in parallel.
The clause grants a permission, and a permission is the easiest kind of
clause to misread in both directions -- as a prohibition that never
existed, or as a blank cheque that lets any two devices share a node.
This leaf holds the middle: the group is allowed, provided it behaves
as one device.

## Domain quick reference

- The allowance covers latching current limiters and high power
  limiters. A retriggerable limiter recovers on its own schedule, a
  foldback device reduces rather than removes current, and a series fuse
  does not come back at all; each shares current by a different law, so
  feeding one into this assessment grades the wrong part.
- One family is not the same as one part. Two limiters of the same
  family from different part references have different limiting laws in
  practice: they drift apart over temperature and over life, and the one
  that trips lowest takes the fault alone every time.
- Threshold match is measured as a spread, not as a pairwise average.
  The number that matters is how far the highest member threshold sits
  above the lowest, because that gap is what decides which member sees
  the fault first.
- A parallel group that is not switched as one can be left part-on. The
  survivors then carry a load sized for the whole group, which is a
  worse condition than the one the parallel arrangement was built to
  avoid.
- Individual status readout is what makes a dropped member visible. A
  group reported only as a whole looks healthy right up to the moment
  the last member goes, because the survivors cover for the losses.
- The member ceiling is a real limit, not a style preference. Every
  added member widens the spread the group has to tolerate and adds one
  more device that can fail on.
- A group that misses a condition is not forbidden. It is a departure
  the project owns, argued with a recorded rationale and at least one
  named verification activity -- the parallel arrangement shown to work,
  not asserted to.
- Capability is judged after margin. The summed limiting threshold of
  the group, derated by the declared margin, is what the load may draw
  against; a group that only just covers the demand has no room for the
  sharing loss the next clause quantifies.

## Workflow

1. Validate the policy: threshold spread tolerance, member ceiling,
   group limit margin, and whether common command and individual status
   are required.
2. Take the first member as the group reference -- its family, part
   reference and limiting threshold.
3. Refuse a limiter type the allowance never covered before reading
   anything else about it.
4. Hold each member to the reference in order: family, part reference,
   threshold spread, common command, individual status. The first
   condition a member misses is the standing it carries.
5. Count the members against the ceiling and record an oversize group.
6. Sum the member thresholds, hold back the margin, and compare the
   result with the declared load demand.
7. If the group is not homogeneous, test the departure argument: a
   rationale with real content and a named verification activity.
8. Rank the group at its worst standing -- capability short, outside the
   allowance, departure argued, allowance met -- and roll up each
   finding under the member that produced it.

## Pitfalls

- Reading the clause as a prohibition and writing a non-conformance
  against every parallel group. Parallel operation is permitted; the
  finding is the missing condition, not the topology.
- Reading it as unconditional and writing nothing. A pair of unmatched
  parts sharing a node is exactly what the conditions exist to surface.
- Matching on family alone. Two latching limiters from different part
  references are two different devices in every way that decides which
  one trips first.
- Averaging the member thresholds. The average hides the spread, and the
  spread is the whole question.
- Grading a retriggerable or foldback device here. It shares current by
  a different law, so the verdict is confidently wrong.
- Sizing the group limit without margin, then discovering in the sharing
  assessment that the worst branch has no headroom left.
- Accepting a group-level status readout as individual status. A group
  that reports only its own health cannot show a member that dropped out.

## Behavior contract (gate 3)

The covered and refused limiter types, the group reference taken from
the first member, the ordered member conditions with family, part
reference, threshold spread, common command and individual status, the
spread measured above the lowest threshold, the member ceiling, the
summed group limit after margin against the declared demand, the
two-part departure argument, and the worst-standing group verdict are
exercised by the gate 3 contract test:
scripts/test_e2020_parallel_limiter_operation_allowance.py against
scripts/e2020_parallel_limiter_operation_allowance_logic.py (stdlib
unittest, offline).
Run: python3 scripts/test_e2020_parallel_limiter_operation_allowance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
