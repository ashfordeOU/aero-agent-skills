---
name: e2008-deliverable-blocking-diode-components
description: "Evaluate whether delivered planar blocking diodes were processed and inspected against the process identification document that governs them, under ECSS-E-ST-20-08C clause 12.2.2: resolve which issue was released and in force on the day a lot ran, refuse a lot built to a superseded or still-unreleased issue, grade declared processing and inspection steps separately so a built-but-unverified lot cannot hide, name a step performed that the issue never declared, keep an unrecorded step apart from one not performed and from a failure, and return a verdict per lot. Use when a planar blocking diode delivery lot, process identification document or traveller set has to be reviewed. Trigger: ecss, e-st-20-08c, deliverable-planar-blocking-diode-components, blocking-diode-process-identification-document, blocking-diode-document-issue-in-force, blocking-diode-unauthorised-process-step, blocking-diode-inspection-step-coverage, blocking-diode-lot-delivery-verdict."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-deliverable-blocking-diode-components, deliverable-planar-blocking-diode-components, blocking-diode-process-identification-document, blocking-diode-document-issue-in-force, blocking-diode-unauthorised-process-step, blocking-diode-inspection-step-coverage, blocking-diode-lot-delivery-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Planar Blocking Diodes -- Deliverable Components (space-systems/ecss/e2008-deliverable-blocking-diode-components)

Use when the task is clause 12.2.2 of ECSS-E-ST-20-08C: the planar blocking
diodes that are delivered are the ones processed and inspected in accordance
with their process identification document. This leaf grades a delivery on
whether each lot can actually be shown to have been built to that document.

## Domain quick reference

- The document is the build standard and the traveller is only evidence that
  the standard was followed. A clean traveller that points at no established
  issue has recorded activity, not conformance.
- A process identification document carries issues, and the one that governs a
  lot is the issue released and in force on the day the lot was processed --
  not the newest one on the shelf and not the one printed on the cover of the
  folder somebody handed over.
- Four issue standings behave differently and only one of them is compliant.
  An issue in force governs. A superseded issue was the standard once, which
  is exactly why the delta to the current issue has to be dispositioned rather
  than waved through. An unreleased draft and an issue used before its
  effective date never were a standard, so nothing was built to anything.
- Both step kinds are owed by the clause. Processing steps build the part;
  inspection steps show it was built right. A lot that ran every processing
  step and no inspection step has been built and not verified, and rolling
  the two kinds into one overall figure buries exactly that case.
- A step the traveller records that the governing issue does not declare is a
  process nobody authorised, not extra diligence. It may well have helped, but
  it was not reviewed, and it moves the lot off the standard it claims.
- Four record states are kept apart because different people disposition them.
  No record at all is the worst: nobody can tell whether the step was skipped,
  lost or never scheduled. A step recorded as not performed is a schedule
  item. A recorded failure is known and can be dispositioned.
- Whether a superseded issue and a dispositioned failure are carried are both
  project positions. Both answers are legitimate, so they are read from policy
  rather than assumed, because assuming either silently accepts hardware.

## Workflow

1. Validate the process identification document: a document identifier and at
   least one issue, each with a unique label, a release state, an effective
   date and a non-empty step list naming a kind for every step.
2. Resolve the issue in force on the day the lot was processed -- the latest
   released issue whose effective date has already passed.
3. Grade the issue the lot names against it: in force, superseded, unreleased,
   not yet effective, or an issue the document never carried.
4. Grade the traveller against the steps that issue declares: what has no
   record, what is recorded as not performed, what failed and what was done.
5. Name every recorded step the issue does not declare as an unauthorised
   process rather than folding it into the coverage figure.
6. Compute processing coverage and inspection coverage separately, each
   against its own declared minimum.
7. Rank the lot -- no established issue first, then an unrecorded step, then an
   unauthorised step, then a step not performed, then a failure -- so the
   report names the root cause before the consequence.
8. Report the delivery: lots grouped by verdict, the lots actually deliverable,
   the weakest lot and every finding in order.

## Pitfalls

- Grading the traveller before establishing the issue. Every downstream answer
  is then measured against a standard nobody has shown applied.
- Taking the newest issue as the governing one. Work done before it took
  effect was correctly built to the previous issue, and calling that a defect
  buries the lots that really were built to a superseded standard.
- Treating an unreleased draft as a document. A draft has not been reviewed,
  so a lot built to it was built to a proposal.
- Pooling processing and inspection steps. A lot fully built and never
  inspected then scores comfortably and ships unverified.
- Counting an unauthorised step as coverage. It inflates the figure while
  moving the lot further off the standard it claims to follow.
- Reading a step with no record as not performed. They are different states
  dispositioned by different people, and absence is the worse of the two.
- Assuming a superseded issue or a failed step closes the lot either way. Both
  are project positions read from policy, and assuming one produces a verdict
  the project did not agree to.
- Judging a coverage figure that lands exactly on its declared minimum by bare
  arithmetic. It is a quotient of two step counts, so a traveller that
  recorded exactly the owed number can evaluate a unit in the last place below
  the minimum; the comparison absorbs that while the minimum stays as declared.

## Behavior contract (gate 3)

The document and issue-history validation, the issue in force on a processing
day, the five issue standings, the separate processing and inspection coverage
figures against their declared minima, the unauthorised step detector, the
four record states, the superseded-issue and failure policies and the
rolled-up delivery verdict are exercised by the gate 3 contract test:
scripts/test_e2008_deliverable_blocking_diode_components.py against
scripts/e2008_deliverable_blocking_diode_components_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_deliverable_blocking_diode_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
