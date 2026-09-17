---
name: q6013-thermistor-procurement-test-table
description: "Evaluate a declared thermistor procurement test matrix against the ECSS-Q-ST-60-13C Table 8-8 programme: confirm every required test group is present and none is declared twice, resolve each row's sample size from a whole-lot, fixed or percent-of-lot rule without gaining a device to rounding, derive the beta constant from a two-point resistance reading, predict the resistance the device reaches at another temperature, and judge reference-resistance tolerance, beta tolerance, post-stress resistance drift, dissipation constant and insulation resistance against their limits in the written direction. Use when a thermistor lot's test table has to become an accept or hold verdict. Trigger: ecss, q-st-60-13c-table-8-8, thermistor-procurement-test-matrix, thermistor-beta-constant-tolerance, thermistor-resistance-drift-limit, thermistor-dissipation-constant, thermistor-lot-sampling-rule, thermistor-row-accept-number."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-thermistor-procurement-test-table, thermistor-procurement-test-matrix, thermistor-beta-constant-tolerance, thermistor-resistance-drift-limit, thermistor-dissipation-constant, thermistor-lot-sampling-rule, thermistor-row-accept-number]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Parts -- Thermistor Procurement Test Matrix (space-systems/ecss/q6013-thermistor-procurement-test-table)

Use when the task is the Table 8-8 procurement test matrix of
ECSS-Q-ST-60-13C: a lot of thermistors has a declared programme of test
groups, methods, sample sizes and acceptance limits, and the question is
whether that programme is complete and whether its results accept or hold
the lot.

## Domain quick reference

- A thermistor row is only meaningful when all three parts are present: the
  test group (what is stressed), the method reference (how it is run) and
  the sampling rule with its accept number (on how many devices, and how
  many may fail). A group with no method is a declaration of intent, not a
  test.
- The device under procurement is not described by one number. A
  negative-temperature-coefficient thermistor carries a reference
  resistance quoted at a stated temperature AND a beta constant that sets
  how steeply that resistance falls as temperature rises. Two lots can hold
  the same reference resistance and behave differently everywhere else.
- Beta is not measured directly; it is reduced from two resistance readings
  at two temperatures, through the logarithm of their ratio over the
  difference of the reciprocal absolute temperatures. Readings taken at one
  temperature, or a pair whose resistance rose with temperature, are a
  measurement or polarity error rather than an unusual device.
- Both halves of the characteristic carry their own procurement tolerance,
  and they fail independently. A part on nominal resistance with a beta two
  percent off specification meets its resistance limit and still misses the
  temperature it was bought to sense at.
- Sample sizes are written three ways: a screen over the whole lot, a fixed
  sample for a characterisation test, and a percentage of the lot with a
  floor so a small lot is not sampled into one device. A percentage resolves
  to whole devices by rounding up, and the representation error of the
  product is absorbed before that rounding.
- Limits are directional. Dissipation constant and insulation resistance
  carry lower bounds, thermal time constant an upper one, and resistance
  drift a bound on a magnitude that may move either way. One direction
  applied across the row inverts half the verdicts.

## Workflow

1. Validate the lot the matrix applies to; a zero or negative device count
   is an input error, and no sample may be drawn larger than its lot.
2. Check coverage: every required thermistor group present, each declared
   once, and any group outside the required set reported as an addition
   rather than counted towards coverage.
3. Reduce the characteristic first. Derive beta from the two-point reading,
   compare the measured reference resistance and the derived beta with
   their procurement tolerances, and predict the resistance at any check
   temperature the matrix names.
4. Resolve each row's sample size from its rule -- whole lot, fixed sample,
   or percentage with a floor -- rounding up to whole devices and absorbing
   the representation error of the product before the rounding.
5. Refuse a row whose failures or accept number exceed the sample it was
   drawn from; those are bookkeeping errors, not results to be clamped.
6. Take each row's failures against its accept number, then each measured
   parameter against its limit in the direction it is written in, absorbing
   an exact equality at the limit with a named tolerance.
7. Hold the lot when any row rejects or the characteristic misses its
   tolerance, naming every rejecting group rather than the first, and report
   a row that consumed its accept number in full as a marginal advisory
   alongside the accept.

## Pitfalls

- Judging the lot on the resistance measurement alone. Beta is the second
  half of the characteristic and fails on its own, so a part on nominal
  resistance can still be the wrong device.
- Deriving beta from two readings that are too close together in
  temperature. The reciprocal-temperature difference is the denominator,
  and a narrow span amplifies the measurement noise of both readings into
  the derived value.
- Rounding a percentage sample down, or letting the floating-point product
  round it up by one device. The first under-tests the lot; the second makes
  the matrix look stricter than the one that was declared.
- Reading every limit as an upper bound. Dissipation constant and insulation
  resistance are floors and resistance drift is a magnitude, so a single
  direction across the row inverts several verdicts.
- Accepting a matrix that declares a group twice. Two methods against one
  group is two programmes; the lot must be judged against one, declared
  before the results are in.
- Comparing a computed exponential against a bound with a strict inequality.
  The exponential is not correctly rounded, so an equality at the limit is
  absorbed by the tolerance inside the comparison instead.

## Behavior contract (gate 3)

The lot validation, Kelvin conversion, two-point beta derivation, resistance
prediction, sampling-rule resolution, directional limit comparison, matrix
coverage, per-row verdict and the overall accept-or-hold disposition are
exercised by the gate 3 contract test:
scripts/test_q6013_thermistor_procurement_test_table.py against
scripts/q6013_thermistor_procurement_test_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_thermistor_procurement_test_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
