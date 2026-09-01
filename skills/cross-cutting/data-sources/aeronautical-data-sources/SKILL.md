---
name: aeronautical-data-sources
description: "Use when you must assess an aeronautical engineering data source before relying on it as the engineering reference in a calculation or report: classify the authoritative data type (atmospheric model, aerodynamic database, materials properties, standard part library, regulatory data), check the publisher, edition, and review status, and score source credibility from regulatory, industry, vendor, or community origin. Produces a source registry entry, an approved or review-required verdict, and a credibility score, then format the citation line with publisher, edition, and access date for the engineering report. Trigger: data source, credibility, revision status, publisher, edition, access date, citation line, source registry."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mmpsd
    reference-only: true
  - id: sep-2640
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: data-sources
  tags: [data-source, data-source-registry, credibility, credibility-score, revision, revision-status, status, publisher, edition, access-date, citation-line, authoritative-data-type, review-status, regulatory-data, vendor-source, community-source, materials-properties, atmospheric-model, aerodynamic-database, standard-part-library, engineering-reference]
  version: 0.1.0
  author: AeroSkills
---

# Aeronautical Data Sources (cross-cutting/data-sources/aeronautical-data-sources)

Use when the task is choosing and citing an aeronautical engineering
data source: authoritative data types (atmospheric models,
aerodynamic databases, materials properties, standard part libraries,
regulatory data), publisher class and credibility, revision and
edition control, review status, and the citation line for the report.
This is the cross-cutting data-sources-pack discipline for the source
as evidence; computing values from a specific source (ISA atmosphere,
MMPDS design values, airfoil polars) lives in the leaf that owns that
data.

## Domain quick reference

- Authoritative data types: atmospheric-model,
  aerodynamic-database, materials-properties, standard-part-library,
  regulatory-data. A source that is none of these is "other" and
  needs extra scrutiny before use.
- Publisher classes and credibility: regulatory (airworthiness
  authorities and government reference data) is the highest class,
  industry (standards bodies and professional societies) next, vendor
  (manufacturer catalogs and company data) lower, community (public
  forums and personal pages) lowest.
- Revision control: every source carries an edition or revision
  identifier (Edition 3, Rev B). A superseded edition is not usable as
  the engineering reference. Record the access date because online
  sources change after retrieval.
- Review status: approved, in-review, unreviewed, superseded. Only an
  approved source passes the registry verdict; every other status
  returns review-required.
- Credibility score: regulatory 10, industry 7, vendor 4, community
  2. Superseded sources score 1; in-review and unreviewed sources
  lose 2 points with a floor at 1.
- Citation line: Name, Edition, Publisher, accessed ACCESS_DATE.
  Example: "ESDU 72018, Edition 3, ESDU International, accessed
  2026-09-01."

## Workflow

1. Classify the source type with authoritative_type_ok; an unknown
   type fails the check.
2. Register the source with register_source: name, source_type,
   publisher, publisher_class, edition, review_status, access_date.
3. Run the verdict with source_verdict; review-required means
   re-check the source before use.
4. Score the source with credibility_score; a regulatory source
   scores highest.
5. Format the citation line with format_citation for the report
   references.

## Pitfalls

- Treating a vendor catalog as regulatory-class data: the class comes
  from the publisher, not the topic.
- Using a superseded edition as the engineering reference: the verdict
  is review-required and the score drops to 1.
- Citing without the access date: the citation line always carries the
  access date.
- Registering an unreviewed community source as approved: only the
  approved status passes the verdict.
- Mixing this leaf with the leaf that computes from the data: MMPDS
  appears here only as a materials data source to register and cite;
  computing design values from the data lives in the mmpsd-allowables
  leaf.

## Behavior contract (gate 3)

The registry, credibility, and citation logic is exercised by the
gate 3 contract test: scripts/test_aeronautical_data_sources.py
against scripts/aeronautical_data_sources_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_aeronautical_data_sources.py

## Compliance

- Standards referenced, not reproduced: MMPDS is referenced as an
  example materials data source and SEP-2640 as the delivery context;
  both are proprietary and summary-only per standards-map.yaml. Never
  reproduce design-value tables or standard text.
- compliance: STANDARDS-REF, gated: false.
