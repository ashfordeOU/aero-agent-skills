---
name: q6005-hybrid-design-activity-flow
description: "Determine the order in which the engineering tasks of a hybrid microcircuit design must run, and how far the design has actually progressed, under ECSS-Q-ST-60-05 clause 7.1.2. Use when a hybrid design programme declares its activities, predecessors, durations and states and the question is whether the flow reaches an approved design solution: refuse a dependency cycle or a predecessor that was never declared, sequence the activities topologically, name the mandated stages the plan omits, list what may start now, expose a task signed off ahead of an open predecessor, and derive the earliest finish and the critical path. Trigger: ecss, q-st-60-05, hybrid-design-activity-flow, hybrid-design-predecessor-cycle, hybrid-design-stage-coverage, hybrid-design-critical-path, hybrid-design-out-of-order-signoff."
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
  tags: [ecss, q-st-60-05-hybrid-microcircuit-scope, q6005-hybrid-design-activity-flow, hybrid-design-predecessor-cycle, hybrid-design-stage-coverage, hybrid-design-critical-path, hybrid-design-out-of-order-signoff, hybrid-design-solution-approval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Microcircuits — Design Activity Flow (space-systems/ecss/q6005-hybrid-design-activity-flow)

Use when the task is the design-flow step of ECSS-Q-ST-60-05 clause 7.1.2 —
laying out the sequence of engineering tasks that carries a hybrid from a
concept to a design solution somebody signs, and judging whether a declared
plan can actually get there.

## Domain quick reference

- The flow is a dependency graph, not a list. Two tasks that both wait on the
  design-input review run in parallel; a Gantt bar drawn in reading order
  hides that and reports a longer programme than the work requires.
- The mandated stages are design-input review, preliminary design, materials
  and parts selection, detailed design, design analysis, design verification,
  and design review and approval. A plan may split a stage across several
  activities, but a stage no activity serves is a gap in the plan, not a
  scheduling choice.
- Materials and parts selection sits early and in parallel with preliminary
  design because a hybrid's die, substrate and attach materials drive the
  detailed design that follows. Deferring it behind detailed design is the
  most common way a hybrid programme discovers a non-procurable part late.
- A dependency cycle is not a slow plan; it is a plan with no runnable order
  at all, so it is refused rather than resolved by picking a starting point.
  A predecessor that was never declared is the same class of defect.
- Progress is two separate questions: what may start now (every predecessor
  complete) and what has been signed off ahead of its inputs. The second is
  the finding that matters, because a verification signed before the analysis
  it verifies is evidence about nothing.
- The critical path is the longest chain of earliest finishes, and it is the
  only chain whose slip moves the approval date. Compressing an off-path task
  buys no programme time at all.

## Workflow

1. Validate every declared activity: an identifier, one of the mandated
   stages, a non-negative duration, a state from the closed vocabulary, and
   a predecessor list that does not name itself or repeat an entry.
2. Build the flow, refusing a duplicate identifier and any predecessor that
   no declared activity provides.
3. Sequence the flow topologically, taking ready activities in identifier
   order so the reported sequence is reproducible; refuse a cycle and name
   the activities caught in it.
4. Compare the declared stages with the mandated set and report the gaps in
   the mandated order.
5. Report what may start now, and separately the pairs where a complete
   activity waits on a predecessor that is not complete.
6. Derive each activity's earliest finish from the latest of its inputs plus
   its own duration, then walk back from the latest finish along the driving
   predecessor to report the critical path and the programme duration.
7. Return the approval verdict: the design solution is approved only when
   every stage is covered, every activity is complete, no sign-off ran ahead
   of its inputs, and an approval activity closes the flow with nothing
   after it.

## Pitfalls

- Reading the activity list top to bottom as the schedule. The order in the
  file is an authoring artefact; the runnable order comes from the
  dependencies and is what the durations have to be applied to.
- Resolving a cycle by cutting whichever edge looks weakest. The cycle is a
  statement that the plan is wrong; cutting an edge silently invents a plan
  nobody reviewed.
- Treating an activity as ready because its stage is next in the mandated
  list. Readiness is a predecessor question, and two stages can be ready at
  once while a third later stage waits on both.
- Counting a signed-off activity as progress without checking its inputs. An
  out-of-order sign-off inflates the completion ratio and buries the fact
  that the evidence underneath it is not there.
- Compressing a task that is not on the critical path and reporting a saving.
  Only the driving chain moves the approval date.
- Letting a plan end on something other than the approval activity. An
  activity after the approval means the signed design solution is not the
  last word, which is itself the finding.

## Behavior contract (gate 3)

The activity validation, flow construction, cycle refusal, topological
sequencing, stage-coverage check, readiness and out-of-order sign-off
detection, earliest-finish and critical-path derivation and the approval
verdict are exercised by the gate 3 contract test:
scripts/test_q6005_hybrid_design_activity_flow.py against
scripts/q6005_hybrid_design_activity_flow_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_hybrid_design_activity_flow.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
