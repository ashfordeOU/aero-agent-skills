---
name: fracture-control-plan
description: "Use when prepare or review a fracture control plan for a spacecraft or launch vehicle structure per ECSS-E-ST-32C DRD Annex F clause 5.2: inventory all structural items and categorize each as fracture-critical (FC) or non-fracture-critical (NFC) based on the failure consequence of fracture, verify the plan contains all required sections (part inventory, criticality rationale, NDE requirements, safe-life or fail-safe life approach, verification methods, approval authority, and update triggers), confirm that FC items carry complete NDE and verification records, determine whether a design or material change triggers a mandatory plan update, and verify that plan approval signatures are present at the required authority level. Aggregate all findings into an overall plan-completeness verdict. Trigger: ecss, e-st-32c, fracture-control-plan, fracture-critical, safe-life, fail-safe, nde-requirements, plan-approval, e-st-32-structures-scope."
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
  tags: [ecss, e-st-32c, fracture-control-plan, fracture-critical, safe-life, fail-safe, nde-requirements, plan-approval, e-st-32-structures-scope]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fracture Control Plan (space-systems/ecss/fracture-control-plan)

Use when the task is to prepare or review a Fracture Control Plan (FCP) for a
spacecraft or launch vehicle structural program per ECSS-E-ST-32C DRD Annex F,
clause 5.2 — inventorying structural items, establishing fracture criticality for
each one, verifying the plan document contains all required elements, and
confirming the plan has been approved and is kept current with design evolution.

## Domain quick reference

- ECSS-E-ST-32C DRD Annex F defines the content requirements for a Fracture
  Control Plan. The plan is the governing document that identifies which parts
  require fracture control treatment and prescribes the methods by which that
  treatment is verified throughout the program lifecycle.
- Each structural item is categorized as fracture-critical (FC) or
  non-fracture-critical (NFC) based on the failure consequence of a fracture
  event. Items whose fracture failure could lead to catastrophic or critical
  consequences (loss of mission, loss of spacecraft, loss of crew, or
  uncontrolled release of a pressurized system) are categorized as FC. Items
  with marginal or negligible failure consequences are categorized as NFC and
  require no fracture control treatment beyond the categorization rationale.
- For each FC item the plan must specify: the non-destructive evaluation (NDE)
  method and its detection limit, the life management approach (safe-life,
  fail-safe, or damage-tolerant), the verification method (analysis, test, or
  analysis-and-test), and the design life in cycles or hours.
- The plan is a living document. Mandatory update triggers include design
  changes to an FC item, material substitutions on FC items, any upward revision
  to design loads, new findings that re-categorize an NFC item to FC, and
  in-service inspection findings that reveal crack-like indications.
- Plan approval requires signatures at project engineer level, fracture control
  authority level, and customer acceptance. All three must be present before the
  plan is considered conforming.

## Workflow

1. Compile the structural item inventory. For every load-carrying part in the
   structure, record its part identifier, function, and the failure consequence
   that would result if the part fractured. This inventory is the anchor of the
   plan; missing items cannot be controlled.
2. Categorize each item as FC or NFC based on its failure consequence.
   Catastrophic and critical consequences map to FC; marginal and negligible
   consequences map to NFC. Document the rationale for every designation — an
   undocumented NFC designation is itself a finding.
3. For each FC item, define the four required engineering parameters:
   (a) NDE method and its detection limit in mm (the assumed initial flaw size
   must be at or above this limit to remain conservative); (b) life management
   approach (safe-life, fail-safe, or damage-tolerant); (c) verification method
   (analysis, test, or both); (d) design life in cycles or flight hours.
   Reject any FC item record that is missing any of these four parameters.
4. Verify that the plan document contains all seven required sections: part
   inventory, fracture criticality rationale, NDE requirements, life approach,
   verification methods, approval authority, and update triggers. A plan
   document that omits any required section is incomplete regardless of the
   quality of its FC item records.
5. Check plan approval: confirm that the project engineer, the fracture control
   authority, and the customer have all signed or accepted the plan. An unsigned
   plan is not in force even if technically complete.
6. Evaluate any pending changes against the mandatory update trigger list.
   Design changes, material changes, load increases, new FC findings, and
   inspection findings all mandate a plan revision before the affected item
   is returned to service. Record which change type triggered the update and
   confirm a revised plan has been issued.
7. Aggregate all findings. The plan is conforming only when: all required
   sections are present, all FC items have complete records, all approval
   signatures are in place, and no pending mandatory update is outstanding.

## Pitfalls

- Treating the fracture criticality categorization as a one-time activity at
  PDR and not revisiting it after design changes. A geometry or material change
  can alter the failure consequence, promoting an NFC item to FC or, less
  commonly, allowing a previously FC item to be re-evaluated.
- Setting the assumed initial flaw size below the NDE detection limit for the
  chosen inspection method. The plan must use a flaw size that the NDE can
  actually find; a smaller assumed flaw makes the analysis non-conservative.
- Recording the life management approach without also recording the design life
  and verification method. All three are needed together — a safe-life approach
  without a verified design life number provides no actual assurance.
- Issuing the plan with an incomplete approval record and treating the
  technical content as equivalent to a conforming plan. Without all three
  signatories the plan is not in force under the standard's requirements.
- Failing to update the plan when an in-service inspection returns a
  crack-like indication. The indication may require re-categorization or a
  revised NDE detection limit, and the plan must be updated before the
  structure is cleared for continued service.

## Behavior contract (gate 3)

The part categorization, FC item completeness, plan section coverage, approval
status, update trigger assessment, and full plan aggregation logic is exercised
by the gate 3 contract test:
scripts/test_fracture_control_plan.py against
scripts/fracture_control_plan_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fracture_control_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
