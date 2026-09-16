---
name: q6013-class-3-selection-rules
description: "Use when a Class 3 build has to justify a commercial part and show the baseline selection rules were applied. Evaluate a candidate commercial EEE part against the baseline Class 3 selection rules of ECSS-Q-ST-60-13C clause 6.2.2.1: measure the rated temperature range against the mission environment at both ends, grade production status, manufacturer quality system, lot and date-code traceability, and whether a qualified higher-assurance part already fits the same slot, then name the binding rule and the action every open rule still owes. Trigger: ecss, q-st-60-13-commercial-eee-scope, class-3-part-selection-baseline, commercial-part-production-status-screening, commercial-part-temperature-range-coverage, commercial-part-lot-traceability, qualified-alternative-availability-test, class-3-selection-binding-rule."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-3-selection-rules, class-3-part-selection-baseline, commercial-part-production-status-screening, commercial-part-temperature-range-coverage, commercial-part-lot-traceability, qualified-alternative-availability-test, class-3-selection-binding-rule]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 3 Selection Rules (space-systems/ecss/q6013-class-3-selection-rules)

Use when the task is the baseline part choice of ECSS-Q-ST-60-13C
clause 6.2.2.1 -- deciding whether a commercial EEE part may take a
slot on a Class 3 build at all, and what a part that only half
qualifies still owes before it can.

## Domain quick reference

- Class 3 is the lowest assurance category a commercial part can be
  bought under, and it is the one most often reached for because it
  costs the least. The baseline rules exist so that lowest assurance
  never drifts into no rule at all: a part still earns its slot.
- Five rules carry the baseline. The maker's rated temperature range
  has to cover the mission environment at both ends with the margin the
  project declares. The part has to still be in supply. The line that
  built it has to be described by a certified or audited quality
  system. The delivery has to carry a lot identity and a date code.
  And no qualified higher-assurance part may already fit the slot.
- The temperature rule is graded at both ends, not as one range. A part
  with an enormous hot margin and four degrees at the cold end is a
  cold-end part, and the answer a designer needs is which end is tight
  and by how much -- not a single pass.
- Production status is about supply, not about the part. A part whose
  end has been announced is still admissible against a secured lifetime
  buy, because the risk the rule guards is running out mid-programme,
  and a lifetime buy retires exactly that risk.
- Traceability is what makes a commercial part usable at all. A Class 3
  part is bought on the statistics of its population; a delivery with
  no lot identity has no population, so the evidence the whole class
  rests on is absent.
- The qualified alternative is the rule teams skip. Where a part with
  higher assurance already fits the slot, the commercial route costs
  assurance for nothing, and the baseline steers away from it.
- The useful output is not the verdict. It is the binding rule -- the
  single one that produced the answer -- and the action it demands,
  because that is the one thing a project has to change.

## Workflow

1. Declare the candidate: rated temperature range, production status
   and any lifetime buy, quality system, traceability level and whether
   the delivery is a single lot, plus whether a qualified alternative
   exists and fits. Reject an absent status rather than defaulting it.
2. Declare the mission environment and the margin the project requires.
   A margin the project never declared is zero by omission, not by
   agreement, so record it explicitly.
3. Grade the temperature rule at both ends. Report a margin sitting
   exactly on the requirement as met, not as a shortfall.
4. Grade production status, quality system, traceability and the
   qualified alternative, each as met, conditional or breached.
5. Take the worst of the five as the part verdict, and name the rule
   that produced it as the binding rule. Break a tie in the declared
   rule order so the answer is reproducible.
6. Close with one action per rule that is not met, phrased as the
   change a project makes rather than the fault it has.

## Pitfalls

- Grading the temperature rule as one range instead of two ends. A
  generous hot margin hides a cold end with nothing left, and the part
  fails in the environment the mission actually sees.
- Treating an announced end of production as an automatic breach. The
  risk is running out mid-programme, and a secured lifetime buy retires
  it; refusing the part anyway costs a design change for no gain.
- Accepting a maker's declared quality system as a verified one. A
  declaration nobody checked describes an intention, not a line, and
  the whole point of the rule is knowing how the part was built.
- Passing a delivery on a date code alone. The date code narrows the
  build window but does not close the population, so the lot-based
  evidence a Class 3 part rests on cannot be assembled later.
- Choosing the commercial route while a qualified part fits the slot.
  The lower assurance buys nothing at that point, and the decision is
  usually made on a price comparison nobody revisited.
- Comparing a margin with its requirement by bare arithmetic. The
  margin is a difference of two declared temperatures, so a margin
  built to sit exactly on the requirement can land a few units in the
  last place below it; the comparison absorbs that representation error
  while the requirement stays untouched.

## Behavior contract (gate 3)

The temperature-margin computation, the two-ended coverage grading, the
production-status, quality-system, traceability and qualified-
alternative rules, the worst-of-five roll-up, the binding-rule
selection with its declared-order tie break and the open-action list
are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_selection_rules.py against
scripts/q6013_class_3_selection_rules_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_selection_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
