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
clauses:
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.1.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.1.2.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.1.2.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.1.2.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.1.3.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.1.3.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.1.4.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.1.4.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.1.5.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.1.5.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.1.5.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.1.5.4
    items: [a, b]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.1.1
    items: [a, b]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.1.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.1.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.1.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.1.5
    items: [a, b]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.7.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.2.7.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.3.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.6.1.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.6.1.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.6.1.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.6.2.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.6.2.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.6.2.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.7.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.7.2.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.7.2.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.7.2.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.7.2.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.7.3.1
    items: [a, b]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.7.3.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.7.3.3
    items: [a]
    relation: verifies
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
2. Grade the draft with `assess_spap` against the Annex B outline:
   missing sections, thin sections, sections not owed, and ids that are
   not in the outline at all. The plan answers the project's assurance
   requirements, and may stand alone or be a section of the supplier's
   overall product assurance plan. Every internal manual, standard or
   procedure it refers to counts as part of the programme and has to be
   available to the reviewer.
3. Check the organisation with `check_organisation`: an organisation for
   software development in which each person has defined tasks; the
   responsibility, authority and working relations of everyone who
   manages, does or checks work that affects software quality, written
   down; the responsibilities and interfaces of every internal and
   external organisation on the project, written down; and enough
   resources for the assurance tasks.
4. Check the assurance lead: a named person; answering to the project
   manager, via the product assurance manager where there is one,
   never through the development line; with the authority and
   independence to set up and sustain the assurance programme; with direct
   access to higher management when needed. Audits and reviews, of
   both products and processes, are done by people who did not do the work.
5. Check any delegation of assurance work to a lower-tier supplier: it
   is documented and controlled, backed by that supplier's own plan held
   and reviewed, and the plan states that responsibility to the customer
   stays with this supplier.
6. Check each supplier with `check_supplier_control`: category and
   requirements flowed down, plan received, pre-award assessment,
   monitoring depth for the category.
7. Check staffing and training: the project requirements were reviewed
   early enough to acquire or build the skills needed, in a training plan;
   training subjects follow from the tools, techniques, methods and
   computers actually used; the people on each planned task have the right
   mix of skills and training by the time the task starts; that training
   covers security analysis and audit, security engineering, security
   assurance methods and tools, and the project's own security rules and
   procedures; and training records are kept.
8. Check the quality model: the software quality requirements are
   specified through one, built on functionality, reliability,
   maintainability, reusability, suitability for safety, security,
   usability, efficiency, portability and development effectiveness.
9. Check the plan links software risks into the project risk policy of
   ECSS-M-ST-80 rather than running a separate register, holds an audit
   plan and schedule run as the general quality assurance standard
   ECSS-Q-ST-10 sets out for audits, and handles software alerts through
   that same standard's alert process.
10. Grade the methods and tools with `assess_tools` against the category.
    The methods and tools for every development activity, from
    requirements analysis and modelling through coding and testing to
    configuration management, verification and assurance, are proposed by
    the supplier and accepted by the customer. Each choice is justified by a
    test or a written assessment showing the team is experienced or
    trained in it, that it suits the product's function and operation,
    that it will stay available through development and maintenance, and
    that it suits the product's security sensitivity. Their correct use is
    checked and reported.
11. Check the development environment: chosen against availability,
    compatibility, performance, maintenance, durability and consistency
    with the operational equipment, the category and the security
    sensitivity, the security regulations that apply, support
    documentation, acceptance and warranty, installation and training,
    maintenance and evolution, copyright, and dependence on one vendor;
    its fitness justified in writing; and its availability to the
    developers confirmed before each phase starts.
12. Check process assessment and improvement: how capable the
    processes in use are, including those that units outside the team
    provide, is monitored and controlled; each assessment has a documented
    model and method conforming to ISO/IEC 33002:2015, a model, method,
    scope, results and assessors that the customer set or recognised and
    that were checked against the project requirements, and a competent
    assessor. Results feed back into the processes, into where the
    project is heading and into technology needs; earlier results are used;
    improvement follows a documented improvement process; and the
    improvement is shown with evidence.
