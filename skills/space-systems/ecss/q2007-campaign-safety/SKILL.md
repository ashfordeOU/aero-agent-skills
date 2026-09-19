---
name: q2007-campaign-safety
description: "Manage the safety of a test campaign under ECSS-Q-ST-20-07C clause 5.9.4 from the declaration rather than from the booking date: decide per hazard family whether a declared item or operation reaches the threshold that makes it hazardous, reconcile the customer safety questionnaire against that hazard set in both directions so an unanswered topic and an undeclared item both surface, flag a hazardous entry placed outside a controlled area, and derive the safety inputs the test process design owes each confirmed family. Use when a campaign is being prepared for a test centre or a safety package is being contested. Trigger: ecss, q-st-20-07c, test-campaign-safety, hazardous-item-identification, customer-safety-questionnaire, hazardous-operation-design-input, campaign-safety-readiness."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-campaign-safety, test-campaign-hazard-identification, customer-safety-questionnaire-reconciliation, hazardous-operation-design-input, test-campaign-safety-readiness, hazard-family-threshold-grading]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres -- Safety of a Test Campaign (space-systems/ecss/q2007-campaign-safety)

Use when the task is the campaign safety step of ECSS-Q-ST-20-07C clause
5.9.4: a customer is bringing items and operations into a test centre and
the question is which of them are hazardous, whether the customer has said
so in the safety questionnaire, and what the test process design therefore
has to carry.

## Domain quick reference

- Hazard is a property of a family plus a level, not of a name. A lifting
  operation below the manual-handling limit and a lift of a flight model
  are the same family at two levels; a pressurised vessel below the
  stored-energy level is a fitting, above it is a hazardous item. Only
  the families whose harm does not scale with quantity -- pyrotechnics,
  propellant, toxic substances, radiation sources, cryogens -- are
  hazardous at any declared presence.
- The questionnaire and the declaration are two independent statements
  about the same campaign, so they have to be reconciled in both
  directions. A hazard with no answered topic is the obvious gap; a topic
  answered yes for a family nothing in the item list reaches is the one
  that gets missed, and it usually means the item arrives anyway.
- A yes with no supporting detail is not an answer. The detail is what
  the test process design consumes: quantity, form, the operation it is
  used in, who performs it. Without it the confirmation cannot be turned
  into a procedure or a hold point.
- Where a hazardous entry lives is part of the campaign, not facility
  housekeeping. A hazardous item held outside a controlled area changes
  who can walk past it, so it is a blocking constraint; a hazardous entry
  with no declared location is an open question and is raised as one.
- The output of the clause is an input to another process. Each confirmed
  family owes named design inputs -- a hazardous-operation procedure, a
  restricted access area, a dedicated authorisation, monitoring -- and
  those inputs are what the test process design is then built around.

## Workflow

1. Normalise the campaign declaration: identifier, hazard family, whether
   it is an item or an operation, the graded metric value, and the
   location. Reject a duplicate identifier, an unknown family, an
   unknown kind, or a non-positive value before anything is graded.
2. Grade each entry against its family threshold, inclusively, so a value
   sitting exactly on the level counts as reaching it.
3. Group the entries into the hazardous set and the below-threshold set,
   keeping the identifiers so a finding can name them.
4. Normalise the returned questionnaire and reconcile it against the
   hazard families: missing topic, contradicting answer, confirmation
   without detail, and confirmation with nothing declared.
5. Grade the location of every hazardous entry, blocking on an
   uncontrolled area and raising an advisory when none was declared.
6. Take the union of the design inputs owed by the confirmed families and
   return the decision: blocked, ready with safety actions, or ready.

## Pitfalls

- Reading a short hazard list as a safe campaign. The families are
  reconciled against the questionnaire before the count means anything;
  a short list with an unanswered topic is an incomplete declaration, not
  a light campaign.
- Treating a questionnaire yes with nothing behind it as coverage. The
  detail is the part the process design uses, so a bare confirmation
  leaves the design with nothing to act on.
- Grading only the declaration. The reverse direction -- a confirmed
  topic that no declared entry reaches -- is the one that puts an
  undeclared hazardous item on the loading dock.
- Clamping a value that sits exactly on a threshold to the safe side. The
  comparison is inclusive and the representation error is absorbed by a
  named tolerance, never by moving the threshold.
- Letting an undeclared location pass as a controlled one. Unknown is not
  inside; it is raised so somebody answers it before the campaign starts.

## Behavior contract (gate 3)

The declaration normalisation, the inclusive family-threshold grading,
the hazardous grouping, the two-way questionnaire reconciliation, the
location grading and the design-input union feeding the readiness
decision are exercised by the gate 3 contract test:
scripts/test_q2007_campaign_safety.py against
scripts/q2007_campaign_safety_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_campaign_safety.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
