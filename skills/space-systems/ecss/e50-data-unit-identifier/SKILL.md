---
name: e50-data-unit-identifier
description: "Verify that every formatted data unit a space link carries holds an identifier naming its source, its destination or both, under ECSS-E-ST-50C clause 5.6.13.2, then size the counter field that carries that identifier so it still names one unit for as long as the design acts on it. Compute the modulus of the counter field, the period it takes to wrap, how many units are live inside the retention window, and the coverage of one against the other; separate a field that wraps inside the window from one that covers it with no margin; size the narrowest field that works by exact integer doubling; and read an observed run for gaps, wraps and repeats. Use when sizing or reviewing data unit counters. Trigger: ecss, e-st-50-communications, data-unit-identifier-field-width, data-unit-counter-wrap-ambiguity, data-unit-sequence-gap-detection, data-unit-retention-window-coverage."
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
    clause: 5.6.13.2
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-data-unit-identifier, data-unit-identifier-field-width, data-unit-counter-wrap-ambiguity, data-unit-sequence-gap-detection, data-unit-retention-window-coverage, data-unit-identifier-sizing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Data Unit Identifier (space-systems/ecss/e50-data-unit-identifier)

Use when the identifier carried by each data unit on a space link is being
sized or reviewed, per ECSS-E-ST-50C clause 5.6.13.2 — whether a formatted
unit carries an identifier at all and which endpoint it names, and then,
past what the clause asks, whether the counter carrying that identifier
still names one unit by the time anyone acts on it.

## Domain quick reference

- What the clause itself asks is short: a formatted data unit on the
  space link carries an identifier, and that identifier names its
  source, its destination, or both at once. Step 1 is where that is
  settled. Everything after it is this leaf's own discipline — a
  counter that wraps still carries an identifier and still satisfies
  the item, and can still leave a receiver acting on the wrong unit.
- Unambiguous has a duration. A counter in a fixed field names a unit
  uniquely only until it wraps, so the sizing question is never whether
  the field is wide enough but whether it is wide enough for the window
  the system still cares about that unit in.
- The window is set by what the design does with the identifier, not by
  the pass. Retransmission, reordering, gap filling and ground-side
  reconciliation all reach back in time, and the longest of them governs.
- Coverage is the number to report: the field modulus divided by the
  units live inside the window. Below one, two live units share an
  identifier. At exactly one, nothing may ever be late.
- A field that covers the window once has no room for the thing that
  will happen. A retransmission, a stretched contact or a slower ground
  turnaround all lengthen the window after the field was sized.
- Size the field by doubling an integer, not by taking a logarithm. A
  demand landing exactly on a power of two must not come out as one bit
  on one platform and the next bit up on another.
- An observed run says different things at once. A backwards step is a
  wrap, a repeated value is a duplicate, and a value the field could
  never have carried is a decoding fault. Reporting all three as missing
  units sends the investigation the wrong way.

## Workflow

1. Check first that every formatted data unit the space link carries
   holds an identifier at all, and which endpoint it names: its source,
   its destination, or both at once. An identifier that names
   neither leaves a receiver with nothing to act on. The name only has
   to hold inside the one spacecraft's domain; a wider, universally
   unique name may be built by reading the identifier together with
   others, the spacecraft identifier among them.
2. State the retention window before the field width. The window is a
   system property; the width is the answer to it.
3. Compute the field modulus from the width, and the wrap period from
   the modulus and the production rate.
4. Compute how many units are live inside the window, and take coverage
   as the modulus over that count.
5. Decide the three-way verdict with a relative tolerance, so a field
   sized exactly to its window is decided the same way everywhere.
6. Report the narrowest width that would cover the window with the
   margin asked for, found by doubling an integer capacity, so the
   recommendation is exact rather than a rounded logarithm.
7. When reading an observed run, reject any value outside the field
   first. It is a decoding fault and it would otherwise manufacture a
   long run of phantom gaps.
8. Separate wraps, gaps and duplicates in the report, and give the
   identifier expected next so a receiver's own bookkeeping can be
   checked against it.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.13.2a | 1 |

## Pitfalls

- Sizing the counter against the pass rather than the retention window.
  The window is usually longer, and the shortfall only shows when a
  retransmission arrives after the wrap.
- Reading a coverage of one as adequate. It means the newest unit takes
  the identifier of the oldest one still in play, with nothing late.
- Taking a logarithm to size the field. The result lands on either side
  of a power of two depending on the platform, so two machines recommend
  different widths for the same input.
- Counting a repeated identifier as a wrap. It inflates how many units
  the run is thought to cover and hides a genuine duplicate.
- Treating an out-of-field value as a lost unit. It is a decoding or
  framing fault, and reported as a gap it produces a list of missing
  units that were never sent.
- Deciding the wrap comparison with a bare strict inequality. A field
  sized exactly to its window can come out ambiguous on one platform and
  unambiguous on another.

## Behavior contract (gate 3)

Field width and rate validation, the modulus, the wrap period, live
units in the window, coverage, the three-way verdict with a relative
tolerance at the coverage bound, exact integer sizing of the narrowest
adequate field with an impossible demand raising, and the observed-run
analysis separating wraps, gaps, duplicates and out-of-field values are
exercised by the gate 3 contract test:
scripts/test_e50_data_unit_identifier.py against
scripts/e50_data_unit_identifier_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_data_unit_identifier.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
