---
name: e20-rf-power-and-intermodulation-verification
description: "Use when evaluate the verification provisions that close out radio-frequency power-handling and intermodulation requirements under ECSS-E-ST-20C clause 7.5: check that each provision carries an admissible verification-method, that a similarity claim is backed by a heritage reference and a bounded design-delta, that the demonstrated level covers the nominal carrier-level plus the qualification-margin required for that method, that every item is allocated to a review-gate and closed by the time that gate is held, and that a verification-plan and a verification-report reference exist before the gate is declared passed. Trigger: ecss, e-st-20-electrical-scope, rf-power-handling, intermodulation-verification, verification-method-admissibility, review-gate-closure, qualification-margin-demonstration, verification-plan-and-report, heritage-similarity."
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
  tags: [ecss, e-st-20-electrical-scope, e20-rf-power-and-intermodulation-verification, rf-power-handling, intermodulation-verification, review-gate-closure, qualification-margin-demonstration, heritage-similarity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS RF Systems — Power-Handling and Intermodulation Verification (space-systems/ecss/e20-rf-power-and-intermodulation-verification)

Use when the task is the verification close-out of ECSS-E-ST-20C
clause 7.5 -- deciding which verification-method is admissible for each
radio-frequency power-handling or intermodulation provision, what
qualification-margin that method has to demonstrate, which review-gate
it closes at, and what documentation has to exist before that gate is
declared passed.

## Domain quick reference

- Four provision families sit under this clause, and they do not share
  the same admissible methods. Multipactor and radio-frequency
  power-handling accept demonstration by hardware campaign, by
  analysis, or by similarity to flown hardware. Corona accepts a
  campaign or analysis but not similarity, because the ascent pressure
  profile is mission-specific. Passive-intermodulation accepts a
  campaign or similarity but never analysis alone -- the generating
  mechanism sits in surface and contact detail that no model predicts.
- The method and the required qualification-margin move together. A
  method that observes the hardware directly carries the smaller
  required margin; a method that infers behaviour (analysis, or
  similarity to another build) carries the larger one, because the
  uncertainty it leaves open has to be bought back in margin. Reading
  a margin without the method that earned it is meaningless.
- A similarity claim is only admissible with two things on record: the
  heritage item it leans on, and the design-delta against that item.
  A delta beyond minor invalidates the claim and pushes the provision
  back to a direct demonstration.
- Every provision is allocated to a review-gate -- the design reviews
  come first for the provisions that constrain the layout, the
  qualification and acceptance reviews for the ones that need
  hardware. Once the programme has reached that gate, an item without
  evidence is overdue, not merely open.
- Documentation closes the loop: a verification-plan reference for
  every item, and a verification-report reference for every item that
  claims evidence. A claimed result without a report reference is an
  assertion, not a verification.

## Workflow

1. Normalise each provision item: identifier, provision family,
   declared verification-method, nominal carrier-level, demonstrated
   level when evidence exists, allocated review-gate, plan and report
   references, and the heritage fields when the method is similarity.
   Reject an unknown family, an unknown method, an unknown gate or a
   non-finite level.
2. Check admissibility: the declared method must appear in the
   admissible set of that provision family. An inadmissible pairing is
   a finding that no amount of margin repairs.
3. For a similarity claim, require a non-empty heritage reference and
   a design-delta of none or minor; anything larger is a finding.
4. Look up the qualification-margin required for the family and method
   pairing (or take the item's own required margin when the project
   has set a stricter one), compute the demonstrated margin as the
   demonstrated level minus the nominal carrier-level, and compare.
   Treat an exactly-met margin as met -- the difference of two levels
   can land a fraction of a unit in the last place below the
   requirement without anything being non-compliant.
5. Compare the allocated review-gate against the gate the programme
   has reached: evidence present is closed; no evidence with the gate
   still ahead is open; no evidence with the gate reached or passed is
   overdue.
6. Check documentation: a plan reference on every item, a report
   reference on every item claiming evidence.
7. Aggregate: the clause is satisfied for the gate under examination
   only when no item is inadmissible, short of margin, overdue, or
   missing a document reference. Report the closure fraction so the
   trend between gates is visible.

## Pitfalls

- Accepting analysis for passive-intermodulation because a model
  produced a number. The clause admits a direct campaign or a
  similarity claim; a predicted intermodulation level is an input to
  design, not verification evidence.
- Carrying the smaller qualification-margin over to an analysis-only
  or similarity-based provision. The margin is attached to the method,
  and swapping the method without re-deriving the margin silently
  drops the uncertainty allowance.
- Letting a similarity claim ride on a heritage item with a major
  design-delta. The delta is the whole question; without it recorded,
  the claim cannot be judged at all.
- Marking an item open when its review-gate has already been held.
  Open and overdue carry different recovery actions, and collapsing
  them hides the schedule breach.
- Declaring the gate passed on results that no report references.
  Evidence that is not documented cannot be re-examined at the next
  gate, and the clause requires both the plan and the report.

## Behavior contract (gate 3)

The method-admissibility, similarity-evidence, qualification-margin,
review-gate closure and documentation logic is exercised by the gate 3
contract test:
scripts/test_e20_rf_power_and_intermodulation_verification.py against
scripts/e20_rf_power_and_intermodulation_verification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_rf_power_and_intermodulation_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
