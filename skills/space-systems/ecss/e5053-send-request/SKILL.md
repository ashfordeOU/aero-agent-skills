---
name: e5053-send-request
description: "Validate a send request handed to the SpaceWire CCSDS packet transfer entity under ECSS-E-ST-50-53C clause 5.5.2, against its three obligations at once: the destination resolves to a usable logical address or a path of output ports, the request carries exactly one complete CCSDS packet whose declared length matches the octets supplied, and the encoded transfer with its address, protocol identifier and reserved octet fits the transmit limit so an over-long request is refused rather than truncated on the link. Use when issuing or reviewing CCSDS send requests over SpaceWire. Trigger: ecss, e-st-50-53c, spacewire-send-request, spacewire-logical-address, spacewire-path-address, ccsds-transfer-encoding, max-transfer-unit-refusal, send-primitive-parameters."
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
  tags: [ecss, e-st-50-53-ccsds-packet-transfer, e5053-send-request, spacewire-send-request, spacewire-logical-address, spacewire-path-address, ccsds-transfer-encoding, send-primitive-parameters]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — Send Request (space-systems/ecss/e5053-send-request)

Use when the task is the send request a user issues to the SpaceWire
CCSDS packet transfer entity, per ECSS-E-ST-50-53C clause 5.5.2 —
deciding whether the request is well enough formed for the entity to
build a transfer from it, and what to do when it is not.

## Domain quick reference

- The request is the whole interface. It names where the packet goes
  and hands over the packet; everything the entity puts on the link —
  the address octets, the protocol identifier, the reserved octet — is
  derived from it, so a defect in the request becomes a defect on the
  link with nothing in between to catch it.
- A destination is one of two shapes. A logical address is a single
  octet in the range assigned to destination nodes, with the values
  below that range and the top value reserved. A path address is a
  sequence of output port numbers, optionally ending in a logical
  address for the last hop, and routers consume one octet per hop.
- The two shapes are distinguishable from the octet values, which is
  what makes an automated check possible: an octet in the port range is
  a hop, an octet in the node range is a destination, and anything else
  belongs to neither and is a request defect.
- The packet parameter carries one complete CCSDS packet. Because the
  space packet declares its own length in its primary header, "complete"
  is checkable at the interface without any agreement between sender
  and receiver: declared length against octets supplied, both ways.
- The transmit limit belongs to the local entity, not the standard. A
  request whose encoded form exceeds it is refused at the interface.
  The one thing that must not happen is silent truncation, which
  produces a transfer the receiver cannot tell from a link fault.

## Workflow

1. Categorize the destination into a logical address or a path, and
   produce the leading address octets from it. Reject reserved values
   rather than passing them through as routable addresses.
2. Validate the packet parameter: at least a primary header, then the
   declared total length derived from the packet data length field
   compared against the octets supplied, rejecting both a shortfall and
   a surplus.
3. Encode the transfer body in order: address octets, protocol
   identifier, reserved octet, then the CCSDS packet unchanged. The
   packet is carried, never rewritten.
4. Measure the encoded length and compare it with the configured
   transmit limit. Equality with the limit is acceptance; exceeding it
   is refusal, with the reason named as a limit and not as a bad packet.
5. Collect the three obligations as separate findings rather than
   stopping at the first, so one review round returns everything wrong
   with the request.
6. Accept the request only when all three obligations hold, and report
   the encoded length and destination kind with the verdict.

## Pitfalls

- Passing a reserved low address through because it is a valid octet.
  Reserved values are not node addresses, and a transfer aimed at one
  is dropped or mis-routed somewhere the sender cannot observe.
- Using the packet data length field as the packet length. It counts
  the data field minus one, so every comparison built on it directly
  fails by seven octets and rejects valid requests.
- Truncating an over-long transfer to the transmit limit. The receiver
  sees a short packet with no way to tell a policy truncation from a
  link fault; the request must be refused instead.
- Rewriting the CCSDS packet on the way through — padding it, aligning
  it, or fixing its length field. The entity is a carrier, and a packet
  that arrives different from the one submitted breaks any end-to-end
  check the user applied.
- Returning only the first defect. A request commonly has a bad
  destination and a bad packet at once, and reporting one at a time
  turns a single review into several.

## Behavior contract (gate 3)

The destination categorization, packet completeness check, transfer
encoding, transmit-limit refusal and combined verdict are exercised by
the gate 3 contract test: scripts/test_e5053_send_request.py against
scripts/e5053_send_request_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e5053_send_request.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
