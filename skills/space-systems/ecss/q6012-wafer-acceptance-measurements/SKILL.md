---
name: q6012-wafer-acceptance-measurements
description: "Evaluate the electrical measurements taken on a wafer's process monitor structures against the foundry parameter limits, per ECSS-Q-ST-60-12C clause 10.2.4: validate the one-sided and two-sided limits, validate the site map, grade every reading inclusively, summarise each parameter across the wafer, and decide the wafer on both its median and its within-limit site fraction. Refuses a maximum-only parameter handed a lower bound, a duplicate site, a missing reading and a sample too small to be a map. Use when a fabricated wafer has to be accepted or rejected on drop-in monitor data. Trigger: ecss, q-st-60-12c-clause-10-2-4, wafer-process-monitor-electrical-measurement, foundry-parameter-limit-comparison, wafer-acceptance-site-fraction, drop-in-monitor-structure-yield, wafer-median-parameter-verdict."
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
  tags: [ecss, q-st-60-12-wafer-acceptance-measurements, q6012-wafer-acceptance-measurements, wafer-process-monitor-electrical-measurement, foundry-parameter-limit-comparison, wafer-acceptance-site-fraction, drop-in-monitor-structure-yield, wafer-median-parameter-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wafer Acceptance Measurements (space-systems/ecss/q6012-wafer-acceptance-measurements)

Use when a wafer has come off the line and the electrical data from the
process monitor structures that rode along with the product dies is on the
desk. The question is whether this specific wafer meets the foundry's own
parameter limits well enough to be accepted, before any die on it is
considered for a build.

## Domain quick reference

- The monitor structures are not the product. They are built alongside it on
  the same wafer and measured because the product dies cannot all be probed,
  so every conclusion here is about the wafer as a population, not about an
  individual die. That is why the decision rests on a median and a site
  fraction rather than on a single reading.
- A parameter is one-sided or two-sided, and that is a property of the
  parameter, not of the order. A leakage current has a ceiling and no floor; a
  drain current has a floor and no ceiling. Handing a one-sided parameter the
  bound it does not have is a specification defect, because the unused bound
  either does nothing or quietly rejects good material.
- A reading landing exactly on a limit is inside the limit. It is reported as
  being on the limit, so the reviewer sees a wafer with no margin instead of a
  wafer that merely passed, but it is never counted as a rejection.
- The two acceptance conditions are independent and a wafer can meet one and
  fail the other. A wafer whose median is comfortably central can still have a
  ring of failing edge sites; a wafer with every site inside limits can still
  have a median that has walked outside them. Both are graded.
- A rejection that names no parameter is not actionable. The foundry needs to
  know which parameter moved and whether it was the median or the spread, so
  the driving parameters are reported with the condition each one failed.

## Workflow

1. Validate the limit set: every parameter gets exactly the bounds its
   sidedness calls for, a two-sided band is refused if inverted, and an
   unknown parameter is refused rather than skipped.
2. Validate the site map: refuse a duplicate site, a reading for a parameter
   the limit set does not bound, a missing reading for one it does, and a
   sample smaller than the minimum site count.
3. Grade every site reading inclusively against its bounds, naming an
   on-limit reading as on-limit rather than folding it into the interior.
4. Summarise each parameter across the wafer: extremes, median, the count and
   fraction of sites within limits, the worst margin, and the failing sites.
5. Apply both acceptance conditions per parameter — median within limits, and
   within-limit site fraction at or above the required fraction — treating a
   fraction that lands exactly on the requirement as meeting it.
6. Report the verdict with the parameters that drove it and the condition each
   one failed.

## Pitfalls

- Deciding the wafer on a mean. A mean is pulled by a handful of dead edge
  sites into a rejection, or pulled back over the line by a strong centre; the
  median and the site fraction separate those two failures.
- Giving a one-sided parameter both bounds because the template has two. The
  invented bound is either inert or rejects wafers on a limit the foundry
  never set.
- Rejecting an on-limit reading. Exactly at the limit is inside it, and a
  strict comparison on a value a float computation lands on is also the
  classic platform-dependent failure.
- Accepting a wafer whose site fraction is fine but whose median has moved.
  The population has shifted even though most sites still pass, and the dies
  taken from it will not behave like the dies from the lot before it.
- Returning a bare reject. Without the driving parameter and the failed
  condition the foundry cannot tell a process shift from a probe problem.

## Behavior contract (gate 3)

The limit validation by sidedness, site map validation, inclusive reading
grading, per-parameter summary with median and site fraction, the two
independent acceptance conditions and the driving-parameter report are
exercised by the gate 3 contract test:
scripts/test_q6012_wafer_acceptance_measurements.py against
scripts/q6012_wafer_acceptance_measurements_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6012_wafer_acceptance_measurements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
