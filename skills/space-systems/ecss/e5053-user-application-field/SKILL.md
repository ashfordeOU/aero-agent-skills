---
name: e5053-user-application-field
description: "Allocate and resolve the user application octet of a packet transfer protocol data unit. Use when an ECSS-E-ST-50-53C clause 5.3.5 node has several users sharing one logical address: fix the octet offset from the path length, read the identifier a received unit carries, hand the packet to the application registered on it and drop a unit whose identifier nothing claims. On the build side, register applications into the node table, refuse an identifier already held and an application registered twice, take the lowest free identifier or honour a free preference, and report how much of the one-octet space is committed. Trigger: ecss, e-st-50-53c, spacewire-user-application-field, user-application-identifier-allocation, user-application-table-collision, user-application-demultiplexing, user-application-field-offset."
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
  tags: [ecss, e-st-50-53-packet-transfer-scope, e5053-user-application-field, spacewire-user-application-field, user-application-identifier-allocation, user-application-table-collision, user-application-demultiplexing, user-application-field-offset, user-application-space-audit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Transfer — User Application Field (space-systems/ecss/e5053-user-application-field)

Use when the task is the user application octet of ECSS-E-ST-50-53C
clause 5.3.5 -- the field that gets a packet from a destination node to
the right user of the protocol inside it.

## Domain quick reference

- The target logical address delivers the unit to a node. It does not
  say which user of the protocol inside that node the packet is for, and
  the user application octet is the only field that does.
- That makes one logical address enough for several users. Without the
  field, every application behind an address would need its own address,
  and the address space is the scarcer of the two.
- The identifier space is one octet and it is administered per node, not
  per network. Two nodes may use the same identifier for different
  applications without any conflict at all.
- A collision behind one address is undetectable at run time. Both
  applications receive each other's packets, neither sees an error, and
  nothing in the unit distinguishes the two, so the collision has to be
  refused at registration.
- Registering one application on two identifiers is the mirror defect.
  It splits the application's packet stream across two demultiplex
  paths, and only one of them usually gets tested.
- An identifier no application claims is dropped, not handed to a
  neighbour. Delivering to the nearest registered user turns a
  configuration error into corrupt application data.
- Identifier zero is an identifier like any other. Treating it as absent
  or unset loses whichever application was allocated it.

## Workflow

1. Fix the user application octet offset from the number of path-address
   bytes, refusing a negative or non-integer path length.
2. On the build side, register each application into the node's table:
   refuse an identifier already held, and refuse an application that is
   already registered on another identifier.
3. Allocate a new identifier by taking the lowest free value, or honour
   a stated preference where it is free and refuse it where it is not.
4. Report how much of the one-octet space is committed and which value
   comes next, so a node approaching exhaustion is visible before it
   runs out.
5. On reception, check the unit is long enough, read the octet at the
   offset, and look it up in the node's table.
6. Deliver to the registered application, or drop the unit and record
   that the identifier named nothing behind this address.

## Pitfalls

- Giving two applications behind one address the same identifier. There
  is no run-time symptom: each simply receives the other's packets, so
  the check belongs at registration and nowhere else.
- Treating identifier zero as unallocated. It is a valid identifier, and
  a table that skips it loses every packet for the application holding
  it.
- Delivering an unregistered identifier to the nearest registered user.
  It converts a configuration error into application data that looks
  legitimate and is not.
- Allocating identifiers per network instead of per node. The space is
  administered behind each address, so network-wide allocation exhausts
  one octet far sooner than it needs to.
- Reading the octet at a fixed offset. Path-address bytes move it, so a
  hard-coded position reads the reserved octet or the first packet byte
  on every path-routed unit.

## Behavior contract (gate 3)

The offset computation, table registration with both collision refusals,
identifier allocation, space audit and receive-side resolution are
exercised by the gate 3 contract test:
scripts/test_e5053_user_application_field.py against
scripts/e5053_user_application_field_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e5053_user_application_field.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
