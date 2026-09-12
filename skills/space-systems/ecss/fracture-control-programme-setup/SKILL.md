---
name: fracture-control-programme-setup
description: "Use when define a fracture control programme for a space structure under ECSS-E-ST-32C clause 5.1: determine whether the programme applies by checking for catastrophic-hazard items, scope the programme to cover pressurised structures, rotating machinery, and fracture-critical components, assign responsibilities to the prime contractor and any sub-tier fracture control boards, and tailor programme requirements to the mission risk category. The workflow identifies every structure whose failure mode is catastrophic, confirms a fracture control board is chartered with documented authority, and verifies that tailoring decisions are approved and traceable to the project risk category. Trigger: ecss, e-st-32-structures-scope, fracture-control, fracture-critical, catastrophic-hazard, programme-setup, tailoring, fracture-control-board."
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
  tags: [ecss, e-st-32-structures-scope, fracture-control, fracture-critical, catastrophic-hazard, programme-setup, tailoring, fracture-control-board]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fracture Control Programme Setup (space-systems/ecss/fracture-control-programme-setup)

Use when the task is establishing or auditing the fracture control programme
under ECSS-E-ST-32C clause 5.1 -- determining whether the programme is
triggered, scoping which structural items fall under it, chartering the
fracture control board, and verifying that tailoring decisions are documented
and approved against the mission risk category.

## Domain quick reference

- A fracture control programme is mandatory whenever at least one structural
  item in the assembly has a catastrophic failure hazard category
  (i.e. failure would result in loss of crew, vehicle, or mission). Items with
  critical, marginal, or negligible hazard categories do not individually
  trigger the programme, though they may be included in scope by programme
  tailoring.
- The programme scope covers: pressure vessels and pressurised lines, rotating
  or moving machinery, primary structural members whose failure is catastrophic,
  and any other item the prime contractor designates fracture-critical via
  tailoring. Items are categorized as fracture-critical or non-fracture-critical
  before the programme scope is fixed.
- The prime contractor establishes a Fracture Control Board (FCB) with at
  minimum a chair, a structural lead, and a quality-assurance representative.
  Sub-tier suppliers with fracture-critical items must either convene their own
  FCB or delegate authority upward in writing. The FCB charter must document
  its authority, membership, and quorum rules.
- Tailoring adjusts programme depth to the mission risk category: higher-risk
  missions require more stringent inspection intervals, lower initial flaw size
  assumptions, and broader scope of fracture-critical item coverage. Tailoring
  decisions require documented rationale and approval by the project authority.

## Workflow

1. Inventory every structural item and assign each one a hazard category
   (CATASTROPHIC, CRITICAL, MARGINAL, or NEGLIGIBLE) based on the consequence
   of its first failure mode. Reject any item that does not carry a recognised
   hazard category before proceeding.
2. Check whether the programme is triggered: if any item is categorized as
   CATASTROPHIC, the fracture control programme is required. Record the
   triggering items explicitly. If no item is CATASTROPHIC, document that the
   programme is not required and stop.
3. Define the programme scope: categorize every item as fracture-critical (any
   item with a CATASTROPHIC hazard category, plus pressurised lines, rotating
   machinery, and any item the programme authority adds via tailoring) or
   non-fracture-critical. Non-fracture-critical items are excluded from the
   formal programme but must still be documented as reviewed.
4. Confirm the Fracture Control Board (FCB) charter exists and includes at
   minimum the chair, structural lead, and QA representative roles. Flag any
   missing mandatory role. Verify that sub-tier suppliers with fracture-critical
   items have either their own FCB or a documented upward delegation of FCB
   authority.
5. Check tailoring completeness: verify that the programme references the
   project's mission risk category, that any deviation from standard programme
   requirements carries a written rationale, and that tailoring decisions are
   approved by the project authority. Flag any undocumented or unapproved
   tailoring item.
6. Produce a programme-setup finding list: trigger status, scope boundary,
   FCB charter gaps, and tailoring gaps. The programme is considered fully
   set up when all finding lists are empty.

## Pitfalls

- Treating a CRITICAL hazard item as sufficient to trigger the programme --
  only CATASTROPHIC hazard items trigger the requirement; CRITICAL items do
  not by themselves mandate a fracture control programme, though they may be
  included by tailoring.
- Assuming the FCB charter is implicit because key people are named in the
  organigram -- the FCB charter must be a dedicated document with explicit
  authority, quorum, and role definitions, not inferred from the project
  organigram.
- Completing the trigger check and scope definition without confirming sub-tier
  coverage -- a supplier with a fracture-critical item that has neither its own
  FCB nor a written upward delegation is a programme gap even if the prime's
  FCB is fully chartered.
- Treating tailoring as approved because no formal objection was raised -- a
  tailoring decision without a written rationale and documented approval is not
  accepted by the standard, regardless of informal agreement.

## Behavior contract (gate 3)

The programme-trigger, item-categorization, FCB-charter, and tailoring-check
logic is exercised by the gate 3 contract test:
scripts/test_fracture_control_programme_setup.py against
scripts/fracture_control_programme_setup_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fracture_control_programme_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
