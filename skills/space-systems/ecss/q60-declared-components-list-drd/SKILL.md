---
name: q60-declared-components-list-drd
description: "Assess a declared components list data item against the fields and approval states its DRD fixes. Use when an Annex B list arrives for review and the question is whether it is releasable: validate the document header, grade every line on the fields an approval decision cannot be taken without, resolve the approval state each entry sits in, check the move that produced it is one the approval route allows, insist a conditional approval records its conditions, catch a part entered twice, weight the decided-and-usable share by declared quantity rather than by line count, and return one release verdict with findings ranked worst first. Trigger: ecss, q-st-60c, q60-dcl-drd-required-fields, q60-dcl-drd-approval-state, q60-dcl-drd-state-transition, q60-dcl-drd-conditional-approval, q60-dcl-drd-quantity-weighted-usable-share, q60-dcl-drd-release-verdict."
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
  tags: [ecss, q-st-60-eee-components-scope, q-st-60c, q60-declared-components-list-drd, q60-dcl-drd-required-fields, q60-dcl-drd-approval-state, q60-dcl-drd-state-transition, q60-dcl-drd-conditional-approval, q60-dcl-drd-quantity-weighted-usable-share, q60-dcl-drd-release-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Declared Components List Data Item (space-systems/ecss/q60-declared-components-list-drd)

Use when the task is Annex B of ECSS-Q-ST-60C: the data item itself — what a
declared components list has to carry field by field, and which approval states
its entries are allowed to sit in before the list can be issued. This leaf
grades a submitted list on the two things a covering signature never shows:
whether each line holds enough to decide on, and whether the states the lines
report were reached legitimately.

## Domain quick reference

- The header is part of the data item, not packaging. A list with no
  identifier, no issue and no named approving authority cannot be referenced by
  a later change, so a perfect set of lines under a nameless header is still
  not a releasable document.
- Completeness is graded per line, and an incomplete line is a different
  problem from a complete line that fails a check. A line missing its
  procurement reference is not an unapproved part; it is a line nobody can
  take a decision on, and reporting it as a refusal sends the supplier to fix
  the wrong thing.
- Decided and usable are independent properties of a state. A refusal is a
  decision and it removes the part; an approval still under review is not a
  decision at all. Collapsing the two into approved-or-not loses the
  distinction between a part the customer said no to and one nobody has looked
  at yet.
- A state is only as good as the route into it. An entry showing approved with
  a previous state of proposed skipped review entirely; every field on that
  line can be correct while the approval behind it is not.
- A conditional approval with no conditions written down is an unconditional
  approval in practice. The conditions are the reason the state exists, and a
  blank conditions field quietly widens what was granted.
- The usable share is weighted by declared quantity, not counted per line. One
  outstanding line carrying ninety parts is a larger hole than three settled
  lines carrying one each, and a line count hides that completely.

## Workflow

1. Validate the header first: identifier, issue, equipment item, issue date and
   approving authority all present and non-blank.
2. Grade each line against the field set, and stop there when any field is
   absent — an incomplete line is not an approval failure and must not be
   reported as one.
3. Resolve the approval state, separating an unknown label from a known state.
   A term the data item does not define is an input defect, not a refusal.
4. Where a previous state is recorded, check the transition against the routes
   the approval process allows, and report a forbidden move before anything
   downstream, because that finding invalidates the state itself.
5. Reject a repeat of a part type, manufacturer and part number already on the
   list; the second line is a duplicate entry, not a second part.
6. Require recorded conditions from a conditional approval, then separate an
   outstanding decision from a refusal and a refusal from a withdrawal, so each
   finding names the correction its own case needs.
7. Weight the accepted lines by declared quantity, compare that share with the
   required level, absorbing floating-point representation error at the
   boundary with a named tolerance rather than by lowering the level, and
   return one verdict with findings ranked worst first.

## Pitfalls

- Treating an incomplete line as an unapproved part. The line was never
  decidable; calling it a refusal sends a correction to the wrong desk and
  leaves the missing field unfilled.
- Reading every non-approved state as a refusal. Proposed, under review,
  rejected and withdrawn need four different responses, and one label produces
  three wrong ones.
- Accepting a state without looking at the route into it. Approved reached
  straight from proposed never passed review, and no field on the line records
  that by itself.
- Letting a conditional approval through with an empty conditions field. The
  state then grants strictly more than the customer agreed to, and the
  difference is invisible in a state column.
- Counting lines instead of weighting them by declared quantity. One
  high-quantity outstanding line disappears behind a long tail of settled ones.
- Widening the required share so an exactly-met case passes. An equality at the
  boundary is a representation question, handled by the tolerance inside the
  comparison; the required level stays as agreed.

## Behavior contract (gate 3)

The header validation, per-line completeness grading, approval-state
resolution, transition checking, duplicate-entry detection, conditional
approval condition requirement, quantity-weighted usable share and ranked
findings are exercised by the gate 3 contract test:
`scripts/test_q60_declared_components_list_drd.py` against
`scripts/q60_declared_components_list_drd_logic.py` (stdlib unittest, offline).
Run: `python3 scripts/test_q60_declared_components_list_drd.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
