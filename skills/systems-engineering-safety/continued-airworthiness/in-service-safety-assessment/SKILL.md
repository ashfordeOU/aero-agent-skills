---
name: in-service-safety-assessment
description: "Use when you must assess in-service safety data for a civil aircraft fleet against the type-design safety assessment predictions: collect field events from service difficulty reports and airline reliability reports grouped by failure condition, compute the observed event rate over the fleet exposure, compare it with the predicted rate from the safety objective, apply the single-event rule for hazardous or catastrophic events, and decide whether the experience is safety-significant. Produces the observed rate, the Poisson exceedance statistic, the significance verdict, and the corrective action route (no action, continued monitoring, service bulletin, or airworthiness directive request) with an urgency band. Trigger: in-service safety assessment, continued airworthiness, service difficulty report, field event rate, fleet exposure, observed versus predicted rate, single-event rule, ARP5150, safety significance, airworthiness directive request."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: continued-airworthiness
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: continued-airworthiness
  tags: [in-service-safety-assessment, continued-airworthiness, service-difficulty-report, field-event-rate, fleet-exposure, observed-versus-predicted-rate, single-event-rule, safety-significance, service-bulletin, airworthiness-directive-request]
  version: 0.1.0
  author: Aero Agent Skills
---

# In-Service Safety Assessment (systems-engineering-safety/continued-airworthiness/in-service-safety-assessment)

Use when field experience on a civil aircraft fleet must be reviewed
against the type-design safety assessment: collect service difficulty
reports, airline reliability reports and incident reports, group them by
the failure condition they demonstrate, and decide whether the observed
event rate over the fleet exposure is consistent with the SSA predicted
rate for each condition. This leaf opens the continued-airworthiness
pack and implements the ARP5150A and ARP5151 style in-service review in
pure Python, stdlib only. ARP5150A and ARP5151 continue the ARP4761A
assessment process into the in-service phase, so the predicted rates
consumed here come from the development safety assessment. It pairs with
systems-engineering-safety/arp4761a/safety-assessment (the producer of
those predicted rates), with arp4761a/failure-rate-estimation (the
statistics sibling; chi-square confidence bounds and zero-failure
demonstrations are NOT re-derived here), and with
certification/mmel-development (dispatch relief uses the same severity
inputs).

## Domain quick reference

- Field event sources: service difficulty reports, airline reliability
  reports and incident reports, each mapped to the failure condition it
  demonstrates with a severity (none, minor, major, hazardous,
  catastrophic) and a description.
- Exposure: total fleet flight hours (fh) or flight cycles (fc) over
  which events were collected; per aircraft average is total divided by
  fleet size.
- Expected events under the prediction: m = predicted_rate * exposure.
- Observed rate: observed / exposure.
- Single-event rule: one hazardous or catastrophic event is
  significant regardless of the rate (SINGLE_EVENT_SEVERITIES).
- Poisson exceedance tail: P(X >= observed | mean m) computed as the
  series sum from k = observed, stopping when the added term falls
  below 1e-12 or k exceeds m * 20 + 50 (CEILING_MULT), via exp and a
  log-factorial start term for stability.
- Significance: tail <= SIGNIFICANCE_ALPHA (0.05), or observed rate at
  least RATE_EXCEEDANCE_MIN (2.0x) the predicted rate, or the
  single-event rule.
- Exposure adequacy: an exposure window is adequate to judge a
  predicted rate when predicted_rate * exposure >= 5.0 expected events
  (EXPOSURE_ADEQUACY_EXPECTED_EVENTS), a typical screening rule.
- Corrective routes: airworthiness-directive-request (catastrophic
  single event or catastrophic rate exceedance, immediate), service-
  bulletin (hazardous significant, or major significant with an
  increasing trend, short-term or scheduled), continued-monitoring
  (minor significant, or any not-significant verdict with inadequate
  exposure or an increasing trend, routine or scheduled), no-action
  (not significant, adequate exposure, non-increasing trend, routine).
- The Poisson tail math is implemented directly in this leaf; the
  chi-square failure-rate statistics belong to the
  failure-rate-estimation sibling.

## Workflow

1. Fix the fleet exposure: fleet_size (aircraft), exposure_hours (total
   fleet exposure) and exposure_unit ("fh" flight hours or "fc" flight
   cycles); get the per-aircraft average with exposure_summary.
2. Collect the field events as dicts with event_id, condition_id,
   severity and description; group_events returns the count per
   condition and severity_max_per_condition preserves the highest
   observed severity per condition.
3. Load the SSA predictions: {condition_id: {predicted_rate, severity,
   note}}; every event condition must appear in predictions.
4. For each condition compute the expected events with
   expected_events(predicted_rate, exposure_hours) and screen the
   exposure with adequacy_verdict (adequate when expected events reach
   the 5.0 threshold).
5. Form the observed rate with observed_rate(events_count,
   exposure_hours).
6. Decide significance with significance_verdict(condition_id,
   observed, expected, severity): the single-event rule for hazardous
   or catastrophic observations, the one-sided Poisson exceedance tail
   against SIGNIFICANCE_ALPHA, and the RATE_EXCEEDANCE_MIN factor.
7. Route the outcome with corrective_route(verdict, exposure_adequate,
   trend_direction) where trend_direction is -1, 0 or 1; read the route
   and the urgency band.
8. Run assessment_summary(fleet_size, exposure_hours, exposure_unit,
   events, predictions, trend_direction) to obtain the full report body
   with every per-condition row and the safety-significant condition
   list.
