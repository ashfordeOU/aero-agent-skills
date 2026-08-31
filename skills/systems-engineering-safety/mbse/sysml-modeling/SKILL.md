---
name: sysml-modeling
description: "Use when you must create or check SysML models for model-based systems engineering in an aerospace program: select the right SysML diagram kind for each modeling purpose (block definition BDD, internal block IBD, parametric, requirement, activity, sequence, state machine, use case), draft block definition and internal block diagrams from the system structure, build requirements diagrams with traceability closure, set up parametric diagrams for constraint-based analysis, and judge model viewpoints complete or missing. Diagram choice follows the modeling purpose; requirements trace through design to verification, and model governance follows the mapped development guidance. Trigger: SysML, block definition diagram, BDD, internal block diagram, IBD, parametric diagram, requirements diagram, traceability."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: mbse
  tags: [sysml-modeling, sysml, block-definition-diagram, bdd, internal-block-diagram, ibd, parametric-diagram, requirements-diagram, traceability, mbse]
  version: 0.1.0
  author: AeroSkills
---

# SysML Modeling (systems-engineering-safety/mbse/sysml-modeling)

Use when the task is SysML diagram modeling for model-based systems
engineering: choosing diagram kinds, building block definition and
internal block diagrams, requirements traceability, parametric
constraint analysis, and model viewpoint coverage.

## Domain quick reference

- SysML diagram kinds: block definition (bdd), internal block (ibd),
  parametric (param), requirement (req), activity (act), sequence
  (seq), state machine (stm), use case (uc), and package (pkg) for
  model organization.
- Block definition diagram (bdd): declares block hierarchy, part
  types, value properties, and the system composition tree. Every
  element referenced by the model needs a definition among its parts.
- Internal block diagram (ibd): shows one block's internal structure:
  its parts, ports, and the connections (item flows) between them.
- Requirements diagram (req): captures requirements and their
  relationships (derive, satisfy, verify, refine, trace); traceability
  links each requirement through design to verification, and
  safety-critical items need full closure.
- Parametric diagram (param): binds constraint equations to block
  value properties so that analysis (mass, power, performance) runs
  on the model instead of in spreadsheets.
- Behavioral kinds: activity (functional flow), sequence (message
  ordering over time), state machine (modes and state transitions).
- Use case diagram (uc): actors, use cases, and the system boundary
  at the scoping stage.
- Viewpoints: structure, behavior, requirements, and parametric must
  all be covered for the model to be complete; a viewpoint that is
  absent is a gap, not a style choice.
- Model governance: models are configuration-managed artifacts of the
  development process (ARP4754A context); diagram content and
  traceability are reviewed like any other engineering data.

## Workflow

1. Identify the modeling purpose; select the diagram kind that matches
   it (structure, behavior, requirements, or analysis).
2. Draft the block definition diagram: enumerate the blocks, their
   parts, and the composition hierarchy.
3. Detail the internal block diagram for each composite block: parts,
   ports, and connections.
4. Capture requirements in a requirements diagram and link each
   requirement to the design elements that satisfy it; check
   traceability closure.
5. Add parametric diagrams for constraint-based analysis and bind the
   constraint equations to block value properties.
6. Add behavioral diagrams (activity, sequence, state machine) for
   functions, interactions, and modes as the model demands.
7. Check viewpoint coverage: structure, behavior, requirements,
   parametric all present; fix gaps.
8. Keep the model under configuration management and link it to the
   verification artifacts.

## Pitfalls

- Using a bdd when the question is about internal connections; that is
  an ibd concern.
- Referencing an element in a bdd that has no block definition; the
  model is invalid even if the diagram renders.
- Declaring traceability closed while a requirement has no satisfying
  design element.
- Skipping parametric diagrams and running analysis outside the model;
  the constraint links are lost.
- Treating an absent viewpoint as optional; a missing viewpoint is a
  model gap.
- Selecting the diagram by habit instead of by the modeling purpose.

## Behavior contract (gate 3)

The diagram-selection, block definition, traceability-closure, and
viewpoint logic is exercised by the gate 3 contract test:
scripts/test_sysml_modeling.py against scripts/sysml_modeling_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_sysml_modeling.py

## Compliance

- Standards referenced, not reproduced: ARP4754A text is proprietary
  (SAE); summary-only per standards-map.yaml and brief 06. SysML
  diagram semantics are common engineering knowledge.
- compliance: STANDARDS-REF, gated: false.
