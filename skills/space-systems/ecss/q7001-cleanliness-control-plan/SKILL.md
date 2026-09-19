---
name: q7001-cleanliness-control-plan
description: "Produce and keep current the contamination and cleanliness control plan a project owes under ECSS-Q-ST-70-01C. Use when a CCCP has to be drafted, or an issued one has to be shown to still be the controlling document. Checks every content area points at a real section, that the plan speaks to each lifecycle phase from design through the launch campaign to operations, that a recognised authority approved it, that its issue postdates the last configuration change, that the periodic review is not overdue, and that each declared update event names both an action and an owner. Trigger: ecss, q-st-70-01, contamination-cleanliness-control-plan, cccp-content-completeness, cleanliness-plan-lifecycle-coverage, cleanliness-plan-approval-authority, cleanliness-plan-update-event, cleanliness-plan-periodic-review."
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
  tags: [ecss, q-st-70-cleanliness-scope, q7001-cleanliness-control-plan, contamination-cleanliness-control-plan, cccp-content-completeness, cleanliness-plan-lifecycle-coverage, cleanliness-plan-approval-authority, cleanliness-plan-update-event]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Control Plan (space-systems/ecss/q7001-cleanliness-control-plan)

Use when the task is the plan itself under the ECSS-Q-ST-70-01C
programme clause — producing the contamination and cleanliness control
plan, or deciding whether the issue on the shelf is still the document
the project is actually being run to.

## Domain quick reference

- The plan is the single place the cleanliness requirements, the way
  they will be met and the evidence that they were met are tied
  together. Anything the plan does not carry has no owner, because the
  plan is what the other disciplines are pointed at.
- A content area is only covered when it points at a section that
  exists. A heading in a table of contents with nothing under it reads
  as coverage in every review until the moment somebody needs what it
  promised.
- Coverage runs the whole lifecycle. A plan that ends at delivery
  leaves the launch campaign, where the hardware is handled most and
  controlled least, without a controlling document, and leaves in-orbit
  contamination behaviour undescribed when the operations team needs it.
- A plan without a recognised approval is a draft however complete it
  is. Approval by someone outside the project's approval authorities is
  the same defect wearing a signature, and an approval dated before the
  issue it approves is evidence the two were never connected.
- Currency is the part that lapses quietly. The plan was correct when
  it was issued; the design has moved since, and an issue predating the
  last configuration change describes hardware that no longer exists.
- Periodic review is separate from change-driven revision. A plan can
  be perfectly current against a design that has not moved and still be
  overdue a review that would have caught what the design did not
  change but the facilities did.
- An update event is only an obligation when it names an action and an
  owner. A list of circumstances under which the plan will be
  revisited, with nobody named, revisits nothing.

## Workflow

1. Validate the plan identity: title and issue label, and an issue date
   that parses as a calendar date.
2. Walk the required content areas and list the ones that point at no
   real section. Treat a named-but-empty section as absent.
3. Walk the lifecycle phases and list those the plan does not speak to.
4. Compute the completeness share over content areas and phases
   together, so the figure moves for either kind of gap.
5. Check the approval: an approver, an approver the project recognises
   where an authority list is given, an approval date, and an approval
   that does not predate its own issue.
6. Compare the issue date with the last configuration change the plan
   has to reflect; an issue older than the change is stale whatever
   else is in order.
7. Compute the periodic-review state as of the assessment date and
   report the days overdue rather than a bare flag.
8. Check each declared update event names an action and an owner, and
   list the required events that are not declared at all.
9. Report the gaps, the completeness, the review state and every
   finding; call the plan controlling only when nothing is outstanding.

## Pitfalls

- Grading the plan on its table of contents. Completeness measured on
  headings is the failure mode the empty-section check exists for.
- Writing the plan for the phases the writer owns. The launch campaign
  and early operations are usually written by nobody, which is where
  the hardware is most exposed.
- Treating issue and approval as one event. They are separately dated
  on purpose, and an approval predating its issue means the approver
  signed something else.
- Reading a current issue as a current plan. Nothing about the document
  changes when the design does, so currency has to be tested against
  the configuration, not against the shelf.
- Folding periodic review into change-driven revision. A stable design
  produces no revisions at all, and the plan quietly ages past the
  point where its facility and supplier assumptions still hold.
- Listing update events without owners. It reads as a maintenance
  process and behaves as a statement of intent.

## Behavior contract (gate 3)

The content-area and lifecycle-phase gap detection, the empty-section
rule, completeness share, approval and authority checks, issue-versus-
configuration currency, periodic-review overdue arithmetic and the
update-event obligations are exercised by the gate 3 contract test:
scripts/test_q7001_cleanliness_control_plan.py against
scripts/q7001_cleanliness_control_plan_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_cleanliness_control_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
