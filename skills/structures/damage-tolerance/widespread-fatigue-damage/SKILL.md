---
name: widespread-fatigue-damage
description: "Use when you must screen transport airplane structure for widespread fatigue damage (WFD) per FAR 25.571: classify multiple site damage (MSD) cracks in adjacent fastener holes and multiple element damage (MED) in adjacent load paths, run the WFD susceptibility screening, and flag when a supplemental inspection (for example the supplemental inspection document, SID/SLWFD) is required for fatigue critical baseline structure. Produces the MSD site-count verdict, the WFD susceptibility verdict, and the supplemental inspection required flag that feed the damage tolerance certification review. Trigger: widespread fatigue damage, MSD, MED, multiple site damage, multiple element damage, supplemental inspection, fatigue critical baseline, WFD."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: damage-tolerance
  tags: [damage-tolerance, widespread-fatigue-damage, msd, med, multiple-site-damage, multiple-element-damage, supplemental-inspection, far-25-571]
  version: 0.1.0
  author: Aero Agent Skills
---

# Widespread Fatigue Damage (structures/damage-tolerance/widespread-fatigue-damage)

Use when the task is screening transport airplane structure for
widespread fatigue damage (WFD) per FAR 25.571(b)/(c): classify
multiple site damage (MSD) versus multiple element damage (MED), run
the WFD susceptibility screening over cracked fastener-hole sites, and
decide whether a supplemental inspection applies to fatigue critical
baseline structure.

## Domain quick reference

- WFD (FAR 25.571(b)/(c)) is the simultaneous cracking of multiple
  sites in a structure element such that the structure can no longer
  sustain the required loads between normal inspections. Transport
  airplane evaluations must show that WFD will not occur before the
  design service goal is reached.
- MSD: multiple site damage. Small fatigue cracks at multiple adjacent
  fastener holes within one element (for example a lap splice row).
  Each crack may be short on its own, but the population can link up.
- MED: multiple element damage. Cracks in adjacent load-path elements
  (for example adjacent stringers or stiffeners) that together reduce
  the redundancy of the structure.
- Fatigue critical baseline structure: the structural elements whose
  failure from fatigue would directly reduce the residual strength of
  the airplane below the required level. This baseline is the scope
  for WFD screening.
- WFD susceptibility screening: compare the detected crack lengths at
  the fastener-hole sites against a screening threshold, count how
  many sites exceed it, and judge whether the population is WFD
  susceptible. A single worst-site crack is not the screening question;
  the site population is.
- Supplemental inspections: for designs that cannot show WFD
  resistance up front, a supplemental inspection program (for example
  the SID/SLWFD style program) is applied to fatigue critical baseline
  structure so cracking is caught before it becomes widespread.
- Certification date thresholds: the WFD rule applies to transport
  airplanes by certification date, and fatigue critical baseline
  structure for earlier designs is handled through supplemental
  inspections rather than a full up-front WFD demonstration.

## Workflow

1. Identify the fatigue critical baseline structure in scope per FAR
   25.571(b)/(c): the elements whose fatigue failure would cut the
   residual strength below the required level.
2. Collect the detected crack lengths at the adjacent fastener-hole
   sites of each element, plus the count of cracked load-path
   elements.
3. Classify the damage: MSD (cracks at adjacent fastener holes of one
   element), MED (cracks in adjacent load-path elements), both, or
   neither. Use `scripts/wfd_logic.py` classify_damage() with the
   cracked-site and cracked-element counts.
4. Run the MSD susceptibility screening with screen_msd(): count the
   sites whose crack length exceeds the screening threshold; the
   verdict is "susceptible" when at least two sites exceed it.
5. Apply the certification date threshold: decide whether the design
   must show WFD resistance up front or whether fatigue critical
   baseline structure is covered by a supplemental inspection program.
6. Set the supplemental inspection required flag with
   supplemental_inspection_required(): required for fatigue critical
   baseline structure when the screen is susceptible or WFD resistance
   has not been shown.
7. Report the classification, the site-count verdict, and the
   supplemental inspection flag together (wfd_screen_report()) and
   file the result in the damage tolerance assessment.

## Pitfalls

- Screening only the largest site crack. WFD is a population
  question: multiple adjacent sites matter, not the single worst
  site.
- Confusing MSD with MED. MSD is multiple cracks in adjacent fastener
  holes of one element; MED is cracks in adjacent load-path elements.
  Count sites for MSD, elements for MED.
- Treating the screening threshold as an exact boundary. A site at
  exactly the threshold is not counted; the verdict flips on sites
  strictly above it and on the two-site minimum.
- Leaving fatigue critical baseline structure out of the screening
  scope, which hides the elements the WFD rule targets.
- Ignoring the certification date threshold. New designs must show WFD
  resistance; older designs rely on supplemental inspections, and the
  flag logic changes accordingly.
- Reporting a supplemental inspection flag without checking the
  fatigue critical baseline flag first: non-baseline structure never
  triggers the flag.

## Behavior contract (gate 3)

The MSD/MED classification, susceptibility screening, and supplemental
inspection flag logic is exercised by the gate 3 contract test:
scripts/test_wfd.py against scripts/wfd_logic.py (stdlib unittest,
offline). Run:

python3 scripts/test_wfd.py

## Compliance

- FAR 25 (14 CFR Part 25) is public-domain US regulation; CS-25 is an
  EASA free-download publication. Both are referenced by id only
  (reference-only: true per standards-map.yaml); no verbatim text is
  reproduced, paraphrase only.
- compliance: STANDARDS-REF, gated: false.
