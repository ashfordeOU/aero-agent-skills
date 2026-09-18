---
name: e2020-parallel-current-sharing-accuracy
description: "Evaluate how paralleled latching and high power limiters divide a load current between them, and whether the branch taking the largest share keeps enough headroom to its own threshold, per clause 5.2.12.2.1 of ECSS-E-ST-20-20C. Use when a group carries a load together and no branch may trip off unexpectedly: turn measured branch currents into share fractions, measure the worst branch above the equal share, flag a starved branch the redundancy was sized on, and find the load at which the first branch reaches its threshold after margin. Trigger: ecss, e-st-20-20c-clause-5-2-12-2-1, paralleled-limiter-current-sharing, parallel-branch-share-imbalance, parallel-branch-trip-headroom, parallel-group-sharing-capability, parallel-branch-starved-share."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-12-2-1, e2020-parallel-current-sharing-accuracy, paralleled-limiter-current-sharing, parallel-branch-share-imbalance, parallel-branch-trip-headroom, parallel-group-sharing-capability, parallel-branch-starved-share]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution -- Paralleled Limiter Current Sharing Accuracy (space-systems/ecss/e2020-parallel-current-sharing-accuracy)

Use when the task is clause 5.2.12.2.1 of ECSS-E-ST-20-20C: limiters
wired in parallel have to be assessed on how accurately they share the
load current, so that none of them trips off when it was not meant to.
Parallel branches never share evenly -- on-resistance, harness drop and
threshold all differ -- and this leaf turns that inequality into the
numbers a reviewer can act on.

## Domain quick reference

- The share fraction is a branch current over the group total. An evenly
  sharing group of n branches sits at 1/n, and that equal share is the
  reference every other number here is measured against.
- Imbalance is asked at the worst branch, not averaged over the group.
  An average hides the branch that reaches its threshold first, which is
  the only branch the clause is about.
- A starved branch is a finding in the other direction. A branch far
  below an equal share contributes almost nothing, so the group carries
  fewer working branches than it was sized for and the redundancy was
  paid for without being received.
- Group capability is not the sum of the thresholds and not the smallest
  threshold. Each branch holds its measured share as the load grows, so
  the group reaches its first trip at the smallest threshold-over-share
  ratio across the branches, derated by the declared margin.
- Headroom is per branch and relative to that branch's own threshold. A
  branch sitting just under its threshold is one thermal excursion from
  tripping even when the group looks comfortable in aggregate.
- An unmeasured branch current is not a zero and not an equal share. It
  means the sharing was never established, which outranks sharing
  measured and found wanting, because one needs a measurement and the
  other needs a design change.
- Headroom outranks imbalance. A branch already out of headroom trips
  off whatever the sharing figures say, and the trip is the event the
  clause exists to prevent.
- A retriggerable limiter and a foldback device divide current by a
  different law, so neither belongs in this assessment.

## Workflow

1. Validate the policy: imbalance ceiling, starved-share floor, branch
   headroom floor and capability margin.
2. Refuse a limiter type this assessment does not cover before reading
   any current.
3. If any branch current is undeclared, stop the group at not-measured;
   each branch is still graded on the headroom that is knowable.
4. Turn the measured branch currents into share fractions and compute
   the equal share for the branch count.
5. Grade each branch in order: headroom first, then share above the
   imbalance ceiling, then share below the starved floor.
6. Find the smallest threshold-over-share ratio, derate it by the
   margin, and compare it with the declared load demand.
7. Rank the group at its worst standing -- not measured, a branch that
   will trip, capability short, imbalance out of band, acceptable -- and
   roll up each finding under the branch that produced it.

## Pitfalls

- Averaging the branch currents and reporting the group as balanced. The
  average is never the branch that trips.
- Treating the group capability as the sum of the branch thresholds. The
  sum is only reached by a group that shares perfectly, which no real
  parallel group does.
- Taking the smallest threshold as the limit. A low-threshold branch
  that carries a small share can be nowhere near limiting.
- Reading a starved branch as harmless. It is the branch that was
  supposed to be there when another one fails.
- Substituting an equal share for an unmeasured branch and reporting a
  clean result. An assumed share is not a measured one.
- Grading imbalance while a branch is already out of headroom. The trip
  happens first and makes the sharing numbers historical.
- Assessing a retriggerable limiter or a foldback device here. Their
  current-division law is not the one these ratios assume.

## Behavior contract (gate 3)

The governed and refused limiter types, the equal share for a branch
count, share fractions from measured currents, imbalance taken at the
worst branch, the starved-share floor, per-branch headroom against its
own threshold, headroom outranking imbalance, the unmeasured branch that
stops the group, the smallest threshold-over-share ratio derated by
margin against the declared demand, and the worst-standing group verdict
are exercised by the gate 3 contract test:
scripts/test_e2020_parallel_current_sharing_accuracy.py against
scripts/e2020_parallel_current_sharing_accuracy_logic.py (stdlib
unittest, offline).
Run: python3 scripts/test_e2020_parallel_current_sharing_accuracy.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
