---
name: e2008-protection-diode-characterization-test
description: "Determine whether an environmental test degraded a protection diode by reading the baseline and follow-up characterizations that bracket it, under ECSS-E-ST-20-08C clause 9.6.15: confirm both visits carry the whole required parameter set and the declared device count, take the junction temperature and test current gaps between them before any drift is judged, then take the forward voltage drift, the reverse leakage growth ratio, the breakdown voltage drop and the series resistance growth. Use when a pre and post environmental diode data pair is written or audited. Trigger: ecss, e-st-20-08c-clause-9-6-15, protection-diode-pre-post-bracket, diode-baseline-followup-parameter-set, diode-reference-condition-match, diode-breakdown-voltage-drop-fraction, diode-series-resistance-growth-fraction, protection-diode-degradation-verdict."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-protection-diode-characterization-test, protection-diode-pre-post-bracket, diode-baseline-followup-parameter-set, diode-reference-condition-match, diode-breakdown-voltage-drop-fraction, diode-series-resistance-growth-fraction, protection-diode-degradation-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Protection Diode Characterization Test (space-systems/ecss/e2008-protection-diode-characterization-test)

Use when the task is clause 9.6.15 of ECSS-E-ST-20-08C -- the pair of
electrical characterizations placed either side of an environmental
test. This clause describes no environment of its own. It describes the
bracket, because a protection diode almost never fails an environment
outright: it comes back working and slightly different, and the only
instrument that sees that is the same measurement taken twice under the
same conditions.

## Domain quick reference

- The comparison is the fragile part, not the measurement. Each visit on
  its own is routine; what carries the verdict is that the two are
  commensurable.
- Both visits have to carry the same parameter set. A follow-up missing
  one is not a smaller data set -- it is a parameter with no verdict,
  and an absent verdict reads as a pass in every summary downstream.
  The absence is reported, and no drift is derived for it.
- The same junction temperature and the same test current, both times.
  A protection diode's forward drop moves around two millivolts per
  kelvin, which swamps any degradation limit worth setting, so a few
  kelvin between the visits manufactures degradation that is not there
  and can equally mask the degradation that is. That is why a condition
  mismatch outranks the drift it would otherwise be reported as.
- The test current matters as much as the temperature. Read at a
  different point on the forward curve, the two drops are not the same
  quantity however well the temperatures were matched.
- Some parameters are only a finding in one direction. A breakdown
  voltage that fell is degradation; one that rose is not. Forward
  voltage is judged unsigned, breakdown by its drop, series resistance
  by its growth.
- Reverse leakage spans decades, so it is judged as a growth ratio
  against the baseline. A percentage of a picoamp is noise wearing a
  limit's clothing.
- A series resistance that grew is not a junction finding. It is a
  contact, a bond or a lead, and naming it that way is what routes the
  failure analysis to the right place.

## Workflow

1. Validate the characterization policy first: device floor, junction
   temperature gap, test current gap, and the four parameter limits. A
   leakage growth ceiling at or below one is refused rather than used.
2. Take the missing-parameter set for each visit and the bracketed
   device count. If anything is absent, close there -- an incomplete set
   outranks everything below it, because a drift derived over a hole is
   not a drift.
3. Take the junction temperature gap and the test current gap between
   the two visits before any parameter drift is judged.
4. Derive all four drifts: forward voltage unsigned, reverse leakage as
   a growth ratio, breakdown voltage as a drop fraction, series
   resistance as a growth fraction. Report them whatever the verdict, so
   a condition mismatch still hands the reviewer the numbers.
5. If the conditions did not match, close on the mismatch rather than on
   the drift it produced.
6. Otherwise hold each drift against its limit. A value landing exactly
   on a limit passes; the comparison tolerance absorbs representation
   error and the limit does not move. Report every finding, not the
   first, and close on degradation detected or characterization
   accepted.

## Pitfalls

- Treating a missing follow-up parameter as one fewer thing to check.
  It is the one parameter with no verdict, and the summary line that
  omits it is indistinguishable from a passing one.
- Comparing a warm follow-up against a room temperature baseline. Two
  millivolts per kelvin turns a sixty kelvin offset into a hundred and
  twenty millivolts of apparent degradation on a half-volt drop.
- Matching the temperature and letting the test current move. The
  forward drop is a point on a curve, and the two visits then read
  different points of it.
- Judging breakdown voltage unsigned. A breakdown that rose is not a
  finding, and flagging it buries the ones that fell.
- Expressing reverse leakage drift as a percentage. Leakage moves in
  decades, so a percentage either saturates or vanishes; the ratio is
  what carries the information.
- Reporting a series resistance growth as junction degradation. It
  points at a contact or a bond, and the distinction is what sends the
  failure analysis to the right place.
- Comparing a derived drift against its limit by bare arithmetic. The
  ratios and fractions land a few units in the last place either side of
  a limit on different hosts, so the comparison absorbs that error while
  the limit itself is never relaxed.

## Behavior contract (gate 3)

The policy validation, the missing-parameter and missing-condition
sets, the bracketed device count, the junction temperature and test
current gaps, the forward voltage relative drift, the reverse leakage
growth ratio, the breakdown voltage drop fraction, the series resistance
growth fraction, the one-directional parameters and the verdict order
are exercised by the gate 3 contract test:
scripts/test_e2008_protection_diode_characterization_test.py against
scripts/e2008_protection_diode_characterization_test_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_protection_diode_characterization_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
