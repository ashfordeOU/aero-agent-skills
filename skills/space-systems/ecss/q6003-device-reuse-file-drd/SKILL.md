---
name: q6003-device-reuse-file-drd
description: "Determine whether a device reuse file holds the heritage evidence its DRD demands and whether that heritage actually reaches the new application. Use when a proposed reuse has to become a substantiated, delta-qualification or not-substantiated verdict under ECSS-Q-ST-60-03C Annex C: refuse a blank section body, check every heritage item names its element, its previous application, the qualification state that application left it in and an evidence reference that resolves, compare the new duty against each heritage envelope bound in the direction it is written, and confirm every change since the heritage build carries an impact assessment and a verification action. Trigger: ecss, q-st-60-03c-annex-c, device-reuse-file-drd, device-heritage-evidence-traceability, device-heritage-environment-envelope, device-delta-qualification-trigger, device-reuse-change-impact-assessment."
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
  tags: [ecss, q-st-60-03-device-development-assurance-scope, q6003-device-reuse-file-drd, device-heritage-evidence-traceability, device-heritage-environment-envelope, device-delta-qualification-trigger, device-reuse-change-impact-assessment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Development -- Reuse File DRD (space-systems/ecss/q6003-device-reuse-file-drd)

Use when the task is the Annex C document requirements definition of
ECSS-Q-ST-60-03C: a device is proposed for reuse in a new application,
the reuse file is the record that carries the heritage evidence, and the
question is both whether the file holds what the DRD asks for and
whether the heritage it describes actually covers the new duty.

## Domain quick reference

- Heritage is a claim about a previous application, not a property of a
  part number. The reuse file exists to make that claim checkable, so
  every heritage item has to name the element, the application it ran
  in, the qualification state that application left it in, and a
  reference into an evidence register somebody can produce a document
  from.
- The eight content blocks are the introduction, the reused element
  identification, the previous application record, the heritage
  environment envelope, the change record, the verification evidence,
  the open risks and limitations, and the reuse justification. A present
  heading with an empty body is absent.
- The qualification state grades the heritage. Fully qualified and
  qualified with limitations can carry a reuse; flight-proven but never
  formally qualified, and development-only, cannot carry one on their
  own however long the element ran, because no qualification programme
  ever bounded it.
- An evidence reference that resolves to nothing is the most common
  defect and the hardest to see, because the file reads complete. The
  reference is checked against the register the project can actually
  produce, not against the file's own bibliography.
- The envelope comparison is directional and per-parameter. A maximum
  junction temperature is an upper bound, a minimum junction temperature
  a lower one, and a drift figure bounds a magnitude that may move
  either way. One direction applied across the envelope inverts half of
  it.
- A new duty that lands exactly on a heritage bound is inside it. The
  duty and the bound come from two different computations, so the
  equality is absorbed by a named tolerance rather than by moving the
  bound.
- An envelope parameter the new duty never declares is not a pass. It
  means the two were never compared, which is a documentary defect
  rather than an exceedance.
- Exceeding the envelope does not void the reuse. It converts it into a
  delta qualification with a named parameter and a measured excess
  behind it. A documentary defect is worse: there is nothing to write a
  delta against.
- Every change between the heritage build and the new one needs an
  impact assessment and a verification action. An unassessed change is
  the mechanism by which heritage quietly stops applying to the item it
  is offered for.

## Workflow

1. Read the reuse file as section key to body text and run
   missing_file_sections, treating a blank body as an absent key.
2. Run heritage_item_deficiencies over the heritage items to catch
   untraceable entries and weak qualification states; an unrecognised
   qualification state is refused rather than graded.
3. Run unresolved_evidence_references against the project's evidence
   register, not against the file's own reference list.
4. Run envelope_exceedances with the heritage envelope and the new duty,
   and read both returned lists: the exceedances and the parameters the
   duty never declared.
5. Run unassessed_changes over the change record to find changes with no
   impact assessment or no verification action.
6. Combine all five with assess_device_reuse_file_drd. Documentary
   defects dominate: they return not-substantiated. A clean file with an
   envelope exceedance returns delta-qualification-required.

## Pitfalls

- Accepting long service as qualification. Flight-proven and
  development-only heritage never had a qualification programme bound
  it, so neither carries a reuse without a delta.
- Checking evidence references against the file's own bibliography. That
  is circular; the register the project can produce documents from is
  the only list that matters.
- Applying one comparison direction to the whole envelope. A minimum
  temperature read as a maximum passes exactly the cases it should stop.
- Reading an undeclared duty parameter as a pass. Nothing was compared,
  so nothing was cleared.
- Widening a bound to absorb a duty that lands exactly on it. The
  equality is a representation question handled inside the comparison;
  the heritage bound stays as established.
- Reporting an envelope exceedance as a rejection. The heritage is real
  and the excess is measured, so the outcome is a delta qualification
  with a named parameter, not a restart.
- Letting a change through without an impact assessment. It is the
  single step that converts valid heritage into a claim about a
  different element.

## Behavior contract (gate 3)

The section coverage, heritage item traceability, evidence-reference
resolution, directional envelope comparison, change-record rigour and
the aggregate reuse disposition are exercised by the gate 3 contract
test: scripts/test_q6003_device_reuse_file_drd.py against
scripts/q6003_device_reuse_file_drd_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6003_device_reuse_file_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
