---
name: systems-engineering
description: "Use when running model-based systems engineering for an aerospace program: sequence the modeling workflow (requirements modeling, functional and logical architecture, allocation, analysis, traceability), check that every function is allocated to a design element, verify traceability closure (full for safety-critical items), and map modeling tasks to open-source toolchains such as Capella, OSATE, and Papyrus. Models are the primary artifacts; the systems engineering process follows the mapped guidance. Trigger: MBSE, model-based systems engineering, SysML, architecture modeling, functional architecture, allocation, digital thread, Capella, OSATE."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: mbse
  tags: [mbse, sysml, architecture, modeling, capella, osate, digital-thread, allocation]
  version: 0.1.0
  author: AeroSkills
---

# MBSE Systems Engineering (systems-engineering-safety/mbse/systems-engineering)

Use when the task is model-based systems engineering: building and
checking the model workflow, allocation, and traceability for an
aerospace program.

## Domain quick reference

- MBSE executes systems engineering with models as the primary
  artifacts: requirements against functional and logical
  architecture, functions allocated to design elements, analysis run
  on the architecture.
- The mapped systems-engineering guidance (ARP4754A) governs the
  development process; MBSE is a means of executing it.
- Traceability links each requirement through design to its
  verification; safety-critical items need full closure.
- Open-source toolchains: Capella (functional architecture), OSATE
  (AADL architecture analysis), Papyrus (SysML modeling).

## Workflow

1. Model the requirements against the functional architecture.
2. Build the logical architecture and allocate functions to design
   elements.
3. Run analysis (safety, performance) on the architecture.
4. Verify traceability closure; full closure for safety-critical
   items.
5. Keep the model under configuration management and link it to the
   verification artifacts (digital thread).

## Pitfalls

- Functions left unallocated while the model is declared closed.
- Safety-critical items with traceability gaps.
- Analysis skipped because the architecture is only diagrammed.
- Tool choice driven by habit instead of the modeling task.

## Behavior contract (gate 3)

The workflow, allocation, traceability, and toolchain logic is
exercised by the gate 3 contract test: scripts/test_mbse.py against
scripts/mbse_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_mbse.py

## Compliance

- Standards referenced, not reproduced: ARP4754A / ARP4761A text is
  proprietary (SAE); summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.
