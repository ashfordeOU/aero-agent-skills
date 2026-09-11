---
name: e1011-user-pop
description: "Use when define user populations for a space system under ECSS-E-ST-10-11
  §4.2.1.3: categorize each user group as crew, ground operator, or maintainer; establish
  capability ranges across physical, cognitive, sensory, and training dimensions for
  each population; verify that all design-relevant population types are covered; and
  flag populations with missing or internally inconsistent capability entries, or any
  design parameter that falls outside the target population's capability envelope.
  Trigger: ecss, e-st-10-system-scope, user-population, human-factors, crew, ground-operator,
  maintainer, capability-range, hfe."
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
  tags: [ecss, e-st-10-system-scope, user-population, human-factors, crew, ground-operator, maintainer, capability-range, hfe]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — User Population Definition (space-systems/ecss/e1011-user-pop)

Use when the task is defining user populations for a space system design under
ECSS-E-ST-10-11 §4.2.1.3 -- identifying every distinct user group, categorizing
each into a recognised population type, and establishing the capability ranges
that bound the design.

## Domain quick reference

- §4.2.1.3 requires the programme to identify every group of people who will
  interact with the system and to characterize each group by its capability
  range across the dimensions relevant to design. Three population types are
  recognised: crew (onboard flight crew operating the system in the space
  environment), ground operator (personnel at ground control facilities),
  and maintainer (technicians who service and repair the system pre- or
  post-flight or during ground operations).
- A capability range is a min/max pair for a given dimension. Recognised
  dimensions for human-factors design include: physical reach (mm),
  cognitive load rating (1-10 scale), visual acuity (logMAR), and
  training level (1 = awareness, 2 = basic, 3 = proficient, 4 = expert).
  A range is internally consistent only when min <= max and both values
  fall within the established bounds for that dimension.
- Design parameters derived from the population definition must fall
  within the relevant population's capability range; a parameter outside
  that envelope is a design mismatch, not a capability exceedance by the
  population.
- Coverage completeness: unless the programme explicitly descopes a
  population type with documented rationale, all three types (crew,
  ground operator, maintainer) must appear in the population set.
  A missing type is flagged as a coverage gap, not silently ignored.

## Workflow

1. Inventory all groups of people who will interact with the system across
   all mission phases. For each group, assign it to exactly one of the three
   recognised population types (crew, ground_operator, maintainer). Reject
   any group whose type is not in the recognised set before it enters the
   capability analysis.
2. For each population, record capability ranges for every dimension
   relevant to the design (at minimum the four standard dimensions). Validate
   each range: confirm min <= max, and confirm both values fall within the
   established bounds for that dimension. Flag any inverted range or
   out-of-bounds value as an internal inconsistency finding for that population.
3. Check coverage completeness: confirm that at least one population entry
   exists for each of the three required types. Record each missing type as
   a coverage gap finding.
4. For each design parameter derived from a population, confirm the parameter
   value falls within the corresponding population's capability range. A
   value below the range minimum or above the range maximum is a design
   mismatch and must be flagged.
5. Aggregate all findings (internal inconsistencies per population, coverage
   gaps, design mismatches) into the population review record. The population
   set is not compliant until all finding lists are empty.

## Pitfalls

- Defining capability ranges without bounds validation and reading "no numeric
  error" as compliance -- an inverted range (min > max) or a value outside
  the dimension's physical bounds is itself a finding that must be captured,
  not suppressed.
- Omitting a population type (e.g. maintainer) because it seems peripheral
  and treating the set as complete -- unless the programme has documented
  descoping rationale, all three types are required by §4.2.1.3.
- Confusing the direction of a capability check: a design parameter must
  fall within the population's capability range; the population is not
  expected to stretch to meet the design. A mismatch means the design
  needs revision, not the population.
- Treating a population with no capability ranges on record as valid because
  no violations were computed -- a population entry with an empty capability
  map means the characterisation was never done, which is a finding.

## Behavior contract (gate 3)

The user-group categorization, capability-range validation, coverage
completeness check, design-parameter check, and population-set review logic
is exercised by the gate 3 contract test:
scripts/test_e1011_user_pop.py against scripts/e1011_user_pop_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1011_user_pop.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
