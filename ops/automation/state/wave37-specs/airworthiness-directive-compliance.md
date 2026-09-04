# Wave-37 leaf spec: airworthiness-directive-compliance (systems-engineering-safety, continued-airworthiness pack)

- Path: skills/systems-engineering-safety/continued-airworthiness/airworthiness-directive-compliance/
- Pack: continued-airworthiness. Closest siblings: in-service-safety-
  assessment (field event rates vs predicted; its corrective-action route
  OUTPUTS an airworthiness-directive-request when field experience is
  safety-significant - it does NOT evaluate an operator's compliance with
  an issued directive), ica-cmr-ali-classification (ALS/CMR items from the
  type certificate, not post-cert directives), msg3-maintenance-analysis
  (routine scheduled tasks, not mandatory directives), mmel-development
  (dispatch relief), arp4754a/configuration-management (change control).
  Whole-tree grep: "airworthiness directive" has ZERO owning leaf hits
  other than the in-service-safety-assessment route mention (its tag
  airworthiness-directive-request is a corrective-action output). ZERO
  owners of the compliance-evaluation function. GENUINE gap in the
  CEO-named airworthiness-management vein (wave-36 broke the SES streak
  with ica-cmr-ali-classification in this same pack).
- Standards id: far-25 (reference-only; ADs amend the type design
  certified under Part 25 and operator compliance is 14 CFR 39 / 91
  context; Part 39 itself is not in standards-map.yaml). Ledger Standard:
  far-25.
- Family: systems-engineering-safety

## Claim

Evaluate whether issued airworthiness directives apply to an operator
aircraft and roll up the fleet compliance position: test applicability by
affected model and serial range, compute the remaining compliance margin
in the directive's own basis (flight cycles, flight hours, or calendar
time from the effective date), classify each aircraft as open (margin
remaining), due (past the compliance point but inside the grace band), or
overdue (past the grace band), and produce the per-directive fleet report
with applicable, open, due and overdue counts and a strict compliance
rate. Does NOT do: field-rate versus predicted-rate safety assessment and
AD/SB request routing (in-service-safety-assessment); ALI/CMR/ALS
classification from certification data (ica-cmr-ali-classification);
MSG-3 task derivation (msg3-maintenance-analysis); MEL dispatch relief
(mmel-development); design change control (configuration-management).

## Model (implement exactly)

Conventions: an AD is a dict {id: str, affected_models: [str],
affected_serials: [(lo, hi), ...], basis: "cycles" | "hours" |
"calendar", value: float > 0, grace: float >= 0, effective_date:
"YYYY-MM-DD"}. An aircraft is a dict {model: str, serial: str,
cycles_since_last_action: float, hours_since_last_action: float,
last_action_date: "YYYY-MM-DD" or None}. elapsed for an event-basis AD is
cycles_since_last_action (basis cycles) or hours_since_last_action (basis
hours); for calendar basis, elapsed days = (as_of - effective_date).days
and the value and grace are converted with DAYS_PER_MONTH = 30.4375
(value_days = value * DAYS_PER_MONTH, grace_days = grace *
DAYS_PER_MONTH).

Functions (pure stdlib; as_of passed as datetime.date):
- ad_applies(ad, aircraft) -> bool: model in affected_models OR any lo <=
  serial <= hi (string compare on zero-padded serials).
- remaining_units(ad, aircraft, as_of) -> float: value - elapsed for
  event basis; value_days - elapsed_days for calendar basis.
- compliance_status(ad, aircraft, as_of) -> "open" | "due" | "overdue":
  remaining > 0 -> open; -grace <= remaining <= 0 -> due; remaining <
  -grace -> overdue (grace is in the same unit as the remaining value:
  raw units for event basis, days for calendar basis).
- fleet_ad_review(ad, aircraft_list, as_of) -> dict {ad_id, basis,
  applicable: n, open: n, due: n, overdue: n, compliance_rate:
  open/applicable}. ValueErrors: basis not in the three, value <= 0,
  grace < 0, empty aircraft_list, aircraft missing required keys.

Identity to test: open + due + overdue == applicable; compliance_rate =
open / applicable exactly; a non-applicable aircraft never appears in the
counts.

## Worked example

AD-2024-001: models ["T-100"], basis "cycles", value 4000, grace 200.
- ac1 T-100/001 cycles_since_last_action 3500 -> remaining 500 -> open
- ac2 T-100/002 cycles_since_last_action 4200 -> remaining -200 -> due
- ac3 T-100/003 cycles_since_last_action 4550 -> remaining -550 -> overdue
- ac4 T-200/009 -> ad_applies False (model not affected)
AD-2024-002: models ["T-100"], basis "calendar", value 24, grace 3,
effective_date "2024-01-15". as_of 2026-02-01: elapsed 748 days,
value_days 730.5 -> remaining -17.5 -> due (within grace_days 91.3125).
as_of 2027-06-01: elapsed 1233 days -> remaining -502.5 -> overdue.
Run your module and take the real outputs as assert targets; bounds
independently verified at prep: the four remaining values above and the
fleet report for the AD-2024-001 fleet (ac1..ac3 + one T-100 aircraft
with 500 cycles remaining) = applicable 4, open 2, due 1, overdue 1,
compliance_rate 0.5.

## Validation list (contract test must include)

- ValueError: unknown basis ("landings"), value 0 or negative, grace
  negative, empty aircraft list.
- Applicability truth table: model hit, serial-range hit, neither.
- Status truth table: open / due / overdue boundaries (remaining exactly
  0 -> due; remaining exactly -grace -> due; below -grace -> overdue).
- Calendar arithmetic: 2024-01-15 + 24 months anchor (748 elapsed days on
  2026-02-01 gives remaining -17.5).
- Identity: counts sum to applicable; compliance_rate = open/applicable.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave37-airworthiness-directive-compliance.yaml)

Query 1 (copy verbatim):
  "check airworthiness-directive-compliance for the fleet by applicability and compliance-time remaining in cycles or calendar months"
  intent: "systems-engineering-safety; AD applicability and compliance margin evaluation"
  expected_skill: "systems-engineering-safety/continued-airworthiness/airworthiness-directive-compliance"
Query 2 (copy verbatim):
  "roll up the airworthiness-directive fleet report with open due and overdue aircraft against the directive grace band"
  intent: "systems-engineering-safety; per-directive fleet compliance report"
  expected_skill: "systems-engineering-safety/continued-airworthiness/airworthiness-directive-compliance"
Task ids: w37-airworthiness-directive-compliance-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must evaluate airworthiness directive
compliance:" and include the outputs in the Claim. First tag:
airworthiness-directive-compliance. Additional tags ONLY:
ad-applicability, compliance-time, compliance-grace-band, fleet-
compliance-report, directive-effectivity. NEVER single generic words
(directive, compliance, fleet, aircraft, maintenance, inspection).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): field event rate, service
difficulty report, observed versus predicted, single-event rule, AD/SB
request route (in-service-safety-assessment); ALS coverage, life-limited
part, CMR (ica-cmr-ali-classification); MSG-3, visibility, consequence
(msg3-maintenance-analysis); dispatch relief, MEL (mmel-development);
change request, impact analysis (configuration-management).
