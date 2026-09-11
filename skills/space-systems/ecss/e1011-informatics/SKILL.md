---
name: e1011-informatics
description: "Use when evaluate on-board informatics support for a crewed space system under ECSS-E-ST-10-11C §4.8: categorize each display element as numerical, graphical, status_text, alert, or control; determine alert urgency level from hazard severity and time criticality; check display format compliance against minimum contrast ratio and character height thresholds; and assess automation authority to confirm crew override is available for supervisory and autonomous operating modes. Flag every display format shortfall, alert level mismatch, and missing crew override before the workstation is accepted. Trigger: ecss, e-st-10-11c, informatics, hfe, display-design, alerts, automation-authority, crew-interface, workstation-review."
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
  tags: [ecss, e-st-10-11c, informatics, hfe, display-design, alerts, automation-authority, crew-interface]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS HFE — On-Board Informatics Support (space-systems/ecss/e1011-informatics)

Use when the task is evaluation of informatics support for a crewed space
workstation per ECSS-E-ST-10-11C §4.8 — checking display element types,
alert urgency tiers, display legibility, and automation authority against
the HFE requirements for on-board data systems, software interfaces, and
crew-automation interaction.

## Domain quick reference

- §4.8 groups display elements into five functional types: **numerical**
  readouts (measured or computed values), **graphical** trend and map
  displays, **status_text** indicators (mode, state, label), **alert**
  indicators (crew-attention demands), and **control** elements (input
  widgets). An element must be placed in exactly one type before its
  legibility is assessed.
- Alert urgency is tiered into three levels. A **warning** demands
  immediate crew action and applies when hazard severity is high and
  corrective action must begin within seconds. A **caution** requires
  timely action (minutes available) and covers high-to-medium severity
  situations not demanding split-second response. An **advisory** covers
  all remaining combinations where crew awareness is needed but no
  time-critical action is required. The declared tier on any alert
  indicator must match the outcome of this hazard-severity ×
  time-criticality mapping.
- Display legibility is governed by two minimum thresholds: luminance
  contrast ratio (text or symbol against background, minimum 4.5) and
  character height (minimum 3.5 mm at design viewing distance up to
  700 mm). Both must be satisfied; failing either is a format violation.
- Automation authority is assigned one of four levels: **advisory**
  (system informs, crew decides and acts), **shared_control** (crew and
  system jointly execute), **supervisory** (crew sets goals, system
  executes steps), **autonomous** (system acts without crew input). At
  supervisory and autonomous levels the crew must retain a documented
  override capability; its absence is an authority violation.

## Workflow

1. Inventory every display element on the workstation and categorize each
   one into numerical, graphical, status_text, alert, or control. Reject
   any element whose type is not in the recognized set before assessment
   continues.
2. For each alert element, determine the required urgency tier by mapping
   the associated hazard severity (low / medium / high) against the
   time criticality for corrective action (seconds / minutes / hours /
   none). Compare the required tier against the declared tier; flag a
   mismatch if they differ.
3. Check every display element for legibility: compute or obtain the
   luminance contrast ratio and the character height at design viewing
   distance. Flag the element when either falls below its minimum
   threshold (contrast ratio < 4.5, character height < 3.5 mm).
4. For each automation function on the workstation, record its authority
   level. Confirm that supervisory and autonomous functions carry a
   documented crew override capability; flag each that does not.
5. Aggregate the format violations, alert tier mismatches, and automation
   violations per workstation. The workstation is not informatics-compliant
   under §4.8 until all three lists are empty.

## Pitfalls

- Assigning a caution tier to a high-severity situation that demands
  action within seconds — the warning tier exists precisely for this
  case and its omission leaves the crew with insufficient urgency cuing.
- Treating contrast ratio and character height as alternatives: both
  thresholds are independent minima and a display that passes one can
  still fail the other.
- Allowing advisory or shared_control automation functions to inherit the
  crew-override requirement from higher authority levels — override is
  mandatory only at supervisory and autonomous levels; adding it elsewhere
  creates unnecessary interface complexity without safety benefit.
- Proceeding with the alert tier check before confirming that the element
  type is recognized — an alert indicator on an unknown element type means
  the hazard mapping has not been scoped to a defined function and the
  tier assignment is unvalidated.

## Behavior contract (gate 3)

The display element type check, alert urgency determination, display
format compliance, automation authority assessment, and workstation
aggregation logic is exercised by the gate 3 contract test:
scripts/test_e1011_informatics.py against
scripts/e1011_informatics_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_informatics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
