---
name: e2007-magnetic-moment-test-sequence
description: "Determine whether a magnetic moment test runs in the order ECSS-E-ST-20-07C clause 5.4.5.3 sets. Use when a moment-test procedure is written or reviewed for a unit measured about six semi-axes across successive conditioning states: confirm every state carries all six semi-axes once, that as-received readings precede any conditioning, that each block follows the deperming or magnetising step which creates it, that deperming precedes magnetising, that no block is split across another state, and size the run from dwell and conditioning times. Trigger: ecss, e-st-20-07c, magnetic-moment-test-sequence, six-semi-axis-measurement-order, deperming-step-placement, magnetising-exposure-step, conditioning-state-block-contiguity, moment-run-duration."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-magnetic-moment-test-sequence, six-semi-axis-measurement-order, deperming-step-placement, magnetising-exposure-step, conditioning-state-block-contiguity, moment-run-duration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Magnetic Moment Test Sequence (space-systems/ecss/e2007-magnetic-moment-test-sequence)

Use when the task is the sequencing requirement of ECSS-E-ST-20-07C
clause 5.4.5.3 -- the order in which a moment test takes its readings:
six semi-axis measurements repeated as the unit is carried through the
as-received, depermed and magnetised conditioning states, with the
deperming and magnetising steps sitting in fixed places between them.

## Domain quick reference

- Six semi-axes, not three axes. A moment is a vector, and reversing
  the unit about an axis separates the unit's own moment from whatever
  offset the sensor and the residual area field contribute. Measuring
  +x and calling -x its mirror image throws away exactly the reading
  that makes the separation possible.
- The conditioning steps are what the sequence is for. As received
  tells you what flew in; depermed is the floor the unit can be taken
  down to; magnetised is the worst case a launch-site magnet or a
  handling incident can leave behind. A sequence that skips one is
  answering a different question.
- Each step is one-way. Deperming erases the history that the
  as-received block measured, and magnetising overwrites the depermed
  state. That is why order is a requirement rather than a convenience:
  a block taken out of turn cannot be repeated without redoing the
  conditioning that preceded it.
- Deperming comes before magnetising. Going the other way leaves the
  depermed reading taken on a unit that has already seen a strong
  field, which is a partially depermed state and not the floor the
  clause asks for.
- A block must stay together. Six readings interrupted by a
  conditioning step or by another state's readings are not six
  readings of one state; the unit has moved on between them, and the
  drift shows up as an axis asymmetry nobody can attribute.
- Run time is a planning output, not a compliance item. Eighteen
  dwells plus a deperming cycle plus a magnetising exposure is a long
  session; a sequence that overruns its facility slot is still a
  correct sequence, so record the overrun as a limitation.

## Workflow

1. Validate the step list: every step has a recognized action, every
   measure step carries a recognized semi-axis and conditioning state,
   and no conditioning step carries either.
2. For each state, collect the semi-axes measured, and report those
   missing and those taken more than once.
3. Check the conditioning steps: each present, each appearing once,
   and deperming ahead of magnetising.
4. Check placement: as-received readings before any conditioning, and
   every other reading after the step that creates its state.
5. Check contiguity: each state's readings form a single run rather
   than being resumed after another state.
6. Size the run from the measurement count, the per-reading dwell and
   the conditioning durations, and compare it with the slot if one is
   given.
7. Aggregate: coverage gaps, repeats, conditioning order or placement
   errors and split blocks are findings; an overrun slot is a
   limitation.

## Pitfalls

- Treating the six semi-axes as three axes measured twice. The two
  senses of an axis are different measurements, and the sequence has
  to name which one each reading is.
- Writing the deperming step into the procedure but running the
  depermed block from readings taken earlier in the session. They are
  as-received readings relabelled, and nothing in the data shows it.
- Adding a second magnetising exposure part way through to "refresh"
  the state. It leaves two states both labelled magnetised, and the
  block no longer describes one condition.
- Reordering blocks around facility availability. Conditioning is
  destructive, so a block moved is a block that has to be recollected
  after the conditioning is redone.
- Failing a sequence for running longer than its booked slot. The
  schedule is not the clause; note it and rebook.

## Behavior contract (gate 3)

The step validation, per-state coverage and repeat detection,
conditioning order checks, state-placement checks, block contiguity,
run-time sizing against an optional slot and the aggregate verdict are
exercised by the gate 3 contract test:
scripts/test_e2007_magnetic_moment_test_sequence.py against
scripts/e2007_magnetic_moment_test_sequence_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_magnetic_moment_test_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
