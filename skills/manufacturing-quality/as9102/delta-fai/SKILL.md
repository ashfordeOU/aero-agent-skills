---
name: delta-fai
description: "Use when you must classify a change and determine the AS9102 delta first article inspection (delta FAI) scope: classify part number, material, process, tooling, drawing revision, location, or supplier changes as full new FAI, delta FAI, or no FAI, then scope the affected forms 1, 2, and 3 and the affected characteristics for the delta. Determine whether a full new FAI is required or a delta FAI suffices, and produce the change classification, the delta scope forms, and the affected characteristic list. Trigger: delta fai, change classification, full new fai, delta first article, material change, process change, tooling change, drawing revision."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9102
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9102
  tags: [delta-fai, change-classification, as9102, full-new-fai, material-change, process-change, tooling-change, drawing-revision]
  version: 0.1.0
  author: Aero Agent Skills
---

# Delta First Article Inspection (manufacturing-quality/as9102/delta-fai)

Use when a change to the article needs change classification and delta
first article inspection scoping: full new FAI, delta FAI, or no FAI,
with the affected forms and the affected characteristics.

## Domain quick reference

- AS9102, published by IAQG and SAE, is the aerospace first article
  inspection standard; the FAI report has form 1 part accountability,
  form 2 material and special processes, and form 3 characteristic
  accountability.
- Following a change, the organization evaluates whether a full new
  FAI, a delta FAI, or no FAI applies; this evaluation is a paraphrase
  of AS9102 change practice, and the standard text is proprietary.
- A part number change or a material change normally calls for a full
  new FAI.
- A process, tooling, drawing revision, location, or supplier change
  normally calls for a delta FAI scoped to the affected forms.
- The delta form scope follows the change type: material or process
  affects forms 1 and 2, tooling or drawing revision affects forms 1
  and 3, location or supplier affects form 1.
- The delta FAI covers only the affected characteristics, so the
  organization lists exactly the characteristics the change touches.

## Workflow

1. Collect the change: change type (part number, material, process,
   tooling, drawing revision, location, supplier, or none) and
   description.
2. Classify the change with classify_change.
3. Determine whether a full new FAI is required with
   verify_full_fai_needed.
4. For delta FAI cases, scope the delta with scope_delta_fai: pass the
   change and the affected characteristics.
5. Confirm the returned forms and characteristics against the change.

## Pitfalls

- Classifying a part number change as a delta FAI (a new part number
  normally needs a full new FAI).
- Scoping a material change to form 3 only (material affects forms 1
  and 2).
- Dropping form 1 from the delta scope (part accountability is always
  in scope).
- Treating the rule table as standard text (it is a practical
  paraphrase; the AS9102 wording is proprietary).

## Behavior contract (gate 3)

The classification and scoping logic is exercised by the gate 3
contract test: scripts/test_delta_fai_logic.py against
scripts/delta_fai_logic.py (stdlib unittest, offline). The module is a
decision table with no physical quantities, so it defines no units.
Run:
python3 scripts/test_delta_fai_logic.py

## Compliance

- AS9102 is proprietary (IAQG/SAE): name plus paraphrase only, per
  standards-map.yaml; no form layouts or clause text are reproduced.
- compliance: STANDARDS-REF, gated: false.
