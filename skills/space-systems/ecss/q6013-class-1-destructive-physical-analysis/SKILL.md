---
name: q6013-class-1-destructive-physical-analysis
description: "Evaluate a purchased commercial EEE lot through destructive physical analysis under ECSS-Q-ST-60-13C clause 4.3.9. Use when sizing a teardown sample per date-code group of a commercial shipment, sorting observed construction defects into major and minor categories from a named register, judging die-attach voiding and wire bond pull strength against declared limits, and turning the combined record into a lot disposition. Refuses an unregistered defect code, a largest void exceeding the total voided area, and a sample that would consume its own date-code group. Trigger: ecss, q-st-60-13c, commercial-lot-destructive-physical-analysis, date-code-group-sampling, die-attach-void-fraction, wire-bond-pull-strength, commercial-eee-construction-defect-register, purchased-lot-disposition."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-destructive-physical-analysis, commercial-lot-destructive-physical-analysis, date-code-group-sampling, die-attach-void-fraction, wire-bond-pull-strength, purchased-lot-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 1 Destructive Physical Analysis (space-systems/ecss/q6013-class-1-destructive-physical-analysis)

Use when the task is the destructive physical analysis of ECSS-Q-ST-60-13C
clause 4.3.9 — tearing down a sample of a purchased commercial lot to
confirm that what was actually built matches what the Class 1 design
assumed, and deciding what the teardown says about the rest of the lot.

## Domain quick reference

- The analysis is a **sample destroyed to speak for a population**, so
  the population has to be defined before the sample is drawn. For a
  commercial purchase the population is the date-code group, not the
  order line: a distributor fills one line from whatever is on the
  shelf, and two date codes are two builds with two assembly histories.
- Sample size is the greater of a sampling fraction of the group,
  rounded up, and a floor, capped at the group size. A group small
  enough that its own sample consumes it is a procurement finding, not
  an arithmetic one — the answer is to buy a larger group, never to
  skip the teardown.
- A defect register with two categories, major and minor, is what turns
  an observation into a disposition. Major defects bear on function or
  on reliability over life: lifted or necked bonds, cracked die,
  excessive die-attach voiding or delamination, corroded or voided
  metallization, a leaking seal, a conductive particle, glassivation
  cracking over metal. Minor ones are cosmetic or positional and are
  recorded without disposing of the lot.
- An observation that is not in the register is not a minor defect. It
  is an unregistered defect, and the correct response is to categorize
  it explicitly and add it, because an unrecognised code silently
  treated as cosmetic is how a real construction defect ships.
- Voiding carries **two** criteria, not one: the total voided area
  fraction under the die and the largest single void. A die attach can
  meet the total and still fail on one void sitting under the hottest
  junction, so both are evaluated and either one disposes of the lot.
- Bond strength likewise carries two: the weakest bond in the sample
  against an absolute floor, and the sample mean against a mean floor.
  A sample that clears every individual bond but sits low on average is
  a process drift finding.

## Workflow

1. Resolve the shipment into date-code groups and validate the counts;
   an empty shipment or a zero-count group is an input error.
2. Size the destructive sample for each group from the sampling fraction
   and the floor, and raise a finding for any group its own sample would
   consume. Raise a finding when the shipment spans more than one date
   code, so the multi-build case is visible in the record.
3. Categorize every observed defect code against the register. Refuse an
   unregistered code rather than defaulting it to minor.
4. Evaluate die-attach voiding against both the total and the
   largest-single-void limits, refusing a largest void that exceeds the
   total and limits that are mutually inconsistent.
5. Evaluate bond pull strengths against the absolute floor and the mean
   floor, refusing a floor set above the mean floor.
6. Fold the numeric failures into the defect record as their registered
   codes, so a voiding failure and an observed void defect land in one
   place and are reported once.
7. Return the disposition — accepted, accepted with a recorded
   observation, or rejected — with the findings that produced it.

## Pitfalls

- Sampling the order line instead of the date-code group. One sample
  spread across two builds speaks for neither, and the build that was
  not sampled is the one that ships.
- Letting an unrecognised observation through as cosmetic. The register
  is the whole mechanism by which a teardown becomes a decision; a code
  outside it has to be categorized deliberately, never by default.
- Judging voiding on the total area alone. A single large void under a
  power die is a thermal path failure whatever the total says.
- Judging bond strength on the mean alone, or on the weakest bond alone.
  The two criteria catch different failures: a single bad bond, and a
  whole sample drifting down.
- Treating a rounded-up proportional sample as optional on a large
  group. The fraction is what makes the sample scale with the purchase;
  the floor exists for small groups, not as the answer for every group.
- Relaxing a limit so an exact-equality case passes. A value that sits
  on its limit is inside it, and the representation error at that
  boundary is absorbed by the tolerance inside the comparison.

## Behavior contract (gate 3)

The sample sizing, date-code grouping, defect categorization,
die-attach void assessment, bond pull assessment and lot disposition are
exercised by the gate 3 contract test:
scripts/test_q6013_class_1_destructive_physical_analysis.py against
scripts/q6013_class_1_destructive_physical_analysis_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6013_class_1_destructive_physical_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
