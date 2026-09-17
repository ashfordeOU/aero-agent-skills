---
name: q60-retinned-part-acceptance
description: "Evaluate a retinned component lot against the acceptance conditions of ECSS-Q-ST-60C clause 8. Use when parts have been hot solder dipped to replace a pure tin finish and the lot has to be accepted, screened or rejected: size the sample from the lot with an integer fraction, a floor, a ceiling and a full-inspection rule for very small lots, set an accept number that is zero for every critical or destructive attribute, bound the dip temperature, dwell, dip count and total time at temperature against the part's own limit, confirm the finish left behind is genuinely lead bearing, and combine the outcomes into one lot verdict. Trigger: ecss, q-st-60c-clause-8-retinning, retinned-lot-acceptance-sample-size, hot-solder-dip-thermal-exposure-limits, retinned-lead-solderability-attribute, retin-accept-on-zero-attribute, residual-lead-content-after-retinning."
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
  tags: [ecss, q-st-60c-eee-component-scope, q60-retinned-part-acceptance, q-st-60c-clause-8-retinning, retinned-lot-acceptance-sample-size, hot-solder-dip-thermal-exposure-limits, retinned-lead-solderability-attribute, retin-accept-on-zero-attribute, residual-lead-content-after-retinning]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Retinned Part Acceptance (space-systems/ecss/q60-retinned-part-acceptance)

Use when the task is the retinning provisions of ECSS-Q-ST-60C clause 8 — a
lot of parts whose terminations have been re-tinned to get them out of pure
tin, the sample the evaluation is drawn on, and whether the lot can be used.

## Domain quick reference

- Retinning is a repair with its own hazards. The operation that removes the
  whisker risk puts the part through a thermal excursion it was not sold to
  survive, so the acceptance looks at the process as hard as at the parts.
- Sample size is a decision, not a percentage. A lot small enough that a
  fraction of it is one or two pieces is inspected part by part; a lot large
  enough to make the fraction unaffordable is capped.
- The fraction is carried in whole numbers. A percentage applied as a float
  lands on either side of a round sample count depending on the host, and a
  sample that differs between two machines is not a sample.
- Accept numbers are not uniform. Solderability, terminal strength, seal and
  electrical behaviour accept on zero — one reject is the lot. Cosmetic and
  dimensional attributes take a small number scaled to the sample drawn.
- Thermal exposure is four bounds, not one. The dip temperature against the
  part's own declared limit, the dwell of a single dip, how many dips were
  taken and the total time at temperature; a process can clear three and fail
  the fourth.
- The composition after the operation is the point of the operation. A retin
  that leaves the finish still under the pure tin threshold has spent the
  thermal budget and bought nothing.
- An unqualified process makes every measurement an observation. The results
  may all be clean and still not be evidence, so qualification is a gate
  ahead of the numbers rather than a line in them.
- Only cosmetic overshoot is recoverable. Screening every part can find
  dimensional rejects the sample flagged; it cannot undo an over-temperature
  dip or put lead into a finish that has none.

## Workflow

1. Validate the lot: identifier, lot size, the retinning process description,
   the attribute results and whether the process is qualified.
2. Size the sample: full inspection below the small-lot threshold, otherwise
   the integer fraction rounded up, held between the floor and the ceiling
   and never larger than the lot.
3. Set the accept number for each attribute — zero where the attribute is
   critical or destructive, scaled to the sample where it is cosmetic — and
   compare the rejects reported against it.
4. Bound the thermal exposure on all four counts and collect every bound the
   operation broke.
5. Check the lead content of the finish left behind against the threshold
   that takes a part out of pure tin.
6. Combine: any critical reject, thermal finding, composition shortfall or
   missing qualification rejects the lot; cosmetic overshoot alone calls for
   screening; anything else is accepted, with every finding behind it.

## Pitfalls

- Applying the sample percentage as a float. The rounding moves between
  hosts, and two reviewers then draw different samples from the same lot.
- Using one accept number for every attribute. A single solderability reject
  and a single cosmetic reject are not the same event, and averaging them
  passes the lot that matters.
- Checking the dip temperature and stopping. Two short dips inside the
  temperature limit can still exceed the total time at temperature the part
  can take.
- Comparing the dip against a generic solder limit. The bound is the part's
  own declared process temperature, and a part with a lower limit than the
  bath is the case the check exists for.
- Forgetting to measure what came out. A retin is judged by the composition
  it leaves, not by the fact that it was performed.
- Screening a lot that cannot be screened. Sorting parts finds the ones that
  failed an attribute; it does not reverse a thermal excursion every part in
  the lot went through.

## Behavior contract (gate 3)

The whole-number sample sizing with its small-lot, floor and ceiling rules,
the per-attribute accept numbers, the attribute result evaluation with
duplicate and over-count rejection, the four thermal exposure bounds judged
at the boundary under a named tolerance, the residual lead check, the
process qualification gate and the combined lot verdict are exercised by the
gate 3 contract test:
scripts/test_q60_retinned_part_acceptance.py against
scripts/q60_retinned_part_acceptance_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_retinned_part_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
