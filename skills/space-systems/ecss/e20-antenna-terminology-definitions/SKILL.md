---
name: e20-antenna-terminology-definitions
description: "Use when verify that one recognised source of antenna terminology governs every project document under ECSS-E-ST-20C clause 7.2.1.2.1: confirm exactly one terminology-source is declared and that it is a recognised vocabulary, resolve each term used in a specification, drawing or report against the canonical-term registry, rewrite a deprecated-synonym onto its canonical form, flag an uncategorized term and a term whose defining vocabulary differs from the declared one, check each project-glossary entry for a unit or a source that contradicts the canonical definition, then take the terminology-conformance-ratio across documents and hold it against the project threshold. Trigger: ecss, e-st-20-electrical-scope, e20-antenna-terminology-definitions, antenna-terminology-source, canonical-term-registry, deprecated-synonym-mapping, project-glossary-conformance, cross-document-term-consistency."
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
  tags: [ecss, e-st-20-electrical-scope, e20-antenna-terminology-definitions, antenna-terminology-source, canonical-term-registry, deprecated-synonym-mapping, project-glossary-conformance, cross-document-term-consistency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Antenna Terminology Definitions (space-systems/ecss/e20-antenna-terminology-definitions)

Use when the task is the terminology requirement of ECSS-E-ST-20C clause
7.2.1.2.1 -- pinning the project to a single recognised antenna
vocabulary and proving that every specification, drawing and report
actually uses the terms that vocabulary defines.

## Domain quick reference

- Clause 7.2.1.2.1 asks for one recognised source of antenna
  terminology, used consistently throughout the project. The check is
  therefore two-sided: exactly one source is declared, and it is a
  vocabulary the discipline recognises rather than a project invention.
  Zero declared sources and two declared sources are both findings, and
  the second is the more damaging: two vocabularies in circulation is
  precisely the condition the clause exists to prevent.
- Terms fall into three states against the registry. A canonical term is
  defined by a recognised vocabulary and is used as written. A
  deprecated-synonym is a term the discipline still hears but that the
  vocabulary replaces -- an ellipticity-ratio for an axial-ratio, an
  electrical-axis for a boresight, a three-decibel beamwidth for a
  half-power-beamwidth; it is rewritten onto its canonical form rather
  than accepted. An uncategorized term appears in neither list and must
  be either added to the project-glossary with a definition or dropped.
- A canonical term still carries the name of the vocabulary that defines
  it. When a document uses a term defined by a vocabulary other than the
  declared one, the term itself is correct but the single-source
  requirement is broken, and the finding names both vocabularies so the
  project can decide which one governs.
- A project-glossary entry that repeats a registry term must agree with
  it. An entry that cites a different defining vocabulary, or that
  assigns a different unit -- an axial-ratio in degrees rather than
  decibels, an antenna-gain as a bare ratio rather than decibels
  relative to isotropic -- silently creates a second definition of the
  same term, which is the failure mode the clause targets.
- The conformance figure is the fraction of term occurrences across all
  documents that need no rewrite. It is formed as one minus the
  nonconforming fraction, so a project with a single deviation in twenty
  occurrences sits exactly on a ninety-five percent threshold; that
  boundary is honoured rather than rounded away.

## Workflow

1. Read the declared terminology sources. Confirm exactly one is
   declared and that it resolves against the recognised vocabularies;
   record a finding for none, for more than one, and for a name that
   resolves against nothing.
2. For each document, resolve every term it uses: canonical,
   deprecated-synonym or uncategorized. Reject a malformed document
   record before it enters the count.
3. Rewrite each deprecated-synonym onto its canonical form and record
   the substitution as a finding against that document, naming the term
   the author should have used.
4. Flag each uncategorized term, and each canonical term whose defining
   vocabulary is not the declared one.
5. Check every project-glossary entry against the registry: defining
   vocabulary and unit must both agree, and a glossary entry keyed on a
   deprecated-synonym is itself a finding.
6. Total the term occurrences and the nonconforming occurrences, form
   the conformance ratio as one minus their quotient, and hold it
   against the project threshold.
7. The project is terminology-conformant only when the source, document
   and glossary finding lists are all empty and the ratio meets the
   threshold.

## Pitfalls

- Accepting a document because every term is recognisable. A
  deprecated-synonym is recognisable and still wrong under this clause;
  the check is which vocabulary defines the term, not whether a reader
  would understand it.
- Declaring two vocabularies "for completeness". Two sources mean two
  definitions of the same term are both defensible, which is exactly
  what a single-source requirement removes.
- Letting the project-glossary redefine a registry term with a
  different unit. The name then agrees across documents while the
  quantity does not, and the inconsistency survives every review that
  checks only spelling.
- Reading a high conformance ratio as a pass while findings remain. The
  ratio counts occurrences; a single uncategorized term in a controlling
  specification can carry more risk than twenty synonym rewrites.
- Comparing the ratio against the threshold with a bare inequality. The
  ratio is formed by subtraction, so a project exactly on the threshold
  can land fractionally below it; absorb the representation error rather
  than moving the threshold.

## Behavior contract (gate 3)

The term normalisation, term resolution, source validation,
document scan, glossary consistency, conformance-ratio and aggregate
project review logic is exercised by the gate 3 contract test:
scripts/test_e20_antenna_terminology_definitions.py against
scripts/e20_antenna_terminology_definitions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_antenna_terminology_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
