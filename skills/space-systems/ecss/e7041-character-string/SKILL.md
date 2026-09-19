---
name: e7041-character-string
description: "Validate, encode and decode the character-string parameters a packet definition declares, under ECSS-E-ST-70-41C clause 7.3.9. Use when a string field comes back truncated, padded or ambiguous on the ground: choosing between a fixed-length field and a counted variable-length one, sizing the count field so the declared maximum is actually representable, refusing a character outside the declared repertoire instead of substituting it, and catching a pad octet that lies inside the repertoire so a value ending in that character can no longer be told from padding. Trigger: ecss, e-st-70-41c, pus-character-string-parameter, fixed-versus-variable-length-string, string-count-field-width, character-repertoire-refusal, string-pad-octet-ambiguity, packet-string-field-sizing."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-character-string, pus-character-string-parameter, fixed-versus-variable-length-string, string-count-field-width, character-repertoire-refusal, string-pad-octet-ambiguity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Character-String Data Type (space-systems/ecss/e7041-character-string)

Use when the task is the character-string data type of ECSS-E-ST-70-41C
clause 7.3.9 — the seven normative items that fix how a human-readable
value is carried in a packet, and everything an implementation gets
wrong when it treats a string field as if it were a byte buffer.

## Domain quick reference

- A character-string parameter is a sequence of octets, one octet per
  character, drawn from a repertoire fixed in the mission definition.
  The repertoire is not carried in the packet, so a ground system that
  guesses it reads a different value from the one the spacecraft sent.
- Two forms exist and they are not interchangeable. A fixed-length
  field occupies the declared number of octets on every occurrence and
  a shorter value is padded to it. A variable-length field carries a
  leading count of the characters actually present, and the definition
  states the maximum separately.
- The count field has to reach the declared maximum. A count of n bits
  states at most 2^n - 1 characters; if that is below the declared
  maximum, the longest legal value cannot be expressed at all. It is a
  definition defect, visible at review time, not a run-time surprise.
- Padding is not part of the value. A fixed-length field is filled out
  to its declared length with a declared pad octet, and decoding strips
  the trailing run of that octet back off again.
- A pad octet drawn from the repertoire makes the round trip lossy. If
  spaces pad a printable field, a value that legitimately ends in a
  space decodes one character shorter, and nothing on the wire
  distinguishes the two cases. A pad outside the repertoire cannot
  collide with content.
- A character outside the repertoire is refused, not substituted. A
  substituted character is a silently wrong value; a refusal is a
  finding somebody acts on.
- The width a string costs a packet depends on the packing rule. A
  fixed-envelope layout reserves count plus maximum on every
  occurrence; a packed layout reserves count plus the actual length,
  and only then is the packet length variable.

## Workflow

1. Normalise the definition: kind, repertoire, and either the fixed
   length or the maximum with its count width. Refuse a padded
   variable-length definition — a counted field has nothing to pad to.
2. Check the count field against the declared maximum before anything
   else; a narrow count is the defect that survives every value test
   because the longest value is the one nobody sends.
3. Encode by mapping each character to its octet, refusing the first
   one outside the repertoire and naming its index, then padding a
   fixed field out to its length.
4. Decode by stripping the trailing pad run from a fixed field, or by
   taking exactly the counted characters from a variable one, and
   refuse a count that states more characters than are present.
5. Report whether the pad octet lies inside the repertoire; that single
   flag is what tells a reviewer the round trip can lose a character.
6. Size the field under the packing rule the packet layout actually
   uses, not under whichever rule makes the budget fit.
7. Assess the definition against representative values and report the
   findings together: refused samples, a padding-dominated field, a
   count field far wider than the maximum needs.

## Pitfalls

- Truncating a value that overruns the field. Truncation changes the
  value and leaves no trace on the wire; the encoder refuses instead.
- Padding a printable field with spaces. It reads naturally in a hex
  dump and quietly eats a trailing space on every decode.
- Sizing the count field from the values in hand rather than from the
  declared maximum. The definition is what the ground decodes against,
  and it outlives the sample set.
- Substituting an unsupported character. A question mark on the ground
  is indistinguishable from a question mark on board.
- Budgeting a variable-length field at its typical length. Unless the
  layout is genuinely packed, every occurrence costs count plus
  maximum, and the packet length was fixed at definition time.
- Decoding a fixed field with a count taken from somewhere else. Its
  length is the definition; a count belongs only to the variable form.

## Behavior contract (gate 3)

The repertoire lookup, count-field capacity check, definition
normalisation, encoding refusals, fixed and variable decoding,
pad-in-repertoire ambiguity flag, packing-rule field sizing and the
definition assessment are exercised by the gate 3 contract test:
scripts/test_e7041_character_string.py against
scripts/e7041_character_string_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_character_string.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
