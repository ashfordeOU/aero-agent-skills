---
name: e3301-over-current-protection-wire-strain
description: "Size the over-current protection of a mechanism drive circuit and the strain relief of the harness crossing its moving joint, per ECSS-E-ST-33-01C clauses 4.7.7.6 and 4.7.7.7. Use when the task is placing a fuse or limiter rating between the worst-case operating current and the derated wire capacity, showing a stall is interrupted before the insulation reaches its limit or the wire carries it indefinitely, and confirming the service loop covers the travel without going taut, stays above the cable bend radius and keeps conductor strain inside its flexure allowable. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-overcurrent-rating-window, motor-stall-current-interruption, wire-bundle-current-derating, moving-joint-service-loop, harness-flexure-cycle-life, cable-bend-radius-strain."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-over-current-protection-wire-strain, mechanism-overcurrent-rating-window, motor-stall-current-interruption, wire-bundle-current-derating, moving-joint-service-loop, harness-flexure-cycle-life]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Over-Current Protection and Wire Strain Relief (space-systems/ecss/e3301-over-current-protection-wire-strain)

Use when the task is the protection step of ECSS-E-ST-33-01C clauses
4.7.7.6 and 4.7.7.7 -- keeping a motor or actuator circuit from
destroying its own harness when it jams, and keeping the harness that
crosses the joint from destroying itself simply by moving.

## Domain quick reference

- A protection rating is bounded from both sides. Too low and nominal
  duty opens it in flight; too high and the wire reaches its
  temperature limit before the device notices. The design question is
  whether a rating exists inside that window at all, and when the
  bounds cross the answer is a heavier wire or a lower drive current,
  not a chosen rating.
- The upper bound rests on the wire's derated capacity, not its
  catalogue rating. A conductor buried in a bundle sheds heat into
  neighbours that are also warm, and at low ambient pressure it sheds
  less still, so the capacity that matters is the rating after both
  factors.
- A stalled motor is the sizing case, not the running one. Stall
  current is several times running current, and two designs are
  acceptable: the device interrupts within the wire's thermal withstand
  time, or the wire is large enough to carry the stall indefinitely. A
  design that is neither survives only because nothing ever jammed.
- A protection rating above the stall current protects nothing. The
  stall then sits below the trip threshold forever, heating the wire at
  a current the device is content with.
- A harness crossing a moving joint fails by fatigue, not by overload.
  The free length has to exceed the travel with slack so the loop never
  goes taut, the radius it takes has to stay above the cable's minimum,
  and the outer-fibre strain that radius produces has to sit inside the
  flexure allowable for the cycles the mission needs.
- Flexure qualification is a cycle count, and it is compared against the
  mission's required cycles including ground testing and the
  re-articulation a recovery mode may call for.

## Workflow

1. Validate each drive circuit: operating and stall current, wire
   rating, bundle and altitude derating, protection rating, trip time
   and the wire's thermal withstand time. A stall current below the
   operating current is an input error.
2. Compute the derated wire capacity, then the protection window: the
   lower bound from the operating current and its factor, the upper
   bound from the derated capacity and its factor.
3. Report whether a window exists at all, then grade the chosen rating
   against both bounds. A rating sitting exactly on a bound within the
   named tolerance is accepted.
4. Grade the stall case. When the wire is declared to carry stall
   indefinitely, compare the derated capacity with the stall current;
   otherwise compare the trip time with the wire withstand time and
   check that the stall current actually reaches the rating.
5. Validate each moving-joint crossing: travel, free length, cable
   diameter, minimum bend radius, wrap angle, allowable strain and the
   required and qualified cycle counts.
6. Compute the required service-loop length from the travel and slack
   factor, the bend radius the free length takes over the wrap angle,
   and the outer-fibre strain that radius produces; grade all three plus
   the cycle count.
7. Report per-circuit and per-crossing records with the aggregated
   findings; the design is compliant only when the list is empty.

## Pitfalls

- Sizing the protection against running current alone. The window's
  upper bound comes from the wire, and a rating chosen only from the
  motor can sit anywhere above it.
- Using the catalogue wire rating as the capacity. In a bundle at
  altitude the usable current is a fraction of it, and the fuse that
  looked conservative is then larger than the wire it protects.
- Picking a rating above the stall current to avoid nuisance trips. The
  circuit is then unprotected in the only case that needs protection.
- Treating a crossed window as a sizing problem. When the lower bound
  is above the upper bound there is no rating; reporting the nearest
  available part number hides a real design change.
- Sizing the service loop to the travel exactly. The loop then goes
  taut at end of travel, and the load lands on the connector backshell
  and the conductor termination.
- Qualifying the harness to the mission's in-orbit cycles only. Ground
  testing, acceptance runs and a recovery re-articulation all consume
  flexure life before launch.
- Relaxing a limit to absorb a value sitting exactly on it. The
  representation error is handled by the named tolerance inside the
  comparison; the limit stays as specified.

## Behavior contract (gate 3)

The circuit validation, wire derating, protection-window construction
and rating grading, stall interruption and stall-capacity grading,
service-loop length, bend radius, conductor strain and flexure-cycle
grading are exercised by the gate 3 contract test:
scripts/test_e3301_over_current_protection_wire_strain.py against
scripts/e3301_over_current_protection_wire_strain_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3301_over_current_protection_wire_strain.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
