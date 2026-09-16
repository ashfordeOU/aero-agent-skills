---
name: e2008-sca-testing-overview
description: "Use when an SCA test matrix, campaign plan or coupon allocation has to be assessed. Plan the solar cell assembly test programme of clause 6.1.1 of ECSS-E-ST-20-08C, where acceptance and qualification activities run as one campaign: hold each declared activity to the category it owes, check the specimen it runs on against that category, size the sample against the policy minimum, measure programme coverage and the qualification share, and return one programme verdict. Trigger: ecss, e-st-20-08c, sca-testing-overview, solar-cell-assembly-test-programme, sca-acceptance-and-qualification-coverage, sca-qualification-coupon-allocation, sca-test-activity-categorization, sca-programme-sample-size."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-testing-overview, e-st-20-08c, sca-testing-overview, solar-cell-assembly-test-programme, sca-acceptance-and-qualification-coverage, sca-qualification-coupon-allocation, sca-test-activity-categorization, sca-programme-sample-size]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Testing Overview (space-systems/ecss/e2008-sca-testing-overview)

Use when the task is clause 6.1.1 of ECSS-E-ST-20-08C: qualifying a solar
cell assembly is one programme in which acceptance and qualification
activities run together, several of them serving both ends at once. This
leaf grades a declared test matrix on coverage, on the article each
activity runs on, and on how many articles it runs on.

## Domain quick reference

- The programme is combined, not sequential. Some activities discharge
  an acceptance obligation, some a qualification obligation, and some
  discharge both in a single run. Reading the matrix as two separate
  campaigns is what produces a plan that looks full and covers half of
  what it owes.
- An activity owed to both ends is not covered by running it for one of
  them. A visual inspection declared as acceptance only leaves the
  qualification obligation open even though the activity is present in
  the matrix and has a result sheet against it.
- The article matters as much as the activity. An acceptance obligation
  is discharged on a sample of the flight lot, because it is the
  delivered hardware that has to be shown good; a qualification
  obligation is discharged on a qualification coupon, because the test
  may be destructive. An activity owed to both needs both articles.
- The three arms are ranked, not merged. A category shortfall is
  reported ahead of a specimen mismatch, and a specimen mismatch ahead
  of a thin sample, because fixing the sample size of an activity that
  is running on the wrong article is wasted effort.
- Sample minimums follow the category, not the activity. A
  qualification obligation carries the larger minimum, so the same
  activity declared at a wider category inherits the larger sample.
- The rollup carries two numbers. Coverage says how much of the owed
  activity set is actually discharged; the qualification-bearing share
  says whether what is covered is a combined campaign at all. A matrix
  can be fully covered and still be an acceptance sweep with a
  qualification title, and only the second number catches it.
- Doing more than is owed is accepted by default and refused under a
  strict policy. Both are legitimate project positions, so the
  behaviour is read from policy rather than assumed.

## Workflow

1. Read each declared activity with its category, the specimens it runs
   on, and its sample count. Reject an activity the required set does
   not name rather than silently carrying it.
2. Resolve the category: expand both the owed and the declared category
   into the obligations they discharge, and report any obligation the
   declaration leaves uncovered.
3. Check the specimens against the declared category, listing the
   article that is missing and, separately, any article the activity
   does not owe.
4. Size the sample against the minimum the declared category carries.
5. Rank the three arms into one activity verdict: category shortfall
   first, then specimen mismatch, then sample shortfall.
6. Roll the programme up: name the activities nobody declared, group
   the rest by verdict, report the coverage share and the
   qualification-bearing share, and return a verdict that is clean only
   when nothing is open and the campaign is genuinely combined.

## Pitfalls

- Counting an activity as covered because it appears in the matrix. The
  obligation it owes, not its presence, is what decides coverage.
- Discharging an acceptance obligation on a qualification coupon. The
  coupon is not the delivered hardware, so the result says nothing
  about the lot that ships.
- Running a qualification activity on flight lot samples. Where the
  activity is destructive or life-consuming, that spends flight
  hardware to produce evidence a coupon was supposed to carry.
- Merging the three arms into one pass or fail. An activity on the
  wrong article with a thin sample is one root cause and one fix; a
  merged verdict sends the plan back for the wrong correction.
- Reporting coverage alone. A programme that covers only the activities
  it finds convenient can still read as fully covered against a
  truncated matrix, which is why the qualification-bearing share is
  reported beside it.
- Judging a programme share that lands exactly on its policy limit by
  bare arithmetic. The share is a ratio of two counts and the limit is
  a round fraction, so a programme meant to sit on the limit can land a
  few units in the last place below it; the comparison absorbs that
  while the limit stays as declared.

## Behavior contract (gate 3)

The required activity set, the category expansion, the specimen
suitability test, the sample minimum, the ranked activity verdict and
the rolled-up coverage and qualification-bearing shares are exercised by
the gate 3 contract test:
scripts/test_e2008_sca_testing_overview.py against
scripts/e2008_sca_testing_overview_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2008_sca_testing_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
