---
name: q80-software-product-quality-metrics
description: "Define and evaluate the software product quality objectives and metrication programme of ECSS-Q-ST-80C Rev.2 clause 7.1: hold a metric catalogue with ceilings and floors, set thresholds per criticality category with project overrides traced to their source, measure comment density and a cyclomatic complexity estimate from source text, grade a measurement set and per-module metrics for pass, fail and missing, and read software maturity from the problem-report trend. Use when quality targets are agreed or a metrics report is prepared for a review. Trigger: q80-metrication, software-quality-metrics, cyclomatic-complexity-threshold, comment-density, test-coverage-goals, software-maturity-trend."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.3.5.2
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.1.1
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.1.2
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.1.3
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.1.4
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.1.5
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.1.6
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.1.7
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.1.8
    items: [a]
    relation: implements
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-80c, q80-software-product-quality-metrics, q80-metrication, software-quality-metrics, cyclomatic-complexity-threshold, comment-density, test-coverage-goals, software-maturity-trend]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Software Product Quality Metrics (space-systems/ecss/q80-software-product-quality-metrics)

Use when the task is the product quality side of ECSS-Q-ST-80C Rev.2
(30 April 2025): the quality objectives in clause 7.1 (deriving them,
stating them as numbers, the activities that check them, the product and
basic metrics, their reporting, numerical accuracy and the analysis of
software maturity) together with the test coverage goals agreed per test
level under 6.3.5.

## Domain quick reference

- The standard asks for quality requirements stated as numbers and for a
  metrication programme that checks them. It does not fix the numbers. The
  thresholds come from the contract and the plan; the defaults in this
  skill are illustrative and every graded row says whether its threshold
  is a default or a project value.
- A metric has a direction. Complexity, nesting, function size and open
  nonconformances are ceilings; comment density and every coverage figure
  are floors. Grading both the same way is how a report shows 0.97
  decision coverage as a pass.
- A missing measurement is not a pass. A metric with a threshold and no
  value fails the set until it is measured.
- Coverage goals rise with category: full statement and decision coverage
  for A and B, modified condition and decision coverage for A, and a lower
  bar for C and D, all to be confirmed against what the customer agreed.
- Per-module grading finds the offenders a project average hides. One
  telecommand handler at complexity 30 is invisible in a mean of 6.
- Software maturity is read from the problem-report history: discovery
  falling over the last periods with a backlog that is not growing.
  Category D does not have to produce this analysis.

## Workflow

1. Derive the software quality requirements, security, safety and
   dependability ones among them, from the requirements set at system
   level, and write each as a number or a hard constraint (a ceiling, a
   floor, a limit) rather than an adjective.
2. For each quality requirement in the technical specification, name the
   assurance activity that will show the product meets it (a review, an
   analysis, a measured metric, a test) and who runs it.
3. Write the metrication programme from the project's quality model:
   the metrics to collect and keep, the tool or method that measures each,
   the target value traced to the quality requirement it serves, the
   analyses run on the data (descriptive statistics, trends such as the
   problem-report trend), how the results reach the developers and turn
   into corrective actions, and when collection, storage, analysis and
   reporting happen across the life cycle. Agree the thresholds per
   category and record every project override against its source.
4. Make sure the set holds the basic product metrics at least: code size,
   design and code complexity, fault density and failure intensity, test
   coverage and the number of failures.
5. Agree with the customer, from the software's criticality and its
   security sensitivity, the coverage goal for each test level (unit,
   integration, and validation against the technical specification and
   against the requirements baseline), and follow each with a coverage
   metric in the set.
6. Collect the measurements from the project's analysers; use the source
   text estimates here only to cross-check them.
7. Grade the measurement set: pass, fail with the margin, missing.
8. Grade per module and list the offenders and the worst module per
   metric.
9. Check that the numerical accuracy of the software has been estimated
   and that the estimate has been verified by analysis or test, for every
   product; look hardest where accuracy decides mission success (attitude
   control, science data). A metric set that passes says nothing about it.
10. Name who collects and analyses the software maturity data (failures,
    corrections, run durations) and by what means, then read the maturity
    trend from the problem-report history.
11. Write the metrics section of the assurance report as a draft, carrying
    the measured results and their analysis so the customer can see the
    quality reached.

## Obligations

| Item | Step |
|---|---|
| ECSS-Q-ST-80C Rev.2 6.3.5.2a | 5 |
| ECSS-Q-ST-80C Rev.2 7.1.1a | 1 |
| ECSS-Q-ST-80C Rev.2 7.1.2a | 1 |
| ECSS-Q-ST-80C Rev.2 7.1.3a | 2 |
| ECSS-Q-ST-80C Rev.2 7.1.4a | 3 |
| ECSS-Q-ST-80C Rev.2 7.1.5a | 4 |
| ECSS-Q-ST-80C Rev.2 7.1.6a | 11 |
| ECSS-Q-ST-80C Rev.2 7.1.7a | 9 |
| ECSS-Q-ST-80C Rev.2 7.1.8a | 10 |

## Pitfalls

- Presenting illustrative thresholds as the standard's. They are not; say
  where each number came from.
- Averaging complexity across the code base.
- Counting preprocessor lines as comments in a C project. Pass the comment
  markers of the language measured.
- Reporting a coverage figure without the test level it was measured at.
- Calling software mature because the backlog shrank while discovery is
  still rising.

## Stop gate: human sign-off required

The agent drafts; it does not decide. Stop and hand the draft to a named
human before any of these leave the working folder:

- The quality thresholds proposed to the customer, and any waiver of a
  failed metric.
- The metrics section of an assurance report or milestone report.
- Any statement that the software is mature enough for a review.

Mark every such output as a draft, list the open questions for the
reviewer, and end with the line: STOP: human sign-off required before
submission.

## Behavior contract (gate 3)

The metric catalogue and its directions, the per-category defaults and
traced overrides, the comment density and cyclomatic estimates from source
text, the pass, fail and missing grading with margins at the boundary, the
per-module offender list and the maturity trend are exercised by the gate 3
contract test: scripts/test_q80_software_product_quality_metrics.py against
scripts/q80_software_product_quality_metrics_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q80_software_product_quality_metrics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite ECSS-Q-ST-80C Rev.2
  (30 April 2025) as the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
