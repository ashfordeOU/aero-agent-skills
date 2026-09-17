---
name: q6013-component-control-plan-drd
description: "Evaluate whether a component control plan for a commercial-parts programme carries the content its data item fixes under ECSS-Q-ST-60-13C Annex A. Use when a plan has been drafted for parts bought outside the space-qualified chain and a reviewer must say whether it is submittable: refuse a plan with no reference or issue, test each required section for a procedure standing behind the heading, confirm the selection, lot-acceptance, radiation and obsolescence sections each name a responsible function, read the issue age against its revision interval, and name the customer-agreement milestones the plan never reached. Trigger: ecss, q-st-60-13c-annex-a, commercial-part-component-control-plan-drd, commercial-parts-plan-section-coverage, commercial-parts-plan-issue-currency, commercial-parts-plan-approval-milestone, commercial-parts-plan-section-ownership."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-component-control-plan-drd, commercial-part-component-control-plan-drd, commercial-parts-plan-section-coverage, commercial-parts-plan-issue-currency, commercial-parts-plan-approval-milestone, commercial-parts-plan-section-ownership]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components — Component Control Plan DRD (space-systems/ecss/q6013-component-control-plan-drd)

Use when the task is the Annex A data item of ECSS-Q-ST-60-13C: a
component control plan has been written for a programme buying parts
from the commercial market, and the question is whether the document
contains what the data item requires, not whether the parts are good.

## Domain quick reference

- A data item is a contents contract. It fixes the sections the plan
  must carry so that a reviewer at another organisation can find the
  selection route, the procurement controls, the evaluation route, the
  screening and lot-acceptance rules, the radiation and environment
  assessment, the derating rules, the obsolescence and alert route and
  the traceability rules in a document they have never read before.
- A section drafted with no procedure behind it is not written. The
  contents page then matches the required list while every section
  defers its subject, so a blank procedure reference reads as an
  unwritten section and the covered share falls accordingly.
- A section nobody owns is not controlled. Commercial parts move fast:
  a substitution offer, a die-shrink notice or a lot rejection is
  answered by whoever is nearest unless the plan names the function that
  answers it, so the selection, lot-acceptance, radiation and
  obsolescence sections carry an owner or the plan states an intention
  rather than a route.
- Currency is a number, not a feeling. The issue age is read against the
  declared revision interval and reported as the share of that interval
  consumed, so a plan drifting out of date is visible before it passes
  the date. An issue landing exactly on its interval is still current,
  the comparison tolerance being there to absorb representation error
  rather than to extend the interval.
- Customer agreement is the point of the document. A plan never taken
  through the design reviews and the parts approval board that depend on
  it was written for the project's own comfort, so the milestones it
  never reached are named rather than counted.

## Workflow

1. Validate the data-item policy first: the minimum section coverage,
   the revision interval, the marginal band at the end of that interval
   inside which a current plan is still advised on, whether ownership
   and customer agreement are required, and the milestones the plan has
   to be taken through. A coverage floor above one, a non-positive
   interval, a full-width marginal band or an unrecognised milestone is
   refused rather than used.
2. Validate the plan identity: a non-blank plan reference, a non-blank
   issue label, a non-negative issue age and a boolean agreement
   declaration. An absent plan, or one with a blank reference or issue,
   closes the assessment on plan not submitted.
3. Validate every section record: a recognised section name, no
   duplicate section, a boolean drafted flag, and a procedure reference
   and responsible function that may each be blank but are then read as
   absent. Take the covered share over the required sections and name
   the absent and the unwritten ones in full.
4. Take the ownership finding over the sections that bear an owner only;
   a section the plan never declared is already an absence and is not
   counted twice.
5. Take the issue currency as the issue age over the revision interval,
   then raise the marginal advisory when a still-current issue sits in
   the last stretch of that interval.
6. Compare the completed milestones against the required ones and name
   what is outstanding.
7. Close on one verdict in order: plan not submitted, section coverage
   short, section ownership missing, plan not agreed by the customer,
   issue overdue, approval milestone outstanding, or plan satisfies the
   data item. Report the coverage, the currency, the absent, unwritten
   and unowned sections and the outstanding milestones alongside it.

## Pitfalls

- Reading the contents page as the coverage. A required section heading
  with no procedure behind it counts as unwritten, however carefully the
  heading is worded.
- Grading the parts instead of the document. The data item asks what the
  plan contains; whether a particular commercial part is acceptable is
  the parts approval document's question, not this one.
- Leaving the fast-moving sections unowned. Selection, lot acceptance,
  radiation and obsolescence are the four that get answered under time
  pressure, and an unnamed owner there is what turns a written plan into
  an unwritten habit.
- Widening the revision interval to make an exact-boundary issue pass.
  An issue landing on its interval is current by the tolerance inside
  the comparison; the declared interval stays as specified.
- Reporting a bare verdict. The coverage, the currency and the
  outstanding milestones are what the next issue is compared against,
  and the verdict word carries none of them.

## Behavior contract (gate 3)

The policy validation, plan identity validation, section validation and
coverage, the ownership finding, the issue currency and its overdue
test, the marginal advisory, the outstanding milestones and the plan
verdict are exercised by the gate 3 contract test:
scripts/test_q6013_component_control_plan_drd.py against
scripts/q6013_component_control_plan_drd_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_component_control_plan_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
