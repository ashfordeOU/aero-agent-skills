---
name: e5053-additional-comments
description: "Assess the additional-comments subclause of a SpaceWire service primitive against ECSS-E-ST-50-53 clause 5.2.2.5. Use when a protocol service definition carries per-primitive closing notes that must stay informative and must not become a second place requirements live: confirm every primitive states the subclause or declares it empty, detect normative wording that would create an unnumbered requirement, resolve every clause cross-reference against the declared index, measure how much of the note merely repeats the function, semantics, generation or receipt subclauses, and hold the note inside its length budget. Trigger: ecss, e-st-50-53, service-primitive-additional-comments-subclause, informative-note-audit, normative-wording-in-a-note, clause-cross-reference-resolution, subclause-duplication-ratio, spacewire-service-definition."
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
  tags: [ecss, e-st-50-spacewire-scope, e5053-additional-comments, service-primitive-additional-comments-subclause, informative-note-audit, normative-wording-in-a-note, clause-cross-reference-resolution, spacewire-service-definition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire Service Primitive — Additional Comments Subclause (space-systems/ecss/e5053-additional-comments)

Use when the task is the additional-comments subclause of ECSS-E-ST-50-53
clause 5.2.2.5 — the closing note on a service primitive, the only part
of the primitive specification with no fixed content, and for that reason
the part that collects the material the other four subclauses should have
carried.

## Domain quick reference

- The subclause is informative. Anything normative written into it is a
  requirement with no number, which means no compliance matrix, no
  verification method and no traceability; it will be implemented by
  whoever happens to read it and missed by everyone else.
- Silence and emptiness are different. A primitive that states the
  subclause has nothing to add is complete; a primitive whose subclause
  is simply absent leaves the reader unable to tell whether it was
  considered. An explicit declaration of emptiness is the compliant form.
- Cross-references are the subclause's real work — pointing at the clause
  that governs a detail rather than restating it. A reference that does
  not resolve against the specification's clause index is worse than no
  reference, because it reads as authority that cannot be checked.
- Duplication is measured, not judged. The useful quantity is the share
  of the note's own informative tokens that already appear in the four
  preceding subclauses of the same primitive. Past a declared share the
  note is a copy that will drift, and the finding should quote the share.
- A note that runs past its budget is a section in the wrong place. The
  budget is a word count, applied after normalisation so that formatting
  does not decide whether a note passes.

## Workflow

1. Validate the record: a primitive name, an optional note, and the four
   preceding subclauses supplied as the comparison text. Non-text values
   anywhere are malformed input rather than findings.
2. Resolve the note: absent, null and whitespace-only are the same defect
   — the subclause was never written. A note matching one of the declared
   empty forms is compliant and skips the remaining content checks.
3. Scan the normalised note for normative wording and report every marker
   found, so the author can see which sentences have to move into a
   numbered requirement.
4. Extract clause references in dotted-number form and resolve each
   against the declared clause index; report the unresolved ones by
   number.
5. Tokenise the note and the four preceding subclauses, drop the closed
   stopword set, and compute the share of the note's tokens already
   present upstream. Compare that share with the declared ceiling using a
   named tolerance so a note sitting exactly on the ceiling is decided by
   the rule rather than by floating-point representation.
6. Count the normalised words against the budget, then roll every
   primitive up into a compliant count with the set-level findings.

## Pitfalls

- Reading an empty note as compliant because nothing is wrong with it. An
  absent subclause and a note that says there is nothing to add carry
  different information, and only the second one tells you the author
  considered the question.
- Searching for normative wording case sensitively, or only at the start
  of a sentence. The marker appears mid-sentence far more often than not.
- Resolving cross-references by pattern alone. A well-formed clause
  number that names no clause in the specification is exactly the failure
  the check exists to find, so the index has to be consulted.
- Computing the duplication share over raw tokens. Stopwords dominate any
  two pieces of English prose and will push every note over any ceiling
  worth setting.
- Asserting a strict comparison on the duplication share. It is a ratio
  of counts and a note built to sit on the ceiling lands there exactly;
  the comparison carries a tolerance and the ceiling itself is never
  moved to make a note pass.

## Behavior contract (gate 3)

The record validation, empty-form recognition, normative wording scan,
cross-reference extraction and resolution, duplication-share measurement
against the ceiling, word budget and set-level roll-up are exercised by
the gate 3 contract test:
scripts/test_e5053_additional_comments.py against
scripts/e5053_additional_comments_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e5053_additional_comments.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
