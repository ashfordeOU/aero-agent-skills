---
name: e2007-discharge-injection-probe-testing
description: "Evaluate the arrangement that applies injected discharge pulses to a powered, operating unit under ECSS-E-ST-20-07C clause 5.4.13.4: place each injection clamp inside the distance window that drives the conductors rather than the connector shell, confirm the bundle can carry the clamp there, walk the amplitude ladder to the required level without overtesting past it, size the pulse budget over points, levels and both polarities, derive the shortest interval the generator recharge and unit settling allow, and bound the monitor interval that still catches the shortest upset. Use when a discharge-injection bench is built or reviewed. Trigger: ecss, e-st-20-07c, discharge-injection-arrangement, discharge-injection-clamp-placement, discharge-pulse-amplitude-ladder, discharge-pulse-repetition-interval, discharge-injection-pulse-budget, injected-discharge-upset-monitoring."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-discharge-injection-probe-testing, discharge-injection-arrangement, discharge-injection-clamp-placement, discharge-pulse-amplitude-ladder, discharge-pulse-repetition-interval, discharge-injection-pulse-budget, injected-discharge-upset-monitoring]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Discharge Injection to a Powered Unit (space-systems/ecss/e2007-discharge-injection-probe-testing)

Use when the task is the injection arrangement of ECSS-E-ST-20-07C clause
5.4.13.4 -- deciding where the discharge pulses are applied, at what
amplitudes, how often, and how the unit is watched while they arrive,
before the bench is wired rather than after a run that proved nothing.

## Domain quick reference

- The unit is powered and running while the pulses arrive. That is the
  whole point of the arrangement: the quantity being observed is how the
  unit behaves during the disturbance, and an unpowered unit can only
  show damage, never upset. Injecting into a dead box and reporting no
  effect is the commonest way to pass this clause without testing it.
- Where the clamp sits on the bundle decides what is injected. Too near
  the connector and the pulse couples into the shell and the backshell
  bond instead of the conductors, so the measured response belongs to
  the connector; too far and the bundle's own series impedance and the
  return path take the injected current away before it reaches the pins.
  The usable placement is a window, not a minimum.
- A placement inside the window but close to an edge is usable and
  carried as a limitation rather than a pass. Harnesses are re-dressed
  between runs, and a setup repeated next month from the same photograph
  lands on the other side of the edge.
- The amplitude is approached in steps, not applied at level. A walk-up
  shows the level at which the unit first responds, which is the useful
  engineering result; a single hit at the required level yields only a
  verdict, and if the unit is damaged there is nothing left to walk up.
- The ladder stops at the required level. Overtesting past it by more
  than the agreed allowance stresses flight hardware for a margin nobody
  asked for, and a failure at an unrequired amplitude still has to be
  dispositioned.
- The repetition interval is bounded from below by two independent
  things: the generator needs time to recharge to the set amplitude, and
  the unit needs time to settle before the next pulse lands. The slower
  of the two governs, with a guard so neither is only just cleared.
  Pulsing faster measures a partly charged generator hitting a unit that
  has not returned to its operating point.
- Monitoring is a rate requirement. To see an upset rather than infer it
  from an end-of-run check, the monitor must take several looks across
  the shortest upset worth catching, and it must run continuously rather
  than between pulses. Recording which pulse each observation belongs to
  is what makes an upset attributable afterwards.

## Workflow

1. Validate the plan: injection points with recognized coupling, a rising
   amplitude ladder, a pulse count per polarity, a repetition interval,
   the generator recharge and unit settling times, the shortest upset
   worth catching, the monitoring configuration and the powered state and
   operating mode of the unit.
2. Normalize the injection points, rejecting a repeated point name, and
   check each bundle can physically carry its clamp at the declared
   distance from the connector.
3. Group every placement against the distance window as adequate,
   marginal or inadequate, and record the factor by which an inadequate
   placement misses the bound it violated.
4. Validate the amplitude ladder: strictly rising, at least three levels,
   reaching the required level and not exceeding it beyond the allowance.
5. Size the pulse budget as points times levels times polarities times
   pulses per polarity, and turn it into a wall-clock duration at the
   declared interval plus the per-point setup.
6. Derive the shortest lawful repetition interval from the recharge and
   settling times and compare the declared interval against it.
7. Derive the slowest monitor interval that still takes the required
   number of looks at the shortest upset, and check the monitor runs
   continuously and tags each observation with its pulse.
8. Aggregate: an unpowered unit, a ladder that misses or overshoots the
   level, an interval that is too short, an inadequate placement or a
   monitor that cannot see an upset are findings; a marginal placement, a
   safe-mode unit and an untagged monitor are limitations. Reduce the
   inadequate placements to the one short by the largest factor.

## Pitfalls

- Applying the pulses to an unpowered unit because it is simpler to set
  up, then reporting no effect. The clause is about behaviour under
  injection, and an unpowered unit has none to show.
- Clamping as close to the connector as the harness allows, on the
  reasoning that nearer is harsher. Nearer moves the injection onto the
  connector shell and the backshell bond, and the conductors under test
  see less, not more.
- Treating the placement distance as a minimum with no upper edge, so a
  convenient mid-harness position is used and the injected current
  largely returns before it reaches the pins.
- Going straight to the required amplitude to save bench time. The level
  at which the unit first responds is the result worth having, and it
  cannot be recovered after a full-level hit.
- Pulsing on a fixed interval taken from a previous programme. The
  interval belongs to this generator and this unit, and a generator that
  has not recharged delivers an amplitude nobody recorded.
- Checking the unit between pulses rather than through them. An upset
  that clears on its own is invisible to a between-pulse look, and the
  run concludes with no effect observed.
- Monitoring continuously but never recording the pulse index, so an
  observed upset cannot be tied to the pulse, the level or the polarity
  that produced it and the whole point has to be repeated.

## Behavior contract (gate 3)

The plan validation, point normalization, clamp-window grouping,
shortfall reduction, ladder validation, pulse-budget and duration
arithmetic, repetition-interval bound and monitoring rate check are
exercised by the gate 3 contract test:
scripts/test_e2007_discharge_injection_probe_testing.py against
scripts/e2007_discharge_injection_probe_testing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_discharge_injection_probe_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
