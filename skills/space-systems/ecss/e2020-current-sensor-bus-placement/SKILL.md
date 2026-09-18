---
name: e2020-current-sensor-bus-placement
description: "Verify that the current sensing element of a power protection device sits on the energised main bus side. Use when an LCL, HLCL or fold-back limiter is reviewed against ECSS-E-ST-20-20C clause 5.2.3.3.1: enumerate every current the branch draws with its origin and its return route, work out which ones actually cross the sensing element in its declared position, name the fault currents that bypass it, convert the sensed share into the real branch current needed to reach the trip threshold, and compare that against the harness rating and the nominal load band. Trigger: ecss, e-st-20-20c-clause-5-2-3-3-1, lcl-current-sense-placement, energised-main-bus-side-shunt, structure-return-fault-bypass, unsensed-fault-current-path, effective-trip-current-inflation, latching-current-limiter-threshold."
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
  tags: [ecss, e-st-20-20-power-supply-interface-scope, e2020-current-sensor-bus-placement, lcl-current-sense-placement, energised-main-bus-side-shunt, structure-return-fault-bypass, unsensed-fault-current-path, effective-trip-current-inflation, latching-current-limiter-threshold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply Interfaces -- Current Sensing Element on the Bus Side (space-systems/ecss/e2020-current-sensor-bus-placement)

Use when the task is clause 5.2.3.3.1 of ECSS-E-ST-20-20C -- deciding
where the current sensing element of a protection device belongs. A
limiter acts on one measurement, and the position of the element that
makes it decides which currents reach that measurement at all. The
clause places it on the side facing the energised main bus, where it
is in series with everything the branch draws from the bus.

## Domain quick reference

- A branch carries more than one current, and they do not share a
  route. The load draw leaves through the feed and comes back on the
  bus return. The device's own housekeeping supply is usually tapped
  ahead of the pass element. A downstream insulation failure returns
  through the structure bond, not through the bus return at all.
- An element at the bus interface is in series with the sum of those.
  It reads the branch total whatever each path does afterwards, which
  is the property the clause is protecting.
- An element on the return rail reads only what comes back along that
  rail. The structure-return fault -- the one the limiter exists for --
  never crosses it, so the device reads a current lower than the branch
  is drawing and holds a fault it cannot see.
- The consequence is arithmetic, not opinion. If the element sees a
  share of the branch current, the branch has to draw the threshold
  divided by that share before the limiter reacts. That inflated
  figure, not the nameplate threshold, is what gets compared against
  the harness rating.
- An element placed after the pass element shows a smaller version of
  the same error: it is not in series with anything tapped ahead of
  it, so the housekeeping draw and any upstream stub leakage sit
  outside the measurement.
- The threshold also has a floor. The sensing element has an accuracy
  band, so a threshold inside the band of the nominal load current
  produces trips nobody can attribute to a fault.

## Workflow

1. Take the sensing element position as two facts -- which rail, and
   whether it precedes or follows the pass element -- and refuse any
   other description rather than guessing at a topology.
2. Enumerate the branch currents. Each one carries an origin, a return
   route and a magnitude, and any that is a fault is marked as one.
3. Decide path by path whether that current crosses the element in its
   declared position: everything at the bus interface, only bus
   returns on the return rail, and nothing tapped ahead of the pass
   element when the element follows it.
4. Name the bypassing paths, and name the bypassing fault paths
   separately -- a fault the element cannot see is a different defect
   from a housekeeping draw it cannot see.
5. Divide sensed by total to get the share, then divide the threshold
   by the share to get the branch current that really trips the
   device.
6. Compare that figure against the harness rating, and the threshold
   against the top of the nominal load's measurement band.
7. Close with a verdict that stays open while any finding stands.

## Pitfalls

- Placing the shunt in the return leg because it keeps the sense
  amplifier near ground. The circuit is easier and the limiter is now
  blind to every fault that returns through structure.
- Quoting the nameplate trip threshold as the branch protection level.
  With a partly blind element the real trip current is the threshold
  divided by the sensed share, and only that number can be compared
  against a harness rating.
- Treating a missed housekeeping draw as negligible because it is
  small. It is a constant offset in the same direction every time, so
  no amount of repetition reveals it.
- Averaging a fault path into the total without marking it as a fault.
  The bypassing fault is the finding; hiding it inside a share makes
  it look like a measurement error.
- Setting the threshold just above the nominal load current with an
  element that has a percent-level accuracy band, then attributing the
  resulting trips to the load.
- Comparing a derived trip current against a rating by bare
  arithmetic. The share is a ratio of summed floats and can land a few
  units in the last place either side of a limit, so the comparison
  absorbs that error while the limit itself is never relaxed.

## Behavior contract (gate 3)

The placement vocabulary, path validation, per-path sensing decision,
sensed share, bypassing and bypassing-fault path lists, effective trip
current, harness margin and nominal measurement band are exercised by
the gate 3 contract test:
scripts/test_e2020_current_sensor_bus_placement.py against
scripts/e2020_current_sensor_bus_placement_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_current_sensor_bus_placement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
