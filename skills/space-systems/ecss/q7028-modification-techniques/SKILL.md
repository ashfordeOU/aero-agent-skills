---
name: q7028-modification-techniques
description: "Validate a printed board modification plan under ECSS-Q-ST-70-28 before any track is cut. Use when a board has to be changed by cutting tracks, adding wires or substituting components and the plan must stand up at review. Interpolates the isolation gap each cut's working voltage demands and refuses a cut still bridged by copper, rates every added wire against its conductor ampacity and derives the intermediate supports its routed length needs, checks each substitution for an approved change reference and a matching land pattern, then draws the plan against the board's added-wire limit. Trigger: ecss, q-st-70-28, board-modification-plan, cut-track-isolation-gap, added-jumper-wire-rating, added-wire-support-spacing, component-substitution-approval, added-wire-board-limit."
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
  tags: [ecss, q-st-70-28-board-repair-scope, q7028-modification-techniques, board-modification-plan, cut-track-isolation-gap, added-jumper-wire-rating, added-wire-support-spacing, component-substitution-approval, added-wire-board-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Board Repair — Modification Techniques (space-systems/ecss/q7028-modification-techniques)

Use when the task is the modification part of the methods of
ECSS-Q-ST-70-28 — changing a printed board assembly away from its
as-designed state by cutting a track, adding a wire, or putting a
different component in an existing position, and showing that the
result is still a controlled configuration.

## Domain quick reference

- A cut track is graded on two separate things. The isolation gap
  between the cut ends has to meet what the working voltage across it
  demands, and the cut has to be complete. A wide gap with a sliver of
  copper still bridging it is not a partial pass; it is an uncut track
  that looks cut.
- The gap the voltage demands is read by interpolating the isolation
  table, not by taking the nearest tabulated row. Rounding down to the
  row below silently accepts a gap the working voltage never permitted.
- An added wire is a new conductor the board was not laid out for, so it
  is rated like one: the gauge has to carry the continuous current, and
  the routed length has to be supported often enough that the wire
  cannot resonate against a neighbour or chafe through its insulation.
- The number of supports follows from the length and the maximum
  unsupported span, and it is a count, not a judgement. A length that
  divides exactly into whole spans needs one fewer support than the
  segment count, and rounding that ratio the wrong way adds a bond the
  board does not need or drops one it does.
- A component substitution is a configuration change before it is a
  workmanship question. Without an approved change reference the board
  no longer matches its drawing, and a replacement whose land pattern
  differs from the one on the board is not a substitution at all.
- Added wires are budgeted per board. A board carrying its limit is at
  the end of what modification can do for it; the next change belongs
  to a board revision, not to another wire.

## Workflow

1. Validate the plan and the board data; an empty plan, a malformed
   item or a non-numeric reading is an input error, not an empty pass.
2. For each cut, interpolate the required isolation gap from the
   working voltage, refusing a voltage outside the tabulated span, and
   compare it with the gap actually left.
3. Independently, check each cut for residual copper; report a bridged
   cut as its own finding rather than folding it into the gap result.
4. For each added wire, take the ampacity of its gauge and compare with
   the continuous current, then derive the intermediate supports the
   routed length needs and compare with the supports planned.
5. For each substitution, check the approved change reference is present
   and non-blank, and that the land pattern matches.
6. Total the added wires the board will carry and compare with its
   limit; reaching the limit is an action, exceeding it is a rejection.
7. Confirm every item carries a modification record, then return
   approve, plan-with-actions or reject with the item-level findings
   listed separately.

## Pitfalls

- Reading the isolation table by nearest row. Interpolation is what
  keeps a cut at an intermediate working voltage honest; rounding to the
  row below accepts gaps the voltage never permitted.
- Accepting a cut on gap alone. Residual copper is a separate
  measurement and a separate failure, and it is the one that leaves the
  net still connected.
- Sizing an added wire on length alone or on current alone. A correctly
  rated conductor routed unsupported across the board is a chafing and
  resonance problem; a well supported wire too thin for its current is a
  thermal one.
- Rounding the support count from a length-to-span ratio without
  absorbing representation error. A length that is exactly four spans
  must not read as four-and-a-bit and buy an extra bond.
- Treating a component substitution as a workmanship step. It is a
  configuration change first, so the approved reference and the land
  pattern are checked before anyone reaches for an iron.
- Adding one more wire to a board already at its limit. The limit is a
  property of the board, not of the plan, so the count includes the
  wires already fitted.

## Behavior contract (gate 3)

The plan validation, isolation-gap interpolation with extrapolation
refused, residual-copper test, conductor ampacity check, support-count
derivation, substitution approval and land-pattern test, added-wire
budget and the approve / plan-with-actions / reject ladder are exercised
by the gate 3 contract test:
scripts/test_q7028_modification_techniques.py against
scripts/q7028_modification_techniques_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7028_modification_techniques.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
