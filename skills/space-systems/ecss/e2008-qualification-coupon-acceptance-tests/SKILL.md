---
name: e2008-qualification-coupon-acceptance-tests
description: "Use when decide whether a lot of solar-array qualification coupons passes the acceptance testing ECSS-E-ST-20-08C clause 5.5.2 places on supplier workmanship: size the coupon sample the delivered lot has to be represented by, evaluate every acceptance measurement -- interconnect peel strength, joint resistance, illuminated power -- against its limit in the correct direction of merit, express each result as a margin fraction so different units compare, group the observed workmanship imperfections into critical, major and minor grades and check each total against its allowance, then accept the lot only when sample size, coupon results and imperfection grades all hold. Trigger: ecss, e-st-20-08c-clause-5-5-2, qualification-coupon-acceptance-testing, solar-array-supplier-workmanship, coupon-sample-size, interconnect-peel-strength, workmanship-imperfection-grades, coupon-lot-acceptance."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-qualification-coupon-acceptance-tests, qualification-coupon-acceptance-testing, solar-array-supplier-workmanship, coupon-sample-size, interconnect-peel-strength, workmanship-imperfection-grades]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Qualification Coupon Acceptance Tests (space-systems/ecss/e2008-qualification-coupon-acceptance-tests)

Use when the task is the clause 5.5.2 acceptance testing of ECSS-E-ST-20-08C
-- deciding whether the qualification coupons a supplier delivers with a lot
demonstrate the workmanship quality the lot was bought on, on the strength of
the measurements taken on those coupons and the imperfections found on them.

## Domain quick reference

- A qualification coupon is not a sample of the product; it is a witness of
  the process that built the product. Its value is that it was laid up,
  welded, bonded and cured alongside the flight hardware, so what it shows
  is what the process was doing that day.
- Acceptance checks come in two directions of merit and mixing them is the
  most common arithmetic error: peel strength and illuminated power have to
  reach their limit, joint resistance and mass have to stay under theirs.
  A single signed margin is only meaningful once the direction is attached
  to it.
- Expressing each result as a fraction of its own limit puts newtons per
  centimetre, milliohms and watts on one scale, so a lot can be read at a
  glance and a marginal check is visible next to a comfortable one.
- Workmanship imperfections are counted by severity grade, and the grades
  carry different allowances: a critical imperfection is usually allowed
  zero times, a minor one several. Totalling them into a single defect count
  destroys exactly the distinction the allowances exist to make.
- Sample size is part of the acceptance argument. A conforming coupon says
  nothing about a lot it is too small to represent, so the sample the lot
  demands is computed from the lot, not from how many coupons happened to
  arrive.

## Workflow

1. Size the sample: take the larger of the sampling fraction applied to the
   lot and the floor the specification sets, then cap it at the lot itself.
   Guard the ceiling against a float product that lands a hair above a whole
   number, or a clean lot buys an extra coupon it never owed.
2. Validate the acceptance criteria: every entry needs a name, a non-zero
   limit and a direction of merit, and no name may appear twice.
3. For every coupon, evaluate every criterion, refusing a coupon that carries
   no measurement for a declared check rather than scoring it absent.
4. Compute each margin as a fraction of the limit, and treat a measurement
   sitting exactly on its limit as conforming through a named tolerance,
   not by shifting the limit.
5. Group the imperfections found across the sample by severity grade and
   compare each grade total with its own allowance.
6. Accept the lot only when the sample was large enough, no coupon failed a
   check, and no grade exceeded its allowance; report which gate the lot
   fell at, and the fraction of coupons that conformed.

## Pitfalls

- Reading a margin without its direction of merit. A resistance 40 percent
  under its ceiling and a peel strength 40 percent under its floor produce
  the same unsigned number and opposite verdicts.
- Judging the lot on the coupons that arrived. A supplier who sends three
  coupons for a lot of two hundred has not demonstrated the lot, however
  well those three measure; the sample gate is independent of the results
  gate and both have to be reported.
- Collapsing severity grades into a defect count. One critical imperfection
  and six minor ones is not seven imperfections; it is a rejected lot next
  to an accepted one.
- Silently scoring a missing measurement as a pass. A criterion with no
  measurement on a coupon is an incomplete acceptance record and has to be
  refused, because the alternative is a lot accepted on data that was never
  taken.
- Accepting a coupon that sits a few ULPs below its limit as a failure. The
  boundary case is a representation question handled by the tolerance inside
  the comparison; the specification limit itself stays where it is.

## Behavior contract (gate 3)

The sample sizing, criteria validation, direction-of-merit margin
computation, per-coupon evaluation, severity grouping against allowances and
the three-gate lot decision are exercised by the gate 3 contract test:
scripts/test_e2008_qualification_coupon_acceptance_tests.py against
scripts/e2008_qualification_coupon_acceptance_tests_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_qualification_coupon_acceptance_tests.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
