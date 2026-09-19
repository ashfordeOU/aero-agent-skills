---
name: q2007-hazards-questionnaire
description: "Generate and grade the customer questionnaire on hazardous items and activities required by ECSS-Q-ST-20-07C Annex A: build the form from the DRD skeleton, adding the detail sections the declared hazard families pull in, then grade the returned response question by question -- an affirmed checklist entry owes its supporting attachment, an affirmed activity whose underlying item is denied is a contradiction inside one response, and the authorisation block must be signed and attributed to a role that can commit the customer. Use when a test centre is issuing or accepting this questionnaire. Trigger: ecss, q-st-20-07c, hazardous-items-questionnaire, annex-a-questionnaire-drd, questionnaire-attachment-check, questionnaire-authorisation-role, questionnaire-completeness-fraction."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-hazards-questionnaire, hazardous-items-questionnaire-drd, questionnaire-section-generation, questionnaire-attachment-completeness, questionnaire-authorisation-signature, questionnaire-internal-consistency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres -- Hazardous Items Questionnaire (space-systems/ecss/q2007-hazards-questionnaire)

Use when the task is the Annex A questionnaire of ECSS-Q-ST-20-07C: the
test centre has to issue a form covering the hazardous items a customer
brings and the hazardous activities performed on them, and then decide
whether what came back can be used as a safety input or has to go back.

## Domain quick reference

- The form is not fixed. Identification, the item checklist, the activity
  checklist and the authorisation block are always issued; the detail
  sections are pulled in by the hazard families the campaign profile
  already declares, so a campaign with no laser is never asked for a beam
  containment arrangement and a campaign with one always is.
- Two declared families can share one detail section. Propellant, toxic
  substances and cryogens all resolve to the substance block, and issuing
  it three times is a different form, not a more thorough one, so the
  section set is a union taken in DRD order.
- A checklist answer of yes is a claim with a document behind it. A
  pressure vessel owes its certificate, a substance owes its safety data
  sheet, a radiation source owes its licence. An affirmation with no
  attachment reads as answered in a completeness count while leaving the
  test process design nothing to work from.
- A questionnaire can contradict itself. An affirmed propellant loading
  operation with the propellant item denied is not two answers to be
  reconciled later against the declaration; it is one response that
  cannot be true, and it is caught inside the form.
- Signature and attribution are separate checks. An unsigned form commits
  nobody, and a signature from somebody who cannot commit the customer
  commits nobody either, so the role is graded against the set that can.

## Workflow

1. Validate the campaign profile -- customer, project, campaign, facility
   -- and refuse an unknown hazard family before a form is built.
2. Take the union of the base sections, the authorisation block and the
   detail sections the declared families trigger, ordered by the DRD.
3. Emit the question set for those sections, each carrying its kind, its
   mandatory flag and the attachment an affirmative answer owes.
4. Normalise the returned response against that form, refusing an answer
   to a question the form does not carry, a duplicate answer, and an
   unrecognised checklist token.
5. Grade each question: unanswered, answered, or affirmed with the
   supporting attachment missing.
6. Grade the internal consistency pairs and the authorisation block.
7. Report the completeness fraction over the mandatory questions and
   decide: accepted, or returned to the customer with the reasons named.

## Pitfalls

- Issuing the full catalogue to every customer. Sections nothing triggers
  get answered not-applicable in bulk, which trains the reader to skim
  the ones that matter.
- Counting an affirmation with no attachment as a complete answer. The
  attachment is the content; without it the completeness fraction is
  measuring how many boxes were ticked.
- Deferring the activity-versus-item contradiction to the campaign safety
  reconciliation. It is visible inside the single response and is cheaper
  to fix while the customer still has the form open.
- Accepting a signature without checking who signed. A form signed by
  somebody outside the recognised roles records that the customer has not
  answered yet.
- Treating a blank text box as an answer. An empty string is unanswered,
  and grading it as answered hides exactly the questions that were hard.

## Behavior contract (gate 3)

The profile validation, the triggered-section union, the question
emission, the response normalisation, the per-question grading with the
attachment rule, the internal consistency pairs, the authorisation checks
and the completeness fraction driving the issue decision are exercised by
the gate 3 contract test:
scripts/test_q2007_hazards_questionnaire.py against
scripts/q2007_hazards_questionnaire_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2007_hazards_questionnaire.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
