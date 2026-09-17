---
name: q60-class-2-handling-and-storage
description: "Assess the handling and storage chain a Class 2 EEE lot passed through under ECSS-Q-ST-60C clause 5.4: band the part by the discharge voltage it withstands, read the protection level and measures that band owes, grade every custody leg from receipt through bonded store, kitting and line issue against the protection its location actually held, accumulate the open-air minutes spent outside dry storage against the lot's budget, report store temperature and humidity as margins to their nearest limits, and read the re-inspection clock. Use when a Class 2 lot is moved, stored or reviewed before issue. Trigger: ecss, q-st-60c, class-2-esd-withstand-band, class-2-custody-leg-protection, class-2-open-air-minute-budget, class-2-store-environment-margin, class-2-handling-chain-disposition."
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
  tags: [ecss, q-st-60c-eee-components-scope, q-st-60c, q60-class-2-handling-and-storage, class-2-esd-withstand-band, class-2-custody-leg-protection, class-2-open-air-minute-budget, class-2-store-environment-margin, class-2-handling-chain-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 2 — Handling and Storage (space-systems/ecss/q60-class-2-handling-and-storage)

Use when the task is clause 5.4 of ECSS-Q-ST-60C: the handling, packaging and
storage procedures that keep Class 2 parts free of damage and degradation.
This leaf grades the chain a lot actually travelled rather than the procedure
the quality plan says it should have travelled.

## Domain quick reference

- What a part is owed comes from what it survives. A part that withstands less
  is owed more, so the band is read off the discharge withstand voltage and
  the protection level and measures follow from the band, never from the value
  of the part or the convenience of the bay it is stored in.
- Protection levels are cumulative. Level three carries everything level two
  carries, which is why a shortfall is a number of levels rather than a list
  of ticked and unticked measures.
- A custody chain is not an average. One leg across an open bench exposes the
  part exactly as much as if the whole chain had run that way, so the weakest
  leg is what the chain is graded on and the protected legs buy nothing back.
- An ungraded location cannot be credited. A location the register does not
  carry has no level to compare against, and crediting it as protected because
  it is indoors is how an unprotected leg disappears from the record.
- The open-air budget is time outside dry storage, not time in custody. Hours
  in a dry cabinet are custody and do not spend the budget; minutes on an open
  bench do, and they accumulate across every leg rather than per visit.
- Environment is reported as a margin, not an alarm. A store sitting one
  degree inside its limit and one in the middle of its band pass the same test
  and are not the same store, so the margin is carried through.

## Workflow

1. Band the part by its withstand voltage and read the protection level and
   measures the band owes, treating a voltage exactly on a band edge as inside
   the more demanding band.
2. Grade every custody leg against the level its location held, refusing an
   ungraded location, and keep the weakest leg rather than a mean.
3. Accumulate the open-air minutes across the chain, excluding legs recorded
   as dry storage, and test them against the lot's budget.
4. Return the store temperature and humidity as margins to their nearest
   limits, counting a reading exactly on a limit as inside by tolerance.
5. Read the months since the last re-inspection against the interval.
6. Rank the findings: a shortfall of two or more levels, an overspent open-air
   budget or an out-of-limit store quarantines the lot; a single-level
   shortfall, a nearly spent budget or a due re-inspection earns actions;
   anything less is fit for issue.

## Pitfalls

- Averaging the chain. Three protected legs and one open bench average to a
  comfortable number and describe a part that was handled unprotected.
- Grading the part on its price rather than its withstand voltage. The cheap
  part with the low withstand is the one that needs the ionizer.
- Counting dry-cabinet hours against the open-air budget. The budget then
  exhausts in store, and the real exposure on the line is never visible.
- Counting open-air minutes per visit. The budget is cumulative across the
  chain, and per-visit counting passes a part opened ten times briefly.
- Reducing the store environment to a pass. The margin is what separates a
  logged deviation from reconditioning, and it is discarded at the comparison.
- Crediting an ungraded location because it looked tidy. An ungraded location
  is a refusal and a register entry, not a judgement made at the door.

## Behavior contract (gate 3)

The withstand banding, owed measures, custody leg grading, weakest-leg
selection, open-air budget accumulation, environment margins, re-inspection
clock and the handling disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_2_handling_and_storage.py against
scripts/q60_class_2_handling_and_storage_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q60_class_2_handling_and_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
