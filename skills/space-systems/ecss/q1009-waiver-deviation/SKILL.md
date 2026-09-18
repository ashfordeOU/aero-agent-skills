---
name: q1009-waiver-deviation
description: "Prepare and route a deviation or waiver request against an agreed requirement under ECSS-Q-ST-10-09C clause 5.2.3.5 and the M-ST-40 configuration rules. Use when a departure has to be authorised before build or accepted after the fact, when the request package is short of fields, or when affected items risk being used before approval: derive deviation against waiver from whether the departure already exists, complete the configuration record and its impact headings, route the signature to the customer or the supplier board, and permit use only inside the authorised effectivity and calendar life. Trigger: ecss, q-st-10-09c, deviation-request, waiver-request, m-st-40-configuration-record, customer-ccb-routing, authorised-effectivity, use-before-approval, departure-justification."
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
  tags: [ecss, q-st-10-09c-nonconformance-scope, q1009-waiver-deviation, deviation-request, waiver-request, m-st-40-configuration-record, customer-ccb-routing, authorised-effectivity, use-before-approval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Deviation and Waiver Requests (space-systems/ecss/q1009-waiver-deviation)

Use when the task is the deviation-and-waiver step of ECSS-Q-ST-10-09C
clause 5.2.3.5 — turning a proposed or existing departure from an
agreed requirement into a configuration record that somebody with the
authority to do so has approved, before the affected items are used.

## Domain quick reference

- One fact separates the two request types: whether the departure has
  already been incurred. Asked before the item is built or the activity
  is performed, the request is a deviation and authorises the departure
  in advance. Asked once the departure exists, it is a waiver and asks
  for acceptance of what is already there. The words are not
  interchangeable, because the configuration record they produce has
  different standing.
- Both are configuration management records under the M-ST-40 branch,
  so both name a configuration item, the requirement departed from, the
  departure itself, a justification, the items covered, and how long
  the authorisation lasts — one-off, a limited effectivity, or
  permanent.
- The impact assessment is a set of headings, not a free paragraph.
  Safety, reliability, interfaces, lifetime and verification each get an
  answer; an unanswered heading is a missing field, not a silent no.
- Routing follows the impact and the baseline. A requirement that sits
  in the customer-approved baseline, or a departure that reaches safety
  or an interface, is the customer board's to approve. Everything else
  stays with the supplier's own board.
- Approval is not open-ended. It covers a stated number of units and,
  where one is given, an expiry date; once either is spent the
  authorisation no longer covers the next item and a fresh request is
  owed.
- Using an affected item before the request is approved is not a
  paperwork lag. It is a departure with no authorisation behind it, so
  it is raised as a nonconformance in its own right.

## Workflow

1. Establish whether the departure already exists and name the request
   accordingly; do not let a late deviation stand in for a waiver.
2. Assemble the configuration record: request identifier the register
   can hold, configuration item, requirement identifier, description of
   the departure, justification, the items it covers, and the duration.
3. Answer every impact heading explicitly and carry the affected areas
   forward; an incomplete assessment stops the request before it
   reaches anyone's signature.
4. Route the approval. Baseline requirements and safety or interface
   impacts go to the customer board; the rest stay with the supplier
   board, and the reason for the routing is recorded with it.
5. Check the state of the request against the use of the items. Draft
   and submitted requests authorise nothing, and items already used
   under one are escalated as a separate nonconformance.
6. For an approved request, take the authorised unit count and the
   expiry date against the date of the decision and report what is
   left; release only while both remain.
7. Report the type, the missing fields, the routing, the remaining
   authorisation and the findings, so the change is traceable from the
   requirement to the delivered item.

## Pitfalls

- Filing a waiver as a deviation because the request form was started
  before the part was cut. The test is the departure, not the
  paperwork, and a mislabelled record overstates how much control the
  programme had at the time.
- Approving a request whose effectivity is a phrase rather than a list.
  "The affected units" covers everything and nothing; the record names
  the items, and a later unit needs its own coverage.
- Treating an expiry date as advisory. An approval that has run out
  authorises nothing, and the next item built under it is a fresh
  departure.
- Letting the supplier board sign a departure from a customer baseline
  requirement. That is the one routing rule the clause does not leave
  to judgement, and it is the one most often taken as an internal
  matter.
- Answering the impact headings with silence. An unanswered safety
  heading reads as a no to every later reader, and nothing in the
  record shows that nobody looked.
- Using the hardware while approval is pending and regularising it
  afterwards. The use is the nonconformance; approving the request
  later does not remove it from the record.

## Behavior contract (gate 3)

The request-type derivation, field and impact completeness, approval
routing, authorisation arithmetic and the use-before-approval verdict
are exercised by the gate 3 contract test:
scripts/test_q1009_waiver_deviation.py against
scripts/q1009_waiver_deviation_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q1009_waiver_deviation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
