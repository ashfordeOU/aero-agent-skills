---
name: e7041-octet-string
description: "Verify an octet-string parameter field against ECSS-E-ST-70-41C clause 7.3.8, where an opaque run of whole octets is carried either at a length the format code fixes or behind a count field. Use when a blob parameter comes back short, or when a ground tool has started interpreting one as text: holding a fixed field to exactly its declared octet count rather than padding or truncating it, bounding a variable run by what its count field can announce, refusing a payload announced longer than the octets that follow, and keeping the content opaque so no character set or numeric reading is imposed on it. Trigger: ecss, e-st-70-41-packet-utilisation-scope, pus-octet-string-parameter-type, octet-string-count-field-width, fixed-length-octet-field, variable-length-octet-field, opaque-payload-handling, truncated-octet-payload."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-octet-string, pus-octet-string-parameter-type, octet-string-count-field-width, fixed-length-octet-field, variable-length-octet-field, opaque-payload-handling, truncated-octet-payload]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Octet-String Parameter Type (space-systems/ecss/e7041-octet-string)

Use when the task is the octet-string parameter type of
ECSS-E-ST-70-41C clause 7.3.8 -- the six normative items covering how
the length is fixed or announced, why the field needs no padding, and
what "opaque" obliges the ground segment to refrain from doing.

## Domain quick reference

- The payload is opaque. The parameter type imposes no character set,
  no byte order and no numeric reading, so the only correct handling
  is to move it, store it and hand it back exactly as it arrived. A
  memory dump, a firmware image and an instrument blob all travel
  this way.
- The field is inherently octet aligned, which is what separates it
  from a bit-string. There is no pad, no partial octet and no
  boundary arithmetic anywhere in it; the length in octets is the
  whole of the geometry.
- The length arrives one of two ways and only one travels with the
  data. A fixed field takes its octet count from the parameter's
  format code, which both ends already hold; a variable field carries
  a count ahead of the octets, and the count field has its own width.
- A fixed field is exactly its declared count. Padding a short
  payload out adds octets the sender never set, and truncating a long
  one drops octets the sender did set. Both produce a well-formed
  field carrying the wrong content, so both are refused rather than
  repaired.
- A variable field is bounded by its count field, not by the packet.
  A count of n bits announces at most two-to-the-n minus one octets,
  so a payload that outgrows the count cannot be carried however much
  room the packet has left.
- The count is a claim, not a guarantee. A count announcing more
  octets than actually follow means the payload is truncated, and the
  short read that "works" is the worst outcome: it delivers a partial
  image that checksums as a complete one somewhere downstream.
- A zero-length payload is legitimate for a variable field and
  meaningless for a fixed one. The variable case sends a count of
  zero and no payload octet; the fixed case has a declared count an
  empty payload cannot satisfy.
- Comparison is exact. Nothing is trimmed, case folded or normalised
  before two payloads are compared, so a trailing zero octet is a
  difference rather than whitespace.

## Workflow

1. Validate the payload as whole octets, refusing text outright. A
   string implies an encoding the parameter type never named, and
   accepting one means guessing it.
2. Read the format code to decide which length regime applies:
   variable with a count field, or fixed at the declared octet count.
3. For a fixed field, compare the payload length with the declared
   count and refuse both the short and the long case by name, so the
   report says whether octets would be invented or dropped.
4. For a variable field, validate the count field width, check it is
   itself a whole number of octets, and refuse a payload longer than
   it can announce, naming the ceiling.
5. Encode a variable field by writing the count big endian ahead of
   the untouched payload.
6. Decode by reading the count, then checking that at least that many
   octets follow. Refuse a short buffer rather than returning what
   arrived, and report the octets consumed and any that remain so the
   caller can carry on through the rest of the data field.
7. Record the payload as opaque in the result. That line is what
   stops a later tool deciding the blob is a string and normalising
   it on the way through.

## Pitfalls

- Decoding the payload as text on arrival. A run of octets that
  happens to be printable is not a string, and any round trip through
  a character set silently rewrites the bytes that are not.
- Returning a short payload when the count announces more. The
  partial content then travels on with a plausible length, and the
  truncation is discovered only when the image fails to load on
  board.
- Padding a short payload into a fixed field. The invented octets are
  usually zeros, which in a memory dump or a table upload are
  perfectly legal values and therefore invisible.
- Sizing the count field from today's largest payload. The count
  width is part of the packet layout and cannot be widened later
  without a format change, so a payload that grows past the ceiling
  stops being transmissible.
- Treating the octet-string like a bit-string and reaching for pad
  arithmetic. There is no pad here; a routine that adds one shifts
  the whole payload and every later field in the data field with it.

## Behavior contract (gate 3)

The payload validation and text refusal, fixed-count enforcement in
both directions, count-field ceiling and alignment, big-endian count
encode, truncation-detecting decode with consumed and trailing
counts, exact payload comparison and field assessment are exercised
by the gate 3 contract test: scripts/test_e7041_octet_string.py
against scripts/e7041_octet_string_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e7041_octet_string.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
