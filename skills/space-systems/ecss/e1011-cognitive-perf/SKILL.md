---
name: e1011-cognitive-perf
description: "Use when apply cognitive performance and fatigue reference data under
  ECSS-E-ST-10-11 §4.5.4 to assess crew task feasibility: categorize each fatigue
  source as task-induced, sleep-deprivation, or circadian; determine the
  fatigue-adjusted sustained-attention duration available; evaluate working memory
  loading against fatigue-reduced capacity; and verify that decision time available
  is sufficient for the option count at the crew member's fatigue level. Compute a
  per-domain risk rating (acceptable, marginal, unacceptable) and derive an aggregate
  crew cognitive risk. Flag any domain that breaches its threshold as a finding before
  task or crew assignment proceeds. Trigger: ecss, e-st-10-system-scope,
  cognitive-performance, fatigue, attention, working-memory, decision-making,
  crew-performance."
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
  tags: [ecss, e-st-10-system-scope, cognitive-performance, fatigue, attention, working-memory, decision-making, crew-performance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Cognitive Performance and Fatigue Assessment (space-systems/ecss/e1011-cognitive-perf)

Use when the task is to apply cognitive performance and fatigue reference
data from ECSS-E-ST-10-11 §4.5.4 to determine whether a crew member is
within safe cognitive limits for a given task -- evaluating sustained
attention duration, working memory loading, and decision-making time
against fatigue-adjusted thresholds, and producing a per-domain and
aggregate risk rating.

## Domain quick reference

- §4.5.4 provides reference data for three cognitive performance domains:
  sustained attention (the ability to maintain focus on a task for a
  continuous period), working memory (the number of information items that
  can be held and processed simultaneously), and decision-making (the time
  needed to evaluate and select among a set of options). Each domain has a
  baseline limit at zero fatigue; the limit degrades as fatigue level
  increases.
- Fatigue is sourced from one of three categories: acute task-induced load
  (cognitive effort accumulated during a work period), sleep deprivation
  (reduced total sleep time below the crew rest requirement), or circadian
  disruption (shift of the sleep-wake cycle by duty scheduling). The
  category does not change the per-domain threshold formula, but it does
  determine which scheduling or operational countermeasure applies and must
  be recorded to support root-cause traceability.
- Risk is rated per domain as acceptable (within adjusted limit), marginal
  (up to the marginal tolerance band beyond the adjusted limit), or
  unacceptable (beyond the marginal band). Aggregate crew cognitive risk is
  the worst rating across all assessed domains. A single unacceptable domain
  makes the overall assessment unacceptable regardless of other domain
  ratings.
- A missing fatigue level or an option count of zero is an incomplete input
  and must be rejected before the assessment proceeds; the tool does not
  default these to zero or best-case values.

## Workflow

1. Identify the fatigue level for the crew member being assessed (a value
   on the 0.0 to 1.0 scale, where 0.0 is fully rested and 1.0 is the
   maximum operationally permitted fatigue level). Reject any value outside
   this range before proceeding.
2. Categorize each fatigue source contributing to the crew member's fatigue
   as acute_task, sleep_deprivation, or circadian. Reject an unrecognized
   source type; record the category for scheduling countermeasure tracing.
3. For each cognitive domain being assessed, compute the fatigue-adjusted
   performance limit:
   - Attention: available duration decreases by a fixed amount per 0.1
     fatigue unit, with a floor at the minimum useful duration (below
     which the task is always unacceptable).
   - Working memory: available item capacity decreases by one item per 0.2
     fatigue unit, with a floor at the critical minimum capacity.
   - Decision-making: required time per option scales up linearly with
     fatigue; the total required time is option count times the
     fatigue-adjusted per-option time.
4. Rate each domain:
   - Acceptable: the task demand is at or below the adjusted limit.
   - Marginal: the task demand exceeds the adjusted limit but is within the
     marginal tolerance band (up to twice the adjusted limit for attention
     and memory; up to 133% of the required decision time).
   - Unacceptable: the task demand exceeds the marginal band.
5. Aggregate domain ratings to the worst per-crew-member risk level.
   Record all findings (domain, adjusted limit, demand, rating) for any
   domain rated marginal or unacceptable.
6. Report the aggregate risk and findings list; proceed with task assignment
   only when the aggregate risk is acceptable.

## Pitfalls

- Applying baseline limits without fatigue adjustment and reading "within
  limit" as acceptable -- the adjusted limit is the operative threshold; a
  rested-crew limit applied to a fatigued crew overstates capacity and
  understates risk.
- Treating a missing fatigue level as zero fatigue -- an unknown fatigue
  state is not the same as a rested state; it is an incomplete input that
  blocks the assessment.
- Collapsing marginal into unacceptable or acceptable -- the marginal band
  exists so the task can be redesigned (shorter duration, fewer items,
  longer decision window) rather than immediately rejected or silently
  accepted; flattening it loses the mitigation signal.
- Ignoring fatigue source category once the level is known -- the level
  drives the threshold, but the category determines the countermeasure
  (rest break for acute load, sleep opportunity for deprivation, schedule
  realignment for circadian disruption); dropping the category creates a
  finding with no actionable corrective path.
- Assessing only one domain for a multi-domain task -- a procedure that
  simultaneously requires sustained attention, high-item working memory,
  and rapid multi-option decisions must be assessed across all three
  domains; the aggregate risk covers the worst case.

## Behavior contract (gate 3)

The fatigue-source categorization, per-domain limit calculation, per-domain
risk rating, aggregate risk, and crew cognitive assessment logic is
exercised by the gate 3 contract test:
scripts/test_e1011_cognitive_perf.py against
scripts/e1011_cognitive_perf_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_cognitive_perf.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
