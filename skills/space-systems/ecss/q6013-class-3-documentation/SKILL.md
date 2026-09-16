---
name: q6013-class-3-documentation
description: "Use when a lowest assurance parts file has to be judged fit to keep. Audit whether the reduced document file kept for a class 3 commercial part activity is complete, custodied and reachable under ECSS-Q-ST-60-13C clause 6.7: refuse a document with no recognized type, identifier, issue, date or custody mode, name every minimum document the file never produced, list the documents kept above the minimum without letting them cover a shortfall, treat a minimum document the supplier holds with no access commitment as one the project cannot produce, derive each retention end from the document date in whole years against the horizon the project has to reach, and report minimum-set completeness as a fraction judged at unity under a named tolerance. Trigger: ecss, q-st-60-13c-clause-6-7, class-3-parts-document-file, minimum-kept-document-set, supplier-held-document-access, class-3-retention-horizon, minimum-set-completeness-fraction."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-3-documentation, q-st-60-13c-clause-6-7, class-3-parts-document-file, minimum-kept-document-set, supplier-held-document-access, class-3-retention-horizon, minimum-set-completeness-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 3 Commercial Parts — Documentation (space-systems/ecss/q6013-class-3-documentation)

Use when the task is the documentation provision of ECSS-Q-ST-60-13C clause
6.7 — the short set of documents a commercial electrical, electronic and
electromechanical part activity keeps at the lowest assurance level, who
physically holds each one, and whether the project can still put its hands on
them when somebody asks.

## Domain quick reference

- The class 3 set is short on purpose. At the lowest assurance level the file
  proves what was bought, what arrived, what went wrong and where the part
  ended up — not that the part was evaluated, screened or lot-accepted,
  because at this level it was not.
- A short set is not a soft set. Every one of the few documents kept is
  load-bearing precisely because there is nothing else to fall back on, so a
  single absent minimum document costs a fifth of the file rather than a
  tenth.
- Custody is the class 3 question the higher levels rarely have to ask.
  Catalogue procurement leaves much of the paper with the supplier, so where
  a document lives, and whether the project has a written claim on it, decide
  whether it is evidence or a rumour.
- A supplier holding a document with no access commitment is the same as no
  document, for the only purpose that matters: producing it on request. The
  file can be nominally full and effectively short at the same time, which is
  why coverage is reported twice — as held, and as reachable.
- Documents above the minimum are welcome and never count. A file carrying a
  voluntary evaluation report but no as-built parts list is short an as-built
  parts list; generosity in one place does not settle a gap in another.
- Retention is two questions. How long the document is kept, and whether
  keeping it that long reaches the date the project has to reach. Whole-year
  calendar arithmetic answers both exactly and survives a leap-day document.

## Workflow

1. Validate the activity: the part number, the supplier it came from and the
   project keeping the file.
2. Validate every document — type, identifier, issue, date, custody mode,
   whole-year retention and the parts it covers — and reject a type declared
   twice in one file.
3. Compare the class 3 minimum set with the types present, name each absent
   minimum document, and list the above-minimum documents separately.
4. Judge custody: flag each minimum document the supplier holds with no
   access commitment, and each supplier-access document with no reference to
   the clause granting that access.
5. Derive each retention end from the document's own date and its whole-year
   retention, compare the retention against the floor and the end against the
   required horizon, and keep both findings when both apply.
6. Report held completeness and reachable completeness as separate fractions,
   both judged at unity under a named tolerance, with a verdict carrying
   every finding.

## Pitfalls

- Importing the class 1 record list. Demanding screening and lot-acceptance
  reports from a class 3 activity manufactures findings against documents
  nobody was ever asked to produce.
- Counting a document the supplier holds as held. It is only evidence if the
  project can produce it, and the second fraction is what shows the
  difference.
- Accepting a supplier-access claim with nothing behind it. An access promise
  with no clause reference evaporates at exactly the moment it is needed.
- Letting an above-minimum document paper over an absent one. The sets are
  scored separately for this reason.
- Reading a long retention as sufficient. Retention runs from the document's
  own date, so an early document with a generous period can still expire
  before a late one with a short period.
- Stopping at the first finding. The file owner needs the whole list to close
  it in one pass rather than one pass per finding.

## Behavior contract (gate 3)

The activity validation, per-document validation, custody judgement,
retention-end derivation and horizon comparison, minimum-set coverage, the
held and reachable completeness fractions and the overall fit-to-keep verdict
are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_documentation.py against
scripts/q6013_class_3_documentation_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
