---
name: e7041-absolute-time
description: "Convert an on-board moment to and from the absolute-time parameter a packet definition declares, under ECSS-E-ST-70-41C clause 7.3.10. Use when a generation time, a time-tagged release or a collection-interval start reads plausibly wrong on the ground: fixing the time code, the coarse and fine field widths and the epoch in the definition rather than on the wire, truncating downwards so an encoded time never names a later moment, and refusing a time past the coarse span instead of wrapping it into the wrong era. Trigger: ecss, e-st-70-41c, pus-absolute-time-parameter, cuc-coarse-fine-time-code, cds-day-segmented-time-code, on-board-time-epoch-agreement, absolute-time-span-overflow, time-code-resolution-budget."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-absolute-time, pus-absolute-time-parameter, cuc-coarse-fine-time-code, cds-day-segmented-time-code, on-board-time-epoch-agreement, absolute-time-span-overflow]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Absolute-Time Data Type (space-systems/ecss/e7041-absolute-time)

Use when the task is the absolute-time data type of ECSS-E-ST-70-41C
clause 7.3.10 — the four normative items that fix how a moment is
carried in a packet, and the three agreements the packet itself does
not carry.

## Domain quick reference

- An absolute-time parameter is a count forward from an epoch, not a
  number with a unit. Three things fix its meaning and none of them
  travels with the value: the time code, the field widths, and the
  epoch. A ground system that assumes any of the three reads a
  plausible wrong time rather than failing loudly.
- Two codes are in use. The unsegmented form counts whole seconds in a
  coarse field and binary fractions of a second in a fine field. The
  day-segmented form counts whole days and milliseconds within the
  day, optionally with a sub-millisecond segment.
- The fine field alone fixes the resolution of the unsegmented form:
  one octet gives a 256th of a second, two give a 65536th. Each added
  octet divides the step by 256, and a wider fine field is a finer
  stamp, never a better clock.
- The coarse field alone fixes the span. A two-octet coarse field
  covers about eighteen hours; a four-octet field covers well past any
  mission. Sizing it below the mission end means the count wraps, and
  a wrapped count is a valid-looking time in the wrong era.
- The value is truncated down to the resolution, never rounded. An
  encoded time that reads later than the moment it came from drops out
  of a window closing on that moment, and the loss is invisible.
- The epoch is declared once for the system. Restating a time against
  a different epoch is a subtraction that can go negative, and a
  negative absolute count has no representation — it is a finding, not
  a clamp.

## Workflow

1. Normalise the definition first: code, coarse and fine widths or day
   width and sub-millisecond segment, and the named epoch. Reject a
   width the code does not support rather than padding it.
2. Derive the resolution and the span from the widths, and compare
   both against what the mission actually needs before any value is
   encoded. These two checks catch the definition defects; the value
   tests catch nothing the definition already permits.
3. Encode by scaling to the fine units, flooring, and splitting into
   the two counts. Refuse a time before the epoch and a time at or
   past the span.
4. Decode by the inverse, refusing a count that does not fit the field
   it claims to come from, so a corrupt frame is a refusal rather than
   a date.
5. Where a mission epoch is in use, restate times through the agency
   epoch explicitly instead of carrying two conventions side by side.
6. Assess a definition against representative times: report the worst
   truncation, confirm it never went the wrong way, and name every
   sample the span refused.

## Pitfalls

- Rounding the encoded time to the nearest step. Half the values then
  name a moment that had not happened yet.
- Sizing the coarse field from the current mission phase. Extensions
  outlive the sizing, and the wrap is silent.
- Inferring the epoch from a value that looks like a recent date. Two
  epochs commonly differ by a round number of years, so the wrong one
  still produces a date somebody believes.
- Treating a finer fine field as a better clock. It narrows the
  quantisation and leaves the on-board timekeeping exactly as coarse.
- Comparing times taken from two definitions without restating them.
  Different epochs or different codes make the comparison meaningless
  while both numbers look reasonable.
- Wrapping an out-of-span time to keep an encoder from raising. The
  wrapped value passes every downstream check.

## Behavior contract (gate 3)

The epoch lookup, definition normalisation, resolution and span
derivation, downward-truncating encode, field-overflow refusals, round
trip, epoch restatement and the definition assessment are exercised by
the gate 3 contract test: scripts/test_e7041_absolute_time.py against
scripts/e7041_absolute_time_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_absolute_time.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
