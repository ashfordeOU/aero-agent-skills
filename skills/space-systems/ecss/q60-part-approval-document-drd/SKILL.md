---
name: q60-part-approval-document-drd
description: "Evaluate a part approval document against the content and per-sheet fields its DRD requires. Use when an Annex D deliverable is about to go to the customer and the question is whether it can be submitted: weight the document blocks by how much of the approval rests on each, select the part types that actually owe a sheet, grade every sheet on what the part is, what it was bought against, what evidence was assessed and who signed, separate an approval from one granted with unrecorded limitations, from a deferral and from a refusal, and weight the approved share by installed quantity. Trigger: ecss, q-st-60c, q60-pad-drd-sheet-fields, q60-pad-drd-document-blocks, q60-pad-drd-decision-state, q60-pad-drd-limitations-recorded, q60-pad-drd-installed-weighted-approval."
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
  tags: [ecss, q-st-60-eee-components-scope, q-st-60c, q60-part-approval-document-drd, q60-pad-drd-sheet-fields, q60-pad-drd-document-blocks, q60-pad-drd-decision-state, q60-pad-drd-limitations-recorded, q60-pad-drd-installed-weighted-approval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Part Approval Document Data Item (space-systems/ecss/q60-part-approval-document-drd)

Use when the task is Annex D of ECSS-Q-ST-60C: the part approval document as a
deliverable — the blocks the document carries and the fields each per-part
sheet has to hold before the decision on that sheet can be acted on. This leaf
grades a compiled deliverable on document content, on sheet completeness, and
on how much of what the build installs is actually approved.

## Domain quick reference

- The document blocks and the sheets are two separate obligations. A perfect
  set of sheets under a deliverable with no approval summary and no signature
  block is not a submittable document, and a complete document wrapper around
  three half-filled sheets is not one either.
- Block coverage is weighted. A missing scope paragraph and a missing approval
  summary both leave five blocks of six; only one of them removes the statement
  the whole deliverable exists to make.
- A sheet exists so somebody can act on the decision. Without the procurement
  reference the reader cannot tell what the part was bought against, without
  the evaluation evidence they cannot tell what was assessed, and without the
  authority and date they cannot tell whether the decision is still current.
- Four decisions, four corrections. An approval, an approval subject to stated
  limitations, a refusal and a deferral each send the programme somewhere
  different; a single approved-or-not column loses three of them.
- An approval with limitations and a blank limitations field is a full
  approval in practice. The limitations are the reason that decision exists
  separately from a plain approval.
- Only an accepted sheet closes a part type. A second sheet after an approval
  is a duplicate; a second sheet after a refusal is the correction, and
  rejecting it as a duplicate strands the part.
- The approved share is weighted by installed quantity. One deferred part type
  installed forty times is a bigger hole than three approved ones installed
  once, and a sheet count hides that entirely.

## Workflow

1. Score the document blocks by weight, naming every absent block rather than
   returning a bare fraction.
2. Validate the build and select the part types the deliverable owes a sheet
   for. A part outside the flight EEE set owes nothing here, so it belongs on
   neither side of the coverage.
3. Grade each sheet against the field set, and stop there when any field is
   absent — an incomplete sheet is not a refused part and must not be reported
   as one.
4. Resolve the part type the sheet names. A sheet for a part not in the build
   is a finding on the sheet; a sheet for another category is outside the
   obligation.
5. Resolve the decision, separating a label the data item does not define from
   the four it does.
6. Require recorded limitations from a limited approval, then separate a
   deferral from a refusal so each finding names its own correction.
7. Weight the approved part types by installed quantity, compare that share
   with the required level, absorbing floating-point representation error at
   the boundary with a named tolerance rather than by lowering the level, and
   return one verdict with findings ranked worst first.

## Pitfalls

- Grading the sheets and ignoring the document blocks, or the reverse. Both
  are part of the same data item and either one alone passes a deliverable
  that cannot be submitted.
- Reading an incomplete sheet as an unapproved part. Nobody ever decided on
  it; the correction is a missing field, not an approval campaign.
- Collapsing deferral and refusal. One is waiting on the customer, the other
  needs a different part, and the same label sends the wrong work to the
  supplier.
- Letting a limited approval through with an empty limitations field. The
  deliverable then grants more than the customer agreed, invisibly.
- Rejecting a corrected sheet after a refusal as a duplicate. Only a part type
  already closed by an approval can produce one.
- Counting sheets instead of weighting by installed quantity, and widening the
  required share so an exactly-met case passes. An equality at the boundary is
  a representation question, handled by the tolerance inside the comparison.

## Behavior contract (gate 3)

The weighted document block coverage, obliged part selection, per-sheet
completeness grading, decision resolution, limitation requirement, duplicate
sheet handling, installation-weighted approved share and ranked findings are
exercised by the gate 3 contract test:
`scripts/test_q60_part_approval_document_drd.py` against
`scripts/q60_part_approval_document_drd_logic.py` (stdlib unittest, offline).
Run: `python3 scripts/test_q60_part_approval_document_drd.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
