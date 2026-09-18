---
name: e5052-rmap-read-command
description: "Compute the sizing and grade the option set of a SpaceWire RMAP read command. Use when an ECSS-E-ST-50-52C clause 5.8.2.4 read is built or reviewed: pack acknowledge, increment and the reply-path length code into the instruction byte, confirm the command carries no payload, size the command and the returning reply separately, derive the address span and the data share of the traffic, then check a captured reply against the command it answers. Flags a read asking for no reply, a verify bit on a read, a span past the address field, and an increment setting that contradicts the region. Trigger: ecss, e-st-50-52c, rmap-read-command, rmap-read-reply-sizing, rmap-read-address-span, rmap-read-instruction-byte, rmap-reply-status-consistency, rmap-non-incrementing-port-read."
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
  tags: [ecss, e-st-50-52-rmap-scope, e5052-rmap-read-command, rmap-read-reply-sizing, rmap-read-address-span, rmap-read-instruction-byte, rmap-reply-status-consistency, rmap-non-incrementing-port-read]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire RMAP — Read Command (space-systems/ecss/e5052-rmap-read-command)

Use when the task is the read command of ECSS-E-ST-50-52C clause 5.8.2.4
— asking a target to return a span of its memory, and deciding whether
the command, the reply it provokes and the traffic the pair costs are
the ones the design intended.

## Domain quick reference

- A read is asymmetric. The command carries a requested length but no
  payload and no payload check byte; the reply carries the returned
  bytes and closes with one. Sizing the two halves with the same formula
  overstates the command and understates the reply.
- Acknowledgement is not optional in practice for a read. The returned
  data lives in the reply, so a read that asks for no reply produces
  nothing at the initiator however well formed it is.
- The verify option belongs to the write side. A read has nothing to
  hold in a buffer and nothing to commit, so a verify bit on a read
  instruction is either a copied template or a mis-packed byte.
- The increment flag chooses between two different operations. An
  incrementing read walks one address per byte and belongs to a memory
  region; a non-incrementing read pulls repeatedly from one location and
  belongs to a port-style register or a queue. Pairing the wrong flag
  with the region returns either a walk off the register or the same
  location copied many times.
- The share of the transaction that is actual data matters at small
  lengths. Twenty-eight header and check bytes accompany every read, so
  a four-byte read spends most of the link on overhead and a long read
  amortises it.
- A reply has to agree with its command. A successful status owes
  exactly the requested number of bytes; a non-zero status owes none at
  all, and the identifier has to be the one the command allocated.

## Workflow

1. Normalise the specification and refuse the inputs that are errors
   rather than findings: a payload attached to a read, a zero length, a
   length past the three-byte field, an address past the four-byte
   field, an unknown region word.
2. Pack the instruction byte with the write bit clear and the option
   flags and reply-path code in their positions; confirm a captured byte
   unpacks back to the same options and is rejected when it marks a
   write or a reply.
3. Size the command as fixed header plus the padded reply path, and the
   reply as reply header plus the requested bytes plus the payload check
   byte, with no reply at all when none was asked for.
4. Derive the address span from the increment flag and the requested
   length, and the returned-data share from both halves of the
   transaction.
5. Grade the option set: missing acknowledgement, a verify bit, a span
   past the address field, and an increment flag that contradicts a
   declared region.
6. When a reply record is supplied, check status against returned length
   and the identifier against the command, and fold those findings into
   the single acceptable flag.

## Pitfalls

- Sizing the reply with the command header. The reply header is shorter
  and carries a status byte in place of the key, so a budget built from
  one header for both directions is wrong in both.
- Leaving the verify bit set after copying a write template. The target
  has no verification to perform on a read, and the stray bit makes a
  capture hard to read back.
- Reading a port-style register with the increment flag set. Each byte
  then comes from a different address and the register is sampled once,
  which is rarely what a queue drain intends.
- Accepting a short successful reply. A success status that returns
  fewer bytes than were asked for is a defect in the target, not a
  partial result to be concatenated with a retry.
- Concatenating data from a reply that reports a non-zero status. A
  failed reply carries no payload, so anything read out of it is
  whatever the buffer held before.

## Behavior contract (gate 3)

The specification validation, instruction-byte packing and unpacking,
reply-path coding, command and reply sizing, address span,
returned-data share and reply consistency checks are exercised by the
gate 3 contract test: scripts/test_e5052_rmap_read_command.py against
scripts/e5052_rmap_read_command_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e5052_rmap_read_command.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
