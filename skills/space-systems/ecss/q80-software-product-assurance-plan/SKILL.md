---
name: q80-software-product-assurance-plan
description: "Draft and audit the software product assurance programme and its plan (SPAP) under ECSS-Q-ST-80C Rev.2: grade a plan against the Annex B outline with conditional sections switched on by scope, check the assurance organisation for a named lead, an independent reporting line and backed supplier delegation, check supplier flow-down and monitoring against the software category, grade methods and tools by their effect on the executable, and state the plan maturity owed at each review. Use when a supplier writes or updates its SPAP or a customer reviews one. Trigger: spap, software-product-assurance-plan, q80-spap-drd, spa-organisation-independence, software-supplier-flow-down, spa-tool-justification."
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
  tags: [ecss, q-st-80c, q80-software-product-assurance-plan, spap, software-product-assurance-plan, q80-spap-drd, spa-organisation-independence, software-supplier-flow-down, spa-tool-justification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Software Product Assurance Plan (space-systems/ecss/q80-software-product-assurance-plan)

Use when the task is the software product assurance (SPA) programme of
ECSS-Q-ST-80C Rev.2 (30 April 2025) and the plan that documents it, the
Software Product Assurance Plan (SPAP) defined by the document requirements
definition (DRD) in Annex B. The programme itself is clause 5: organisation
and responsibility, programme management, risk and critical items, supplier
selection and control, procurement, tools and supporting environment, and
process assessment and improvement.

## Domain quick reference

- The plan is where every other obligation is first promised. Its last
  section is a compliance matrix to the standard, so an incomplete plan
  makes an incomplete matrix before any work is done.
- The outline has fixed sections and conditional ones. Supplier control,
  operations and maintenance, security and reuse sections are owed only
  when the project has that scope; grading a plan without scope turned on
  either invents findings or misses real ones.
- A present section is not an answered section. A heading followed by two
  lines does not describe an organisation, a quality model or a metrics
  programme.
- Independence is about the reporting line. The assurance lead reports to
  the project manager, through the product assurance manager where there
  is one, never through the software development line, and never holds
  the development lead role at the same time.
- Delegating assurance tasks to a supplier is allowed only when the
  supplier's own plan is held and reviewed.
- Supplier control is proportionate: category, assurance requirements and
  the supplier's plan flow down in every case; the depth of monitoring
  rises with the category.
- A tool matters by what it can do to the product. A generator or compiler
  can put a defect into the executable; a verification tool can hide one.
  Those need qualification evidence for categories A and B; a documentation
  tool needs only its justification.
- The plan is issued for the system requirements review (SRR), updated for
  the preliminary and critical design reviews (PDR, CDR) and maintained
  through qualification (QR), acceptance (AR) and operational readiness
  (ORR).

## Workflow

1. Fix the scope: suppliers, operations and maintenance, security
   sensitivity, reuse. Each switches a conditional section on.
2. Grade the draft against the outline: missing sections, thin sections,
   sections not owed, and ids that are not in the outline at all.
3. Check the organisation: named lead, reporting line, dual roles,
   delegation backed by supplier plans.
4. Check each supplier: category and requirements flowed down, plan
   received, pre-award assessment, monitoring depth for the category.
5. Grade the methods and tools against the category.
6. State the maturity the plan owes at the next review and list what must
   change to reach it.

## Pitfalls

- Grading against the full outline regardless of scope.
- Accepting an organisation chart as independence. The line of report is
  what is checked, not the box the lead sits in.
- Letting a supplier's category be lower than the product it feeds
  without a recorded justification.
- Justifying a code generator by popularity. Its effect on the executable
  decides what evidence it needs.
- Leaving the compliance matrix section for last. It is the section the
  customer reads first.

## Stop gate: human sign-off required

The agent drafts; it does not decide. Stop and hand the draft to a named
human before any of these leave the working folder:

- The SPAP, or any update of it, submitted to the customer.
- The statement of the assurance organisation and the independence of the
  assurance lead.
- Any delegation of assurance tasks to a supplier, and any tool
  qualification argument.

Mark every such output as a draft, list the open questions for the
reviewer, and end with the line: STOP: human sign-off required before
submission.

## Behavior contract (gate 3)

The section id normalisation, the outline with its conditional sections,
the plan grading with missing, thin and not-owed sections and a coverage
fraction, the organisation and independence findings, the supplier
flow-down and monitoring check, the tool grading by impact and category and
the plan maturity per review are exercised by the gate 3 contract test:
scripts/test_q80_software_product_assurance_plan.py against
scripts/q80_software_product_assurance_plan_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q80_software_product_assurance_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite ECSS-Q-ST-80C Rev.2
  (30 April 2025) as the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
