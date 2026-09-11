---
name: e1006-char-uniqueness
description: "Use when verify that every requirement in a spacecraft system
  specification is unique in wording and content — detecting exact duplicates
  (identical normalised text) and near-duplicates (high substantive-vocabulary
  overlap) across the requirement set, and reporting each offending pair with a
  finding that identifies which requirements must be reworded or consolidated.
  Applies the uniqueness characteristic of ECSS-E-ST-10C §8.2.5: a requirement
  whose meaning or wording already exists in another requirement in the same
  set adds no engineering value and creates traceability ambiguity. Trigger:
  ecss, e-st-10-system-scope, requirement-uniqueness, duplicate-detection,
  near-duplicate, requirement-quality, wording-overlap, consolidation."
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
  tags: [ecss, e-st-10-system-scope, requirement-uniqueness, duplicate-detection, near-duplicate, requirement-quality, wording-overlap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Requirement Characteristic — Uniqueness (space-systems/ecss/e1006-char-uniqueness)

Use when the task is to verify that a set of spacecraft system requirements
satisfies the uniqueness characteristic of ECSS-E-ST-10C §8.2.5 — confirming
that no two requirements duplicate each other in wording or intent, and
producing findings for every offending pair.

## Domain quick reference

- ECSS-E-ST-10C §8.2.5 states that each requirement in a specification shall
  be unique: no other requirement in the same document shall convey the same
  information or impose the same constraint, whether through identical wording
  or through different wording that amounts to the same engineering obligation.
  Duplicate requirements create ambiguity in traceability matrices (which
  parent feeds which child?), inflate verification cost (the same test must be
  linked to two IDs), and make change control error-prone (a change to one
  copy is often missed in the other).
- Two requirements are **exact duplicates** when their texts are identical
  after normalisation (lowercase, whitespace collapse, Unicode NFC). Exact
  duplicates are the clearest violation: one must be removed or renumbered.
- Two requirements are **near-duplicates** when their substantive vocabulary
  overlaps above a configurable similarity threshold (default Jaccard ≥ 0.85
  after stopword removal). Near-duplicates may reflect a legitimate engineering
  distinction captured by the differing tokens, or may reflect copy-paste drift;
  each pair requires human judgement before consolidation.
- The uniqueness check is complementary to, not a replacement for, the
  consistency check (§8.2.7) and the completeness check (§8.2.3); a
  requirement set can be unique yet inconsistent, or complete yet contain
  duplicates.

## Workflow

1. Collect the full requirement set from the specification under review.
   Each requirement must carry a stable identifier (e.g. REQ-SYS-001) and
   its full text. If a requirement lacks an identifier, assign a provisional
   one before proceeding — the identifier is the key used in all findings.
2. Normalise every requirement text: apply Unicode NFC, convert to
   lowercase, collapse all internal whitespace to single spaces. This removes
   formatting artefacts that would cause the comparison to miss genuine
   duplicates or flag non-duplicates.
3. Group requirements by their normalised text. Any group containing more than
   one requirement is an exact-duplicate group; produce one finding per
   additional member of each group (the first-occurrence member is retained as
   the canonical requirement, subsequent members are the offenders).
4. For each remaining requirement pair not already flagged as exact duplicates,
   compute the Jaccard similarity of their substantive-vocabulary token sets
   (all word tokens after stopword removal). Flag pairs at or above the
   near-duplicate threshold. Record the similarity score in the finding so the
   reviewer can judge severity.
5. Compile findings: each exact-duplicate finding names both requirement IDs
   and states that the text is identical; each near-duplicate finding names
   both IDs and reports the similarity score. A requirement set with no
   findings is unique per §8.2.5.
6. For each exact-duplicate finding, the authoring team must either remove one
   copy and update all traceability links, or rephrase one copy to capture a
   genuinely distinct engineering obligation. For near-duplicate findings, the
   team must confirm the differing tokens convey a distinct constraint and, if
   not, consolidate.

## Pitfalls

- Comparing raw text without normalisation: a requirement copied with an
  extra trailing space or a different apostrophe form will evade exact-duplicate
  detection even though it is substantively identical.
- Setting the near-duplicate threshold too low: at Jaccard ≥ 0.5 almost every
  pair of requirements in the same subsystem will flag, flooding the reviewer
  with false positives. Start at 0.85 and lower only if the vocabulary is
  highly domain-specific and repetitive.
- Removing the shorter duplicate without updating traceability: if REQ-001 was
  allocated downstream and is then deleted in favour of REQ-002, the
  downstream links must be retargeted or verification evidence will dangle.
- Treating near-duplicate findings as automatic violations: two requirements may
  legitimately share most vocabulary while differing in a single critical
  qualifier (e.g. "shall survive" vs. "shall withstand") — the differing token
  captures a distinct verification method and must not be removed.

## Behavior contract (gate 3)

The normalisation, Jaccard-similarity, exact-duplicate, near-duplicate, and
validation logic is exercised by the gate 3 contract test:
scripts/test_e1006_char_uniqueness.py against
scripts/e1006_char_uniqueness_logic.py (stdlib unittest, offline). Run:

    python3 scripts/test_e1006_char_uniqueness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
