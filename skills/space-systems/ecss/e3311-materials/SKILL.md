---
name: e3311-materials
description: "Evaluate a material list for an explosive device against ECSS-E-ST-33-11C clause 4.9. Use when the task is deciding which candidates may sit next to a charge and which are out: grading vacuum mass loss and condensable volatiles, grading gas evolution and decomposition-onset depression measured in contact with the explosive, holding stress-corrosion susceptibility to the allowed category unless a justification is on record, checking each temperature rating against the hot case plus margin, and computing the potential difference across every declared contact pair against the allowance its environment carries. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-material-compatibility, explosive-gas-evolution-limit, explosive-outgassing-screening, explosive-galvanic-couple, stress-corrosion-susceptibility-explosive, decomposition-onset-depression."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-materials, explosive-material-compatibility, explosive-gas-evolution-limit, explosive-outgassing-screening, explosive-galvanic-couple, stress-corrosion-susceptibility-explosive, decomposition-onset-depression]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Materials (space-systems/ecss/e3311-materials)

Use when the task is the material screen of ECSS-E-ST-33-11C clause
4.9 -- choosing what may be in contact with, or enclose, an explosive
charge, given both what the space environment does to the material and
what the material and the charge do to each other.

## Domain quick reference

- The screen is a combination question, not two separate ones. A
  polymer can pass a vacuum outgassing screen on its own and a charge
  can be stable on its own, and the pair can still produce a device
  whose composition has been slowly attacked by what the polymer
  released into the cavity.
- Vacuum screening produces two numbers and both are graded: total
  mass loss says how much left the material, and the condensable
  volatile fraction says how much of that will land on something else
  and stay there.
- Compatibility is measured with the material against the charge. Gas
  evolution says whether the pair is reacting; the depression of the
  decomposition onset says whether the pair has made the charge less
  stable than it was alone, and that second number is the one that
  changes the thermal case.
- Stress-corrosion susceptibility is a property of the alloy and its
  temper, and it is a category rather than a measurement. A candidate
  outside the allowed category is not simply rejected: with a
  justification on record it is retained under restriction, and the
  restriction travels with it into the report.
- The temperature rating is graded against the hot case plus the same
  margin the thermal case carries, so a material rated exactly at the
  predicted temperature is short, not marginal.
- Galvanic coupling is a property of a pair and of the environment
  around it, never of a material alone. The same two alloys are an
  acceptable couple in a controlled bay and an unacceptable one at a
  coastal launch site, so the allowance is read from the environment
  the assembly will actually see.
- Contacts are declared, not inferred. A pair nobody wrote down is a
  pair nobody graded.

## Workflow

1. Normalize the candidate list and reject it outright on a duplicate
   identifier, a contact naming a material that is not in the list, or
   a material declaring contact with itself, because a couple that
   cannot be resolved cannot be graded.
2. Grade the vacuum figures for each candidate, reporting mass loss
   and condensable volatiles as separate findings so a marginal
   material is not confused with a badly contaminating one.
3. Grade contact-with-charge behaviour: gas evolution against its
   limit, then the decomposition-onset depression against its own.
4. Grade stress-corrosion susceptibility against the allowed category,
   and split the outcome three ways: inside the category, outside but
   justified, and outside with nothing on record.
5. Grade each temperature rating against the predicted hot case plus
   the declared margin.
6. Build the contact pairs from the declared contacts, grade each
   against the environment's allowance, and close with the accepted,
   restricted and rejected groups plus any pair that failed.

## Pitfalls

- Screening the material and the explosive separately and declaring
  the pair acceptable. The gas evolution and onset numbers only exist
  because that inference is unreliable.
- Reading total mass loss as the whole outgassing answer. A material
  can lose very little and still deposit enough condensable volatiles
  on an optic or a contact to matter; the two limits fail
  independently.
- Treating an onset depression of a few kelvin as noise. It moves the
  decomposition-onset margin the thermal case was closed against, so
  the material choice quietly reopens a check that was already signed.
- Rejecting a moderately susceptible alloy outright, or keeping it
  silently. The honest middle is to keep it against a recorded
  justification and carry the restriction forward into the report.
- Grading a galvanic couple against one allowance for the whole
  programme. The allowance follows the environment, and a couple
  qualified in a controlled bay can be unacceptable on the pad.
- Comparing a measurement with its limit by bare arithmetic. A
  material sitting exactly on a limit can land a few units in the last
  place above it; the comparison absorbs that while the limit stays
  untouched.

## Behavior contract (gate 3)

The candidate normalization, contact-pair resolution, outgassing,
compatibility, corrosion, service-temperature and galvanic gates, the
per-material grouping and the assembly verdict are exercised by the
gate 3 contract test: scripts/test_e3311_materials.py against
scripts/e3311_materials_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e3311_materials.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
