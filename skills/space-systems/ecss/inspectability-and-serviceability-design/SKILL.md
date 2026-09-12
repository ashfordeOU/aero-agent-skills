---
name: inspectability-and-serviceability-design
description: "Use when assess the inspectability, interchangeability, maintainability, and dismountability of spacecraft structural design under ECSS-E-ST-32C clauses 4.5.1–4.5.4: categorize each structural joint or component by its inspection access method and verify the access clearance meets the minimum for the selected inspection tool, verify replaceable parts carry fully defined interface tolerances with no manual fit or adjustment required, confirm every planned maintenance action has defined access clearance, tooling, and procedure on record, and verify joints intended for repeated dismounting are designed for the required assembly–disassembly cycle count without damage or galling. Trigger: ecss, e-st-32-structures-scope, inspectability, interchangeability, maintainability, dismountability, serviceability, structural-design, nde-access."
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
  tags: [ecss, e-st-32-structures-scope, inspectability, interchangeability, maintainability, dismountability, serviceability, nde-access]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structural Design — Inspectability and Serviceability Design (space-systems/ecss/inspectability-and-serviceability-design)

Use when the task is the serviceability design assessment of ECSS-E-ST-32C
clauses 4.5.1–4.5.4 — verifying that structural joints and components
are accessible for inspection, that replaceable parts are fully
interchangeable, that maintenance actions are supportable by the design,
and that joints intended for repeated disassembly are rated for the
required cycle count without galling or damage.

## Domain quick reference

- Clause 4.5.1 (Inspectability): Every structural joint or member
  designated as critical shall carry an inspection access method and
  adequate clearance for that method. The four recognised methods are
  direct visual inspection (minimum 50 mm clearance), borescope
  (minimum 15 mm), ultrasonic probe (minimum 5 mm contact clearance),
  and eddy current (minimum 5 mm). A primary or secondary structural
  element with no identified access path is a finding regardless of
  analysis confidence.
- Clause 4.5.2 (Interchangeability): Parts designed for in-service
  replacement shall be fully interchangeable. Interface dimensions and
  tolerances shall be completely defined in engineering drawings so that
  any conforming replacement unit installs without manual fitting,
  shimming, or custom adjustment.
- Clause 4.5.3 (Maintainability): The structural design shall provide
  the clearances and access needed to perform every planned maintenance
  action (inspection, replacement, repair, lubrication, adjustment).
  Required tooling and a documented procedure shall be on record for
  each action; missing either is a finding.
- Clause 4.5.4 (Dismountability): Joints intended for disassembly shall
  be designed for the number of assembly–disassembly cycles required by
  the programme. For material combinations with known galling risk
  (same-family metals under clamp load — aluminium/aluminium,
  stainless steel/stainless steel, titanium/titanium, inconel/stainless
  steel), an anti-galling treatment (silver plating, dry-film lubricant,
  or equivalent) shall be specified; its absence is a finding.

## Workflow

1. Inventory every structural joint and component. Assign each a
   criticality (primary, secondary, non_structural). Non-structural
   items have no inspectability, interchangeability, or dismountability
   requirements; skip to step 5 for them.
2. For each primary or secondary joint, identify the inspection method
   and measure the available access clearance. Flag any joint with no
   identified method, and any joint whose clearance falls below the
   minimum for its assigned method.
3. For each component marked as replaceable, confirm that interface
   tolerances are fully defined in the drawing set and that no manual
   adjustment is required for fit. Flag any replaceable part that fails
   either check.
4. For each planned maintenance action, record the action type
   (inspection, replacement, repair, lubrication, adjustment), the
   available access clearance, the defined tooling set, and the
   procedure document reference. Flag any action whose clearance is
   below the minimum for that action type, any action with no tooling
   defined, and any action with no procedure document.
5. For each joint rated for in-service dismounting, confirm the design
   cycle count meets or exceeds the programme requirement. Identify
   the fastener and mating-part material pair; if the pair is on the
   galling-risk list, confirm an anti-galling treatment is specified.
   Flag insufficient cycle rating and any missing treatment separately.
6. Aggregate findings by category (inspectability, interchangeability,
   maintainability, dismountability). The item is serviceability-
   compliant only when all four finding lists are empty.

## Pitfalls

- Treating analysis-based acceptance as a substitute for inspection
  access — clause 4.5.1 requires a physical access path for critical
  joints; a positive margin of safety does not replace inspectability.
- Recording "no adjustment required" without specifying tolerances —
  interchangeability requires both: the tolerance definition enables the
  claim that adjustment is unnecessary.
- Logging a maintenance action as defined when only the tooling exists
  but no procedure, or vice versa — both are required; each absence is
  an independent finding.
- Assuming galling risk applies only to identical metals — inconel
  against stainless steel is also on the risk list; always look up the
  pair, not just whether the two materials are the same.

## Behavior contract (gate 3)

The inspectability-access categorization, inspectability clearance
check, interchangeability tolerance and adjustment check, maintainability
clearance/tooling/procedure check, dismountability cycle and anti-galling
check, and full serviceability review logic are exercised by the gate 3
contract test: scripts/test_inspectability_and_serviceability_design.py
against scripts/inspectability_and_serviceability_design_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_inspectability_and_serviceability_design.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
