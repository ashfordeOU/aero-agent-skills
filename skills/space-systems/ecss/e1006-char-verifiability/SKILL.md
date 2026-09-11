---
name: e1006-char-verifiability
description: "Use when verify that every system requirement is assigned at least one
  recognized verification method (Test, Analysis, Inspection, Review of Design) and
  at least one verification level (system, subsystem, equipment, component) as required
  by ECSS-E-ST-10C §8.2.9 and ECSS-E-ST-10-02C: flag requirements with no method,
  no level, an unrecognized method or level code, or text that bundles multiple
  independently verifiable conditions into one statement, and confirm each method-level
  pairing is on record in the project verification requirements database. Trigger:
  ecss, e-st-10-system-scope, verifiability, verification-method, verification-level,
  e-st-10-02, vrdb, requirement-verifiability."
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
  tags: [ecss, e-st-10-system-scope, verifiability, verification-method, verification-level, vrdb]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Systems Engineering — Requirement Verifiability (space-systems/ecss/e1006-char-verifiability)

Use when the task is to verify that every system requirement in a requirement set
can be confirmed as met -- specifically, that each requirement carries at least one
recognized verification method and at least one verification level, that the
requirement text does not bundle multiple independently verifiable conditions into
a single statement, and that each method-level pairing is recorded in the project's
verification requirements database per ECSS-E-ST-10C §8.2.9 and ECSS-E-ST-10-02C.

## Domain quick reference

- ECSS-E-ST-10C §8.2.9 requires that every requirement be verifiable: its
  fulfilment must be demonstrable by at least one recognized method at a specific
  point in the system hierarchy. The four verification methods per ECSS-E-ST-10-02C
  are Test (T), Analysis (A), Inspection (I), and Review of Design (D). Each
  method demonstrates fulfilment differently: testing performs a physical
  demonstration against acceptance criteria; analysis uses mathematical or
  simulation models; inspection is a visual or dimensional check; review of design
  examines documented evidence that the requirement is addressed in the design.
- Verification levels identify the tier in the system hierarchy at which the
  verification is performed: system, subsystem, equipment, or component. A
  requirement may be assigned more than one method and more than one level when
  the project's verification approach calls for confirmation at multiple tiers.
- A compound requirement -- one whose text contains more than one "shall" clause --
  bundles multiple independently verifiable conditions. This makes it difficult to
  declare individual verification closure on each condition and is flagged as a
  verifiability issue that must be resolved by splitting the requirement before
  method-level assignment proceeds.
- Every valid method-level assignment for every requirement must be recorded in
  the project's verification requirements database (VRDB) as a traceable link;
  a requirement with a method and level assigned but not entered in the VRDB is
  not yet verifiability-compliant under the standard.

## Workflow

1. For each requirement in the set, confirm its text is present and contains
   exactly one verifiable condition (one "shall" clause). Flag requirements with
   empty text or with multiple "shall" occurrences for rework before proceeding.
2. For each requirement that passes step 1, check that at least one verification
   method code is assigned and that every assigned code is recognized (T, A, I, D).
   Flag requirements with no method or with an unrecognized method code.
3. For each requirement that passes step 2, check that at least one verification
   level is assigned and that every assigned level is recognized (system, subsystem,
   equipment, component). Flag requirements with no level or with an unrecognized
   level identifier.
4. Confirm that each method-level pairing for the requirement is documented in the
   project VRDB; a requirement that passed steps 1-3 but has no VRDB entry is
   compliant in assignment but not yet in documentation -- flag this as a
   traceability gap rather than a verifiability failure.
5. Aggregate findings per requirement and per finding type. A requirement is
   verifiability-compliant only when steps 1-3 produce no findings and step 4
   shows at least one VRDB entry.

## Pitfalls

- Treating a compound requirement as verifiable because a method is assigned: if
  the text bundles two "shall" conditions, the method assignment is ambiguous and
  verification closure on each condition cannot be individually declared, making
  the requirement non-verifiable as written.
- Accepting any method code without checking it against the recognized set: a
  project-local code or abbreviation is not a recognized ECSS method and signals
  a gap in the verification approach, not a valid assignment.
- Conflating "assigned" with "documented": a method-level pair may be agreed
  informally but not yet entered in the VRDB; the standard's traceability
  requirement is met only when the entry exists.
- Treating a requirement with no level as covered by the method assignment: method
  and level are both mandatory; a requirement that specifies how it will be verified
  but not at which tier of the system hierarchy is incomplete.

## Behavior contract (gate 3)

The method validation, level validation, compound-requirement detection,
per-requirement assessment, and summary aggregation logic are exercised by the gate
3 contract test: scripts/test_e1006_char_verifiability.py against
scripts/e1006_char_verifiability_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1006_char_verifiability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
