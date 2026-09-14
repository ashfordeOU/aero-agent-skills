---
name: q6013-class-3-component-control-plan
description: "Assess whether a component control plan carries what the lowest assurance class still demands for commercial EEE parts under ECSS-Q-ST-60-13C clause 6.1.2.2: accept a plan issued as a section of a wider product-assurance document, refuse one naming neither carrier nor issue, treat a core subject named without a procedure behind it as untreated, compute core coverage and depth-weighted completeness, separate a tailorable subject dropped with a recorded reason from one dropped in silence, require customer agreement past a declared tailoring count, and check issue before the first procurement commitment. Use when a light plan has to become a coverage verdict. Trigger: ecss, q-st-60-13c-clause-6-1-2-2, class-three-component-control-plan, core-plan-subject-coverage, plan-tailoring-justification-record, unagreed-tailoring-cap, embedded-plan-host-document, shallow-core-subject-advisory."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-3-component-control-plan, class-three-component-control-plan, core-plan-subject-coverage, plan-tailoring-justification-record, unagreed-tailoring-cap, embedded-plan-host-document, shallow-core-subject-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Component Control Plan (space-systems/ecss/q6013-class-3-component-control-plan)

Use when the task is the clause 6.1.2.2 plan-scope question of
ECSS-Q-ST-60-13C at the lowest assurance class: a light component
control plan has been drafted for commercial EEE parts, and the question
is whether what it left out was left out on purpose.

## Domain quick reference

- At the lowest class the plan is allowed to be short. It is not allowed
  to be silent. The scope question is no longer whether every subject is
  treated, because most of them need not be; it is whether the subjects
  that are compulsory at any class are treated, and whether each subject
  the plan drops was dropped on the record.
- Five subjects stay compulsory whatever the class: part selection and
  approval, procurement source and authenticity, application and
  derating, traceability to lot and date code, and the route a failed
  part takes. They are what make a commercial part usable at all, so
  none of them is tailorable and none of them accepts a justification in
  place of a procedure.
- Four subjects are tailorable: evaluation and lot qualification,
  screening and lot acceptance, radiation and environment suitability,
  and the obsolescence and lifetime-buy plan. Dropping one is a
  legitimate lowest-class choice. Dropping one without saying why is the
  defect, because nobody reading the plan later can tell a decision from
  an omission.
- A subject never declared at all carries no justification by
  definition, and a subject declared shallow with no reason behind it is
  the same silence written at greater length. Both are read as a silent
  drop rather than as tailoring.
- The plan need not be a standalone document at this class. A section of
  a wider product-assurance plan is an acceptable carrier, so the
  identity check asks for a plan reference or a host document, and only
  refuses when there is neither.
- Tailoring has a volume at which it stops being tailoring. Past a
  declared count of justified omissions the plan is a different plan
  from the one the class describes, and the customer carries that
  residual risk, so the agreement is required rather than assumed.
- Coverage and depth stay two different numbers. The core coverage share
  answers how many compulsory subjects the plan treats properly; the
  depth-weighted completeness answers how thoroughly, over the full core
  denominator so that deleting a weak section cannot raise the score.
- Issue timing decides whether the plan controlled anything. A plan
  issued after the first procurement commitment documents choices
  already made, and a light class does not make that recoverable.

## Workflow

1. Validate the plan policy first: the depth floor a core subject must
   reach to count as treated, the marginal band inside which a treated
   core subject is still advised on, the count of justified omissions
   that may stand without customer agreement, and the issue-timing flag.
   A floor above one, a band wider than the floor, or a cap above the
   number of tailorable subjects is refused rather than used.
2. Validate the plan identity: a plan reference or a host document, a
   non-blank issue label, and boolean agreement and timing declarations.
   Neither carrier and no issue closes the assessment on plan not
   established.
3. Validate every declared subject record: a recognised subject name, no
   duplicate, a depth in the unit interval, and a procedure reference
   that may be blank but is then read as no procedure. A core subject
   carrying an omission justification is refused outright, because a
   core subject is not tailorable at any class.
4. Decide each core subject: treated when declared, at or above the
   depth floor, with a non-blank procedure reference behind it. Anything
   else is untreated and every untreated core subject is named, not just
   the first.
5. Group each tailorable subject as treated, dropped with a recorded
   reason, or dropped in silence. Undeclared and declared-bare both fall
   in the silent group.
6. Take the core coverage share and the depth-weighted completeness over
   the full core subject list, counting a missing or procedure-less
   subject as zero depth.
7. Report the carrier, the issue, both numbers, the untreated core
   subjects, the justified and silent drops, the weakest treated core
   subject and its depth, and an advisory for every core subject inside
   the marginal band. Close on one verdict: plan not established, core
   subject coverage short, tailoring not justified, tailoring not agreed
   with customer, plan issued after procurement, or plan adequate for
   the lowest class.

## Pitfalls

- Reading a short plan as a non-compliant plan. Shortness is the class
  working as intended; the finding is the unrecorded drop, not the page
  count.
- Accepting a justification against a core subject. Selection, source,
  derating, traceability and the disposition route are not tailorable,
  and a reason offered in place of a procedure there is refused rather
  than weighed.
- Counting an undeclared tailorable subject as tailored away. Silence is
  not a decision; the subject has to be named and its drop reasoned
  before it counts as tailoring.
- Averaging core depth only over the sections that exist. Deleting a
  weak section would then raise the score, which is exactly backwards;
  the denominator stays the full core list.
- Refusing a plan that lives inside a wider product-assurance document.
  At this class the host document is a legitimate carrier, and demanding
  a standalone issue invents a requirement the class does not carry.
- Reporting a bare pass. The core coverage, the completeness, the drop
  lists and the weakest core subject are what the next issue is compared
  against, and the verdict word carries none of them.

## Behavior contract (gate 3)

The policy validation, plan identity validation, subject validation, the
treated, untreated, justified-drop and silent-drop decisions, the core
coverage share, the depth-weighted completeness, the weakest core
subject, the tailoring-agreement cap, the issue-timing check, the
marginal advisories and the plan verdict are exercised by the gate 3
contract test:
scripts/test_q6013_class_3_component_control_plan.py against
scripts/q6013_class_3_component_control_plan_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_component_control_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
