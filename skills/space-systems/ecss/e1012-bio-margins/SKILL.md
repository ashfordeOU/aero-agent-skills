---
name: e1012-bio-margins
description: "Use when calculate biological effects margins for a crewed mission
  under ECSS-E-ST-10C §5.5.5: categorize each biological stressor as radiation
  (ionizing), physiological (microgravity effects), atmospheric (gas composition,
  pressure), thermal, or acoustic; determine the design-point exposure for each
  stressor; apply the margin factor appropriate to that stressor category
  (radiation uses 1.5×; all other biological stressors use 1.25×); compare
  the margined exposure against the crew health allowable limit; and flag every
  stressor whose margined exposure exceeds its limit or whose allowable limit is
  not on record. Trigger: ecss, e-st-10-system-scope, biological-effects,
  bio-margins, crewed-missions, radiation, margin-philosophy, crew-health,
  physiological."
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
  tags: [ecss, e-st-10-system-scope, biological-effects, bio-margins, crewed-missions, radiation, crew-health, margin-philosophy, physiological]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Biological Effects Margins (space-systems/ecss/e1012-bio-margins)

Use when the task is to calculate and verify biological effects margins for a
crewed mission under ECSS-E-ST-10C §5.5.5 — categorizing each biological
stressor, applying the prescribed margin factor to the design-point exposure,
and comparing the result against the crew health allowable limit.

## Domain quick reference

- §5.5.5 defines a margin philosophy that distinguishes radiation stressors
  from all other biological stressors because radiation dose–response
  relationships carry greater model uncertainty. Radiation (ionizing: cosmic
  rays, trapped particles, solar particle events) therefore uses a 1.5× margin
  factor applied to the design-point dose. All other biological stressors —
  physiological (microgravity-driven bone loss, muscle atrophy, cardiovascular
  deconditioning), atmospheric (CO₂ partial pressure, O₂ partial pressure,
  humidity), thermal (cabin temperature delta), and acoustic (noise level) —
  use a standard 1.25× margin factor.
- Design-point exposure is the predicted value at the worst-case design
  operating point (orbit, mission duration, worst-case source intensity)
  before any margin is applied.
- Crew health allowable limit is the maximum margined exposure a crew member
  may experience, derived from occupational health requirements and linked to
  the applicable crew health standard. A stressor with no limit on record
  cannot be assessed and must be flagged as an unresolved finding.
- A stressor is compliant when margined exposure ≤ allowable limit. Equality
  is compliant; any value strictly above the limit is an exceedance.

## Workflow

1. Inventory every biological stressor relevant to the mission profile:
   radiation sources (cosmic-ray background, trapped belt, solar particle
   events), physiological stressors (duration-scaled microgravity exposure),
   atmospheric parameters (CO₂ and O₂ partial pressures, humidity), thermal
   loads, and acoustic noise levels. Reject any stressor whose type is not
   recognized before it enters the margin calculation.
2. For each stressor, record the design-point exposure — the predicted value
   under the worst-case operating condition without margin. Confirm the
   exposure value is non-negative; a negative exposure indicates a data error
   that must be resolved upstream.
3. Select the margin factor: apply 1.5× to radiation stressors and 1.25× to
   all other biological stressor categories. Multiply the design-point
   exposure by the selected factor to obtain the margined exposure.
4. Retrieve the crew health allowable limit for each stressor. If no limit is
   on record, record a LIMIT_UNSET finding for that stressor — do not default
   to any assumed value.
5. Compare each margined exposure against its allowable limit. Record a
   COMPLIANT finding if margined exposure ≤ limit. Record an EXCEEDANCE
   finding if margined exposure > limit, quoting both values in the finding
   detail.
6. Aggregate findings across all stressors. A mission margin assessment is
   complete only when every stressor has a recorded finding. The mission is
   margin-compliant only when every finding has status COMPLIANT.

## Pitfalls

- Applying the physiological margin factor (1.25×) to a radiation stressor —
  the higher radiation factor exists precisely to account for the added
  uncertainty in ionizing dose–response models, and collapsing the two
  underestimates the conservatism required by §5.5.5.
- Reading a LIMIT_UNSET stressor as passing — absence of a limit means the
  crew health requirement was never captured, which is itself a finding, not
  a pass. Every stressor must have an explicit limit to generate a compliance
  verdict.
- Using a margin factor below 1.0 — a factor less than 1.0 reduces the
  design-point exposure rather than adding conservatism, which inverts the
  margin intent and must be rejected as a data error.
- Treating a zero design-point exposure as trivially compliant without
  verifying the value is meaningful — a zero can indicate a stressor that
  is genuinely absent from the mission profile, or it can indicate a missing
  data input. Confirm the source before accepting zero.
- Stopping after finding the first exceedance — §5.5.5 requires that all
  stressors be assessed; a partial assessment that stops at the first finding
  will miss additional exceedances or unset limits.

## Behavior contract (gate 3)

The stressor-categorization, margin-factor selection, margin application,
limit comparison, and aggregation logic is exercised by the gate 3 contract
test: scripts/test_e1012_bio_margins.py against
scripts/e1012_bio_margins_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_bio_margins.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
