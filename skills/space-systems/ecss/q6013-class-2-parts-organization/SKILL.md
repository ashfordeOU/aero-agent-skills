---
name: q6013-class-2-parts-organization
description: "Use when a declared parts function has to become a coverage verdict. Determine which organizational function controls commercial EEE parts at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.1.2.1: refuse a function carrying no contractual mandate, name the unit holding part-selection approval directly, treat that duty as one that cannot be lent, accept a supporting unit only where its delegation is recorded, report every unassigned, contested and unrecorded duty rather than the first found, weigh a delegated duty at a declared credit below one, and require a product assurance escalation route where the function sits inside the design authority. Trigger: ecss, q-st-60-13c-clause-5-1-2-1, class-two-commercial-eee-parts-function, parts-duty-delegation-record, part-selection-approval-non-delegable, parts-function-design-authority-embedding, product-assurance-escalation-route-declaration, delegated-duty-coverage-credit."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-parts-organization, class-two-commercial-eee-parts-function, parts-duty-delegation-record, part-selection-approval-non-delegable, parts-function-design-authority-embedding, product-assurance-escalation-route-declaration, delegated-duty-coverage-credit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Parts Organization (space-systems/ecss/q6013-class-2-parts-organization)

Use when the task is the clause 5.1.2.1 organization question of
ECSS-Q-ST-60-13C at the intermediate assurance class: a project intends
to fly commercial EEE parts, and the first thing that has to exist is a
named function that controls them.

## Domain quick reference

- The intermediate class is not the highest class with its numbers
  relaxed. It is a different shape of answer, and the difference is
  delegation: a supporting unit may exercise a duty on behalf of the
  named function, which the class above does not permit, and the whole
  assessment turns on whether that delegation was written down.
- An unrecorded delegation is worse than a gap. A gap is visible and
  gets assigned; a duty exercised under a delegation nobody recorded
  reads as covered on every chart and cannot be shown to be held by
  anyone when the alert arrives.
- Part-selection approval is the duty that does not travel. Whoever may
  say yes to a commercial part entering the design is the function this
  clause names, so a programme lending that duty out has named no
  function, and two units holding it directly have named two.
- Two coverage figures are carried rather than one. The plain coverage
  says how many duties are disposed at all; the credited coverage weighs
  a delegated duty below one, so a function run entirely through others
  reads differently from one run directly, and the difference shows
  before it matters.
- Embedding is tolerated here and it is priced. A parts function
  reporting inside the design authority is acceptable at this class
  where a product assurance escalation route is declared, because the
  route is what lets a refusal survive the schedule pressure that the
  reporting line applies. With no route, the embedding is a finding.
- A mandate that exists only in a presentation is not a mandate. The
  function has to be established in the contract chain, because the
  authority to stop a procurement has to survive a programme review that
  wants the part.
- Competence is measured and reported, never assumed from the unit name.
  A correctly drawn function staffed at the edge of its floor clears the
  structure question and fails in practice, and that difference is only
  visible if the number travels with the verdict.

## Workflow

1. Validate the organization policy first: the plain and credited
   coverage floors, the credit a delegated duty earns, the competence
   floor in staffed years and its marginal band. A credited floor above
   the plain floor, a credit of zero, or a band wider than the floor is
   refused rather than used.
2. Validate every declared unit: a non-blank identifier, no duplicate
   identifier, duty names drawn only from the recognised list, no duty
   held directly and under delegation at once, a recorded delegation
   that actually lends something, and a finite non-negative competence
   figure.
3. Establish the function exists at all: an absent organization, an
   empty unit list, or a unit set carrying no contractual mandate closes
   the assessment on function not established.
4. Dispose each required duty as held directly, held by a recorded
   delegation, contested between units, or unassigned. A duty lent
   without a recorded delegation is unassigned and is reported
   separately by unit and duty.
5. Read the non-delegable duty first. Nobody holding it closes the
   assessment; two direct holders is a contested accountability; a
   holder under delegation closes on the anchor duty having been lent.
6. Take the plain coverage over the required duties and the credited
   coverage with the delegated credit applied, name every gap and every
   contested duty rather than the first, and compare both figures
   against their floors with a tolerance that absorbs representation
   error.
7. Check the named function against the design authority, requiring a
   non-blank product assurance escalation route when it is embedded and
   the policy asks for one. Report both coverages, the gaps, the
   contested and unrecorded duties, the competence figure and the
   marginal advisories. Close on one verdict: function not established,
   part-selection approval lent, accountability contested, duty coverage
   short, escalation route not declared, or organization meets class
   two.

## Pitfalls

- Reading a delegation off an organigram. A box with an arrow is not a
  recorded delegation; the record is what the clause accepts, and
  without it the duty is unassigned however confidently it is drawn.
- Averaging the plain coverage alone. A function that lends out five of
  its six duties reaches full plain coverage and is a different
  organization from one that holds them, which is exactly what the
  credited figure exists to show.
- Lending part-selection approval because the supporting unit is more
  expert. The clause is naming the function that answers for the part in
  the design, and expertise is bought through the delegation of the
  other duties, not this one.
- Accepting an embedded function because the people are experienced.
  The test is structural: with no escalation route the unit cannot
  afford to refuse a part its own management wants, whatever its
  staffing.
- Reporting coverage as a bare pass. The two coverage figures and the
  competence figure beside the verdict are what the next review compares
  against, and none of them can be recovered later from the word alone.

## Behavior contract (gate 3)

The policy validation, unit validation, mandate and existence checks,
the duty disposition including recorded and unrecorded delegation, the
non-delegable duty reading, the plain and credited coverages against
their floors, the embedding and escalation route checks, the competence
advisories and the organization verdict are exercised by the gate 3
contract test:
scripts/test_q6013_class_2_parts_organization.py against
scripts/q6013_class_2_parts_organization_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_parts_organization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
