---
name: e2008-shunt-diode-test
description: "Use when a shunt diode forward-voltage test has to be set up, sentenced or repeated. Determine the forward voltage each shunt diode drops while the string it protects is driven backwards, under ECSS-E-ST-20-08C clause 5.5.3.3.7: check the forced drive reaches the worst-case string current the diode exists to carry, refer every measured drop to the reference junction temperature with the declared coefficient, group each part as conducting, suspect-shorted, suspect-degraded or open-circuit from where its referred drop falls, compute the dissipation the drive imposes, and charge any string drop the diode inventory cannot explain to a resisting joint. Trigger: ecss, e-st-20-electrical-scope, shunt-diode-forward-voltage, reverse-mode-string-drive, shunt-diode-conduction-window, open-shunt-diode-detection, solar-array-shunt-diode-screening."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-shunt-diode-test, shunt-diode-forward-voltage, reverse-mode-string-drive, shunt-diode-conduction-window, open-shunt-diode-detection, solar-array-shunt-diode-screening, shunt-diode-dissipation-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Shunt Diode Test (space-systems/ecss/e2008-shunt-diode-test)

Use when the task is the shunt diode test of ECSS-E-ST-20-08C clause
5.5.3.3.7 -- proving that the diode which carries a shadowed or failed
section actually conducts, which can only be seen by driving the
protected string in reverse mode.

## Domain quick reference

- A shunt diode does nothing for the whole mission until the day it has
  to carry the entire string current around a section. Nothing on the
  illuminated side of the array reveals whether it will, so the test
  forces current backwards through the protected string and reads the
  drop the diode develops.
- The reading only means something with its two conditions attached: the
  current it was taken at, and the junction temperature it was taken at.
  A drop quoted bare is not a measurement, it is a number.
- The forced current has to reach the worst-case string current the
  diode is there to carry. A gentle drive parks the junction at a knee
  it will never occupy in flight, and the drop it produces flatters the
  part.
- A silicon forward drop falls as the junction warms, so the coefficient
  is negative and every reading is referred to the declared reference
  temperature before it meets a window. A coefficient declared positive
  is a sign error; correcting with it turns a hot marginal part into an
  apparently healthy one.
- Where the referred drop falls names the fault. Below the window the
  junction is not developing a drop, so the protected section is shunted
  whenever it is lit -- a permanent power loss, not a dormant one. Above
  the window means added series resistance, a damaged junction or the
  wrong part. Far above means the drive is pushing against a broken path
  and no diode is conducting at all.
- Summing the drops of the driven string and comparing that with the
  voltage the supply actually had to develop catches a drop the diode
  inventory does not account for: a resisting joint in the reverse path
  that no per-diode reading would show.
- The window, the reference temperature, the coefficient and the
  dissipation budget are declared project policy rather than physical
  constants, so they are stated with the result.

## Workflow

1. Capture the flight case: the worst-case string current the shunt path
   has to carry when its section is shadowed or has failed.
2. Screen the forced drive against it. A shortfall stops the assessment
   before any diode is judged, and the shortfall is reported in amperes
   so the retest is scoped.
3. Read the drop across each diode with the string driven in reverse,
   and record the junction temperature alongside every reading.
4. Refer each drop to the reference junction temperature using the
   declared coefficient.
5. Group each part from its referred drop: conducting, suspect-shorted,
   suspect-degraded or open-circuit. Compute the dissipation the drive
   imposes on it and check it against the budget, since a part can sit
   inside the window and still be overrun.
6. Where the string voltage was recorded, subtract the diode drops and
   charge the residual to the reverse path. Then sentence the campaign,
   reporting each shortfall separately so the retest is scoped to the
   one that failed.

## Pitfalls

- Driving the string at a convenient bench current. The diode is bought
  for the shadowed case, so a drive below the worst-case string current
  tests a condition the design never has to survive.
- Reading the drop without the junction temperature. Tens of millivolts
  of drift separate a warm part from a cold one, which is most of the
  margin the window allows.
- Reading the string terminals instead of each diode. One open diode
  inside a group can hide behind the drops of its neighbours until the
  totals are compared, which is exactly why the residual is taken.
- Treating a low drop as good news. A diode that develops almost no
  forward voltage is not efficient, it is shorted, and it bleeds its
  section every time the array is lit.
- Comparing a referred drop against a window edge by bare arithmetic.
  The referral is a difference of products, so a part meant to sit on
  the edge can land a few units in the last place outside it; the
  comparison absorbs that representation error while the window stays
  untouched.

## Behavior contract (gate 3)

The reverse-drive adequacy screen, the junction-temperature referral,
the conduction window grouping, the dissipation load, the unexplained
string drop and the campaign verdict are exercised by the gate 3
contract test: scripts/test_e2008_shunt_diode_test.py against
scripts/e2008_shunt_diode_test_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_shunt_diode_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
