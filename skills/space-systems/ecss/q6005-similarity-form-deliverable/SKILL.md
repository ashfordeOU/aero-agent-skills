---
name: q6005-similarity-form-deliverable
description: "Evaluate the form filed when likeness to an already approved hybrid design is offered as grounds for a reduced approval programme, against the entries Annex C of ECSS-Q-ST-60-05C requires it to record. Use when the claim reaches the procurement authority and the record itself must be judged sound before the route is even considered: check the reference identity block and the recorded approval status, confirm a comparison row exists for every mandated attribute, test each declared same-or-differs verdict against the values written beside it, demand a justification and an impact statement on every divergent row, and return a documented-evidence ratio with findings. Trigger: ecss, q-st-60-05c-annex-c, hybrid-similarity-claim-form, similarity-comparison-row-integrity, similarity-divergence-justification, similarity-reference-identity-block, similarity-documented-evidence-ratio."
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
  tags: [ecss, q-st-60-05-hybrid-microcircuit-scope, q6005-similarity-form-deliverable, hybrid-similarity-claim-form, similarity-comparison-row-integrity, similarity-divergence-justification, similarity-reference-identity-block, similarity-documented-evidence-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Microcircuits — Similarity Form Deliverable (space-systems/ecss/q6005-similarity-form-deliverable)

Use when the task is the record step of ECSS-Q-ST-60-05C Annex C — not
whether the shortened approval route is granted, but whether the form
filed to claim it records what the annex says a likeness claim has to
record, so the claim can be read, checked and kept as evidence.

## Domain quick reference

- The form is evidence before it is an argument. An authority that
  cannot see the reference circuit's identity, its approval reference,
  the status that approval is currently in, and the two quality levels
  side by side has nothing to assess, whatever the comparison rows go
  on to say.
- The comparison is row-per-attribute and the attribute list is fixed:
  circuit function, substrate material and metallization, die attach,
  wire bond, package and sealing, passive element technology,
  screening sequence, manufacturing line and operating temperature
  range. An attribute with no row is a silence, and a silence reads as
  likeness unless the form is graded for coverage.
- A row carries both the two values and a declared verdict, which
  means the row can contradict itself. A row declaring likeness over
  two visibly different values, or divergence over two identical ones,
  is the defect this grading exists to surface — the declared verdict
  is tested against the values, never taken on trust.
- A divergent row owes two further entries: why the divergence does
  not break the likeness, and what it changes. One without the other
  is an unsupported divergence, because a justification with no impact
  statement never says what the reader should now go and check.
- A blank compared value is its own finding. It supports no verdict at
  all, so the row is treated as divergent for the purpose of the
  evidence it owes rather than quietly read as a match.
- A recorded approval status outside the recognised vocabulary and a
  recognised but non-current one are different findings. The first is
  a filing error; the second says the record as filed cannot carry the
  claim, and the authority is told which of the two it has.

## Workflow

1. Normalise the identity block, fold the spelling of its entry names,
   refuse an entry recorded twice, and split absent entries from
   entries recorded blank.
2. Read the reference approval status against the recognised
   vocabulary and report an unrecognised value separately from a
   recognised but non-current one.
3. Normalise the comparison rows, refuse an unrecognised verdict token
   and refuse the same attribute given two rows.
4. Report the mandated attributes with no row at all, and group the
   rows written for attributes outside the mandated list as remarks.
5. For each row, derive the verdict the two recorded values support
   and compare it with the declared one; a row with no declared
   verdict is read from the values and the reading is reported.
6. On every effectively divergent row, require both the justification
   and the impact statement, and collect the attributes left
   unsupported.
7. Score the documented evidence over the obligations the claim
   creates — a row per attribute, a consistent verdict per row, and
   two supporting entries per divergence — and return record-complete,
   record-complete-with-remarks or record-incomplete.

## Pitfalls

- Believing the declared verdict. The whole value of grading the form
  is that a row can assert likeness over two different values; a
  grader that reads the verdict column and stops finds nothing.
- Treating an attribute with no row as a match. Absence of a row is
  absence of evidence, and it has to cost coverage rather than pass
  quietly as agreement.
- Accepting a justification alone on a divergent row. Without the
  impact statement the reader is never told what changed, so the
  delta work the claim implies stays invisible.
- Reading a blank compared value as equality. Two blanks compare equal
  as strings and would score a clean likeness row; the blank is
  refused as a basis for any verdict instead.
- Folding the unrecognised approval status into the non-current one.
  A misspelt status is corrected by the filer in minutes; a withdrawn
  approval ends the claim. Merging them sends the wrong instruction.

## Behavior contract (gate 3)

The identity block validation, approval status vocabulary, row
normalisation, derived-versus-declared verdict test, divergence
support requirement, attribute coverage, documented-evidence ratio and
the record-complete / with-remarks / incomplete verdict are exercised
by the gate 3 contract test:
scripts/test_q6005_similarity_form_deliverable.py against
scripts/q6005_similarity_form_deliverable_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_similarity_form_deliverable.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
