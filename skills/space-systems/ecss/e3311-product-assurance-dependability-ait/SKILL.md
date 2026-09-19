---
name: e3311-product-assurance-dependability-ait
description: "Assess the dependability of an explosive train and the assembly, integration and test controls around it under ECSS-E-ST-33-11C clause 4.17. Use when the task is proving a pyrotechnic chain is reliable enough and handled safely on the floor: computing train reliability from series stages of parallel elements, apportioning a system target across those stages, finding the single-point stages and checking each sits on the critical-items list, and validating that the live device goes in late, inside a controlled area, with nothing needing an inert vehicle afterwards and every powered operation running on its inhibit. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-train-reliability-apportionment, pyrotechnic-single-point-failure, explosive-critical-items-list, live-device-installation-sequence, explosive-ait-inhibit-control."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-product-assurance-dependability-ait, explosive-train-reliability-apportionment, pyrotechnic-single-point-failure, explosive-critical-items-list, live-device-installation-sequence, explosive-ait-inhibit-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Dependability and AIT (space-systems/ecss/e3311-product-assurance-dependability-ait)

Use when the task is the product-assurance requirement of
ECSS-E-ST-33-11C Rev.1 clause 4.17 -- the dependability numbers an
explosive subsystem owes, and the assembly, integration and test
discipline that keeps those numbers true once the hardware is on a
vehicle.

## Domain quick reference

- An explosive train is series in function and often parallel in
  hardware. Stages multiply, elements inside a stage combine through
  their failure probabilities, and the distinction matters: two
  initiators on one charge is a parallel stage, an initiator feeding a
  transfer line feeding a nut is three series stages.
- Redundancy buys orders of magnitude inside a stage and nothing at
  all across stages. Two parallel elements at 0.9 give a stage of 0.99;
  two series stages at 0.9 give 0.81. A design review that reports
  "redundant initiators" has said nothing about the stages downstream
  of them.
- Apportionment turns a system target into something a stage owner can
  design against: the equal share for a series train of n stages is the
  nth root of the target. Stages below their share are where the design
  effort goes, and naming them is more useful than a single pass or
  fail on the total.
- Any stage with one element is a single-point failure. At the severe
  criticality levels that has a consequence in paperwork as well as
  design: the stage belongs on the critical-items list, and a
  single-point stage missing from that list is the finding, whether or
  not the reliability total is met.
- The AIT rule that matters is ordering. A live device goes in as late
  as the flow allows, because everything scheduled after it is done
  around live explosive. An operation that needs an inert vehicle and
  is scheduled after installation has not been made safe by being
  written down carefully.
- After installation, powering the vehicle is only acceptable with the
  inhibit fitted, and the installation itself belongs in an
  electrostatically controlled area. Both are binary conditions, which
  is what makes them checkable.

## Workflow

1. Normalise the train: reject an empty stage, a duplicate stage
   identifier, a reliability outside the unit interval and a
   criticality outside its range, before computing anything.
2. Compute each stage from its parallel elements, then multiply the
   stages into the train reliability, keeping the per-stage breakdown
   for the report.
3. Compare the achieved reliability against the system target,
   absorbing representation error so an architecture that exactly meets
   its target is not failed by the last bit of a product.
4. Apportion the target across the stage count and name every stage
   that sits below its share, as design guidance rather than a
   pass-or-fail verdict.
5. Find the single-element stages, and raise a finding for each one at
   severe criticality that the declared critical-items list does not
   carry.
6. Walk the AIT flow, locate the installation of the live device, and
   grade the controlled area at that step plus every later operation
   for an inert-vehicle need or an uninhibited power-up.
7. Report the count of operations remaining after installation, because
   shortening that tail is the actual mitigation.

## Pitfalls

- Multiplying element reliabilities inside a parallel stage. Parallel
  elements combine through their failure probabilities; multiplying
  them makes a redundant stage look worse than a single element, which
  is the wrong direction and is usually spotted only after the design
  has been changed to remove the redundancy.
- Reporting only the train total. A total that meets its target can
  hide a stage an order of magnitude below its apportioned share, and
  that stage is where the next failure comes from.
- Treating the critical-items list as documentation. It is what drives
  the inspection, screening and traceability the single-point stage
  then receives; leaving a stage off it removes those controls
  silently.
- Scheduling a test that needs an inert vehicle after the live device
  goes in and mitigating it with a procedure note. The ordering is the
  control; the note is not.
- Powering the vehicle after installation without the inhibit because
  the operation is short. Duration is not a control either.
- Widening the reliability target to absorb a shortfall. An exact
  equality at the target is a representation question, handled by the
  tolerance inside the comparison; a genuine shortfall is a design
  change.

## Behavior contract (gate 3)

The stage and train reliability computation, target apportionment,
single-point stage detection, critical-items cross-check and AIT
installation-ordering validation are exercised by the gate 3 contract
test: scripts/test_e3311_product_assurance_dependability_ait.py against
scripts/e3311_product_assurance_dependability_ait_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3311_product_assurance_dependability_ait.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
