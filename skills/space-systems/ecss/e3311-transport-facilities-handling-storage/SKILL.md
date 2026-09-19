---
name: e3311-transport-facilities-handling-storage
description: "Manage the transport, facility, handling and storage controls an explosive item is owed under ECSS-E-ST-33-11C clause 4.15. Use when the task is deciding whether a magazine, a handling bay or a shipment is actually safe: grouping stored items by compatibility group and reporting every pair that must not share a magazine, aggregating the net explosive quantity against the licensed holding, deriving the quantity-distance separation from the cube-root scaling law and grading real distances to exposed sites, checking the storage temperature and humidity envelope, and grading bonding, personnel limits, radio-frequency exclusion and the safing device. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-compatibility-group-segregation, net-explosive-quantity-licence, quantity-distance-cube-root, explosive-storage-envelope, explosive-handling-rf-exclusion, explosive-shipment-safing."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-transport-facilities-handling-storage, explosive-compatibility-group-segregation, net-explosive-quantity-licence, quantity-distance-cube-root, explosive-storage-envelope, explosive-handling-rf-exclusion, explosive-shipment-safing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Transport, Facilities, Handling and Storage (space-systems/ecss/e3311-transport-facilities-handling-storage)

Use when the task is the transport, facility, handling and storage
requirement of ECSS-E-ST-33-11C Rev.1 clause 4.15 -- the period of an
explosive item's life where nothing is being verified and everything
can still go wrong, from the magazine it sits in to the van it leaves
in.

## Domain quick reference

- Compatibility grouping decides what may share a building. Items whose
  group requires isolation share a magazine with nothing but their own
  kind; items packaged so their effects stay inside the package mix
  with almost anything; the ordinary transport-device groups mix with
  each other. A store is graded pairwise, because one added item can
  break a store that was compliant an hour earlier.
- Quantity-distance is a cube-root law. The separation a store owes an
  exposed site scales with the cube root of the net explosive quantity,
  so eight times the quantity needs twice the distance, not eight
  times. The consequence people get wrong is the other direction:
  halving a distance needs the quantity cut by a factor of eight.
- Net explosive quantity is the aggregate actually present, counted
  over units, not the figure on the licence and not the figure on the
  last stock sheet. A store goes over its licence by receiving a
  delivery, which is the moment nobody recomputes it.
- The storage envelope is a shelf-life instrument. Explosives age
  faster warm and absorb water damp, so an excursion is a finding even
  when the item still looks serviceable, because its remaining life has
  been spent rather than its function lost.
- Handling controls exist to keep the item inert while people are
  within its effect radius: a bonded handling point so no electrostatic
  path builds, a personnel limit so an event injures as few people as
  possible, a radio-frequency exclusion so no transmitter couples into
  the initiation circuit, and the safing device physically fitted.
- A shipment is a store that moves. It owes the same compatibility
  segregation inside the load, a container qualified for the item, the
  safing device fitted, and a declared quantity that matches what is
  actually packed -- the declaration is what the emergency responder
  will act on.

## Workflow

1. Walk the stored items pairwise and report every compatibility
   conflict by both item names and both groups, so the reader can see
   which item to move.
2. Aggregate the net explosive quantity over units and counts, and
   grade it against the licensed holding.
3. Derive the required separation for that aggregate from the
   cube-root law and the site's scaling factor, then grade each exposed
   site's real distance against it, naming the site in the finding.
4. Grade the measured storage temperature and humidity against the
   item's envelope, reporting a low-temperature excursion as readily as
   a high one.
5. Grade each handling operation on bonding, personnel count, radio
   exclusion distance and the safing device, and report every control
   that is open rather than stopping at the first.
6. Grade each shipment on its container, its safed state, the match
   between declared and packed quantity, and the compatibility of the
   load with itself.
7. Snap a cube root to an exact integer root where one exists, and
   absorb representation error at every distance comparison, so a
   site sitting exactly on its required distance is not failed by the
   last bit of a power.

## Pitfalls

- Grading a store by its largest item instead of pairwise. The conflict
  is between two specific items; a store holding one isolation-group
  item and twenty compatible ones is non-compliant because of the one.
- Scaling separation linearly with quantity. The cube-root law is what
  makes a small increase in holding cheap and a large one expensive,
  and a linear estimate is wrong in both directions depending on which
  side of the reference point it is taken from.
- Trusting the declared net explosive quantity. It is a copied number;
  the aggregate is a computed one, and a mismatch between them is the
  finding, not a rounding difference to be reconciled quietly.
- Treating a storage excursion as recoverable because the item still
  functions. The envelope protects remaining life, not present
  function, so a passed post-excursion test does not close it.
- Leaving the safing device off during a handling operation because the
  item is "only being moved". Movement is when it is dropped.
- Failing a site that sits exactly on its required distance. Equality
  at the boundary is a representation question, absorbed by the
  tolerance inside the comparison; the required distance stays as
  derived.

## Behavior contract (gate 3)

The pairwise compatibility grouping, net-explosive-quantity aggregation,
licensed-holding check, cube-root quantity-distance derivation, storage
envelope grading, handling-control grading and shipment grading are
exercised by the gate 3 contract test:
scripts/test_e3311_transport_facilities_handling_storage.py against
scripts/e3311_transport_facilities_handling_storage_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3311_transport_facilities_handling_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
