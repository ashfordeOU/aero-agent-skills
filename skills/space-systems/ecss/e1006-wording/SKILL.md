---
name: e1006-wording
description: "Use when verify requirement wording against ECSS-E-ST-10C §8.3 rules: confirm each statement uses shall (mandatory), should (recommendation), or may (permission); detect non-standard verbal forms (will, must); flag ambiguous or unverifiable terms (adequate, appropriate, user-friendly); enforce single obligation per statement; and reject embedded rationale text. Replace forbidden terms with measurable criteria and move justification to a NOTE. Trigger: ecss, e-st-10-system-scope, wording, verbal-form, shall, requirements-authoring, ambiguity, single-statement, verifiability."
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
  tags: [ecss, e-st-10-system-scope, wording, verbal-form, shall, requirements-authoring, ambiguity, single-statement, verifiability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Requirements Authoring — Wording Rules (space-systems/ecss/e1006-wording)

Use when the task is to verify or correct the wording of system
requirements per ECSS-E-ST-10C §8.3 — selecting the right verbal form,
removing ambiguous terms, splitting compound obligations, and relocating
embedded rationale.

## Domain quick reference

- §8.3 prescribes three verbal forms: **shall** for every mandatory
  requirement, **should** for a recommendation that is not binding, and
  **may** for a permitted option. Any other form (will, must, is required
  to) is non-standard and must be replaced with the correct keyword before
  the requirement enters a baseline.
- A requirement must express exactly one obligation. If a statement
  contains more than one **shall** clause, it covers more than one
  requirement; each clause must be separated into its own standalone
  statement so that traceability, verification, and change control can be
  applied at the right granularity.
- Ambiguous and unverifiable terms are forbidden in requirement text.
  Words such as "adequate", "appropriate", "sufficient", "user-friendly",
  "maximize", "minimize", "easy", "robust", "flexible", "where
  applicable", and "etc." have no measurable criterion attached and must
  be replaced with specific, quantified limits or pass/fail conditions.
- Rationale and justification belong in a NOTE attached to the
  requirement, never in the requirement text itself. Phrases such as
  "in order to", "so that", "because", and "to enable" signal that
  rationale has been embedded and must be moved.

## Workflow

1. For each candidate requirement statement, identify the verbal form
   present: **shall**, **should**, **may**, or a non-standard form.
   If a non-standard form (will, must, is required to, are required to)
   is found, reject the statement and instruct the author to substitute
   **shall**. If no verbal form is present, the statement is not a
   requirement and must be reworded or removed.
2. Count the number of **shall** clauses in the statement. If the count
   is greater than one, split the statement at each obligation boundary
   so that each resulting statement contains exactly one **shall** clause
   and is independently traceable.
3. Scan the requirement text for ambiguous or unverifiable terms from
   the forbidden list. For each hit, flag the term and require the
   author to replace it with a specific, measurable criterion (a
   numeric limit, a test-observable condition, or a defined standard
   reference).
4. Scan the requirement text for rationale-marker phrases. For each
   hit, extract the rationale clause and move it verbatim into a NOTE
   below the requirement. The requirement text itself retains only the
   obligation.
5. After applying steps 1–4, re-check the resulting statement. A
   requirement passes wording review when: the verbal form is **shall**
   (or **should**/**may** for the appropriate type), no forbidden terms
   remain, the obligation count is one, and no rationale-marker phrase
   is present.

## Pitfalls

- Accepting "will" as equivalent to "shall" — in English-language
  technical standards "will" is a declaration of fact about what the
  system is expected to do, not an obligation imposed on it; replacing
  it with "shall" changes the normative weight.
- Leaving "and/or" in requirement text — the ambiguity (is one
  sufficient, or are both required?) makes the verification criterion
  undefined; the author must decide and write two explicit alternatives
  or a conjunction.
- Treating the absence of a forbidden term as a guarantee of
  verifiability — a requirement can be free of listed forbidden terms
  and still be unverifiable if it lacks a measurable threshold. The
  forbidden-term scan is a minimum filter, not a completeness check.
- Splitting a compound requirement and losing shared context — when a
  single statement is split into two, both new requirements must carry
  the subject noun and any qualifying conditions that were implicit in
  the original combined form.

## Behavior contract (gate 3)

The verbal-form detection, obligation-count, forbidden-term, and
rationale-marker logic is exercised by the gate 3 contract test:
scripts/test_e1006_wording.py against scripts/e1006_wording_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1006_wording.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
