---
name: e2040-support-maintenance-plan-data-item
description: "Evaluate a device support and maintenance plan against the required contents of ECSS-E-ST-20-40C Annex E before delivery is accepted. Use when the plan has to state the after-delivery service, the upkeep regime and the obsolescence position across a stated service life: grade each response-time commitment against the contracted one, compute how often every upkeep task falls due over that life, measure the years a part stands unsupported beyond its last-time-buy date, size the lifetime-buy quantity from consumption, attrition and stock on hand, and categorize each part as monitor, lifetime-buy or alternate-source. Trigger: ecss, e-st-20-40-device-scope, e2040-support-maintenance-plan-data-item, after-delivery-service-commitment, upkeep-interval-coverage, obsolescence-last-time-buy-gap, lifetime-buy-sizing, support-plan-drd."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-support-maintenance-plan-data-item, after-delivery-service-commitment, upkeep-interval-coverage, obsolescence-last-time-buy-gap, lifetime-buy-sizing, support-plan-drd]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Support and Maintenance Plan Data Item (space-systems/ecss/e2040-support-maintenance-plan-data-item)

Use when the task is the required contents of the device support and
maintenance plan of ECSS-E-ST-20-40C Annex E -- establishing that the
plan says what service the supplier owes after delivery, what upkeep the
device needs to stay usable, and what happens to each part when its
manufacturer stops making it.

## Domain quick reference

- The **service life** is the horizon the whole plan is measured
  against. A commitment, an upkeep interval or a stock position is
  neither adequate nor inadequate on its own; it is adequate only
  relative to the number of years the device is to stay supportable.
- An **after-delivery service commitment** is a response time the
  supplier owes for a named service class. It is gradeable only when
  the plan states both the offered response time and the contracted
  one, in the same unit; an offered time equal to the contracted time
  meets it, and the comparison absorbs representation error rather than
  loosening the contracted figure.
- An **upkeep task** falls due on a fixed interval. The number of
  occurrences across the service life is the whole number of intervals
  that fit inside it, so a task on a 30-month interval falls due twice
  in 72 months, not 2.4 times. A plan declaring a different count has
  either the interval or the resource estimate wrong.
- The **last-time-buy date** ends resupply, not use. The years between
  that date and the end of the service life are the unsupported window,
  and the quantity that has to be bought before the window opens is
  consumption across the window, grossed up for attrition, less the
  stock already held.
- A part with an unsupported window is **categorized** by how large the
  buy would have to be, not by how far away the date is: a buy inside
  the storable quantity is a lifetime-buy, a buy above it needs an
  alternate source or a redesign, and a part supported past the end of
  life needs only monitoring.

## Workflow

1. Check the plan's section list against the required contents and name
   each absent section before grading anything inside the plan.
2. Validate the service life in months; a zero or negative life makes
   every downstream quantity meaningless and is an input error.
3. For each service commitment, validate the offered and contracted
   response times and grade the commitment, treating an offered time
   equal to the contracted one as met within a named tolerance.
4. For each upkeep task, validate a positive interval and compute the
   occurrences that fall due inside the service life. Compare with the
   declared count and raise a finding on any mismatch.
5. For each obsolescence item, compute the unsupported window in years
   from the last-time-buy date to the end of the service life, floored
   at zero for a part supported throughout.
6. Size the lifetime-buy quantity as consumption over the window,
   grossed up by the attrition fraction, less stock on hand, rounded up
   to a whole unit with a tolerance so a quantity that lands on an
   integer is not pushed to the next one.
7. Categorize each item as monitor, lifetime-buy or alternate-source
   against the storable quantity, and report the unmet commitments,
   interval mismatches and alternate-source items as findings.

## Pitfalls

- Reading a last-time-buy date far in the future as no exposure. What
  matters is whether the date falls before the end of the service life,
  and a long-lived device can outlive a date a decade away.
- Sizing a lifetime buy from consumption alone. Attrition in storage,
  screening and assembly is what turns a nominally sufficient buy into
  a shortfall years later, and stock already held is what keeps the buy
  from being double-counted.
- Rounding a lifetime-buy quantity up from a floating-point product
  that should have been a whole number. A quantity landing on an
  integer within tolerance is that integer; rounding it up buys a part
  nobody needs and, worse, hides the arithmetic error underneath.
- Prorating an upkeep interval into a fractional occurrence count. A
  task either falls due inside the life or it does not, and the
  resource estimate has to be built on whole occurrences.
- Grading a response-time commitment with the units left implicit. An
  offered figure in days against a contracted figure in hours passes
  every naive comparison and means the opposite of what it appears to.

## Behavior contract (gate 3)

The section check, service-life validation, response-time grading,
upkeep-occurrence computation, unsupported-window measurement,
lifetime-buy sizing with tolerant rounding and the mitigation
categorization are exercised by the gate 3 contract test:
scripts/test_e2040_support_maintenance_plan_data_item.py against
scripts/e2040_support_maintenance_plan_data_item_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_support_maintenance_plan_data_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
