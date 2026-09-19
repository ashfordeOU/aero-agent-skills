---
name: e4008-assembly
description: "Validate an SMP assembly artefact against the catalogues it instantiates, under ECSS-E-ST-40-08C clause 5.2.10 and the five normative items that clause places on the artefact. Use when an assembly has to be accepted or rejected while the simulator is still in its building state: resolving every instance to a type its declared catalogue actually supplies, keeping instance paths unique and every parent path resolvable, accepting a field value only where the type declares that field, the field is writable and the value fits the declared type and range, and counting the children of each container against its multiplicity bounds. Trigger: ecss, e-st-40-08-simulation-modelling-scope, e4008-assembly, smp-assembly-artefact, assembly-instance-resolution, assembly-field-configuration, assembly-container-multiplicity, assembly-build-verdict."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-assembly, smp-assembly-artefact, assembly-instance-resolution, assembly-field-configuration, assembly-container-multiplicity, assembly-build-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling — Assembly Artefact (space-systems/ecss/e4008-assembly)

Use when the task is the assembly artefact of ECSS-E-ST-40-08C clause
5.2.10 -- the document that turns a catalogue of model types into a
concrete simulator by naming the instances, placing them in the
composition tree and setting the field values that configure them.

## Domain quick reference

- The assembly is read once, while the simulator is still being built.
  Every defect it carries is a defect the whole run carries, and the
  build is the last cheap place to find one.
- An instance is only meaningful against a type. The assembly declares
  the catalogues it depends on, and an instance whose catalogue was
  never declared, or was declared but never supplied to the build, is
  two different faults with two different fixes.
- The composition path, not the instance name, is the identity. Two
  instances may both be called "gyro" as long as they hang under
  different parents; two at the same path are one instance declared
  twice and the second silently wins in a naive loader.
- Containment is typed. A child sits in a named container declared on
  the parent's type, so a child placed in a container the parent type
  does not declare has no home in the composition tree even though
  both instances resolve.
- A configured value is admissible only against the field's declared
  type. An unsigned field does not take a negative number, an integer
  field has a width and therefore a range, and a boolean is not a
  narrow integer -- the loader would widen it and no later check sees
  what was meant.
- A read-only field is a fact the model publishes, not a setting. An
  assembly that writes one is asserting control it does not have.
- Multiplicity is counted, not declared. The bounds live on the type's
  container and the count comes from the assembly, so a container
  below its lower bound is an incomplete simulator and one above its
  upper bound is an over-populated one; both are build-time facts.

## Workflow

1. Validate the catalogue set first: every field declares a known
   primitive type and every container carries sane bounds. A malformed
   catalogue makes every downstream verdict meaningless, so it raises
   rather than producing findings.
2. Walk the instances once, building the composition path for each and
   recording a duplicate path as a finding rather than overwriting.
3. Resolve each instance against its catalogue and type, separating
   the undeclared-catalogue case from the unsupplied-catalogue case
   and from the unknown-type case.
4. Resolve containment: check every parent path exists and that the
   named container is declared on the parent's type, then count the
   children that land in each container.
5. Check every configured field value in turn -- declared on the type,
   writable, type-compatible, and inside the range the declared type
   permits.
6. Compare each container's child count against its bounds and close
   with a verdict, the finding codes, and the declared catalogues that
   no instance used.

## Pitfalls

- Treating the instance name as the identity. Names repeat by design
  across branches of the composition tree; only the path is unique,
  and a name-keyed loader merges two unrelated instances.
- Accepting a boolean where an integer field is declared. Python
  widens it without complaint, the assembly records a 1 where a mode
  number was meant, and the model runs in the wrong mode all mission.
- Collapsing "catalogue not declared" and "catalogue not supplied"
  into one finding. The first is an edit to the assembly and the
  second is an edit to the build invocation.
- Checking multiplicity from the type alone. The bounds are only half
  the statement; the count comes from the assembly, and a container
  with a lower bound of one is satisfied by nothing until a child is
  actually placed in it.
- Grading a float field by a bare strict comparison against its
  magnitude bound. A value that should sit exactly on the bound can
  land a few units in the last place above it, so the comparison
  absorbs the representation error while the bound stays untouched.
- Letting an unused declared catalogue fail the build. It is worth
  reporting, because it usually means an instance was deleted and its
  dependency was not, but it does not make the simulator unbuildable.

## Behavior contract (gate 3)

The catalogue validation, path construction, type resolution,
containment and container-multiplicity counting, field-value type and
range admissibility and the build verdict are exercised by the gate 3
contract test: scripts/test_e4008_assembly.py against
scripts/e4008_assembly_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e4008_assembly.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
