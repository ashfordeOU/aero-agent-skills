---
name: e1011-cognitive-ergo
description: "Use when assess cognitive ergonomics for a human-operated space system
  interface under ECSS-E-ST-10-11C §4.6.6: evaluate information presentation density
  and coding-dimension count per display element, determine workload band from a composite
  operator workload index, check simultaneous-task count against the cognitive capacity
  threshold, and verify that situation-awareness indicators at all three levels —
  perception, comprehension, and projection — are present. Trigger: ecss,
  e-st-10-system-scope, cognitive-ergonomics, information-presentation,
  workload-management, situation-awareness, hfe."
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
  tags: [ecss, e-st-10-system-scope, cognitive-ergonomics, information-presentation, workload-management, situation-awareness, hfe]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — Cognitive Ergonomics (space-systems/ecss/e1011-cognitive-ergo)

Use when the task is the cognitive ergonomics assessment of
ECSS-E-ST-10-11C §4.6.6 — evaluating information presentation quality,
workload band, and situation-awareness coverage for every human-operated
interface in the system under review.

## Domain quick reference

- §4.6.6 organises cognitive ergonomics around three areas: information
  presentation, workload management, and situation awareness (SA). Each
  area has distinct checkable criteria; a finding in any one area makes
  the interface non-compliant until resolved.
- Information presentation is governed by two density limits rooted in
  working-memory research. A single display view should carry no more
  than nine distinct information elements (Miller's Law upper bound,
  common knowledge); exceeding this forces the operator to chunking
  strategies that increase error risk. Each individual display element
  should use no more than three simultaneous coding dimensions drawn from
  the recognised set — color, shape, size, position, brightness, motion,
  text label, auditory code — because adding a fourth or more dimension
  degrades rather than improves discrimination.
- Workload is assessed as a composite index on a 0-to-10 scale
  (NASA-TLX-inspired, common knowledge). An index below 3.0 represents
  under-load, where the operator may miss infrequent critical events due
  to reduced vigilance. An index in [3.0, 7.0] is the optimal range for
  sustained error-free performance. An index above 7.0 is over-load,
  where commission errors and degraded monitoring become probable. In
  addition, the peak number of simultaneous cognitive tasks is checked
  independently against a four-task threshold (multiple-resource theory,
  common knowledge); exceeding the threshold is a workload risk even
  when the composite index is within bounds.
- Situation awareness is decomposed into three levels (Endsley model,
  common knowledge): Level 1 — perception of current element states
  (raw parameter values, alarms); Level 2 — comprehension of their
  combined meaning (status summaries, mode indicators); Level 3 —
  projection of future states (trend displays, predictive alerts). An
  interface that does not supply indicators supporting every level leaves
  the operator with an incomplete picture and is not SA-adequate.

## Workflow

1. Inventory every display view in the operator interface. For each
   view, count the distinct information elements and compare against the
   nine-element density limit; flag any view that exceeds it.
2. For each individual display element in each view, list the coding
   dimensions it uses. Flag any element that uses more than three
   coding dimensions; record the excess dimensions as the violation
   detail.
3. Obtain the composite workload index for the operational scenario
   (from a task-analysis study or human performance model) and determine
   the workload band: under-loaded (< 3.0), optimal ([3.0, 7.0]), or
   over-loaded (> 7.0). Under-load and over-load are both findings.
4. For the peak simultaneous-task scenario, count the number of
   concurrent cognitive tasks the operator must manage; flag the count
   if it exceeds four.
5. For each operator interface, verify that SA indicators are provided
   at all three levels: raw-state indicators for Level 1, interpreted
   status indicators for Level 2, and trend or predictive indicators for
   Level 3. Flag any SA level that has no supporting indicator.
6. Aggregate findings per interface. The interface is not cognitively
   ergonomic until every density violation, coding-dimension violation,
   workload finding, and SA-level gap is resolved or formally accepted
   with a design rationale.

## Pitfalls

- Treating an optimal composite workload index as a guarantee that
  no task-overload condition exists — the composite may mask a brief
  peak window where simultaneous tasks exceed four; the task-count
  check is independent and must be performed separately.
- Counting coding dimensions across elements in the same view as if
  they compound against a shared limit — the three-dimension rule
  applies per element, not per view; two elements each using three
  dimensions is not a violation.
- Assuming Level 1 SA indicators (raw parameter displays) alone
  satisfy the full SA requirement — Levels 2 and 3 require dedicated
  comprehension and projection support and will not emerge from raw
  data alone under time pressure.
- Treating under-load as a pass because no over-load was detected —
  sustained under-load degrades vigilance and is a distinct ergonomic
  risk that requires design attention (event pacing, alerting, workload
  shaping).

## Behavior contract (gate 3)

The workload categorization, simultaneous-task, coding-dimension,
information-density, SA-coverage, and aggregate review logic is
exercised by the gate 3 contract test:
scripts/test_e1011_cognitive_ergo.py against
scripts/e1011_cognitive_ergo_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_cognitive_ergo.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