13. Check the compliance matrix delivered with the plan: one row per
    applicable assurance requirement, and for each a reference to the
    document holding its expected output.
14. State the maturity the plan owes at the next review with
    `plan_maturity_due` and list what must change to reach it. The plan
    is revised at every milestone so the next phase's work is fully
    defined, and before the acceptance review it is extended with the
    quality measures for operations and maintenance, or a separate plan
    for them is issued.

## Obligations

| Item | Step |
|---|---|
| ECSS-Q-ST-80C Rev.2 5.1.1a | 3 |
| ECSS-Q-ST-80C Rev.2 5.1.2.1a | 3 |
| ECSS-Q-ST-80C Rev.2 5.1.2.2a | 3 |
| ECSS-Q-ST-80C Rev.2 5.1.2.3a | 5 |
| ECSS-Q-ST-80C Rev.2 5.1.3.1a | 3 |
| ECSS-Q-ST-80C Rev.2 5.1.3.2a | 4 |
| ECSS-Q-ST-80C Rev.2 5.1.4.1a | 4 |
| ECSS-Q-ST-80C Rev.2 5.1.4.2a | 4 |
| ECSS-Q-ST-80C Rev.2 5.1.5.1a | 7 |
| ECSS-Q-ST-80C Rev.2 5.1.5.2a | 7 |
| ECSS-Q-ST-80C Rev.2 5.1.5.3a | 7 |
| ECSS-Q-ST-80C Rev.2 5.1.5.4a | 7 |
| ECSS-Q-ST-80C Rev.2 5.1.5.4b | 7 |
| ECSS-Q-ST-80C Rev.2 5.2.1.1a | 2 |
| ECSS-Q-ST-80C Rev.2 5.2.1.1b | 2 |
| ECSS-Q-ST-80C Rev.2 5.2.1.2a | 2 |
| ECSS-Q-ST-80C Rev.2 5.2.1.3a | 14 |
| ECSS-Q-ST-80C Rev.2 5.2.1.4a | 14 |
| ECSS-Q-ST-80C Rev.2 5.2.1.5a | 13 |
| ECSS-Q-ST-80C Rev.2 5.2.1.5b | 13 |
| ECSS-Q-ST-80C Rev.2 5.2.3a | 9 |
| ECSS-Q-ST-80C Rev.2 5.2.4a | 9 |
| ECSS-Q-ST-80C Rev.2 5.2.7.1a | 8 |
| ECSS-Q-ST-80C Rev.2 5.2.7.2a | 8 |
| ECSS-Q-ST-80C Rev.2 5.3.1a | 9 |
| ECSS-Q-ST-80C Rev.2 5.6.1.1a | 10 |
| ECSS-Q-ST-80C Rev.2 5.6.1.2a | 10 |
| ECSS-Q-ST-80C Rev.2 5.6.1.3a | 10 |
| ECSS-Q-ST-80C Rev.2 5.6.2.1a | 11 |
| ECSS-Q-ST-80C Rev.2 5.6.2.2a | 11 |
| ECSS-Q-ST-80C Rev.2 5.6.2.3a | 11 |
| ECSS-Q-ST-80C Rev.2 5.7.1a | 12 |
| ECSS-Q-ST-80C Rev.2 5.7.2.1a | 12 |
| ECSS-Q-ST-80C Rev.2 5.7.2.2a | 12 |
| ECSS-Q-ST-80C Rev.2 5.7.2.3a | 12 |
| ECSS-Q-ST-80C Rev.2 5.7.2.4a | 12 |
| ECSS-Q-ST-80C Rev.2 5.7.3.1a | 12 |
| ECSS-Q-ST-80C Rev.2 5.7.3.1b | 12 |
| ECSS-Q-ST-80C Rev.2 5.7.3.2a | 12 |
| ECSS-Q-ST-80C Rev.2 5.7.3.3a | 12 |

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
