---
name: q60-class-3-radiation-hardness-selection
description: "Verify that a Class 3 part's radiation tolerance covers the environment behind its own local shielding across the whole declared lifetime under ECSS-Q-ST-60C clause 6.2.2.4: accumulate dose phase by phase, set the design margin from how the capability figure was obtained rather than from a constant, owe a lot-specific test once a datasheet or similarity claim passes the trigger dose, cut a rate-sensitive technology characterised at high dose rate, grade destructive and recoverable single event mechanisms apart, then name the binding mechanism, the evidence still owed and one disposition. Use when a Class 3 design has to show a part survives its orbit for the full mission. Trigger: ecss, q-st-60c, q60-c3-radiation-tolerance-matching, q60-c3-mission-accumulated-dose, q60-c3-evidence-weighted-design-margin, q60-c3-destructive-single-event-bar, q60-c3-lot-specific-dose-test-trigger."
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
  tags: [ecss, q-st-60c, q60-class-3-radiation-hardness-selection, q60-c3-radiation-tolerance-matching, q60-c3-mission-accumulated-dose, q60-c3-evidence-weighted-design-margin, q60-c3-destructive-single-event-bar, q60-c3-lot-specific-dose-test-trigger, q60-c3-rate-sensitivity-cut]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Radiation Hardness Selection (space-systems/ecss/q60-class-3-radiation-hardness-selection)

Use when the task is the radiation matching of ECSS-Q-ST-60C clause
6.2.2.4 -- deciding, for a Class 3 design, whether a candidate part's
tolerance covers the environment behind its own shielding over the full
declared lifetime, and what each shortfall costs.

## Domain quick reference

- A part is not selected against a radiation number in the abstract. It
  is selected against the dose it will actually accumulate behind its
  own local shielding over the declared lifetime, and against the heavy
  ions it will meet while it is switched on.
- Dose is a lifetime quantity, so it is accumulated phase by phase. A
  transfer orbit contributes more per year than the operational orbit
  and a short commissioning phase can dominate a long quiet one; a
  single average annual figure hides both. Local shielding scales what
  arrives -- a part inside a filled box sees less than the box wall
  implies, a part on an external panel sees more.
- The margin on top is not a constant. It is set by how the capability
  figure was obtained: a lot-specific test on the parts being bought
  carries the least uncertainty, heritage on the same date code carries
  more, a manufacturer's datasheet figure is a population claim rather
  than a lot claim, and a similarity argument to another part is the
  weakest of all. The margin rises as the evidence weakens, which is
  what makes a cheap datasheet number expensive in dose terms.
- Past a mission dose threshold the weak claims stop being admissible
  at all. A lot-specific test is owed instead, and the part is neither
  adequate nor inadequate until it exists -- it is unevidenced.
- A rate-sensitive technology adds a trap. Bipolar and BiCMOS parts
  degrade more at the slow dose rates of a real orbit than in a fast
  ground test, so a capability characterised at high dose rate is cut
  before it is compared with anything.
- Single event effects are graded apart and not all alike. A
  destructive mechanism ends the part, so its ion threshold has to
  clear the environment with margin and only latch-up can be argued
  away at application level by limiting and cycling the supply. A
  recoverable mechanism costs availability rather than hardware, so a
  credited application-level mitigation closes it.
- An undeclared destructive mechanism is untested, not immune. It is
  reported as evidence owed rather than quietly passing.

## Workflow

1. Declare the mission phase by phase with its years and annual dose,
   and the local shielding factor at the part.
2. Accumulate the dose across the phases and scale it by the shielding.
3. Read the margin from the capability data source and apply it to the
   accumulated dose to get what the part has to withstand.
4. Cut the rated capability where the technology is rate-sensitive and
   the characterisation was fast, then grade it. A part sized exactly
   to its requirement is on the limit, not short.
5. Where the accumulated dose passes the trigger and the claim is a
   datasheet or similarity figure, record a lot-specific test as owed
   instead of grading the margin.
6. Grade each single event mechanism against the environment, with the
   larger factor on the destructive ones, and credit only the
   mitigations that genuinely apply to that mechanism.
7. Close with the binding mechanism, the evidence owed, the mitigations
   to hold as design constraints and one disposition.

## Pitfalls

- Grading against the operational orbit alone. The transfer and
  commissioning phases are short and hot, and dropping them understates
  the lifetime dose the part is being selected against.
- Applying one margin factor to every part. The margin is the price of
  the evidence; a datasheet figure and a lot test do not deserve the
  same one, and using the small factor on the weak claim is the common
  way a selection looks covered.
- Comparing a fast ground characterisation with a slow orbit directly
  on a bipolar part. The cut exists because the ground number flatters
  the part, and skipping it flatters the selection.
- Treating an absent single event threshold as a pass. Nothing was
  measured, so nothing is known; a destructive mechanism nobody
  declared is the one that ends the mission.
- Crediting a mitigation against the wrong mechanism. Limiting and
  cycling the supply saves a latched part; it does nothing for burnout
  or gate rupture, which are over before any protection reacts.
- Comparing a margin ratio with unity by bare arithmetic. Every ratio
  here is a quotient of accumulated quantities, so a part sized exactly
  to its requirement can land a few units in the last place under it;
  the comparison absorbs that while the requirement stays untouched.

## Behavior contract (gate 3)

The mission profile validation, phase-by-phase dose accumulation with
the shielding factor, the evidence-weighted design margin, the
lot-specific test trigger, the rate-sensitivity cut, the dose grade
including the exact-limit case, the destructive and recoverable single
event bars with their mitigation credits, the undeclared destructive
mechanisms, the binding mechanism and the disposition are exercised by
the gate 3 contract test:
scripts/test_q60_class_3_radiation_hardness_selection.py against
scripts/q60_class_3_radiation_hardness_selection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_3_radiation_hardness_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
