---
name: q6013-class-1-radiation-hardness
description: "Use when a Class 1 build has to tie a commercial part choice to hardness assurance. Evaluate a commercial EEE part against the mission radiation environment for a Class 1 build under ECSS-Q-ST-60-13C clause 4.2.2.4: set the radiation design margin from the evidence basis, size the total-dose requirement the part has to cover, test destructive single-event immunity above the environment ion energy with no rate credit, check the mitigated upset rate against the mission budget, decide whether the delivered lot has to be irradiated, and report the dose relief lot testing would buy back. Trigger: ecss, q-st-60-13-commercial-eee-scope, class-1-radiation-hardness-assurance, commercial-part-total-ionising-dose, radiation-design-margin, destructive-single-event-immunity, lot-radiation-acceptance-test, single-event-upset-rate-budget."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-radiation-hardness, class-1-radiation-hardness-assurance, commercial-part-total-ionising-dose, radiation-design-margin, destructive-single-event-immunity, lot-radiation-acceptance-test, single-event-upset-rate-budget, commercial-part-radiation-evidence-basis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 1 Radiation Hardness (space-systems/ecss/q6013-class-1-radiation-hardness)

Use when the task is the hardness tie of ECSS-Q-ST-60-13C clause
4.2.2.4 -- deciding whether a commercial part chosen for a Class 1
build actually meets the mission radiation requirement, and what
evidence the project is entitled to count towards that.

## Domain quick reference

- A commercial part carries no radiation guarantee. Nothing in the
  catalogue entry is a hardness statement, so a Class 1 choice is tied
  to the mission environment by project evidence or it is not tied at
  all.
- Three effects are weighed separately because they fail differently.
  Total ionising dose is a cumulative parameter drift, so it is a dose
  budget. Single-event upset is a recoverable state flip, so it is a
  rate budget that mitigation can work against. Latch-up and burnout
  are destructive, so on a Class 1 build they are an immunity
  requirement with no rate credit at all.
- Evidence basis, strongest to weakest: lot-radiation-test (the
  delivered lot was irradiated), manufacturer-rha (the maker declares a
  level for the line but not for this lot), heritage-data (a different
  lot of the same part number flew), and similarity-argument (a related
  part number was tested).
- A weak basis does not change what the part can survive. It changes
  how much of that capability may be counted, so the basis sets the
  radiation design margin the mission dose is multiplied by before the
  part's capability is asked to cover it.
- Lot testing is compelled in two ways: by a basis that cannot speak
  for the delivered lot at all, and by a maker declaration carried on
  so thin a dose margin that lot-to-lot spread could eat it.
- The gap between the requirement on the current basis and the
  requirement on a lot-tested basis is the dose relief an irradiation
  campaign would buy back, and it is the business case for running one.

## Workflow

1. Declare the evidence basis, the mission dose, the part's dose
   capability, the environment ion energy, the part's destructive
   single-event threshold, the raw upset rate and the mitigation level.
   Reject an uncategorized basis rather than defaulting it.
2. Set the radiation design margin from the basis and size the dose the
   part itself has to cover. Compare the capability against that
   margined figure, not against the bare mission dose.
3. Test destructive single-event immunity against the environment ion
   energy. Treat an undeclared threshold as susceptible: silence is not
   immunity, and a Class 1 build takes no rate credit on a destructive
   effect.
4. Apply the mitigation credit to the raw upset rate and compare the
   residual against the mission rate budget.
5. Decide whether the delivered lot has to be irradiated, from the
   basis and from the dose margin the basis is carrying.
6. Close with one verdict -- suitable, needs lot radiation testing,
   needs upset mitigation, or not suitable -- and report the dose
   relief a lot-tested basis would buy back.

## Pitfalls

- Comparing the part's dose capability with the bare mission dose. The
  margined requirement is the one the part has to clear, and skipping
  the multiplier quietly grants a lot-tested basis to evidence that
  never earned it.
- Counting mitigation against latch-up or burnout. Scrubbing and
  redundancy work on recoverable upsets; a destructive event takes the
  part with it, so on a Class 1 build the threshold has to sit above
  the environment on its own.
- Reading an absent destructive threshold as an absent problem. A
  commercial datasheet is silent on effects it was never tested for,
  and silence has to be carried as susceptible until a test says
  otherwise.
- Letting heritage stand in for the delivered lot. Heritage says a
  different lot survived; commercial lines move wafer fab, die
  revision and assembly site without notice, so the lot in the box is a
  different population.
- Comparing a capability with a requirement by bare arithmetic. The
  requirement is a product and the margin ratio is a quotient, so a
  part built to sit exactly on its requirement can land a few units in
  the last place below it; the comparison absorbs that representation
  error while the requirement stays untouched.

## Behavior contract (gate 3)

The design-margin selection, dose sizing, destructive single-event
immunity test, upset budget check, lot-test trigger and overall verdict
are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_radiation_hardness.py against
scripts/q6013_class_1_radiation_hardness_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_radiation_hardness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
