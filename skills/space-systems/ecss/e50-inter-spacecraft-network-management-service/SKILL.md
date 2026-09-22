---
name: e50-inter-spacecraft-network-management-service
description: "Evaluate the management service an inter-spacecraft network offers the entity that operates it under ECSS-E-ST-50C clause 5.7.4.3, which asks that such a network be manageable and not merely connected. Compare the declared functions against what an operator has to be able to do — membership, addressing, route maintenance, link state, configuration, performance — then price the service: the polling traffic it puts on the link as a share of capacity, and how long the network takes to notice a topology change and settle again. Use when reviewing a formation or constellation network design. Trigger: ecss, e-st-50c-clause-5-7-4-3, inter-spacecraft-network-management, network-management-overhead-budget, topology-change-convergence-time, management-polling-period-sizing, managed-member-count-limit."
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
    clause: 5.7.4.3
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50c-clause-5-7-4-3, e50-inter-spacecraft-network-management-service, inter-spacecraft-network-management, network-management-overhead-budget, topology-change-convergence-time, management-polling-period-sizing, managed-member-count-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Inter-Spacecraft Network Management Service (space-systems/ecss/e50-inter-spacecraft-network-management-service)

Use when an inter-spacecraft network has to be operated and not just built,
per ECSS-E-ST-50C clause 5.7.4.3 — whether the management service it offers
covers what an operator needs, at a cost the link can carry, in time to be
acted on.

## Domain quick reference

- A management service is judged on three independent axes and a design
  can fail any one of them alone. Coverage says whether the operator can
  act at all; overhead says what acting costs the user data; convergence
  says whether the answer arrives while it still matters.
- Coverage is a set comparison, not a word count. Membership changes,
  address assignment, route maintenance, link-state monitoring,
  configuration control and performance reporting each let an operator
  do something the others do not, and a service missing one of them
  leaves a part of the network the operator cannot reach.
- An unrecognised function name is a finding, not noise. In practice it
  is a required function under a house name, and quietly discarding it
  turns a naming slip into a missing capability that the coverage check
  then reports as absent.
- Management traffic competes with the payload it manages. Polling cost
  is members times exchange size over the period, so it grows with the
  formation and shrinks with patience, and the allowance is expressed
  against the same capacity the mission data was sized against.
- Convergence has a floor the polling rate cannot lower. Detection
  scales with the polling period, but propagation across the network
  diameter and the reconfiguration itself do not, so once those two
  exceed the allowance no polling rate meets it and the honest answer
  says so.
- Both overhead and convergence invert cleanly, and the inverses are the
  useful output: the largest membership the allowance holds, and the
  longest polling period that still converges in time.

## Workflow

1. Take the declared management functions and compare them against the
   required set case-insensitively. Report present, missing and
   unrecognised separately.
2. Compute the polling overhead from the member count, the per-member
   exchange size and the polling period, and express it as a share of
   link capacity.
3. Compare that share against the overhead allowance with a relative
   tolerance so a design sitting exactly on the allowance passes
   everywhere.
4. Compute detection from the polling period and the miss threshold,
   then add propagation across the network diameter and the
   reconfiguration time to get convergence.
5. Compare convergence against the time the operator has, using the
   same relative tolerance.
6. Invert both bounds: the largest membership inside the overhead
   allowance at this period, and the longest period inside the
   convergence allowance. Report zero for the period where propagation
   and reconfiguration already spend it all.
7. Check each stated remedy back through the model before offering it,
   and report the verdict as complete only when coverage, overhead and
   convergence all hold.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.7.4.3a | 1 |

## Pitfalls

- Treating connectivity as management. A network that carries traffic
  between members but offers no way to add one, re-address one or see
  that a link has gone is not manageable, and nothing in the throughput
  figures shows that.
- Discarding a declared function whose name is not on the list. It is
  usually the required function spelled differently, and dropping it
  silently is how a coverage report becomes wrong in both directions.
- Sizing the overhead for today's membership. Polling cost is linear in
  members, so a formation that grows walks into the allowance; the
  member limit is the number worth carrying forward.
- Answering slow convergence by polling harder without checking the
  fixed part. Propagation and reconfiguration do not move with the
  polling period, and a period computed as if they did comes out
  negative or unbuildable.
- Deciding either bound with a bare inequality. A design landing exactly
  on its allowance can pass on one build host and fail on another, so
  both comparisons carry a relative tolerance.
- Rounding the member limit up. The limit is the last count that fits;
  one more member breaks the allowance, and a ceiling hands over a
  design that is already over.

## Behavior contract (gate 3)

Function-set coverage including unrecognised names, the polling overhead
model and its capacity share, detection and convergence timing, the
exact-allowance boundaries, the largest-membership and longest-period
inverses and their zero cases are exercised by the gate 3 contract test:
scripts/test_e50_inter_spacecraft_network_management_service.py against
scripts/e50_inter_spacecraft_network_management_service_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e50_inter_spacecraft_network_management_service.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
