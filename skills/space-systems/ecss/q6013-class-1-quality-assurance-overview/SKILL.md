---
name: q6013-class-1-quality-assurance-overview
description: "Assess how the quality assurance duties of a highest-assurance commercial EEE part programme are allocated under ECSS-Q-ST-60-13C clause 4.5.1: confirm every mandatory duty carries a named owner, test that owner for independence from the activity being assured, keep an absent duty apart from one deferred on an approved authorisation, weight the covered duties into a programme coverage score, and return ranked findings with one assurance readiness verdict. Use when a parts control plan, quality assurance duty matrix or supplier assurance allocation is reviewed. Trigger: ecss, q-st-60-13c, class-1-quality-assurance-duties, parts-control-plan-ownership, assurance-owner-independence, quality-duty-coverage-score, programme-assurance-readiness-verdict."
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
  tags: [ecss, q-st-60-eee-component-scope, q-st-60-13c, q6013-class-1-quality-assurance-overview, class-1-quality-assurance-duties, parts-control-plan-ownership, assurance-owner-independence, quality-duty-coverage-score, programme-assurance-readiness-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Class 1 — Quality Assurance Overview (space-systems/ecss/q6013-class-1-quality-assurance-overview)

Use when the task is clause 4.5.1 of ECSS-Q-ST-60-13C: the frame of quality
assurance duties that applies to a commercial component programme run at the
highest assurance level. This leaf grades a duty matrix on whether every owed
duty has an owner, whether that owner can judge the work, and what fraction of
the frame the programme actually covers.

## Domain quick reference

- The assurance frame exists because the part does not bring one. A
  space-qualified component arrives with the manufacturer's own assurance
  system behind it; a commercial component arrives with a datasheet. At class
  1 the buying organisation supplies the missing frame, so the duties are the
  product, not the paperwork around it.
- A duty with no owner is not a small gap. Every other finding in the
  programme is discovered by somebody whose job it is to look, so an
  unallocated duty removes the detector rather than the activity, and nothing
  downstream reports its absence.
- Independence is what makes a review a review. The duties that judge
  delivered work — lot acceptance, data package review, nonconformance
  disposition — cannot be owned inside the organisation executing that work,
  because an owner grading its own output has no failure mode that produces a
  finding.
- Not every duty needs an independent owner, and demanding it everywhere
  costs credibility. Reporting duties and traceability upkeep sit naturally
  with the executing organisation; the independence test is applied to the
  duties that dispose of results.
- Absence, deferral and planning are three different states. A duty deferred
  on an approved authorisation is a decision with a name attached; a duty with
  an owner but no evidence is an intention; a duty missing from the matrix is
  invisible. Collapsing them into one bar loses exactly the distinction the
  review exists to make.
- Coverage is weighted because the duties are not equal. The duties whose
  absence cannot be recovered later — specification approval, manufacturer
  assessment, lot acceptance, nonconformance disposition — carry more of the
  score than periodic reporting does.

## Workflow

1. Take the duty matrix and validate each row: the duty named, its owner, the
   organisation that owner sits in, the state of the assignment and the state
   of its evidence. A duty outside the owed set is an input error, not a bonus
   row.
2. Establish which organisation executes the work being assured, because the
   independence test is relative to it and not an absolute property of the
   owner.
3. For each owed duty, find its row. A duty appearing nowhere in the matrix is
   the most serious finding available; report it by name rather than as a
   count.
4. Apply the independence test to the duties that dispose of delivered
   results. An owner inside the executing organisation on one of those duties
   is a critical finding even when the evidence is complete.
5. Count a duty as covered only when it is assigned, independently owned where
   that is required, and carries recorded or planned evidence. Weight the
   covered duties and divide by the total weight of the owed set.
6. Compare the coverage score with the score the programme requires, absorbing
   floating-point representation error at the boundary with a named tolerance
   rather than by lowering the required score.
7. Rank the findings and return one verdict: ready, ready-with-actions, or
   not-ready, with the unallocated and self-assured duties named first.

## Pitfalls

- Reading a full matrix as a covered programme. Every row can carry a name and
  the programme still fail, because a row with an owner and no evidence is an
  intention and a row owned by the executing organisation is not a review.
- Applying the independence test to every duty. Over-applied independence
  produces an unworkable matrix that gets quietly ignored, which costs more
  coverage than the duties it was protecting.
- Treating a deferral as an absence. A deferral names an authority and a
  reference and can be revisited at a review; an absence names nobody, and
  merging them destroys the trail the next review needs.
- Scoring duties as equal. An unweighted fraction lets a programme lose lot
  acceptance and gain a reporting duty at no cost, which is exactly the trade
  the weighting exists to prevent.
- Judging independence in the abstract. The same quality organisation is
  independent for a supplier-executed lot and not independent when it executes
  the work itself, so the executing organisation is an input to the test.
- Lowering the required coverage score to clear an exact-equality case. An
  equality at the limit is a representation question, handled by the tolerance
  inside the comparison; the required score stays as agreed.

## Behavior contract (gate 3)

The duty weighting, assignment validation, independence test, coverage
scoring, per-duty findings and the readiness verdict are exercised by the gate
3 contract test:
scripts/test_q6013_class_1_quality_assurance_overview.py against
scripts/q6013_class_1_quality_assurance_overview_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_quality_assurance_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
