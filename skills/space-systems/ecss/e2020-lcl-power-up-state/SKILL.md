---
name: e2020-lcl-power-up-state
description: "Evaluate whether latching and high power limiters come up with their output off, and whether any channel that does not has argued its way there, per clause 5.2.7.2.1 of ECSS-E-ST-20-20C. Use when a recommendation rather than a hard requirement governs the power-up state: tell an off default from an accidental one with no positive enable, separate a departure carrying a rationale, an assessed criticality and compensating provisions from a bare declaration, and add up the inrush every defaulting channel asks of the source at the same instant. Trigger: ecss, e-st-20-20c-clause-5-2-7-2-1, lcl-power-up-output-off, high-power-limiter-default-state, limiter-departure-justification, limiter-positive-enable-command, default-on-aggregate-inrush."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-7-2-1, e2020-lcl-power-up-state, lcl-power-up-output-off, high-power-limiter-default-state, limiter-departure-justification, limiter-positive-enable-command, default-on-aggregate-inrush]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution -- Latching and High Power Limiter Power-Up State (space-systems/ecss/e2020-lcl-power-up-state)

Use when the task is clause 5.2.7.2.1 of ECSS-E-ST-20-20C: a latching
current limiter and a high power limiter are recommended to come up with
the output off. The clause recommends, so a design can conform two ways
and fail one way, and this leaf exists to keep those three answers apart
instead of collapsing them into a single pass or fail.

## Domain quick reference

- A recommendation has two conforming answers. Output off meets it.
  Output on, taken deliberately with a recorded rationale, an assessed
  criticality and compensating provisions, is a departure the project
  owns. Output on with none of that is the case the clause exists to
  make visible, and it is the only one of the three that is a finding
  against the design rather than against the paperwork.
- The recommendation governs latching and high power limiters. A
  retriggerable limiter has the opposite power-up state by its own
  clause, and a foldback device is not in this family at all; feeding
  either into this assessment produces a tidy verdict about the wrong
  part, so an out-of-scope type is refused rather than graded.
- An output that is off because nothing turns it on is not the same as
  an output that is off until a positive enable command turns it on.
  The first is the absence of a design decision and will drift the
  moment somebody adds a pull-up; the second is the decision itself.
- An indeterminate power-up state is not a middle answer. It means the
  channel was never evaluated, which outranks a channel evaluated and
  found wanting, because one needs an analysis and the other needs a
  change.
- A justified departure still has to survive arithmetic. Every channel
  that defaults on charges the source in the same instant, so the
  aggregate inrush of the defaulting set -- not the largest single
  channel -- is what the source sees, and it is compared against the
  capability after the declared margin is held back.
- Criticality bounds what may be argued at all. A departure whose
  assessed consequence sits above the band the project allows a
  departure to be argued at is not justified by a longer rationale; it
  is outside what a rationale can carry.

## Workflow

1. Validate the policy: inrush margin, the criticality ceiling a
   departure may be argued at, the number of compensating provisions a
   departure owes, and whether a positive enable is required.
2. Name each channel's limiter type and refuse a type this
   recommendation does not govern before anything else is read.
3. Read each declared power-up state; an indeterminate one stops that
   channel there as unevaluated.
4. For an off channel, check the off state is commanded -- a declared
   positive enable -- rather than merely observed.
5. For an on channel, test the argument in three parts: a rationale with
   real content, a criticality assessed and inside the ceiling, and
   enough distinct compensating provisions. Refuse a provision list that
   repeats itself or carries an empty entry.
6. Sum the inrush of every channel that defaults on and compare it with
   the source capability after margin.
7. Rank the design at its worst standing -- unevaluated, inrush
   exceeded, unjustified departure, justified departure, recommendation
   met -- and roll up each finding under the channel that produced it.

## Pitfalls

- Reading the clause as a requirement and writing a non-conformance
  against every channel that comes up on. It is a recommendation; the
  finding is the missing argument, not the state.
- Reading it as optional and writing nothing. A departure with no
  rationale, no criticality and no compensating provisions is exactly
  what the recommendation was put there to surface.
- Accepting "the output happens to be off at power-up" as the off
  state. Without a positive enable in the design, the off state is a
  property of this build of the hardware and not of the design.
- Sizing the inrush against the biggest defaulting channel. They all
  turn on together; the source sees the sum.
- Grading a retriggerable limiter here. Its clause asks for the
  opposite state, so it fails this one by construction and the report
  is confidently wrong.
- Treating an indeterminate state as a mild version of on. It is the
  absence of an answer, and it outranks a wrong answer because the two
  need different work.

## Behavior contract (gate 3)

The governed and out-of-scope limiter types, the ordered criticality
bands, the three-part departure argument with its rationale, criticality
ceiling and compensating provisions, the positive-enable distinction on
an off channel, the indeterminate state as unevaluated, the aggregate
default-on inrush against the source capability after margin, and the
worst-standing design verdict are exercised by the gate 3 contract test:
scripts/test_e2020_lcl_power_up_state.py against
scripts/e2020_lcl_power_up_state_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2020_lcl_power_up_state.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
