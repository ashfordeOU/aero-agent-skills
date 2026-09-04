---
name: msg3-maintenance-analysis
description: "Use when you must run the MSG-3 maintenance steering group decision logic to develop a scheduled maintenance program for an aircraft system or component: categorize each failure mode by effect visibility (evident to the flight crew or hidden) and consequence (safety-significant or economic-only), select the applicable scheduled maintenance task categories (lubrication, servicing, operational check, visual check, inspection, functional check, restoration, discard), and assign the interval verdict including the hidden failure exposure rule at half the single-failure interval. Produces the failure category, the recommended task set with rationale, and the interval verdict that gate the maintenance program development handoff. Trigger: MSG-3, maintenance steering group, scheduled maintenance, hidden failure, evident failure, task category selection, exposure rule, interval determination, maintenance program development."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: msg-3
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: continued-airworthiness
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: continued-airworthiness
  tags: [msg3-maintenance-analysis, msg-3, maintenance-steering-group, scheduled-maintenance-task-selection, hidden-failure, evident-failure, task-category-selection, exposure-rule, interval-determination, maintenance-program-development, continued-airworthiness]
  version: 0.1.0
  author: Aero Agent Skills
---

# MSG-3 Maintenance Analysis (systems-engineering-safety/continued-airworthiness/msg3-maintenance-analysis)

Use when the task is developing the scheduled maintenance program for an
aircraft system or component with the ATA MSG-3 maintenance steering
group logic: decide whether each failure mode is evident to the flight
crew or hidden, whether its consequence is safety-significant or
economic-only, pick the scheduled maintenance task categories that
apply, and set the detection or preventive interval. This leaf encodes
the MSG-3 decision logic as a deterministic rule table (paraphrased
categories and task codes, never MSG-3 text or worksheets) in pure
Python, stdlib only, fully offline. It pairs with
in-service-safety-assessment, whose field data later revises the
MSG-3-derived program, and with the safety assessments that feed the
failure-effect categorization. It is the decision logic for scheduled
maintenance task selection, not a reliability calculation.

## Domain quick reference

- Failure effect visibility: evident means the flight crew detects the
  failure during normal operation; hidden means it stays undetected
  until a scheduled task or a second failure exposes it.
- Top branch categories (paraphrased): 5-hidden-safety when a hidden
  failure can combine with a second failure into a safety consequence;
  6-hidden-economic when a hidden failure is economic-only;
  7-evident-safety when an evident failure has a direct safety effect on
  the operating crew or vehicle; 8-evident-economic when an evident
  failure is economic or operational only. A hidden failure carrying any
  safety concern (combination or direct) is categorized 5-hidden-safety;
  an evident failure is judged on its own safety significance.
- Task category codes: TASK_CATEGORIES = LU (lubrication), SV
  (servicing), OP (operational check), VC (visual check), IN
  (inspection), FC (functional check), RS (restoration), DS (discard).
  Task sets per category, ordered highest-value first: 5 gives FC, IN,
  VC (reveal the hidden failure; lubrication or servicing alone is never
  sufficient), 6 gives FC, IN when a check can reveal the hidden
  function and VC otherwise, 7 gives IN, FC, RS, DS (preventive), 8
  gives VC, IN, FC, RS, DS (economic grounds).
- Hidden exposure rule: HIDDEN_EXPOSURE_FACTOR = 0.5, so a hidden
  failure must be detected within half the single-failure interval. With
  the detection interval taken as the maintenance opportunity interval,
  opportunity above 0.5 x single-failure interval yields verdict
  interval-too-long with recommended interval 0.5 x single-failure
  interval; otherwise interval-ok.
- Evident intervals: when the manufacturer-recommended task_interval is
  supplied, the opportunity interval is compared against it (too long
  when opportunity exceeds it); without task_interval the verdict is
  interval-not-scoped.
- Interval verdict keys: failure_id, exposure_limit, opportunity_interval,
  verdict, recommended_interval.

## Workflow

1. Record each failure mode as a dict with failure_id, function,
   failure_effect, evident, safety_significant, hidden_safety,
   maintenance_opportunity_interval and single_failure_interval (flight
   hours), and task_interval when a manufacturer interval exists for an
   evident item.
2. Categorize the failure with classify_failure(record); the returned
   category and rationale capture the MSG-3 top branch.
3. Select the scheduled maintenance task categories with
   select_tasks(classification); pass applicable_hidden=False when no
   functional check can reveal a hidden function (category 6 falls back
   to a visual check).
4. Assign the interval verdict with interval_verdict(record,
   classification, task_categories); the exposure rule binds whenever a
   detection task (FC, IN, VC) is selected on a hidden failure.
5. Run the whole program pass with run_msg3_analysis(records) to get
   per-record results and the summary counts (total, hidden_count,
   safety_significant_count, interval_too_long_count), then confirm the
   deterministic checks with the contract test
   scripts/test_msg3_maintenance_analysis.py.

## Worked example

Three failure modes (flight hours):

1. F1 hydraulic pressure, pressure loss, hidden (evident False), not
   safety-significant on its own but hidden_safety True (a second
   failure would combine into a safety consequence), opportunity 3000.0
   FH, single-failure interval 4000.0 FH.
2. F2 cabin lighting, light loss, evident, economic-only, opportunity
   6000.0 FH.
