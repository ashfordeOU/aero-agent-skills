# Wave-26 leaf spec: in-service-safety-assessment (systems-engineering-safety, continued-airworthiness pack - NEW PACK)

- Path: skills/systems-engineering-safety/continued-airworthiness/in-service-safety-assessment/
- Pack: continued-airworthiness (NEW pack; first leaf in it)
- Standards ids: arp4761a  (Ledger Standard: arp4761a)
  NOTE: the governing continued-airworthiness guidelines ARP5150A and
  ARP5151 are NOT in standards-map.yaml; name them in prose only
  (reference-only, no reproduction) and use arp4761a as the mapped
  frontmatter id (ARP5150/5151 continue the ARP4761A assessment process
  into the in-service phase).
- Family: systems-engineering-safety

## Claim

Assess in-service safety data for a civil aircraft fleet against the
type-design safety assessment: collect field events (service
difficulty reports, airline reliability reports, incident reports)
grouped by the failure condition they map to, compute the observed
event rate over the fleet exposure, compare it with the predicted rate
from the SSA safety objective, apply the single-event rule for
hazardous or catastrophic events, decide whether the experience is
safety-significant, and route the corrective action (no action,
continued monitoring, service bulletin, or airworthiness directive
request) with an urgency band. Produces the observed rate, the
exceedance statistic, the significance verdict, and the corrective
action route that gate the continued-airworthiness decision.

Does NOT do: derive confidence bounds or reliability demonstration
statistics from test data (arp4761a failure-rate-estimation owns the
chi-square bounds and zero-failure rule), run the development safety
assessment of a new design (arp4761a safety-assessment owns the
FHA/PSSA/SSA sequence), or manage manufacturing corrective action
processes (as9100 corrective-action owns the quality-process side).
This leaf consumes SSA predicted rates as inputs and decides whether
field experience requires action. The Poisson tail math is implemented
directly (small-k series sum), not via the failure-rate leaf.

## Model (implement exactly)

Inputs:
- fleet_size (int), exposure_hours (float, total fleet flight hours or
  cycles; document which in the SKILL body), exposure_unit ("fh" or
  "fc").
- events: list of dicts {event_id (str), condition_id (str, e.g.
  "FCS-1 catastrophic loss of pitch control"), severity (none, minor,
  major, hazardous, catastrophic), description (str)}. Each event maps
  to one predicted failure condition.
- predictions: dict {condition_id: {predicted_rate (float per unit),
  severity (str), note (str)}}.
Module constants:
- SINGLE_EVENT_SEVERITIES = {"hazardous", "catastrophic"} (a single
  event at this severity is significant regardless of rate).
- EXPOSURE_ADEQUACY_EXPECTED_EVENTS = 5.0 (exposure is adequate to
  judge a predicted rate when the expected event count
  predicted_rate * exposure >= 5; documented typical screening rule).
- SIGNIFICANCE_ALPHA = 0.05 (one-sided Poisson exceedance threshold).
- RATE_EXCEEDANCE_MIN = 2.0 (observed rate at least 2x predicted to be
  significant on its own, documented typical screening factor).
Functions:
- exposure_summary(exposure_hours, fleet_size) -> dict (total, per
  aircraft average).
- group_events(events) -> {condition_id: count} preserving severity
  max per condition.
- observed_rate(events_count, exposure_hours) -> float.
- poisson_exceedance_p(observed_count, expected_count) -> one-sided
  tail P(X >= observed | mean = expected): implement by summing the
  Poisson mass from observed to a large ceiling (module constant
  CEILING_MULT = 20, i.e. stop when the added term is below 1e-12 or
  k exceeds expected * CEILING_MULT + 50); use math.exp and log-factorial
  recurrence for stability; ValueError on negative expected.
