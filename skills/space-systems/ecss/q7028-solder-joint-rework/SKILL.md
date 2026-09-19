---
name: q7028-solder-joint-rework
description: "Evaluate whether a solder joint on a printed board assembly may be reworked, and grade the joint the rework leaves behind, under ECSS-Q-ST-70-28. Use when a joint must be touched again and the iron settings, cycles already spent and workmanship criteria must all agree. Converts planned dwell into thermal exposure units on a doubling rule, so a short hot touch and a long warm one add on one scale, checks the total against the budget, refuses a lifted pad or a spent cycle count, then grades wetting angle, fillet coverage and lead protrusion on the worst characteristic. Trigger: ecss, q-st-70-28, solder-joint-rework-permission, solder-rework-cycle-budget, solder-iron-tip-window, solder-thermal-exposure-units, solder-wetting-contact-angle, solder-fillet-coverage."
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
  tags: [ecss, q-st-70-28-board-repair-scope, q7028-solder-joint-rework, solder-joint-rework-permission, solder-rework-cycle-budget, solder-iron-tip-window, solder-thermal-exposure-units, solder-wetting-contact-angle, solder-fillet-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Board Repair — Solder Joint Rework (space-systems/ecss/q7028-solder-joint-rework)

Use when the task is the solder-joint part of the repair methods of
ECSS-Q-ST-70-28 — deciding whether a particular joint may be reworked
today given its pad, its history and the iron in front of it, and then
grading the finished joint against the same soldering workmanship
criteria a first-time joint is held to.

## Domain quick reference

- Rework is budgeted twice over, and the two budgets are different
  things. One is a count of cycles the joint may take. The other is
  thermal: how much heat the pad, the laminate bond beneath it and the
  component body have absorbed in total.
- A count alone is too coarse to protect the pad, because a cycle is
  not a fixed dose. Dwell and tip temperature both set the dose, and
  they trade against each other, so they are put on one scale before
  they can be added: seconds at a reference tip temperature count once,
  and each doubling interval above the reference counts double.
- On that scale a two-second touch one interval hot is the same dose as
  four seconds at the reference. That is what lets prior history and a
  planned operation be compared with a single budget rather than argued
  about case by case.
- The iron window is a gate, not a contributor. A tip below its window
  will not wet and will be held on longer to compensate; a tip above it
  damages the pad quickly. Either way the setting is corrected before
  the work starts, not traded against the exposure budget.
- A pad that has separated from the laminate ends the discussion: there
  is nothing for a new joint to key to. A pad that is damaged but still
  bonded is a different case, reworkable only under an approved
  deviation.
- The finished joint is graded on its worst characteristic, never on an
  average of them. Wetting contact angle, fillet coverage and, for a
  through-hole lead, protrusion are independent; each one failing is
  enough, and the report names which one drove the rejection.

## Workflow

1. Validate the pad condition, the rework history, the iron window and
   the planned dwell; a negative count, an inverted window or a
   non-numeric reading is an input error, not a marginal joint.
2. Take the cycle budget state: how many cycles remain, whether this is
   the last permitted one, whether the count is already spent.
3. Check the tip setting against its qualified window with a named
   tolerance, so a setting exactly on an edge reads as inside.
4. Convert the planned dwell and tip temperature into exposure units on
   the doubling rule, add the exposure the joint already carries, and
   compare the total with the budget.
5. Refuse the rework on a lifted pad, a spent cycle count, an iron out
   of window or an exceeded exposure budget; route a damaged-bonded pad
   or a last permitted cycle to approval; otherwise permit it.
6. Where post-rework measurements exist, grade wetting angle, fillet
   coverage and lead protrusion separately and take the worst.
7. Report the permission, the exposure arithmetic, the finished-joint
   verdict and every finding by name.

## Pitfalls

- Counting rework cycles and calling that thermal control. A cycle is
  not a fixed dose; two cycles with a cool iron can be gentler than one
  long touch with a hot one, and only the exposure scale sees that.
- Adding seconds across operations carried out at different tip
  temperatures. Raw seconds are not comparable; they have to be
  converted onto the reference scale before they are summed.
- Trading an out-of-window iron against a remaining exposure budget. The
  window is a precondition of the operation, so it refuses the work
  regardless of how much budget is left.
- Reading a damaged pad as a lifted pad, or the reverse. One is
  reworkable under approval and the other is not reworkable at all, and
  collapsing them either scraps good hardware or flies a joint with
  nothing under it.
- Averaging the finished-joint characteristics. A generous fillet cannot
  compensate a dewetted contact angle; the verdict is the worst
  characteristic and the report names it.
- Widening the coverage minimum or the angle limit to pass a marginal
  joint. An exact equality at a limit is absorbed by the tolerance
  inside the comparison; the workmanship limit stays as specified.

## Behavior contract (gate 3)

The input validation, cycle budget, iron-window gate, doubling-rule
exposure conversion, cumulative budget comparison, permission ladder and
worst-characteristic joint grading are exercised by the gate 3 contract
test: scripts/test_q7028_solder_joint_rework.py against
scripts/q7028_solder_joint_rework_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7028_solder_joint_rework.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
