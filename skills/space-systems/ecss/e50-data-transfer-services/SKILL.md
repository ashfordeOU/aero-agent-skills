---
name: e50-data-transfer-services
description: "Evaluate the data transfer services an on-board network offers against the traffic it has to carry, under ECSS-E-ST-50C clause 5.7.2.1, whose two normative items fail differently: a service exists for every flow, and the service carrying a flow meets what that flow asked for. Assign flows to services by best fit, aggregate the load each service ends up carrying, and separate a flow with no service at all from one whose service misses its rate, its latency bound or its delivery assurance. Report utilisation, spare capacity and the shortfall in each dimension. Use when sizing or reviewing on-board network transfer services. Trigger: ecss, e-st-50-communications, on-board-network-data-transfer-service, network-service-class-assignment, on-board-flow-latency-bound, network-service-utilisation, assured-delivery-service-gap."
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
  tags: [ecss, e-st-50-communications, e50-data-transfer-services, on-board-network-data-transfer-service, network-service-class-assignment, on-board-flow-latency-bound, network-service-utilisation, assured-delivery-service-gap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — On-Board Network Data Transfer Services (space-systems/ecss/e50-data-transfer-services)

Use when the data transfer services of an on-board network are being sized
against the flows they carry, per ECSS-E-ST-50C clause 5.7.2.1 — whether a
service exists for each flow, and whether it is the service that flow needed.

## Domain quick reference

- Two normative items, and they are not the same question. One asks
  that a data transfer service exists for the traffic the network is
  required to carry. The other asks that the service actually meets
  what the flow needs. A design can pass the first and fail the second
  in the same review.
- A flow states three things, not one: a sustained rate, an upper bound
  on how long a transfer may take, and whether delivery has to be
  assured. A service that satisfies two of the three has not served it.
- Adequacy is a property of the service under its whole load. Two flows
  that each fit a service can together exceed it, so the rate test runs
  against the aggregate after every flow has been placed, never against
  the flow on its own.
- Latency and assurance behave the other way round: they are properties
  of the service alone, so they decide which services a flow may sit on
  before capacity is looked at.
- Utilisation and spare capacity belong in the report even when nothing
  failed. A network at ninety-nine percent passes every check and has
  nowhere to put the next flow the programme adds.
- Assignment has to be deterministic or the report is not reviewable.
  Largest flow first, best fit by the spare capacity left behind, and
  the service name as the tie-break gives the same answer on every run.

## Workflow

1. Declare each service with a name, its sustained capacity, the
   latency bound it commits to and whether it assures delivery.
2. Declare each flow with a name, its rate, its deadline and whether it
   needs assured delivery. Reject a duplicate name on either side: two
   entries under one name are two teams sizing the same traffic.
3. For each flow, take the services that meet its latency bound and its
   assurance need. Do not filter on capacity here.
4. Place the flows largest first, choosing the eligible service that is
   left with the least spare capacity afterwards.
5. Sum the load each service carries once every flow is placed, then
   compare that aggregate against the service capacity.
6. Compare rates and latencies with a relative tolerance. A flow sized
   to exactly fill a service, or sitting exactly on its latency bound,
   must come out adequate rather than depend on the build machine.
7. Report the two items separately — coverage and adequacy — with the
   named flows under each, the utilisation of every service and the
   rate shortfall where there is one.

## Pitfalls

- Reporting one verdict for the clause. A flow with no service and a
  flow on the wrong service are different defects with different
  owners, and one pass-or-fail line hides which you have.
- Testing rate per flow instead of per service. Every flow fits, the
  service does not, and the check that looked at them one at a time
  says the design is fine.
- Treating assured delivery as a nice-to-have that a faster service can
  substitute for. Rate does not make a lossy path lossless, and a flow
  that asked for assurance is not served by bandwidth.
- Deciding capacity or latency with a bare inequality. Two
  arithmetically identical designs can straddle the bound on different
  platforms, so the verdict changes with the host.
- Leaving assignment implicit. If the report cannot say which service
  carries which flow, nobody can reproduce the utilisation figures it
  printed, and the next reviewer starts again.
- Quoting utilisation without spare capacity. A percentage reads as
  comfortable until someone works out what it leaves in bit/s.

## Behavior contract (gate 3)

Service and flow validation, eligibility by latency and assurance,
deterministic best-fit assignment, per-service aggregate load, the
three-way flow verdict with a tolerance at the capacity and latency
bounds, the separated coverage and adequacy items, and the utilisation
and spare-capacity report are exercised by the gate 3 contract test:
scripts/test_e50_data_transfer_services.py against
scripts/e50_data_transfer_services_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_data_transfer_services.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
