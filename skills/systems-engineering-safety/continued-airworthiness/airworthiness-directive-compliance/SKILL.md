---
name: airworthiness-directive-compliance
description: "Use when you must evaluate airworthiness directive compliance: test each aircraft in an operator fleet against the directive effectivity by affected model and serial range, compute the remaining compliance margin in the directive's own basis (flight cycles, flight hours, or calendar months from the effective date), classify each aircraft as open, due, or overdue against the directive grace band, and roll up the per-directive fleet compliance report with applicable, open, due and overdue counts and the strict compliance rate. Produces per-aircraft statuses and the fleet report. Trigger: airworthiness directive, AD applicability, directive effectivity, compliance margin, compliance time remaining, grace band, due aircraft, overdue aircraft, fleet compliance report, mandatory airworthiness action."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: continued-airworthiness
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: continued-airworthiness
  tags: [airworthiness-directive-compliance, ad-applicability, compliance-time, compliance-grace-band, fleet-compliance-report, directive-effectivity]
  version: 0.1.0
  author: AeroSkills
---

# Airworthiness Directive Compliance (systems-engineering-safety/continued-airworthiness/airworthiness-directive-compliance)

Use when issued airworthiness directives must be checked against the
operator fleet: which aircraft fall inside the directive effectivity,
how much compliance margin each one has left in the directive's own
basis, and how the fleet rolls up against the grace band. This leaf
implements the compliance-evaluation model in pure Python, stdlib only:
applicability by affected model and serial range, margin as value minus
elapsed usage (cycles, hours, or calendar days converted from months),
per-aircraft status open / due / overdue, and the per-directive fleet
report with counts and the strict compliance rate. It sits in the
continued-airworthiness pack with in-service-safety-assessment, whose
field-experience corrective-action route can issue a directive request
when an operator has none to evaluate yet; it does not judge field
rates, derive routine tasks, or touch design change control.

## Domain quick reference

- AD record shape: {id, affected_models: [str], affected_serials:
  [(lo, hi), ...], basis: "cycles" | "hours" | "calendar", value:
  float > 0, grace: float >= 0, effective_date: "YYYY-MM-DD"}.
- Aircraft record shape: {model, serial, cycles_since_last_action,
  hours_since_last_action, last_action_date or None}.
- Applicability: an aircraft is applicable when its model is in
  affected_models (whole-model effectivity) or its serial falls inside
  any (lo, hi) serial range (serial-specific effectivity). Serials
  compare as strings, so they must be zero-padded to a common width.
- Compliance margin: remaining = value - elapsed. Elapsed for an
  event-basis AD is the cycles or hours since the last action on that
  aircraft; for calendar basis it is the whole days from the effective
  date to as_of, with DAYS_PER_MONTH = 30.4375 so value_days =
  value * 30.4375.
- Status rule: remaining > 0 -> open (margin remains); -grace <=
  remaining <= 0 -> due (past the compliance point, inside the grace
  band); remaining < -grace -> overdue. The grace band is in the same
  unit as the margin: raw cycles or hours for the event bases, days for
  calendar.
- Fleet report: {ad_id, basis, applicable, open, due, overdue,
  compliance_rate}, with compliance_rate = open / applicable exactly
  and None when no aircraft in the list is applicable. Identity:
  open + due + overdue = applicable; a non-applicable aircraft never
  appears in the counts.
- Regulatory frame: an AD amends the type design certified under FAR
  Part 25, and operator compliance sits in the 14 CFR 39 and 91 frame;
  this leaf evaluates the directive record against aircraft records and
  does not reproduce the directive text. Standards are reference-only.

## Workflow

1. Assemble the AD record for the directive under review (id,
   affected_models, affected_serials, basis, value, grace, and
   effective_date for calendar basis) and the aircraft records with
   their since-last-action counters; fix as_of as a datetime.date.
2. Screen the fleet with ad_applies: model hit or serial-range hit is
   applicable; a serial outside every range and a model outside the
   effectivity list drops out of the review entirely.
3. Compute the margin for each applicable aircraft with
   remaining_units; positive means the compliance point is ahead.
4. Classify with compliance_status: open when margin remains, due when
   past the point but inside the grace band, overdue beyond it.
5. Roll up with fleet_ad_review for the per-directive report and check
   the identity open + due + overdue == applicable and the rate.
6. Confirm the deterministic checks with the contract test
   scripts/test_airworthiness-directive-compliance.py.

## Worked example

AD-2024-001: models ["T-100"], basis cycles, value 4000, grace 200.
Fleet: ac1 T-100/001 at 3500 cycles, ac2 T-100/002 at 4200, ac3
T-100/003 at 4550, ac4 T-200/009, and ac5 T-100/004 at 3500. Real
module outputs:

