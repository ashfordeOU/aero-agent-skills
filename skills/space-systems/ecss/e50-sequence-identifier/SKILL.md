---
name: e50-sequence-identifier
description: "Size the sequence identifier of a space data transfer protocol under ECSS-E-ST-50C clause 5.6.13.3, which asks that each transferred data unit carry an identifier the receiver can use to tell loss, duplication and reordering apart. Compute the identifier space a field width gives, the largest outstanding window that space keeps unambiguous under go-back-N or selective repeat, the field width a required window actually needs, and how long the mission runs before the space wraps. Replay a received identifier trace and name the gaps, repeats and reorderings it contains. Use when sizing a sequence number field or reviewing a retransmission window on a space link. Trigger: ecss, e-st-50-communications, space-link-sequence-identifier, sequence-identifier-field-width, sequence-number-wraparound-ambiguity, sliding-window-sequence-space, selective-repeat-sequence-modulus, out-of-order-data-unit-detection."
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
    clause: 5.6.13.3
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-sequence-identifier, space-link-sequence-identifier, sequence-identifier-field-width, sequence-number-wraparound-ambiguity, sliding-window-sequence-space, selective-repeat-sequence-modulus, out-of-order-data-unit-detection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Sequence Identifier (space-systems/ecss/e50-sequence-identifier)

Use when a space data transfer protocol has to distinguish one data unit from
the next, per ECSS-E-ST-50C clause 5.6.13.3 — how wide the identifier field
has to be for the window the link keeps outstanding, and what a received
identifier trace says about loss, duplication and reordering.

## Domain quick reference

- The identifier exists so the receiver can name what is missing. Without
  one a gap, a repeat and a swapped pair all look the same on arrival, and
  every recovery decision after that is a guess.
- A field of n bits gives exactly two-to-the-n identifiers, and that count
  is an integer, not an approximation. Deriving it through a logarithm
  invites a rounding answer to a counting question.
- The unambiguous window is smaller than the identifier space, and by how
  much depends on the retransmission scheme. Go-back-N can hold one less
  than the modulus outstanding; selective repeat can hold only half of it,
  because the receiver has to tell a retransmission of an old unit from a
  fresh unit that landed on the same identifier.
- Wrap is a time, not just a count. The identifier space divided by the
  unit rate says how long the link runs before an identifier is reused,
  and that time has to stay clear of the longest delivery the protocol
  will still accept.
- The window the link needs is set by the bandwidth-delay product, so the
  identifier width follows the data rate and the round trip. A window
  chosen for a near-Earth pass is not the window a deep-space link needs.
- A trace replay is the cheap acceptance check. Walking the received
  identifiers once, modulo the space, separates the gaps from the repeats
  from the reorderings and turns an argument into a list.

## Workflow

1. Confirm that every formatted data unit the link carries holds a
   sequence identifier giving its place in the stream, which is what lets
   a receiver separate a repeated unit from an omitted one. Then state
   the link as the identifier field width, the retransmission scheme, the
   outstanding window the design wants, the unit size and the data rate.
2. Compute the identifier space from the width with integer arithmetic,
   and the unambiguous window the scheme allows on that space.
3. Compare the wanted window against the unambiguous window. Where it does
   not fit, report the field width that does, found by widening one bit at
   a time rather than by inverting a logarithm.
4. Derive the window the bandwidth-delay product actually asks for, and
   say when the design window is below it — a window too small to fill the
   round trip throttles the link whether or not the identifier fits.
5. Compute the wrap time and compare it with the longest delivery latency
   the protocol still accepts. An identifier reused inside that latency is
   ambiguous even when the window is legal.
6. Replay any received identifier trace against the space and report the
   missing, repeated and out-of-order units by identifier.
7. Report the verdict with both numbers a designer can act on: the width
   that makes the wanted window safe, and the window the present width
   can carry.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.13.3a | 1 |

## Pitfalls

- Sizing the window at the full modulus. One identifier has to stay spare
  under go-back-N, and half the space has to stay spare under selective
  repeat, or a retransmission is indistinguishable from a new unit.
- Deriving the field width from a base-two logarithm. The result is a
  float on a counting problem and can land a bit low at an exact power of
  two; widening from one bit upwards answers it exactly.
- Checking only the window and not the wrap time. A legal window on a fast
  link can still reuse an identifier while a delayed copy of the earlier
  unit is in flight.
- Reading an out-of-order arrival as a loss. A trace replay that does not
  look ahead in the window reports units as missing that arrive a moment
  later, and the retransmissions it triggers make the congestion worse.
- Fixing an overlarge window by shrinking it below the bandwidth-delay
  product. That makes the identifier legal and the link slow; the field
  width is the part that should move.

## Behavior contract (gate 3)

Field width and window validation, the identifier space, the go-back-N and
selective-repeat unambiguous windows, the required width search, the
bandwidth-delay window, the wrap time against the accepted latency and the
identifier trace replay are exercised by the gate 3 contract test:
scripts/test_e50_sequence_identifier.py against
scripts/e50_sequence_identifier_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_sequence_identifier.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
