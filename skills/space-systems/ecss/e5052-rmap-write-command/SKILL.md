---
name: e5052-rmap-write-command
description: "Build and grade a SpaceWire RMAP write command before it goes on the link. Use when an ECSS-E-ST-50-52C clause 5.8.2.3 write is constructed or reviewed: pack the verify, acknowledge and increment options plus the reply-path length code into the instruction byte, unpack a captured byte back into those options, pad the reply path to whole four-byte groups, size the packet from header, payload and check bytes, fold the byte-wise check value over the data, and derive the address span the write touches. Flags a verified write that overruns the target buffer, asks for no reply, or aims at one fixed address. Trigger: ecss, e-st-50-52c, rmap-write-command, rmap-verified-write-buffer, rmap-instruction-byte-packing, rmap-reply-address-padding, rmap-data-check-value, rmap-write-address-span."
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
  tags: [ecss, e-st-50-52-rmap-scope, e5052-rmap-write-command, rmap-verified-write-buffer, rmap-instruction-byte-packing, rmap-reply-address-padding, rmap-data-check-value, rmap-write-address-span]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire RMAP — Write Command (space-systems/ecss/e5052-rmap-write-command)

Use when the task is the write command of ECSS-E-ST-50-52C clause
5.8.2.3 — assembling the command that deposits data into a target's
memory, or reviewing one that has already been assembled, so its option
combination, its sizing and its address span are all defensible.

## Domain quick reference

- A write command carries its payload with it. That makes three things
  vary together: the option flags in the instruction byte, the declared
  data length, and the data check byte that closes the packet. A change
  to any one of them without the others is a malformed command, not a
  variant.
- The instruction byte is a packed field, not a flag word. The top bits
  mark the packet as a command, the next bit separates a write from a
  read, three more carry verify-before-write, acknowledge and increment,
  and the bottom two count the reply path in four-byte groups. Reading a
  captured byte means unpacking exactly those positions.
- Verification is a target-side buffer operation. The target holds the
  whole payload, checks it, and only then commits it, so a verified
  write is bounded by the buffer the target offers. A payload larger
  than that buffer cannot be verified at all, whatever the data-length
  field says.
- A verified write that asks for no acknowledgement is self-defeating:
  the one thing verification produces is a pass-or-fail outcome, and
  with no reply there is nowhere for that outcome to go.
- Incrementing and non-incrementing writes have different address spans.
  An incrementing write occupies one address per byte, so its span has
  to stay inside the base address field; a non-incrementing write
  deposits every byte at the same address, which is what a port or a
  first-in-first-out register wants and what a memory block does not.
- The reply path is padded, not truncated. A path shorter than a whole
  group of four bytes is carried with leading zero bytes so the length
  code stays an integer count of groups.

## Workflow

1. Normalise the specification: logical addresses, key, transaction
   identifier, extended and base address, option flags, reply path and
   either a payload or a declared data length. A payload that disagrees
   with a declared length is an input error, not a preference.
2. Refuse a zero-length write, a length past the three-byte field and an
   address past the four-byte field at validation rather than letting
   them surface as findings later.
3. Pack the instruction byte from the option flags and the reply-path
   length code, and confirm it unpacks back to the same options.
4. Pad the reply path to the whole group its code implies, then size the
   packet as fixed header plus padded path plus payload plus the data
   check byte.
5. Compute the byte-wise check value over the payload when one is
   supplied, and confirm the run of payload plus check value closes on
   zero.
6. Derive the address span from the increment flag and the data length,
   and grade the verified-write combinations: buffer overrun, missing
   acknowledgement, fixed address.
7. Report the instruction byte, header and packet sizes, span, padded
   reply path, findings and a single acceptable flag.

## Pitfalls

- Sizing a write from the payload alone. The header, the padded reply
  path and the data check byte are all on the link, and a link budget
  built from the payload understates the transaction every time.
- Setting verify without agreeing a buffer size with the target. The
  target's buffer is the real limit on a verified write, and a payload
  chosen from the data-length field alone will be rejected rather than
  committed.
- Treating a non-incrementing write as a degenerate incrementing one. It
  is a different operation aimed at a single register; collapsing the
  two hides a payload that is silently overwriting itself.
- Truncating a short reply path instead of padding it. The length code
  counts whole groups, so a three-byte path is carried in a four-byte
  field with a leading zero byte, and dropping that byte shifts every
  field after it.
- Reusing a transaction identifier that is still in flight because the
  write was unacknowledged. An unacknowledged write frees nothing; the
  identifier budget is still the initiator's to manage.

## Behavior contract (gate 3)

The specification validation, instruction-byte packing and unpacking,
reply-path length coding and padding, packet sizing, byte-wise check
value, address span and verified-write grading are exercised by the gate
3 contract test: scripts/test_e5052_rmap_write_command.py against
scripts/e5052_rmap_write_command_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e5052_rmap_write_command.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