3. F3 thrust reverser unlock, uncommanded reverser deployment, evident,
   safety-significant, opportunity 4000.0 FH.

Results:

- classify_failure(F1) = category "5-hidden-safety" with a rationale
  that names the hidden failure combination; select_tasks gives FC, IN,
  VC (never lubrication or servicing alone).
- classify_failure(F2) = category "8-evident-economic".
- classify_failure(F3) = category "7-evident-safety"; select_tasks gives
  IN, FC, RS, DS (preventive set contains RS and DS).
- interval_verdict(F1): exposure_limit = 0.5 x 4000 = 2000.0 FH;
  opportunity 3000.0 FH exceeds 2000.0 FH, so verdict
  interval-too-long with recommended_interval 2000.0 FH.
- A second hidden record with opportunity 1000.0 FH and
  single-failure_interval 4000.0 FH: exposure_limit 2000.0 FH, verdict
  interval-ok.
- F2 and F3 carry no task_interval, so their verdicts are
  interval-not-scoped.
- run_msg3_analysis([F1, F2, F3]) summary: total 3, hidden_count 1,
  safety_significant_count 1, interval_too_long_count 1.

## Verification

- Confirm the anchors: F1 categorized 5-hidden-safety with the exposure
  limit 2000.0 FH and verdict interval-too-long, F2 categorized
  8-evident-economic, F3 categorized 7-evident-safety with RS or DS in
  its task set, and the summary counts total 3, hidden 1, safety 1,
  too-long 1.
- Confirm classify_failure returns exactly the six documented keys with
  non-empty rationale for every branch, and select_tasks and
  interval_verdict return their documented key sets.
- Confirm the exposure rule boundary: an opportunity exactly equal to
  the exposure limit is interval-ok (the rule trips only when the
  opportunity exceeds the limit).
- Confirm the interval-not-scoped verdicts: evident items without
  task_interval, and hidden items whose selected task set has no
  detection task.
- Confirm ValueError rejection of non-physical inputs: a record missing
  any required key, a negative single_failure_interval, a non-positive
  maintenance_opportunity_interval on a hidden item, and a negative
  task_interval.
- Run the contract test offline: python3
  scripts/test_msg3_maintenance_analysis.py (42 tests, deterministic,
  under a second).

## Related leaves

- systems-engineering-safety/continued-airworthiness/
  in-service-safety-assessment: field experience data that later revises
  the MSG-3-derived program.
- systems-engineering-safety/arp4761a/zonal-safety-analysis and
  systems-engineering-safety/arp4761a/particular-risk-analysis: the
  ARP4761A physical-zone and particular-risk assessments, analyses that
  stay outside this leaf.
- systems-engineering-safety/arp4761a/fta-fmea: quantitative failure
  propagation analysis that this decision logic does not run.
- systems-engineering-safety/certification/mmel-development: item-level
  relief decisions that build on, and stay separate from, the scheduled
  program.
- systems-engineering-safety/certification/certification-basis: the
  maintenance program supports continued airworthiness of the certified
  type design.

## Pitfalls

- Scheduling lubrication or servicing on a hidden safety failure: a
  5-hidden-safety item needs detection tasks (FC, IN, VC) that reveal
  the hidden failure, and lubrication or servicing alone is never
  sufficient.
- Judging a hidden item by its own safety significance: a hidden
  failure carrying any safety concern — combination with a second
  failure or direct — categorizes as 5-hidden-safety, while evident
  failures are judged on their own safety significance; the two
  visibility classes resolve differently.
- Forgetting the half-interval exposure rule: a hidden failure must be
  detected within 0.5 x the single-failure interval (2000.0 FH on the
  4000.0 FH worked record), so an opportunity of 3000.0 FH is
  interval-too-long with the recommended interval set to the exposure
  limit — and an opportunity exactly at the limit is interval-ok, the
  rule trips only when it exceeds.
- Assuming a check exists for every hidden function: a 6-hidden-economic
  item whose hidden function no functional check can reveal falls back
  to a visual check via applicable_hidden=False instead of claiming an
  FC task that cannot work.
- Reading a missing interval as a pass: an evident item without a
  task_interval, and a hidden item whose selected task set contains no
  detection task, both return interval-not-scoped — not interval-ok.
- Copying MSG-3 text or worksheets: this leaf is a paraphrased
  deterministic rule table (categories and task codes only), and
  MSG-3 decision-logic text, tables and worksheets are never
  reproduced (standards-map gated: true).

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_msg3_maintenance_analysis.py

The test covers the four classification branches (5-hidden-safety,
6-hidden-economic, 7-evident-safety, 8-evident-economic) including the
hidden direct-safety resolution, task category selection per branch
(with the FC/IN/VC detection set, the lubrication-only rejection, the
preventive RS/DS set and the economic set), the hidden exposure rule
pass and fail cases with the 2000.0 FH anchor, the interval boundary at
the exposure limit, the evident task_interval comparisons, the
interval-not-scoped paths, the worked-example summary counts, the output
key sets, and the ValueError rejections of non-physical inputs.

## Compliance

- ATA MSG-3 (Operator/Manufacturer Scheduled Maintenance Development) is
  referenced, not reproduced: the categories, task codes and exposure
  rule above are paraphrased summary methodology per standards-map.yaml
  (gated: true, never reproduce MSG-3 decision-logic text, tables or
  worksheets verbatim).
- compliance: STANDARDS-REF, gated: false.
