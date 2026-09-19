---
name: q7028-laminate-and-hole-repair
description: "Determine whether laminate damage, a delamination or a damaged plated hole on a printed board may be repaired under ECSS-Q-ST-70-28, and by which method. Use when a board has come back with base-material damage or a broken barrel and the decision has to survive review. Sizes the affected area against the board, tests whether the defect entered the conductor clearance envelope, recomputes the barrel wall left after damaged plating is removed and replated, then picks barrel replating, an eyelet or refusal, and draws the work against the board's repair allowance. Trigger: ecss, q-st-70-28, board-repair-laminate-damage, board-delamination-area-fraction, board-repair-conductor-clearance, plated-hole-barrel-replating, plated-hole-eyelet-insertion, board-repair-allowance."
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
  tags: [ecss, q-st-70-28-board-repair-scope, q7028-laminate-and-hole-repair, board-repair-laminate-damage, board-delamination-area-fraction, board-repair-conductor-clearance, plated-hole-barrel-replating, plated-hole-eyelet-insertion, board-repair-allowance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Board Repair — Laminate and Plated-Hole Repair (space-systems/ecss/q7028-laminate-and-hole-repair)

Use when the task is the laminate and hole part of the repair methods of
ECSS-Q-ST-70-28 — deciding whether damage to the base material, a
delamination, or a damaged plated-through hole on a printed board
assembly may be repaired at all, which method applies, and what the
repair costs the board out of its remaining allowance.

## Domain quick reference

- Two different things make a surface defect unrepairable, and they are
  not the same measurement. One is size: the affected area as a fraction
  of the board. The other is position: a defect that has entered the
  clearance envelope between two conductors has changed the insulation
  the design relies on, however small it is.
- Because those two are independent, the common mistake is to grade the
  defect on area alone. A one-square-millimetre delamination sitting
  between two adjacent tracks is a refusal; a considerably larger one in
  clear laminate away from any conductor is routine.
- A plated hole is graded on what is left of the barrel wall after the
  damaged plating has been removed, not on what was deposited during the
  repair. Removal thins, replating restores: the number that matters is
  original minus removed plus replated, compared with the minimum wall.
- Removal also grows the hole. A barrel that has been cleaned back until
  the finished diameter exceeds the drawing allowance no longer matches
  the annular ring or the lead it must accept, so diameter growth is a
  refusal in its own right and outranks a healthy replated wall.
- When the wall cannot be brought back, an eyelet or interfacial insert
  can re-establish the connection, but only in a hole big enough to seat
  one without lifting the remaining ring. That route is a deviation from
  the as-designed board and carries an approval, not a signature.
- Repairs are budgeted per board. A board that has already taken its
  permitted repairs is not a harder case; it is scrap, and the count is
  checked before the method is chosen, never after the work is done.

## Workflow

1. Validate the board geometry, the repair history and the defect
   record; a zero board dimension, a negative count or a defect larger
   than the board it sits on is an input error, not a severe case.
2. Size the surface defect: form its bounding area, divide by the board
   area, and compare with the area allowance using a named tolerance so
   a defect exactly on the limit is accepted rather than lost to
   floating-point representation.
3. Independently, compare the distance from the defect to the nearest
   conductor with the minimum clearance. Record encroachment as its own
   outcome; do not fold it into the area result.
4. For a plated hole, recompute the barrel wall as original minus
   removed plus replated, and refuse outright if the removal took more
   than the original wall — that barrel is gone, not thinned.
5. Check the finished-diameter growth against its allowance before
   looking at the wall, so a hole cleaned past the drawing limit is
   refused even when the replating reads well.
6. Pick the method: barrel replating while the wall meets its minimum,
   an eyelet when it does not and the hole can seat one, refusal
   otherwise.
7. Draw the repair against the board allowance and return repairable,
   repair-with-approval, or not-repairable, with every finding that
   drove the verdict named separately.

## Pitfalls

- Grading a surface defect on area alone. Position is the other half of
  the decision, and a small defect between conductors fails on clearance
  while passing on area.
- Reading the replating thickness as the barrel wall. The deposited
  layer is one term of three; a heavy replate over a barrel that was
  cleaned almost away still leaves a wall under the minimum.
- Accepting a hole because the wall came back, without checking what the
  cleaning did to the diameter. Growth past the allowance breaks the
  annular ring and the lead fit whatever the wall reads.
- Treating an eyelet as an equivalent repair. It re-establishes the
  connection by adding hardware the design did not call for, so it is
  reported as a deviation needing approval, never as a routine method.
- Choosing the method first and checking the repair count afterwards. A
  board out of allowance is not repairable by any method, so the count
  is a precondition of the decision.
- Relaxing the area allowance or the minimum wall to let a marginal case
  through. An exact equality at a limit is a representation question,
  absorbed by the tolerance inside the comparison; the engineering limit
  stays as specified.

## Behavior contract (gate 3)

The input validation, defect sizing, clearance encroachment test, barrel
wall recomputation, diameter-growth refusal, method ladder, repair
allowance and the combined verdict are exercised by the gate 3 contract
test: scripts/test_q7028_laminate_and_hole_repair.py against
scripts/q7028_laminate_and_hole_repair_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7028_laminate_and_hole_repair.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
