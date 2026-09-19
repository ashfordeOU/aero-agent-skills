---
name: e3311-ead-general-separation-nuts-bolts
description: "Assess an explosively actuated device and, in particular, a separation nut or explosive bolt against ECSS-E-ST-33-11C clauses 4.12.1 and 4.12.2. Use when the task is showing that a one-shot release actuator does its mechanical job with margin: recovering the bolt preload from the installation torque, building the work the release actually costs from friction, stored strain energy and notch fracture, converting the cartridge output into delivered work, grading the ratio against the device margin floor, and checking initiation redundancy, debris containment and release time. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosively-actuated-device-function-margin, separation-nut-preload-release, explosive-bolt-fracture-energy, ead-initiation-redundancy, separation-device-debris-containment, ead-release-time-budget."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-ead-general-separation-nuts-bolts, explosively-actuated-device-function-margin, separation-nut-preload-release, explosive-bolt-fracture-energy, ead-initiation-redundancy, separation-device-debris-containment, ead-release-time-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — EAD General, Separation Nuts and Bolts (space-systems/ecss/e3311-ead-general-separation-nuts-bolts)

Use when the task is the explosively actuated device requirement of
ECSS-E-ST-33-11C clause 4.12.1 and the separation nut and bolt
requirement of clause 4.12.2 -- showing that a device which fires once,
cannot be tested on the article that flies and has no second attempt
still delivers more work than the release costs, under the worst
combination of preload, friction and cartridge output.

## Domain quick reference

- An explosively actuated device converts a cartridge output into one
  mechanical action. Everything downstream of that conversion is a
  work balance: the work the cartridge delivers against the work the
  release costs, expressed as a ratio because the inputs on both sides
  carry lot variation.
- The preload is rarely measured. It is recovered from the installation
  torque through the nut factor, and the nut factor is the loose term:
  it carries thread and bearing friction, lubrication and plating, so
  a preload quoted to three figures from a torque wrench is already an
  estimate with a wide band.
- A separation nut and an explosive bolt pay for the release
  differently. The nut drives segments out radially against the
  friction the clamped preload generates; the bolt severs a notched
  section, so it pays a fracture energy and then releases the strain
  energy stored in the stretched shank. The same preload therefore
  buys a different required work in the two devices.
- The delivered side is not the cartridge rating. Only part of the
  cartridge output becomes useful mechanical work, so the rating is
  multiplied by a conversion efficiency before it is compared with
  anything, and an efficiency taken as unity is the commonest way a
  marginal device looks compliant.
- Margin is a ratio with a floor set by device kind. A separation
  device on a deployment path carries a higher floor than a general
  actuator because a partial function leaves the structure joined and
  the mission stopped.
- Function is necessary but not sufficient. A device that works and
  sheds fragments, vents gas into the bay or takes longer to release
  than the sequence allows has still failed the clause, and a single
  initiator or a single firing circuit leaves a single point of
  failure on a one-shot action.

## Workflow

1. Declare the device kind, the installation torque, the nut factor and
   the bolt diameter, and recover the preload. Reject a nut factor or
   a diameter that is not a positive number rather than defaulting it.
2. Build the required release work from the device kind: friction work
   against the preload for a separation nut, notch fracture energy plus
   released strain energy for an explosive bolt, direct work against
   the load for a general actuator. Reject a case that omits the term
   its device kind needs.
3. Reduce the cartridge rating to delivered work through the declared
   conversion efficiency, and reject an efficiency at or above unity.
4. Grade the ratio of delivered work to required work against the
   margin floor for that device kind, and report the shortfall rather
   than only the verdict.
5. Assess initiation redundancy: count the initiators and the
   independent firing circuits and name any single point of failure on
   the one-shot action.
6. Assess the non-function requirements that sit alongside it: fragment
   containment, a sealed gas path and a release time inside the
   sequence allowance. Combine everything into one verdict, so a device
   that functions but vents into the bay does not read as acceptable.

## Pitfalls

- Treating the torque-derived preload as a measurement. The nut factor
  carries the whole friction state of the joint, so the preload band is
  wide and the margin has to survive its upper end, which is the end
  that raises the required work.
- Using the cartridge rating as delivered work. The rating is chemical
  output; only the fraction that becomes mechanical work moves the
  piston or the segments, and skipping the efficiency inflates the
  margin by the whole conversion loss.
- Carrying the separation-nut work model over to an explosive bolt. The
  bolt pays a fracture energy the nut never pays, and the nut pays a
  friction term the bolt does not, so swapping the models silently
  changes the answer by more than the margin.
- Counting two initiators in one device as redundancy when they share a
  single firing circuit. The redundancy has to be independent all the
  way back, otherwise the shared circuit is the single point of
  failure on an action with no second attempt.
- Declaring the device compliant on the work balance alone. Fragment
  release, gas leakage into the compartment and a release time outside
  the sequence window each fail the clause on their own.
- Comparing a work ratio with its floor by bare arithmetic. Both sides
  are products of estimated terms, so a case that sits exactly on the
  floor can land a few units in the last place below it; the comparison
  absorbs that while the floor stays untouched.

## Behavior contract (gate 3)

The preload recovery, required-work build-up by device kind, delivered
work conversion, margin grading, redundancy screen and combined verdict
are exercised by the gate 3 contract test:
scripts/test_e3311_ead_general_separation_nuts_bolts.py against
scripts/e3311_ead_general_separation_nuts_bolts_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3311_ead_general_separation_nuts_bolts.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
