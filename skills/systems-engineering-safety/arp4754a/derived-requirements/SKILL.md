---
name: derived-requirements
description: "Use when you must identify, classify, and manage derived requirements per ARP4754A: decide whether a requirement is derived or allocated from its traceability fields, list the required rationale fields (design decision, implementation constraint, interface resolution, architectural choice, environmental assumption) plus the derivation rationale and impact analysis, and run the validation checklist before the requirement enters the requirements baseline. Derived requirements are not directly traceable to a parent requirement or source document; they arise from design choices and need their own justification and traceability path. Trigger: derived requirements, derivation rationale, impact analysis, derivation source, design decision, implementation constraint, interface resolution."
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
  subdomain: arp4754a
  tags: [derived-requirements, derivation-rationale, derivation-source, impact-analysis, requirements-baseline, design-decision]
  version: 0.1.0
  author: AeroSkills
---

# ARP4754A Derived Requirements (systems-engineering-safety/arp4754a/derived-requirements)

Use when the task is derived requirements per ARP4754A: deciding
whether a requirement is derived or allocated, recording the
derivation rationale and impact analysis, and running the validation
checklist before the requirement enters the requirements baseline.

## Domain quick reference

- A derived requirement is a requirement whose content is not directly
  traceable to a parent requirement or to a source document (customer
  requirement, regulation, system requirement). It arises during the
  development process itself.
- Allocated requirements trace up to a parent or source; derived
  requirements have no such upward trace and must carry their own
  justification.
- Derivation sources are: design decision, implementation constraint,
  interface resolution, architectural choice, environmental assumption.
- Each derived requirement must record a derivation source, the
  derivation rationale (why the requirement exists), and an impact
  analysis (which requirements, designs, or plans it affects).
- Derived requirements join validation and verification planning and
  the requirements traceability matrix with the same rigor as allocated
  requirements, plus the extra rationale path.

Worked example: a low-level requirement states "the backup power unit
shall maintain 28 VDC output for 30 minutes after primary power loss."
No high-level requirement or source document states this; the content
came from a design decision on the power architecture. Classified as
derived, source = design decision, rationale = the backup unit must
cover the full diversion duration, impact = the electrical load
analysis and the verification plan.

## Workflow

1. For each requirement, read the traceability fields: has parent
   trace, has source document trace, and any derivation source.
2. Classify: a requirement with a parent trace or a source document
   trace is allocated; a requirement with neither is derived.
3. For a derived requirement, record the derivation source from the
   five categories plus the derivation rationale and the impact
   analysis.
4. Run the validation checklist; every derived requirement must carry
   all three rationale fields or it fails.
5. Carry the derived requirement into validation, verification
   planning, and the traceability matrix with its rationale attached.

## Pitfalls

- Treating "not in the original requirements document" as derived: a
  requirement traced to any parent or source is allocated even when it
  appears late.
- Confusing with requirements-allocation: allocation assigns
  requirements to items and functions; derivation explains where a
  requirement came from. An unallocated requirement is not the same as
  a derived one.
- Confusing with requirements-traceability: traceability maps links
  between levels and flags derived requirements; this leaf classifies
  and justifies them. Traceability records the flag, derivation records
  the why.
- Confusing with validation: validation confirms the requirement set is
  correct and complete for the intended function. Derivation rationale
  does not validate the requirement; both run in parallel.
- Confusing with verification-planning: verification plans show the
  requirement is met. A derived requirement still needs a verification
  method; its rationale is not evidence of satisfaction.
- Confusing with functional-hazard-assessment: FHA identifies failure
  conditions and severities; a derived safety requirement may follow
  from FHA results, but FHA is a source, not a classification of the
  requirement.
- Dropping the impact analysis: a derived requirement that changes one
  design often changes several; an impact analysis missing its targets
  is an incomplete rationale.

## Behavior contract (gate 3)

The logic is exercised by the gate 3 contract test:
scripts/test_derived_requirements.py against
scripts/derived_requirements_logic.py (stdlib unittest, offline).
Run: python3 skills/systems-engineering-safety/arp4754a/derived-requirements/scripts/test_derived_requirements.py

## Compliance

- Standards referenced, not reproduced: ARP4754A text is proprietary
  (SAE); summary-only per standards-map.yaml and brief 06.
- Revision note: ARP4754B (2023) supersedes ARP4754A; this skill keys
  to ARP4754A as the certification-baseline revision (FAA AC 20-174
  cites A); see standards-map.yaml arp4754a.revision_decision.
- compliance: STANDARDS-REF, gated: false.
