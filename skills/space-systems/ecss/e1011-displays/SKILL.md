---
name: e1011-displays
description: "Use when design displays for a crewed spacecraft interface under ECSS-E-ST-10-11C §4.9.4: verify each display's format properties (layout type, font size, contrast ratio) against HFE minimum thresholds, check the information-density budget (parameter count and visible alarm count per display) against project limits, and assess each alarm entry for valid priority, consistent state, visual and auditory distinctiveness for high-priority active alarms, and correct suppression-indicator visibility. Flag every format, density, or alarm finding; a display is not compliant until all findings are resolved. Trigger: ecss, e-st-10-11c, e-st-10-system-scope, displays, display-format, information-density, alarm-presentation, hfe, human-factors-engineering."
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
  tags: [ecss, e-st-10-11c, e-st-10-system-scope, displays, display-format, information-density, alarm-presentation, hfe, human-factors-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — Display Design (space-systems/ecss/e1011-displays)

Use when the task is to design or verify that displays on a crewed spacecraft
interface satisfy the Human Factors Engineering (HFE) design requirements of
ECSS-E-ST-10-11C §4.9.4, covering display format properties, information
density limits, and alarm presentation rules.

## Domain quick reference

- §4.9.4 governs three separable design dimensions that must each be assessed
  before a display is accepted. **Format** addresses the physical and visual
  layout properties of the display itself: the layout type, font size, and
  luminance contrast between text and background. **Information density**
  addresses how much content is placed on a single display: the number of
  parameters shown simultaneously and the number of alarms visible at one
  time. **Alarm presentation** addresses each individual alarm entry: its
  priority level, its current state, and whether the cueing characteristics
  match what that priority and state require.

- Display format requirements set minimum thresholds rather than exact
  values, because the thresholds may be tightened by a project's human
  interface specification. The defaults used here (font size ≥ 10 pt,
  contrast ratio ≥ 4.5) reflect the HFE floor for crew-readable text under
  operational lighting conditions. The layout type must be drawn from the
  set of approved types (list, graphical, schematic, alphanumeric, combined);
  an ad-hoc layout not in that set is a format finding.

- Information density limits are project-configurable but must be explicitly
  set. The defaults (maximum 15 parameters per display, maximum 12 visible
  alarms per display) reflect the HFE cognitive-load guideline for continuous
  monitoring tasks. Exceeding either limit is a density finding even if no
  individual parameter or alarm is erroneous.

- Alarm entries are each categorized by priority and state before their
  cueing characteristics are checked. Priority levels form an ordered set:
  advisory < caution < warning < emergency. High-priority active alarms
  (warning or emergency) require both visual distinctiveness and an auditory
  signal; lower-priority active alarms require visual distinctiveness at
  minimum. Suppressed alarms at any priority must carry a visible suppression
  indicator so that operators know a condition has been masked. Emergency-
  priority alarms cannot enter the suppressed state; if that combination
  appears in the alarm register it is an immediate finding, not a suppression
  check.

## Workflow

1. Obtain the display register (one entry per display: display identifier,
   layout type, font size, contrast ratio) and the density register (parameter
   count and visible-alarm count per display, with project limits). Collect
   the alarm register (one entry per alarm: alarm identifier, priority, state,
   visual-distinctiveness flag, auditory-signal flag, suppression-visible flag).

2. For each display entry, check format: (a) the display identifier is
   non-empty; (b) the layout type is in the approved set; (c) the font size
   meets or exceeds the project minimum (default 10 pt); (d) the contrast
   ratio meets or exceeds the project minimum (default 4.5). Record a finding
   for each check that fails.

3. For each display entry, check density: (a) the parameter count does not
   exceed the project maximum (default 15); (b) the visible alarm count does
   not exceed the project maximum (default 12). Record a finding for each
   limit that is exceeded.

4. For each alarm entry, check presentation: (a) priority is from the approved
   set; (b) state is from the approved set; (c) if the state is 'active' and
   the priority is 'warning' or 'emergency', visual_distinct and
   auditory_distinct must both be true; (d) if the priority is 'emergency',
   the state must not be 'suppressed'; (e) if the state is 'suppressed',
   suppression_visible must be true. Record a finding for each check that fails.

5. Aggregate format findings, density findings, and alarm findings across the
   entire register. A display is not compliant until every finding in all
   three categories is resolved. Report the total finding count and the
   per-item breakdown.

6. Re-run the checks after any corrective action and confirm the finding count
   reaches zero before closing the review.

## Pitfalls

- Checking alarm cueing only for 'emergency' state and missing 'warning'
  priority items — the high-priority cueing threshold applies at 'warning'
  and above. A warning-priority active alarm with no auditory signal fails
  even if its visual indicator is prominent.

- Reading a 'suppressed' alarm as inactive and skipping its suppression-
  visible check — a suppressed alarm is still a live condition; the suppression
  indicator is the only crew notification that the condition exists in a masked
  state. Omitting the check can leave operators unaware of masked faults.

- Treating 'acknowledged' the same as 'normal' for cueing purposes —
  acknowledgment confirms operator awareness but does not remove the condition.
  An acknowledged 'warning' alarm still requires its visual indicator to remain
  active; only the auditory signal may be cleared on acknowledgment.

- Accepting a density count that reaches the project limit in normal operations
  and then exceeds it during alarm floods — the density check applies to the
  maximum simultaneously visible count, which should be evaluated against a
  credible alarm flood scenario, not just the nominal display state.

- Allowing an emergency alarm to enter the 'suppressed' state on the grounds
  that a suppress action was procedurally authorised — the HFE rule is
  unconditional: emergency alarms are always visible. The finding is recorded
  regardless of how the suppression was initiated.

## Behavior contract (gate 3)

The display format, density, and alarm-presentation logic are exercised by
the gate 3 contract test:
scripts/test_e1011_displays.py against scripts/e1011_displays_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1011_displays.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
