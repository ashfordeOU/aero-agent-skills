---
name: e1011-labels-cues
description: "Use when verify labels, colour codings, and warning cues for a crewed spacecraft interface under ECSS-E-ST-10-11C §4.7.3: categorize each marking as a label (text identifying a control, display, or panel) or a cue (colour-coded indicator or alert signal), confirm every label is non-empty and within the character-length limit, check each colour-coded indicator against the HFE colour-status convention (red for danger, amber for caution, green for nominal, white or grey for information), and confirm every warning cue is detectable and that items with criticality 'warning' or 'emergency' carry at least two redundant cueing modalities (visual, auditory, or tactile). Flag every label, colour, or cue that fails its check; a panel is not compliant until all findings are resolved. Trigger: ecss, e-st-10-11c, e-st-10-system-scope, labels-cues, colour-coding, warning-cues, hfe, human-factors-engineering."
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
  tags: [ecss, e-st-10-11c, e-st-10-system-scope, labels-cues, colour-coding, warning-cues, hfe, human-factors-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — Labels and Cues (space-systems/ecss/e1011-labels-cues)

Use when the task is to verify that labels, colour codings, and warning cues
on a crewed spacecraft interface satisfy the Human Factors Engineering (HFE)
design requirements of ECSS-E-ST-10-11C §4.7.3.

## Domain quick reference

- §4.7.3 governs two distinct marking types that must each be checked
  separately. A **label** is a text string placed adjacent to a control,
  display, or panel item to identify it unambiguously. A **cue** is a
  perceptible signal — colour-coded indicator, auditory tone, or tactile
  feedback — that conveys system status or alerts the crew to an event
  requiring attention. Every marking on the interface is categorized as one
  or the other before its compliance is checked; an uncategorized marking
  is a gap.

- Label requirements address legibility and content: the label text must be
  non-empty, must use consistent approved terminology (no ad-hoc
  abbreviations), and must not exceed the character-length limit established
  in the HFE requirements (50 characters is the default ceiling; a project may
  tighten this). A label that identifies the wrong item or duplicates an
  adjacent label name is an ambiguity finding, not just a content finding.

- Colour coding follows a fixed HFE status convention. Each colour maps to
  exactly one status class and must not be repurposed: red indicates
  danger/emergency conditions; amber or yellow indicates caution/advisory
  conditions; green indicates nominal or safe conditions; white or grey
  indicates information or inactive state; blue indicates a selected or active
  state in some interface conventions. An indicator whose colour contradicts
  its stated status intent is a convention violation and must be corrected
  before the interface can be accepted.

- Warning cues must be perceptible under operational conditions (lighting,
  noise, suit-glove limitations). For items with criticality level 'warning'
  or 'emergency', a single-modality cue is insufficient; at least two
  independent modalities (chosen from visual, auditory, tactile/haptic) are
  required so that a failure in one modality channel does not eliminate the
  alert. Non-critical and caution-level items may use a single modality, but
  the cue must still be confirmed detectable.

- Criticality levels form an ordered set: non-critical < caution < warning <
  emergency. The redundant-cueing threshold applies at 'warning' and above.

## Workflow

1. Obtain the interface marking inventory (label register and cue register).
  Categorize every entry as a label or a cue. Flag any entry with no
  categorization before proceeding; uncategorized entries are not checked
  against either ruleset and represent a coverage gap.

2. For each label, check: (a) the label text is non-empty; (b) the text
  length is within the project character limit (default 50 chars); (c) the
  item identifier is non-empty and unique within the inventory. Record a
  finding for each failed check; a label passes only when all three are clear.

3. For each colour-coded indicator, identify the colour and the intended
  status. Look up the colour in the HFE convention map. If the colour is not
  in the approved palette, record an unknown-colour finding. If it is in the
  palette but the mapped status class does not match the stated status intent,
  record a convention-violation finding. Amber and yellow are treated as
  equivalent (both map to caution).

4. For each warning cue, verify: (a) at least one cueing modality is
  specified; (b) the modalities are drawn from the approved set (visual,
  auditory, tactile, haptic); (c) the cue is confirmed detectable in the
  operational environment; (d) for criticality 'warning' or 'emergency', at
  least two distinct modalities are listed. Record a finding for each check
  that fails.

5. Aggregate all label findings, colour findings, and cue findings. A panel
  or interface area is not compliant until every finding in all three
  categories is resolved. Report the total finding count and the per-item
  breakdown.

6. Re-run the checks after any corrective action and confirm the finding count
  reaches zero before closing the review.

## Pitfalls

- Accepting a label that falls within the character limit but uses an
  unapproved abbreviation — the length check and the terminology check are
  independent; passing one does not imply passing the other.

- Treating amber and yellow as different status classes — the HFE convention
  maps both to caution; using one colour in a caution context and then the
  other for a different caution item does not create a conflict, but mixing
  them with a third status class (e.g. treating yellow as nominal and amber as
  caution) is a convention violation.

- Assuming a non-detectable cue at 'non-critical' level is acceptable —
  detectability is mandatory regardless of criticality. A cue that cannot be
  perceived by the crew in the expected operational environment provides no
  information and must be redesigned or relocated.

- Applying the two-modality rule only to 'emergency' items and missing
  'warning' items — the threshold is at 'warning' and above. A warning-level
  cue with a single visual indicator fails even if the visual is bright and
  unambiguous.

- Leaving entries in the marking inventory with no categorization and reading
  the check results as complete — only categorized entries are checked.
  Uncategorized entries are silently excluded, which can mask entire panels
  from the review.

## Behavior contract (gate 3)

The label validation, colour-convention check, and warning-cue redundancy
logic are exercised by the gate 3 contract test:
scripts/test_e1011_labels_cues.py against scripts/e1011_labels_cues_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1011_labels_cues.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
