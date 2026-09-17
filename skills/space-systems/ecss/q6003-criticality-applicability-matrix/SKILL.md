---
name: q6003-criticality-applicability-matrix
description: "Derive the assurance requirement set that applies to a device from its criticality category through the normative applicability matrix of ECSS-Q-ST-60-03C clause 9.2. Use when a device assurance plan is being tailored and the category has to follow the worst credible failure effect rather than a declaration, then drive which requirements apply outright and which apply only with agreed tailoring. Reports requirements deleted with no justification, mandatory rows tailored or dropped, declarations citing rows the matrix never carried, applicable rows left undeclared, and scores tailoring coverage. Trigger: ecss, q-st-60-03, device-criticality-category, assurance-applicability-matrix, requirement-tailoring-justification, mandatory-requirement-retention, failure-effect-severity, criticality-driven-requirement-set."
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
  tags: [ecss, q-st-60-device-assurance-scope, q6003-criticality-applicability-matrix, device-criticality-category, assurance-applicability-matrix, requirement-tailoring-justification, mandatory-requirement-retention, failure-effect-severity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Assurance — Criticality Applicability Matrix (space-systems/ecss/q6003-criticality-applicability-matrix)

Use when the task is the tailoring step of ECSS-Q-ST-60-03C clause 9.2 —
turning a device's criticality category into the actual set of assurance
requirements it has to meet, and judging whether a proposed tailoring of
that set holds.

## Domain quick reference

- The category is derived, not declared. It follows the severity of the
  worst credible failure effect of the device in its application, and
  the extent to which that effect can be recovered. Recovery relaxes the
  category by at most one step and never relaxes a catastrophic effect
  at all, because a recovery path that has to work is not a reason to
  assure the part less.
- A device that does not carry a mission-critical function sits one step
  further down than the same failure effect would otherwise place it.
  That is the only other relief, and the result is clamped at the least
  critical category rather than running off the end of the scale.
- The matrix is the normative object and it has three cell values, not
  two. A requirement can apply outright, apply only with agreed
  tailoring, or not apply at that category. Collapsing the middle value
  into either neighbour is what turns a tailoring review into an
  argument.
- The two applicable values behave differently under tailoring. A row
  that applies outright is retained; it cannot be tailored down or
  deleted, with or without a justification, because the matrix already
  decided that at this category. A row that applies with tailoring can
  be tailored or dropped, but only against a recorded justification.
- Four different things go wrong and they have different repairs: a row
  deleted with no justification, a mandatory row weakened, a declaration
  citing a row the matrix never carried, and an applicable row nobody
  declared at all. The last one is the quiet failure, because a
  declaration list that says nothing about a requirement looks clean
  until it is compared with the matrix row by row.
- Declaring something about a row that does not apply at this category
  is not a finding. It is redundant, and treating it as an error pushes
  reviewers toward stripping harmless statements from the plan.

## Workflow

1. Derive the criticality category from the failure-effect severity, the
   recoverability and whether the device carries a mission-critical
   function, or take a declared category when the programme has fixed
   one; keep both so the review can see which route was used.
2. Validate the matrix: every requirement row states an applicability
   for every category, from the closed three-value vocabulary, and no
   requirement identifier appears twice.
3. Read the matrix at the device's category to get the applicable set,
   then split it into the rows that apply outright and the rows that
   apply only with agreed tailoring.
4. Normalise the declared tailoring, refusing a requirement declared
   twice or declared with a state outside retained, tailored or deleted.
5. Produce the four finding lists separately: unjustified deletions,
   weakened mandatory rows, declarations outside the matrix, and
   applicable rows left undeclared.
6. Score tailoring coverage as the fraction of applicable rows that are
   soundly declared — retained, or justifiably tailored where the matrix
   permits it — and compare it with its floor, absorbing representation
   error at the equality with a named tolerance.
7. Report the category, the requirement sets, the findings and the
   verdict; the tailoring is acceptable only when no finding stands.

## Pitfalls

- Letting the programme name the category. A category picked to suit the
  schedule undoes the whole matrix in one step; it follows the failure
  effect, and the derivation is shown so the choice can be challenged.
- Relaxing a catastrophic effect because the failure is recoverable. The
  recovery is itself something that has to work, so it does not reduce
  the assurance the device needs.
- Treating apply-with-tailoring as not applicable. The row still applies;
  what is negotiable is its extent, and only against a recorded
  justification.
- Accepting a justification on a mandatory row. At that category the
  matrix has already answered the question, so the justification is an
  argument for changing the category or the design, not for dropping the
  requirement.
- Reviewing only what was declared. An applicable row that nobody
  mentioned never appears in a declaration-driven review, which is
  exactly how a requirement is lost between a matrix and a plan.
- Lowering the coverage floor for a plan that lands exactly on it. The
  equality is a representation question, handled by the tolerance inside
  the comparison; the floor stays where the assurance plan set it.

## Behavior contract (gate 3)

The category derivation, matrix validation, per-category requirement
sets, declaration normalisation, the four finding lists and the coverage
comparison are exercised by the gate 3 contract test:
scripts/test_q6003_criticality_applicability_matrix.py against
scripts/q6003_criticality_applicability_matrix_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6003_criticality_applicability_matrix.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
