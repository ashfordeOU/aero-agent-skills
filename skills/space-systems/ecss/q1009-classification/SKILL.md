---
name: q1009-classification
description: "Determine whether a raised nonconformance is minor or major under ECSS-Q-ST-10-09 clause 5.2.2.2, and whether several minor ones on a single item have quietly become a major. Use when departures have to be sorted before the review board sits, because the category decides which board may dispose of them. Answers every clause 3.2 severity criterion explicitly and treats the set as a disjunction, so one true answer is major and is never traded against the false ones; then groups the minor departures by the item they sit on and sums the margin they consume, escalating the whole group once the allocated margin is gone or the permitted count is passed. Trigger: ecss, q-st-10-09, nonconformance-severity-category, minor-versus-major-nonconformance, clause-3-2-severity-criteria, cumulative-minor-nonconformance-assessment, per-item-margin-consumption, nonconformance-group-escalation."
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
  tags: [ecss, q-st-10-09-nonconformance-control-scope, q1009-classification, nonconformance-severity-category, minor-versus-major-nonconformance, cumulative-minor-nonconformance-assessment, per-item-margin-consumption, nonconformance-group-escalation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Severity Categorization (space-systems/ecss/q1009-classification)

Use when the task is the categorization step of ECSS-Q-ST-10-09 clause
5.2.2.2 — deciding whether a raised departure is minor or major against
the clause 3.2 criteria, and whether an item carrying several minor
departures has to be re-presented as a major one.

## Domain quick reference

- The category is not a severity opinion, it is a routing decision. A
  minor departure can be disposed of by the supplier's own board; a
  major one cannot be disposed of at all until the customer's board has
  seen it. Getting the category wrong therefore does not soften a
  judgement, it sends the departure to the wrong authority.
- The clause 3.2 criteria are a disjunction, not a score. Safety,
  reliability or lifetime, interchangeability, performance outside the
  specified limits, interfaces, a budget allocation exceeded, the
  validity of qualification, a higher-level or contractual requirement,
  operational use — any single one answered yes makes the departure
  major. Eight comfortable answers do not offset the ninth.
- Every criterion is answered explicitly. An unanswered criterion is not
  a no; it is an incomplete assessment, and it is refused rather than
  defaulted, because the missing answer is usually the one that would
  have changed the category.
- Minor departures accumulate on the item, not on the paperwork. Three
  separate minor mass overruns on one bracket are three minor reports
  and one item that has eaten its mass margin, so the group is summed
  against the margin the item was allocated. Reaching that margin
  escalates — an item with exactly nothing left has no margin for the
  next departure.
- A count limit sits alongside the margin limit. An item carrying more
  open minor departures than the programme permits is a workmanship
  finding in its own right, whichever budgets they each consume.
- A group that already holds a major departure is major on that
  departure. It is not an escalation, and reporting it as one hides
  which criterion actually drove the category.

## Workflow

1. Validate each raised departure: an identifier, the item it sits on,
   an explicit true or false against every clause 3.2 criterion, and the
   share of the item's allocated margin it consumes. A missing criterion
   answer, a non-boolean answer or a share outside zero to one is an
   input error.
2. Categorize each departure on its own: any criterion true makes it
   major and the triggering criteria are named in reporting order;
   nothing true makes it minor.
3. Group the departures by item, preserving first-seen item order so the
   report matches the raising sequence. A duplicated report identifier
   is an input error.
4. Sum the margin consumed by the minor departures of each group. A
   major departure's consumption stays out of that sum — it is already
   being handled at the higher authority and would double-count.
5. Compare the group against both limits: the allocated margin, absorbing
   representation error at an exactly-consumed margin with a named
   tolerance, and the permitted open-minor count. Either limit reached
   escalates the group and the reason is named.
6. Report the per-departure categories, the per-item cumulative verdicts
   and the escalated items, so each item is re-presented to the board
   that can actually dispose of it.

## Pitfalls

- Treating the criteria as a weighted judgement. One safety answer is
  the whole decision; averaging it against the criteria that came back
  clean is how a safety-affecting departure gets disposed of internally.
- Defaulting an unanswered criterion to no. The interface question is
  the one most often skipped and most often the one that would have made
  the departure major.
- Assessing each minor departure in isolation. Five departures of a
  fifth of the margin each are individually unremarkable and together
  leave the item with nothing, which is the case the grouping exists to
  catch.
- Grouping by report rather than by item. The margin belongs to the
  item, so a group keyed on anything else sums departures that never
  competed for the same budget.
- Reporting a group that already contains a major departure as an
  escalation. It was major from the start, and the label hides the
  criterion that made it so.
- Widening the allocated margin to keep a group minor. The limit is the
  allocation; an exact-equality case is a representation question,
  handled by the tolerance inside the comparison.

## Behavior contract (gate 3)

The record validation, the per-criterion answers, the disjunctive
categorization, the grouping by item, the cumulative margin sum, both
escalation limits and the overall verdict are exercised by the gate 3
contract test: scripts/test_q1009_classification.py against
scripts/q1009_classification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q1009_classification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
