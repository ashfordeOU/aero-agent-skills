---
name: e2006-charging-standard-cross-references
description: "Use when audit the applicable-document tree of a spacecraft-charging activity under ECSS-E-ST-20-06C clause 4.2: parse each ECSS identifier into branch, document kind, discipline, issue and revision, confirm the charging standard sits in the engineering branch under the electrical-and-electromagnetic discipline, map every charging-analysis topic onto the normative reference that governs it, and screen the declared applicable-document list for missing references, malformed identifiers, duplicate roots, superseded issues and supplementary entries. Trigger: ecss, e-st-20-06c, normative-reference-resolution, applicable-document-tree, ecss-document-identifier, engineering-branch-placement, issue-and-revision-check, superseded-issue-detection, charging-standard-cross-reference."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-charging-standard-cross-references, e-st-20-06c, normative-reference-resolution, applicable-document-tree, ecss-document-identifier, engineering-branch-placement, superseded-issue-detection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Standard Cross-References (space-systems/ecss/e2006-charging-standard-cross-references)

Use when the task is clause 4.2 of ECSS-E-ST-20-06C: placing the
charging standard inside the ECSS document tree and pinning down the
related standards a charging activity depends on, so that a project's
applicable-document list can be audited against the topics it actually
covers.

## Domain quick reference

- An ECSS identifier is structured, not opaque. ECSS-E-ST-20-06C reads
  as engineering branch (E), standard kind (ST), discipline 20
  (electrical and electromagnetic), sub-discipline 06 (the charging
  document), issue C. Other kinds exist in the same grammar — HB for a
  handbook, TM for a technical memorandum — and an issue may carry a
  revision suffix. Parsing the identifier is what makes placement,
  issue comparison and duplicate detection mechanical instead of
  eyeballed.
- Placement is a two-part check: the branch letter and the discipline
  number. A charging document that parses into the product-assurance
  branch, or into the engineering branch but a thermal-control
  discipline, has been mis-cited; both halves are reported separately
  because they fail for different reasons.
- The charging activity does not stand alone. The plasma environment it
  assumes comes from the space-environment standard, the interference
  consequences land in the electromagnetic-compatibility standard, the
  surface properties that drive secondary-electron-emission and
  photoemission come from the materials and thermal-control coating
  standards, part-level electrostatic-discharge control comes from the
  parts branch, and the vocabulary comes from the glossary standard.
  Each analysis topic therefore resolves to exactly one governing
  reference; an unrecognized topic is rejected rather than resolved to
  a default.
- Two identifiers of the same document differ only in issue letter and
  revision, so they are directly comparable. A declared issue older
  than the registered one is superseded and is a finding; a newer issue
  is allowed but noted, because tailoring has to be confirmed before a
  later issue is used in place of the registered one.
- Two entries that share a branch, kind, discipline and sub-discipline
  are the same document regardless of issue. Counting them as two
  distinct references is how an applicable-document list ends up
  claiming coverage twice at two different issues.

## Workflow

1. Parse the anchor standard and confirm its placement: engineering
   branch, electrical and electromagnetic discipline. Report a branch
   mismatch and a discipline mismatch as separate findings.
2. List the charging-analysis topics in scope and resolve each one to
   its governing normative reference. Reject an unrecognized topic.
   Deduplicate into the required-reference set.
3. Parse every entry of the project's declared applicable-document
   list. An entry that does not parse is isolated as malformed and is
   excluded from the coverage arithmetic — it cannot be credited
   against a required reference.
4. Collapse the parsed entries by document root. A second entry on a
   root already seen is a duplicate, whatever its issue.
5. For each required reference, find the declared entry on the same
   root. No entry is a missing reference; an older issue is superseded;
   a newer issue is a note, not a finding.
6. Entries on roots no topic required are supplementary — reported as
   notes so they are visible without failing the tree.
7. The tree is compliant only when the placement holds and the
   malformed, duplicate, missing and superseded lists are all empty.

## Pitfalls

- Matching applicable documents by exact string. ECSS-E-ST-20-07B and
  ECSS-E-ST-20-07C are the same document at two issues; a string match
  reports the required one as missing and the declared one as
  supplementary, hiding the real finding, which is that the tree names
  a superseded issue.
- Crediting a malformed entry. A free-text line in the list is not a
  reference; counting it as coverage lets a required standard vanish
  from the findings.
- Treating a newer declared issue as a defect. It is acceptable with
  confirmed tailoring, so it belongs in the notes; treating it as a
  hard finding trains reviewers to ignore the report.
- Comparing the issue of two different documents. The comparison is
  only defined on a shared root, and forcing it produces a confident
  ordering of two unrelated standards.
- Assuming the charging standard carries the environment definition
  itself. The plasma model it uses is normative elsewhere; dropping
  that reference from the tree leaves the analysis without an agreed
  environment.

## Behavior contract (gate 3)

The identifier parser, round trip, issue comparison, branch and
discipline placement, topic resolution and applicable-document audit
are exercised by the gate 3 contract test:
scripts/test_e2006_charging_standard_cross_references.py against
scripts/e2006_charging_standard_cross_references_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_charging_standard_cross_references.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
