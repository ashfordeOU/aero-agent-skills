---
name: e2020-parallel-trip-off-timing
description: "Determine when a group of paralleled latching and high power limiters trips off as a whole, and whether the current the first member sheds is what carried the rest over their own thresholds, per clause 5.2.12.3.1 of ECSS-E-ST-20-20C. Use when the combined trip time of a parallel group decides an unintended disconnection: take each member trip time from its own branch current, redistribute the shed current across the members still conducting, walk the cascade event by event, and test the group trip time and the gap between consecutive trips against the declared limits. Trigger: ecss, e-st-20-20c-clause-5-2-12-3-1, paralleled-limiter-trip-off-timing, parallel-group-trip-cascade, parallel-trip-current-redistribution, parallel-trip-cascade-margin, parallel-group-trip-window."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-12-3-1, e2020-parallel-trip-off-timing, paralleled-limiter-trip-off-timing, parallel-group-trip-cascade, parallel-trip-current-redistribution, parallel-trip-cascade-margin, parallel-group-trip-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution -- Paralleled Limiter Trip-Off Timing (space-systems/ecss/e2020-parallel-trip-off-timing)

Use when the task is clause 5.2.12.3.1 of ECSS-E-ST-20-20C: limiters
wired in parallel have to be assessed on their combined trip-off time,
so that the group does not disconnect the load when it was never meant
to. The combined time is not any member's time, because the members are
wired together and the first one to open changes the conditions every
other member is working under.

## Domain quick reference

- A member trip time comes from its own inverse-time characteristic at
  its own branch current. A member at twice its threshold opens in one
  time constant; a member at or below its threshold does not open at all
  and has no trip time to combine.
- The first trip resets the problem. The current that member was
  carrying moves to the members still conducting, so every remaining
  trip time has to be recomputed from that instant rather than read off
  the original table.
- The shed current does not split evenly. It follows the surviving
  members' thresholds, so the largest member takes the largest part of
  it and reaches its own limit first among the survivors.
- The fingerprint of an unintended disconnection is a trip that the
  member's own branch current would never have caused. A group that
  opens entirely, with at least one member carried over by
  redistribution, disconnected a load that was inside its rating.
- A group that opens entirely on its members' own currents is a genuine
  overload, not a cascade. It is still worth reporting, because the load
  is gone either way, but the remedy is a different one.
- The gap between consecutive trips is its own criterion. A gap too
  short to be seen and acted on means the group behaves as one device,
  whatever the per-member numbers look like, and no protection
  coordination downstream can use the difference.
- A full trip that takes too long is the opposite failure: the harness
  carries fault current past the window the coordination was built for.
- An undeclared trip characteristic is not a slow trip. It means the
  member was never characterized, and a policy that lets the assessment
  proceed is recording an assumption that the member never opens.

## Workflow

1. Validate the policy: cascade margin between consecutive trips, the
   ceiling on a full group trip, and whether a declared trip
   characteristic is required.
2. Refuse a limiter type whose recovery law is not the one this cascade
   assumes before reading any timing.
3. Prepare each member: threshold, branch current, time constant, and
   whether its characteristic is declared at all.
4. Walk the cascade one event at a time -- earliest trip first, ties
   broken by declaration order -- redistributing the shed current across
   the survivors in proportion to their thresholds after each event.
5. Record every trip as driven by its own branch current or by
   redistribution, using the member's original current as the test.
6. Take the first trip time, the full group trip time when every member
   opens, and the spread between first and last.
7. Test the gaps against the cascade margin and the full group time
   against its ceiling.
8. Rank the group -- not characterized, unintended disconnection, group
   too slow, cascade too fast, group fully trips, partial hold, no trip
   -- and roll up each finding under the member that produced it.

## Pitfalls

- Reporting the fastest member's trip time as the group trip time. The
  group is not finished until the last member opens.
- Recomputing nothing after the first trip. The survivors are carrying
  more current than they were a moment before, and that is the whole
  mechanism.
- Splitting the shed current evenly across unequal members. The split
  follows the thresholds, and getting it wrong moves the next trip.
- Calling every full trip a cascade. A group whose members were each
  over their own thresholds was genuinely overloaded.
- Ignoring the gap between trips because the total time looks fine. Two
  trips a millisecond apart are one event as far as the load is
  concerned.
- Treating an undeclared characteristic as a slow member. It is an
  unmeasured member, and assuming it never opens is a declared
  assumption that belongs in the report.
- Walking a retriggerable limiter or a foldback device through this
  cascade. Neither opens and stays open, so the redistribution never
  settles the way the model assumes.

## Behavior contract (gate 3)

The governed and refused limiter types, the inverse-time member trip
delay with its no-trip case at and below threshold, the shed current
split across survivors in proportion to their thresholds, the event-by-
event cascade with deterministic tie-breaking, the own-current versus
redistribution attribution of each trip, the first trip time, the full
group trip time and the spread, the cascade margin between consecutive
trips, the group trip ceiling, the undeclared characteristic under both
policy settings, and the worst-standing group verdict are exercised by
the gate 3 contract test:
scripts/test_e2020_parallel_trip_off_timing.py against
scripts/e2020_parallel_trip_off_timing_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_e2020_parallel_trip_off_timing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