9. Confirm the deterministic checks with the contract test
   scripts/test_in_service_safety_assessment.py.

## Worked example

Fleet of 200 aircraft with 1,000,000 fleet flight hours (fh).
Predictions from the SSA: "FCS-1" predicted_rate 3e-7 per fh, severity
hazardous (expected events 0.3); "PP-1" predicted_rate 2e-6 per fh,
severity major (expected events 2.0). Field events: 2 hazardous
"FCS-1" and 3 major "PP-1".

- FCS-1: observed rate 2e-6 per fh (observed_rate(2, 1e6)), expected
  events 0.3. Exposure is inadequate to judge the rate (0.3 is below
  the 5.0 adequacy threshold). Poisson tail P(X >= 2 | mean 0.3) =
  0.0369, at or below alpha 0.05, and the hazardous single-event rule
  applies. Verdict: significant; route service-bulletin, urgency
  short-term.
- PP-1: observed rate 3e-6 per fh, expected events 2.0. Poisson tail
  P(X >= 3 | mean 2.0) = 0.3233, above alpha 0.05; the rate ratio 1.5
  is below the 2.0 exceedance factor. Verdict: not significant. With
  expected events 2.0 the exposure is below the 5.0 adequacy threshold,
  so the route is continued-monitoring (routine) rather than a close
  out; the spec anchor permits no-action or continued-monitoring.
- Single catastrophic event: one event on a condition predicted at
  1e-8 per fh triggers the single-event rule even at a low rate; route
  airworthiness-directive-request, urgency immediate.

## Verification

- Confirm observed_rate(2, 1e6) returns 2e-6 and expected_events(3e-7,
  1e6) returns 0.3; the rate times the exposure recovers the event
  count (round-trip identity).
- Confirm poisson_exceedance_p(2, 0.3) is 0.0369 and
  poisson_exceedance_p(3, 2.0) is 0.3233, both within 1e-3 of the spec
  anchors; the tail is 1.0 for zero observed events and 0.0 for a
  positive count against a zero mean.
- Confirm adequacy_verdict(5.0) is adequate and adequacy_verdict(0.3)
  is inadequate against the 5.0 threshold.
- Confirm a single catastrophic event routes
  airworthiness-directive-request with urgency immediate, and that a
  hazardous significant verdict routes service-bulletin short-term.
- Confirm every non-physical input raises ValueError: negative
  exposure, non-positive fleet size, negative observed count or
  expected count, zero exposure when forming a rate, negative
  predicted rate, unknown severity strings, empty predictions, an
  event condition missing from predictions, an invalid exposure_unit,
  and a trend_direction outside -1/0/1.
- Run the contract test offline: python3
  scripts/test_in_service_safety_assessment.py (35 tests,
  deterministic, under 20 seconds).

## Related leaves

- systems-engineering-safety/arp4761a/safety-assessment: the
  development safety assessment whose FHA/PSSA/SSA predicted rates are
  consumed as inputs here.
- systems-engineering-safety/arp4761a/failure-rate-estimation: the
  statistics sibling; chi-square confidence bounds, test-hours sizing
  and the zero-failure rule live there, this leaf consumes predicted
  rates instead of re-deriving them.
- systems-engineering-safety/certification/mmel-development: dispatch
  relief planning uses the same failure-condition severity inputs.

## Pitfalls

- Waiting for the rate to prove a single severe event: one hazardous
  or catastrophic event is significant regardless of the rate — the
  single-event rule fires even against a 1e-8 predicted rate and
  routes an airworthiness-directive-request with immediate urgency.
- Closing a condition out on a not-significant verdict alone: with
  inadequate exposure (expected events below the 5.0 threshold, as in
  both worked conditions) the route is continued-monitoring, not
  no-action — the verdict and the adequacy screen must be read
  together.
- Judging significance on one path only: significance fires on the
  Poisson exceedance tail at or below alpha 0.05, OR the observed rate
  at least 2.0x the predicted rate, OR the single-event rule — any one
  path makes the condition significant.
- Reviewing events against an unknown condition: every event
  condition must appear in the SSA predictions, and an event mapped
  to a condition missing from predictions raises ValueError rather
  than silently scoring against nothing.
- Confusing this leaf with the statistics sibling: the Poisson tail is
  implemented here, but chi-square confidence bounds, test-hours
  sizing and zero-failure demonstrations belong to
  failure-rate-estimation and are not re-derived in this review.
- Routing without the trend input: corrective_route takes
  trend_direction (-1, 0, 1), so a major significant condition with an
  increasing trend routes service-bulletin while the same verdict
  without the trend signal does not.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_in_service_safety_assessment.py

The test covers the worked-example anchors (FCS-1 observed rate 2e-6
against expected 0.3 with Poisson tail 0.0369, PP-1 observed 3e-6
against expected 2.0 with tail 0.3233), the exposure summary and
adequacy threshold, expected and observed rate math with the round-trip
identity, Poisson tail boundary and ceiling behavior, the single-event
rule for hazardous and catastrophic events, the rate-exceedance factor
path, the route and urgency branches (airworthiness-directive-request,
service-bulletin, continued-monitoring, no-action), the full
assessment_summary report, and ValueError rejection of non-physical
inputs.

## Compliance

- Standards referenced, not reproduced: ARP4761A is the mapped
  standards id; ARP5150A and ARP5151 are named in prose only (they are
  not in standards-map.yaml). All content above is paraphrase at
  reference level per standards-map.yaml; no standard text is
  reproduced.
- compliance: STANDARDS-REF, gated: false.
