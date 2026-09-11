---
name: e1011-medical
description: "Use when assess medical facilities and provisions for a crewed spacecraft against ECSS-E-ST-10-11C §4.7.9 HFE requirements: categorize each provision item as emergency, diagnostic, routine, or preventive; determine the minimum required provision set for the mission duration category (short ≤30 days, medium 31–180 days, long >180 days); verify the on-board inventory covers every required item; compute consumable quantities against crew size and mission duration with a 10 percent margin; and flag any missing capability or consumable shortfall as a non-compliance finding. Trigger: ecss, e-st-10-system-scope, medical, crew-health, hfe, medical-provisions, consumables, mission-duration."
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
  tags: [ecss, e-st-10-system-scope, medical, crew-health, hfe, medical-provisions, mission-duration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS HFE — Medical Facilities and Provisions (space-systems/ecss/e1011-medical)

Use when the task is the human factors assessment of medical facilities
and provisions on a crewed spacecraft under ECSS-E-ST-10-11C §4.7.9 —
categorizing every provision item, verifying inventory completeness
against mission duration, and checking consumable quantities for
adequacy against crew size and flight duration.

## Domain quick reference

- ECSS-E-ST-10-11C §4.7.9 establishes that each crewed mission must
  carry a set of medical facilities and provisions commensurate with
  the mission duration and crew size. Provision items are grouped into
  four capability families: emergency (trauma care, resuscitation,
  oxygenation, vascular access), diagnostic (vital-sign monitoring,
  imaging), routine (wound and oral care, first aid), and preventive
  (nutritional supplements, countermeasure exercise equipment,
  radiation dosimetry). Each item belongs to exactly one family and
  is entered in the provision inventory as that family before
  completeness is checked.
- Mission duration drives the minimum required provision set.
  Short-duration missions (flight time ≤30 days) require the emergency
  and basic diagnostic and routine core. Medium-duration missions
  (31–180 days) add the full diagnostic suite, extended consumables,
  and dosimetry. Long-duration missions (>180 days) additionally
  require preventive items covering nutritional and countermeasure
  exercise provisions. A mission whose duration places it in a higher
  tier inherits all requirements of lower tiers.
- Consumables (medications, wound dressings, oxygen, IV fluid) must
  cover the full planned crew size multiplied by the mission duration
  and a 10 percent margin. A shortfall in any consumable is a
  non-compliance finding for that item regardless of whether the
  provision type itself is present.

## Workflow

1. Receive the medical provision inventory — a list of provision items
   each identified by type (e.g. "trauma_kit", "pulse_oximeter",
   "vitamins") — and verify that every type falls into a known
   capability family. Reject any unrecognized type before entering it
   into the assessment.
2. Determine the mission duration category (short, medium, or long)
   from the planned flight duration in days, then retrieve the
   corresponding minimum required provision set for that category.
3. Compare the set of types present in the on-board inventory against
   the required set; record every type that is required but absent as
   a missing-provision finding.
4. For each consumable item in the inventory, compute the minimum
   required quantity: daily rate per person × crew size × mission
   duration days × 1.10. If the on-board quantity falls below that
   threshold, record a consumable-shortfall finding for that item,
   including the available and required quantities.
5. Aggregate the missing-provision findings and consumable-shortfall
   findings; the medical facilities assessment is compliant only when
   both lists are empty.

## Pitfalls

- Assuming presence of a provision type implies adequate consumable
  quantity. A "medications" line item in the manifest satisfies the
  type check but not the quantity check; both must pass independently.
- Applying short-duration requirements to medium- or long-duration
  missions. The required set is monotonically larger with duration;
  a mission whose duration exceeds a threshold must meet the full
  tier above it, not just the one below.
- Omitting the 10 percent consumable margin. The margin exists to
  cover contingency extensions; dropping it and computing the
  bare minimum produces a finding-free result that does not satisfy
  the §4.7.9 requirement.
- Entering a provision item under the wrong family. Categorization
  is deterministic from the item type; a wrong family does not affect
  the type-completeness check (which operates on item types) but
  will produce misleading capability-gap analysis if the family
  grouping is used for capability reporting.

## Behavior contract (gate 3)

The provision-categorization, mission-duration-category,
required-provision-set, missing-provision, consumable-requirement, and
full medical-HFE-review logic is exercised by the gate 3 contract
test: scripts/test_e1011_medical.py against
scripts/e1011_medical_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_medical.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
