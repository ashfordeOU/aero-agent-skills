---
name: e2040-device-requirements-specification-data-item
description: "Audit a device requirements specification against the contents ECSS-E-ST-20-40C Annex A makes mandatory: confirm the function, performance, interface and quality areas all exist and that none is an empty heading, then read every statement for an identifier and a nominated verification method, a quantity with a unit on each performance line, a named counterpart on each interface line and an acceptance criterion on each quality line, and report wording no method can answer. Use when a device specification is being drafted or reviewed for acceptance. Trigger: ecss, e-st-20-electrical-scope, device-requirements-specification-data-item, mandatory-content-area, performance-quantity-and-unit, interface-counterpart-naming, quality-acceptance-criterion, unverifiable-requirement-wording."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-requirements-specification-data-item, device-requirements-specification-data-item, mandatory-content-area, performance-quantity-and-unit, interface-counterpart-naming, quality-acceptance-criterion, unverifiable-requirement-wording]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Requirements Specification Data Item (space-systems/ecss/e2040-device-requirements-specification-data-item)

Use when the task is the contents duty of ECSS-E-ST-20-40C Annex A --
saying whether a device requirements document actually holds what the
data item asks for, across the function it performs, the performance it
reaches, the interfaces it presents and the quality it has to hold.

## Domain quick reference

- The data item is a contents list, so the first pass is presence: all
  four mandatory areas exist. The second pass is the one worth having,
  because a heading with nothing under it passes the first pass and
  delivers nothing. Absent and empty are separate findings and they
  have different fixes.
- Headings differ between organisations. "Functional requirements",
  "Functions" and "function" are one area, and folding them before
  counting is what stops the same content being read as two areas or
  as none. Two headings that fold onto the same area are a document
  defect, not something to merge silently.
- Every statement needs an identifier and a nominated verification
  method. Without an identifier nothing downstream can cite it; without
  a method from analysis, review-of-design, inspection or test, the
  statement has no route to being closed.
- Each area adds its own demand. A performance statement without a
  value and a unit cannot be verified by any method. An interface
  statement that does not name what it interfaces TO describes half a
  boundary. A quality statement with no acceptance criterion states an
  aspiration.
- Unverifiable wording is caught in the same pass. "Adequate margin",
  "as required", "suitable" and their relatives read like requirements
  and cannot be answered by analysis, inspection, review or test, so
  they are reported rather than counted as content.
- Identifiers have to be unique across the whole document, not just
  within an area. A repeated identifier breaks the trace in both
  directions, and it is invisible while each area is read alone.

## Workflow

1. Fold every heading onto one of the four content areas, keeping any
   unrecognised heading as an extra rather than refusing it. Extras are
   allowed and are reported so the reader can see them.
2. Report a mandatory area that is absent and, separately, one whose
   heading exists with no statement under it.
3. Resolve each statement and refuse a malformed one outright: an
   unknown key, a non-string identifier, a numeric field that is not a
   number. These are input defects, not document findings.
4. Read every statement for the two universal demands, an identifier
   and a verification method, and refuse a method outside the four.
5. Apply the per-area demand: a value and unit for performance, a named
   counterpart for interface, an acceptance criterion for quality.
6. Scan the statement text for wording no method can answer, matching
   whole terms so that a word merely containing one does not trip.
7. Check identifier uniqueness across the whole document, then score
   each area by the fraction of its statements carrying no finding and
   average the four into the document score.

## Pitfalls

- Closing the review on headings. A document can carry all four
  headings, score full marks on presence, and hold nothing a verifier
  could act on.
- Accepting a performance requirement with no number. It reads like a
  requirement, survives review, and then cannot be closed by any of
  the four methods when verification planning starts.
- Letting an interface requirement stand without its counterpart. Both
  sides of the boundary then assume the other owns the definition, and
  the gap is found at integration.
- Reading a quality statement as self-evident. Without the criterion it
  is accepted against, the acceptance decision moves to whoever reads
  it last.
- Checking identifier uniqueness inside each area only. Duplicates
  across areas are the ones that survive, and they break the trace
  exactly where the verification matrix is built.

## Behavior contract (gate 3)

The heading folding, presence and emptiness checks, statement
validation, per-area demands, vague-wording scan, uniqueness check and
scoring are exercised by the gate 3 contract test:
scripts/test_e2040_device_requirements_specification_data_item.py
against
scripts/e2040_device_requirements_specification_data_item_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2040_device_requirements_specification_data_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
