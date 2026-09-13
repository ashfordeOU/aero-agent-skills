---
name: e2006-electric-propulsion-requirement-coverage
description: "Use when allocate every electric-propulsion requirement to the standard that owns it and confirm the charging provisions of ECSS-E-ST-20-06C clause 11.1.2 sit correctly alongside the propulsion standard governing performance, interfaces and verification-of-requirements: resolve each requirement-topic to its owning standard, flag a misallocated owner, demand an explicit cross-reference on a jointly-governed topic, reject an unrecognised verification-method, detect duplicate identifiers and conflicting ownership claims, compute weighted requirement-coverage of the mandatory charging-interaction topics, and grade the set against the agreed coverage-threshold. Trigger: ecss-e-st-20-06c, clause-11-1-2, electric-propulsion-requirement-coverage, requirement-ownership-allocation, propulsion-standard-cross-reference, verification-method-allocation, charging-provision-coverage, jointly-governed-topic."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-electric-propulsion-requirement-coverage, ecss-e-st-20-06c, electric-propulsion-requirement-coverage, requirement-ownership-allocation, propulsion-standard-cross-reference, verification-method-allocation, jointly-governed-topic]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Electric-Propulsion Requirement Coverage (space-systems/ecss/e2006-electric-propulsion-requirement-coverage)

Use when the task is placing the electric-propulsion provisions of
ECSS-E-ST-20-06C clause 11.1.2 against the propulsion standard that
governs thruster performance, interfaces and verification -- deciding
which document owns each requirement, and proving the charging side is
covered without duplicating or contradicting the propulsion side.

## Domain quick reference

- Clause 11.1.2 is a scoping clause. It does not restate propulsion
  requirements; it says the charging standard carries only the
  interaction between a thruster and the charging state of the host
  spacecraft, while thrust, specific-impulse, propellant-feed,
  mechanical and electrical interfaces, throughput-life and the
  functional-verification programme stay with the propulsion standard.
  Ownership is therefore a property of the topic, not of the author.
- Three ownership classes exist. Charging-owned topics
  (beam-neutralization-capacity, plume-charge-exchange-backflow,
  plume-sputter-erosion, neutral-gas-discharge-triggering,
  spacecraft-floating-potential, differential-charging-mitigation) are
  written here. Propulsion-owned topics are written in the propulsion
  standard and consumed here as input data. Jointly-governed topics
  (electrical-power-interface, plume-impingement-envelope,
  ground-facility-effect-correction) are written in one document only
  if the other is cross-referenced explicitly.
- A requirement that names the wrong owner is not a wording defect. It
  moves the requirement into a document whose verification programme
  does not run it, so the topic is silently unverified at
  qualification even though both documents look complete.
- Coverage is weighted, not counted. The six charging-owned topics
  carry unequal weight, so covering four low-weight topics does not
  substitute for the neutralization-capacity topic. The set is graded
  against a threshold agreed for the mission, and any gap is named
  topic by topic rather than reported as a single percentage.
- The declared verification method is part of the allocation.
  Similarity is not an acceptable route for a charging-owned topic,
  because the interaction depends on the host spacecraft geometry and
  bias state, which differ between the heritage unit and the new one.

## Workflow

1. Normalise each requirement record: identifier, topic, declared
   owning standard, verification method, optional cross-reference.
   Reject a missing field, a blank identifier, an uncategorized topic,
   an unknown owner or an unrecognised verification method.
2. Resolve the topic to its registry owner and compare it with the
   declared owner; raise a misallocated-ownership finding on a
   mismatch.
3. On a jointly-governed topic, require a cross-reference naming the
   other governing standard; a missing or unrelated cross-reference is
   a finding.
4. Reject similarity as the verification route for a charging-owned
   topic.
5. Across the set, reject duplicate identifiers and raise a finding
   when two requirements claim different owners for one topic.
6. Compute the weighted coverage of the mandatory charging-owned
   topics, list the topics still missing, and grade the ratio against
   the agreed threshold. The set is coverage-compliant only when the
   threshold is reached and no finding stands.

## Pitfalls

- Copying a propulsion requirement into the charging document so the
  charging document "looks complete". That creates two owners for one
  topic, and the two drift apart at the first design change.
- Reading a high coverage percentage as coverage of the important
  topics. Weighted coverage exists precisely because the
  neutralization-capacity topic dominates; report the missing topics,
  not only the ratio.
- Accepting a jointly-governed topic with no cross-reference because
  one document covers it adequately today. The cross-reference is what
  keeps the other document's reviewer from deleting the provision.
- Comparing the coverage ratio against the threshold with a bare
  arithmetic test. The ratio is a quotient of summed weights and an
  exactly-compliant set can land a few units in the last place below
  the threshold; absorb that representation error rather than lowering
  the threshold.
- Allowing similarity on a charging-owned topic because the thruster
  is flight-proven. The thruster may be; its interaction with this
  spacecraft's surfaces and bias state is not.

## Behavior contract (gate 3)

The ownership resolution, cross-reference rule, verification-method
validation, duplicate and conflict detection, weighted-coverage
computation and threshold grading are exercised by the gate 3 contract
test: scripts/test_e2006_electric_propulsion_requirement_coverage.py
against scripts/e2006_electric_propulsion_requirement_coverage_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2006_electric_propulsion_requirement_coverage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
