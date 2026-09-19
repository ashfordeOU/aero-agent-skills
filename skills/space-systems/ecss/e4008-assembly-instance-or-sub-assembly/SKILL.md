---
name: e4008-assembly-instance-or-sub-assembly
description: "Verify the instance and sub-assembly tree of an SMP Level-2 assembly artefact against ECSS-E-ST-40-08C clause 5.2.9: every node carries a valid identifier unique among its siblings, names exactly one implementation - a catalogue model type or a sub-assembly, never both - instantiates no abstract type, expands no sub-assembly that is undeclared or that recurses into itself, stays within the nesting depth, holds children only where containment and its multiplicity admit them, and leaves no declared assembly unreached from the root. Use when an assembly artefact will not build or an instance path resolves to nothing. Trigger: ecss, e-st-40-08c, smp-level-2, assembly-instance-tree, sub-assembly-expansion, sub-assembly-recursion, container-child-multiplicity, abstract-type-instantiation."
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
  tags: [ecss, e-st-40-08c-smp-level-2, e4008-assembly-instance-or-sub-assembly, smp-assembly-artefact, assembly-instance-tree, sub-assembly-expansion, sub-assembly-recursion-guard, container-child-multiplicity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SMP L2 — Assembly Instance or Sub-Assembly (space-systems/ecss/e4008-assembly-instance-or-sub-assembly)

Use when the task is the instance tree of an SMP Level-2 assembly artefact per
ECSS-E-ST-40-08C clause 5.2.9 — what each node of the tree may name, how a
sub-assembly is expanded into it, and which paths the rest of the artefact is
then allowed to reference.

## Domain quick reference

- A node of the tree is one of two things and never both: an instance of a
  model type taken from a catalogue, or a sub-assembly, which is a reference to
  another assembly expanded in place. A node naming both is ambiguous; a node
  naming neither builds nothing.
- The instance path is the product of the tree, not a label on it. Every link
  endpoint, every configuration target and every schedule entry elsewhere in
  the artefact addresses a node by the dotted chain of names from the root, so
  name uniqueness among siblings is what makes those references resolvable.
- Sub-assembly expansion is substitution, not containment. The children of a
  sub-assembly node come from the assembly it names, which is why that node
  cannot declare children of its own and why the same sub-assembly can be
  expanded at several places in one tree.
- Recursion through sub-assemblies is the failure that does not announce
  itself. An assembly that reaches itself, directly or through a chain,
  describes an infinite tree, so the expansion has to carry its own stack and
  stop at the repeat rather than discovering it by exhausting memory.
- Containment is a property of the model type. A type that declares no
  containment cannot hold children at all; one that declares it carries a
  multiplicity, and both ends of that multiplicity bind — a container short of
  its lower bound is as non-conformant as one past its upper bound.
- A declared assembly that the root never reaches is dead weight in the
  artefact. It is not built, nothing can address it, and it usually marks
  either a deleted reference or the sub-assembly someone forgot to wire in.

## Workflow

1. Take the root assembly and expand its node list, carrying the path prefix,
   the depth and the stack of assemblies currently being expanded.
2. For each node, validate the name as an identifier and reject a repeat among
   its siblings before anything else is examined.
3. Establish which implementation the node names, rejecting the both-and the
   neither-case explicitly rather than letting one of them win silently.
4. Stop descending when the depth passes the declared maximum, reporting the
   path that crossed it.
5. For a model-type node: confirm the type is in the catalogue, refuse an
   abstract type, then grade its children against the containment declaration
   and its multiplicity before descending into them.
6. For a sub-assembly node: refuse inline children, confirm the assembly is
   declared, and refuse to descend when that assembly is already on the
   expansion stack, reporting the cycle at the node that closed it.
7. Compare the set of declared assemblies with the set the expansion visited,
   and report every assembly the root never reached; return the flattened node
   records, the achieved depth and all findings.

## Pitfalls

- Detecting recursion by depth alone. A depth limit stops the expansion but
  reports the wrong defect: the tree is not too deep, it is circular, and the
  repair is a reference to remove rather than a limit to raise.
- Letting a node carry both a type and a sub-assembly. Loaders pick one by
  order of appearance, so the artefact behaves consistently until the day the
  file is regenerated with the keys in the other order.
- Giving a sub-assembly node children. They look like an override of the
  referenced assembly and are not; the referenced definition supplies the
  children, and the inline ones are silently dropped or duplicated.
- Checking only the upper bound of a container. A container below its lower
  bound builds an incomplete subsystem that fails much later, during
  initialisation, with no reference back to the assembly artefact.
- Treating an unreached assembly as harmless. It is never validated against the
  catalogue by the build, so it rots quietly and fails the moment somebody
  wires it in.
- Instantiating an abstract type because the catalogue lists it. Presence in
  the catalogue is what makes it referenceable by derived types, not what makes
  it buildable.

## Behavior contract (gate 3)

The name and sibling-uniqueness rules, one-implementation rule, catalogue and
abstract-type checks, containment multiplicity, depth limit, stack-guarded
sub-assembly expansion, static cycle detection and reachability sweep are
exercised by the gate 3 contract test:
scripts/test_e4008_assembly_instance_or_sub_assembly.py against
scripts/e4008_assembly_instance_or_sub_assembly_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e4008_assembly_instance_or_sub_assembly.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
