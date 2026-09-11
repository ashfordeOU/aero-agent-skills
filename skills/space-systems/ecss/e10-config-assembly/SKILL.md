---
name: e10-config-assembly
description: "Use when determining the physical and functional grouping rules that govern how configuration items are assembled for integration under ECSS-E-ST-10C clause 5.4.2.3: check every pair of configuration items proposed for one physical assembly for mounting-zone match, hazard separation between energetic and non-energetic items, and EMI role conflict between a sensitive and an emitting item; flag a functional grouping conflict when items sharing a function group are physically incompatible; account each assembly's total mass against its allocable mass budget; and derive a dependency-ordered integration sequence across assemblies. Trigger: ecss, e-st-10c, configuration assembly, configuration item grouping, physical grouping rules, functional grouping rules, integration sequence, mass budget, hazard separation, emi conflict."
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
  tags: [ecss, e-st-10c, config-assembly, configuration-items, integration-sequence, mass-budget, hazard-separation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Configuration Assembly Constraints (space-systems/ecss/e10-config-assembly)

Use when the task is capturing the configuration assembly constraints
of ECSS-E-ST-10C clause 5.4.2.3 -- checking the physical and
functional grouping rules that decide which configuration items (CIs)
may be integrated into the same physical assembly, accounting each
assembly's mass against its budget, and deriving the integration
sequence across assemblies from their functional dependencies.

## Domain quick reference

- Clause 5.4.2.3 requires that CIs proposed for one physical assembly
  satisfy a physical rule set before integration: a shared mounting
  zone/interface, hazard separation between an energetic item (e.g.
  a pyrotechnic device) and a non-energetic item, and no EMI role
  conflict between an EMI-sensitive item and an EMI-emitting item.
  Two neutral, same-zone, non-hazardous items are always physically
  compatible.
- A separate functional rule set groups CIs that belong to the same
  function group -- they are expected to integrate together. When a
  functional grouping expectation collides with a physical rule (the
  CIs share a function group but fail a physical check), that is a
  functional grouping conflict: the functional expectation cannot be
  honored as-is and the assembly plan must change, not the check.
- Each physical assembly carries an allocable mass budget; the total
  mass of every CI assigned to it must not exceed that budget. An
  assembly with no budget on record is itself a finding -- the
  requirement was never captured, not a pass by default.
- Assemblies with a functional dependency between them (one must be
  integrated before another) must be sequenced in that order; a cycle
  in the dependency set means no valid integration sequence exists and
  the dependency capture itself is wrong.

## Workflow

1. Inventory every configuration item proposed for a given physical
   assembly, with its mounting zone, hazard class (energetic or
   none), EMI role (sensitive, emitter, or neutral), mass, and
   function group (or none). Reject a CI record missing a required
   attribute or carrying an unrecognized hazard class or EMI role.
2. For every pair of CIs in the assembly, check physical
   compatibility: flag a mounting-zone mismatch, flag hazard
   separation when exactly one of the pair is energetic, and flag an
   EMI conflict when one is sensitive and the other is an emitter.
3. For every pair sharing a function group, check whether the
   physical compatibility check for that pair failed; if so, record a
   functional grouping conflict distinct from the physical finding.
4. Sum the mass of every CI in the assembly and compare it to the
   assembly's allocable mass budget; flag an exceedance, and
   separately flag an assembly with no budget captured.
5. Aggregate the pairwise findings and the mass finding per assembly;
   the assembly is not integration-ready until both are clear.
6. Across assemblies with a captured functional dependency (one
   assembly must integrate before another), derive the integration
   sequence by dependency order; a cycle means the dependency capture
   must be corrected before a sequence can be produced.

## Pitfalls

- Treating a mounting-zone match alone as sufficient for physical
  compatibility -- hazard separation and EMI role conflicts are
  independent checks and must all clear, not just the zone match.
- Resolving a functional grouping conflict by dropping the physical
  finding instead of flagging both -- the functional expectation does
  not override a hazard-separation or EMI-conflict requirement.
- Leaving an assembly's mass budget unset and reading "no exceedance"
  as compliant -- an unset budget means the requirement was never
  captured, which is itself a finding.
- Picking an arbitrary integration order when assemblies have no
  captured dependency between them -- absence of a dependency is not
  itself a constraint violation, but a captured dependency cycle is
  and must be corrected, not worked around by re-ordering silently.

## Behavior contract (gate 3)

The physical-compatibility, functional-grouping-conflict,
mass-budget, and integration-sequence logic is exercised by the gate
3 contract test: scripts/test_e10_config_assembly.py against
scripts/e10_config_assembly_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_config_assembly.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
