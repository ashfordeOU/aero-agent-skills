---
name: e5053-target-spacewire-address
description: "Validate the target SpaceWire address prefixed to a CCSDS packet transfer protocol data unit under ECSS-E-ST-50-53C clause 5.1.4: group each leading octet as a router port selector, a logical destination, a configuration port or the reserved encoding, confirm the sequence is a run of selectors terminated at most once, trace what each router consumes, and reconcile the prefix against a directly attached target or a declared hop count. Use when a sending node builds or reviews a route prefix. Trigger: ecss, e-st-50-53-spacewire-ccsds-scope, target-spacewire-address, spacewire-path-address, spacewire-route-prefix, router-port-selector, reserved-address-encoding, direct-attachment-addressing."
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
  tags: [ecss, e-st-50-53-spacewire-ccsds-scope, e5053-target-spacewire-address, target-spacewire-address, spacewire-path-address, spacewire-route-prefix, router-port-selector, reserved-address-encoding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — Target SpaceWire Address (space-systems/ecss/e5053-target-spacewire-address)

Use when the task is the target SpaceWire address that ECSS-E-ST-50-53C
clause 5.1.4 obliges a sending node to put in front of a CCSDS packet
transfer protocol data unit — what octets belong there, in what order, and
when there should be none at all.

## Domain quick reference

- The address is a prefix, not a field inside the transfer. It exists only
  to get the data unit to the target node and is consumed on the way, so
  what the target finally reads is not what the sender wrote.
- A low-valued octet selects an output port of the next router it reaches
  and is deleted by that router. A higher-valued octet names a destination
  logically, is not deleted, and is used by every router along the way to
  look the route up. The consequence is directional: selectors have to come
  first, and a logical octet terminates the address.
- The lowest encoding of all does not reach an attached node. It addresses
  the configuration port of the router itself, which is a legitimate thing
  to want and almost never what a packet transfer wants, so it is worth
  surfacing rather than silently routing.
- The highest encoding is held reserved and must not appear anywhere in the
  prefix. It is the encoding a zeroed or all-ones buffer produces, which is
  exactly why an implementation that tolerates it will route corrupted
  addresses.
- An empty prefix is a real address. It says the target is reached with no
  routing decision, which is correct for a directly attached node and wrong
  for anything behind a router.

## Workflow

1. Validate the prefix as a sequence of octets, accepting an empty
   sequence, and refuse any member outside the range one octet can hold.
2. Group each octet: port selector, logical destination, configuration port
   or reserved encoding.
3. Count the leading port selectors. That count is the number of routers
   that will each consume exactly one octet, and it is the quantity to
   reconcile with the topology.
4. Check the shape. The prefix must be a run of selectors, optionally
   ending in a single logical octet; anything after that logical octet
   cannot be delivered and is a malformed address, not a longer route.
5. Trace the route hop by hop, removing the leading selector the way a
   router would, and confirm the address that finally arrives is the one
   the target expects to see.
6. Reconcile against the topology: a directly attached target should carry
   no prefix, a routed target must carry one, and a declared router count
   that disagrees with the selector count is a route that stops in the
   wrong place. Report a configuration-port selector as a limitation rather
   than a fault.

## Pitfalls

- Assuming the target reads the address the sender wrote. Each router
  consumes its selector, so a target checking the prefix sees only what
  survived; a test that compares the two byte for byte fails on every
  correct multi-hop route.
- Putting a logical octet before a selector. Routers stop deleting at the
  first non-selector, so the selectors behind it are delivered as data and
  the route silently ends at the logical destination.
- Treating an empty prefix as an error. It is the correct address for a
  directly attached target, and rejecting it forces implementers to invent
  a filler octet that then selects a real port.
- Letting the reserved encoding through because it parsed. It is the value
  an uninitialised buffer supplies, so tolerating it converts a memory
  fault into a routed packet.
- Reconciling the hop count against the whole prefix length rather than the
  leading selectors. A logical octet is not consumed, so counting it as a
  hop makes every mixed address look one router too long.

## Behavior contract (gate 3)

The octet grouping, prefix validation including the empty case, selector
counting, address-form checking, the per-hop consumption trace and the
reconciliation against direct attachment and a declared router count are
exercised by the gate 3 contract test:
scripts/test_e5053_target_spacewire_address.py against
scripts/e5053_target_spacewire_address_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e5053_target_spacewire_address.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
