---
name: q6005-hybrid-procurement-activity-sequence
description: "Determine the order the procurement activities for a hybrid microcircuit run in and where the chosen manufacturer joins that order. Use when a hybrid buy is being planned, or an executed step list is being audited, against ECSS-Q-ST-60-05 clause 4: fix the entry point from the manufacturer category, drop the line evaluation and line approval activities for a maker whose production line already carries an approval, keep them for a maker whose line does not, report an activity run before its prerequisite or run at all on a route that does not own it, and name the outstanding activities and the next one due. Refuses an unknown or repeated activity name. Trigger: ecss, q-st-60-05-clause-4, hybrid-microcircuit-procurement-sequence, hybrid-procurement-entry-point, approved-line-manufacturer-entry, hybrid-line-evaluation-step-order, hybrid-procurement-step-prerequisite, outstanding-hybrid-procurement-activity."
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
  tags: [ecss, q-st-60-eee-scope, q6005-hybrid-procurement-activity-sequence, hybrid-microcircuit-procurement-sequence, hybrid-procurement-entry-point, approved-line-manufacturer-entry, hybrid-line-evaluation-step-order, hybrid-procurement-step-prerequisite]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Microcircuits — Procurement Activity Sequence (space-systems/ecss/q6005-hybrid-procurement-activity-sequence)

Use when the task is the clause 4 activity ordering of ECSS-Q-ST-60-05 — a
hybrid microcircuit is being procured and the question is which activities
the buy owes, in what order they run, and which of them the chosen
manufacturer is entitled to start past because the production line it will
build on already carries an approval.

## Domain quick reference

- The procurement of a hybrid is a chain, not a checklist. The requirement
  definition comes before the manufacturer is chosen, the manufacturer is
  chosen before anything is said about the line, the specification is agreed
  before a part type is qualified, and a lot is only accepted after it has
  been tested. An activity carried out before the activity it depends on has
  not been carried out early — it has been carried out on an input that did
  not exist yet.
- The two manufacturer categories do not run different chains; they join the
  same chain at different points. A maker with an approved production line
  joins at the specification agreement. A maker without one joins two
  activities earlier, at the line evaluation, and its approval has to be in
  hand before the specification step is reachable at all.
- The line evaluation and line approval activities are therefore not optional
  extras on the shorter route. They are absent from it. Running them anyway
  for an already-approved line is a finding about the plan, not extra rigour:
  it means the category was read wrong somewhere upstream, and the same
  misreading usually shows up in what the purchase order cites.
- Progress against the chain is measured against the route the category
  actually owes, not against the longest route. The same two completed
  activities leave an approved-line buy further along than a buy that still
  has a line evaluation and a line approval in front of it, and a progress
  figure computed against the wrong denominator under-reports one and
  over-reports the other.
- A claimed milestone is a claim about everything behind it. Saying the buy
  has reached part-type qualification asserts that every activity up to and
  including it is complete, so the milestone is graded by walking back down
  the route rather than by looking at the milestone activity alone.

## Workflow

1. Normalise the manufacturer category. Two categories exist; a supplier
   label such as preferred or long-standing is not one of them and is an
   input error, not a third route.
2. Derive the ordered activity set the category owes, and the set it does
   not: the line evaluation and line approval belong to the non-approved
   route only.
3. Read the entry point off that set — the activity the category joins at
   once the manufacturer has been selected — and state it explicitly, so the
   plan can be checked against it rather than against a remembered chain.
4. Canonicalise the executed activity list. An unknown name or a name
   recorded twice is an error in the record; resolve it before grading,
   because both distort every ordering answer downstream.
5. Grade the list. An activity outside the category's set is a
   not-applicable finding. An activity whose prerequisite is missing, or
   whose prerequisite is recorded as having run after it, is an ordering
   finding naming both activities.
6. Report the outstanding activities in route order, the next one due, and
   the completed fraction of the category's own route.
7. When a milestone is claimed, walk the route back from it and list every
   activity up to it that is still outstanding.

## Pitfalls

- Treating the approved-line route as the full route with two activities
  marked not-applicable. They are not in that route, so a progress figure
  that still counts them in the denominator is wrong on both routes.
- Grading the executed list as a set. The order the activities were recorded
  in carries the finding: a prerequisite that is present but recorded after
  its dependant is exactly the defect the clause ordering exists to catch,
  and a set comparison cannot see it.
- Accepting a claimed milestone because the milestone activity itself is
  recorded. The claim covers everything behind it, and the outstanding
  activity is usually several steps back, not the one being claimed.
- Letting a supplier's history stand in for the category. The category is
  decided by whether the specific production line carries an approval, and a
  buy that assumes the shorter route without that being established has
  skipped two activities rather than earned the right to skip them.
- Silently repairing a duplicated activity in the record. A duplicate means
  two different people recorded the same work, or one activity was run twice;
  either way the record is the finding and collapsing it hides it.

## Behavior contract (gate 3)

The category normalisation, route derivation, entry-point selection,
prerequisite construction, executed-list validation, ordering and
not-applicable findings, milestone walk-back and progress reporting are
exercised by the gate 3 contract test:
scripts/test_q6005_hybrid_procurement_activity_sequence.py against
scripts/q6005_hybrid_procurement_activity_sequence_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_hybrid_procurement_activity_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
