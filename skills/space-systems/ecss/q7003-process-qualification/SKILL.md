---
name: q7003-process-qualification
description: "Evaluate whether an anodizing line is qualified against its declared parameter window. Use when a tank, rectifier or rack pattern is taken into service or brought back after a change and the coupon campaign that was actually run has to be graded: demand several consecutive runs rather than one good one, insist on coupons at the ends of the rack and not only its comfortable middle, grade every recorded parameter against the window being qualified, check each required characteristic was measured and passed, and separate an outright fail from a qualification that stands with a coverage finding attached. Trigger: ecss, q-st-70-03-anodizing, anodizing-line-qualification, anodize-witness-coupon-campaign, anodize-rack-position-coverage, anodize-parameter-window-control, anodize-requalification-trigger."
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
  tags: [ecss, q-st-70-03-anodizing, q7003-process-qualification, anodizing-line-qualification, anodize-witness-coupon-campaign, anodize-rack-position-coverage, anodize-parameter-window-control, anodize-requalification-trigger]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Anodizing — Process Qualification (space-systems/ecss/q7003-process-qualification)

Use when the task is the quality-assurance clause of ECSS-Q-ST-70-03:
demonstrating that an anodizing line, running inside a declared
parameter window, produces a conforming coating repeatably and
everywhere on the rack -- and saying when that demonstration expires.

## Domain quick reference

- Qualification is a statement about a line, not about a part. The
  claim is that this tank, this rectifier, this rack pattern and this
  declared window together produce a conforming coating, so a
  qualification cannot be inherited from a part that happened to pass.
- Repeatability needs consecutive runs, not one. A single good run
  shows the line managed it once, which is a weaker claim than the one
  being made and the one the hardware depends on.
- Coupons are hung where the process fails first. Current density,
  electrolyte flow and local temperature all vary along a rack, so the
  ends are the informative positions and a campaign that samples only
  the middle has looked at the comfortable case.
- Coverage has two separate failures. Missing an end of the rack is
  fatal, because the risk region was never sampled. Sampling both ends
  but almost nothing between them is thin rather than fatal, and is
  carried as a finding on a qualification that still stands.
- A run that drifted outside the window did not qualify the window. It
  demonstrated some other process, so an excursion invalidates the run
  rather than widening the window that was being claimed.
- A parameter that was never recorded is not a parameter that was in
  control. An unrecorded value and an out-of-window value both break the
  same claim, and both belong in the same list.
- Qualification expires. A bath rebuild, a rectifier replacement, a
  change of alloy family, a rack redesign, a seal chemistry change or
  simple elapsed time each put the line back in front of the campaign.
- A parameter set at a window edge is logged through a conversion and
  reads a few units in the last place outside its own bound. The
  comparison absorbs that; the window itself is never widened.

## Workflow

1. Validate the declared parameter windows before anything is graded
   against them. Reject an inverted window and an empty window set,
   because a campaign cannot qualify a bound that was never stated.
2. Count the runs. Below the minimum consecutive count, the campaign has
   not made a repeatability claim at all, and that is recorded as the
   finding rather than inferred from the coupon results.
3. Grade rack position coverage against the positions available. Check
   both extremes first and treat a missing extreme as fatal; then check
   the interior spread and treat a thin one as a finding.
4. Check every required characteristic was measured on a coupon and
   passed. An unmeasured characteristic is not a passed one, so the two
   are reported separately and both block qualification.
5. Grade each run's recorded parameters against the window, naming the
   run index with the excursion so the campaign record can be opened at
   the right page. Treat an unrecorded parameter as an excursion.
6. Give the verdict: not qualified on too few runs, any excursion, a
   missing rack extreme or an incomplete or failed coupon set;
   conditionally qualified when everything held but a finding stands;
   qualified only when nothing was raised.
7. Separately, evaluate whether a standing qualification has lapsed
   against the declared change triggers and the validity period.

## Pitfalls

- Qualifying on one good run. Repeatability is the property being
  claimed, and a single run cannot evidence it however good the coupons
  from it were.
- Hanging coupons only in the middle of the rack. The middle is where
  the process is most comfortable, so a campaign sampled there passes
  while the parts at the ends of the rack are the ones that will come
  out thin or burnt.
- Widening the window to take in an excursion after the fact. The runs
  then evidence the wider window with a sample of one at its edge, which
  is exactly the region the campaign was supposed to cover properly.
- Reading an unrecorded parameter as nominal. Nothing was measured, so
  nothing is known, and a campaign that silently fills the gap qualifies
  a window it never demonstrated.
- Treating a thin interior spread as equivalent to a missing extreme.
  One is a gap in the risk region and fatal; the other is a
  completeness finding on a qualification that stands, and collapsing
  them either blocks good lines or passes unsampled ones.
- Letting a qualification run indefinitely because nothing obviously
  changed. Bath chemistry ages, anodes consume and racks get repaired,
  which is why the validity period exists alongside the change list.

## Behavior contract (gate 3)

The window validation, run-parameter control check, rack position
coverage, coupon completeness, requalification triggers and the overall
qualification verdict are exercised by the gate 3 contract test:
scripts/test_q7003_process_qualification.py against
scripts/q7003_process_qualification_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7003_process_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
