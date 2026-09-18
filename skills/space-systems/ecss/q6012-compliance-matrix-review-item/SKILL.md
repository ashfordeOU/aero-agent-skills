---
name: q6012-compliance-matrix-review-item
description: "Audit the compliance matrix review item of ECSS-Q-ST-60-12C clause 7.3.10 for a microwave die design: normalize every row onto a canonical requirement identifier, reject a requirement stated twice, confront the tabulated conformance statements with the applicable design requirement list to expose the requirements no row answers and the rows answering nothing, find the conformance claims carrying no evidence reference and the departures carrying no deviation or waiver, check each exclusion is justified, then accept, action or reject the matrix. Use when a microwave die design review reaches the tabulated statement of conformance. Trigger: ecss, q-st-60-12-microwave-die-scope, compliance-matrix-review, requirement-conformance-status, matrix-coverage-gap, evidence-reference-completeness, deviation-and-waiver-reference, unwaived-non-conformance, not-applicable-justification."
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
  tags: [ecss, q-st-60-12-microwave-die-scope, q6012-compliance-matrix-review-item, compliance-matrix-review, requirement-conformance-status, matrix-coverage-gap, evidence-reference-completeness, deviation-and-waiver-reference, unwaived-non-conformance, not-applicable-justification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die — Compliance Matrix Review Item (space-systems/ecss/q6012-compliance-matrix-review-item)

Use when the task is the compliance matrix review item of
ECSS-Q-ST-60-12C clause 7.3.10 -- reviewing the tabulated statement of
conformance the die design presents against every applicable design
requirement, rather than reviewing the design itself.

## Domain quick reference

- The matrix is a claim, not evidence. Each row states where the design
  stands against one requirement and points at the thing that shows it.
  Reviewing the matrix means confronting the rows with the requirement
  list they claim to answer, then testing each row for what it owes.
- Four conformance states carry four different duties. A conformant row
  owes an evidence reference. A partially conformant row owes both an
  evidence reference and a departure reference. A non-conformant row
  owes a departure reference. An excluded row owes a justification for
  the exclusion, which is the one duty reviewers routinely skip.
- Coverage is the first question and it is asymmetric. A requirement
  with no row is a hole in the statement and blocks; a row against no
  applicable requirement is usually a stale line carried from a
  previous baseline, which is worth an action rather than a rejection.
- Matrices are assembled by hand from several sources, so the same
  requirement arrives spelled with stray space and mixed case. Coverage
  has to be counted on a canonical identifier, or a requirement that is
  answered reads as a hole and a requirement stated twice slips past.
- A departure with no deviation or waiver reference is the finding with
  the longest tail. The design has already moved away from the
  requirement; what is missing is the record that somebody with the
  authority to accept that agreed to it.
- The share of rows in full conformance is reported over the assessed
  rows only. A matrix earns no credit for a requirement it declared
  inapplicable, and it is not penalised for one either.

## Workflow

1. Normalize every row: canonical requirement identifier, canonical
   conformance state, references reduced to present or absent. Reject an
   unknown state and an unknown field rather than carrying them through.
2. Reject a requirement stated twice. Two rows against one requirement
   means the matrix has two answers, and the review cannot pick one.
3. Confront the normalized rows with the applicable requirement list.
   Report the uncovered requirements and the orphan rows separately,
   because they carry different consequences.
4. Test the conformance claims for an evidence reference and the
   departures for a deviation or waiver reference. Both absences are
   blocking, because in each case the row states something nothing
   supports.
5. Test each exclusion for a justification, and carry a bare exclusion
   as an action to justify it or restore the requirement to the
   assessed set.
6. Report the counts and the full conformance share over the assessed
   rows, then accept, action or reject the matrix with the findings
   that drove the verdict.

## Pitfalls

- Reading the matrix without the requirement list beside it. Every row
  can be well formed and fully referenced while an entire requirement
  group is simply absent, and nothing inside the table reveals that.
- Counting coverage on the identifier as typed. A leading space or a
  lower-case prefix makes an answered requirement read as a hole, and
  hides the duplicate that the canonical form would have caught.
- Accepting a non-conformance because it is stated plainly. Stating a
  departure is not raising one: without a deviation or waiver reference
  nobody with the authority to accept the departure has seen it.
- Letting an excluded requirement pass on the word alone. The exclusion
  is a technical claim about the die -- that the requirement addresses
  something the design does not contain -- and it needs the same
  support as a conformance claim.
- Quoting a conformance percentage over all the rows. Exclusions
  inflate it, so a matrix that declares half its requirements
  inapplicable reports better than one that assessed everything;
  computing the share over the assessed rows removes that incentive.

## Behavior contract (gate 3)

The row normalization, duplicate rejection, coverage confrontation,
evidence and waiver duties, exclusion justification, conformance share
and matrix verdict are exercised by the gate 3 contract test:
scripts/test_q6012_compliance_matrix_review_item.py against
scripts/q6012_compliance_matrix_review_item_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_compliance_matrix_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
