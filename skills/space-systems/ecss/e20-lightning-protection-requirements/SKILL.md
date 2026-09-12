---
name: e20-lightning-protection-requirements
description: "Use when verify that a space system withstands direct and indirect lightning effects under ECSS-E-ST-20C clause 6.3.2.4 without performance degradation: categorize each coupling mechanism as a direct attachment effect or an indirect induced effect, assign every external region its lightning attachment zone, confirm the zone provisions and the adiabatic conductor cross-section carry the stroke action integral, build the induced bundle transient from its inductive and resistive coupling terms, compare that level against the equipment transient design level as a decibel separation, and record every function whose performance degrades or needs intervention to recover. Trigger: ecss, e-st-20-electrical-scope, e-st-20c-clause-6-3-2-4, lightning-protection-requirements, direct-lightning-effect, indirect-lightning-effect, lightning-attachment-zone, lightning-induced-transient, transient-design-level-margin, stroke-action-integral."
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
  tags: [ecss, e-st-20-electrical-scope, e20-lightning-protection-requirements, direct-lightning-effect, indirect-lightning-effect, lightning-attachment-zone, lightning-induced-transient, transient-design-level-margin, stroke-action-integral]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Lightning Protection Requirements (space-systems/ecss/e20-lightning-protection-requirements)

Use when the task is the clause 6.3.2.4 lightning protection
requirement of ECSS-E-ST-20C -- showing that a space system exposed to
a lightning strike, on the pad or in flight through the atmosphere,
survives both the effects of the channel attaching to it and the
effects the channel's field and potential rise couple into it, and
that nothing it is meant to do degrades as a result.

## Domain quick reference

- Every coupling mechanism is categorized once as direct or indirect.
  Direct effects are what the attached channel does to the structure:
  arc-root attachment, resistive burn-through, magnetic force pinch,
  acoustic shock overpressure, metal erosion at the root. Indirect
  effects are what the strike couples into internal circuits without
  attaching to them: field leakage through apertures, inductive
  coupling into cable bundles, the resistive voltage rise along the
  structural return, ground potential rise, and diffusion flux through
  a finite-conductivity skin. The two families take different
  protection, so a mechanism outside the list is rejected rather than
  defaulted into one of them.
- Direct protection is zoned. A region that takes the initial
  attachment is a zone 1 region, one swept by the channel is zone 2,
  and one that only conducts current without attaching is zone 3; the
  "b" variants additionally hold the channel for the long-duration
  component and so need a dwell provision on top of the attachment
  path. Each zone has a fixed provision set, and a region with no zone
  on record is a finding -- an unzoned external surface is not
  silently a zone 3 surface.
- The conductor carrying the stroke is sized against the action
  integral, not the peak current. The adiabatic cross-section is the
  square root of the action integral divided by a material action
  constant, so copper needs less metal than aluminium for the same
  stroke and a meshed composite needs several times more. Halving the
  section does not halve the capacity: the relationship goes with the
  square root.
- Indirect protection is a level comparison. The induced open-circuit
  transient on a bundle is the inductive term -- mutual inductance
  times the current rate of rise -- plus the resistive term -- the
  structural return resistance times the peak current -- added in
  phase, which is the conservative assumption when their relative
  timing is not established. That level is compared against the
  equipment transient design level as twenty times the base-ten
  logarithm of the ratio, and a separation at or below the required
  decibel margin is a finding against the installation, not against
  the equipment alone.
- The clause asks for no performance degradation, which is stricter
  than survival. A function whose measured parameter leaves its
  allowed band fails, and so does a function that stays inside the
  band but needs ground intervention to come back -- an autonomously
  recovering upset is the only acceptable transient response.

## Workflow

1. Categorize every coupling mechanism in the threat list as a direct
   or an indirect effect; reject a mechanism that is neither before it
   reaches the protection check.
2. Assign each external region its lightning attachment zone and list
   the zone provisions the design does not carry.
3. Compute the adiabatic conductor cross-section the stroke action
   integral demands for that region's material and flag a conductor
   below it.
4. For each cable bundle, compute the inductive and resistive coupling
   terms and sum them into the induced transient level.
5. Compare the equipment transient design level against that induced
   level as a decibel separation and flag a margin below the required
   minimum.
6. Record every exposed function whose parameter deviation leaves its
   allowed band, and separately every function that recovers only with
   intervention.
7. Aggregate the direct, indirect and performance findings; the system
   meets clause 6.3.2.4 only when all three lists are empty.

## Pitfalls

- Sizing the lightning conductor from the peak current alone. The
  metal is heated by the action integral, so a short high-peak stroke
  and a long moderate one that share a peak demand very different
  cross-sections.
- Treating an external region with no zone on record as protected
  because no provision was found missing. The zone is the input to the
  provision list; without it the region was never checked.
- Adding only the inductive term to the bundle transient. The
  structural return resistance is small, but multiplied by a
  200 kA peak it contributes volts, and an equipment design level set
  a few volts above the inductive term alone has no margin left.
- Comparing the design level and the induced level as a bare ratio and
  reading anything above one as a pass. The requirement is a margin in
  decibels, so a ratio of 1.2 is about 1.6 dB and fails a 6 dB
  requirement.
- Accepting a function that latches into a safe state and is recovered
  by a ground command. Clause 6.3.2.4 asks for no degradation, and an
  upset needing intervention is degradation that happens to be
  repairable.
- Reusing an aircraft zoning map unchanged for a vehicle on the launch
  pad. The attachment geometry on the ground, with the tower and the
  umbilical panel in the picture, is not the in-flight geometry.

## Behavior contract (gate 3)

The effect categorization, attachment-zone assignment, zone-provision,
adiabatic conductor cross-section, induced-transient, decibel-margin
and no-degradation logic is exercised by the gate 3 contract test:
scripts/test_e20_lightning_protection_requirements.py against
scripts/e20_lightning_protection_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_lightning_protection_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
