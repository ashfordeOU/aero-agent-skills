---
name: q80-compliance-matrix
description: "Build a clause-by-clause compliance matrix against ECSS-Q-ST-80C Rev.2 as a draft for human sign-off: join the clause list to an evidence index of document, section, status and justification, set each clause to compliant, partially compliant, not compliant or not applicable, pre-fill clauses tailored out for the software category, raise gaps such as missing evidence, compliance claimed without a reference and not-applicable claims that contradict the tailoring, summarise coverage, and render Markdown or CSV ending at the stop line. Use when a supplier answers the Q-80 compliance matrix or a customer audits one. Trigger: q80-compliance-matrix, software-product-assurance-compliance, clause-by-clause-compliance, evidence-index, compliance-gap-list, statement-of-compliance."
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
  tags: [ecss, q-st-80c, q80-compliance-matrix, software-product-assurance-compliance, clause-by-clause-compliance, evidence-index, compliance-gap-list, statement-of-compliance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS-Q-ST-80C Compliance Matrix (space-systems/ecss/q80-compliance-matrix)

Use when a software product assurance (PA) manager has to answer
ECSS-Q-ST-80C Rev.2 (30 April 2025) clause by clause: the compliance matrix
that closes the Software Product Assurance Plan (SPAP) and that customers
ask for at the system requirements review, or an audit of one received from
a supplier. The skill turns a clause list and an evidence index into the
matrix, a coverage summary and the gap list, and stops at a human sign-off.

## Domain quick reference

- Four statuses and no others: compliant, partially compliant, not
  compliant, not applicable. Every status other than compliant needs a
  justification; every status other than not applicable needs an evidence
  reference down to the section of the document.
- A clause with no evidence is open, not compliant by default. Silence is
  never compliance.
- Compliance claimed without a document reference is downgraded to
  partial and raised as a gap: a claim nobody can check is not evidence.
- Not applicable has two sources. The category tailoring removes some
  requirements outright, and those rows are pre-filled with that reason.
  A not-applicable claim on a clause the tailoring keeps is a deviation
  and needs the customer's agreement, so it is raised as a gap.
- Several evidence rows on one clause combine to the weakest status. One
  audit finding outweighs a compliant claim in the plan.
- Evidence mapped to a clause that is not in the list usually means a
  clause was mistyped or the list is from another revision; it is
  reported, not dropped.
- Coverage is two numbers: the compliant fraction of the applicable
  clauses, and the fraction with an evidence reference. A high first
  number with a low second one is a matrix of promises.

## Workflow

1. Take the clause list: the customer's, or the full requirement list of
   the standard for the software category.
2. Load the evidence index (CSV or rows) and normalise the status
   vocabulary; refuse anything outside the four statuses.
3. Build the matrix with the category, so tailored-out rows pre-fill and
   contradictions surface.
4. Read the coverage summary and the gap list; resolve what can be
   resolved from existing documents, and list the rest as open.
5. Render the matrix with the draft banner and the stop line.
6. Hand it to the responsible human. Only that person records the sign-off,
   and approving over open gaps has to be an explicit choice.

## Pitfalls

- Marking a clause compliant because the plan promises it. A promise is
  evidence for the plan clause, not for the activity clause.
- Pointing at a document without a section. The reviewer then re-does the
  mapping, and usually finds it missing.
- Using not applicable as a softer not compliant.
- Answering against the wrong revision. Rev.2 renumbered and deleted
  requirements; clauses from an older list show up as unknown or orphan
  evidence here.
- Letting the matrix leave the building as a statement of compliance
  before a named person has signed it.

## Stop gate: human sign-off required

The agent drafts; it does not decide. Stop and hand the draft to a named
human before any of these leave the working folder:

- The compliance matrix, in any format, sent to a customer or supplier.
- Any not-applicable claim that departs from the category tailoring.
- Any statement of compliance built on the matrix.

The matrix is always produced with status DRAFT. Mark every such output as
a draft, list the open gaps for the reviewer, and end with the line: STOP:
human sign-off required before submission.

## Behavior contract (gate 3)

The clause id and status normalisation, the tailored status per category
with security-driven clauses, the CSV evidence parsing with loose headers,
the row rules (no evidence, missing reference, weakest status wins,
not-applicable conflicts), orphan evidence, the coverage summary, the
Markdown and CSV rendering with the draft marker and stop line, and the
sign-off that refuses an unnamed signatory and silent approval over open
gaps are exercised by the gate 3 contract test:
scripts/test_q80_compliance_matrix.py against
scripts/q80_compliance_matrix_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q80_compliance_matrix.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite ECSS-Q-ST-80C Rev.2
  (30 April 2025) as the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