- expected_events(predicted_rate, exposure_hours) -> float.
- adequacy_verdict(expected_events) -> (adequate_bool, note).
- significance_verdict(condition_id, observed, expected, severity) ->
  dict {significant (bool), reasons}: significant when severity in
  SINGLE_EVENT_SEVERITIES and observed >= 1 (single-event rule); or
  observed >= 1 and poisson_exceedance_p <= SIGNIFICANCE_ALPHA; or
  observed_rate / predicted_rate >= RATE_EXCEEDANCE_MIN; else not
  significant (with the reason "rate within expectation" when the tail
  probability is above alpha).
- corrective_route(verdict, exposure_adequate, trend_direction in
  {-1, 0, 1}) -> (route, urgency): route "airworthiness-directive-
  request" when a catastrophic single event or catastrophic rate
  exceedance occurred; "service-bulletin" when hazardous significant
  or major significant with increasing trend; "continued-monitoring"
  when significant minor or when not significant but exposure
  inadequate; "no-action" when not significant and exposure adequate
  and trend not increasing. Urgency band: "immediate" (catastrophic
  single event), "short-term" (hazardous significant), "scheduled"
  (major/minor), "routine" (no action / monitoring).
- assessment_summary(...) -> dict with all outputs for the SKILL
  worked example and report body.
ValueError on: negative exposure, negative predicted rate, unknown
severity strings, empty predictions, event with a condition_id missing
from predictions.

## Worked example

Fleet 200 aircraft, exposure 1,000,000 flight hours. Predictions:
- "FCS-1": predicted_rate 3e-7 per fh, severity hazardous (expected
  events 0.3),
- "PP-1": predicted_rate 2e-6 per fh, severity major (expected 2.0).
Events: 2 x "FCS-1" hazardous, 3 x "PP-1" major.
- observed FCS-1 rate 2e-6; expected 0.3; poisson_exceedance_p(2, 0.3)
  ~ 0.0369 (assert within 1e-3; the builder runs the module and asserts
  its real output): <= 0.05 -> significant; route service-bulletin,
  urgency short-term.
- PP-1: observed 3e-6 vs expected 2.0; poisson_exceedance_p(3, 2.0) ~
  0.3233 -> not significant on the tail; rate ratio 1.5 < 2.0 -> not
  significant; route no-action or continued-monitoring with adequate
  exposure.
- Single catastrophic event case: observed 1 x catastrophic condition
  -> immediate airworthiness-directive-request via the single-event
  rule even when the rate is low.
- Adequacy: FCS-1 expected 0.3 < 5 -> inadequate exposure note.
- ValueError on negative exposure and unknown severity.
Keep at least 16 test methods (grouping, rate math, Poisson tail
values, single-event rule, adequacy, route and urgency branches,
ValueErrors).

## Corpus tasks (ids w26-in-service-safety-assessment-1/2)

Distinctive tokens: in-service safety assessment, service difficulty
report, continued airworthiness, field event rate, fleet exposure,
ARP5150, observed versus predicted rate, single-event rule, service
bulletin, airworthiness directive request, safety significance.
Avoid: failure rate demonstration, chi-square, zero-failure rule,
test-hours (arp4761a failure-rate-estimation), FHA/PSSA/SSA of a new
design (safety-assessment), corrective action process (as9100).

1. "assess the in-service safety data for the fleet after 1 million
   flight hours: two hazardous events on the flight control condition
   against the predicted 3e-7 per hour rate, apply the single event
   rule, and route the corrective action with the urgency band"
2. "run the ARP5150 style continued airworthiness review of the
   service difficulty reports: group the field events by failure
   condition, compare the observed event rate with the SSA prediction,
   and decide whether a service bulletin or an airworthiness directive
   request is warranted"

## SKILL body notes

Pair with arp4761a safety-assessment (the predicted rates consumed
here), arp4761a failure-rate-estimation (the statistics sibling; do not
re-derive bounds), and certification mmel-development (dispatch relief
uses the same severity inputs). Compliance: ARP5150A/ARP5151 and
ARP4761A referenced by name and paraphrased at reference level only;
no reproduced text. This leaf opens the continued-airworthiness pack.
