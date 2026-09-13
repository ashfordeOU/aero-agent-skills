---
name: e2001-measurement-temperature-range
description: "Use when verify that the emission-yield measurement temperature-range ECSS-E-ST-20-01C clause 9.4.1.4 leaves to the supplier is both defensible and customer-approved: normalise the declared and predicted-service ranges from kelvin or celsius, confirm the declared range envelops the in-service extremes and report the cold-end and hot-end margin, categorize the approval-state from the declaration, revision and approval dates, grade the measurement setpoints for endpoint-anchoring and interpolation-gap, and check the thermometry-uncertainty against the span it has to resolve. Flags a missing or superseded approval, an unmeasured range endpoint, and an absent range-justification. Trigger: ecss, e-st-20-electrical-scope, e2001-measurement-temperature-range, emission-yield-temperature-range, supplier-declared-range, customer-approval-state, setpoint-interpolation-gap, service-range-envelopment, thermometry-uncertainty."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-measurement-temperature-range, emission-yield-temperature-range, supplier-declared-range, customer-approval-state, setpoint-interpolation-gap, service-range-envelopment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Emission-Yield Measurement Temperature Range (space-systems/ecss/e2001-measurement-temperature-range)

Use when the task is the clause 9.4.1.4 check of ECSS-E-ST-20-01C: the
range over which emission yield is measured is defined by the supplier
and approved by the customer, so the check is that the declared range
covers the hardware in service, that the approval on record still applies
to the declaration on record, and that the measurement points inside the
range can actually carry an interpolated yield curve.

## Domain quick reference

- The clause deliberately leaves the range to the supplier: the right
  bracket depends on the material, the coating and the thermal design,
  not on a number the standard could fix. What is not left open is the
  obligation to state it, justify it, and have the customer approve it.
- Envelopment is the first test. The declared measurement range has to
  bracket the predicted in-service extremes at both ends; a range that
  stops short means the yield used in the multipactor-margin case at
  that extreme is an extrapolation, not a measurement. Margin is
  reported per end, so a comfortable hot end cannot mask a cold-end
  shortfall.
- Ranges arrive in kelvin or in celsius depending on the document, so
  both are normalised before anything is compared, and a value below
  absolute zero is rejected rather than carried.
- Approval is a two-party state with three outcomes: approved, pending,
  or superseded. Superseded is the one that gets missed — a declaration
  revised after the customer signed it carries an approval that no
  longer covers the range actually declared, which reads as an approval
  in a document list and is not one.
- Setpoint coverage decides whether the range is measured or merely
  spanned. Both declared endpoints need a setpoint within the endpoint
  tolerance, and no interior gap may exceed the interpolation limit,
  because yield varies smoothly but not linearly with surface
  temperature. A setpoint outside the declared range is a separate
  defect: it is data the declaration does not cover.
- Thermometry uncertainty is graded against the span it has to resolve,
  as a fraction rather than an absolute figure, so a narrow declared
  range demands a proportionately tighter sensor. An uncertainty that
  was never captured is a finding in its own right, not a pass.

## Workflow

1. Normalise the declared range and the predicted in-service range to
   kelvin, rejecting an inverted, degenerate or sub-absolute-zero record.
2. Compute cold-end and hot-end margin and decide envelopment. Report
   each shortfall separately, in kelvin.
3. Categorize the approval-state from the supplier declaration date, the
   revision date and the customer approval date. A record with no
   supplier declaration is rejected outright; an approval older than the
   revision it covers is superseded.
4. Grade the setpoints: sort and deduplicate, check both endpoints are
   anchored within tolerance, flag any interior gap wider than the
   interpolation limit, and flag any setpoint outside the declared range.
5. Check the thermometry uncertainty against its allowed share of the
   declared span; treat an absent value as a finding.
6. Confirm a written rationale for the range exists, then aggregate. The
   declared range satisfies the clause only when the finding list is
   empty.

## Pitfalls

- Reading "supplier defined" as "supplier discretion" — the range is the
  supplier's to choose and the customer's to approve, and an unapproved
  range leaves every yield-derived margin unsubstantiated.
- Counting a signed approval without checking what it approved: a
  declaration revised after the signature is the common way a compliant
  document list hides a non-compliant range.
- Declaring a wide range and measuring three points inside it — the
  curve between setpoints is interpolated, so an interior gap wider than
  the interpolation limit is an unmeasured band, even though both
  endpoints were tested.
- Comparing the declared range against a qualification range instead of
  the predicted in-service range, which usually flatters the cold end.
- Letting a boundary case fail on representation: a declared endpoint
  that equals the in-service endpoint, or a setpoint ladder whose
  accumulated step lands a few units in the last place above the gap
  limit, is compliant, and the tolerance belongs in the comparison, never
  in a widened limit.
- Quoting a sensor accuracy in kelvin and calling it adequate without
  reference to the span — the same sensor that comfortably resolves a
  wide range can consume the whole budget of a narrow one.

## Behavior contract (gate 3)

The unit-normalisation, envelopment, margin, approval-state,
setpoint-coverage and thermometry logic is exercised by the gate 3
contract test: scripts/test_e2001_measurement_temperature_range.py
against scripts/e2001_measurement_temperature_range_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_measurement_temperature_range.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
