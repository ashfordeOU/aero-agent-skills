---
name: e7041-relative-time
description: "Compute and encode the relative-time parameters a packet definition declares, under ECSS-E-ST-70-41C clause 7.3.11. Use when a collection interval, an offset from a reference or a gap between two events is being carried in a packet: keeping a duration epoch-free so nobody reads it as a date, holding it as a signed two's-complement coarse count whose negative reach is one step longer than its positive one, flooring towards minus infinity so the fine count stays non-negative, and refusing a difference of moments the field cannot hold. Trigger: ecss, e-st-70-41c, pus-relative-time-parameter, signed-duration-two-s-complement, epoch-free-duration, coarse-fine-duration-encoding, absolute-minus-absolute-interval, duration-range-overflow."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-relative-time, pus-relative-time-parameter, signed-duration-two-s-complement, epoch-free-duration, coarse-fine-duration-encoding, duration-range-overflow]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Relative-Time Data Type (space-systems/ecss/e7041-relative-time)

Use when the task is the relative-time data type of ECSS-E-ST-70-41C
clause 7.3.11 — the three normative items that make a duration a
different thing from a moment, even though the two are counted with the
same coarse-and-fine fields.

## Domain quick reference

- A relative-time parameter carries a duration: a collection interval,
  an offset from a reference time, a timeout, the gap between two
  events. It is not measured from anywhere.
- It has no epoch, and that absence is the point. Applying an epoch to
  a duration turns a twelve-second interval into a date twelve seconds
  after the epoch, and the date looks entirely reasonable in a display.
- It is signed. An offset can point before its reference and a drift
  can go the other way, so the coarse count is a two's-complement
  quantity. That makes the range asymmetric: a one-octet coarse field
  reaches -128 but only +127, and code that assumes a symmetric range
  fails at exactly one value.
- The fine count stays non-negative whatever the sign of the duration.
  The total is counted in fine units and floored towards minus
  infinity, so minus half a second with one fine octet is coarse -1
  and fine 128 — not coarse 0 with a negative fine part, which has no
  field to live in.
- Resolution comes from the fine field exactly as it does for an
  absolute time. A duration differenced from moments held at a finer
  resolution than its own is quantised coarser than its own endpoints,
  and the interval is then less precise than either moment in it.
- The arithmetic that is defined is narrow. A moment plus a duration
  is a moment. A moment minus a moment is a duration. A moment plus a
  moment is nothing at all, and every one of the three produces a
  number.

## Workflow

1. Normalise the definition: coarse and fine widths only. Refuse an
   epoch key outright — a relative-time definition that names one has
   already been confused with an absolute-time definition.
2. Derive the resolution from the fine field and the signed range from
   the coarse field, and state the range asymmetrically rather than as
   a magnitude.
3. Encode by scaling to fine units and flooring towards minus
   infinity, then splitting so the fine part is non-negative. Refuse a
   coarse count outside the two's-complement range.
4. Decode by the inverse, refusing a negative fine count and a coarse
   count the field cannot hold.
5. Offset a moment by a duration through a checked addition: refuse a
   result before the epoch and a result at or past the span of the
   absolute field, rather than returning a number that encodes
   somewhere else.
6. Difference two moments into a duration and check the result against
   the signed range before it is stored; a long mission easily exceeds
   a short coarse field.
7. Accumulate durations term by term and refuse on the running total,
   not on the final one — an intermediate that left the range already
   lost the answer.

## Pitfalls

- Reading a duration against an epoch. The result is a plausible
  timestamp, and nothing downstream questions it.
- Assuming a symmetric signed range. The negative end reaches one step
  further, and a bound derived from the positive end rejects a legal
  value while a bound derived from the negative end admits an illegal
  one.
- Encoding a negative duration as a negative fine count. There is no
  field for it; the sign belongs to the coarse count alone.
- Rounding a negative duration towards zero. Flooring and truncating
  agree above zero and disagree below it, so the sign of the error
  flips halfway through the range.
- Differencing two moments held against different epochs. The interval
  is wrong by the epoch offset and stays in range.
- Checking only the final accumulated total. An intermediate overflow
  has already discarded information the final value cannot recover.

## Behavior contract (gate 3)

The epoch-free definition, resolution and asymmetric signed range,
floor-towards-minus-infinity encoding, non-negative fine count, decode
refusals, moment-plus-duration and moment-minus-moment arithmetic,
running-total accumulation and the usage assessment are exercised by the
gate 3 contract test: scripts/test_e7041_relative_time.py against
scripts/e7041_relative_time_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_relative_time.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
