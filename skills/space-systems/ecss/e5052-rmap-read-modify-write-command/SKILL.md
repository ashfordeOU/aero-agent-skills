---
name: e5052-rmap-read-modify-write-command
description: "Derive the merge, the sizing and the option bits of a SpaceWire RMAP read-modify-write command. Use when an ECSS-E-ST-50-52C clause 5.8.2.5 operation is built or reviewed: split the data field into an operand and an equal-width mask, confirm the length is even and permitted, check the option bits that pick this command out of the others, apply the merge taking masked bits from the operand, size the command against the half-length reply, and count the bits really flipped. Flags an empty mask, a full mask, operand bits the mask discards and an unaligned address. Trigger: ecss, e-st-50-52c, rmap-read-modify-write, rmap-operand-mask-pair, rmap-atomic-bit-merge, rmap-rmw-reply-length, rmap-rmw-address-alignment, rmap-rmw-option-bits."
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
  tags: [ecss, e-st-50-52-rmap-scope, e5052-rmap-read-modify-write-command, rmap-operand-mask-pair, rmap-atomic-bit-merge, rmap-rmw-reply-length, rmap-rmw-address-alignment, rmap-rmw-option-bits]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire RMAP — Read-Modify-Write Command (space-systems/ecss/e5052-rmap-read-modify-write-command)

Use when the task is the read-modify-write command of ECSS-E-ST-50-52C
clause 5.8.2.5 — changing selected bits of one location without
disturbing the rest of it, in a single transaction the target performs
without releasing the location in between.

## Domain quick reference

- The data field of this command is two things side by side: an operand
  and a mask of exactly the same width. That is why its length is always
  even, and why the reply is exactly half as long as the command data —
  the reply returns the content found before the merge, not the operand
  and mask again.
- The merge is per bit. Every bit the mask selects is taken from the
  operand; every bit it does not select is left as the target found it.
  Bits set in the operand outside the mask are discarded, so an operand
  that carries them is either sloppy or aimed at a different mask.
- The whole value of the command is that the read and the write are not
  separable. A read followed by a write from the initiator leaves a
  window in which another initiator, or the target's own logic, can
  change the location; this command closes that window.
- The operand width is one, two, three or four bytes, which is why the
  data field runs from two to eight bytes in even steps. A wider update
  is not this command's job.
- An all-zero mask reads and rewrites the same content, which costs a
  full transaction and changes nothing. An all-ones mask replaces the
  whole location, which a plain write does with no read half at all.
  Both are legal encodings and both usually mean the mask was built
  wrong.
- The operation touches one address. Aligning that address to the
  operand width keeps the update inside one natural register and avoids
  a target implementation splitting it across two.

## Workflow

1. Normalise the specification and refuse the inputs that are errors:
   an empty data field, an odd length, a length outside the permitted
   even set, a byte outside its range, a declared length that disagrees
   with the supplied bytes, and a previous-content record whose width is
   not the operand width.
2. Split the data field at its midpoint into operand and mask, and take
   the operand width from that midpoint rather than from a separate
   declaration.
3. Pack the instruction byte from the fixed option-bit combination that
   identifies this command plus the reply-path length code, and reject a
   captured byte whose option bits are any other combination.
4. Size the command as header plus reply path plus operand and mask plus
   the payload check byte, and the reply as reply header plus the
   operand width plus its own check byte.
5. Apply the merge to the previous content when it is supplied, and
   count the bits that actually flip — a merge that changes nothing is
   worth knowing about before the transaction is scheduled.
6. Grade the mask: empty, full, or discarding operand bits; then grade
   the address against the operand width.
7. Report operand, mask, widths, instruction byte, both sizes, mask
   selectivity, findings and a single acceptable flag.

## Pitfalls

- Sizing the reply from the command data length. The reply returns the
  previous content only, so it is half the command payload; a buffer
  sized for the full data field will be half empty and a buffer sized
  from the reply will under-read the command.
- Building the mask from the bits you want to end up set rather than the
  bits you want to control. Clearing a bit needs it selected in the mask
  and clear in the operand; a mask built from the target value alone can
  never clear anything.
- Treating an all-ones mask as the safe default. It turns the command
  into a slower write and discards the atomicity argument that justified
  using the command in the first place.
- Splitting the operation into a read then a write when a target reports
  the command unimplemented. The two are not equivalent; the split
  reintroduces exactly the window the command exists to close.
- Ignoring the previous content the reply returns. It is the evidence
  that the merge started from the state the design assumed, and it is
  the only record of what was there before.

## Behavior contract (gate 3)

The specification validation, operand and mask split, option-bit packing
and rejection, command and reply sizing, masked merge, selected-bit and
changed-bit counts and the mask and alignment grading are exercised by
the gate 3 contract test:
scripts/test_e5052_rmap_read_modify_write_command.py against
scripts/e5052_rmap_read_modify_write_command_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e5052_rmap_read_modify_write_command.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
