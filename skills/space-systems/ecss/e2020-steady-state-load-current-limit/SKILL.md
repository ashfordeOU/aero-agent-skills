---
name: e2020-steady-state-load-current-limit
description: "Verify the steady load current of a switched line stays below the class current once the line is on. Use when ECSS-E-ST-20-20C clause 5.3.1.1.1 asks a load to show its post-switch-on consumption never reaches the limiter class current: convert every operating mode to amperes at both ends of the bus voltage window, remembering a constant-power load draws hardest at the lowest bus, carry the heaviest mode forward, stack the one-sided consumption uncertainties arithmetically or by root-sum-square, derate the class current by the project factor and report utilisation, margin and the mode that binds. Refuses an inverted bus window, an efficiency above unity and a mode with no declared consumption. Trigger: ecss, e-st-20-20c, lcl-steady-state-load-current-limit, derated-class-current-utilisation, constant-power-load-minimum-bus-voltage, steady-state-consumption-stack, bounding-operating-mode, nuisance-limitation-avoidance."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-steady-state-load-current-limit, derated-class-current-utilisation, constant-power-load-minimum-bus-voltage, steady-state-consumption-stack, bounding-operating-mode, nuisance-limitation-avoidance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Steady-State Load Current Limit (space-systems/ecss/e2020-steady-state-load-current-limit)

Use when the task is the steady-state consumption check of
ECSS-E-ST-20-20C clause 5.3.1.1.1 — showing that once a protected line
has switched on and its turn-on transient is over, the current the load
draws stays below the class current the line was given.

## Domain quick reference

- The clause governs everything after turn-on. The excess a load is
  allowed to draw while its input filter charges is a separate
  allowance with its own clause, and folding the two together is how a
  design ends up justifying a steady overdraw with an inrush argument.
- The failure being prevented is nuisance limitation. A limiter asked to
  carry a steady current at or above its class current enters limitation
  with nothing wrong downstream, holds the load at a reduced voltage and
  then opens on its trip-off delay, so a healthy unit presents as a
  fault and the recovery logic chases a defect that is not there.
- A constant-power load draws hardest at the LOW end of the bus voltage
  window. The power is fixed and the current is what moves, so sizing at
  the nominal bus understates the current by exactly the regulation
  band. The converter makes it worse: the bus current is the load power
  divided by both the bus voltage and the conversion efficiency.
- A constant-current load — a heater string, a bias chain — does not
  move with the bus voltage at all. Both shapes appear in the same
  equipment, so each mode is converted on its own terms and both ends of
  the window are evaluated rather than assumed.
- The mode that binds is not always the one the data sheet leads with.
  Every declared mode is converted and ranked, and the heaviest is the
  only one carried into the comparison.
- The uncertainty stack is one-sided by construction. Only an upward
  excursion — consumption tolerance, temperature drift, ageing, a return
  path offset — can threaten the class current, so a two-sided stack
  reported here is answering a different question.
- Arithmetic stacking puts every contributor at its own worst case at
  the same instant and is the bounding answer. Root-sum-square assumes
  independence and always returns a smaller figure, so it buys margin
  only against an independence argument, and the method travels with the
  result.
- The separation is strict. Equality with the derated capability is the
  boundary the clause draws, not compliance, and a design sitting on it
  has no room for the first contributor anybody adds later.
- The derating factor and the utilisation advisory floor are declared
  project policy rather than physical constants; the defaults in the
  logic module are a starting point a project substitutes its own values
  into.

## Workflow

1. Validate the bus voltage window: positive, the right way up, and
   wide enough to be the regulation band rather than a single nominal
   figure repeated twice.
2. Validate the mode set: unique names, a known kind, a positive
   declared consumption, an efficiency at or below unity on every
   constant-power mode and no efficiency at all on a constant-current
   one.
3. Convert every mode to amperes at both ends of the window and record
   the voltage that produced the larger current, so a reviewer sees the
   constant-power modes binding at the bottom.
4. Rank the modes heaviest first and carry the top one forward. Keep the
   whole ranking in the result: the second mode is what a later growth
   estimate is argued against.
5. Validate the uncertainty set and stack it on the bounding mode by the
   declared method, recording which method was used.
6. Derate the class current by the project factor and compare, strictly,
   against both the derated capability and the class current itself. The
   second comparison separates a margin problem from a design that will
   actually limit in flight.
7. Report the margin in amperes and the utilisation as a share of the
   derated capability, and raise an advisory when the load consumes most
   of it even though every comparison passed.

## Pitfalls

- Sizing a constant-power load at the nominal bus voltage. The current
  peaks at the bottom of the regulation band, and the shortfall is
  exactly the band, which is usually enough to move the class.
- Dropping the conversion efficiency. The bus carries the load power
  divided by the efficiency as well as by the voltage, and an efficiency
  taken at the nominal input overstates it where it matters least.
- Taking the mode the data sheet leads with. The heaviest mode can be a
  short acquisition or a heater case, and the ranking is what surfaces
  it; a single declared figure hides the question entirely.
- Stacking the uncertainties two-sided. Only the upward direction can
  reach the class current, so a symmetric band reported against this
  clause is answering something else.
- Reaching for root-sum-square to make a failing stack pass. It is a
  claim of independence; consumption tolerance and temperature drift on
  the same converter are not independent, and the smaller figure it
  returns is then not a bound at all.
- Justifying a steady overdraw with the turn-on allowance. That
  allowance covers charging the input filter and stops when the filter
  is charged; it does not extend to operation.
- Treating equality with the derated capability as a pass. The clause
  asks the current to stay below the class current, and a design landing
  on the boundary has consumed the whole project margin.
- Comparing a stacked current with a derated capability by bare
  arithmetic. The current is built from divisions, sums and sometimes a
  square root, so a case meant to sit exactly on the capability can land
  a few units in the last place either side; the comparison resolves the
  tie against the design while the ratings stay as declared.

## Behavior contract (gate 3)

The policy validation, bus window validation, mode validation, per-mode
ampere conversion at both ends of the window, mode ranking, one-sided
uncertainty stacking, class-current derating, strict comparison and
overall verdict are exercised by the gate 3 contract test:
scripts/test_e2020_steady_state_load_current_limit.py against
scripts/e2020_steady_state_load_current_limit_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_steady_state_load_current_limit.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
