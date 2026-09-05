---
name: command-data-handling
description: "Use when the task is command validation, telemetry packetization, CCSDS framing, onboard data storage sizing, downlink budgeting, spacecraft data bus selection, or C&DH redundancy. Design and check spacecraft command and data handling (C&DH): validate telecommands against opcode, length, and CRC-16 checksum; packetize telemetry into CCSDS-style frames with sequence counts and error detection; size onboard storage from per-orbit data volume; and budget downlink time and rate from stored data volume and link capacity. Computes CRC-16 checksums, byte-exact CCSDS packets, storage sizes, and downlink verdicts with deterministic functions. Trigger: command data handling, telemetry, telecommand, CCSDS, packetization, downlink, CRC-16, onboard storage, data bus, SpaceWire, MIL-STD-1553."
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
  subdomain: subsystems
  tags: [command-data-handling, telemetry, telecommand, ccsds, packetization, downlink, crc-16, onboard, storage, payload, data, bus, spacewire, mil-std-1553, redundancy, frame, orbit, data-bus, onboard-storage]
  version: 0.1.0
  author: Aero Agent Skills
---

# Spacecraft Command and Data Handling (space-systems/subsystems/command-data-handling)

Use when the task is spacecraft command and data handling: validating
telecommands, packetizing telemetry into CCSDS-style frames, sizing
onboard storage from collected data volume, budgeting the downlink
against a contact window, or checking C&DH redundancy.

Units convention (stated once): data volume in bits (downlink
functions) or bytes (onboard storage), rates in bits per second, time
in seconds, frames are whole units. Margin fractions are dimensionless
(e.g. 0.1 = 10%).

## Domain quick reference

- C&DH is the subsystem that collects payload and housekeeping
  telemetry, formats it into packets, stores it onboard, and relays
  it to the ground; it also receives, validates, and distributes
  uplinked telecommands to the other subsystems.
- Telemetry packetization: a CCSDS-style space packet carries a 6-byte
  primary header (version, packet type, APID, sequence flags, sequence
  count, packet data length) plus data and a CRC-16 trailer. The
  length field stores len(data) - 1, so a 2-byte payload reads 1.
- Error detection: CRC-16-CCITT (poly 0x1021, init 0xFFFF) over
  header + data detects any single-bit corruption and most burst
  errors; a corrupted packet must be dropped or retransmitted, never
  executed.
- Command validation: each telecommand is checked for structural
  length, CRC-16 integrity, expected opcode, and addressed APID before
  execution; a rejected command is discarded and logged.
- Onboard storage sizing: storage = per-orbit data volume x orbits,
  plus a margin (typically 10-30%) for retransmissions, housekeeping
  growth, and file-system overhead; round up to whole bytes.
- Downlink budgeting: downlink time = data volume (bits) / link rate
  (bps); the stored volume must clear inside the contact window, or
  the required rate is volume / window. Storage growth over N orbits
  must fit the mass memory until the next downlink opportunity.
- Redundancy: dual-string C&DH keeps the function available while at
  least one string is healthy; string loss degrades margin, not
  availability, until the second string fails.

## Workflow

1. Validate the incoming telecommand: check structure and length
   field with validate_command_packet, then the CRC-16, then the
   expected opcode and APID; execute only on (True, "ok").
2. Packetize telemetry with telemetry_packet: choose the APID per
   source, increment the 14-bit sequence count per packet (wrap at
   16383), and append the CRC-16 trailer.
3. Parse and verify on the ground side with parse_telemetry_packet;
   a CRC mismatch means the packet is corrupted and must be dropped.
4. Size onboard storage with storage_size_bytes from the per-orbit
   data volume, the number of orbits between downlinks, and the
   sizing margin.
5. Budget the downlink: downlink_time_s or data_rate_for_window
   against the contact window; close with downlink_fits_window.
6. Size the link framing with frame_count and confirm the redundancy
   arrangement with redundancy_ok.

## Pitfalls

- Executing a command on CRC failure: the checksum is the last line
  of defense; a corrupted command must never reach the subsystem.
- Storing len(data) instead of len(data) - 1 in the packet length
  field, or parsing it off by one; the CCSDS field is payload minus
  one, and the two-byte field is big endian.
- Sizing storage without a margin: retransmissions and file-system
  overhead turn a "full" memory into an overwritten one.
- Budgeting the downlink with bytes instead of bits, or mixing
  megabits with megabytes.
- Using float ceil on margin arithmetic (3000 x 1.1 can round up to
  3301); use integer basis-point math as storage_size_bytes does.
- Forgetting the sequence count is 14 bits: it wraps at 16383, not
  65535.
- Treating a single healthy string as full redundancy: dual-string
  means two independent strings, not one with spares.

## Behavior contract (gate 3)

The CRC, packetization, command validation, storage sizing, downlink
budget, framing, and redundancy logic is exercised by the gate 3
contract test: scripts/test_command_data_handling.py against
scripts/command_data_handling_logic.py (stdlib unittest, offline).
Run from the repo root:
python3 skills/space-systems/subsystems/command-data-handling/scripts/test_command_data_handling.py

## Compliance

- ECSS standards (E-ST-50 series for space data links and
  communication) are freely downloadable from https://ecss.nl/standards/
  and copyright ESA; cite the source and paraphrase, per
  standards-map.yaml and brief 06. This leaf cites ECSS as reference
  only; the logic here is generic C&DH arithmetic (CRC, packet layout,
  data rates), not ECSS text.
- compliance: STANDARDS-REF, gated: false.
