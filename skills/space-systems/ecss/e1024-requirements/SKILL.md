---
name: e1024-requirements
description: "Use when structure interface requirements for an Interface Requirements
  Document (IRD) per ECSS-E-ST-10-24C §5.3: categorize each requirement as
  functional, physical, environmental, or data-characteristic, verify that every
  requirement carries a unique identifier, text, rationale, and verification method,
  check that each interface is covered across all four mandatory requirement
  categories, and flag incomplete or missing coverage. Applicable at any level where
  two items exchange signals, mechanical loads, thermal energy, or data streams.
  Trigger: ecss, e-st-10-system-scope, ird, interface-requirements,
  functional-requirements, physical-requirements, environmental-requirements,
  data-characteristics."
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
  tags: [ecss, e-st-10-system-scope, ird, interface-requirements, functional-requirements, physical-requirements, environmental-requirements, data-characteristics]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Management — Interface Requirements (space-systems/ecss/e1024-requirements)

Use when the task is to structure and check interface requirements under
ECSS-E-ST-10-24C §5.3 — organizing every requirement into one of four
mandatory categories, confirming each requirement is fully formed, and
verifying that no category is left uncovered for a given interface.

## Domain quick reference

- ECSS-E-ST-10-24C §5.3 requires that each interface be governed by an
  Interface Requirements Document (IRD) which captures requirements in
  four mandatory categories: functional (what the interface shall
  accomplish — signal types, commands, data flows, power transfer),
  physical (mechanical and dimensional attributes — connector type,
  pinout, mounting envelope, harness routing), environmental (conditions
  at the interface boundary — temperature range, vibration levels, EMC
  emission and susceptibility limits, radiation tolerance), and data
  characteristics (protocol, packet format, data rate, encoding, timing
  margins, error detection).
- Each requirement within an IRD must carry a unique identifier, a
  requirement text stated in "shall" form, a rationale that traces the
  requirement to a higher-level obligation, and a declared verification
  method (analysis, test, inspection, or review of design).
- An IRD is coverage-complete for a given interface when at least one
  requirement exists in each of the four categories and no requirement
  is missing a mandatory field. A requirement with an unrecognized
  category cannot be counted toward coverage.

## Workflow

1. Enumerate every interface to be documented and assign each one a
   unique interface identifier; the IRD scope is one interface per
   document.
2. For each interface, inventory all candidate requirements and assign
   each a category: functional, physical, environmental, or
   data_characteristic. Reject a requirement whose category falls
   outside the four recognized types before it enters the IRD.
3. Validate the mandatory fields on every requirement — unique id,
   non-empty text, category, rationale, and verification method. Flag
   any requirement that is missing a field or has an empty value.
4. Check category coverage: verify that at least one valid requirement
   exists in each of the four mandatory categories. Record a coverage
   gap for any category with no entry.
5. Check identifier uniqueness within the interface: flag any id that
   appears on more than one requirement.
6. Aggregate the field issues, coverage gaps, and duplicate-id findings
   per interface. The interface is IRD-compliant only when all three
   finding lists are empty.

## Pitfalls

- Merging two interfaces into one IRD to avoid writing a fourth
  coverage entry — each IRD must describe exactly one interface;
  merging hides missing requirements and breaks traceability.
- Using a category label outside the four recognized types (e.g.,
  "optical", "thermal_control") — the requirement cannot be counted
  toward coverage and its category is flagged as invalid.
- Leaving the verification method blank or set to a free-text note
  rather than one of the accepted methods (analysis, test, inspection,
  review) — the field check will flag it as empty if the value is
  missing, and a non-empty but unrecognized method is a reviewer
  finding.
- Treating a rationale that says "TBD" as populated — although this
  logic checks only for an empty string, a rationale that defers
  content is itself a finding at review; capture a substantive
  rationale at the requirement-definition stage.

## Behavior contract (gate 3)

The requirement categorization, field validation, category-coverage
check, and duplicate-identifier detection logic is exercised by the
gate 3 contract test: scripts/test_e1024_requirements.py against
scripts/e1024_requirements_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1024_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
