---
name: q7030-wrapping-operation
description: "Determine the wrap a solid-wire connection needs on a wrapping post under ECSS-Q-ST-70-30C process rules. Use when the turn schedule, the tightness and the position of a wrap are set or reviewed: read the bare-turn count the conductor gauge owes, add the insulated turns a modified wrap carries, compute the height the wrap occupies from the conductor diameter, subtract it from the usable post length so the level fits over the wraps already there, require every turn to seat on every post corner, bound the single and cumulative turn gap, and return the operation with its findings. Trigger: ecss, q-st-70-30c, wire-wrap-turn-schedule, modified-wire-wrap-insulated-turns, wire-wrap-post-level-capacity, wire-wrap-corner-seating, wire-wrap-turn-gap-limit, wrapping-post-usable-length."
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
  tags: [ecss, q-st-70-30c, q7030-wrapping-operation, wire-wrap-turn-schedule, modified-wire-wrap-insulated-turns, wire-wrap-post-level-capacity, wire-wrap-corner-seating, wire-wrap-turn-gap-limit, wrapping-post-usable-length]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wire Wrapping — Wrapping Operation (space-systems/ecss/q7030-wrapping-operation)

Use when the task is the wrapping operation itself under
ECSS-Q-ST-70-30C -- fixing how many turns go on the post, how tightly
they are laid, and where on the post the wrap sits, before the wrap is
made rather than after it has been graded.

## Domain quick reference

- A wrapped connection is a gas-tight joint made by pressing bare
  conductor onto the sharp corners of a rectangular post. The joint is
  the sum of the corner contacts, so the turn count is what the design
  actually buys, and a turn that never touched a corner contributes
  nothing regardless of how the wrap looks.
- The turn schedule is a property of the conductor gauge, not of the
  operator or the post. A finer conductor carries a smaller contact
  area per corner, so it owes more turns to reach the same joint: the
  coarse end of the range settles around four bare turns and the fine
  end around seven.
- A modified wrap starts with part of a turn of insulated wire. That
  insulated turn is not decoration -- it supports the conductor where it
  leaves the wrap, which is the point that fails first under vibration.
  A conventional wrap carries none, so an insulated turn on a
  conventional wrap is as much a departure from configuration as a
  missing one on a modified wrap.
- Height is geometry, not judgement. Turns are laid adjacent, so a wrap
  occupies its bare turns times the conductor diameter plus its
  insulated turns times the conductor diameter plus both insulation
  walls. That height has to fit inside what is left of the post after
  the base offset and the levels already wrapped.
- Tightness is graded two ways at once: every bare turn seats on every
  corner of the post, and the gap between adjacent turns stays inside a
  fraction of the conductor diameter both singly and cumulatively. A
  wrap can pass the count and still fail as an open spiral.
- Position is a stacking rule. The first level starts at the base of
  the post, each later level starts on top of the one below it, and the
  post carries a bounded number of levels because the usable length is
  finite.

## Workflow

1. Declare the conductor gauge and the wrap configuration. Reject a
   gauge outside the schedule rather than interpolating one, because
   every number downstream is read from the gauge row.
2. Read the minimum bare turns from the gauge and the insulated-turn
   window from the configuration, and compare both against what was
   actually laid.
3. Compute the wrap height from the turn counts, the conductor diameter
   and the insulation wall thickness.
4. Compute the usable post length from the post length, the base offset
   and the length already occupied by lower levels, and refuse a post
   that is already over-committed rather than returning a negative
   allowance.
5. Grade tightness: compare the observed corner contacts against turns
   times corners, then test each turn gap against the single-gap limit
   and their sum against the cumulative limit.
6. Grade position: hold the first level at the base, hold a later level
   on top of the one below, hold the level index inside the post
   capacity, and confirm the wrap height fits the free length.
7. Return the operation with its findings, then aggregate the set so a
   single refused wrap fails the assembly rather than being averaged
   away.

## Pitfalls

- Counting turns and stopping there. A wrap with the right number of
  turns that bridged a corner has fewer contacts than the count
  suggests, which is why the corner-contact tally is graded separately
  from the turn tally.
- Reading the turn schedule off the post size instead of the conductor.
  The post fixes the contact geometry, but the number of turns is owed
  by the wire, so two gauges on the same post carry different
  schedules.
- Treating the insulated turn of a modified wrap as optional tidiness.
  Removing it moves the stress riser onto bare conductor at the exit of
  the wrap, which is exactly where a vibration failure starts.
- Planning levels by eye. The usable length is the post length minus
  the base offset minus everything already wrapped; a third level
  planned without that subtraction is discovered to be short only after
  the wire has been cut.
- Comparing a computed height against the free length by bare
  arithmetic. Both sides are sums of measured floats, so a wrap that
  exactly fills the post can land a few units in the last place over
  it; the comparison absorbs that representation error while the limit
  itself stays untouched.

## Behavior contract (gate 3)

The gauge schedule, the insulated-turn window, the wrap-height and
usable-length geometry, the corner-contact and turn-gap tightness
grading, the level stacking rules and the set-level verdict are
exercised by the gate 3 contract test:
scripts/test_q7030_wrapping_operation.py against
scripts/q7030_wrapping_operation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7030_wrapping_operation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
