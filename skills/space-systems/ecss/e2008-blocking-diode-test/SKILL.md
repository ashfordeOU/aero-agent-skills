---
name: e2008-blocking-diode-test
description: "Compute the reverse current a solar array blocking diode passes at the highest open-circuit voltage its string can reach in flight, under ECSS-E-ST-20-08C clause 5.5.3.3.6: build that worst-case bias from the cold-case cell open-circuit voltage, the series count and a beginning-of-life margin; refuse a bench whose applied reverse bias falls short of it, because an under-stressed diode proves nothing; refer every measured leakage to the reference junction temperature; group each diode as within limit, above limit or reverse-conducting; and total the parasitic loss the array then carries. Use when a blocking diode reverse-current test has to be set up, sentenced or repeated. Trigger: ecss, e-st-20-electrical-scope, blocking-diode-reverse-current, worst-case-open-circuit-voltage, blocking-diode-leakage-limit, reverse-bias-adequacy-check, solar-array-blocking-diode-screening."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-blocking-diode-test, blocking-diode-reverse-current, worst-case-open-circuit-voltage, blocking-diode-leakage-limit, reverse-bias-adequacy-check, solar-array-blocking-diode-screening, solar-array-parasitic-reverse-loss]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Blocking Diode Test (space-systems/ecss/e2008-blocking-diode-test)

Use when the task is the blocking diode test of ECSS-E-ST-20-08C clause
5.5.3.3.6 -- showing that the diode which stops a string draining the
bus still refuses to conduct backwards at the hardest reverse bias the
mission puts across it.

## Domain quick reference

- A blocking diode is bought for what it does not do. The only number
  that matters is the current it passes in the reverse direction, and
  that current is meaningless until the voltage it was measured at is
  stated alongside it.
- The reverse bias the diode has to stand is the open-circuit voltage of
  the string behind it. That voltage peaks when the string is
  illuminated, unloaded and cold -- eclipse exit is the classic case --
  so the test condition comes from the cold end of the thermal
  environment, not from the operating point.
- The cell open-circuit voltage coefficient is negative. A build record
  that declares it positive has a sign error, and taking it at face
  value moves the worst case to the hot end and understates the bias by
  the whole span of the environment.
- A bench that cannot reach the worst-case bias has not performed the
  test. Its result is not a weak pass, it is no evidence at all, so the
  campaign is reported as not evaluated and repeated at the right
  voltage rather than sentenced on what it produced.
- Reverse current roughly doubles for a fixed rise in junction
  temperature, so a reading taken on a cool bench is referred to the
  declared reference junction temperature before it meets a limit. A raw
  reading well inside the limit can sit well outside it once referred.
- Leakage is also a standing loss: every microampere flows against the
  full reverse bias for the whole mission, so the population total is
  converted to watts and compared with a budget.
- The limits, the reference temperature, the doubling interval and the
  loss budget are declared project policy rather than physical
  constants, so they are stated with the result.

## Workflow

1. Capture the flight case: series cell count, cell open-circuit voltage
   at its reference temperature, the temperature coefficient, the
   coldest illuminated temperature and the beginning-of-life margin.
   Reject a sign error in the coefficient instead of computing through
   it.
2. Build the worst-case reverse bias from that case. It is the number
   the bench has to reach and the number every leakage is quoted at.
3. Screen the applied bias against it. A shortfall stops the assessment
   before any diode is judged, and the shortfall is reported in volts so
   the retest is scoped.
4. Refer each measured reverse current from its measured junction
   temperature to the reference junction temperature using the declared
   doubling interval.
5. Group each diode: within limit, above limit, or reverse-conducting --
   the last being a part that has lost the blocking function outright
   and is a failure of the string, not of a limit.
6. Total the referred population current, convert it to a parasitic loss
   at the applied bias, and sentence the campaign against the limit, the
   grouping and the loss budget. Report each shortfall separately so the
   retest is scoped to the one that failed.

## Pitfalls

- Testing at the bus voltage or at a round bench number instead of the
  string open-circuit voltage. The diode then sees less reverse stress
  on the ground than it will in orbit, and the leakage recorded is a
  number about the bench.
- Taking the open-circuit voltage at the operating temperature. The
  string is coldest and unloaded at exactly the moment the blocking
  diode is most stressed, so an operating-point voltage understates the
  requirement by a wide margin.
- Quoting a leakage without its junction temperature. The same part
  reads a few microamperes cool and tens of microamperes hot, so an
  untemperatured reading cannot be compared with a limit or with another
  unit.
- Averaging the population. A blocking diode is a series element: one
  reverse-conducting part drains its whole string regardless of how
  quiet the others are, so the assessment is per unit and the total is
  only used for the loss budget.
- Comparing a referred current against the limit by bare arithmetic. The
  referral is a product with a fractional power, so a unit meant to sit
  exactly on the limit can land a few units in the last place above it;
  the comparison absorbs that representation error while the limit stays
  untouched.

## Behavior contract (gate 3)

The cold-case open-circuit voltage, the worst-case reverse bias, the
bias adequacy screen, the junction-temperature referral, the reverse
current grouping, the parasitic loss and the campaign verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_test.py against
scripts/e2008_blocking_diode_test_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_blocking_diode_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
