---
name: e1011-hfe-req-process
description: "Use when manage the HFE requirements process for a space system under ECSS-E-ST-10-11C §4.6.1–4.6.2: capture each human factors engineering requirement with a non-empty source identifier, categorize it by type (functional, performance, environmental, safety, anthropometric), allocate it to one or more system elements (hardware, software, procedure, training), and verify bidirectional traceability from source to requirement and from requirement to implementing element. Flag any requirement missing its upstream source trace, any requirement in an allocation-required lifecycle state with no assigned implementing element, and any element of an unrecognized type. Track lifecycle status through proposed, approved, allocated, implemented, verified, and closed. Trigger: ecss, e-st-10-11c, hfe, human-factors-engineering, hfe-requirements, requirements-process, traceability, allocation."
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
  tags: [ecss, e-st-10-11c, hfe, human-factors-engineering, hfe-requirements, requirements-process, traceability, allocation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — HFE Requirements Process (space-systems/ecss/e1011-hfe-req-process)

Use when the task is managing the HFE requirements process under
ECSS-E-ST-10-11C §4.6.1–4.6.2 — capturing each human factors
engineering requirement with a traceable source, categorizing it by
type, allocating it to system elements, and verifying bidirectional
traceability and allocation completeness throughout the requirement
lifecycle.

## Domain quick reference

- §4.6.1 covers HFE requirements capture: each requirement originates
  from a documented source — a regulatory obligation, contractual
  requirement, operational concept item, or derived context-of-use
  finding. The source identifier is the upstream trace anchor. HFE
  requirements fall into five types: functional (a capability the
  human must be able to perform), performance (a measurable quality of
  the human-system interaction, e.g., task completion time or error
  rate), environmental (a constraint on the physical environment
  affecting human performance — lighting, noise, vibration, thermal),
  safety (a safety-critical HFE control — emergency access, critical
  control placement), and anthropometric (a dimensional constraint
  derived from human body-size ranges).
- §4.6.2 covers HFE requirements allocation and traceability: each
  captured requirement is allocated to one or more system elements —
  hardware (physical controls, displays, workstations), software (user
  interface logic, alarm presentation, display content), procedure
  (operational and maintenance procedures), or training (training
  material content). Bidirectional traceability is mandatory: the
  upstream trace links the requirement to its source, and the
  downstream trace links it to its implementing element or elements. A
  requirement that has advanced past the approved state but carries no
  allocated element is a process gap, not a compliance pass.
- Lifecycle status moves through: proposed → approved → allocated →
  implemented → verified → closed. The transitions from allocated
  onward require allocation to be complete before advancement is valid.

## Workflow

1. Capture each HFE requirement, recording a non-empty source
   identifier (upstream trace anchor). Reject a requirement with no
   source identifier before it enters the requirements register.
2. Categorize each requirement into one of the five recognized types
   (functional, performance, environmental, safety, anthropometric).
   Reject an unrecognized type before the requirement is registered.
3. Confirm the lifecycle status is a recognized value (proposed,
   approved, allocated, implemented, verified, closed). Reject an
   unrecognized status.
4. For each requirement in the allocated, implemented, verified, or
   closed lifecycle states, confirm that at least one implementing
   element has been assigned. Flag any requirement in these states with
   no allocated elements as an allocation gap.
5. For each allocated element, confirm the element type is one of the
   four recognized categories (hardware, software, procedure,
   training). Flag any element with an unrecognized type as an
   allocation-integrity finding.
6. Aggregate traceability and allocation findings per requirement. A
   requirement is fully compliant with the HFE requirements process
   only when both finding lists are empty.

## Pitfalls

- Treating a requirement with no source identifier as informally
  traceable because the engineering team knows its origin — the source
  identifier must be recorded explicitly; verbal traceability is not
  verifiable and is itself a finding.
- Advancing a requirement from approved to allocated status without
  actually linking it to an implementing element — the status label
  does not substitute for the allocation record.
- Accepting an unrecognized element type on the assumption that it
  will be rationalized later — the type must be validated at
  allocation time, not at closure.
- Treating requirements at proposed status as not yet subject to
  source-traceability — a source identifier is required from initial
  capture, not deferred to approval.
- Conflating allocation with verification — allocation records that an
  implementing element is responsible for the requirement, not that
  the requirement has been satisfied and verified.

## Behavior contract (gate 3)

The requirement categorization, lifecycle status validation,
traceability check, and allocation check logic is exercised by the
gate 3 contract test: scripts/test_e1011_hfe_req_process.py against
scripts/e1011_hfe_req_process_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_hfe_req_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
