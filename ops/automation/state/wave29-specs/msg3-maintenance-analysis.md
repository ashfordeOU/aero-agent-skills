# Wave-29 leaf spec: msg3-maintenance-analysis (systems-engineering-safety, continued-airworthiness pack)

- Path: skills/systems-engineering-safety/continued-airworthiness/
  msg3-maintenance-analysis/
- Pack: continued-airworthiness (existing sibling:
  in-service-safety-assessment)
- Standards ids: msg-3 (reference-only; new id added to
  standards-map.yaml at wave-29 prep). Ledger Standard: msg-3.
- Family: systems-engineering-safety

## Claim

Apply the MSG-3 maintenance steering group decision logic to develop
a scheduled maintenance program for an aircraft system or component:
classify each failure mode by effect visibility (evident to the flight
crew or hidden) and consequence (safety-significant or
economic-only), select the applicable scheduled maintenance task
categories (lubrication, servicing, operational check, visual check,
inspection/functional check, restoration, discard), and assign an
interval logic verdict including the hidden-function exposure rule.
Produces the failure classification, the recommended task set with
rationale, and the interval verdict that gate the maintenance program
development handoff.

Does NOT do: assess in-service field data against safety objectives
(in-service-safety-assessment owns the Poisson exceedance and
single-event rules on service difficulty reports); perform zonal or
particular-risk analysis (arp4761a zonal-safety-analysis and
particular-risk-analysis own those); run FTA/FMEA quantification
(fta-fmea owns the fault tree and failure modes); develop MMEL items
(certification mmel-development owns dispatch relief). This leaf is
the MSG-3 decision logic for scheduled maintenance task selection,
not a reliability calculation.

## Model (implement exactly)

Module constants:
- TASK_CATEGORIES = ["LU", "SV", "OP", "VC", "IN", "FC", "RS", "DS"]
  (lubrication, servicing, operational check, visual check,
  inspection, functional check, restoration, discard).
- HIDDEN_EXPOSURE_FACTOR = 0.5 (hidden failures must be detected
  within half the exposure time to a second failure).

Failure classification inputs (each failure mode record is a dict):
- failure_id (str), function (str), failure_effect (str),
- evident (bool: does the flight crew detect the failure during normal
  operation?),
- safety_significant (bool: can the failure or its effects reach a
  safety consequence before maintenance?),
- hidden_safety (bool: if hidden, would the undetected failure
  combination with a second failure create a safety consequence?),
- maintenance_opportunity_interval (float, flight hours: the typical
  interval at which the item is accessible),
- single_failure_interval (float, flight hours: the interval over
  which a second independent failure could occur while the first is
  undetected).

Functions (pure stdlib, deterministic):
- classify_failure(record) -> dict: applies the MSG-3 top-level
  branch:
  * if not evident and not safety_significant and hidden_safety:
    category "5-hidden-safety" (hidden failure with a safety
    consequence in combination).
  * if not evident and not safety_significant and not hidden_safety:
    category "6-hidden-economic".
  * if evident and safety_significant: category "7-evident-safety"
    (evident failure with direct safety effect on the operating
    crew or vehicle).
  * if evident and not safety_significant: category "8-evident-
    economic" if the effect is economic or operational only.
  Returns {failure_id, category, evident, safety_significant,
  hidden_safety, rationale: str}.
- select_tasks(classification, applicable_hidden=True) -> dict:
  task selection per category:
  * "5-hidden-safety": ["FC", "IN", "VC"] (functional or inspection
    tasks that reveal the hidden failure) with note that a
    lubrication/servicing task alone is never sufficient.
  * "6-hidden-economic": ["FC", "IN"] if the item has a hidden
    function, else ["VC"].
  * "7-evident-safety": ["IN", "FC", "RS", "DS"] (preventive tasks
    that reduce the probability of the safety effect).
  * "8-evident-economic": ["VC", "IN", "FC", "RS", "DS"].
  Returns {failure_id, category, task_categories: list (ordered,
  highest-value first), rationale}.
