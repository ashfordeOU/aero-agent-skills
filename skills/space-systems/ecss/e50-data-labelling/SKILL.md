---
name: e50-data-labelling
description: "Validate the label a space communication system puts on the data it carries, per ECSS-E-ST-50C clause 5.8.2, which asks that data be labelled well enough for a receiver to recover its identity from the unit alone. Compare the declared fields against source, destination, data type, sequence and generation time; size each identifier field in whole bits against the things it has to name; find whether the sequence counter wraps inside the window where two units must stay distinguishable; and price the label against the payload. Use when sizing a header or reviewing a data unit format. Trigger: ecss, e-st-50c-clause-5-8-2, space-data-unit-labelling, label-field-width-sizing, sequence-counter-wrap-ambiguity, label-overhead-fraction, source-and-destination-identifier-capacity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.8.2
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50c-clause-5-8-2, e50-data-labelling, space-data-unit-labelling, label-field-width-sizing, sequence-counter-wrap-ambiguity, label-overhead-fraction, source-and-destination-identifier-capacity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Data Labelling (space-systems/ecss/e50-data-labelling)

Use when the data a communication system carries has to be labelled, per
ECSS-E-ST-50C clause 5.8.2 — whether the label a receiver actually gets is
enough to say where a unit came from, where it is going, what it is, when it
was made and which one it is.

## Domain quick reference

- A label is judged by what a receiver can recover without being told.
  Anything the ground has to look up in a configuration file is not in
  the label, however well documented it is elsewhere.
- Five things have to be readable off the unit: source, destination,
  data type, sequence position and generation time. Each answers a
  question the others cannot, and a label missing one leaves a
  question the receiver has to guess at.
- The ground network owes its own version of that test, over every
  item of data it takes from the spacecraft: a reader of one item has
  to be able to say which parameter it holds, when the value was
  sampled on board and when it arrived on the ground, and no two of
  those items may end up wearing the same label.
- Field width is arithmetic, not judgement. Naming N distinct things
  takes the bit count that addresses N, and a field one bit short does
  not carry most of them — it carries half, and aliases the rest onto
  each other silently.
- Compute those widths with integer bit arithmetic. A count sitting
  exactly on a power of two is both the case a floating-point logarithm
  rounds wrong and the case a designer is most likely to have picked,
  so the two failure modes coincide precisely where it hurts.
- A sequence counter is only useful while it has not wrapped. The
  design question is not how wide the counter is but whether it repeats
  inside the window over which two units still have to be told apart —
  a retransmission window, a store-and-forward gap, a ground retention
  period.
- The label is paid for out of the payload, every unit, forever. The
  overhead fraction is the label over the whole unit, and the cheapest
  way to move it is usually a larger data unit rather than a smaller
  label.

## Workflow

1. Take the declared label as named fields with widths in whole bits.
   Reject a zero-width field, a duplicate name and a non-integer width
   rather than coercing them.
2. Compare the field names against the required set
   case-insensitively; report present, missing and unrecognised
   separately, because an unrecognised name is usually a required field
   under a house name. For data the ground has acquired, run the same
   comparison against what one item has to yield by itself — the
   parameter it holds, the time that value was sampled on board, the
   time it reached the ground — and confirm that no two acquired items
   can carry identical labels.
3. Size each identifier field: the bits needed to address the declared
   number of distinct sources and destinations, against the bits
   declared. Report how many things the declared field can actually
   name.
4. Compute the sequence wrap period from the counter width and the unit
   rate, and compare it with the window over which units must stay
   distinguishable. Report the narrowest counter that closes the gap.
5. Compute the label overhead as a share of the whole data unit and
   compare it with the allowance under a relative tolerance, so a
   design landing exactly on the allowance passes everywhere.
6. Report the effective payload rate the link delivers after the label,
   which is the number a data budget actually needs.
7. Grade sufficient only when coverage, both identifier widths, the
   sequence window and the overhead all hold, and give each shortfall a
   number: the width needed, or the payload size that fits.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.8.2a | 2 |

## Pitfalls

- Counting fields instead of reading them. A label with five fields
  that does not include a generation time is still missing a generation
  time, and only a set comparison catches it.
- Sizing an identifier from today's node count. Formations grow and
  data types multiply; a field sized to the exact current count aliases
  the first addition onto an existing address.
- Using a floating-point logarithm for the bit count. It rounds the
  power-of-two case the wrong way on some hosts, which is the one case
  a designer is most likely to have chosen deliberately.
- Treating counter width as the requirement. Width only matters through
  the wrap period; a wide counter on a fast source can still repeat
  inside the window, and a narrow one on a slow source may never.
- Quoting link capacity as the data rate. Every unit pays its label, so
  the delivered payload rate is lower, and a budget built on capacity
  is short by exactly the overhead fraction.
- Shrinking the label to meet an overhead allowance. Dropping a field
  or narrowing an identifier buys percentage points by removing the
  thing the label existed for; a larger data unit costs nothing the
  receiver needs.

## Behavior contract (gate 3)

Label validation including duplicate and zero-width fields, required
field coverage with unrecognised names, integer identifier sizing across
the power-of-two boundary, the sequence wrap period and the narrowest
counter that covers the window, the overhead fraction at its exact
allowance and the delivered payload rate are exercised by the gate 3
contract test:
scripts/test_e50_data_labelling.py against
scripts/e50_data_labelling_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_data_labelling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
