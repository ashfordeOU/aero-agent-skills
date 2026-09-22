---
name: e50-on-board-network-management-service
description: "Audit the management service an on-board network offers over its own resources, under ECSS-E-ST-50C clause 5.7.2.4, where a resource counts as managed only when the service reaches it for every operation it is owed and can still reach it when that resource has failed. Compute per-resource operation coverage against the required set, then test each management path for the two faults that matter: a path that runs through the resource it manages, and a hop nobody in the inventory manages. Report a three-way verdict, a gap list and a coverage ratio. Use when reviewing on-board network management. Trigger: ecss, e-st-50-communications, on-board-network-management-service, network-resource-management-coverage, management-path-self-dependency, unmanaged-network-hop, network-management-operation-gap."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.7.2.4
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-on-board-network-management-service, on-board-network-management-service, network-resource-management-coverage, management-path-self-dependency, unmanaged-network-hop, network-management-operation-gap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — On-Board Network Management Service (space-systems/ecss/e50-on-board-network-management-service)

Use when an on-board network's own resources are being reviewed for
manageability, per ECSS-E-ST-50C clause 5.7.2.4 — whether the management
service reaches every resource, and whether it still reaches it on a bad day.

## Domain quick reference

- The clause asks for a service over the network's own resources, and
  two independent properties decide whether that service exists for a
  given resource. A review that asks only the first passes designs that
  cannot be managed at the moment management is needed.
- Operation coverage is the first. A resource is owed a set of
  operations — typically setting its configuration, reading its state,
  and commanding it — and a resource that can be read but not commanded
  is monitored, not managed.
- Path independence is the second, and it is the one that is assumed.
  Management traffic for a resource must not have to pass through that
  resource. A router managed only through itself is manageable exactly
  while it is working, which is when nobody needs to.
- A hop that is not itself in the managed inventory is the same defect
  one step out. Nothing in the design says who configures it or reports
  its state, so the management path depends on something unmanaged.
- The two failures stack, and the report must not let one hide the
  other. A resource with an unreliable path can be missing operations
  as well, and a verdict that stops at the path fault loses the gap.
- A coverage ratio over the whole inventory is worth printing next to
  the verdict. It is what turns nine scattered gaps into a number a
  programme can track between reviews.

## Workflow

1. Declare every managed resource with a name, the management
   operations it supports, and the hops its management traffic takes.
2. State the required operation set explicitly, and check it covers the
   work the clause gives the service: holding the routing and
   configuration tables of the network correct as the network changes,
   which is what keeps it dependable and available rather than merely
   observable. Shortening the set is how a gap becomes a pass, so make
   the set an input and print it back.
3. For each resource, take the required operations it does not support.
   An extra operation beyond the set is not a gap.
4. Test the management path for a self-dependency: the resource's own
   name among its hops.
5. Test each remaining hop against the declared inventory. A hop that
   is not a managed resource is an unmanaged dependency.
6. Give a three-way verdict — managed, partial, unreachable — letting a
   path fault outrank an operation gap, and keep both in the reasons.
7. Report the coverage ratio over every resource and every required
   operation, and list the two clause failures separately.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.7.2.4a | 2 |

## Pitfalls

- Counting a resource as managed because it answers a status poll.
  Reading state is one operation of the set, and it is the one that
  works when the others were never wired.
- Silently shortening the required set to whatever the design happens
  to support. The gap is then reported as full coverage and nobody sees
  what was dropped.
- Assuming the management path is out of band. On a shared on-board
  network it usually is not, and the path that carries management
  traffic is often the thing being managed.
- Letting the path fault swallow the operation gap. Fixing the path
  then produces a resource that is reachable and still cannot be
  commanded, which is a second review nobody budgeted.
- Accepting a path hop that is not in the inventory. It is not managed
  by anybody, so no gate will ever ask whether it works.
- Reporting a verdict with no ratio. Nine gaps across thirty resources
  and nine gaps across three are different programmes.

## Behavior contract (gate 3)

Name and operation-list validation, per-resource gaps against a
declared required set, self-dependency and unmanaged-hop path faults,
the three-way resource verdict with a path fault outranking a coverage
gap without hiding it, and the inventory-wide coverage ratio with the
two clause failures reported separately are exercised by the gate 3
contract test:
scripts/test_e50_on_board_network_management_service.py against
scripts/e50_on_board_network_management_service_logic.py (stdlib
unittest, offline).
Run:
python3 scripts/test_e50_on_board_network_management_service.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
