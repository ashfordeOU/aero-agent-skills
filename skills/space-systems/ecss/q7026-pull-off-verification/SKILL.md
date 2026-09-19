---
name: q7026-pull-off-verification
description: "Determine whether a crimped lot passes pull-off verification on its sample, its forces and its break modes. Use when destructive pull tests have been run and the lot needs an acceptance decision: resolve the specimen count the lot size demands, compare every recorded force with the minimum tabulated for its own gauge, separate a conductor break outside the barrel from a conductor that pulled out of it, hold an undersized sample at review rather than accepting it, and escalate the rate for the next lot once a specimen fails. Trigger: ecss, q-st-70-26-crimping, crimp-pull-off-force-minimum, crimp-pull-test-sample-rate, crimp-pull-out-versus-conductor-break, crimp-lot-acceptance-rule, crimp-sample-rate-escalation."
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
  tags: [ecss, q-st-70-26-crimping, q7026-pull-off-verification, crimp-pull-off-force-minimum, crimp-pull-test-sample-rate, crimp-pull-out-versus-conductor-break, crimp-lot-acceptance-rule, crimp-sample-rate-escalation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Pull-off Verification (space-systems/ecss/q7026-pull-off-verification)

Use when the Quality clause of ECSS-Q-ST-70-26 is the task at the pull
tester: deciding whether a crimped lot is verified, from a destructive
sample that by definition never includes the hardware that flies.

## Domain quick reference

- The test destroys what it measures, so the result is about the lot and
  not about any delivered crimp. Everything therefore rests on the
  sample being the one the plan demands.
- An undersized sample cannot accept a lot. Five specimens that all
  cleared the minimum, where the plan asked for eight, is a measurement
  and not a verification, and the lot sits at review until the rest are
  pulled.
- Sample size is a function of lot size, and the function is a step
  function. A lot one unit past a tier boundary moves to the next tier
  entirely, and a plan with no rule above its largest tier cannot
  resolve a big lot at all.
- The minimum force is per gauge. It follows the conductor, so a single
  figure carried across a mixed-gauge lot passes the fine wire on the
  heavy wire's evidence.
- Where the specimen let go matters as much as when. A conductor that
  breaks outside the barrel proves the crimp is stronger than the wire,
  which is the result the test is looking for.
- A conductor that pulls out of the barrel is a finding even above the
  minimum. The force cleared the number, and the crimp still released
  before the wire did, so the joint is weaker than the conductor it
  terminates.
- A contact that fails in its own body says nothing about the crimp.
  That specimen is spent without producing evidence, so it cannot be
  counted as a pass.
- A failure changes the next sample, not just this lot. One failure in a
  sample of five is evidence about the population, which is why the rate
  escalates and a second failure takes the whole lot.

## Workflow

1. Validate the per-gauge minimum force table, refusing a gauge it does
   not carry rather than interpolating a minimum between neighbours.
2. Validate the sampling plan: tiers ordered by lot size, samples that
   never shrink as the lot grows, no tier asking for more specimens than
   the lot holds, and a resolvable rule above the largest tier.
3. Resolve the required specimen count for this lot size, capping it at
   the lot itself.
4. Grade each specimen: force against its own gauge minimum, then break
   mode, splitting pull-out below the minimum from pull-out above it and
   from a contact body failure.
5. Grade the sample actually pulled against the required count and
   report the shortfall and the coverage fraction explicitly.
6. Take the worst of the sampling result and every specimen result, so
   an undersized sample alone is enough to block acceptance.
7. Report the force statistics, the worst margin, the pull-out count,
   the failed and inconclusive specimens by identifier, and the sample
   size the next lot inherits.

## Pitfalls

- Reporting a pull-test result without the size of the sample it came
  from. A sample of one on a lot of forty reads exactly like a sample of
  four unless the count is on the page.
- Accepting a lot on an undersized sample because every specimen passed.
  The specimens that were not pulled are the ones the plan was sized to
  cover.
- Interpolating a sample size between tiers. The plan is a step
  function and a lot one unit over a boundary belongs entirely to the
  next tier.
- Carrying one minimum force across a mixed-gauge lot. The fine wire is
  then accepted on evidence that belongs to the heavy wire.
- Recording only the force and not the break mode. A pull-out and a
  conductor break at the same reading are opposite results.
- Reading a pull-out above the minimum as a pass. The number was met and
  the crimp still released before the conductor, which is the failure
  the test exists to find.
- Counting a contact body failure as a passing specimen. It consumed a
  place in the sample without producing evidence about the crimp.
- Failing the lot and leaving the sample rate alone. One failure in a
  small sample is information about the population, and the next lot
  inherits it.
- Comparing a force with its minimum by bare arithmetic. A force
  specified to land exactly on the minimum can evaluate a few units in
  the last place below it after a load cell conversion, so the
  comparison absorbs that representation error while the minimum stays
  untouched.

## Behavior contract (gate 3)

The per-gauge force table and its refusal of an untabulated gauge, the
sampling plan validation including ordering and the above-tier rule, the
required and escalated sample sizes, the undersized-sample review
outcome, the specimen grading across force and all three break modes,
the lot rollup with its force statistics, pull-out count and named
failed and inconclusive specimens are exercised by the gate 3 contract
test: scripts/test_q7026_pull_off_verification.py against
scripts/q7026_pull_off_verification_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7026_pull_off_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
