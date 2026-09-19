---
name: q7026-terminal-placement
description: "Assess where a contact or terminal sits on a prepared conductor before the die closes. Use when a wire has been inserted into a barrel and the seating has to be graded while it can still be changed for free: measure the insulation-to-barrel gap against the band for that contact, confirm the conductor bottomed in the bore, read the inspection window fill, count strands left outside the barrel, check that insulation and conductor are each under their own grip, and grade how square the contact sits in the nest. Trigger: ecss, q-st-70-26-crimping, crimp-insulation-gap-band, crimp-conductor-bottoming-check, crimp-inspection-window-fill, crimp-strands-outside-barrel, crimp-contact-die-nest-seating."
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
  tags: [ecss, q-st-70-26-crimping, q7026-terminal-placement, crimp-insulation-gap-band, crimp-conductor-bottoming-check, crimp-inspection-window-fill, crimp-strands-outside-barrel, crimp-contact-die-nest-seating]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Terminal Placement (space-systems/ecss/q7026-terminal-placement)

Use when the Preparation clause of ECSS-Q-ST-70-26 is the task at the
moment the contact goes on the wire: deciding whether the terminal is
positioned correctly, before the tool is closed and while every finding
is still a reposition rather than a remake.

## Domain quick reference

- Placement is the last free decision. Once the die closes, each of
  these findings costs the contact and the wire length, so the grading
  is deliberately done before the cycle and not after it.
- The insulation gap is two-sided for two different reasons. Too small
  and insulation is driven under the conductor grip, where it sits
  between the barrel wall and the strands and no cold weld forms
  through it. Too large and bare conductor is exposed between the two
  grips, supported by neither and free to flex.
- Bottoming is not the same question as gap. A conductor can sit at the
  correct gap and still be short of the back of the bore, because the
  strands compressed or the bundle caught on the barrel mouth.
- Bottoming has two different failures that need different answers. A
  conductor pushed in short can be pushed further; a conductor whose
  exposed length is shorter than the bore can never reach the back, and
  that end goes back to preparation instead of being nudged.
- The inspection window exists to make bottoming visible. On contacts
  that have one, a part-filled window is often the only observable
  warning that the bundle did not go all the way in, because the
  insertion measurement is taken outside the contact.
- A strand outside the barrel is two problems. It is conductor removed
  from the joint, and it is a loose piece of metal inside a sealed
  assembly.
- The two grips have different jobs. The conductor grip makes the
  electrical joint and the insulation grip takes the bending load off
  the strands, so insulation under the first and bare conductor under
  the second are both misplacements even when the dimensions pass.
- Squareness in the nest propagates. A contact that sits off axis is
  crimped off axis, and the resulting crimp height is measured across a
  section the die never intended.

## Workflow

1. Validate the contact table: a two-sided gap band, a positive bore
   depth with a bottoming tolerance that stays inside it, a window fill
   requirement, a strand count and a stray allowance below it, and a
   seating error limit.
2. Take the entry for the contact part in hand, refusing a part number
   the table does not carry rather than borrowing a neighbour's band.
3. Grade the insulation gap against the band and report which side it
   fell on and where inside the band it sits.
4. Grade bottoming against the bore depth less its tolerance, and split
   the shortfall into the reposition case and the back-to-preparation
   case on the exposed conductor length. Refuse an insertion depth
   larger than the conductor that was exposed.
5. Read the inspection window where the contact has one, and say so
   explicitly where it does not, so a reviewer knows the bottoming
   evidence rests on the insertion measurement alone.
6. Balance the strand bookkeeping: strands in the barrel plus strands
   outside it must account for the strand count the contact expects.
7. Check both grips and the seating angle, then take the worst of the
   six checks, name every check at that level, and roll the batch up
   with an explicit ready-to-crimp flag that also fails on unrecorded
   placements.

## Pitfalls

- Grading the insulation gap as a maximum only. A gap driven to zero is
  the more common defect and it is the one that hides insulation inside
  the crimp where nothing downstream can see it.
- Treating gap and bottoming as the same measurement. They are taken at
  opposite ends of the barrel and a wire can pass one while failing the
  other.
- Nudging a conductor that cannot reach the back of the bore. Pushing
  harder on an end that is simply too short deforms the strands and
  leaves the same shortfall.
- Skipping the inspection window because the insertion depth was
  measured. The measurement is taken outside the contact and cannot see
  a bundle that caught on the barrel mouth.
- Letting a strand outside the barrel pass because the joint will still
  carry the current. The loose strand is a contamination and shorting
  question independent of the conductor cross-section.
- Reading insulation under the conductor grip as extra strain relief.
  It is an insulator inside the electrical joint.
- Accepting an off-axis contact because the crimp height will be
  measured afterwards. The height is then measured across a section the
  die geometry never defined.
- Reporting a batch ready to crimp without counting the placements that
  were never recorded. An unrecorded placement is not an accepted one.
- Comparing a gap, an insertion depth or a seating angle with its limit
  by bare arithmetic. A value specified to land exactly on the limit can
  evaluate a few units in the last place past it after a unit
  conversion, so the comparison absorbs that representation error while
  the limit stays untouched.

## Behavior contract (gate 3)

The contact table validation and its refusal of an untabulated part, the
two-sided insulation gap grading, the bottoming split between reposition
and back-to-preparation, the inspection window reading including the
no-window case, the strand bookkeeping and stray allowance, the two grip
checks, the nest seating grade, the per-placement worst disposition and
the batch rollup with its ready-to-crimp flag are exercised by the gate 3
contract test: scripts/test_q7026_terminal_placement.py against
scripts/q7026_terminal_placement_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7026_terminal_placement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
