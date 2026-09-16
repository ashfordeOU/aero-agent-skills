---
name: q6013-class-3-destructive-physical-analysis
description: "Use when a commercial lot needs a teardown decision. Determine whether destructive physical sampling is owed by a lowest assurance commercial EEE lot under ECSS-Q-ST-60-13C clause 6.3.9: run the trigger register over source franchise, manufacturer history, technology watch list, application criticality and date-code age, hold a quiet lot open until its waiver carries a recorded reason, size the teardown sample in exact integer arithmetic, credit a matching recent prior analysis down to a confirmation count, group observed findings against a named defect register, and dispose the lot on the major-defect rule. Trigger: ecss, q-st-60-13c-clause-6-3-9, class-three-destructive-physical-sampling, teardown-trigger-register, recorded-waiver-justification, prior-analysis-teardown-credit, major-defect-lot-disposition, class-three-teardown-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-destructive-physical-analysis, class-three-destructive-physical-sampling, teardown-trigger-register, recorded-waiver-justification, prior-analysis-teardown-credit, major-defect-lot-disposition, class-three-teardown-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE -- Class 3 Destructive Physical Sampling (space-systems/ecss/q6013-class-3-destructive-physical-analysis)

Use when the task is the clause 6.3.9 construction question of
ECSS-Q-ST-60-13C at the lowest assurance category: a commercial lot has
arrived, and the first question is not how much of it to tear down but
whether any of it has to be torn down at all.

## Domain quick reference

- This is the category where the teardown is owed on risk rather than on
  every lot. The register decides, and it asks about what is unknown
  regarding how the part was built, never about whether the part works.
- Five conditions fire it: a source outside the franchised chain, a
  manufacturer with no prior lot behind it, a technology already on the
  watch register, an application where the part is a single point of
  failure, and a date code past the shelf limit. Any one of them is
  enough, and they are read independently.
- A quiet lot is not automatically a released lot. Nothing firing means
  the teardown can be waived, and a waiver is a decision somebody makes
  on the record. A lot released with no written reason has not been
  waived, it has been forgotten.
- Sample size is a percentage of the lot, rounded up, raised to a floor
  and capped. Integer arithmetic throughout, so the same lot gives the
  same sample on every machine that runs it.
- A lot small enough that its own sample consumes it is a procurement
  finding, not an arithmetic one. The answer is to buy a larger lot,
  never to skip the teardown or to shave the sample until it fits.
- Credit for a prior analysis is conditional on five things at once:
  same manufacturer, same technology, same date code, young enough to
  describe the same build, and no major defect found. Four out of five
  buys nothing, because the one that failed is the one that matters.
- Credit thins the sampling; it never removes it. A credited lot still
  owes a confirmation count, because the units in the box are not the
  units the prior report describes.
- An observation outside the defect register is refused rather than
  filed as cosmetic. Unregistered is unexamined, and the only honest
  answer is to name it before deciding what it means.

## Workflow

1. Run the trigger register over the lot, reading each condition
   independently and refusing a condition name the register does not
   hold.
2. When nothing fired, look for the recorded reason: a written
   justification closes the lot, its absence leaves the question open.
3. Validate the sampling policy: the percentage, the floor, the cap and
   the confirmation count a credited lot still owes. A confirmation
   count above the full sample would sample a credited lot harder than
   an uncredited one and is refused rather than used.
4. Size the teardown sample from the lot, and raise the feasibility
   finding when the sample would consume it.
5. Decide credit from the prior analysis offered, recording every reason
   whether or not credit is granted, and drop a credited lot to the
   confirmation count.
6. Group the observations against the defect register, then dispose:
   any major defect rejects the lot, a credited clean teardown closes on
   the credit, and an uncredited clean teardown meets the category.

## Pitfalls

- Treating a quiet register as a finished assessment. The waiver is the
  output in that case, and an unwritten waiver is not one.
- Reading the triggers as a score to be weighed. They are independent
  conditions; one firing is the whole answer, and four not firing does
  not soften it.
- Crediting a prior analysis on the strength of the manufacturer alone.
  A different date code is a different build with a different assembly
  history, and that is precisely what a teardown looks at.
- Letting credit drive the sample to nothing. The relaxation this
  category grants is a thinner sample, not an absent one.
- Shaving the sample so a small lot survives it. A lot that cannot
  afford its own teardown has told you something about the procurement,
  not about the sampling plan.
- Defaulting an unfamiliar observation to minor. The register is the
  decision, and an observation outside it has not been judged at all.
- Moving the credit age limit so a report sitting exactly on it passes.
  A value on its limit is inside it, and the representation error at
  that boundary is absorbed by the tolerance inside the comparison
  rather than by widening the limit.

## Behavior contract (gate 3)

The trigger register, the recorded-waiver rule, integer sample sizing
and the feasibility finding, the five prior-analysis credit conditions,
the defect-register grouping including the unregistered-code refusal,
and the six verdicts are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_destructive_physical_analysis.py against
scripts/q6013_class_3_destructive_physical_analysis_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6013_class_3_destructive_physical_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
