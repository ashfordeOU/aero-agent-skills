---
name: e2020-load-inductance-operating-range
description: "Verify that a current limiter operates normally across every load inductance up to the specified maximum, under ECSS-E-ST-20-20C clause 5.2.19.1.1. Use when an inductive load has to be shown safe over a whole range rather than at one convenient point: refuse a range whose maximum nobody specified, compute the energy stored at the limitation current and the turn-off transient that inductance drives, weigh both against what the clamp path can absorb and stand off, and audit whether the demonstrated points span the range without leaving a stretch wide enough to hide a resonance. Trigger: ecss, e-st-20-20c-clause-5-2-19-1-1, limiter-load-inductance-operating-range, maximum-load-inductance-turn-off-energy, load-inductance-range-test-coverage, freewheel-clamp-energy-capability, inductive-turn-off-transient-voltage."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-19-1-1, e2020-load-inductance-operating-range, limiter-load-inductance-operating-range, maximum-load-inductance-turn-off-energy, load-inductance-range-test-coverage, freewheel-clamp-energy-capability, inductive-turn-off-transient-voltage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Limiters -- Load Inductance Operating Range (space-systems/ecss/e2020-load-inductance-operating-range)

Use when the task is the clause 5.2.19.1.1 question of ECSS-E-ST-20-20C:
a limiter has to behave normally for every load inductance the design
allows, from a nearly resistive load up to the maximum the specification
names, and the claim covers the range rather than the endpoint.

## Domain quick reference

- A maximum has to exist before anything can be shown up to it. A design
  record with no specified maximum load inductance is not a passing case
  with a missing field; it is a clause that has nothing to be assessed
  against, and saying so is the result.
- The stress is computed at the limitation current, not the nominal load
  current. The turn-off that matters is the one following an overload,
  and that is where the inductance is carrying the most.
- Two independent limits sit at the top of the range. The energy the
  inductance holds has to be absorbed by the freewheel or clamp path,
  and the voltage that inductance drives across the opening switch has
  to stay inside the standoff. A design can pass one and fail the other,
  so both are reported rather than the first to trip.
- Both limits scale with the inductance, which is why the declared
  maximum is the evaluation point -- and why a later increase in the
  specified maximum is not a paperwork change.
- Behaviour across the range is not guaranteed monotonic. A resonance
  between the load inductance and the output filter lives at one
  inductance and nowhere near the ends, so a range demonstrated only at
  its endpoints steps straight over it.
- The gap below the lowest demonstrated point counts too. A record that
  starts halfway up the range has left the lightly inductive loads
  untested, and those are the ones most likely to be flown.
- A demonstration above the specified maximum is margin evidence, not
  range coverage. It is worth recording, in that column.
- Capability is judged before the test record. A design whose clamp path
  cannot take the energy does not become compliant by being tested more
  thoroughly.

## Workflow

1. Validate the operating-range policy first: the clamp energy and
   voltage margins the project demands, the fraction of the range that
   may sit between demonstrated points, whether the maximum itself must
   be demonstrated, and the margin at which a passing case still earns
   an advisory. A required margin below one, or a gap allowance of zero,
   is refused rather than used.
2. Validate the limiter record: identifier, limitation current, current
   fall time, bus voltage, clamp standoff and clamp energy capability. A
   clamp standoff at or below the bus voltage leaves no headroom for any
   inductive turn-off and is refused here.
3. Read the declared range. When no maximum is specified, close on range
   not declared and say why, rather than defaulting to a number.
4. At the declared maximum, compute the stored energy and the turn-off
   transient, and take both margins against the clamp path.
5. Report every margin that falls short, not the first, and close on
   transient beyond clamp capability when any does.
6. Index the demonstrated points, sort them by inductance, and measure
   the gaps as fractions of the declared span -- including the stretch
   below the lowest point and above the highest one inside the range.
7. Check the maximum itself was demonstrated rather than approached,
   take the widest gap, and close on coverage incomplete when either
   fails.
8. Otherwise close on operation across range demonstrated, with the
   energy, the transient, both margins, the widest gap and any advisory
   beside it.

## Pitfalls

- Evaluating at the nominal load current. The inductance is carrying the
  limitation current when the interesting turn-off happens, and the
  stored energy goes with the square of it.
- Testing at the maximum and calling the range covered. One point is one
  point, and the clause asks about the values underneath it too.
- Ignoring the low end. A limiter demonstrated from half the maximum
  upwards has said nothing about the nearly resistive load, which is a
  different turn-off entirely.
- Reporting the first margin that fails. Energy and standoff are
  separate design limits with separate fixes, and a reviewer who sees
  one goes and solves one.
- Reading a demonstration above the maximum as coverage. It is margin,
  and treating it as coverage leaves the interior of the range exactly
  as untested as before.
- Comparing a computed margin against its floor with a strict
  inequality. A margin that should land exactly on the bound lands a
  hair either side of it depending on the machine, and the verdict then
  travels badly.

## Behavior contract (gate 3)

The policy validation, limiter and range validation, the undeclared
maximum stop, the stored energy and turn-off transient, both clamp
margins, the demonstrated-point indexing, the coverage gaps including
the ends, the endpoint check, the outside-range points and the
advisories are exercised by the gate 3 contract test:
scripts/test_e2020_load_inductance_operating_range.py against
scripts/e2020_load_inductance_operating_range_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_load_inductance_operating_range.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
