---
name: e1011-hcd-drd
description: "Use when validate the Human-Centred Design (HCD) process plan against the ECSS-E-ST-10-11C Annex A Document Requirements Definition (DRD): confirm every mandatory section is present (scope, context-of-use description, stakeholder inventory, HCD activity schedule, evaluation plan, HFE staffing, and requirements traceability), verify each HCD activity is linked to a project milestone and a responsible practitioner, confirm evaluation events are categorized as formative or summative with success criteria, and flag any missing HFE practitioner competency record or traceability gap before the plan is submitted for review. Trigger: ecss, e-st-10-11c, hcd, human-centred-design, hfe, human-factors, hcd-plan, drd, evaluation-plan."
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
  tags: [ecss, e-st-10-11c, hcd, human-centred-design, hfe, human-factors, hcd-plan, drd, evaluation-plan]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — HCD Process Plan DRD Validation (space-systems/ecss/e1011-hcd-drd)

Use when the task is to validate or generate the Human-Centred Design (HCD)
process plan required by ECSS-E-ST-10-11C Annex A (normative): checking that
the plan document satisfies the DRD's mandatory section list, that each HCD
activity is anchored to a project milestone, that evaluation events are
categorized as formative or summative, and that HFE practitioner competencies
are on record.

## Domain quick reference

- ECSS-E-ST-10-11C Annex A defines a normative DRD for the HCD Process Plan.
  The DRD specifies which sections and content elements must appear before the
  plan can be formally accepted at a project review. This leaf validates that
  structure without reproducing the standard's verbatim text.
- Mandatory sections are: scope (document title + applicable standard),
  context-of-use description (mission phases, crew roles, operational
  environment), stakeholder inventory (users and operators identified),
  HCD activity schedule (activities with milestone linkage and responsible
  practitioner), evaluation plan (formative and summative events with
  success criteria), HFE staffing (practitioners with documented competency),
  and requirements traceability (activity-to-requirement mappings).
- Formative evaluations give iterative design feedback during development;
  summative evaluations provide final acceptance verification. An evaluation
  event with neither type is a DRD non-conformance.
- The traceability section maps each HCD activity to at least one system- or
  HFE-level requirement identifier; a mapping without a requirement ID is a
  gap. The evaluation plan drives the acceptance evidence chain.

## Workflow

1. Confirm the plan document contains all seven mandatory sections. A missing
   section is a DRD non-conformance; record it with the section name before
   proceeding to content checks.
2. For each section present, verify the required fields are populated. Flag
   every absent field individually so the author can address them in one pass.
3. Walk the activity schedule: each activity entry must carry a project
   milestone reference and a named responsible HFE practitioner. Activities
   without either field are non-conformant.
4. Walk the evaluation plan: each event must carry a type of "formative" or
   "summative" and at least one success criterion. Events with an unrecognized
   type or empty success criteria are flagged.
5. Walk the HFE staffing list: each practitioner entry must include a
   documented competency statement. A practitioner record without a competency
   field is flagged.
6. Walk the traceability mappings: each entry must link an activity identifier
   to a requirement identifier. Mappings missing either ID are flagged.
7. Aggregate all findings; the plan is DRD-compliant only when every list is
   empty. Return the finding structure to guide the author's revision.

## Pitfalls

- Treating section presence as sufficient and skipping field-level checks —
  a section with a heading but no content fails the DRD just as badly as a
  missing section.
- Accepting an evaluation event typed as anything other than "formative" or
  "summative" — the DRD recognizes exactly these two categories; anything
  else is non-conformant and must be corrected, not carried as a note.
- Confusing HFE staffing with HR org charts — the DRD requires a competency
  statement (training, qualification, or role description), not merely a
  name and job title.
- Treating activities without milestone linkage as a minor editorial gap —
  the schedule is the primary evidence that HCD is integrated into the
  project lifecycle; unlinked activities cannot be verified at reviews.

## Behavior contract (gate 3)

The mandatory-section check, field completeness check, activity-milestone
linkage, evaluation-type validation, HFE staffing competency check, and
traceability-mapping completeness are exercised by the gate 3 contract test:
scripts/test_e1011_hcd_drd.py against scripts/e1011_hcd_drd_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1011_hcd_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
