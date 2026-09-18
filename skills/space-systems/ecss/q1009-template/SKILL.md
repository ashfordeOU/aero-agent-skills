---
name: q1009-template
description: "Evaluate a candidate nonconformance report form against the informative template of ECSS-Q-ST-10-09 Annex C, whose headings and fields follow the normative Annex A data item. Use when a project is adopting or reviewing its default NCR form: refuse a form carrying no section for a content group the data item fixes, weigh field coverage as the mean over the groups rather than a count of fields found, measure a re-sequenced form as an inversion share against the annex order, record local additions as deviations rather than errors, and keep what the informative form permits apart from what the normative content still owes. Trigger: ecss, q-st-10-09-annex-c, ncr-report-form-heading-coverage, ncr-report-form-field-coverage, ncr-report-form-order-inversion-share, ncr-report-form-local-deviation."
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
  tags: [ecss, q-st-10-09-nonconformance-control-scope, q1009-template, q-st-10-09-annex-c, ncr-report-form-heading-coverage, ncr-report-form-field-coverage, ncr-report-form-order-inversion-share, ncr-report-form-local-deviation, ncr-report-form-default-pattern]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — NCR Report Template (space-systems/ecss/q1009-template)

Use when the task is Annex C of ECSS-Q-ST-10-09: a project is adopting
the report form the annex offers, or grading the form it already uses
against it. The annex is informative and the content it lays out is not,
which is what the grading has to keep apart.

## Domain quick reference

- A heading is a container for content. A form adopting the pattern
  carries a section for every content group the Annex A data item fixes,
  and a form dropping the requirement-not-met heading has dropped the
  content rather than simplified the layout.
- Fields are weighed by what the group holds. A group asking for four
  fields and a group asking for two are not equally covered by one field
  each, so the figure is the weighted mean across the groups and not a
  tally of fields found anywhere on the form.
- A content group belongs in one section. Laying the same group out
  twice leaves two places to fill it in and two answers on file, so it
  is refused rather than counted twice.
- Order is a deviation, not a defect. Re-sequencing an informative form
  changes nothing the data item demands, so the difference is measured
  as an inversion share against the annex sequence and recorded; a
  heavily re-sequenced form is still accepted, with the share reported.
- Local sections are additions. A project form carrying its own routing
  block still follows the pattern, and the addition belongs on the
  deviation list so the record of what was adopted is complete — unless
  a project has decided its form carries nothing extra.
- Accepted and accepted-as-is are different answers. A form matching the
  pattern exactly is the default; a form with tolerated gaps, additions
  or a changed order is adopted with its deviations named.

## Workflow

1. Validate the grading policy first: the heading coverage demanded, the
   field coverage demanded, the inversion share expected to be recorded,
   and whether local sections are permitted. A policy asking for more
   field coverage than heading coverage is refused, because it demands
   fields inside sections the form need not carry.
2. Validate the candidate form: a reference, a heading on every section,
   a recognised content group where one is mapped, no field named twice,
   no heading twice, and no content group laid out twice.
3. Take the mapped groups in form order, the groups with no heading at
   all, and the heading coverage.
4. Take the field gaps group by group and the weighted field coverage
   across the whole pattern, counting a dropped group as carrying none
   of its fields.
5. Take the inversions against the annex sequence and the share of the
   pairs that could have been inverted.
6. Collect the deviations: tolerated field gaps, local additions and a
   changed order.
7. Close on one verdict in order: template not supplied, required
   heading missing, field coverage short, template accepted with
   deviations, or template accepted as the default pattern. Report the
   coverages, the gaps, the additions and the inversion share alongside
   it.

## Pitfalls

- Grading an informative annex as though it were normative. The form may
  be adapted; the content it carries may not, and conflating the two
  either blocks a sound project form or waves through a missing field.
- Counting fields across the form. Ten fields in the identification
  block do not cover a disposition section with none, which is why the
  coverage is weighted by group.
- Reading a re-sequenced form as non-compliant. The inversion share is
  the measurement, and its purpose is to be recorded rather than to
  fail the form.
- Leaving local additions off the deviation list. They are permitted and
  they are still deviations, and a later audit reads the list, not the
  intent.
- Letting one content group appear under two headings. Two places to
  fill it in becomes two different answers on the same report.

## Behavior contract (gate 3)

The policy validation, section validation, the mapped and missing
content groups, heading coverage, per-group field gaps, the weighted
field coverage, the order inversions and their share, the local-section
handling, the deviation list and the template verdict are exercised by
the gate 3 contract test: scripts/test_q1009_template.py against
scripts/q1009_template_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q1009_template.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
