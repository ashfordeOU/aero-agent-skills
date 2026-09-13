---
name: e2008-visual-inspection-general-criteria
description: "Validate the supplier-defined visual acceptance criteria for every component of a photovoltaic assembly under ECSS-E-ST-20-08C clause 5.5.3.2.3, then screen a coupon against them: check each criterion carries a positive limit, a unit consistent with its kind, an inspection method, a customer-agreement state and the document it was agreed in; report components left with no criteria at all; reduce the observed features to a largest single dimension, a cumulative area fraction and a count; and disposition each result as accepted, referred to the customer, or rejected. Use when an inspection outcome has to be defended against an agreed and documented criteria set. Trigger: ecss, e-st-20-08c, supplier-defined-acceptance-criteria, customer-agreed-inspection-criteria, photovoltaic-assembly-component-criteria, coverglass-edge-chip-limit, cumulative-defect-area-fraction, visual-criteria-document-reference."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-visual-inspection-general-criteria, supplier-defined-acceptance-criteria, customer-agreed-inspection-criteria, photovoltaic-assembly-component-criteria, coverglass-edge-chip-limit, cumulative-defect-area-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Visual Inspection General Criteria (space-systems/ecss/e2008-visual-inspection-general-criteria)

Use when the task is the acceptance-criteria rule of ECSS-E-ST-20-08C
clause 5.5.3.2.3 -- the limits the supplier writes for each component of
a photovoltaic assembly, the customer agreement that makes them binding,
and the document that lets the same coupon draw the same verdict a year
later.

## Domain quick reference

- The standard does not supply the numbers. The supplier writes them per
  component -- solar cell, coverglass, interconnect, adhesive fillet, bus
  bar, insulation film -- so the reviewable object is the criteria set
  itself, not any single limit inside it.
- Two jobs live here and they separate cleanly. Admissibility asks
  whether a set exists for every component, whether every criterion is
  agreed, and whether every agreed criterion names the document it was
  agreed in. Adjudication asks what a real observed feature comes out as
  against that set.
- Three criterion kinds cover what a visual examination can actually
  measure: a limit on one feature, a limit on the cumulative area those
  features occupy as a fraction of the assembly, and a limit on how many
  of them there may be. A coupon can sit comfortably inside the
  single-feature limit and still fail on the cumulative one, so all
  three are adjudicated and the highest utilisation names the governing
  criterion.
- The unit is part of the criterion, not decoration. A millimetre limit
  written as a fraction, or an area fraction above unity, is a
  transcription error that would otherwise pass silently into a
  disposition.
- An unagreed criterion is not a licence to reject. A feature inside a
  supplier-only limit is accepted while the agreement is open, and a
  feature outside one is referred to the customer rather than
  dispositioned by the supplier alone.
- A feature observed that no criterion covers is the most dangerous
  outcome of all, because there is nothing to compare it to. It is
  referred, never quietly accepted for want of a limit.

## Workflow

1. Validate every criterion: a known component, a known kind, a feature
   name, a positive limit, a unit matching the kind, an inspection
   method, a known agreement state, and a document reference wherever
   the criterion is agreed. Reject a whole-number count limit expressed
   as a fraction and an area fraction greater than unity.
2. Roll the criteria up into a set review: components covered, the
   components left with nothing, criteria not yet agreed, criteria with
   no document reference, and the coverage fraction. The set is
   admissible only when all four gaps are empty.
3. Validate each observation: a known component, a feature name, and a
   positive length and width, from which the major dimension and the
   feature area follow.
4. Reduce the matching observations for each criterion to the quantity
   it limits -- the largest measure, the summed area over the assembly
   area, or the plain count -- and treat an unseen feature as zero
   rather than as missing data.
5. Disposition each criterion by utilisation, absorbing representation
   error exactly on the limit with a named tolerance rather than by
   widening the limit. Accept inside an agreed limit, accept pending
   agreement inside an unagreed one, reject outside an agreed one, refer
   outside an unagreed one.
6. Report the worst disposition as the assembly verdict, name the
   governing criterion, and list any observed feature the agreed set
   never covered.

## Pitfalls

- Screening a coupon against a set that was never agreed. The numbers
  may be sensible and the verdict still has no standing; the
  admissibility review is what the customer signed, and it runs first.
- Judging on the single-feature limit alone. Many small chips can hold
  every individual measure inside its limit while the cumulative area
  fraction or the count is already exceeded.
- Accepting an observed feature because no limit exists for it. Absence
  of a criterion is a gap in the agreed set, not evidence of compliance;
  the feature is referred and the set is amended.
- Letting an area fraction be written as a percentage. A limit of two
  entered as 2 rather than 0.02 is a hundredfold relaxation that no
  downstream arithmetic can detect, which is why the kind fixes the unit
  and an above-unity fraction is refused outright.
- Asserting a strict inequality on a utilisation that is meant to sit
  exactly on the limit. A cumulative fraction is a sum of products
  divided by an area and can land a few units in the last place either
  side of one; compare with a tolerance and assert the disposition that
  follows.

## Behavior contract (gate 3)

The criterion validation, set-admissibility review, observation
reduction, utilisation adjudication and assembly verdict are exercised
by the gate 3 contract test:
scripts/test_e2008_visual_inspection_general_criteria.py against
scripts/e2008_visual_inspection_general_criteria_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_visual_inspection_general_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
