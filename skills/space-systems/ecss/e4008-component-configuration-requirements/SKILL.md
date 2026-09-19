---
name: e4008-component-configuration-requirements
description: "Validate the configuration block of a component instance in an SMP Level-2 assembly artefact under ECSS-E-ST-40-08C clause 5.2.6.2: resolve every assigned field path against the instantiated type, including structure members and array elements, confirm the field is writeable at configuration time rather than model-produced output, evaluate the value against the declared datatype, range and enumeration literals, reject a path assigned twice, and refuse a value on a field already driven by a field link. Use when an assembly refuses to build, a configured value is silently overwritten, or a configuration block needs grading before the simulator leaves the building state. Trigger: ecss, e-st-40-08c, smp-level-2, assembly-artefact-configuration, component-field-assignment, configuration-value-range, enumeration-literal-check, field-link-overwrite-conflict."
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
  tags: [ecss, e-st-40-08c-smp-level-2, e4008-component-configuration-requirements, smp-assembly-artefact, component-field-configuration, configuration-value-assignment, configuration-datatype-compatibility, configuration-field-link-conflict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SMP L2 — Component Configuration Requirements (space-systems/ecss/e4008-component-configuration-requirements)

Use when the task is the configuration part of a component instance inside an
SMP Level-2 assembly artefact, per ECSS-E-ST-40-08C clause 5.2.6.2 — deciding
which field assignments the assembly may carry, and which of them the simulator
would reject or quietly discard while it is still in the building state.

## Domain quick reference

- An assembly artefact does two separable things to a component: it
  *instantiates* a model type taken from a catalogue, and it *configures* that
  instance by assigning values to its fields. Clause 5.2.6.2 governs only the
  second: what may be assigned, to what, and with which value.
- A field assignment is addressed by a path, not by a name. A path walks
  structure members with a dot and selects an array element with an index, so
  `limits.low` and `gains[2]` are both single assignments and both have to
  resolve inside the declared type before the value is looked at.
- Field direction decides configurability. An input or state field is written
  before the simulator runs and is a legitimate target; an output field is
  produced by the model on its first update, so assigning it is not a small
  inefficiency but a value that never survives.
- The value is graded twice: against the datatype (an integer primitive carries
  a representable range of its own width, an enumeration carries a literal set)
  and against any range the type declares on that particular field. A boolean
  is not a narrow integer and must not be accepted as one.
- Configuration and field links are two ways of writing the same field, and
  only one of them can win. A field that is the target of a field link is
  driven every step, so a configured value on it is overwritten as soon as the
  simulator starts — the conflict is caught at build time, not observed later.

## Workflow

1. Take the instantiated type model from the catalogue; refuse the instance
   outright if the named type is abstract, because there is nothing to
   configure.
2. Parse each assignment path into its member and index steps, rejecting a
   segment that is not a valid member reference before any lookup happens.
3. Resolve each path against the type: the member has to be declared, an index
   has to fall inside the declared extent, and a dotted continuation requires
   the preceding member to be a structure.
4. Evaluate the direction of the resolved field and set aside any assignment
   that targets model-produced output.
5. Grade the value against the datatype, the width of the integer primitive,
   the enumeration literal set, and the declared minimum and maximum.
6. Collapse the assignment set onto canonical paths so two spellings of the
   same element are seen as the duplicate they are, and cross-check the
   surviving paths against the set of fields driven by field links.
7. Report the accepted value map plus every finding, keyed by instance path and
   type, so one pass grades a whole assembly rather than one component.

## Pitfalls

- Reading an assignment failure as a value problem when it is a path problem.
  An index one past the extent and a misspelled structure member both surface
  as "the value did not take"; resolving the path first separates them.
- Configuring an output field because the model happens to expose it. The
  assignment is accepted by a permissive loader and then overwritten on the
  first update, which looks like a model defect rather than an assembly one.
- Accepting a boolean where an integer field is declared. Python treats `True`
  as 1, so a permissive check lets a wrong-typed value through and the defect
  only appears when the value is read back as an integer.
- Assigning a field that a field link already drives. Both writers are
  individually legal; it is their combination that is not, so neither the
  configuration block nor the link set looks wrong when they are graded apart.
- Comparing two spellings of the same element as text. `gains[1]` and
  `gains[01]` are one field; duplicate detection has to run on the canonical
  path, or a contradictory pair of values is silently reduced to whichever the
  loader happened to apply last.

## Behavior contract (gate 3)

The path parsing, field resolution, direction rule, datatype and range grading,
duplicate collapse and field-link conflict detection are exercised by the gate 3
contract test:
scripts/test_e4008_component_configuration_requirements.py against
scripts/e4008_component_configuration_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e4008_component_configuration_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
