---
name: q7001-cleanliness-requirements-flowdown
description: "Allocate a programme cleanliness requirement into the documents that actually bind a supplier and an integration team, then grade the result. Use when a top-level particulate, residue or largest-particle limit has to appear in purchase orders and in AIT procedures, and somebody must show that none of it was lost on the way down. Confirms each requirement reaches both document families, compares every carried limit with its parent, refuses a looser carried limit unless a waiver is cited, flags a clause that changes the requirement kind or names no verification method, flags a document carrying a requirement no parent defines, and reports coverage with the gaps named. Trigger: ecss, q-st-70-01, cleanliness-requirement-flowdown, procurement-cleanliness-clause, ait-cleanliness-procedure, carried-limit-strictness-check, cleanliness-relaxation-waiver."
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
  tags: [ecss, q-st-70-cleanliness-control-scope, q7001-cleanliness-requirements-flowdown, cleanliness-requirement-flowdown, procurement-cleanliness-clause, ait-cleanliness-procedure, carried-limit-strictness-check, cleanliness-relaxation-waiver]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness Control — Requirements Flowdown (space-systems/ecss/q7001-cleanliness-requirements-flowdown)

Use when the task is taking a programme-level cleanliness requirement
out of the contamination control plan and into the paper that binds
people — the purchase orders that buy the item and the AIT procedures
that handle it — and then showing that the flowdown is complete.

## Domain quick reference

- A cleanliness limit binds nobody until it appears in a document
  somebody works to. A contamination control plan states the programme
  intent; a purchase order and an AIT procedure are where a supplier and
  a bench technician read it. Grading the flowdown means grading those,
  not the plan.
- Two families have to be reached, and they fail differently. A limit
  that reaches procurement but not AIT buys a clean item and then
  handles it dirty. A limit that reaches AIT but not procurement asks
  the integration team to protect a cleanliness the item never had.
- Every limit here is an upper bound in which a smaller number is
  cleaner: particles per unit area, residue mass per unit area, the
  largest permitted particle. A carried limit is therefore compared, not
  matched. Stricter than the parent is the supplier's own business and
  passes; looser has relaxed a programme requirement.
- A relaxation is not automatically wrong, but it is never silent. The
  waiver reference is what separates a decision from a transcription
  error, and it is the only thing a reviewer two years later can follow.
- A clause that quietly changes the requirement kind — a residue limit
  arriving as an obscuration percentage — is worse than a missing
  clause, because it looks like coverage. It is refused as a comparison
  and raised as a finding.
- A carried requirement with no verification method named is carried in
  name only. Nobody at goods receipt knows what to measure, so it can
  never be shown to have been met, and it surfaces at the review as an
  open action instead of at the bench as a test.
- A document carrying a requirement identifier that no parent defines is
  normally a requirement renumbered upstream. The supplier is building
  to the old one, and nothing else in the chain will notice.

## Workflow

1. Validate each parent requirement: identifier, a known requirement
   kind, a positive limit, the surface it applies to, and the document
   roles it must reach.
2. Validate each receiving document: identifier, role, and clauses that
   name a requirement once each with a positive limit.
3. Match every carried clause to its parent. Refuse the comparison and
   raise a finding where the kind changed; raise a separate finding for
   a clause whose parent does not exist.
4. Compare each carried limit with the parent limit, absorbing
   representation error with a relative tolerance rather than widening
   the requirement, and raise a relaxation finding where the carried
   limit is genuinely looser.
5. Demand a waiver reference beside any relaxation, and raise a second
   finding where none stands.
6. Raise a finding for any carried clause with no verification method.
7. Roll up per requirement: which documents carry it, which required
   roles are still uncovered, the tightest limit carried, and whether it
   flowed cleanly.
8. Report the coverage fraction, the gap list, the verdict and every
   finding, so the gaps can be closed by name rather than by re-reading
   the whole set.

## Pitfalls

- Counting clauses instead of comparing them. A flowdown that reports
  "every requirement appears somewhere" hides the purchase order that
  bought to twice the residue limit.
- Treating a stricter child as an error. A supplier working cleaner than
  asked has cost itself money, not broken the requirement, and chasing
  it wastes the review that should have caught the relaxation.
- Accepting procurement coverage as coverage. The item arrives clean and
  is then integrated under a procedure that never heard of the limit.
- Letting a renumbered requirement pass as an unmatched clause. It reads
  as harmless noise and is usually a supplier building to a superseded
  number.
- Carrying a limit with no verification method. The number is in the
  contract and nothing in the programme can demonstrate it, which is
  discovered at the acceptance review rather than at goods receipt.

## Behavior contract (gate 3)

Requirement and document validation, the strictness comparison with its
tolerance, the relaxation and waiver rules, the kind-change refusal, the
unmatched-clause finding, per-role coverage and the coverage roll-up are
exercised by the gate 3 contract test:
scripts/test_q7001_cleanliness_requirements_flowdown.py against
scripts/q7001_cleanliness_requirements_flowdown_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7001_cleanliness_requirements_flowdown.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
