---
name: e7041-time-stamping
description: "Derive the storage time stamp a packet store writes beside every packet it holds, under ECSS-E-ST-70-41C clause 6.15.3.2. Use when a time-window retrieval returns the wrong set of packets, or when a stored record has to be placed on the on-board timeline: separating storage time from the generation time carried inside the packet, encoding the stamp as a coarse-seconds and fine-fraction pair truncated downwards so it never reads later than the moment it came from, bounding the quantisation error by the fine-field width, and flagging a stamp that went backwards. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, packet-storage-time-stamp, storage-time-versus-generation-time, coarse-fine-time-encoding, time-window-packet-retrieval, non-monotonic-storage-stamp."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-time-stamping, packet-storage-time-stamp, storage-time-versus-generation-time, coarse-fine-time-encoding, time-window-packet-retrieval, non-monotonic-storage-stamp]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Packet Storage Time-Stamping (space-systems/ecss/e7041-time-stamping)

Use when the task is the storage time-stamping of ECSS-E-ST-70-41C
clause 6.15.3.2 -- the single requirement that every packet a packet
store holds is held with the on-board time at which it was stored, and
everything a time-window retrieval then depends on.

## Domain quick reference

- Storage time is not generation time. A packet normally carries its
  own generation time in its data field header; the stamp this clause
  asks for records when the store took the packet in. The two coincide
  only when the store was accepting at the moment the packet was made.
- The gap between them is routine, not exceptional. A report generated
  while storage was switched off, or while a store was full and
  bounded, is either lost or taken in later, and either way the
  generation time tells the ground nothing about which retrieval window
  will find it.
- A time-window retrieval selects on storage time, because that is the
  question it is actually asking: which packets did this store take in
  between these two moments. Answering it from generation time returns
  a different set, and for a window that sits inside a link outage it
  can return nothing at all for a period the ground can see was busy.
- The stamp is written in the on-board coarse-and-fine form: whole
  seconds since the epoch plus a fractional count in a fine field of a
  chosen width. The resolution is a negative power of two of a second,
  fixed by that width, and the stamp is the time truncated down to it.
  Truncating down matters: a stamp must never claim a packet was stored
  later than it was, because a window ending at that moment would then
  miss it.
- A wider fine field is not more accurate time, only a finer stamp. It
  narrows the quantisation error and nothing else; a coarse on-board
  clock stays coarse.
- The stamps a store writes are non-decreasing, because it takes
  packets in arrival order. Two stored inside one resolution step
  legitimately share a stamp. One that goes backwards does not -- it
  says the on-board time was stepped by a correction while the store
  was filling, and every window over that region answers wrongly until
  someone knows about the discontinuity.

## Workflow

1. Validate the fine-field width and the time: a finite, non-negative
   number of seconds since the epoch, and a width the encoding
   supports.
2. Scale the time by the number of fine units in a second, truncate
   downwards, and split the result into the coarse and fine fields.
   Refuse a time that overflows the coarse field rather than wrapping
   it.
3. Keep the packet's generation time, if it carries one, beside the
   storage stamp instead of replacing it -- the latency between them is
   itself evidence.
4. Decode the stamp back to seconds for any arithmetic, so the
   quantisation is applied once and everything downstream agrees.
5. Walk a run of stamped packets in order: a stamp equal to the one
   before it is a repeat inside one resolution step, a stamp below it
   is a backwards finding naming both packets.
6. Answer a retrieval window on storage time, closed at both ends, and
   report the answer the same window would have given on generation
   time so the difference is visible rather than assumed away.
7. Report the resolution alongside the stamps; a window narrower than
   the resolution cannot separate the packets inside it.

## Pitfalls

- Retrieving a window on generation time. It is the time that happens
  to be printed in the packet, not the time the store used, and the
  answer is quietly wrong rather than empty.
- Rounding the stamp to the nearest step. Half the packets then carry a
  stamp later than their storage moment, and a window ending on that
  moment drops them.
- Reading repeated stamps as a fault. Inside one resolution step they
  are correct; the resolution is the thing to report, not a defect to
  chase.
- Treating a backwards stamp as a sorting problem. Re-sorting hides the
  clock correction that caused it and leaves every window over that
  region answering from a timeline that never existed.
- Widening the fine field to fix a coarse clock. The stamps get finer
  and no more true.
- Subtracting generation time from storage time without checking the
  sign. A negative latency is a stamp or a clock problem, not a fast
  store.

## Behavior contract (gate 3)

The fine-field validation, downward truncation, coarse-field overflow
refusal, round-trip decoding, quantisation-error bound, latency check,
repeated- and backwards-stamp findings and the storage-versus-generation
window comparison are exercised by the gate 3 contract test:
scripts/test_e7041_time_stamping.py against
scripts/e7041_time_stamping_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_time_stamping.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
