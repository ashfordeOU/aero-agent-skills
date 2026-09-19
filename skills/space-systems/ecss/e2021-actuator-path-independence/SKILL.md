---
name: e2021-actuator-path-independence
description: "Analyze whether the nominal and redundant actuator firing paths stay independent all the way to the device under ECSS-E-ST-20-21C clause 5.3.2. Use when the task is finding the single failure a block diagram hides: validate each path as a chain from energy source to actuator interface, intersect the element sets to catch a box both paths pass through, intersect the resources to catch a shared harness bundle, connector shell, secondary bus or routing zone, collect the common cause failures, and report which path still reaches the device after any named element or resource is lost. Trigger: ecss, e-st-20-21-actuation-scope, actuator-path-independence, firing-path-common-cause, shared-harness-bundle-routing, firing-path-element-intersection, actuation-loss-single-failure."
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
  tags: [ecss, e-st-20-21-actuation-scope, e2021-actuator-path-independence, firing-path-common-cause, shared-harness-bundle-routing, firing-path-element-intersection, actuation-loss-single-failure, firing-path-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuation Electronics — Actuator Path Independence (space-systems/ecss/e2021-actuator-path-independence)

Use when the task is the path independence requirement of
ECSS-E-ST-20-21C clause 5.3.2 -- establishing that the nominal and the
redundant firing path stay separate all the way to the actuator, so
that no single failure can take actuation away.

## Domain quick reference

- Independence fails in two ways and only one of them is on the block
  diagram. A shared element is a box both paths pass through, and it
  is visible to anyone reading the drawing. A shared resource is two
  separate boxes that nonetheless depend on the same thing, and the
  drawing says nothing about it.
- The resources that matter are the ones integration creates: a
  harness bundle both paths are tied into, a connector shell both sets
  of wires pass through, a secondary bus both electronics draw from, a
  routing zone both cables cross. A connector crushed during
  integration takes both paths just as completely as a failed switch.
- A path is only a firing path when it carries the whole chain: an
  energy source to supply the pulse, a firing switch to break it, a
  harness to carry it and an interface at the actuator to terminate
  it. A declared path missing one of those cannot be graded for
  independence because it does not yet reach the device.
- The right object to report is the common cause set: the union of the
  shared elements and the shared resources. Every member of it is a
  single failure that removes both paths, and an empty set is what the
  clause actually asks for.
- Naming which element on each side brings a shared resource in is
  what makes the finding actionable. Reporting that both paths use
  bundle A is an observation; reporting that the nominal harness and
  the redundant harness are both tied into bundle A is a work order
  for the harness drawing.
- The loss case closes the argument the other way round. Take any
  named element or resource away and say which path still reaches the
  device; an empty answer is the failure the whole duplication was
  bought to avoid.

## Workflow

1. Declare each path as an ordered chain of elements, each with its
   kind and the resources it depends on. Refuse an unknown element
   kind, an element declared twice inside one path, a resource listed
   twice on one element, and two paths declared under the same name.
2. Check each path for completeness against the element kinds a firing
   path needs, and report the missing kinds per path before grading
   independence.
3. Intersect the two element sets and report every element both paths
   pass through.
4. Intersect the resources the two paths depend on, and for each
   shared resource name the elements on each side that bring it in.
5. Collect the common cause failures as the union of those two
   intersections, sorted so a report is stable between runs.
6. For any element or resource of interest, report which paths still
   reach the actuator once it is lost, and close with an independence
   verdict and the findings that block it.

## Pitfalls

- Grading independence from the block diagram alone. The diagram shows
  the elements, not the bundle they are tied into or the bus they draw
  from, so a pair of paths that looks fully separated can still have a
  single connector between it and total loss of actuation.
- Treating separate boxes as separate paths. Two firing switches on
  two boards fed from one secondary bus fail together on that bus, and
  the element intersection is empty while the resource intersection is
  not.
- Grading a path that does not reach the device. A declared chain with
  no actuator interface, or with no firing switch, is incomplete;
  intersecting it with the other path answers a question about
  something that is not yet a firing path.
- Reporting a shared resource without its holders. The resource name
  alone does not say what to change; the element on each side that
  brings it in is what the harness drawing or the bus allocation has
  to act on.
- Stopping at the verdict. The loss case -- which path survives when
  this element or this resource goes -- is what a failure analysis and
  an integration review both need, and it is not recoverable from a
  yes or no.

## Behavior contract (gate 3)

Element and path validation, path completeness, the element
intersection, the resource intersection with its holders, the common
cause set, the element and resource loss cases and the independence
verdict are exercised by the gate 3 contract test:
scripts/test_e2021_actuator_path_independence.py against
scripts/e2021_actuator_path_independence_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2021_actuator_path_independence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
