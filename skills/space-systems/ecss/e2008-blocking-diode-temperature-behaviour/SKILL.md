---
name: e2008-blocking-diode-temperature-behaviour
description: "Use when a blocking diode temperature map is planned, read back or audited. Map the electrical parameters of a planar blocking diode against operating temperature under ECSS-E-ST-20-08C clause 12.6.9: read the sweep in order and refuse a repeated point, hold its span and its endpoint gaps against the declared service range, hold the widest step against the resolution ceiling, check that forward voltage falls and reverse leakage rises across it, interpolate both between mapped points, and settle the self-heated junction the string current drives the diode to against its rating. Trigger: ecss, e-st-20-08c-clause-12-6-9, planar-blocking-diode-temperature-map, blocking-diode-forward-voltage-versus-temperature, blocking-diode-self-heated-junction-temperature, blocking-diode-string-forward-loss-fraction, blocking-diode-reverse-leakage-versus-temperature."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-temperature-behaviour, planar-blocking-diode-temperature-map, blocking-diode-forward-voltage-versus-temperature, blocking-diode-self-heated-junction-temperature, blocking-diode-string-forward-loss-fraction, blocking-diode-reverse-leakage-versus-temperature]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Planar Blocking Diodes -- Temperature Behaviour (space-systems/ecss/e2008-blocking-diode-temperature-behaviour)

Use when the task is clause 12.6.9 of ECSS-E-ST-20-08C -- producing the
electrical parameters of a planar blocking diode as a function of
operating temperature rather than at whatever the bench happened to sit
at. A blocking diode is in series with its string, so its forward drop
is subtracted from the string voltage in every sunlit second and its
reverse leakage is what the string gives back in the dark. A wing swings
through more than a hundred degrees an orbit and both numbers move the
whole way.

## Domain quick reference

- The map is the deliverable and the map is graded first. Everything
  read off it afterwards inherits the sweep's defects, so a confident
  hot-case number can come straight out of a sweep that never went
  there.
- The ends carry the load. The cold end sets the largest forward drop
  and therefore the worst string voltage loss; the hot end sets the
  largest leakage and the largest dissipation. A sweep that stops short
  of either extrapolates into exactly the region the array works in.
- Step size is resolution. Between neighbouring points the curve is an
  assumption, so a knee inside a wide step is absent from the map no
  matter how many points sit either side of it.
- One reading per temperature. A repeated point is two readings of one
  state and weights that state twice in everything derived from it.
- Both parameters have a direction. Forward drop falls as the junction
  warms and leakage rises. A sweep that shows either moving the other
  way is describing the fixture -- lead resistance on the forward side,
  an instrument noise floor on the leakage side -- and not the junction.
- The hot case is a loop, not a lookup. Forward dissipation lifts the
  junction above its mounting, the warmer junction drops less voltage,
  and the dissipation follows it down. The operating point is where that
  settles, and reading the drop at the mounting temperature understates
  the junction by the whole self-heating rise.
- That rise is why the map needs a little headroom past the hot service
  end. A bounded extension along the end slope carries it; a junction
  that self-heats past the extension is a case this sweep cannot answer,
  and saying so is the honest result.
- Leakage is interpolated geometrically because it moves
  multiplicatively with temperature. A straight line between two mapped
  points understates the middle of the interval badly.
- The forward loss share is a reported number rather than a stop. A
  drop that eats too much of the string voltage is a design finding
  about the part selected, not a defect in the sweep that measured it.

## Workflow

1. Validate the map policy first: point floor, step ceiling, endpoint
   gap ceiling, extension allowance, junction rating, loss share and the
   settling tolerance. A floor that admits a single point is refused.
2. Read the declared service range, refusing an inverted or empty one,
   and read the sweep into temperature order, refusing a repeated
   temperature and a sweep of fewer than two points.
3. Take the span, the two endpoint gaps against the service ends, and
   the widest step between neighbouring points.
4. Grade coverage: point count against its floor and both endpoint gaps
   against their ceiling. Report every coverage finding together so the
   sweep is not repaired one end at a time, then close.
5. Grade resolution: the widest step against its ceiling, with a
   comparison that absorbs representation error so a sweep stepped
   exactly to the ceiling is admissible.
6. Grade direction: forward drop non-rising and leakage non-falling
   across the sweep, and close on both findings when both are present.
7. Bound the reachable junction from the highest mapped drop, the string
   current and the thermal resistance. When that bound leaves the map
   plus its extension allowance, close -- the hot case is not readable
   from this sweep.
8. Settle the self-heating loop at the hot mounting temperature, take
   the junction, the rise, the dissipation and the leakage there, and
   hold the junction against its rating.
9. Take the cold-end drop and its share of the string voltage, report
   the share as a finding when it is heavy, and close on one verdict:
   coverage insufficient, resolution insufficient, trends inconsistent,
   self-heating beyond the mapped range, junction rating exceeded, or
   parameters mapped.

## Pitfalls

- Quoting a parameter from a single bench temperature. Both parameters
  move across the orbit, and the room-temperature value is the one
  operating point the diode spends almost no time at.
- Reading the hot-case drop at the mounting temperature. The junction
  sits above its mount by the whole self-heating rise, and the rating
  is written against the junction.
- Stopping the sweep at the hot service end. Self-heating carries the
  junction past it, so the map runs out exactly where the hot case
  needs it.
- Extrapolating without a bound. An end slope carried far enough will
  produce any number asked of it; past the declared allowance the map
  is silent and should say so.
- Interpolating leakage linearly. It moves multiplicatively, so the
  straight line between two mapped points sits well under the curve in
  the middle of the interval.
- Accepting a rising forward drop as device behaviour. A drop that
  climbs with temperature is lead and fixture resistance dominating the
  measurement, and the map inherits that error everywhere.
- Treating a wide step as covered because the endpoints are. The points
  either side of a knee say nothing about the knee.
- Comparing a step or an endpoint gap against its ceiling by bare
  arithmetic. Both are differences of declared temperatures, so a sweep
  planned exactly to the ceiling can land in the last place above it;
  the comparison absorbs that while the ceiling stays as written.

## Behavior contract (gate 3)

The policy validation, the service range and sweep reading with its
repeated-point refusal, the span, endpoint gaps and widest step, the two
direction checks, the linear forward interpolation and geometric leakage
interpolation with their extension allowance, the reachable junction
bound, the settled self-heating loop with its rise and dissipation, the
forward loss share and the single run verdict are exercised by the gate
3 contract test:
scripts/test_e2008_blocking_diode_temperature_behaviour.py against
scripts/e2008_blocking_diode_temperature_behaviour_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_temperature_behaviour.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
