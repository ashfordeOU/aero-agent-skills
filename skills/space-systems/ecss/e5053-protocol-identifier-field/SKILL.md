---
name: e5053-protocol-identifier-field
description: "Verify the protocol identifier octet of a packet transfer protocol data unit. Use when an ECSS-E-ST-50-53C clause 5.3.3 unit has to be demultiplexed at its destination: fix the identifier offset from the number of path-address bytes that preceded the target address, read the octet there, categorize it as the escape value, a registered protocol or an unclaimed value, compare it against the identifier this protocol is registered under, hand the remainder to the matching handler and drop a unit no handler claims. Refuses a unit too short to hold the field, a declared path byte holding a logical address and an identifier wider than one byte. Trigger: ecss, e-st-50-53c, spacewire-protocol-identifier-field, protocol-identifier-offset, protocol-handler-demultiplexing, extended-identifier-escape, unclaimed-protocol-identifier."
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
  tags: [ecss, e-st-50-53-packet-transfer-scope, e5053-protocol-identifier-field, spacewire-protocol-identifier-field, protocol-identifier-offset, protocol-handler-demultiplexing, extended-identifier-escape, unclaimed-protocol-identifier, protocol-identifier-registry]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Transfer — Protocol Identifier Field (space-systems/ecss/e5053-protocol-identifier-field)

Use when the task is the protocol identifier of ECSS-E-ST-50-53C clause
5.3.3 -- the octet that tells a receiving node which protocol the rest
of the unit belongs to, and where in the unit that octet is found.

## Domain quick reference

- The clause settles two separate things: the position of the field,
  which is the octet immediately after the target logical address, and
  its content, which is the identifier this transfer protocol is
  registered under.
- The position is not a constant. Path-address bytes precede the target
  address and shift everything after it, so the identifier offset is
  the path length plus one and a receiver that assumes a fixed offset
  mis-reads every path-routed unit.
- The low escape value does not name a protocol. It announces that a
  wider identifier follows, so a unit carrying it is not a packet
  transfer unit and cannot be graded as one.
- An identifier that names a different registered protocol is a
  well-formed unit for somebody else. It is not corrupt, and the
  correct disposition is to hand it to that protocol's handler, not to
  parse it as a packet transfer unit.
- An identifier no handler on this node claims is dropped. Parsing on
  regardless is how a foreign unit gets read against packet transfer
  field boundaries and produces a plausible, wrong packet.
- Conformance and routing are two verdicts, not one. A unit can be
  routed to a handler that exists and still fail the check that it
  carries the identifier expected on this interface.

## Workflow

1. Take the number of path-address bytes the unit was sent with and
   compute the identifier offset from it. Refuse a negative or
   non-integer path length rather than assuming none.
2. Check the unit is long enough to hold an octet at that offset, and
   that every declared path byte really sits in the path range -- a
   logical address among them means the offset cannot be trusted.
3. Read the identifier octet and categorize it: the escape value, a
   value the registry names, or a value nothing claims.
4. Compare it with the identifier expected on this interface and record
   which protocol a mismatching value actually names.
5. Demultiplex on the octet: deliver the remainder to the handler
   registered for it, drop an escape value before any handler, and drop
   an identifier no handler claims.
6. Report the two verdicts separately -- whether the identifier was the
   expected one, and where the unit was sent.

## Pitfalls

- Reading the identifier at a fixed offset. Every path byte moves it,
  so a hard-coded position works only on the directly connected case
  and silently mis-parses everything routed through a path.
- Treating the escape value as a protocol. It is a marker that a longer
  identifier follows, so grading it against the expected identifier
  reports a mismatch where the real finding is that the unit uses a
  different identifier width.
- Dropping a unit that names another registered protocol. It is valid
  traffic for a different handler on the same link, and discarding it
  turns a working multiplex into a silent loss.
- Parsing a unit whose identifier no handler claims. The packet field
  boundaries are protocol-specific, so the parse produces a structurally
  valid result that describes nothing that was sent.
- Collapsing conformance and routing into one answer. A unit can reach a
  handler and still be non-conformant for this interface, and reporting
  only the routing hides that.

## Behavior contract (gate 3)

The offset computation, identifier read, categorization, conformance
comparison and handler demultiplexing are exercised by the gate 3
contract test: scripts/test_e5053_protocol_identifier_field.py against
scripts/e5053_protocol_identifier_field_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e5053_protocol_identifier_field.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
