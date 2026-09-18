---
name: q1009-records-analysis
description: "Analyze the nonconformance records periodically as ECSS-Q-ST-10-09 clause 5.5.3 asks, and say what the result obliges the project to do. Use when a reporting milestone falls due and the records collected so far have to be turned into trends, recurring causes and indicators feeding product assurance reporting and corrective action: refuse a study never run or gone stale, normalise every period by the exposure it carries, take the least-squares slope over the normalised rates rather than the endpoints, group the causes and weigh the largest by share and by occurrence count, and decide between corrective action, a trend under watch and reporting with no action. Trigger: ecss, q-st-10-09-clause-5-5-3, nonconformance-trend-slope-analysis, nonconformance-recurring-cause-share, nonconformance-rate-indicator-alert, nonconformance-corrective-action-trigger."
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
  tags: [ecss, q-st-10-09-nonconformance-control-scope, q1009-records-analysis, q-st-10-09-clause-5-5-3, nonconformance-trend-slope-analysis, nonconformance-recurring-cause-share, nonconformance-rate-indicator-alert, nonconformance-corrective-action-trigger, nonconformance-exposure-normalised-rate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Periodic Records Analysis (space-systems/ecss/q1009-records-analysis)

Use when the task is clause 5.5.3 of ECSS-Q-ST-10-09: the nonconformance
records have accumulated, a periodic analysis of them falls due, and the
question is what the trends and the recurring causes in the set oblige
the project to do about them.

## Domain quick reference

- A count is not a rate. Ten nonconformances over a month of full
  production and ten over a single integration shift are not the same
  signal, so each period is normalised by the exposure it carries before
  it is compared with any other period.
- A trend is a slope, not a pair of endpoints. The least-squares slope
  over the normalised rates uses every period and does not swing on one
  noisy month, which is exactly what a first-to-last reading does.
- A recurring cause is a share, not a tally. The largest cause group
  matters when it takes a large part of the whole and has occurred often
  enough to be a pattern, so the share and the occurrence count both
  gate the corrective action call.
- Cause groups cannot account for more records than the periods counted.
  That disagreement is an input error rather than a finding, and records
  carrying no cause group at all are reported, because the recurrence
  picture is then drawn from part of the set.
- The analysis has to be current to be an analysis. A study last run
  further back than the analysis interval describes an earlier
  programme, and the clause is not discharged by reprinting it.
- Rising and actionable are different. A rate rising below the action
  indicator is reported and watched; the watch is the output of the
  clause in that case, not a softened refusal.

## Workflow

1. Validate the analysis policy first: the periods a trend needs, the
   analysis interval, the recurring-cause share and minimum occurrence
   count, the rate alert indicator, the action slope and the Pareto
   share. A one-period basis or a one-occurrence recurrence is refused
   rather than used.
2. Test whether the analysis is current against its interval; a stale or
   absent study closes the assessment on records not analysed.
3. Validate the periods: a label each, no period twice, whole
   non-negative counts and a positive exposure. Take the normalised rate
   for each and the mean and latest across them.
4. Check the cause groups against the records counted, and carry the
   ungrouped remainder as an advisory.
5. Take the least-squares slope of the normalised rate against the
   period index, and name its direction with a flat band around zero.
6. Group the causes, rank them, take the dominant share and the number
   of categories needed to reach the Pareto share.
7. Close on one verdict in order: records not analysed, analysis basis
   too short, corrective action required, trend under watch, or analysis
   reported with no action. Report the slope, the direction, the
   dominant cause and the indicator values alongside it.

## Pitfalls

- Comparing raw counts between periods of different size. The rate the
  programme is running at is the count over the exposure, and a count
  alone makes a busy month look like a quality collapse.
- Reading the trend off the first and last period. Two periods out of
  eight is not a trend, and the one noisy month is usually the one that
  made someone look.
- Calling every largest group a recurring cause. A category with two
  occurrences out of three records has a high share and no pattern
  behind it, which is why the occurrence count gates the call.
- Analysing the grouped records as though they were the whole set. The
  ungrouped remainder can be larger than the dominant group.
- Reporting a bare verdict. The slope, the dominant share and the alert
  comparison are what the corrective action proposal has to argue from.

## Behavior contract (gate 3)

The policy validation, period validation, exposure-normalised rates, the
least-squares slope and its direction, the cause grouping and ranking,
the dominant share, the Pareto count, the cause-consistency check, the
analysis currency and the action verdict are exercised by the gate 3
contract test: scripts/test_q1009_records_analysis.py against
scripts/q1009_records_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q1009_records_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
