---
name: mission-lifetime-environment-spec
description: "Use when specify the mission design lifetime and compile the natural
  and induced environment inventory for a spacecraft structure programme under
  ECSS-E-ST-32 clauses 4.2.1-4.2.2: establish the reference design duration that
  bounds fatigue, creep, and material-degradation calculations; inventory each
  environmental load family (thermal, radiation, debris, atomic oxygen, acoustic,
  vibration, shock) active across launch, transfer-orbit, and on-orbit phases; assign
  each family to the natural or induced environment category; confirm every family
  carries a quantified numeric specification; and verify completeness before
  structural margins and allowables are sized. Trigger: ecss, e-st-32-structures-scope,
  mission-lifetime, design-lifetime, natural-environment, induced-environment,
  thermal, radiation, environment-inventory."
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
  tags: [ecss, e-st-32-structures-scope, mission-lifetime, design-lifetime, natural-environment, induced-environment, thermal, radiation, environment-inventory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Mission Lifetime and Environment Specification (space-systems/ecss/mission-lifetime-environment-spec)

Use when the task is to establish the design lifetime and compile a complete
natural and induced environment inventory for a spacecraft structural programme
under ECSS-E-ST-32 clauses 4.2.1-4.2.2. The output of this leaf is the
quantified environment set that feeds downstream sizing: margin policy,
allowables selection, fatigue life, and load-combination rules all depend on
a complete, quantified inventory being in place first.

## Domain quick reference

- Clause 4.2.1 requires the programme to declare a design lifetime in years,
  then derive a qualification test duration by multiplying by the qualification
  life factor (minimum 1.5 per ECSS-E-ST-32 guidance) and an acceptance test
  duration by multiplying by the acceptance life factor (minimum 1.25). These
  derived durations set the endurance the structural hardware must demonstrate
  without failure or unacceptable degradation.
- Clause 4.2.2 requires an inventory that assigns every environmental load
  family to exactly one category: natural (originating outside the spacecraft —
  solar thermal flux, ionising radiation, meteoroid/debris flux, atomic oxygen,
  UV) or induced (originating from the spacecraft or launch vehicle — acoustic
  noise, random vibration, shock, quasi-static load, internal pressure, thruster
  plume thermal). A family must not be double-counted across categories.
- Every environment family in the inventory must carry a quantified numeric
  specification before it may be used in a structural analysis. A family listed
  without a quantified spec is incomplete — it is not a pass, it is an open
  finding that blocks analysis.
- Mission phases — launch, transfer orbit, on-orbit, disposal — each activate
  different environment subsets. An environment family is active in a phase only
  if it is explicitly assigned to that phase in the inventory; absence from a
  phase means no contribution, not a conservative worst case.

## Workflow

1. Declare the design lifetime in full years. Apply the qualification life
   factor (≥ 1.5) to derive the qualification test duration and the acceptance
   life factor (≥ 1.25) to derive the acceptance test duration. Reject any
   factor below its minimum before proceeding.
2. List every environmental load source expected to act on the structure across
   all mission phases. For each source, identify which mission phases it is
   active in (launch, transfer-orbit, on-orbit, disposal).
3. Assign each environment family to either the natural category or the induced
   category. Reject any family name not in the programme's recognised environment
   taxonomy — an unrecognised source must be resolved or explicitly excluded
   before the inventory is considered complete.
4. For each environment family, confirm a quantified numeric specification exists
   (level, duration, and applicable phases explicitly stated). Flag every family
   that lacks a numeric spec as an open finding.
5. Verify that the minimum required families (thermal, radiation, acoustic,
   vibration, shock) are all present and quantified. A missing required family
   is an inventory-completeness finding.
6. Aggregate all findings. The environment inventory is complete only when the
   finding list is empty — no missing families, no unquantified entries.

## Pitfalls

- Assigning a life factor below the ECSS-E-ST-32 minimum and treating the
  programme as compliant — the minimum factors are not suggestions; a factor of
  1.4 for qualification is a non-conformance regardless of test outcome.
- Omitting mission phases from the environment family's scope and later applying
  the family's level as a worst-case envelope across all phases — only phases
  explicitly assigned to a family contribute to that family's load; blank-field
  universalism understates conservative analysis in some phases and overstates
  it in others.
- Recording an environment family in the inventory without a numeric
  specification and reading the inventory as complete — an entry without a number
  is an open action item, not a quantified environment.
- Allowing a family to appear in both the natural and induced categories — every
  family has exactly one origin type; double-counting inflates the environment
  budget and produces inconsistent load combinations downstream.
- Deferring the environment inventory until after structural margins are
  computed — the inventory must be locked first because margins, allowables, and
  load-combination factors all reference it.

## Behavior contract (gate 3)

The lifetime-margin validation, environment-family categorization, inventory
completeness check, and per-phase filtering logic is exercised by the gate 3
contract test: scripts/test_mission_lifetime_environment_spec.py against
scripts/mission_lifetime_environment_spec_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_mission_lifetime_environment_spec.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
