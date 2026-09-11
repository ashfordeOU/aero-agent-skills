---
name: e1006-char-singularity
description: "Use when verify each requirement statement adheres to the singularity characteristic of ECSS-E-ST-10-06C §8.2.7: confirm that every statement expresses exactly one verifiable requirement and does not embed multiple requirements through coordinating conjunctions, compound predicates, or stacked modal clauses. Scan each statement for multiple 'shall' occurrences, coordinating conjunctions joining independent requirement predicates, and list structures under a single modal verb. Flag each violating statement, identify the conjunction or structural pattern causing the violation, and recommend how to split the statement so each result expresses a single, standalone requirement. Trigger: ecss, e-st-10-system-scope, e-st-10-06c, requirements, singularity, compound-requirement, shall, conjunction, requirement-quality."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-06c, requirements, singularity, compound-requirement, shall, conjunction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Requirements Characteristics — Singularity (space-systems/ecss/e1006-char-singularity)

Use when the task is checking each requirement statement for the
singularity characteristic per ECSS-E-ST-10-06C §8.2.7 -- confirming
that each statement expresses exactly one requirement and does not embed
multiple requirements through compound modal clauses, coordinating
conjunctions joining independent predicates, or list structures under a
single modal verb.

## Domain quick reference

- §8.2.7 (paraphrased) states that each requirement statement shall
  express one and only one requirement. A statement that bundles two
  independently verifiable obligations into one sentence violates this
  characteristic, regardless of how the conjunction is phrased.
- A statement violates singularity when it contains more than one modal
  verb ("shall … shall"), joins independent requirement predicates with
  a coordinating conjunction ("shall measure … and report …"), uses
  additive phrases ("as well as", "in addition to"), or collapses a
  list of obligations under one modal ("shall: a) …; b) …").
- Compliant example: "The system shall measure inlet pressure." (one
  requirement, one modal, one predicate.)
- Non-compliant example: "The system shall measure inlet pressure and
  report it to the ground station." (two independently verifiable
  obligations joined by "and" -- split into two statements.)
- Splitting always produces two or more simpler, independently
  verifiable statements, each with its own identifier and rationale.

## Workflow

1. For each requirement statement, count every occurrence of the modal
   verb "shall" (case-insensitive). Any count greater than one
   immediately signals a compound requirement -- record a
   multiple-shall violation.
2. Check for the explicit pattern "and shall" or "or shall", which
   reveals that two modal clauses were joined after the fact.
3. Check for additive conjunctions: "as well as" and "in addition to"
   both embed a secondary obligation and violate singularity.
4. Check for compound predicates: a single "shall" followed by "and"
   and a second action verb (provide, store, transmit, monitor, etc.)
   suggests two requirements were merged into one predicate.
5. Check for list structures: "shall:" followed by a colon introduces a
   list where each item is a separate requirement; the entire construct
   violates singularity.
6. For each flagged statement, record the violation pattern id, a
   description of the structural problem, and a concrete split
   recommendation.
7. A statement is singularity-compliant only when all checks return
   no violation. Aggregate findings across the full set and report
   total, compliant count, non-compliant count, and the index list
   of non-compliant statements.

## Pitfalls

- Confusing "and" joining attributes or values with "and" joining
  requirements: "shall operate at 5 V and 12 V" expresses one
  requirement with two permissible values; "shall operate at 5 V and
  shall transmit telemetry" is two requirements. The presence of a
  second modal verb is the decisive signal.
- Treating "or" as always harmless: "shall measure pressure or
  temperature" may reflect a legitimate alternative-implementation
  choice (one requirement, two means), but in a prescriptive context it
  can also encode two distinct obligations -- evaluate in context and
  flag when the interpretation is ambiguous.
- Overlooking implicit lists: "shall support A, B, and C" may encode
  three independently verifiable obligations even without repeating
  "shall". If A, B, and C are separable requirements, the statement
  violates singularity.
- Declaring compliance because no explicit second "shall" appears:
  compound predicates with a single modal but two action verbs are
  still violations. The check must cover predicate structure, not only
  modal count.

## Behavior contract (gate 3)

The singularity violation checks (multiple-shall, and-shall,
as-well-as, in-addition-to, compound-predicate, shall-list) are
exercised by the gate 3 contract test:
scripts/test_e1006_char_singularity.py against
scripts/e1006_char_singularity_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e1006_char_singularity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