- interval_verdict(record, classification, task_categories) -> dict:
  for any selected category that detects a hidden failure ("FC", "IN",
  "VC" on a hidden-safety item), enforce the exposure rule: the
  detection interval must be <= HIDDEN_EXPOSURE_FACTOR *
  single_failure_interval when a second-failure combination is the
  concern; compare against maintenance_opportunity_interval:
  * if hidden and detection interval (taken as
    maintenance_opportunity_interval) > 0.5 * single_failure_interval:
    verdict "interval-too-long", recommended interval = 0.5 *
    single_failure_interval.
  * else verdict "interval-ok".
  For evident categories the verdict compares the opportunity interval
  against the manufacturer-recommended task interval if provided
  (record key task_interval); if absent return "interval-not-scoped".
  Returns {failure_id, exposure_limit, opportunity_interval,
  verdict, recommended_interval}.
- run_msg3_analysis(records) -> dict: applies classify_failure,
  select_tasks, and interval_verdict to every record; returns
  {results: [...], summary: {total, hidden_count,
  safety_significant_count, interval_too_long_count}}.

## Worked example

Records:
1. {"failure_id": "F1", "function": "hydraulic pressure", "failure_effect":
   "pressure loss", "evident": False, "safety_significant": False,
   "hidden_safety": True, "maintenance_opportunity_interval": 3000.0,
   "single_failure_interval": 4000.0} (hidden failure that would
   combine with a second failure into a safety consequence).
2. {"failure_id": "F2", "function": "cabin lighting", "failure_effect":
   "light loss", "evident": True, "safety_significant": False,
   "hidden_safety": False, "maintenance_opportunity_interval": 6000.0,
   "single_failure_interval": 0.0} (evident economic).
3. {"failure_id": "F3", "function": "thrust reverser unlock",
   "failure_effect": "uncommanded reverser deployment", "evident": True,
   "safety_significant": True, "hidden_safety": False,
   "maintenance_opportunity_interval": 4000.0,
   "single_failure_interval": 0.0} (evident safety).

Deterministic anchors:
- classify_failure(F1) = category "5-hidden-safety", rationale
  mentions the hidden failure combination.
- classify_failure(F2) = category "8-evident-economic".
- classify_failure(F3) = category "7-evident-safety".
- select_tasks(F1 classification) contains "FC" and "IN"; does NOT
  contain "LU" as the only task.
- select_tasks(F3 classification) contains "RS" or "DS".
- interval_verdict(F1): exposure_limit = 0.5 * 4000 = 2000.0 FH;
  opportunity 3000 > 2000 so verdict "interval-too-long",
  recommended_interval 2000.0 FH.
- interval_verdict on a second hidden record with opportunity 1000.0
  and single_failure_interval 4000.0: verdict "interval-ok".
- run_msg3_analysis summary counts: total 3, hidden_count 1,
  safety_significant_count 1, interval_too_long_count 1.
- ValueErrors: record missing a required key; single_failure_interval
  negative; maintenance_opportunity_interval <= 0 on a hidden item.

Keep at least 18 test methods: classification branches 5/6/7/8,
task category selection per branch, exposure rule pass and fail,
summary counts, rationale non-empty strings, ValueErrors. Runs offline
in under 20 s.

## Corpus tasks (ids w29-msg3-maintenance-analysis-1/2)

Distinctive tokens: MSG-3, maintenance steering group, scheduled
maintenance task selection, hidden failure, evident failure, task
category, interval determination, maintenance program development.
Avoid: service difficulty report, Poisson exceedance, in-service
safety assessment (in-service-safety-assessment); zonal analysis,
particular risk (zonal-safety-analysis, particular-risk-analysis);
fault tree, FMEA (fta-fmea); MMEL, dispatch relief (mmel-development).

1. "run the MSG-3 decision logic on a hidden hydraulic failure: pick
   the scheduled maintenance task categories and apply the exposure
   rule to set the detection interval"
2. "classify an evident safety-significant failure under MSG-3 and
   select the preventive task categories for the maintenance program"

## SKILL body notes

Pair with in-service-safety-assessment (field data that later revises
the MSG-3-derived program), arp4761a leaves (safety assessments feed
the failure-effect classification), certification-basis (the
maintenance program supports continued airworthiness). State the
boundary: this leaf encodes the MSG-3 decision logic as a deterministic
rule table with paraphrased categories, never reproduces MSG-3 text or
worksheets (gated: true in standards-map.yaml). Mirror the
continued-airworthiness SKILL body style (process logic, stdlib only,
deterministic offline).
