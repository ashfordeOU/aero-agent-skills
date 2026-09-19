---
name: e7041-enumerated
description: "Derive the enumerated parameter encoding of ECSS-E-ST-70-41C clause 7.3.3, where a symbol travels as an unsigned binary code in a field whose width the format code fixes. Use when a report decodes to a state nobody declared, or a new mode has to be added to a live enumeration: sizing the field from the largest declared code by exact bit length, refusing a table that reaches past its width, counting the spare codes a future state could take, and reporting an undefined code as undefined rather than resolving it to a default symbol. Trigger: ecss, e-st-70-41-packet-utilisation-scope, pus-enumerated-parameter-type, enumerated-code-field-width, undefined-enumeration-code, enumeration-spare-code-headroom, symbol-to-code-mapping, enumeration-widening-decision."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-enumerated, pus-enumerated-parameter-type, enumerated-code-field-width, undefined-enumeration-code, enumeration-spare-code-headroom, symbol-to-code-mapping, enumeration-widening-decision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Enumerated Parameter Type (space-systems/ecss/e7041-enumerated)

Use when the task is the enumerated parameter type of ECSS-E-ST-70-41C
clause 7.3.3 -- the two normative items that say the declared symbol
set has to fit the coded field, and that a code outside the set is an
undefined value rather than a default one.

## Domain quick reference

- An enumerated parameter never carries its symbol. It carries an
  unsigned binary code standing for that symbol, and the width of the
  code field is fixed by the parameter's format code, not by the
  number of symbols that happen to be declared today.
- The width question is exact integer arithmetic: the field has to
  reach the largest declared code, so the narrowest usable width is
  the bit length of that code, never a rounded logarithm. Working it
  out in floating point is how an enumeration ends up one bit short at
  a power-of-two boundary.
- Capacity and occupancy are different numbers. A field of n bits
  carries two-to-the-n codes; the declared set may claim far fewer,
  and the codes it leaves unclaimed are the only room a later mode
  has. A set that exactly fills its field is valid today and blocks
  every future state.
- A sparse table is normal. Codes are frequently allocated with gaps
  so related states group together, so the sizing question turns on
  the largest code present, not on how many entries the table holds.
- The undefined case is the substance of the clause. A received code
  that is not in the declared set carries no symbol at all. Resolving
  it to the first entry, to the last, or to an "unknown" member of the
  set invents a spacecraft state that was never reported, and the
  invented state then propagates into limit checking and event logic.
- A code too wide for the field is a different fault from a code the
  table does not define. The first says the extraction was wrong; the
  second says the extraction was right and the on-board software is
  emitting a state the database has not been told about.

## Workflow

1. Validate the symbol table before anything else: integer codes, no
   negatives, non-blank names, and no name declared against two codes.
   A table that fails here cannot be sized or decoded meaningfully.
2. Validate the declared field width against the permitted range and
   compute its capacity, keeping the two separate from the count of
   declared symbols.
3. Compute the narrowest width that reaches the largest declared code
   and compare it with the declared width. Report a shortfall as an
   overflow and a surplus as declared slack; neither is silently
   corrected.
4. List the unclaimed codes. Report an exactly filled field as having
   no headroom, because that is the finding a database change request
   needs.
5. Encode by looking the symbol up in the declared set and refusing an
   undeclared name; refuse a declared symbol whose code sits outside
   the field rather than truncating it.
6. Decode by bounds-checking the code against the field first, then
   resolving it in the table. Return an undefined result with a
   finding when the table does not define it, and let the caller
   decide -- never substitute a symbol.

## Pitfalls

- Sizing the field from the number of symbols instead of the largest
  code. A four-entry table numbered 0, 1, 2 and 7 needs three bits,
  and the count says two; the table then loses its top entry.
- Rounding a logarithm to get the width. Bit widths are integers and
  the boundary cases are exactly the powers of two, which is where a
  floating-point log lands on either side depending on the platform.
  Use the bit length of the largest code and the question disappears.
- Defaulting an unrecognised code to a safe-looking symbol. It reads
  as defensive and is the opposite: downstream limit checks, event
  actions and operator displays then all agree on a state the
  spacecraft never reported.
- Treating an exactly filled field as having headroom. Every code is
  claimed, so the next mode cannot be added without widening the
  field, and widening it changes the layout of every packet the
  parameter appears in.
- Confusing a too-wide code with an undefined one. A code that does
  not fit the field means the extraction offset or width is wrong; a
  code that fits but is not in the table means the database is behind
  the on-board software. The repairs are unrelated.

## Behavior contract (gate 3)

The width validation, exact minimum-width computation, symbol-table
validation, encode refusal, undefined-code reporting, spare-code
listing and field assessment are exercised by the gate 3 contract
test: scripts/test_e7041_enumerated.py against
scripts/e7041_enumerated_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_enumerated.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
