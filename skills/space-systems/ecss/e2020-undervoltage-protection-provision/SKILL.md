---
name: e2020-undervoltage-protection-provision
description: "Audit a power bus for the input undervoltage protection each limiter carries, per ECSS-E-ST-20C clause 5.2.5.1.1. Use when the provision has to be shown to hold over every limiter and each function shown to be placed usefully rather than merely present: count the population first, then check the trip threshold sits below the steady-state band yet above the limiter's own operating floor, that threshold plus hysteresis gives a recovery level the bus can still reach, that the hysteresis clears the chatter floor, and that the response time lets a survivable dip pass. Trigger: ecss, e-st-20-electrical-scope, limiter-undervoltage-protection-provision, input-undervoltage-threshold-window, undervoltage-recovery-level-reachability, bus-dip-ride-through-time, limiter-bus-interface-protection, undervoltage-provision-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-undervoltage-protection-provision, limiter-undervoltage-protection-provision, input-undervoltage-threshold-window, undervoltage-recovery-level-reachability, bus-dip-ride-through-time, limiter-bus-interface-protection, undervoltage-provision-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Undervoltage Protection Provision (space-systems/ecss/e2020-undervoltage-protection-provision)

Use when the task is the provision of ECSS-E-ST-20C clause 5.2.5.1.1 --
showing that every limiter on a power bus carries an input undervoltage
protection function on its bus interface, and that each of those
functions is set where it actually does the job.

## Domain quick reference

- The provision is stated over the whole population, and the word doing
  the work is "each". A design where most limiters carry the function
  and two do not has not met the clause, and those two are exactly the
  units that keep drawing full load while the bus collapses. So the
  first half of the assessment is answered by counting, never by
  sampling.
- The second half is harder, because a function that exists can still
  sit where it does nothing or where it does harm. Four placements go
  wrong and each has its own symptom.
- A threshold set too high sits inside the band the bus legitimately
  occupies, so the function sheds load on a healthy day and turns a bus
  excursion into a mission event. The threshold belongs a declared
  margin below the lowest steady-state voltage the bus holds.
- A threshold set too low sits under the limiter's own minimum
  operating input. By the time it notices anything the limiter has
  already left its specified behaviour, so the function protects
  nothing that was still working.
- A recovery level above the bus minimum latches the unit out for good.
  Recovery is the threshold plus the hysteresis, and if that sum lands
  above the lowest voltage the bus holds, the limiter opens on a dip
  and never sees a voltage high enough to come back -- a permanent loss
  from a transient cause.
- A hysteresis too narrow chatters. With almost no separation between
  trip and recovery, ripple and source impedance alone will cycle the
  function, so a floor on the hysteresis is part of the provision
  rather than an implementation detail.
- The response time is the last placement. If a dip the design is
  expected to survive reaches below the threshold, the function has to
  be slow enough to let it pass, otherwise a transient the bus was
  built to absorb becomes a shed load. Where the dip floor never
  reaches the threshold the dip does not exercise the function at all,
  and that is worth recording rather than scoring.
- The margins are declared project policy rather than physical
  constants, so the policy reference travels with the verdict.

## Workflow

1. Declare the bus envelope: the steady-state minimum and maximum, the
   floor of the dip the design is expected to survive, and how long
   that dip lasts. Reject a dip floor that is not below the steady-state
   minimum, because that is not a dip.
2. Read every limiter on the bus with its declared function, trip
   threshold, hysteresis, response time and its own minimum operating
   input. Refuse a duplicate identifier and an empty population.
3. Count first. Name every limiter with no declared function and stop
   there -- one omission fails a provision stated over each limiter, and
   the placement questions below cannot rescue it.
4. For each protected limiter, build the admissible threshold window:
   ceiling at the steady-state minimum less the nuisance margin, floor
   at the limiter's own operating minimum. Refuse a limiter whose floor
   is already above the ceiling, since no threshold satisfies both.
5. Check the threshold inside that window, the recovery level against
   the bus minimum, and the hysteresis against the chatter floor.
6. Where the survivable dip reaches below the threshold, require a
   response time that outlasts the dip by the declared margin; where it
   does not, record that the dip never exercises the function.
7. Report coverage, every shortfall by name, and the limiter whose
   threshold sits closest to the operating band.

## Pitfalls

- Sampling the population. Coverage is the requirement, so a review
  that checked the three limiters someone had drawings for has not
  answered the clause for the fifteen it did not open.
- Accepting presence as compliance. A declared function with a
  threshold inside the operating band is worse than no function, and it
  will pass any check that only asks whether the box exists.
- Setting the threshold from the limiter datasheet alone. The window
  has two sides: the datasheet gives the floor, the bus envelope gives
  the ceiling, and a threshold chosen from one side lands wherever the
  other side happens to allow.
- Forgetting that recovery is threshold plus hysteresis. Widening the
  hysteresis to cure chatter quietly pushes the recovery level up, and
  past the bus minimum it becomes a latch-out that no operator action
  clears.
- Tuning the response time for speed. Faster is not better here: the
  function has to be slower than the dip the bus is specified to
  survive, or it will shed load on exactly the transients the design
  already accounted for.
- Comparing a threshold with a computed window edge by bare arithmetic.
  The ceiling comes out of a float product, so a threshold landing
  exactly on it can fall a few units in the last place outside; the
  comparison absorbs that representation error while the declared
  margin stays untouched.

## Behavior contract (gate 3)

The policy validation, bus-envelope resolution, population coverage
count, threshold-window construction, recovery and hysteresis checks,
dip ride-through requirement and weakest-placement report are exercised
by the gate 3 contract test:
scripts/test_e2020_undervoltage_protection_provision.py against
scripts/e2020_undervoltage_protection_provision_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_undervoltage_protection_provision.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
