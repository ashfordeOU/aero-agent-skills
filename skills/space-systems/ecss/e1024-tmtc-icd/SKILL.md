---
name: e1024-tmtc-icd
description: "Use when produce TM/TC interface control documents (ICDs) for a spacecraft following ECSS-E-ST-10-24C §5.9: register CCSDS application process identifiers (APIDs), define PUS-based telemetry and telecommand packet structures with service and subservice assignments, validate packet field ranges against CCSDS and PUS-C conventions, check APID registration completeness, and verify the ICD includes at least one TM downlink and one TC uplink definition. Trigger: ecss, e-st-10-system-scope, tmtc-icd, telemetry, telecommand, ccsds, pus, apid, packet-definition, icd."
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
  tags: [ecss, e-st-10-system-scope, tmtc-icd, telemetry, telecommand, ccsds, pus, apid]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS E-ST-10-24C §5.9 — TM/TC Interface Control Documents (space-systems/ecss/e1024-tmtc-icd)

Use when the task is to produce the telemetry (TM) and telecommand (TC) interface
control documents for a spacecraft project under ECSS-E-ST-10-24C §5.9. The skill
covers CCSDS Space Packet Protocol-based packet structure definition, PUS-C
service/subservice assignment, APID registration, and ICD completeness verification.

## Domain quick reference

- A TM/TC ICD documents every packet exchanged between the spacecraft's on-board
  application processes and the ground segment. Each application process is identified
  by an Application Process Identifier (APID), an 11-bit field in the CCSDS primary
  header (CCSDS 133.0-B-2). Valid operational APIDs range from 0x000 to 0x7FE;
  0x7FF is reserved as the idle-packet APID and may not be assigned to an application.
- CCSDS primary header (6 bytes per packet): version number (3 bits, always 0),
  packet type (1 bit: 0 = TM, 1 = TC), secondary header flag (1 bit, set to 1 when a
  PUS secondary header is present), APID (11 bits), sequence flags (2 bits: 11 =
  standalone unsegmented packet), packet sequence count (14 bits), and packet data
  length (16 bits, equal to total data-field octets minus 1).
- PUS-C (ECSS-E-ST-70-41C) secondary header for TM adds: PUS version (4 bits, value 2
  for PUS-C), spacecraft time reference status (4 bits), service type (8 bits),
  service subtype (8 bits), message type counter (16 bits), destination ID (16 bits),
  and absolute time (variable). Minimum PUS-C TM secondary header size is 10 bytes.
- PUS-C secondary header for TC adds: PUS version (4 bits, value 2), acknowledgement
  flags (4 bits, one bit each for acceptance, start, progress, completion), service type
  (8 bits), service subtype (8 bits), and source ID (16 bits). Minimum size is 5 bytes.
- Each service/subservice pair must be drawn from either the PUS-C reserved range
  (services 1–23 as defined in ECSS-E-ST-70-41C) or a project-allocated range; values
  0 and 256+ are out of range for both fields.
- ICD completeness requires: every APID appearing in a packet definition must have a
  registered human-readable name; every registered APID must appear in at least one
  packet definition; the ICD must contain at least one TM and one TC packet definition.

## Workflow

1. Establish the APID allocation table: assign an APID in the range 0x000–0x7FE to
   each on-board application process. Record the APID value and a unique human-readable
   process name. Flag any APID outside the valid range or any duplicate assignment
   before proceeding.
2. For each TM packet to be produced by an application process, define a packet entry:
   APID, PUS service type, PUS subservice, a plain-language description, and the
   application data field size in bytes. Compute the CCSDS Packet Data Length field
   value (PUS-C secondary header size + application data size − 1). Reject a packet
   whose computed Packet Data Length value exceeds 65535 (CCSDS 16-bit field limit).
3. For each TC packet accepted by an application process, define a packet entry: APID,
   PUS service type, PUS subservice, a plain-language description, the acknowledgement
   flag byte (4-bit field, 0x0–0xF), and the parameter field size in bytes. Compute
   and validate the Packet Data Length field as for TM, using the 5-byte PUS-C TC
   secondary header baseline.
4. Validate all service and subservice values: both fields must be in the range 1–255.
   Cross-reference against PUS-C reserved services to detect conflicts or gaps.
5. Check APID registration completeness: every APID referenced in a TM or TC packet
   definition must be present in the APID allocation table, and every registered APID
   must have at least one packet definition. Flag mismatches as ICD findings.
6. Confirm the ICD contains at least one TM entry and at least one TC entry; an ICD
   missing either direction is incomplete per §5.9.
7. Aggregate all findings; the ICD is compliant only when the findings list is empty.

## Pitfalls

- Assigning APID 0x7FF to an application process — that value is reserved as the
  CCSDS idle-packet APID and must never appear in a TM/TC ICD application entry.
- Setting the PUS version nibble to 1 (PUS-A) in a project using PUS-C packets — the
  secondary header layout differs between versions, and a mismatch causes ground
  software to misparse every field that follows.
- Omitting the Packet Data Length validation and allowing a data field whose encoded
  length value would overflow the 16-bit CCSDS field — ground decoders will compute
  a wrong end-of-packet boundary and corrupt the subsequent packet in a multi-packet
  frame.
- Using service type 0 or subservice type 0 — both are out of range in PUS-C; a
  packet registered with either value will not match any PUS handler on board.
- Leaving an APID without a registered process name and reading the absence as "no
  packets yet" — in the ICD completeness check, an unregistered APID is a finding,
  not a placeholder.
- Treating the ICD as complete when only one direction (TM or TC) is populated — §5.9
  requires both uplink and downlink definitions to be present before the document is
  accepted as a deliverable.

## Behavior contract (gate 3)

APID validation, PUS service/subservice range checking, TM and TC packet definition
building, and ICD completeness logic are exercised by the gate 3 contract test:
scripts/test_e1024_tmtc_icd.py against scripts/e1024_tmtc_icd_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1024_tmtc_icd.py

## Compliance

- ECSS standards are freely downloadable from the ESA website; cite source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
