---
name: q6013-legacy-class-1-acceptance-table
description: "Evaluate a legacy lot acceptance test list for active commercial parts bought to the highest assurance class against the ECSS-Q-ST-60-13C Table 8-11 programme: confirm every required acceptance subgroup is declared once, resolve each subgroup's sample and accept number from the band the screened quantity falls into rather than from a proportion, refuse a list that draws less than its band asks for, take each subgroup's failures against that accept number, allow one doubled-sample retest only where the list permits one, hold back what the destructive subgroups consume, and report the deliverable quantity left. Use when a heritage active part lot's acceptance list has to become a verdict and a shippable count. Trigger: ecss, q-st-60-13c-table-8-11, legacy-lot-acceptance-test-list, acceptance-sampling-band-table, destructive-subgroup-consumption, doubled-sample-retest-rule, deliverable-quantity-after-acceptance."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-legacy-class-1-acceptance-table, legacy-lot-acceptance-test-list, acceptance-sampling-band-table, destructive-subgroup-consumption, doubled-sample-retest-rule, deliverable-quantity-after-acceptance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Parts -- Legacy Lot Acceptance Test List, Highest Assurance Class (space-systems/ecss/q6013-legacy-class-1-acceptance-table)

Use when the task is the Table 8-11 lot acceptance test list of
ECSS-Q-ST-60-13C: a screened lot of active commercial parts with legacy
standing is being accepted to the highest assurance class, and the question
is whether the declared subgroups accept the lot and how many parts are left
to deliver once they have been run.

## Domain quick reference

- The population here is what screening delivered, not what was ordered.
  Acceptance follows screening, so every sample is drawn from the screened
  quantity and a list written against the procurement quantity draws from a
  lot that no longer exists.
- The sample comes from a band table, not a proportion. A lot of sixty and a
  lot of a hundred and forty fall in one band and draw the same number of
  parts; reading the sample off a percentage under-draws a large lot and
  over-draws a small one, and changes the accept number with it.
- A list may draw more than its band asks for. It may never draw less: an
  enlargement is a tightening the buyer is free to make, while a reduction
  is the sampling plan being rewritten and has to be corrected in the list
  rather than absorbed at the verdict.
- Acceptance is on the accept number of the band, which is zero for every
  band a small or medium lot falls into. A single failure in an accept-on-
  zero subgroup fails that subgroup outright.
- One retest, on a doubled sample, and only for the subgroups the list
  permits it for. The construction analyses take none: drawing a second
  sample asks the same question about a different device rather than
  resolving the first answer. A second retest is refused, not run.
- Several subgroups end the parts they touch. Bond strength, die shear, the
  sealed-package moisture reading, the life sample and the physical analysis
  all consume their sample, so the deliverable quantity is the screened
  quantity less every destructive sample drawn -- retests included.

## Workflow

1. Validate the screened quantity; it is the population every sample comes
   from and the number the deliverable count is taken off.
2. Check coverage: every required acceptance subgroup present and declared
   once, with any additional subgroup reported as an addition rather than
   counted towards coverage.
3. Resolve each subgroup's sample and accept number from the band the
   screened quantity falls into, take a declared enlargement as written, and
   refuse a declared sample below the band or an accept number above it.
4. Take each subgroup's failures against its accept number, refusing a
   failure count larger than the sample it came from.
5. Run at most one doubled-sample retest, only for a subgroup that failed
   and that the list permits a retest for, and refuse a doubled sample the
   screened quantity cannot supply.
6. Total what the destructive subgroups consumed, including any retest
   sample, and subtract it from the screened quantity to get the deliverable
   count; refuse a programme that consumes more than the lot holds.
7. Accept the lot only when coverage is complete and every subgroup ended
   accepted, naming every failing subgroup rather than the first, and report
   the deliverable quantity either way.

## Pitfalls

- Drawing the sample as a percentage of the lot. The plan is a band table,
  and a proportion silently replaces both the sample size and the accept
  number that came with it.
- Letting a list declare a smaller sample than its band. That is the
  sampling plan being rewritten at the point of use, and it always looks
  like a lot that passed.
- Retesting a construction analysis. A second destructive sample answers the
  same question about another device and consumes more of the lot doing it.
- Running a second retest after the first failed. The rule is one, and a
  subgroup that failed twice has already answered.
- Reporting the screened quantity as the deliverable quantity. The
  destructive subgroups consumed their samples, and a shipping count that
  ignores them promises parts that no longer exist.
- Forgetting the retest sample in the consumption. A recovered subgroup
  consumed three times the parts of a clean one, and that is exactly the
  case where the deliverable count matters most.

## Behavior contract (gate 3)

The screened-quantity validation, sampling-band resolution, declared-sample
checks, list coverage, per-subgroup verdict, the single doubled-sample
retest, the destructive consumption and the deliverable quantity with the
accept-or-reject disposition are exercised by the gate 3 contract test:
scripts/test_q6013_legacy_class_1_acceptance_table.py against
scripts/q6013_legacy_class_1_acceptance_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_legacy_class_1_acceptance_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
