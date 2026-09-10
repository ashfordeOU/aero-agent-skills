---
name: e1003-retesting
description: "Use when applying ECSS-E-ST-10-03C clause 4.6 retesting rules to define whether an article must be retested: a design modification made after qualification, storage after a protoflight/acceptance test beyond the qualified shelf life, a previously flown article being prepared for reflight, or a qualification-model article proposed for flight use. Classify each case's required action (no retest, requalification, acceptance-level retest, or disallowed for flight) ahead of test-programme execution (sibling e1003-test-programme leaf), and verify no case in the retesting scope is left undetermined. Anchor: E-ST-10-03C clause 4.6. Trigger: retesting, retest, requalification, design modification after qualification, storage shelf life, reflown hardware, qualification model flight use, E-ST-10-03C, ecss."
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
  tags: [ecss, e-st-10-03c, retesting, requalification, storage-shelf-life, reflown-hardware, qualification-model, testing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Testing Retesting Rules (space-systems/ecss/e1003-retesting)

Use when the task is deciding, for a specific article and a specific
trigger event, whether ECSS-E-ST-10-03C requires it to be retested
before it can be used, stored further, or flown -- ahead of handing
the resulting retest scope to test-programme planning (sibling
e1003-test-programme leaf) and execution.

## Domain quick reference

- ECSS-E-ST-10-03C clause 4.6 covers four distinct retesting triggers,
  each with its own rule; treating them as one generic "retest if in
  doubt" check loses the specific evidence each one turns on.
- Design modification after qualification: a change made after an
  article's design was already qualified only demonstrates continued
  compliance if it did not touch the qualified envelope. A change that
  affects form, fit, function, or any previously verified qualified
  parameter forces requalification of the affected requirements; a
  change kept outside that envelope needs a documented engineering
  justification but no new test.
- Storage after a protoflight or acceptance test: flight hardware does
  not stay flight-ready indefinitely once accepted. If it was stored
  outside its qualified/specified storage conditions, or for longer
  than its qualified shelf life, its acceptance disposition can no
  longer be trusted and a retest is required before flight use; storage
  within both bounds needs no retest.
- Re-flown articles: hardware recovered and proposed for a second
  flight cannot be re-accepted on its prior flight record alone. It is
  first inspected for flight-induced damage or degradation; damage
  found routes to repair and requalification of the affected areas,
  while a clean inspection still requires a fresh acceptance-level
  retest before the next flight -- a reflown article is never simply
  "still accepted."
- Flight use of a qualification article: flying the article that was
  used to demonstrate qualification margin is only acceptable if that
  qualification testing did not consume damaging life/margin and left
  no damage; either finding disallows the article from flight outright.
  A clean qualification article is not flown as-is either -- it still
  needs an acceptance-level retest first, since qualification testing
  demonstrates design margin, not the specific article's workmanship.

## Workflow

1. Identify the retesting trigger that applies to the case in hand:
   design_modification, storage_after_test, reflown_article, or
   qualification_article_for_flight. Each trigger has its own required
   input evidence (see logic module docstrings) -- do not reuse another
   trigger's evidence fields.
2. For a design_modification case, capture whether the modification
   affects the qualified envelope. If yes, the outcome is
   requalification_required for the affected requirements; if no, the
   outcome is no_retest_required (still needs a documented engineering
   justification, tracked outside this leaf).
3. For a storage_after_test case, capture the storage duration, the
   qualified shelf life, and whether storage conditions stayed within
   spec. Conditions outside spec force retest_required regardless of
   duration; conditions within spec but duration exceeding the
   qualified shelf life also force retest_required; only duration
   within the shelf life and conditions within spec give
   no_retest_required.
4. For a reflown_article case, capture the post-flight inspection
   result. Damage found routes to repair_and_requalify; a clean
   inspection still routes to acceptance_retest_required, never to an
   automatic "still accepted."
5. For a qualification_article_for_flight case, capture whether the
   qualification testing consumed damaging life/margin and whether
   inspection found damage. Either condition routes to
   disallowed_for_flight; a clean article routes to
   acceptance_retest_required.
6. Build the disposition set for every case in the retesting review and
   confirm no case id from the intended review scope is missing --
   clause 4.6 applies per case, not on a sample.
7. Hand off every disposition that is not no_retest_required to
   test-programme planning (sibling e1003-test-programme leaf) as a
   required test activity before the article proceeds.

## Pitfalls

- Applying the design-modification rule to a reflown or qualification
  article (or vice versa) -- each trigger has a distinct evidence set
  and outcome vocabulary; they are not interchangeable.
- Treating a documented engineering justification as equivalent to a
  passed requalification when a design modification did affect the
  qualified envelope.
- Crediting a reflown article's prior acceptance instead of running a
  fresh acceptance-level retest after a clean post-flight inspection.
- Flying a qualification-model article straight off its qualification
  campaign without the acceptance-level retest it still needs even
  when undamaged and margin-clean.
- Closing the retesting review while a case id from the intended scope
  has no recorded disposition.

## Behavior contract (gate 3)

The per-trigger classification, dispatch, and review-completeness
logic is exercised by the gate 3 contract test:
scripts/test_e1003_retesting.py against
scripts/e1003_retesting_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_retesting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
