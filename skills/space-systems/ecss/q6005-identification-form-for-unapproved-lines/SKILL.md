---
name: q6005-identification-form-for-unapproved-lines
description: "Evaluate the identification form content a supplier owes when its hybrid production line holds no approval at all: derive the blocks the case owes, including the three that stand in for the missing approval, validate the submission against the registry, grade each block complete, partial or absent, read every blank cell as absent rather than supplied, split the absent fields into the deciding ones and the merely supporting ones, and decide admissibility on the deciding fields alone. Use when a form arrives from an unapproved line and a reviewer must name what is missing before it can be accepted. Trigger: ecss, q-st-60-05, hybrid-identification-form, unapproved-hybrid-production-line, hybrid-form-content-completeness, hybrid-compensating-controls, comparable-build-evidence, hybrid-delta-screening-plan."
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
  tags: [ecss, q-st-60-hybrid-procurement-scope, q6005-identification-form-for-unapproved-lines, hybrid-identification-form, unapproved-hybrid-production-line, hybrid-form-content-completeness, hybrid-compensating-controls, comparable-build-evidence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Identification Form, Unapproved Line (space-systems/ecss/q6005-identification-form-for-unapproved-lines)

Use when the task is the content of a hybrid identification form under
ECSS-Q-ST-60-05 clause 6.2.4 — the supplier's production line holds no
approval at the time the hybrids are used, and the question is what the form
has to carry before a reviewer can accept it at all.

## Domain quick reference

- The unapproved case is not the ordinary form with a caveat. It owes the
  ordinary content blocks plus three that exist only because the approval is
  absent: where the line's approval actually stands, the compensating
  controls added in its place, and the evidence from comparable builds that
  the line can do the work.
- Those three are the substitute for the approval. A form that carries the
  ordinary blocks perfectly and none of these has not produced a thin
  submission, it has produced one with nothing standing where the approval
  should be.
- Not every field decides admissibility. Each block separates the fields the
  decision turns on from the ones that add confidence, so a form missing a
  package outline is a finding while a form missing its lot acceptance
  criteria is a stop.
- A present-but-blank cell is an absent field. Grading on key presence lets
  an empty cell buy coverage, which is how a form reaches a high completion
  share while its deciding content is still missing.
- The completion share is a progress measure, not the verdict. Admissibility
  is decided on the deciding fields alone; the share tells the supplier how
  far the rest of the submission has to travel.
- Gaps are reported as a set, in registry order. A form returned once with
  every gap named costs one cycle; a form returned per finding costs as many
  cycles as there are findings.

## Workflow

1. Take the line's approval standing as an input and derive the owed block
   set from it — base blocks for an approved line, base plus the three
   stand-in blocks when the line is unapproved.
2. Validate the submission against the registry. An unrecognised block or
   field is a data error in the submission, not extra content to be scored.
3. Grade each owed block: complete when every field is carried, partial when
   some are, absent when none are.
4. Within each block, split the absent fields into the deciding ones and the
   supporting ones.
5. Count carried fields against owed fields for the completion share, reading
   a blank cell as absent.
6. Decide admissibility on the deciding gaps alone, then emit the findings —
   absent blocks once each rather than once per field, deciding gaps,
   supporting gaps, and any block supplied that this case does not owe.

## Pitfalls

- Scoring an unapproved line against the approved block set. The form then
  reads as complete precisely because the blocks that matter for this case
  were never asked for.
- Counting a key that exists as a field that is filled. Blank strings, empty
  lists and null cells are absent content; treating them as supplied is the
  quickest way to a high share with a hollow form.
- Letting the completion share decide admissibility. A form can carry most of
  its fields and still be missing a deciding one; the share never overrides
  the deciding-field test.
- Reporting an absent block as a stack of absent fields. The supplier reads
  three findings about one block and fixes one of them; naming the block once
  asks for the whole block.
- Accepting the stand-in blocks on a line that already holds approval. They
  are not owed there, and quietly scoring them changes the share of a case
  they do not belong to.

## Behavior contract (gate 3)

The owed-block derivation, registry validation, per-block grading, deciding
versus supporting split, blank-cell handling, completion share and
admissibility decision are exercised by the gate 3 contract test:
scripts/test_q6005_identification_form_for_unapproved_lines.py against
scripts/q6005_identification_form_for_unapproved_lines_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_identification_form_for_unapproved_lines.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
