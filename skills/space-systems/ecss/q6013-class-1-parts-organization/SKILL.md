---
name: q6013-class-1-parts-organization
description: "Use when a declared parts organization has to become an accountability verdict. Identify the single unit accountable for commercial EEE part control at the highest assurance class under ECSS-Q-ST-60-13C clause 4.1.2.1: refuse an organization carrying no contractual mandate, name the unit holding part-selection approval, check that every required accountability sits with exactly one unit, report unassigned and split duties rather than the first found, confirm independence from the design authority and a declared customer escalation route, and flag a thinly staffed accountable unit. Trigger: ecss, q-st-60-13c-clause-4-1-2-1, class-one-commercial-eee-parts-organization, parts-control-accountability-assignment, part-selection-approval-authority, parts-organization-design-authority-independence, commercial-parts-customer-escalation-route, parts-organization-competence-advisory."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-1-parts-organization, class-one-commercial-eee-parts-organization, parts-control-accountability-assignment, part-selection-approval-authority, parts-organization-design-authority-independence, commercial-parts-customer-escalation-route, parts-organization-competence-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 1 Parts Organization (space-systems/ecss/q6013-class-1-parts-organization)

Use when the task is the clause 4.1.2.1 organization question of
ECSS-Q-ST-60-13C at the highest assurance class: a project intends to
fly commercial EEE parts, and the first thing that has to exist is a
named unit that is accountable for controlling them.

## Domain quick reference

- The clause asks for an accountable unit, not a distributed good
  intention. A commercial part reaches a flight board through selection,
  a procurement source, an evaluation, a screening decision, an alert
  disposition and an obsolescence call, and the highest assurance class
  is the one where a single unit answers for all of them together.
- Accountability is singular per duty. A duty nobody holds is a gap, and
  a duty two units both hold is worse than a gap, because each will
  assume the other exercised it and neither record will show the
  decision. Both shapes are findings, and the second is the one that
  survives an audit unnoticed.
- The anchor duty is part-selection approval. Whoever may say yes to a
  commercial part entering the design is the unit this clause is
  identifying; the remaining duties follow that unit or are explicitly
  delegated from it, which is why zero holders and two holders are both
  refusals rather than degenerate cases.
- Independence from the design authority is structural, not personal. A
  parts unit reporting into the team whose schedule a refusal would slip
  is not able to refuse, and its competence and integrity are not the
  point being tested.
- A mandate that exists only in a presentation is not a mandate. The
  accountable unit has to be established in the contract chain, because
  the authority to stop a procurement has to survive a programme review
  that wants the part.
- The customer escalation route is part of the organization, not an
  afterthought. At the highest assurance class the customer carries the
  residual risk of a commercial part, so a route that reaches them has
  to be declared before the first disagreement rather than invented
  during one.
- Competence is measured and reported, never assumed from the unit name.
  A correctly drawn organization staffed below the declared competence
  floor clears the structure question and fails in practice, and that
  difference is only visible if the number is carried with the verdict.

## Workflow

1. Validate the organization policy first: the minimum accountability
   coverage the class demands, the competence floor in staffed years,
   and whether a customer escalation route is required. A coverage
   floor above one, or a non-positive competence floor, is refused
   rather than used.
2. Validate every declared unit: a non-blank identifier, no duplicate
   identifier, a finite non-negative competence figure, and an
   accountability list drawn only from the recognised duty names. An
   unrecognised duty name is a transcription defect, not a new duty.
3. Establish the organization exists at all: an absent organization, an
   empty unit list, or a unit set carrying no contractual mandate closes
   the assessment on organization not established.
4. Name the accountable unit from the anchor duty, part-selection
   approval. Zero holders closes the assessment; two or more holders is
   a split-accountability finding.
5. Build the duty assignment across all units and take the coverage as
   the share of required duties held by exactly one unit. Name every
   unassigned duty and every split duty, not the first one found, and
   compare the coverage against the policy floor with a tolerance that
   absorbs representation error.
6. Check the accountable unit is independent of the design authority
   and that the declared customer escalation route is non-blank when
   the policy requires one.
7. Report the accountable unit, the coverage, the gaps, the splits and
   the competence figure, raising an advisory for an accountable unit
   staffed inside the marginal band above the floor. Close on one
   verdict: organization not established, accountability not singular,
   accountable unit not independent, escalation route not declared, or
   organization meets class one.

## Pitfalls

- Reading a project organigram as an answer. A box on a chart is not an
  accountability; the duty list is what this clause identifies, and a
  chart with no duty mapping leaves every duty unassigned.
- Treating a shared duty as double cover. Two units holding part
  selection means two units may approve a part and neither owns the
  refusal, so the split is reported as a finding rather than as
  redundancy.
- Accepting a parts unit inside the design authority because the people
  are experienced. The test is structural: the unit has to be able to
  stop a part the design team wants, and a reporting line that makes
  that career-costly fails the clause whatever the staffing.
- Deferring the customer escalation route until a disagreement. The
  route is declared with the organization; invented mid-dispute, it
  becomes another thing to agree while the procurement clock runs.
- Reporting coverage as a bare pass. A coverage figure and a competence
  figure beside the verdict are what the next review compares against,
  and neither can be recovered later from the word alone.

## Behavior contract (gate 3)

The policy validation, unit validation, mandate and existence checks,
anchor-duty identification, duty assignment with gaps and splits, the
coverage against its floor, the independence and escalation checks, the
competence advisory and the organization verdict are exercised by the
gate 3 contract test:
scripts/test_q6013_class_1_parts_organization.py against
scripts/q6013_class_1_parts_organization_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_parts_organization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
