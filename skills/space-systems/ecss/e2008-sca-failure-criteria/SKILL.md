---
name: e2008-sca-failure-criteria
description: "Evaluate whether a solar cell assembly counts as failed during subgroup testing under ECSS-E-ST-20-08C clause 6.5.1: take each degradation against its own limit for maximum power, short-circuit current and open-circuit voltage rather than one combined figure, hold the insulation resistance above its floor, group the observed defects into disqualifying and acceptable, then count the failed assemblies against the allowance the subgroup carries. Use when a subgroup test record has to become an accept or reject decision. Trigger: ecss, e-st-20-08c-clause-6-5-1, solar-cell-assembly-failure-criteria, sca-subgroup-failure-allowance, assembly-power-degradation-limit, sca-insulation-resistance-floor, disqualifying-assembly-defect."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-sca-failure-criteria, solar-cell-assembly-failure-criteria, sca-subgroup-failure-allowance, assembly-power-degradation-limit, sca-insulation-resistance-floor, disqualifying-assembly-defect]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Solar Cell Assembly Failure Criteria (space-systems/ecss/e2008-sca-failure-criteria)

Use when the task is clause 6.5.1 of ECSS-E-ST-20-08C -- deciding which
conditions make a solar cell assembly count as failed while a subgroup
is under test, and turning a set of those decisions into the subgroup's
own outcome.

## Domain quick reference

- The campaign tests subgroups, not single assemblies, and a subgroup
  carries an allowance for how many of its assemblies may fail. That
  allowance means nothing unless every assembly in the subgroup was
  judged by the same criteria, settled before anyone starts counting.
- An assembly fails when any one criterion is met. The criteria are not
  weighed against each other and they do not average: a defect ends the
  assembly whatever the electrical readings say, and a degradation past
  its limit ends it however clean the inspection was.
- The three electrical criteria are deliberately separate. Maximum
  power, short-circuit current and open-circuit voltage each carry
  their own limit, because a current loss points at the cell and the
  coverglass while a voltage loss points at a shunt or a cracked
  junction. One combined power limit hides whichever of them the test
  was run to find.
- Degradation is relative to that assembly's own pre-test reading, not
  to a family average or a datasheet value. The subgroup is a set of
  individuals and the test measures what the environment did to each.
- Insulation resistance to structure is a criterion in its own right.
  An assembly can hold all three electrical figures and still have lost
  the isolation the array design depends on.
- Observations are grouped, not scored. An observation is disqualifying,
  acceptable, or unrecognised -- and an unrecognised one stops the
  judgement instead of being quietly counted as acceptable, because the
  point of the criteria list is that nothing reaches the count
  undeclared.
- A degradation landing exactly on its limit is inside the limit. The
  comparison has to absorb representation error without moving the
  limit itself, or the same assembly passes on one machine and fails on
  another.

## Workflow

1. Validate the failure policy first: the three loss limits, the
   insulation floor and the subgroup allowance. A limit above one, or a
   fractional allowance, is refused rather than used.
2. For each assembly, compute the three relative losses from its own
   before and after readings. A missing block stops the judgement; an
   absent inspection is not a clean one.
3. Compare each loss against its own limit, and the insulation
   resistance against its floor, gathering every criterion met rather
   than stopping at the first.
4. Group the observations into disqualifying and acceptable, rejecting
   an unrecognised one, and add the defect criterion when anything
   disqualifying is present.
5. Close the assembly on one verdict -- accepted or failed -- carrying
   the full list of criteria met, so the subgroup count can be audited
   back to the reason each assembly is in it.
6. Count the failed assemblies across the subgroup, refusing a repeated
   assembly id rather than counting one article twice, and compare the
   count with the allowance. A count exactly at the allowance is inside
   it.
7. Close the subgroup on accepted or rejected, with a finding per
   failed assembly naming the criteria it met.

## Pitfalls

- Judging degradation against a family average. The criterion is what
  the test did to that assembly, and an assembly that started low can
  pass a family comparison while having lost more than the limit.
- Collapsing the three electrical criteria into one power limit. The
  current and the voltage terms point at different failure mechanisms,
  and the combined figure can sit inside its limit while one of them is
  far outside its own.
- Treating an unlisted observation as acceptable. Silence in the
  criteria list is not permission; an observation nobody declared is
  the one most likely to be the real failure.
- Counting an assembly twice. A repeated id in a subgroup record is
  usually a transcription error, and it moves the failed count in
  whichever direction the duplicate carries.
- Comparing a loss against its limit by bare arithmetic. The loss is a
  quotient of floats that can land a unit in the last place either side
  of a limit written as a round fraction, so the comparison absorbs
  that error while the limit is never relaxed.
- Reporting only the first criterion an assembly met. The repair, the
  failure analysis and the next subgroup all depend on which
  combination of criteria the article actually met.

## Behavior contract (gate 3)

The policy validation, relative loss computation, the three separate
electrical criteria, the insulation floor, observation grouping and
defect-criterion mapping, the per-assembly verdict, the duplicate-id
refusal and the subgroup allowance count are exercised by the gate 3
contract test: scripts/test_e2008_sca_failure_criteria.py against
scripts/e2008_sca_failure_criteria_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_sca_failure_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
