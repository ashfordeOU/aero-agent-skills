---
name: e2008-sca-deliverable-components
description: "Evaluate whether the cell assemblies in a delivery lot were produced and inspected under the approved process identification document, as ECSS-E-ST-20-08C clause 6.1.3 requires. Use when a lot is presented for release and the build paperwork has to carry it: confirm the cited process document is approved rather than draft or withdrawn, compare the revision each unit was built to against the revision approved for delivery, check every mandatory inspection was performed and passed rather than merely listed, disposition each unit as deliverable, deliverable under concession or withheld, and size the release share against the lot. Trigger: ecss, e-st-20-08c, sca-deliverable-component-release, process-identification-document-approval, cell-assembly-delivery-lot-disposition, sca-inspection-record-completeness, pid-revision-build-alignment, sca-concession-disposition."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-sca-deliverable-components, sca-deliverable-component-release, process-identification-document-approval, cell-assembly-delivery-lot-disposition, sca-inspection-record-completeness, pid-revision-build-alignment, sca-concession-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Deliverable Components (space-systems/ecss/e2008-sca-deliverable-components)

Use when the task is clause 6.1.3 of ECSS-E-ST-20-08C: what a supplier
delivers under this clause is not simply a cell assembly but a cell
assembly produced by the process the customer approved and inspected by
the inspections that process calls for. This leaf takes a delivery lot
and says, unit by unit, whether the records release it, release it only
on a concession, or do not release it at all.

## Domain quick reference

- Two independent questions decide every unit. Did the process
  identification document that governed the build actually govern --
  approved, and at the issue approved for this delivery? And was every
  inspection that document calls for performed, with a result?
- Document standing is not a single flag. A draft was never approved
  and governs nothing; a withdrawn document cannot be revived by the
  delivery that cites it; a superseded document approved the build once
  and the delta to the current issue has to be dispositioned; an
  approved document cited at the wrong issue means the unit was built
  under a process the customer did not sign.
- An inspection has three states, not two, and the third one is the
  dangerous one. Passed and failed both mean the inspection happened.
  A required inspection with no record at all, and one listed on the
  travelling sheet with no result, are both absences -- and an absence
  read as a pass is how an uninspected unit ships.
- Completeness is the share of the called-for inspections that actually
  passed, which is not the count of records held. Records for
  inspections the process never called for raise the count and change
  nothing, so they are reported separately rather than credited.
- A concession carries a process difference, not a test result. A unit
  built to a superseded or off-approval issue can release on a written
  concession because what differs is the route. A unit with a failed or
  an unperformed inspection cannot, because what is missing is the
  evidence that the hardware is good, and no signature supplies it.
- The lot verdict is a share, not a count of problems. A delivery
  accepted against a required release share is judged on the share it
  actually reaches, and the weakest unit is named so the repair has an
  address.

## Workflow

1. Take the lot with its identifier, the inspections the process
   document calls for, the required release share, and one record per
   unit: serial, document state, the approved issue, the issue the unit
   was built to, its inspection records and any concession reference.
2. Resolve document standing per unit before touching the inspections:
   governing at the current issue, governing off-issue, or not
   governing at all.
3. Grade the inspection records against the called-for set. Separate
   the failed from the missing from the listed-but-unperformed, and
   report records outside the called-for set rather than counting them.
4. Disposition each unit. Anything failed, missing or unperformed, and
   any document that does not govern, withholds the unit outright; an
   off-issue build releases on a cited concession and is withheld
   without one; everything else is deliverable.
5. Reject a concession cited against a failed or absent inspection as a
   finding on the record, and flag a concession cited where the records
   need none so it can be closed out instead of shipped.
6. Roll the lot up: the withheld units, the units on concession, the
   release share against the share required, and the weakest unit by
   disposition then by inspection completeness.

## Pitfalls

- Reading a required inspection with no record as a pass. It is the
  single most common way an uninspected unit reaches a customer,
  because nothing on the sheet is red -- there is simply nothing on the
  sheet.
- Grading only the records held rather than the inspections called for.
  A unit with six records and one missing inspection looks better on a
  record count than a unit with three records and none missing, and it
  is the worse unit.
- Treating the document state and the issue as one check. An approved
  document cited at the wrong issue passes a state check and still
  means the unit was built to a process nobody approved for this
  delivery.
- Letting a concession carry a failed inspection. A concession
  dispositions a difference in the route, not a result on the hardware,
  and accepting one here converts a test failure into paperwork.
- Counting withheld units instead of sizing the release. Two units held
  out of a lot of four and two out of a lot of two hundred are not the
  same delivery, and a count reports them identically.
- Comparing a release share against its requirement with bare
  arithmetic. The share is a quotient of two unit counts, so a lot
  landing exactly on its required share can evaluate a unit in the last
  place below it and be withheld on one platform and released on
  another.

## Behavior contract (gate 3)

The document standing check, the inspection completeness grading, the
unit disposition precedence, the concession admissibility rule and the
rolled-up lot release share are exercised by the gate 3 contract test:
scripts/test_e2008_sca_deliverable_components.py against
scripts/e2008_sca_deliverable_components_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_deliverable_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
