---
name: e7041-determining-orbit-positions
description: "Compute an orbit position and the angular distance between two of them under ECSS-E-ST-70-41C clause 6.22.4: check an ascending-node angle against one revolution and an orbit number against its on-board field, order positions on a single key, and decide whether a scheduled orbit position has already been passed. Use when the on-board orbit position representation, an orbit counter wrap, the degrees still to fly to a scheduled position, or the passed-or-pending decision behind a position-based schedule is being defined or reviewed. Refuses an angle outside one revolution and an orbit number beyond the field. Trigger: ecss, e-st-70-41c, pus-service-22, orbit-position-determination, ascending-node-angle, orbit-number-field-wrap, orbit-position-ordering-key, position-passed-decision."
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
  tags: [ecss, e-st-70-41c, pus-service-22, e7041-determining-orbit-positions, orbit-position-determination, ascending-node-angle, orbit-number-field-wrap, orbit-position-ordering-key, position-passed-decision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Position-Based Scheduling — Determining Orbit Positions (space-systems/ecss/e7041-determining-orbit-positions)

Use when the task is the orbit position determination of ECSS-E-ST-70-41C
clause 6.22.4 — fixing what an orbit position means on board, comparing two
of them, and deciding whether the spacecraft has already flown past a
position something was scheduled at.

## Domain quick reference

- An orbit position is two numbers, not one. The orbit number counts whole
  revolutions and the angle locates a point inside the current one, and a
  comparison that looks at either half alone gets the wrong answer roughly
  once per revolution.
- The angle spans one revolution measured from the ascending node, so it
  reaches the node again at zero of the next orbit number rather than at a
  full revolution of the current one. A value at the top of the range is an
  input error, not the node.
- Comparison is easiest on one key. Folding the pair into degrees flown since
  the counter started makes ordering, distance and the passed decision plain
  arithmetic, and removes the boundary case that a pairwise comparison keeps
  reintroducing.
- Distance runs forward only. The spacecraft cannot fly backwards along its
  own ground track, so a target behind the current position is reached after
  the orbit number field wraps, and that wrap is a real distance rather than
  a negative one.
- The orbit number field is finite. A counter of a given width returns to
  zero, and a schedule that assumes a monotonically rising orbit number stops
  releasing anything the first time it wraps.
- Equality needs a tolerance. The angle arrives from an orbit propagation, so
  two computations of the same point differ in the last bits and a strict
  equality test on it never fires.

## Workflow

1. Validate the orbit number field width, then validate each position: a
   whole orbit number inside the field and a finite angle inside one
   revolution measured from the ascending node.
2. Fold each position into its ordering key in degrees flown, so that
   ordering and distance need no boundary handling.
3. Compare two positions for equality on the orbit number plus an angle
   tolerance, never on a bare float equality.
4. Measure the forward angular distance from the current position to a
   target, adding a whole field wrap when the target lies behind.
5. Decide whether each scheduled position has been passed, counting a
   position the spacecraft is standing on as passed.
6. Group a set of scheduled positions into passed and pending, report the
   degrees still to fly to each pending one, and name the nearest.

## Pitfalls

- Comparing orbit positions by angle alone. Two positions at the same angle
  on different orbits then look identical, and an activity scheduled a
  revolution ahead releases immediately.
- Accepting a full revolution as an angle. It names the ascending node of the
  next orbit, so the position it encodes is off by one whole revolution from
  the one intended.
- Reporting a negative distance for a target behind the current position. The
  caller reads it as a small remaining distance and releases the activity a
  whole counter wrap early.
- Assuming the orbit number never wraps. The field has a width, and a
  schedule built on an ever-rising number goes silent at the wrap rather than
  reporting anything.
- Testing angle equality exactly. The angle comes from a propagation, so the
  two sides differ in the last bits and the equality branch is dead code.

## Behavior contract (gate 3)

The angle validation, position validation, ordering key, tolerance-based
equality, forward angular distance across the field wrap, the passed decision
and the grouping of a scheduled set are exercised by the gate 3 contract
test: scripts/test_e7041_determining_orbit_positions.py against
scripts/e7041_determining_orbit_positions_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e7041_determining_orbit_positions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
