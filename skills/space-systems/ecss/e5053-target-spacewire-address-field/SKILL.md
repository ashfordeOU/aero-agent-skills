---
name: e5053-target-spacewire-address-field
description: "Build and validate the target SpaceWire address field that leads a packet, against ECSS-E-ST-50-53 clause 5.3.1. Use when a route to a target node has to be turned into leading address bytes, or an existing field has to be graded before it is sent: categorize every byte as null padding, path address, logical address or reserved, reject a reserved byte and padding that has drifted out of the leading run, assemble a field from a port list with an optional logical address, pad it to the declared alignment, consume it hop by hop the way a router does, and report an empty field against a target that is not directly attached. Trigger: ecss, e-st-50-53, target-spacewire-address-field, spacewire-path-address, spacewire-logical-address, leading-address-padding, router-hop-address-consumption, spacewire-packet-header."
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
  tags: [ecss, e-st-50-spacewire-scope, e5053-target-spacewire-address-field, target-spacewire-address-field, spacewire-path-address, spacewire-logical-address, leading-address-padding, router-hop-address-consumption]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire — Target Address Field (space-systems/ecss/e5053-target-spacewire-address-field)

Use when the task is the target SpaceWire address field of
ECSS-E-ST-50-53 clause 5.3.1 — the run of address bytes that leads a
packet, carries it across the routers between initiator and target, and
has been consumed entirely by the time the packet arrives.

## Domain quick reference

- The field is positional, not a header with named fields. Every byte in
  it is one of four things and its value alone decides which: the null
  byte used as leading padding, a path address naming the output port of
  the next router, a logical address naming the target itself, or a
  reserved value that may not be sent.
- Path addresses occupy the low byte values and logical addresses the
  range above them, up to but excluding the top value, which is reserved.
  A field can therefore be read without any knowledge of the network it
  crosses, which is what lets a router forward on the leading byte alone.
- A router consumes the leading significant byte and forwards the rest.
  The field a node receives is therefore shorter than the one the
  initiator sent, and the remaining field after a given hop is computable
  in advance — which is how a route is checked before it is used.
- Leading null bytes are padding. They are discarded on the way and exist
  only so the field can be brought up to an alignment the initiator
  wants. A null that has drifted into the middle of the field is not
  padding any more; it terminates the route early and the packet is lost.
- A path byte after a logical address is unroutable in the same way. Once
  the logical address has been reached the route is over, so anything
  following it cannot be part of the target address.
- An empty field means the target is attached directly to the initiator.
  For any other target the empty field is the defect that looks like a
  valid short route.

## Workflow

1. Categorize each byte of the field: null, path, logical or reserved.
   Values outside the byte range, and non-integer values, are malformed
   input rather than findings.
2. Parse the field positionally: count the leading null run, collect the
   path bytes that follow, then the optional single logical address.
   Refuse an interior null, a reserved byte, and any byte following the
   logical address.
3. To build a field, validate the port list against the path-address
   range and the logical address against its own range, concatenate them,
   and prepend null padding only when an alignment is asked for.
4. Compute the alignment state of a field rather than assuming it: the
   length and whether it is a whole multiple of the declared alignment.
5. Consume a hop by taking the leading significant byte, refusing when it
   is not a path address, and returning the port together with the
   remaining field the next router will see.
6. Route the whole way by consuming hops in turn, so the ports taken and
   the residue at the target can be reported together.
7. Grade a field against its intent: the declared hop count, whether the
   target is directly attached, and whether alignment was required.

## Pitfalls

- Treating the null byte as a valid address because it is inside the byte
  range. It is padding, and only in the leading run; anywhere else it
  truncates the route.
- Padding at the end of the field to reach the alignment. The padding has
  to lead, because the router consumes from the front and trailing nulls
  would arrive as route bytes.
- Building a route with the logical address in the middle so the packet
  can be forwarded past the target. The route ends at the logical
  address; anything after it is unreachable.
- Assuming the field a target receives is the field that was sent. Each
  router removes one byte, so the residue has to be computed before the
  packet is graded at the far end.
- Reading an empty field as a valid short route. It is valid only for a
  directly attached target, and that is a property of the topology, not
  of the field.
- Using the top byte value as a broadcast or wildcard. It is reserved and
  a field carrying it is refused.

## Behavior contract (gate 3)

The byte categorization, positional parsing, field assembly, padding and
alignment, hop consumption, whole-route walking and field grading are
exercised by the gate 3 contract test:
scripts/test_e5053_target_spacewire_address_field.py against
scripts/e5053_target_spacewire_address_field_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e5053_target_spacewire_address_field.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
