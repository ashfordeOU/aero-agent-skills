---
name: e2040-final-application-procurement-documents
description: "Verify that the closing versions of the documents used to apply and to procure the device can actually be released. Use when an ECSS-E-ST-20-40C clause 5.8.5 document set is being issued: resolve what the procurement route owes, check each document is present, at final issue and approved, compare every revision against the one carried from the previous phase to catch a reissue that never advanced or went backwards, confirm each names the delivered article, and report the application and procurement halves separately. Refuses an unknown route, a non-numeric revision segment and a duplicate document. Trigger: ecss, e-st-20-40c, final-application-procurement-documents, device-procurement-route-applicability, closing-document-final-issue, document-revision-advance-check, delivered-article-document-consistency, escc-detail-specification-release."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-final-application-procurement-documents, device-procurement-route-applicability, closing-document-final-issue, document-revision-advance-check, delivered-article-document-consistency, escc-detail-specification-release]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Final Application and Procurement Documents (space-systems/ecss/e2040-final-application-procurement-documents)

Use when the task is the closing document issue of ECSS-E-ST-20-40C clause
5.8.5 — releasing the final versions of the documents a user needs to apply
an ASIC, FPGA or IP core and a buyer needs to procure it, and deciding
whether that set is releasable.

## Domain quick reference

- The owed set follows the procurement route, not the device alone. A
  part going through formal evaluation owes a detail specification; an
  IP core delivered under licence owes a licence and delivery
  specification instead and owes no detail specification at all.
  Demanding the wrong one of those is the commonest finding here, and it
  is always wrong in both directions at once.
- The set has two halves that fail independently. The application
  documents let an integrator use the device; the procurement documents
  let a buyer order it. A clean data sheet with a draft procurement
  specification blocks buying, not using, and saying so is more useful
  than one aggregate verdict.
- A closing document that reissues the previous phase revision has
  changed content without saying it changed. That is the defect this
  check exists to catch: the revision is the only signal a downstream
  reader has that the document they cached is stale.
- Revisions are numeric, not textual. Revision 2.10 follows 2.9, and a
  string comparison puts them the other way round, so the comparison
  parses the dotted segments and pads the shorter one rather than
  comparing characters.
- Every document in the set describes one article. A data sheet still
  naming the engineering model tells the integrator about a device that
  was not delivered, so the delivered configuration is checked across
  the whole set and not only on the specification.

## Workflow

1. Normalise the procurement route and derive the owed document set from
   it. An unknown route is an input error, not a default to the widest
   set.
2. Validate each document: a name outside the closing set, an unknown
   issue state, a non-numeric or empty revision segment, a missing
   configuration reference, a non-boolean approval flag or a duplicate
   issue is refused rather than scored.
3. Collect the owed documents that are absent, and separately the
   documents issued that the route does not owe.
4. Collect the owed documents not at final issue, and those not
   approved; they are different recoveries.
5. Compare each revision with the one carried from the previous phase.
   Report a revision that did not advance separately from one that went
   backwards — the first is an omission, the second is a mix-up of two
   document copies.
6. Compare every document configuration reference with the delivered
   configuration and collect the mismatches.
7. Report the application and procurement halves separately, then return
   released only when no finding stands at all.

## Pitfalls

- Applying one fixed document list to every device. The route
  applicability step is the first thing this check does, and skipping it
  demands an evaluation specification of a soft IP core.
- Comparing revisions as strings. Lexicographic order puts 2.9 above
  2.10 and turns a real advance into a reported regression.
- Treating an unchanged revision as harmless because the issue state
  says final. The issue state says the document is closed; the revision
  is what tells a reader whether their copy is the closed one.
- Folding a revision regression into the same finding as a revision that
  did not advance. A regression usually means two copies of the document
  were merged the wrong way round, and it needs a different fix.
- Reporting one aggregate verdict over both halves. The buyer and the
  integrator are blocked by different documents, and the aggregate hides
  which of them can proceed.
- Checking the delivered article only on the procurement specification.
  A data sheet naming the engineering model misleads every integrator
  who reads it.

## Behavior contract (gate 3)

Route applicability, document validation, final-issue and approval checks,
numeric dotted-revision parsing and comparison against the previous phase,
delivered-article consistency across the set, the application and
procurement split and the release decision are exercised by the gate 3
contract test: scripts/test_e2040_final_application_procurement_documents.py
against scripts/e2040_final_application_procurement_documents_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2040_final_application_procurement_documents.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
