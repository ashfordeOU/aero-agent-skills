---
name: q80-software-criticality-tailoring
description: "Classify space software into criticality categories A to D from the severity of the functions it serves and the compensating provisions in place, then derive the ECSS-Q-ST-80C Rev.2 tailoring matrix for that category: which software product assurance requirements apply, apply in reduced form, drop out, or follow the security sensitivity instead. Summarise the matrix per requirement group, list what relaxes when a category is lowered, and resolve a product's category from its components. Use when a software criticality category is being argued or a Q-80 tailoring proposal is prepared for the customer. Trigger: q-st-80c-annex-d, software-criticality-category, q80-applicability-matrix, q80-tailoring, category-downgrade-impact, compensating-provision."
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
  tags: [ecss, q-st-80c, q80-software-criticality-tailoring, q-st-80c-annex-d, software-criticality-category, q80-applicability-matrix, q80-tailoring, category-downgrade-impact, compensating-provision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Software Criticality Categories and Q-80 Tailoring (space-systems/ecss/q80-software-criticality-tailoring)

Use when the question is which software criticality category a space
software product belongs to, and what that category does to the software
product assurance obligations of ECSS-Q-ST-80C Rev.2 (30 April 2025). The
standard's Annex D carries both halves: the relation between function
severity, compensating provisions and category (D.1), and the applicability
of every requirement to each category (D.2).

## Domain quick reference

- The category belongs to the software product, not to a function. It
  follows the most severe function the software takes part in: severity I
  (catastrophic) gives A, II gives B, III gives C, IV gives D.
- A compensating provision at system level (hardware, another piece of
  software, or an operational procedure) can lower the category by one
  step, but only once the provision itself meets the system dependability
  and safety requirements. A software provision is not free: it inherits
  the category the protected software would have had.
- Software that IS the compensating provision takes no credit at all; it
  sits at the category of the functions it protects.
- The applicability matrix reads per requirement, not per clause heading.
  Most requirements hold for every category; category D loses the
  critical-software, dependability-analysis, process-assessment and
  software-maturity requirements, and several others shrink rather than
  vanish. Category C loses independent verification and re-running unit
  and integration tests on uninstrumented code.
- The security requirements (6.2.9 and 6.2.10) are not keyed to
  criticality at all. They follow the security sensitivity of the
  software, which is a separate decision.
- A downgrade is argued by what it removes. Listing the requirements that
  relax between the two categories is the evidence a customer asks for
  before agreeing to it.
- A product made of components takes its most critical component's
  category unless a partitioning analysis shows the components cannot
  interfere; without that analysis the lower components are raised.

## Workflow

1. Collect the functions the software takes part in and the highest
   severity among them, from the system dependability and safety analyses.
2. List the compensating provisions actually in place and confirm each one
   meets the system requirements before claiming credit.
3. Assign the category and record the rationale and the constraints the
   assignment places on any software provision.
4. Resolve the product category from its components; claim a partition
   only with its analysis in hand.
5. Derive the tailoring matrix for the category, with the security rows set
   by the security sensitivity decision.
6. Summarise per requirement group for the customer, and where a lower
   category is proposed, attach the list of what relaxes.

## Pitfalls

- Classifying per function and averaging. The worst function sets the
  category of the whole product.
- Taking credit for a provision that has not been shown to meet the system
  requirements, or for a software provision developed to a lower category.
- Reading D.2 at heading level. A heading whose group is "mostly
  applicable" still hides requirements that drop out or shrink.
- Treating the security requirements as tailored out because the software
  is category D. They follow security sensitivity, not criticality.
- Proposing a downgrade without the relaxation list. The customer cannot
  agree to a change whose consequences are not on the page.

## Stop gate: human sign-off required

The agent drafts; it does not decide. Stop and hand the draft to a named
human before any of these leave the working folder:

- The software criticality category assigned to each product or
  component. The agent may propose it with the severity and provision
  rationale; it stands only once the responsible engineer has agreed it
  with the system dependability and safety function.
- Any tailoring proposal or category downgrade sent to the customer.
- Any claim of partitioning between components of different categories.

Mark every such output as a draft, list the open questions for the
reviewer, and end with the line: STOP: human sign-off required before
submission.

## Behavior contract (gate 3)

The severity and category normalisation, the category assignment with
compensating-provision credit and the no-credit rule for a provision, the
per-requirement applicability data with its reduced and security-driven
entries, the group summary, the downgrade relaxation list and the product
category rollup are exercised by the gate 3 contract test:
scripts/test_q80_software_criticality_tailoring.py against
scripts/q80_software_criticality_tailoring_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q80_software_criticality_tailoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite ECSS-Q-ST-80C Rev.2
  (30 April 2025) as the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
