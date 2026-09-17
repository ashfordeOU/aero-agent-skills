---
name: q60-component-control-plan-drd
description: "Audit a component control plan against the content its ECSS-Q-ST-60C Annex A deliverable description requires. Use when a plan has been drafted or received and someone has to say whether it is submittable: sort every required section into its general, organization, controls or schedules group, credit each one from whether it is absent, outlined or written through, make every group clear its own floor rather than letting a strong group carry a weak one, hold the plan as a whole to a higher floor, fail a missing mandatory section outright, and check the committed milestones run in a sequence that can happen. Trigger: ecss, q-st-60c-annex-a-drd, component-control-plan-content, component-control-plan-group-floor, component-engineering-organization-section, declared-list-submission-milestone-order, component-control-plan-mandatory-section."
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
  tags: [ecss, q-st-60c-eee-component-scope, q60-component-control-plan-drd, q-st-60c-annex-a-drd, component-control-plan-content, component-control-plan-group-floor, component-engineering-organization-section, declared-list-submission-milestone-order, component-control-plan-mandatory-section]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Component Control Plan DRD (space-systems/ecss/q60-component-control-plan-drd)

Use when the task is the component control plan of ECSS-Q-ST-60C Annex A —
the deliverable that says who controls the components, what controls they
operate and when the commitments fall due, and whether a draft of it carries
enough of that to be submitted.

## Domain quick reference

- The deliverable has three jobs and a front matter. Who does it, what they
  do, and when it happens; a plan that answers two of those is not two thirds
  of a plan, it is a plan with a hole in it.
- That is why the audit is group-wise. A single weighted total lets twenty
  pages of procurement control cover a paragraph on who signs anything, and
  the weighted total is exactly the reassurance a reviewer wants least.
- Every group clears its own floor first, and the plan then clears a higher
  floor on top. Clearing every group by a hair is not a submittable plan
  either, which is what the second floor is for.
- Presence is not content. A section that outlines its intent earns half its
  weight and a section written through earns all of it, because a heading
  with a sentence under it is where these plans actually fail.
- Mandatory sections are not weights. Selection and approval, declared list
  management, procurement, incoming inspection, radiation assurance, pure tin
  control, nonconformance handling and the discharge controls fail the plan
  by their absence, whatever either floor reads.
- The schedules group carries an obligation the others do not. Its content
  can be complete and still be wrong, because the dates have to describe a
  sequence that can happen: the preliminary list before the selection freeze,
  the freeze before the long-lead release, the final list before delivery.
- An uncommitted milestone and a backwards pair are different defects. One is
  a gap in the commitment and the other is a commitment that cannot be met,
  and reporting them the same way loses the difference.

## Workflow

1. Validate the submission: document identifier, the sections the plan
   contains, and the milestones it commits to.
2. Normalize every submitted section against the required content, rejecting
   an unknown heading and a section submitted twice, and marking anything
   unsubmitted as absent.
3. Credit each section from its state and roll the credits up per group and
   across the plan as a whole.
4. List the mandatory sections that are absent; any entry on that list blocks
   submission on its own.
5. Validate the milestones, then collect the ones not committed and the pairs
   that run backwards along the required order.
6. Grade every group against its floor and the plan against the higher floor,
   both at the boundary under the named tolerance, and return the verdict
   with the findings and the actions that close them.

## Pitfalls

- Auditing on one total. It is the arithmetic that lets a plan with no
  organization section pass, and it is the reason the group floors exist.
- Counting headings. A contents page matching the required list says nothing
  about whether a section carries a procedure anyone could follow.
- Treating an outline as written. Half credit is deliberate: it keeps a draft
  visible as a draft instead of promoting it on the strength of its title.
- Scoring the schedules group and stopping. Three complete schedule sections
  with a long-lead release before the selection freeze is a complete
  description of something that cannot happen.
- Folding an uncommitted milestone into the section score. A milestone the
  plan never commits is not a weaker section, it is an absent commitment, and
  it is reported on its own.
- Returning floors with no actions. A group that fell short and a section
  that is missing each imply a specific next edit, and naming it is what
  makes the audit usable by the author.

## Behavior contract (gate 3)

The section catalogue and its groups, the state credits, duplicate and
unknown section rejection, absent-section defaulting, the per-group and
overall completeness rollups, the mandatory shortfall list, milestone
validation with duplicate, unknown and negative-day rejection, the
uncommitted and out-of-sequence milestone findings, the group and overall
floors judged at the boundary under a named tolerance and the verdict with
its findings and actions are exercised by the gate 3 contract test:
scripts/test_q60_component_control_plan_drd.py against
scripts/q60_component_control_plan_drd_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_component_control_plan_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
