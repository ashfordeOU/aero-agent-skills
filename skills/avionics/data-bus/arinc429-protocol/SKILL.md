---
name: arinc429-protocol
description: "Encode and decode ARINC 429 digital information transfer words for avionics data buses: build the 32-bit word from the octal label, SDI, 19-bit data field, SSM, and odd parity bit, split a received word back into its fields, and convert BNR and BCD parameters to and from engineering units at the word rate of 12.5 or 100 kbps. Use when checking a bus monitor decode, writing a test stimulus for an LRU interface, or explaining the one-transmitter up-to-20-receivers twisted shielded pair topology. Trigger: ARINC 429, data word, octal label, SDI, SSM, parity, BNR, BCD, 100 kbps, 12.5 kbps, avionics data bus."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arinc-429
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: data-bus
  tags: [arinc-429, data-bus, word-format, octal-label, sdi, ssm, odd-parity, bnr, bcd, 100-kbps, 12.5-kbps, twisted-shielded-pair]
  version: 0.1.0
  author: AeroSkills
---

# ARINC 429 Data Bus Protocol (avionics/data-bus/arinc429-protocol)

Use when the task is the ARINC 429 digital information transfer standard
(Mark 33 DITS) for civil avionics: the 32-bit word format and bit
numbering, octal label addressing and common label tables, word
transmission at 12.5 or 100 kbps over a twisted shielded pair, the
one-transmitter up-to-20-receivers topology, and encoding and decoding
of typical parameters in BNR (binary) and BCD formats. The module is
data-driven: you supply the label table and coding choices from the
applicable equipment definition, and the functions validate bounds,
pack and unpack words, compute odd parity, and convert data fields to
and from engineering units.

## Domain quick reference

- ARINC 429 transfers 32-bit digital words point-to-point over a twisted
  shielded pair at 12.5 or 100 kbps, with exactly one transmitter driving
  up to 20 receivers on a bus.
- Word layout, ARINC bit numbering (bit 1 is the least significant bit
  and is transmitted first; in the integer, bit 0 = ARINC bit 1):
  label bits 1-8 (octal), SDI bits 9-10, data bits 11-29 (19 bits),
  SSM bits 30-31, parity bit 32.
- Octal labels: label 010 octal = 8 decimal; the label field spans 000
  to 377 octal. Label-to-parameter assignments come from ARINC 429
  appendix tables and the equipment definition; confirm the applicable
  table before mapping.
- Worked encode anchor: label 010, SDI 1, data field 1234, SSM 3
  (normal operation) -> word 0x60134908 (1611876616 decimal) with odd
  parity.
- Odd parity: the full 32-bit word always has an odd number of 1 bits.
  The anchor payload (bits 1-31) has 9 set bits, so parity bit 32 = 0
  and the word stays odd.
- BNR: two's complement, with the data MSB (bit 29) as the sign bit and
  the least significant bit weight equal to the scale factor. Worked:
  123.4 at scale 0.1 -> field 1234; -12.3 at scale 0.1 -> field 524165
  (two's complement 19-bit), decoding back to -12.3.
- BCD: four decimal digits in the low 16 data bits, plus an optional
  fifth digit (0-7) in the top 3 bits. Worked: 1234 -> field 4660.
- SSM conventions (typical): 11 normal operation, 10 functional test,
  01 no computed data, 00 failure warning. Interpretation can differ
  between BNR and BCD words; confirm per label.
- Word timing: 32 data bit-times plus a 4-bit gap between words ->
  about 2778 words per second at 100 kbps, about 347 words per second
  at 12.5 kbps.
- The exact word-format tables, label tables, and equipment
  identification tables are revision-specific standard data; confirm
  them against the current revision before freezing an interface
  design.

## Workflow

1. Identify the bus direction, the word rate (12.5 or 100 kbps), and
   the parameter to transfer; look up its octal label and data format
   (BNR or BCD) in the applicable equipment table.
2. Convert the engineering value to the raw 19-bit data field with
   bnr_encode (scale factor for the LSB weight, two's complement) or
   bcd_encode (decimal digits).
3. Pack the word with build_word(label, sdi, data, ssm); the odd
   parity bit is computed and placed in bit 32 automatically.
4. On reception, split the word with decode_word and check parity_ok
   before trusting the payload; a parity failure flags a corrupted or
   marginal transmission.
5. Convert the data field back to an engineering value with
   bnr_decode or bcd_decode, and interpret the SSM (normal operation
   vs failure warning, no computed data, or functional test).
6. Verify the transmit budget: word rate at the chosen speed, and the
   receiver count (up to 20) against the single transmitter.
7. Report the encoded or decoded fields, the parity verdict, and any
   label table entries that still need confirmation against the
   current revision.

## Pitfalls

- Confusing the ARINC 429 data bus with the aircraft electrical bus in
  do160/power-input: power-input is section 16 equipment power
  characteristics (steady-state voltages, sag/surge transients); 429 is
  the digital data transfer protocol. A voltage test does not touch
  word format, and a label decode does not touch voltage limits.
- Confusing this leaf with do160/radio-frequency-susceptibility: RS103
  radiated and CS114 conducted immunity tests concern RF interference
  on equipment and wiring; this leaf concerns how digital words are
  formatted, coded, and transferred, not immunity levels.
- Confusing this leaf with flight-management/flight-planning: FMS route
  tasks (waypoints, great-circle track, leg geometry) operate on the
  navigation content that may ride an ARINC 429 bus; 429 is the
  transfer protocol, not the navigation math.
- Confusing this leaf with far-cs25/special-conditions: special
  conditions address novel design features for the certification basis;
  429 is a wiring and interface standard, not a certification topic.
- Bit-order mistakes: ARINC bit 1 is the LSB and is transmitted first,
  so the label sits in the LOW byte of the integer, not the high byte.
- Octal label traps: label 010 octal is 8, not 10 decimal; passing 10
  decimal encodes label 012, a different word.
- Parity is odd, not even: the 32-bit word must contain an odd number
  of 1 bits; recompute the parity bit whenever the payload changes.
- Mixing BNR and BCD: BNR is signed two's complement scaled by the LSB
  weight, BCD is packed decimal digits; the SSM meaning can also
  differ between the two formats.
- Forgetting the one-transmitter rule: two transmitters on one bus is a
  wiring violation; up to 20 receivers are permitted on the pair.
- Treating the label table as fixed: label-to-parameter assignments are
  standard data that vary by equipment definition; confirm every label
  against the applicable table before freezing the interface.

## Behavior contract (gate 3)

The logic is exercised by the gate 3 contract test:
scripts/test_arinc429_logic.py against scripts/arinc429_logic.py (stdlib
unittest, offline). Run: python3 scripts/test_arinc429_logic.py

## Compliance

- Standards referenced, not reproduced: ARINC 429 text is proprietary
  (ARINC/SAE ITC); summary-only per standards-map.yaml.
- The module implements the bit layout, odd parity, and BNR/BCD coding
  helpers from common knowledge; no standard table is embedded in the
  code or this page.
- compliance: STANDARDS-REF, gated: false.
