---
name: e2040-device-verification-control-document
description: "Audit the device verification control document of ECSS-E-ST-20-40C clause 5.1.5 as the controlled record it is meant to be: check the issue and revision that identify the baseline, place every requirement against the qualification, acceptance, pre-launch and in-orbit stages in that order, refuse a stage recorded closed while an earlier applicable stage is still open, report a closure carrying no evidence reference, keep not-applicable stages out of the denominator while counting them, and report per-stage closure against the targets the document declares. Use when a verification control document is compiled, baselined or reviewed before flight release. Trigger: ecss, e-st-20-40-device-scope, device-verification-control-document, verification-stage-ordering, vcd-closure-evidence, vcd-baseline-issue-revision, per-stage-closure-fraction, flight-release-readiness."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-device-verification-control-document, device-verification-control-document, verification-stage-ordering, vcd-closure-evidence, vcd-baseline-issue-revision, per-stage-closure-fraction, flight-release-readiness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Verification Control Document (space-systems/ecss/e2040-device-verification-control-document)

Use when the task is the control-record duty of ECSS-E-ST-20-40C clause
5.1.5 -- keeping one controlled document that carries every device
requirement through the verification stages, from qualification to
acceptance and on to the stages that release it for flight, and saying
what is still open at each of them.

## Domain quick reference

- The document is a controlled record, not a working list. It is
  identified by an issue and a revision, and a row that changes without
  the baseline changing leaves two different documents claiming to be
  the same one.
- The stages run in a fixed order: qualification, then acceptance, then
  pre-launch, then in-orbit. The order is the whole point of the
  record, because each stage assumes the one before it closed on the
  same requirement.
- A stage closed while an earlier applicable stage on the same
  requirement is open is the defect the document exists to catch. Read
  row by row it looks like progress; read in stage order it says the
  acceptance evidence rests on a qualification that never finished.
- Closure needs an evidence reference. A status of closed with no
  report, procedure or certificate behind it is an assertion, and the
  record is the place where that assertion is supposed to become
  traceable.
- Not-applicable is a real disposition and it is not closure. A stage
  that does not apply to a requirement leaves the denominator, but it
  is still reported, because a document quietly re-labelling its hard
  rows as not-applicable reads as fully closed.
- Closure is a fraction of the applicable rows in a stage. A fraction
  landing exactly on its target has met it, so the comparison absorbs
  the representation error of a division rather than failing on it.
- Flight release rests on the earlier stages. Qualification and
  acceptance fully closed is the condition; pre-launch and in-orbit
  rows may legitimately still be open at the point the document is
  baselined.

## Workflow

1. Resolve the document control block: an issue number of at least one,
   a revision label, and the configuration item the record covers.
   Refuse a missing or non-positive issue rather than defaulting it.
2. Resolve the rows: unique requirement identifiers, and for each one a
   status and an evidence reference per stage. Refuse an unknown stage
   name or an unknown status as an input defect.
3. Report every row whose stage is recorded closed with no evidence
   reference behind it.
4. Walk each row in stage order and report a closed stage that sits
   behind an applicable stage still open or in work.
5. Count the applicable rows per stage, and the not-applicable ones
   separately, so both are visible.
6. Compute the closure fraction per stage over the applicable rows
   only, and the overall closure across every applicable row.
7. Compare each declared target against what the document reaches,
   absorbing representation error, and decide whether qualification and
   acceptance support a flight release.

## Pitfalls

- Reading the document row by row. Every ordering defect lives between
  the stages of one row, and a reviewer who checks statuses one cell at
  a time will never see an acceptance closed ahead of its
  qualification.
- Accepting closed with no evidence reference. The status is the claim
  and the reference is the proof; a record full of the first and short
  of the second is exactly what an audit later cannot reconstruct.
- Marking a difficult stage not-applicable to clear the board. It
  leaves the denominator and the closure figure jumps, which is why the
  not-applicable count is reported next to the fraction rather than
  hidden inside it.
- Letting a row change without moving the issue or revision. The
  baseline is the only thing that makes the record controlled, and two
  copies at the same issue with different content cannot be
  reconciled afterwards.
- Comparing a closure fraction against its target with a strict
  inequality. A three-in-four division landing on a 0.75 target can sit
  a unit in the last place below it and red-flag a stage that is
  exactly on target.

## Behavior contract (gate 3)

The document control block, stage and status folding, evidence-backed
closure check, stage-order violation detection, applicable and
not-applicable accounting, per-stage closure and flight-release verdict
are exercised by the gate 3 contract test:
scripts/test_e2040_device_verification_control_document.py against
scripts/e2040_device_verification_control_document_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_verification_control_document.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
