---
name: q7028-conductor-repair
description: "Design the repair of a broken, cut or lifted conductor on a printed-circuit-board assembly. Use when a track is open and the method, the wire and the bonding still have to be worked out: it chooses between a lap-soldered replacement segment and an insulated jumper from the gap length and the track width, refuses a break past the reach of either, computes the overlap each lap end needs, sizes the jumper from the circuit current and a current-density derating, spaces the bonds along the unsupported run, and compares the replacement cross-section against the copper it replaces. Trigger: ecss, q-st-70-28c-board-repair, pcb-conductor-repair, pcb-track-lap-solder-splice, pcb-jumper-wire-sizing, pcb-jumper-bond-spacing, pcb-conductor-cross-section."
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
  tags: [ecss, q-st-70-28c-board-repair, q-st-70-28c, q7028-conductor-repair, pcb-conductor-repair, pcb-track-lap-solder-splice, pcb-jumper-wire-sizing, pcb-jumper-bond-spacing, pcb-conductor-cross-section]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Board Repair — Conductor Repair (space-systems/ecss/q7028-conductor-repair)

Use when the task is the conductor method clause of ECSS-Q-ST-70-28C: a track
is open, cut or lifted, and the repair has to restore the path it carried
without becoming the next thing that fails.

## Domain quick reference

- Two things pick the method, not one. A short gap is lapped only if the
  surviving track is also wide enough to solder a replacement segment onto; a
  fine track takes a jumper however small the break, because there is nowhere
  to make the joint.
- The lap overlap scales with the track it lands on, with a floor. A wide
  track needs a proportionally longer overlap to carry the joint, and a very
  fine track still needs a minimum length of contact regardless of how narrow
  it is.
- The replacement segment is longer than the gap by both overlaps. Cutting it
  to the gap is the commonest way a lap repair ends up with no joint at either
  end.
- A jumper is sized from current, not from what is on the bench. Wire
  cross-section carries a current density, that density is derated on a
  repaired board, and the thinnest wire whose derated capacity still covers
  the circuit current is the one to use — thicker wire is stiffer and pulls on
  its terminations.
- An unsupported jumper run is a vibration problem. Bonds along the route hold
  it down, and the count follows from the length: every span up to the
  unsupported limit needs an end, so the bonds are one more than the spans.
- The repaired path must not be thinner than the original. A fine jumper
  across a wide power track restores continuity and moves the weakest point to
  the repair, which is why the two cross-sections are compared rather than
  assumed.
- A board only carries so many jumpers before it stops being a repaired board.
  The count is held per board, not per repair, so the fifth jumper is visible
  to the person approving the first.
- Past the reach of a jumper there is no method at all, and saying so is the
  output. Stretching a jumper across the board is not a longer repair, it is
  an unqualified one.

## Workflow

1. Take the gap and the track width; refuse the repair outright where the gap
   is past what a jumper may span.
2. Choose a lapped replacement segment where the gap is short and the track is
   wide enough to solder to; otherwise choose a jumper and say which of the
   two drove it.
3. For a lap joint, compute the overlap from the track width against its
   floor, and the replacement segment length as the gap plus both overlaps.
4. For a jumper, size the wire from the circuit current against the derated
   capacity of each available gauge, thinnest first.
5. Count the bonds along the jumper route from the unsupported-run limit, and
   check the route length and the board's jumper count.
6. Compare the replacement cross-section against the original track copper and
   flag a repair that would be the new weakest point.
7. Return the repair with every finding; ready only when there are none.

## Pitfalls

- Choosing the method on gap length alone. The gap is short so the repair is
  lapped, the track is too fine to hold a joint, and the splice lifts on the
  first thermal cycle.
- Cutting the replacement segment to the size of the gap. There is no overlap
  left at either end and the joint is a butt joint made with solder.
- Grabbing the wire that is already stripped on the bench. It is either too
  thin for the current or stiff enough to lever its own terminations off the
  board.
- Running a jumper point to point and bonding only the ends. The span in
  between resonates, and the failure appears in vibration testing with no
  visible cause at either termination.
- Jumpering a power track with signal wire. Continuity is restored, the board
  passes test, and the repair is now the current-limiting element in the path.
- Counting jumpers per repair event. Five separate approvals each added one,
  nobody ever saw the total, and the board is a wiring loom.

## Behavior contract (gate 3)

Method selection from gap and track width, the lap overlap floor and segment
length, gauge selection against a derated current density, bond counting over
the unsupported run, the per-board jumper count and the replacement
cross-section comparison are exercised by the gate 3 contract test:
scripts/test_q7028_conductor_repair.py against
scripts/q7028_conductor_repair_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7028_conductor_repair.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
