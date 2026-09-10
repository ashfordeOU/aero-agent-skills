---
name: e1002-qualification
description: "Use when running the qualification stage of an ECSS-E-ST-10-02C verification programme: closing design qualification against requirements before acceptance/QR, tailoring the qualification scope by product heritage category (Table 5-1: new design, unmodified heritage within envelope, modified or envelope-exceeding heritage), and confirming every product in scope is closed with matching evidence. Trigger: qualification stage, design qualification, heritage product category, Table 5-1, qualification by similarity, delta qualification, qualification review, QR, e-st-10-02, ecss, e-st-10c."
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
  tags: [ecss, e-st-10c, qualification, heritage, verification-stage, delta-qualification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Qualification Stage & Heritage Tailoring (space-systems/ecss/e1002-qualification)

Use when the task is running the qualification stage of an
ECSS-E-ST-10-02C verification programme: closing design qualification
against requirements, tailored by product heritage, ahead of
acceptance and the qualification review (QR).

## Domain quick reference

- ECSS-E-ST-10-02C clause 5.2.4.2 defines the qualification stage:
  demonstrate, before acceptance, that the design (hardware, software,
  and its production process) meets its requirements with adequate
  margin, using the verification methods already assigned under clause
  5.2.2 and a qualification or protoflight article.
- Table 5-1 tailors how much qualification evidence is needed by
  product heritage: a new design needs full qualification against
  every applicable requirement; an existing design reused unmodified
  and within its previously-qualified envelope can close qualification
  by similarity/heritage evidence instead of repeating tests; an
  existing design that has been modified, or is applied outside its
  previously-qualified envelope, needs delta qualification limited to
  the requirements affected by the change or the envelope difference.
- A safety-critical requirement cannot be closed by heritage/similarity
  alone once the design has changed or the envelope has moved -- it
  needs delta (or full) qualification evidence specific to that
  change, consistent with the safety-critical rule used for method
  selection in the sibling e10-req-verif-methods leaf.
- The qualification stage cannot be declared complete, and cannot feed
  the stage-closure check owned by the sibling e1002-stages leaf
  (clause 5.2.4.1), until every product/requirement in scope is closed
  with evidence matching its assigned scope.

## Workflow

1. For each product (or requirement) in the qualification scope,
   capture its heritage inputs: is it a new design, has the design
   been modified, is the intended application within the design's
   previously-qualified envelope, and is it safety-critical.
2. Classify the product into a Table 5-1 heritage category:
   new design; heritage, unmodified and within envelope; or heritage,
   modified or outside envelope.
3. Derive the qualification scope from the category: new design ->
   full qualification; unmodified-within-envelope heritage -> closed
   by similarity; modified-or-outside-envelope heritage -> delta
   qualification, escalated to full when the requirement is
   safety-critical (heritage cannot waive it).
4. Determine the evidence type required for the assigned scope (full:
   qualification test or analysis result; similarity: heritage
   dossier/similarity justification; delta: test or analysis on the
   requirements affected by the change or envelope difference only).
5. Record each product's qualification status: closed when evidence of
   the matching type has been supplied, otherwise open.
6. Before declaring the qualification stage complete and handing off
   to acceptance / QR, confirm every product/requirement in scope is
   closed; list any still open rather than assuming completion.

## Pitfalls

- Closing a modified or envelope-exceeding design by heritage/
  similarity alone instead of running delta qualification on the
  affected requirements.
- Waiving qualification evidence for a safety-critical requirement
  just because the parent product has heritage -- the escalation to
  full/delta scope for safety-critical items is mandatory, not
  discretionary.
- Treating a "delta" qualification as covering the whole product
  rather than only the requirements affected by the specific change or
  envelope difference.
- Declaring the qualification stage complete while some products or
  requirements in scope are still open.

## Behavior contract (gate 3)

The heritage-classification, scope-derivation, evidence-requirement,
and stage-completeness logic is exercised by the gate 3 contract test:
scripts/test_e1002_qualification.py against
scripts/e1002_qualification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
