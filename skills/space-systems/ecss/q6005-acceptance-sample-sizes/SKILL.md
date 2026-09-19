---
name: q6005-acceptance-sample-sizes
description: "Size the acceptance sample drawn from a hybrid production batch under ECSS-Q-ST-60-05C clause 12.1.2: validate the batch and the sampling schedule for gaps and overlaps, read the band the batch falls in, collapse a small batch to full inspection, cap the sample at the batch so no plan asks for units that do not exist, report the sampling fraction against a contractual minimum, check that a destructive plan still leaves the deliverable quantity, and disposition the batch against its acceptance number. Use when planning or auditing hybrid batch acceptance sampling. Trigger: ecss, q-st-60-05c, hybrid-acceptance-sample-size, hybrid-batch-sampling-schedule, hybrid-lot-size-sample-band, destructive-acceptance-sample-shortfall, hybrid-acceptance-number, hybrid-sampling-fraction."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-acceptance-sample-sizes, hybrid-acceptance-sample-size, hybrid-batch-sampling-schedule, hybrid-lot-size-sample-band, destructive-acceptance-sample-shortfall, hybrid-sampling-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Acceptance Sample Sizes (space-systems/ecss/q6005-acceptance-sample-sizes)

Use when the task is deciding how many hybrid units come out of a
production batch for acceptance testing under ECSS-Q-ST-60-05C clause
12.1.2 — the number drawn, the number of nonconforming units that
number still accepts, and whether the batch is big enough to carry both
the sample and the order.

## Domain quick reference

- The sample size is a function of the batch size, read off a schedule
  of bands, not a fixed percentage. Between bands the sample steps; the
  sampling fraction therefore falls as a batch grows inside one band and
  jumps back up when it crosses into the next. A plan written as "ten
  percent" and a plan read off a schedule agree almost nowhere.
- A small batch collapses to full inspection. Below a threshold the
  scheduled sample is most of the batch anyway, and the statistical
  argument for sampling — that the untested remainder is large enough to
  be worth not testing — has stopped applying.
- The sample is capped at the batch. A band is written for a range of
  batch sizes, and at the low end of a band the scheduled number can
  exceed the batch sitting just inside it. Without the cap a plan asks
  for units that were never built.
- The acceptance number is part of the plan, not a separate tolerance.
  Small samples carry zero: one nonconforming unit refuses the batch.
  Larger samples carry one, two or more, because a larger sample seeing
  a single failure is weaker evidence of a bad population than a small
  one seeing the same failure.
- Destructive acceptance tests consume what they measure. Units in the
  sample never ship, so the batch has to carry the sample on top of the
  deliverable quantity. Sizing the build to the order and then drawing
  the sample out of it is the most common way a batch runs short.
- The schedule itself is project data. A table with a gap leaves some
  batch size with no plan at all, and a table whose acceptance number
  reaches its own sample size accepts everything; both are found by
  validating the schedule, not by reading a batch against it.

## Workflow

1. Validate the batch as a positive count of units actually built, and
   validate the schedule: ascending contiguous bands, only the last one
   open ended, every acceptance number below its own sample size.
2. Read the band the batch falls in, taking both band edges as
   inclusive.
3. Apply the full-inspection threshold first, then cap the sample at the
   batch, and record which of the two acted so the plan can be explained.
4. Compute the sampling fraction and compare it with any contractual
   minimum percentage, absorbing representation error at the bound
   rather than relaxing the bound.
5. Where the acceptance tests are destructive, subtract the sample from
   the batch and check the remainder still covers the deliverable
   quantity; report the shortfall in units, not as a warning.
6. Disposition the batch by comparing the nonconforming count found
   against the band's acceptance number, and refuse a result that
   reports more failures than units sampled.
7. Return the band, the sample, the acceptance number, the fraction, the
   shortfall and every finding, so the plan can be reproduced and
   defended at the review.

## Pitfalls

- Reading the sampling fraction as the requirement. The schedule sets
  the sample; the fraction is a consequence of it and moves inside a
  band. A contract quoting a percentage has to be checked against the
  schedule, not substituted for it.
- Sizing the build to the order when acceptance testing is destructive.
  The sample is consumed, so a batch built to the order ships short by
  exactly the sample size.
- Taking the scheduled number blindly at the bottom of a band. The cap
  at the batch is what keeps the plan buildable, and a plan that was
  capped is a different plan — it is now full inspection.
- Treating the acceptance number as a quality target. It is the count at
  which the evidence still supports the batch; a batch at its acceptance
  number passed, and reading that as "nearly failed" invents a grade the
  plan does not have.
- Substituting a project schedule without validating it. A gap between
  two bands is silent until a batch lands in it, and then the plan
  either falls through to full inspection or to nothing at all.
- Accepting a sample result larger than the sample. More nonconforming
  units than units drawn means the count came from somewhere other than
  this sample, and dispositioning on it grades the wrong batch.

## Behavior contract (gate 3)

The batch validation, schedule validation, band lookup, full-inspection
collapse, cap at the batch, sampling fraction, destructive shortfall and
the accept/reject disposition are exercised by the gate 3 contract test:
scripts/test_q6005_acceptance_sample_sizes.py against
scripts/q6005_acceptance_sample_sizes_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_acceptance_sample_sizes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
