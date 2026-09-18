---
name: q7030-pull-off-verification
description: "Verify the pull-off evidence behind a lot of wire wraps under ECSS-Q-ST-70-30C quality rules. Use when the destructive sample is planned or graded: size the sample from the lot, hold a first-article wrap for every operator, tool and gauge setup, read the minimum unwrap force the conductor gauge owes, compare each measured force against it and state the margin, refuse a sample cut from flight hardware instead of a process coupon, and return the lot disposition, whether that is acceptance, a hold for full re-verification, or rewrap. Trigger: ecss, q-st-70-30c, wire-wrap-pull-off-force, wire-wrap-destructive-sampling, wire-wrap-first-article-wrap, wire-wrap-lot-disposition, wire-wrap-process-coupon, wire-wrap-unwrap-force-margin."
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
  tags: [ecss, q-st-70-30c, q7030-pull-off-verification, wire-wrap-pull-off-force, wire-wrap-destructive-sampling, wire-wrap-first-article-wrap, wire-wrap-lot-disposition, wire-wrap-process-coupon, wire-wrap-unwrap-force-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wire Wrapping — Pull-off Verification (space-systems/ecss/q7030-pull-off-verification)

Use when the task is the destructive pull-off verification of wrapped
connections under ECSS-Q-ST-70-30C -- deciding how many wraps the lot
owes to the test, which setups each sample stands for, and what the
measured forces say about the lot as a whole.

## Domain quick reference

- The pull-off test destroys the wrap it grades. That single fact
  shapes everything else: it can only be a sampling test, the sample
  can only come from a coupon made alongside the work, and its result
  is evidence about a process setting rather than about any delivered
  connection.
- The sample grows with the lot far more slowly than the lot does,
  because what is being demonstrated is that the tool, the wire and the
  hand producing the wraps are set correctly, and that does not become
  more uncertain as more wraps are made from the same setting.
- A setup is the combination of operator, tool and conductor gauge. Any
  one of the three changing is a different process, and the new setup
  owes its own first-article wrap before production on it continues. A
  lot that covers two operators with one first article has one setup
  unverified.
- The minimum unwrap force is owed by the conductor gauge. A coarser
  conductor presses harder on the post corners and carries more metal
  to shear, so it must survive a larger force; reading one figure
  across a mixed-gauge lot passes fine-gauge wraps that were never
  tested against their own number.
- The margin -- measured force over the minimum -- is reported
  alongside the verdict, because a lot that passed at 1.02 and a lot
  that passed at 1.8 are the same verdict and completely different
  process news.
- The dispositions differ in kind. A force below the minimum is a
  process that is not making sound joints, so the lot is rewrapped. A
  sampling or coverage gap is an evidence problem, so the lot is held
  for full re-verification rather than condemned.

## Workflow

1. Size the sample from the lot with the declared plan, and cap it at
   the lot itself so a lot smaller than the sample is fully tested
   rather than over-drawn.
2. Identify the setups present among the samples, and list any setup
   with no first-article wrap behind it.
3. Read the minimum unwrap force from each sample's own conductor
   gauge.
4. Grade each sample: compare the measured force against that minimum,
   compute the margin, and raise a finding on any sample whose origin
   is flight hardware rather than a process coupon.
5. Decide the lot. Any sample below its minimum rejects the lot for
   rewrap; a sampling shortfall, an uncovered setup or a
   wrongly-sourced sample holds the lot for full re-verification;
   otherwise the lot is accepted.
6. Report the worst margin in the lot with the disposition, so a lot
   that only just passed is visible as such.

## Pitfalls

- Sampling flight hardware because the coupons were not made. The
  destroyed wrap has to be replaced on a deliverable assembly, which is
  a rework on the very hardware the test was meant to protect, and the
  result is evidence of nothing that the coupon would not have shown.
- Applying one minimum force across a mixed-gauge lot. The schedule is
  per gauge, and the coarse figure over-tests the fine wraps while the
  fine figure passes coarse wraps that never met their own
  requirement.
- Counting the sample and stopping there. The right number of samples
  drawn entirely from one operator's work leaves every other setup in
  the lot with no evidence at all, which is why coverage is checked
  separately from count.
- Comparing a measured force against the minimum by bare arithmetic. A
  wrap that lands exactly on the number can read a few units in the
  last place below it; the comparison absorbs that representation error
  while the minimum itself stays untouched.
- Collapsing every problem into one verdict. Rewrap and re-verification
  answer different questions -- one says the joints are weak, the other
  says the evidence is thin -- and treating a sampling gap as a
  rejection scraps sound hardware.

## Behavior contract (gate 3)

The force schedule, the sampling plan, the setup and first-article
coverage, the per-sample grading with its margin, the origin rule and
the three lot dispositions are exercised by the gate 3 contract test:
scripts/test_q7030_pull_off_verification.py against
scripts/q7030_pull_off_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7030_pull_off_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
