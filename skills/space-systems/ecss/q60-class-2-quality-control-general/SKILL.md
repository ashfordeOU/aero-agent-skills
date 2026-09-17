---
name: q60-class-2-quality-control-general
description: "Determine the receiving control plan a class 2 EEE lot owes once it is booked in under ECSS-Q-ST-60C clause 5.5.1: stop a lot with no identity, quantity, date code or conformity certificate at the door, derive the baseline activities the package style, temperature duty, radiation duty, source and age call for, add the upscreening delta when the delivered flow sits below the flow the application demands, credit back only what current manufacturer evidence carries, order non-destructive work ahead of destructive, size each sample from the delivered quantity, and return one entry disposition. Use when a class 2 lot reaches incoming quality control. Trigger: ecss, q-st-60c, class-2-receiving-control-plan, class-2-manufacturer-evidence-credit, class-2-upscreening-delta, class-2-lot-admissibility-disposition."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-2-quality-control-general, class-2-eee-part, class-2-receiving-control-plan, class-2-manufacturer-evidence-credit, class-2-upscreening-delta, class-2-lot-admissibility-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 2 — Receiving Quality Control Entry Point (space-systems/ecss/q60-class-2-quality-control-general)

Use when the task is clause 5.5.1 of ECSS-Q-ST-60C: the entry point to the
control measures applied to class 2 parts once they have been received. This
leaf opens the control plan for one lot, decides what the project itself still
owes after the manufacturer's own evidence is credited, and says what is
outstanding.

## Domain quick reference

- The entry point is a gate, not a queue. A lot with no traceable identity, no
  stated quantity, no date code or no conformity certificate does not get a
  control plan at all; opening one on an inadmissible lot spends parts on a lot
  that can never be released.
- Class 2 is where the manufacturer's flow carries part of the evidence. The
  plan the project performs is the baseline minus what accepted manufacturer
  evidence already covers — which is exactly the economy class 2 exists for,
  and exactly the place a plan copied from the highest assurance class doubles
  the cost for nothing.
- Credit is conditional, not automatic. Evidence from an unqualified source,
  evidence older than the validity window, and evidence from a flow that never
  reached the demanded grade all carry nothing at all.
- The conformity review, the radiation lot verification and the destructive
  physical analysis stay with the project whatever the manufacturer supplies.
  A credit against those is a credit against work the manufacturer never did
  for this application.
- A part delivered below the flow the application demands owes the upscreening
  delta, and the upscreened lot is the one case where every manufacturer credit
  falls away: the delta is precisely what the manufacturer did not perform.
- Order is a cost decision with no way back. Destructive activities consume the
  parts they touch, so every non-destructive activity closes first.
- Sample size follows lot size in bands, not proportionally. A band boundary
  belongs to the lower band, and a sample can never exceed the lot.
- Coverage is a fraction of the owed plan, not of the activities performed.

## Workflow

1. Test admissibility first: lot identity, delivered quantity, date code and
   the conformity certificate. Report every reason, ordered from identity
   outwards, rather than stopping at the first.
2. Derive the baseline activities from the always-owed class 2 set plus the
   additions the package style, temperature duty, radiation duty, source
   history and months since manufacture call for. A lot sitting exactly on the
   age trigger has not passed it.
3. Compare the delivered procurement flow with the flow the application
   demands and add the upscreening delta when the delivered flow falls short.
4. Credit back the creditable activities the manufacturer's accepted evidence
   carries, withdrawing every credit when the source is unqualified, the
   evidence is past its validity window, or an upscreening delta is owed.
5. Order what remains so every non-destructive activity precedes the
   destructive ones, and size each sample from the delivered quantity: the
   full lot for the whole-lot activities, the banded plan for the sampled ones,
   never more than the lot holds.
6. Compare the activities already closed against the owed set and return the
   outstanding ones, the coverage fraction, and one entry disposition:
   controls-complete, controls-outstanding or lot-not-admissible.

## Pitfalls

- Opening a control plan before testing admissibility. The plan looks healthy
  right up to the point someone asks which lot the parts came from.
- Running the class 1 activity list against a class 2 lot. Every creditable
  activity is then performed twice, once by the manufacturer and once by the
  project, and the lot is no closer to release for it.
- Crediting the manufacturer for an activity on an upscreened lot. The delta
  exists because the delivered flow never reached the demanded grade, so the
  evidence behind it is evidence for a different application.
- Treating a conformity certificate as evidence of the controls themselves.
  The certificate admits the lot; it does not close a single activity.
- Reading a band boundary as the start of the next band. A lot of exactly one
  hundred sits in the lower band; treating it as the higher one draws parts the
  plan never asked for.
- Counting closed activities rather than owed ones. Work performed outside the
  plan inflates progress and closes nothing the lot actually needs.

## Behavior contract (gate 3)

The admissibility test, upscreening comparison, baseline derivation,
manufacturer-evidence credit, non-destructive-first ordering, banded sample
sizing, outstanding-control comparison, coverage fraction and the entry
disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_2_quality_control_general.py against
scripts/q60_class_2_quality_control_general_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_quality_control_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
