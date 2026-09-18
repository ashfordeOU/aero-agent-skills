---
name: q6005-hybrid-technology-identification-form
description: "Determine whether a hybrid procurement case has the technology identification form it needs and what that form must cover before supplier assessment can begin, under ECSS-Q-ST-60-05C clause 6.2. Use when a hybrid is being procured, the supplier has declared its construction technologies, and the assessment team needs to know which form sections are owed, which assessment activities the form unlocks, and which stay blocked. Maps each declared technology onto the assessment areas it feeds, reports the areas left uncovered, derives the sealing category, refuses an unknown technology or an empty declaration, and returns a readiness verdict. Trigger: ecss, q-st-60-05, hybrid-technology-identification-form, hybrid-supplier-assessment-readiness, declared-construction-technology, identification-form-section-coverage, assessment-activity-enablement, hybrid-sealing-category."
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
  tags: [ecss, q-st-60-hybrid-procurement-scope, q6005-hybrid-technology-identification-form, hybrid-technology-identification-form, hybrid-supplier-assessment-readiness, declared-construction-technology, identification-form-section-coverage, assessment-activity-enablement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Procurement — Technology Identification Form (space-systems/ecss/q6005-hybrid-technology-identification-form)

Use when the task is the purpose-and-application step of ECSS-Q-ST-60-05C
clause 6.2 — establishing why a hybrid supplier owes a technology
identification form at all, what the form has to carry for the hybrid
actually being procured, and which parts of the supplier assessment it
releases.

## Domain quick reference

- The form exists so that the supplier's declared construction and the
  evidence needed to judge it arrive together, before anybody travels.
  It is an assessment input, not a deliverable that follows assessment;
  a case with no form is not a case with a weak form, it is a case the
  assessment cannot be planned against at all.
- What the form owes is driven by the hybrid, not by a fixed template.
  Each declared construction technology pulls in the assessment areas it
  obliges an assessor to form an opinion on, and only the sections
  carrying those areas are owed. A thick-film substrate brings resistor
  trim with it; a co-fired ceramic substrate does not. An adhesive die
  attach brings outgassing and materials with it; a eutectic attach does
  not.
- Coverage is judged per assessment area, not per section count. A
  submission can carry most of its sections and still leave an area with
  no evidence behind it, because one section can be the only carrier of
  an area that a single declared technology made relevant.
- Activity enablement is the useful output. An activity is released only
  when every area it depends on that is relevant to this hybrid is
  covered. An activity whose areas are all irrelevant here is not
  applicable, which is a different answer from enabled and must not be
  reported as a pass.
- The packaging declaration decides the sealing category, and that
  category steers whole branches of the later assessment. A declaration
  naming both a hermetic and a polymer seal is contradictory
  construction data, not a dual option, and is refused rather than
  resolved by preference.

## Workflow

1. Validate the declared technology set against the closed construction
   vocabulary; an unrecognised technology or an empty declaration is an
   input error, not a sparse case to be worked around.
2. Group the declaration by construction step and report any step with
   no declared technology, so a declaration missing a whole stage of the
   build is visible before coverage is counted.
3. Expand the declaration into the relevant assessment areas, then into
   the form sections those areas make owed.
4. Compare the submitted sections with the owed ones and list both the
   absent sections and, separately, the assessment areas left with no
   evidence.
5. Derive the sealing category from the declared packaging, refusing a
   contradictory hermetic-plus-polymer declaration.
6. Grade every supplier-assessment activity as enabled, blocked or not
   applicable against the relevant-and-covered area sets.
7. Return the readiness verdict together with the covered-area
   percentage and an ordered findings list; a case with no submitted
   form gets its own state rather than a zero score.

## Pitfalls

- Treating the form as paperwork that follows the audit. It is the input
  that makes the audit plannable; collecting it afterwards means the
  assessment was scoped against an undeclared construction.
- Grading coverage by counting sections. Sections are unequal carriers —
  losing the one section that evidences a singly-sourced area blocks an
  activity that a high section count would have called ready.
- Reporting a not-applicable activity as enabled. Both look like an
  absence of blockage, but only one of them means an assessor actually
  has evidence in hand.
- Applying a fixed section template to every hybrid. A template demands
  sections the declaration never made owed and, worse, stays silent
  about an area a declared technology did make relevant.
- Resolving a hermetic-plus-polymer declaration by preferring one of
  them. The two imply different downstream assessments, so the
  contradiction is an input defect to be returned to the supplier.

## Behavior contract (gate 3)

The technology-vocabulary validation, family grouping, area expansion,
owed-section derivation, coverage and uncovered-area reporting, sealing
category, activity enablement and the readiness verdict are exercised by
the gate 3 contract test:
scripts/test_q6005_hybrid_technology_identification_form.py against
scripts/q6005_hybrid_technology_identification_form_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_hybrid_technology_identification_form.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