- ad_applies: ac1, ac2, ac3, ac5 True; ac4 False (model T-200 not
  affected).
- remaining_units on 2026-02-01: ac1 500.0 (4000 - 3500), ac2 -200.0,
  ac3 -550.0, ac5 500.0. All four magnitude bounds from the spec hold.
- compliance_status: ac1 open, ac2 due (-200.0 inside [-200, 0]), ac3
  overdue (-550.0 below -200), ac5 open.
- fleet_ad_review: applicable 4, open 2, due 1, overdue 1,
  compliance_rate 0.5 exactly; ac4 never appears in the counts.

AD-2024-002: models ["T-100"], basis calendar, value 24, grace 3,
effective_date 2024-01-15. Real module outputs on 2026-02-01 (748
elapsed days): value_days 730.5, remaining -17.5, status due (inside
grace_days 91.3125). On 2027-06-01 (1233 elapsed days): remaining
-502.5, status overdue.

## Verification

- Confirm ad_applies(AD-2024-001, ac4) is False and True for the four
  T-100 aircraft; serial-range effectivity includes both bounds.
- Confirm remaining_units returns 500.0, -200.0, -550.0 for ac1, ac2,
  ac3 and -17.5 / -502.5 for the two calendar anchors.
- Confirm compliance_status boundaries: remaining exactly 0 is due;
  remaining exactly -grace is due; anything below -grace is overdue.
- Confirm the fleet report identity open + due + overdue == applicable,
  compliance_rate == open / applicable, and compliance_rate is None
  when nothing is applicable (never a misleading 0).
- Confirm ValueError rejection of an unknown basis, non-positive value,
  negative grace, an empty aircraft list, and records missing required
  keys; calendar basis without a valid effective_date also raises.
- Run the contract test offline: python3
  scripts/test_airworthiness-directive-compliance.py (34 tests,
  deterministic).

## Related leaves

- systems-engineering-safety/continued-airworthiness/in-service-safety-
  assessment: the field-experience route that can issue a directive
  request when field rates are safety-significant; this leaf evaluates
  compliance with a directive that is already issued.
- systems-engineering-safety/continued-airworthiness/ica-cmr-ali-
  classification: ALS/CMR items born with the type certificate, not
  post-cert directives.
- systems-engineering-safety/continued-airworthiness/msg3-maintenance-
  analysis: routine scheduled task derivation, distinct from mandatory
  directive action.
- systems-engineering-safety/certification/mmel-development: dispatch
  relief context when an aircraft is unairworthy.
- systems-engineering-safety/arp4754a/configuration-management: design
  change control for the type design that directives amend.

## Pitfalls

- Comparing unpadded serials: "9" does not sort inside ("001", "050")
  under string compare, so aircraft serials and range bounds must share
  a zero-padded width before ad_applies is trusted.
- Measuring a calendar directive from the last action: the model's
  compliance clock runs from the AD effective date, (as_of -
  effective_date).days, so all aircraft in the fleet share the same
  calendar margin on a given as_of.
- Leaving grace in months for a calendar basis: the margin is in days
  (value_days - elapsed_days), so grace must be converted too, grace *
  30.4375, or the band is 30 times too narrow.
- Reading a 0 compliance rate when nothing applies: compliance_rate is
  None for a zero-applicable review; a bare 0.0 would claim total
  non-compliance where no obligation exists.
- Calling a due aircraft compliant: due means the compliance point is
  already passed and action is required now, only the grace band keeps
  it out of the overdue class.
- Forgetting to reset the event counters: cycles_since_last_action and
  hours_since_last_action are since the last action, so they must be
  zeroed at the action before the next margin is computed.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_airworthiness-directive-compliance.py

The test covers the worked-example contract (remaining 500.0, -200.0,
-550.0 and -17.5 / -502.5; fleet report applicable 4, open 2, due 1,
overdue 1, rate 0.5), the applicability truth table including serial
range bounds, the status boundaries (exactly 0 and exactly -grace are
due), calendar day arithmetic anchored at 748 and 1233 elapsed days,
the fleet identities, ValueError rejection of an unknown basis,
non-positive value, negative grace, empty aircraft list and missing
record keys, exact dict keys, and run-to-run determinism.

## Compliance

- Standards referenced, not reproduced: FAR Part 25 frames the type
  design that directives amend; the compliance model above is standard
  engineering methodology, summary-only per standards-map.yaml. The
  directive text and the 14 CFR 39 / 91 rule text are never reproduced.
- compliance: STANDARDS-REF, gated: false.
