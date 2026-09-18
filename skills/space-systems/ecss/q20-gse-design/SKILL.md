---
name: q20-gse-design
description: "Audit the design, development and verification of ground support equipment under ECSS-Q-ST-20C clause 5.8.1: trace each GSE requirement up to a source requirement that actually exists and down to a verification record, compare the method a record used with the method the requirement planned, refuse a paper closure on a requirement that protects flight hardware or people, compute the closure coverage of the set, and return approved, approved-with-actions or not-approved. Use when a GSE design has to be reviewed before it goes near flight hardware. Trigger: ecss, q-st-20c-clause-5-8-1, gse-requirement-traceability, gse-verification-record, gse-verification-method-substitution, gse-closure-coverage, gse-design-review-verdict."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-gse-design, gse-requirement-traceability, gse-verification-record, gse-verification-method-substitution, gse-closure-coverage, gse-design-review-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS GSE Design Assurance (space-systems/ecss/q20-gse-design)

Use when the task is the clause 5.8.1 quality assurance of ground support
equipment design, development and verification in ECSS-Q-ST-20C: a GSE design
is being reviewed, and the question is whether its requirements trace, whether
the verification actually closed them, and whether the design may be used.

## Domain quick reference

- GSE is not flight hardware, but it holds, lifts, powers and tests flight
  hardware, so its requirement set is traced with the same discipline. A GSE
  requirement with no source requirement behind it was invented inside the GSE
  design, and nobody outside that design agreed to it.
- Traceability runs both ways. Upward, every GSE requirement names a parent in
  the source set; downward, every GSE requirement has a verification record
  that closes it. A record pointing at a requirement that does not exist is a
  finding in the other direction.
- The method is part of the requirement, not a free choice at verification
  time. A requirement planned for test and closed by analysis has not been
  verified as agreed, whatever the analysis says.
- Criticality decides what a method may be. A requirement protecting personnel
  or the flight hardware the GSE touches is closed by test; review of design
  and analysis show intent, not behaviour.
- Coverage is a set property, not a per-requirement one. A requirement with a
  passing record and a later failing one is not closed, and the coverage
  fraction has to say so.
- The review outcome separates what stops the design from what follows it. An
  open record on a non-critical requirement is an action; an untraced
  requirement or a failed verification is not.

## Workflow

1. Validate the requirement set: unique identifiers, a criticality and a
   planned method from the closed vocabularies, and a parent identifier where
   one is claimed.
2. Validate the verification records the same way, refusing a duplicated record
   identifier and an unknown result state.
3. Trace upward, separating a requirement that names no parent from one whose
   parent is not in the declared source set.
4. Trace downward: name each requirement with no record, each method
   substitution, each failed record and each open record as its own finding.
5. Grade method adequacy against criticality independently of whether the
   verification happened at all.
6. Compute closure coverage, counting a requirement closed only when it has a
   passing record and no failing or open one, and compare it with the required
   value through a named tolerance.
7. Sort the findings into blocking and actions, then return the review verdict.

## Pitfalls

- Counting records instead of requirements. Three records against one
  requirement leaves the other two requirements unverified, and a record count
  hides that.
- Accepting a method substitution because the substitute passed. The planned
  method is what the requirement was agreed against; changing it is a change to
  the requirement, and it goes through the same approval.
- Closing a lifting or mating requirement on review of design. The GSE holds
  flight hardware, and a drawing review does not show what the fixture does
  under load.
- Treating a passing record as permanent. A later failure on the same
  requirement reopens it, and the coverage figure has to fall accordingly.
- Folding every finding into one verdict. An open record on a non-critical item
  is an action the review carries; an untraced requirement is not.
- Reading an empty verification set as nothing to report. No records means no
  requirement is closed, which is the loudest finding the review can make.

## Behavior contract (gate 3)

The requirement and record validation, upward and downward traceability,
method-substitution detection, criticality-based method adequacy, closure
coverage and the review verdict are exercised by the gate 3 contract test:
scripts/test_q20_gse_design.py against scripts/q20_gse_design_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q20_gse_design.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
