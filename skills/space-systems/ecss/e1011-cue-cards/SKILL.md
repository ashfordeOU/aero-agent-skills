---
name: e1011-cue-cards
description: "Use when develop cue cards for spacecraft emergency and contingency
  operations under ECSS-E-ST-10-11C §4.9.2: identify the scenario scope and crew
  task sequence, structure each card as a compact step-by-step action list within
  brevity and legibility limits, assign severity and scenario type, verify action
  steps carry imperative verbs and respect the maximum step count per card face,
  and confirm the complete card set covers all mandatory emergency and contingency
  scenarios. Trigger: ecss, e-st-10-system-scope, cue-cards, emergency-procedures,
  contingency-operations, crew-procedures, quick-reference, human-spaceflight."
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
  tags: [ecss, e-st-10-system-scope, cue-cards, emergency-procedures, contingency-operations, crew-procedures, quick-reference, human-spaceflight]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Cue Cards (space-systems/ecss/e1011-cue-cards)

Use when the task is developing cue cards — compact quick-reference cards
for crew use during emergency and contingency operations on crewed space
systems — per ECSS-E-ST-10-11C §4.9.2. The skill covers identifying
applicable scenarios, structuring card content within human-factors
brevity limits, verifying action-verb formatting, and confirming that
the card set covers all mandatory scenarios.

## Domain quick reference

- A cue card addresses exactly one emergency or contingency scenario.
  Emergency scenarios involve an immediate threat to crew safety or
  vehicle integrity (e.g., rapid depressurization, fire, toxic release)
  and require the highest-priority response. Contingency scenarios involve
  operational anomalies that do not immediately endanger the crew but
  require prompt corrective action (e.g., subsystem failure, sensor
  discrepancy).
- Card brevity is a hard human-factors constraint: each card face must
  carry no more than nine action steps. Exceeding this limit degrades
  crew performance under stress. Cards that cannot be reduced to nine
  steps per face must be split across multiple sequenced card faces.
- Each action step is a single, grammatically complete imperative
  statement beginning with an action verb (e.g., "Close", "Activate",
  "Report"). Steps that begin with a noun phrase or explanatory clause
  are not compliant with the crew-readable format.
- Every step must fit within 80 characters so the text is legible at
  arm's length under degraded lighting. Steps exceeding this limit must
  be rephrased or split.
- Cards are severity-graded: CRITICAL (immediate life-safety), HIGH
  (significant operational impact), or MEDIUM (limited impact).
  Severity drives card placement in the on-board card set and the
  order in which a crew member locates and retrieves the card.
- The card set as a whole must cover every scenario identified in the
  crew operations scenario inventory. A scenario with no corresponding
  card is a gap finding, not a pass.

## Workflow

1. Obtain the crew operations scenario inventory for the mission and
   identify every scenario that requires a cue card — at minimum all
   scenarios where crew must act within 60 seconds of detection.
2. For each scenario, assign a scenario type (emergency or contingency)
   and a severity level (CRITICAL, HIGH, or MEDIUM) based on the hazard
   analysis and crew task timeline.
3. Draft the action step sequence for each card: list every discrete
   action the crew must perform in the correct execution order, using
   imperative action verbs at the start of each step.
4. Check each card for compliance with the brevity limit: if the step
   count on any face exceeds nine, split the card into sequenced faces
   (Face 1, Face 2, …) and add a continuation marker at the bottom of
   each face.
5. Check every step for legibility: verify each step is at most 80
   characters and is not blank.
6. Verify the complete card set against the scenario inventory:
   confirm that a card exists for every required scenario and that no
   required scenario is uncovered.
7. Record any gap findings (uncovered scenarios, step-count violations,
   step-length violations, missing severity or type fields) and resolve
   each finding before the card set is approved for crew use.

## Pitfalls

- Treating a contingency card as an emergency card because the scenario
  sounds urgent — the distinction drives retrieval priority; merging the
  two types results in cards buried in the wrong section of the on-board
  library when the crew needs them fastest.
- Writing explanatory or conditional prose as a step ("If pressure drops
  below threshold, then …") instead of a single imperative action —
  conditional logic belongs in the procedure document, not the cue card;
  the card must give only the action to take once the trigger condition
  is already met.
- Allowing a card to grow to ten or more steps without splitting — the
  human-factors brevity limit is not advisory; it reflects empirically
  measured performance degradation under stress.
- Declaring the card set complete after checking only individual cards —
  a card set passes when every required scenario in the inventory has a
  corresponding card; a card set with no per-card violations but a
  missing scenario is still incomplete.

## Behavior contract (gate 3)

The card structure, step-count, step-length, action-verb, scenario
categorization, severity validation, card-set coverage, and metrics
logic is exercised by the gate 3 contract test:
scripts/test_e1011_cue_cards.py against
scripts/e1011_cue_cards_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_cue_cards.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
