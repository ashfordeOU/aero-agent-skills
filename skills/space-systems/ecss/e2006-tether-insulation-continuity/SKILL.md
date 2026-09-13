---
name: e2006-tether-insulation-continuity
description: "Use when verify that the insulation jacket of a tether stays unbroken across its service life under ECSS-E-ST-20-06C clause 10.2.4: categorize each observed defect as through-thickness (pinhole, crack, cut-through) or partial-thickness (abrasion-scuff, delamination, thermal-blister), subtract atomic-oxygen erosion and the abrasion allowance from the as-built wall to obtain the end-of-life remaining-thickness, compute the dielectric-withstand of that wall against the applied tether voltage and its required factor, and check insulation-resistance, defect-density and pinhole leakage-current against their acceptance limits. Trigger: ecss, e-st-20-06c, tether-insulation-continuity, dielectric-withstand, pinhole-defect, atomic-oxygen-erosion, insulation-resistance, remaining-thickness, service-life-degradation."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-tether-insulation-continuity, tether-insulation-continuity, dielectric-withstand, pinhole-defect, atomic-oxygen-erosion, insulation-resistance, remaining-thickness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Tether — Insulation Continuity (space-systems/ecss/e2006-tether-insulation-continuity)

Use when the task is the insulation-continuity verification of
ECSS-E-ST-20-06C clause 10.2.4 -- showing that the dielectric jacket
over a tether conductor has no hole, crack or thinned region that
breaks its continuity, and that it still holds off the applied tether
voltage at the end of the declared service life, not only at delivery.

## Domain quick reference

- A defect is categorized by how far it goes through the wall, because
  the two families are graded by different rules. A through-thickness
  defect (pinhole, crack, cut-through) exposes bare conductor to the
  ambient plasma: it is a continuity break on sight, and no remaining
  wall arithmetic rescues it. A partial-thickness defect
  (abrasion-scuff, delamination, thermal-blister) leaves a reduced but
  intact wall, and is graded on the depth fraction it consumes against
  the allowance for that segment. An unrecognized defect type is
  rejected rather than assumed benign.
- Continuity is a service-life property, not a delivery property. The
  as-built wall loses thickness to atomic-oxygen erosion over the
  mission fluence -- eroded depth is fluence x erosion-yield of the
  jacket material -- and to the abrasion allowance booked for
  deployment, reeling and micrometeoroid scuffing. The wall that must
  hold off voltage is what remains after both are subtracted, and a
  remaining-thickness of zero or less is a breach, reported as such
  rather than as a very small number.
- The dielectric-withstand of the remaining wall is its thickness
  times the material dielectric strength. It is compared against the
  applied tether voltage multiplied by the required factor for the
  design; the ratio of withstand to required voltage is the margin,
  and a margin below one is a finding. An exactly-at-unity margin is
  compliant -- the comparison absorbs the representation error of a
  difference of floats rather than the limit being relaxed.
- Two acceptance measurements close the loop. Insulation-resistance
  measured over the segment must meet the minimum on record; a segment
  with no minimum on record is an open finding, not a pass. The
  leakage-current collected through the exposed area of
  through-thickness defects, taken as the ambient plasma
  current-density over that area, must stay within the leakage budget,
  and the defect-density per metre must stay within its acceptance
  limit.

## Workflow

1. Inventory every defect found on the segment by inspection or
   proof-testing and categorize each as through-thickness or
   partial-thickness. Reject an unrecognized defect type before it
   enters the assessment.
2. Flag every through-thickness defect as a continuity break, and
   accumulate its exposed area for the leakage-current calculation.
   Grade each partial-thickness defect on the fraction of wall it
   consumes against the allowed depth fraction for that segment.
3. Compute the eroded depth over the mission from the atomic-oxygen
   fluence and the jacket material erosion-yield, subtract it and the
   booked abrasion allowance from the as-built thickness, and report
   the end-of-life remaining-thickness; zero or less is a breach.
4. Compute the dielectric-withstand of the remaining wall and divide
   by the applied tether voltage times the required factor. A margin
   below one is a finding; an exactly-at-unity margin passes.
5. Compare the measured insulation-resistance against the minimum on
   record, the defect-density per metre against its limit, and the
   summed pinhole leakage-current against the leakage budget. A
   missing minimum or a missing measurement is itself a finding.
6. Aggregate the defect, wall, withstand and acceptance findings per
   segment; the segment is continuity-compliant only when every list
   is empty.

## Pitfalls

- Grading insulation on the as-built wall and never subtracting
  service-life erosion. The jacket that passes proof-testing at
  delivery can be a third thinner after the mission fluence, and the
  withstand scales directly with what is left.
- Treating a pinhole as a small partial-thickness defect because its
  area is small. Area sets the collected leakage-current; depth sets
  continuity, and a through-thickness defect of any area is a break.
- Reporting a negative remaining-thickness as a number and continuing
  the arithmetic. Once the wall is consumed the dielectric model no
  longer applies, and the correct output is a breach finding.
- Accepting a segment because no defect was recorded while the
  insulation-resistance minimum was never captured. An unset
  acceptance limit means the requirement is missing, which is a
  finding in its own right.
- Relaxing the required voltage factor so a marginal wall passes. The
  factor stays; only the floating-point comparison at the exact
  boundary is made tolerant.

## Behavior contract (gate 3)

The defect-categorization, erosion, remaining-thickness,
dielectric-withstand, insulation-resistance, defect-density and
leakage-current logic is exercised by the gate 3 contract test:
scripts/test_e2006_tether_insulation_continuity.py against
scripts/e2006_tether_insulation_continuity_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_tether_insulation_continuity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
