---
name: e2020-load-response-to-switch-failure
description: "Assess how a protected load behaves when the switch feeding it fails into a partly conducting, dissipative state. Use when an ECSS-E-ST-20-20C clause 5.3.3.1.1 failure analysis has to state the load response to a degraded feed: solve the series operating point for a constant-power, constant-current or resistive load against the failed switch resistance, categorize the outcome as degraded operation, an undervoltage inhibit or a feed that cannot be sustained at all, test the constant-power point against the stability boundary at half the bus voltage, and compare the power left in the failed switch with what it can dissipate. Trigger: ecss, e-st-20-20c, load-response-to-switch-failure, dissipative-switch-failure-mode, series-operating-point, constant-power-load-stability, load-undervoltage-inhibit, failed-switch-dissipation."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-load-response-to-switch-failure, dissipative-switch-failure-mode, series-operating-point, constant-power-load-stability, load-undervoltage-inhibit, failed-switch-dissipation, load-inhibit-retrigger-cycling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Load Response To Switch Failure (space-systems/ecss/e2020-load-response-to-switch-failure)

Use when the task is the load-side failure question of ECSS-E-ST-20-20C
clause 5.3.3.1.1 — stating what a protected load does when the switch
feeding it fails in a dissipative mode instead of failing cleanly on or
cleanly off.

## Domain quick reference

- A protective switch normally sits fully on, with a negligible drop, or
  fully off. A dissipative failure leaves it in neither: it stays partly
  conducting and behaves as a series resistance, dropping part of the bus
  voltage and turning the difference into heat inside the failed device.
  The load downstream is then fed at a degraded voltage.
- The response depends on what kind of load it is, and that is the whole
  point of the clause. A constant-power load draws MORE current as its
  input droops, which deepens the drop, which droops it further. A
  constant-current load holds its draw, so the drop is fixed. A resistive
  load draws less as the voltage falls and settles benignly on a divider.
- For a constant-power load the operating point is the root of
  V_load^2 - V_bus*V_load + P*R = 0. Its discriminant goes negative
  exactly when the failed switch can no longer pass the power demanded,
  and there is then no operating point at all: the feed collapses rather
  than settling somewhere low.
- The most power any series resistance can pass is V_bus^2/(4R), reached
  at a load voltage of half the bus. That half-voltage is the stability
  boundary: at or below it a further droop raises the current instead of
  relieving it, so a point sitting there is reported even though the
  arithmetic returned a root.
- Three questions then follow whatever the model. Is the degraded voltage
  still above the load's undervoltage threshold? Can the failed switch
  survive the heat now left in it? And if the load does inhibit itself,
  does the input recover far enough to restart it?
- That last one is a real failure mode, not a detail. An inhibited load
  draws only housekeeping current, so the input recovers towards the bus;
  if it recovers past the release threshold the load restarts, collapses
  the rail again and cycles indefinitely. A load with enough hysteresis,
  or enough inhibit draw, stays down.
- The dissipation derating and the stability voltage margin are declared
  project policy rather than physical constants; the defaults in the
  logic module are a starting point a project substitutes its own values
  into.

## Workflow

1. Validate the failed switch: a positive series resistance for the
   dissipative state and the power it is rated to dissipate.
2. Validate the load: a model the routine carries, the parameter that
   model needs, the undervoltage threshold, the release threshold above
   it, the inhibit draw and the input current rating. Hysteresis that is
   the wrong way up is a data error and is refused.
3. Solve the series operating point for the declared model. For a
   constant-power load take the upper root and stop on a negative
   discriminant rather than forcing an imaginary answer.
4. Compare the point with the stability boundary at half the bus
   voltage. Report a point at or below it, and advise on a point that
   clears it only inside the project margin.
5. Compare the heat left in the failed switch with its derated rating,
   and the load current with the load's input rating.
6. Categorize the response: the load keeps operating at a degraded
   input, it inhibits at its undervoltage threshold, it keeps drawing
   below that threshold because it has no inhibit, or the feed cannot be
   sustained at all.
7. When the load inhibits, solve where the input settles on the inhibit
   draw alone and report whether that recovery restarts the load and
   sets it cycling.

## Pitfalls

- Treating the degraded feed as a simple divider for every load. That is
  only true of a resistive load; a constant-power load moves the opposite
  way and is the case the clause exists for.
- Solving the constant-power quadratic and taking the lower root. The
  lower root is the branch the converter cannot hold; the physical
  settling point is the upper one.
- Reporting a low but real operating point as merely degraded when it
  sits at or below half the bus voltage. There the load is past the point
  of maximum power transfer, and a small further droop makes the current
  worse rather than better.
- Forcing an answer out of a negative discriminant. A constant-power load
  demanding more than V_bus^2/(4R) has no operating point, and reporting
  a collapsed feed is the correct result, not a failure of the routine.
- Stopping at the inhibit. A load that inhibits itself is only safe if it
  stays inhibited; a recovery above the release threshold restarts it and
  the pair cycles, which is a different finding with a different repair.
- Comparing a dissipation or a voltage against a rating by bare
  arithmetic. An operating point comes out of a square root and a
  dissipation out of a squared current, so a case meant to sit exactly on
  a rating can land a few units in the last place the wrong side of it;
  the comparison absorbs that representation error while the ratings and
  the derating stay as specified.

## Behavior contract (gate 3)

The policy validation, switch and load validation, dissipation and
deliverable-power helpers, the per-model operating point, the inhibited
recovery point and the full clause response are exercised by the gate 3
contract test: scripts/test_e2020_load_response_to_switch_failure.py
against scripts/e2020_load_response_to_switch_failure_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_load_response_to_switch_failure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
