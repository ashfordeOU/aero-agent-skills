---
name: e1011-iso-index
description: "Use when identify the applicable ISO and European standards that support an ECSS-E-ST-10-11C human factors engineering (HFE) requirement: map each HFE topic area to the relevant indexed standards (ISO 9241 series, ISO 10075, ISO 11064, ISO 14738, EN 614, EN 894), confirm every topic area in the HFE design plan has at least one indexed standard on record, and flag any topic area with no indexed standard so the coverage gap can be resolved before the HFE plan is accepted. Trigger: ecss, e-st-10-system-scope, hfe, iso-9241, iso-10075, iso-11064, human-factors, ergonomics, hfe-standards-index, annex-e."
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
  tags: [ecss, e-st-10-system-scope, hfe, iso-9241, iso-10075, iso-11064, human-factors, ergonomics, hfe-standards-index, annex-e]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS HFE — ISO and European Standards Index (space-systems/ecss/e1011-iso-index)

Use when the task is identifying which ISO and European standards support a
specific HFE topic area under ECSS-E-ST-10-11C — querying the Annex E
reference catalog to retrieve matching standards, confirming every topic in
an HFE design plan has at least one indexed reference, and flagging any
topic area that is not yet covered by an entry in the index.

## Domain quick reference

- Annex E of ECSS-E-ST-10-11C is an informative (non-normative) annex that
  lists related ISO and European standards as supporting references for HFE
  activities. The annex is a reference aid; HFE activities remain governed
  by the normative clauses of ECSS-E-ST-10-11C.
- The index organises standards into HFE topic areas. The principal topic
  areas and their associated standard families are:
  - **Anthropometry and workstation layout** — ISO 11064-4 (control centre
    workstation dimensions), ISO 14738 (anthropometric requirements at
    machinery), EN 614-1 (ergonomic design principles).
  - **Display design and physical input** — ISO 9241-110 (dialogue
    principles), ISO 9241-400 (physical input devices), ISO 11064-1
    (control centre display layout), EN 894-2 (display ergonomics).
  - **Cognitive ergonomics and mental workload** — ISO 9241-110,
    ISO 10075-1 and ISO 10075-2 (mental workload concepts and design).
  - **Human-centred design and context of use** — ISO 9241-11 (usability
    definitions), ISO 9241-210 (human-centred design process).
  - **Environmental ergonomics** — ISO 7933 (thermal stress).
- Each standard record in the index carries: a standard identifier (e.g.
  "ISO 9241-11"), a short descriptive title, and a set of HFE topic tags
  (e.g. "anthropometry", "display_design", "mental_workload").
- A coverage gap occurs when an HFE topic area named in the design plan has
  no matching record in the index. A gap does not automatically indicate a
  design deficiency; it may mean the index needs updating. The gap must be
  reviewed before the HFE plan is accepted.

## Workflow

1. For each HFE topic area named in the design plan or HFE requirement,
   query the index with the topic tag and retrieve every standard whose
   record includes that tag. Record the standard identifiers and titles as
   the supporting references for that topic area.
2. For any topic area whose query returns an empty result, record a coverage
   gap. Do not suppress a gap on the assumption that a relevant standard
   exists but is absent from the index — the gap must be surfaced explicitly.
3. For each standard identifier explicitly cited in the design document
   (e.g. "ISO 9241-11"), look up the identifier in the catalog to confirm it
   is a registered entry; flag any identifier that does not resolve. An
   unresolved identifier must not be propagated into the HFE plan without
   resolution.
4. Produce a coverage summary with three sections: (a) topic areas covered,
   each with the list of matching standard identifiers; (b) topic areas with
   coverage gaps, each requiring a review action; (c) any explicitly cited
   standard identifiers that did not resolve in the catalog.
5. Treat the informative annex as a reference aid only — if a topic has
   been addressed in the normative clauses without an Annex E entry, the
   normative treatment takes precedence. Record the absence in the coverage
   summary and do not raise a non-compliance finding solely on that basis.

## Pitfalls

- Treating the informative annex as normative — the index is a reference
  aid; each HFE activity is governed by the normative clauses of
  ECSS-E-ST-10-11C, not by the standards listed in Annex E.
- Reporting "no gaps" for a topic area that was never checked — a topic
  that was never queried against the index is indistinguishable from a topic
  that has no match unless the check is performed explicitly for every topic
  in scope.
- Using a partial standard identifier (e.g. "ISO 9241" without a part
  number) to look up a record — the index registers each part individually;
  a bare family name does not resolve to a single entry and will raise an
  error.
- Treating a coverage gap as a design non-compliance — a gap indicates the
  index may need a new entry, not that the design is wrong; the correct
  response is a review action, not a non-compliance finding.
- Assuming that all ISO 9241 parts are present — the index holds specific
  parts (e.g. "-11", "-110", "-210", "-400"); a query for an unlisted part
  will return an empty list.

## Behavior contract (gate 3)

The catalog lookup, topic-to-standard mapping, coverage-check, and
gap-detection logic is exercised by the gate 3 contract test:
scripts/test_e1011_iso_index.py against scripts/e1011_iso_index_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1011_iso_index.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
