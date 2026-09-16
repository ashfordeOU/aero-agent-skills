---
name: q6013-class-2-destructive-physical-analysis
description: "Use when a teardown record has to become a lot disposition. Evaluate the destructive physical sampling owed by a delivered commercial EEE lot at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.3.9: size the teardown sample per date-code group, decide whether a signed manufacturer teardown report covers that group and credits it down to a confirmation sample, categorize observed construction defects against a named register, judge die-attach voiding and wire bond pull strength against declared limits, and separate a single major defect calling for a second sample from a group that is rejected outright. Trigger: ecss, q-st-60-13c-clause-5-3-9, class-two-destructive-physical-sampling, date-code-group-teardown-sizing, credited-manufacturer-teardown-report, die-attach-void-criteria, wire-bond-pull-criteria, second-sample-construction-disposition."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-destructive-physical-analysis, class-two-destructive-physical-sampling, date-code-group-teardown-sizing, credited-manufacturer-teardown-report, die-attach-void-criteria, wire-bond-pull-criteria, second-sample-construction-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Destructive Physical Sampling (space-systems/ecss/q6013-class-2-destructive-physical-analysis)

Use when the task is the clause 5.3.9 construction question of
ECSS-Q-ST-60-13C at the intermediate assurance class: a commercial EEE
lot has arrived, a sample of it is going to be destroyed to see how it
was actually built, and the question is how much has to be torn down and
what the teardown then says about the rest of the delivery.

## Domain quick reference

- The sample is destroyed to speak for a population, so the population
  is defined before the sample is drawn. That population is the
  date-code group, not the order line: a distributor fills one line off
  the shelf, and two date codes are two builds with two assembly
  histories.
- Two relaxations define this class and neither exists at the class
  above. A manufacturer teardown report may be credited in place of part
  of the receiving activity's own sampling, and a single major defect
  calls for a second sample rather than disposing of the group.
- Credit is conditional, not automatic. The report has to name the same
  date-code group, be signed, be young enough to describe the same
  build, and cover every construction criterion the group is judged on.
  A report that covers three of the four criteria leaves the fourth
  unexamined, and crediting it buys nothing.
- Credit thins the sampling; it never removes it. A credited group still
  owes a confirmation sample, because the units in the box are not the
  units the report describes, and the confirmation sample is the only
  thing tying the two together.
- Sample size is the greater of a sampling fraction of the group,
  rounded up, and a floor, capped at the group size. A group small
  enough that its own sample consumes it is a procurement finding, not
  an arithmetic one; the answer is to buy a larger group, never to skip
  the teardown.
- A defect register with two categories, major and minor, is what turns
  an observation into a decision. An observation outside the register is
  not a minor defect, it is an unregistered one, and it is categorized
  deliberately rather than defaulting to cosmetic.
- Voiding carries two criteria and so does bond strength. A die attach
  can meet the total voided area and still fail on one void under the
  hottest junction; a bond sample can clear every individual bond and
  still sit low on average, which is process drift rather than one bad
  bond.
- The second sample is the mechanism that separates an assembly escape
  from a process producing them. A major defect surviving into the
  second sample is no longer a one-off and disposes of the group.

## Workflow

1. Validate the sampling policy first: the proportional fraction, the
   sample floor, the confirmation sample a credited group still owes,
   the age limit on a credited report and the major-defect count that
   calls for a second sample. A confirmation sample above the floor
   would sample a credited group harder than an uncredited one and is
   refused rather than used.
2. Resolve the delivery into date-code groups and validate each one. A
   repeated date code, a zero-count group or a group with neither a
   teardown nor a credited report closes the assessment.
3. Decide credit for each group from the report offered against it,
   recording the reason whether or not credit is granted, then size the
   sample and raise a finding for any group its own sample consumes.
4. Categorize every observed defect code against the register. Refuse an
   unregistered code rather than defaulting it to minor.
5. Evaluate die-attach voiding against both the total and the
   largest-single-void limits, refusing a largest void that exceeds the
   total and limits that are mutually inconsistent.
6. Evaluate bond pull strengths against the absolute floor and the mean
   floor, refusing a floor set above the mean floor.
7. Fold the numeric failures back into the defect record as their
   registered codes, dispose each group, and close the delivery on one
   verdict: sampling not performed, sample not feasible, construction
   rejected, second sample required, or sampling meets class two scope.

## Pitfalls

- Sampling the order line instead of the date-code group. One sample
  spread across two builds speaks for neither, and the build that was
  not sampled is the one that ships.
- Taking a manufacturer report at face value. An unsigned report, one
  for a neighbouring date code, or one old enough to describe a
  superseded assembly line is evidence about a different population.
- Letting credit drive the sample to nothing. The relaxation this class
  grants is a thinner sample, not an absent one, and a group with no
  confirmation sample has no link at all to the box that arrived.
- Judging voiding on the total area alone, or bond strength on the mean
  alone. Each criterion catches a failure the other misses.
- Treating the second sample as a way to pass. It exists to test whether
  a major defect repeats; a defect that repeats disposes of the group,
  and a third sample is not the next step.
- Relaxing a limit so an exact-equality case passes. A value sitting on
  its limit is inside it, and the representation error at that boundary
  is absorbed by the tolerance inside the comparison rather than by
  widening the limit.

## Behavior contract (gate 3)

The policy validation, the manufacturer credit decision, the per-group
sample sizing and feasibility finding, the defect categorization, the
die-attach void and bond pull assessments, the group disposition
including the second-sample rule, and the delivery verdict are exercised
by the gate 3 contract test:
scripts/test_q6013_class_2_destructive_physical_analysis.py against
scripts/q6013_class_2_destructive_physical_analysis_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6013_class_2_destructive_physical_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
