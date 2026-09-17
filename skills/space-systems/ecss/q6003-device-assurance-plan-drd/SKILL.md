---
name: q6003-device-assurance-plan-drd
description: "Assess whether a drafted product assurance plan for a device development carries the content its DRD demands before the plan is baselined. Use when the plan has to become an accept or rework verdict under ECSS-Q-ST-60-03C Annex A: refuse a section that is a heading with nothing behind it, confirm every assurance function the plan owes is owned by a role the organisation section actually declares, check each development milestone carries at least one planned activity whose owner resolves to a declared role, resolve every committed deliverable record to the milestone that issues it, and return the aggregate verdict naming every gap rather than the first. Trigger: ecss, q-st-60-03c-annex-a, device-assurance-plan-drd, device-assurance-plan-section-coverage, device-assurance-function-ownership, device-development-milestone-activity-coverage, device-assurance-deliverable-linkage."
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
  tags: [ecss, q-st-60-03-device-development-assurance-scope, q6003-device-assurance-plan-drd, device-assurance-plan-section-coverage, device-assurance-function-ownership, device-development-milestone-activity-coverage, device-assurance-deliverable-linkage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Development -- Product Assurance Plan DRD (space-systems/ecss/q6003-device-assurance-plan-drd)

Use when the task is the Annex A document requirements definition of
ECSS-Q-ST-60-03C: a product assurance plan for a device development has
been drafted, and the question is whether its content is what the DRD
asks for -- not whether the plan reads well, but whether every block,
owner, milestone activity and committed record is actually there.

## Domain quick reference

- A DRD is a content contract, not a template. The plan satisfies it
  when each required block carries a procedure a reviewer could follow,
  so a section key that exists with an empty body is a placeholder and
  counts as absent. Checking for the heading alone is the failure this
  leaf exists to prevent.
- The nine content blocks are the introduction, the applicable and
  reference documents, the organisation and its responsibilities, the
  development flow with its milestones, the design and verification
  assurance approach, part and material selection, nonconformance and
  alert handling, the reuse and heritage policy, and the deliverable
  items and records the development will issue.
- The organisation block is only complete when every assurance function
  the development needs -- design authority, product assurance,
  verification and validation, configuration management, procurement
  and supplier control, customer interface -- sits under a named role.
  A function discussed in prose but owned by nobody is a gap.
- Milestone coverage runs the other way from activity coverage. Every
  declared milestone must attract at least one planned activity, and
  every activity must attach to a milestone the plan declared. An
  activity pointing at an undeclared milestone is an input error rather
  than a finding, because it means the two lists were drafted apart.
- Activity ownership is checked against the role names the organisation
  block defines, not against free text. An owner that appears nowhere
  else is the way a renamed team quietly orphans half a plan.
- The deliverable list is a commitment with three distinct defects: a
  required record never committed at all, one committed at two
  milestones so that two issue points exist for one record, and one
  issued at a milestone the plan never declared.
- The plan is reworked once, so the verdict names every gap together. A
  check that stops at the first finding turns one review cycle into
  several.

## Workflow

1. Read the drafted plan as section key to body text and run
   missing_plan_sections; treat a blank body exactly as an absent key.
2. List the organisation block's roles with the functions each owns and
   run unowned_assurance_functions. Reject a function name outside the
   known set rather than ignoring it, because an ignored name reads as
   coverage.
3. Declare the development milestones once each and run
   milestones_without_activities against the planned activity list;
   a duplicate milestone or an activity on an undeclared milestone is
   refused as an input defect.
4. Run activities_with_unknown_owner against the roles from step 2 to
   catch activities orphaned by a renamed or deleted role.
5. Run dangling_deliverables to separate the missing, duplicated and
   undeclared-milestone defects in the committed record list.
6. Combine all five with assess_device_assurance_plan_drd; the plan is
   DRD-compliant only when the flat findings list is empty, otherwise
   the disposition is rework with every gap named.

## Pitfalls

- Accepting a section because the key is present. The DRD asks for
  content, and an empty body is the most common way a plan passes a
  shallow check and fails the review it was drafted for.
- Reading the organisation chart as function coverage. A role list
  proves people exist; it does not prove the customer interface or
  supplier control has an owner.
- Silently dropping an unrecognised function name. A typo then reads as
  a covered function, and the gap survives to the review board.
- Counting an activity attached to a milestone the plan never declared
  as milestone coverage. It is evidence the milestone list and the
  activity list were drafted from different baselines.
- Treating a deliverable committed twice as harmless redundancy. Two
  issue points for one record means the later one is the one nobody
  tracks.
- Stopping the check at the first finding. The plan goes back to its
  author once, so the verdict has to carry the whole list.

## Behavior contract (gate 3)

The section coverage, assurance-function ownership, milestone activity
coverage, activity owner resolution, deliverable linkage and the
aggregate plan verdict are exercised by the gate 3 contract test:
scripts/test_q6003_device_assurance_plan_drd.py against
scripts/q6003_device_assurance_plan_drd_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6003_device_assurance_plan_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
