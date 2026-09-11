---
name: e1011-hfe-role
description: "Use when define the Human Factors Engineering (HFE) role in a space-systems project under ECSS-E-ST-10-11C §4.3.1–4.3.2: identify required HFE task categories (requirements definition, task analysis, design support, human-machine interface definition, verification and validation, design-review participation), assign each task to a lifecycle phase, and verify that formal interfaces are established with Systems Engineering, Safety, Operations, Training, and Software Engineering. Flag any task category missing from the role definition, any mandatory interface discipline absent, and any lifecycle phase with no HFE task assigned. Trigger: ecss, e-st-10-11c, e-st-10-system-scope, hfe-role, human-factors-engineering, hfe-interface, hfe-tasks, lifecycle-phase."
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
  tags: [ecss, e-st-10-11c, e-st-10-system-scope, hfe-role, human-factors-engineering, hfe-interface, hfe-tasks, lifecycle-phase]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — HFE Role in Project (space-systems/ecss/e1011-hfe-role)

Use when the task is to define and verify the Human Factors Engineering (HFE)
role within a space-systems project, covering the HFE function task set
(ECSS-E-ST-10-11C §4.3.1) and the formal discipline interfaces the HFE
function must maintain (§4.3.2).

## Domain quick reference

- §4.3.1 specifies that the project must establish an HFE function with a
  defined task set spanning the full lifecycle. The required HFE task
  categories are: **requirements definition** (capture and flow-down of
  human factors requirements), **task analysis** (decomposing operator and
  crew tasks to identify human performance constraints), **design support**
  (contributing HFE inputs at each design step), **human-machine interface
  (HMI) definition** (specifying the interface between human and system
  elements), **verification and validation** (confirming HFE requirements
  are met by the design), and **design-review participation** (HFE
  representation at project review gates). Every category must be covered;
  a gap means the HFE function is incomplete.

- §4.3.2 requires the HFE function to maintain formal, documented interfaces
  with five disciplines: **Systems Engineering** (for requirements flow-down
  and architectural trades involving human performance), **Safety** (for
  hazard analyses that involve human actions or human error), **Operations**
  (for operational concept and procedure inputs before the design is fixed),
  **Training** (for early training-needs analysis so hardware supports
  learnability), and **Software Engineering** (for human-machine interface
  software design). Each interface must name a responsible contact and
  specify at least one concrete output exchanged.

- Lifecycle scope: ECSS phases 0, A, B, C, D, and E. HFE tasks must be
  assigned to phases; a phase with no HFE task is a coverage gap regardless
  of whether HFE activity is planned later, because the project plan drives
  resource commitment and review evidence.

## Workflow

1. Obtain the project's HFE role definition document (HFE management plan
   or equivalent). Extract the list of HFE task categories stated as
   assigned to the project.
2. Compare the extracted categories against the six required categories
   (requirements definition, task analysis, design support, HMI definition,
   verification and validation, design-review participation). For each
   missing category, raise a finding: the HFE role definition is incomplete
   until the category is added and assigned to at least one lifecycle phase.
3. For each stated HFE task, confirm it is assigned to a named lifecycle
   phase (phase 0 through E). Flag any task without a phase and any phase
   (0 through E) that has no HFE task assigned.
4. Obtain the project's interface matrix or equivalent. For each of the five
   required interface disciplines (Systems Engineering, Safety, Operations,
   Training, Software Engineering), check that a record exists naming a
   responsible contact and at least one documented output (requirement,
   analysis result, review comment, or agreed input). Flag absent disciplines
   and records with no outputs.
5. Validate each interface record individually: the discipline name must be
   present, a contact must be named, and the outputs list must be non-empty.
   An interface record that fails any of these checks is incomplete.
6. Aggregate all findings across task-category gaps, phase-coverage gaps,
   missing interface disciplines, and incomplete interface records. Compute
   a completeness score as the fraction of mandatory checks passed. The HFE
   role definition is not accepted until all findings are resolved.

## Pitfalls

- Treating "design support" and "design-review participation" as a single
  category — §4.3.1 keeps them separate. Design support is continuous
  contribution to the design process; design-review participation is formal
  representation at gate reviews. Merging them hides whether one or the
  other is actually being performed.
- Recording interfaces at project close rather than at the start of phase A —
  the interfaces are needed to shape the design, not to document what
  happened. An interface established after detailed design is locked cannot
  influence the result and does not satisfy §4.3.2.
- Leaving the "training" interface to the training team's schedule — HFE must
  engage Training early (phase A/B) to feed learnability constraints into the
  design. If Training is listed as an interface but the first exchange happens
  in phase D, the interface is nominal only.
- Assigning all HFE tasks to a single lifecycle phase (typically phase C) —
  HFE requirements definition must precede design, so phase 0/A engagement is
  mandatory. A plan that shows HFE work only in phase C will miss the
  requirements influence window entirely.
- Accepting an interface record with no outputs — an interface that specifies
  only a contact name but no deliverable or exchange document is
  unverifiable. The outputs field is the evidence that the interface is real.

## Behavior contract (gate 3)

The HFE task-category validation, lifecycle phase coverage, and interface
record checks are exercised by the gate 3 contract test:
scripts/test_e1011_hfe_role.py against scripts/e1011_hfe_role_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1011_hfe_role.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
