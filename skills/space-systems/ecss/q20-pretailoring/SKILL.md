---
name: q20-pretailoring
description: "Derive the tailored clause 5 requirement set from the ECSS-Q-ST-20C clause 6 pre-tailoring matrix for one space product type: refuse a matrix row that says nothing about a product type or calls a requirement modified without stating the modification, keep each surviving requirement with its disposition, name every requirement the matrix does not cover, reconcile the project's own proposal against the baseline so a relaxation needs an approved justification while a tightening does not, and report the share of the set that still applies. Use when a project has to justify which quality requirements it works to. Trigger: ecss, q-st-20c-clause-6, pre-tailoring-matrix, space-product-type-applicability, tailored-requirement-set, requirement-relaxation-justification, applicable-requirement-fraction."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-pretailoring, pre-tailoring-matrix, space-product-type-applicability, tailored-requirement-set, requirement-relaxation-justification, applicable-requirement-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Q-ST-20C Pre-Tailoring (space-systems/ecss/q20-pretailoring)

Use when the task is the clause 6 pre-tailoring of ECSS-Q-ST-20C: the standard
already states, per space product type, which of its clause 5 requirements
apply as written, which do not apply, and which apply in a modified form, and
a project has to work out what its own requirement set actually is.

## Domain quick reference

- The matrix is the baseline, not the proposal. What a project ends up working
  to is the matrix as the project modified it, and the two are compared line by
  line rather than assumed to agree.
- A row that is silent about a product type is not a row that says not
  applicable. Silence is the defect, and it is caught at the matrix rather than
  discovered at the review.
- Modified is not a softer word for not applicable. A modified requirement
  stays in the set, it is verified, and the modification it stands for is
  written down or the disposition means nothing.
- The two directions of a departure are not symmetric. Relaxing below the
  baseline takes a justification and an approval; tightening above it is the
  project's own business and is recorded rather than challenged.
- The applicable fraction is the number the tailoring argument is really about.
  A set at four fifths and one at one half are different programmes, and the
  fraction is what makes the difference visible.
- A requirement nobody pre-tailored is not a requirement that dropped out. It
  is a gap in the matrix, and it is reported against the matrix rather than
  silently applied or silently ignored.

## Workflow

1. Validate the matrix: every covered requirement carries a disposition for
   every declared product type, each disposition sits in the closed vocabulary,
   and a modified entry carries the modification it stands for.
2. Validate the product type against the closed list before anything is read
   out of the matrix for it.
3. Apply the matrix to the requirement set, keeping applicable and modified
   requirements in the tailored set and listing what dropped out.
4. Name each requirement with no matrix entry as its own finding rather than
   defaulting it either way.
5. Reconcile the project's proposed dispositions with the baseline, separating
   relaxations from tightenings by their position in the vocabulary.
6. Raise a relaxation with no approved justification behind it, and record a
   tightening without raising one.
7. Compute the applicable fraction over the full requirement set and return the
   tailored set, the findings and whether the tailoring may be adopted.

## Pitfalls

- Reading the matrix as the finished requirement set. It is the starting point;
  what the project proposed on top of it is where the argument lives.
- Dropping a modified requirement. It stays in, it is verified, and the
  modification is what the verification is against.
- Accepting a modified disposition with no modification written down. The
  disposition then means whatever the reader assumes, which is the failure the
  matrix exists to prevent.
- Treating every departure the same way. Challenging a project for being
  stricter than the baseline wastes the review on the one deviation that is
  never a risk.
- Reporting a count of applicable requirements. The fraction is what is
  comparable between product types and between projects; the count is not.
- Letting an uncovered requirement fall through quietly. Whichever way it
  falls, nobody decided it, and that is the finding.

## Behavior contract (gate 3)

The matrix validation including product-type completeness and the modification
note, product-type validation, application of the matrix to the requirement
set, uncovered-requirement findings, the relaxation-versus-tightening
reconciliation with approved justifications, the applicable fraction and the
adoption verdict are exercised by the gate 3 contract test:
scripts/test_q20_pretailoring.py against scripts/q20_pretailoring_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q20_pretailoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
