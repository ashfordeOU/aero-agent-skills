---
name: e1006-char-ambiguity
description: "Use when determine whether requirements are unambiguous under ECSS-E-ST-10C §8.2.4: identify vague qualitative terms (adequate, sufficient, appropriate, optimal), weasel qualifiers (TBD, TBC, as required, where possible), compound connective ambiguity (and/or without explicit resolution), and implicit subjects with no stated system element; flag each finding with its category and severity; confirm every requirement admits exactly one interpretation before passing the ambiguity gate. Trigger: ecss, e-st-10-system-scope, requirement-ambiguity, vague-terms, single-interpretation, requirement-quality, e1006, e-st-10c."
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
  tags: [ecss, e-st-10-system-scope, requirement-ambiguity, vague-terms, single-interpretation, requirement-quality, e1006]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Requirements Characteristic — Unambiguity (space-systems/ecss/e1006-char-ambiguity)

Use when the task is to determine whether requirements are unambiguous
per ECSS-E-ST-10C §8.2.4 — confirming that each requirement text admits
exactly one interpretation so that every reader derives the same meaning.

## Domain quick reference

- A requirement is unambiguous when it can be interpreted in one and only
  one way. Any term that a reader could reasonably resolve in more than one
  direction introduces ambiguity.
- Four categories of ambiguity are checked in sequence: (1) vague
  qualitative terms — words such as adequate, sufficient, appropriate, or
  optimal that carry no measurable bound; (2) weasel qualifiers — escape
  clauses or placeholders such as TBD, TBC, as required, or where possible
  that defer the requirement without a concrete value; (3) compound
  connective ambiguity — the construction "and/or" which conflates inclusive
  OR, exclusive OR, and AND into a single unresolved choice; (4) implicit
  subject — a requirement text that begins with a modal verb or action verb
  without first naming the system element the requirement binds to.
- Severity is assigned per finding: HIGH for terms that make the requirement
  unverifiable (adequate, TBD, and/or), MEDIUM for terms that introduce
  uncertainty but leave a plausible single reading (flexible, implicit
  subject), LOW for borderline terms that depend on context (support).

## Workflow

1. For each requirement, scan the text for vague qualitative terms from the
   standard watchlist (adequate, sufficient, appropriate, optimal, optimum,
   reasonable, user-friendly, easy, fast, slow, good, robust, simple,
   minimize/maximize without a bound, etc., and so on). Flag every match
   with category VAGUE_TERM and its associated severity.
2. Scan for weasel qualifiers (TBD, TBC, TBR, as required, as necessary,
   as applicable, if required, if necessary, where possible, where
   practicable, to be defined, to be determined). Flag every match with
   category WEASEL_QUALIFIER and severity HIGH.
3. Scan for the compound connective "and/or" in any case. Flag every match
   with category COMPOUND_CONNECTIVE and severity HIGH, with guidance to
   either split into two requirements or use explicit inclusive/exclusive
   language.
4. Check whether the requirement text begins with a modal or action verb
   (shall, should, must, will, may, can, provide, ensure, support, enable,
   allow, handle) without a preceding noun phrase naming the subject. Flag
   the opening word with category IMPLICIT_SUBJECT and severity MEDIUM.
5. Collect all findings per requirement. A requirement is unambiguous only
   when its finding list is empty. Report requirements with findings for
   rework; report unambiguous requirements as passing.
6. Produce a batch summary: total count, unambiguous count, flagged count,
   and per-category finding totals.

## Pitfalls

- Treating severity MEDIUM as acceptable without review — a MEDIUM finding
  still introduces a second possible interpretation; the standard requires a
  single interpretation, not a dominant one.
- Accepting "minimize X" or "maximize X" as unambiguous — without a
  measurable bound or reference state, no verifier can determine when the
  requirement is met; these must carry an explicit numerical criterion.
- Passing a requirement whose only ambiguity is an implicit subject on the
  grounds that the subject is "obvious from context" — the standard requires
  the subject to be stated, not inferred.
- Conflating "and/or" resolution with a design choice — the ambiguity
  must be resolved at the requirement level, not left to the implementer.

## Behavior contract (gate 3)

The vague-term, weasel-qualifier, compound-connective, and implicit-subject
logic is exercised by the gate 3 contract test:
scripts/test_e1006_char_ambiguity.py against
scripts/e1006_char_ambiguity_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1006_char_ambiguity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
