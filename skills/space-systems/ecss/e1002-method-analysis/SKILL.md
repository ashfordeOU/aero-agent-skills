---
name: e1002-method-analysis
description: "Use when determine which ECSS-E-ST-10-02C clause 5.2.2.3 analysis technique (worst-case, statistical, qualitative, classical calculation, or similarity) applies to a requirement being verified by analysis, validate the heritage conditions that must all hold before a case can close by similarity to a previously verified reference item -- verified reference item, design/manufacturing equivalence, and an enveloped operating environment -- check an analysis plan for the fields a closure review requires, and roll a set of analysis cases up into open/closed status. Trigger: ecss, e-st-10-02c, verification by analysis, verification by similarity, heritage, analysis technique selection, similarity validation conditions, environment envelope, analysis plan completeness."
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
  tags: [ecss, e-st-10-02c, verification-by-analysis, verification-by-similarity, heritage, analysis-technique]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Analysis Method Including Similarity (space-systems/ecss/e1002-method-analysis)

Use when the task is applying the analysis verification method of
ECSS-E-ST-10-02C clause 5.2.2.3 -- selecting the analysis technique
for a requirement, validating the heritage conditions required to
close a case by similarity to a previously verified reference item,
checking an analysis plan for completeness, and rolling a set of
analysis cases up into an open/closed status.

## Domain quick reference

- Clause 5.2.2.3 recognizes several analysis techniques: worst-case
  (bounding the requirement with the most severe credible combination
  of inputs), statistical (probabilistic treatment of a margin),
  qualitative (engineering-judgement argument where no numeric model
  applies), classical calculation (a direct analytical or numerical
  solution), and similarity (closing the requirement on the strength
  of a reference item already verified under equal or enveloping
  conditions). A case uses exactly one technique.
- Similarity is the strongest claim and carries the strictest
  conditions: the reference item must itself have been previously
  verified, the new item's design must be identical to the reference
  or every difference must be explicitly assessed, the manufacturing
  process must be equivalent, and every operating-environment
  parameter of the new item's application must be enveloped by (no
  more severe than) the environment the reference item was verified
  against. All four conditions must hold; any one unmet condition
  means the requirement cannot close by similarity alone.
- An analysis plan is not review-ready until it carries the
  requirement it verifies, the chosen technique, the input data
  sources the analysis draws on, the acceptance criteria the result is
  checked against, and who verified it; a similarity-technique plan
  additionally needs the specific reference item identifier.
- A set of analysis cases is not closed out until every case in it has
  an empty findings list; a case with any open finding (missing
  heritage condition, missing plan field) keeps the set open.

## Workflow

1. For each requirement to be verified by analysis, select the
   analysis technique from the case's evidence flags: a verified
   reference item takes precedence and drives selection of similarity;
   otherwise choose statistical, worst-case, or qualitative per the
   evidence available, defaulting to classical calculation.
2. When the technique is similarity, confirm the reference item was
   itself previously verified before treating it as heritage -- an
   unverified or unidentified reference item cannot support a
   similarity claim.
3. Confirm the new item's design is identical to the reference item,
   or that every design difference has been explicitly assessed;
   confirm the manufacturing process is equivalent. Do not accept a
   similarity claim on an unassessed design difference or a
   non-equivalent process.
4. Compare every operating-environment parameter of the new item's
   application against the reference item's verified environment;
   any parameter exceeding the reference value breaks the envelope and
   the difference must be justified or retired before the case closes.
5. Before a case is scheduled for closure review, check its analysis
   plan for the required fields (requirement, technique, input data
   sources, acceptance criteria, verified-by, and reference item for a
   similarity plan); an incomplete plan is not ready for review.
6. Roll the case set up into open/closed counts; a case with any
   unresolved heritage or plan finding stays open, and the set as a
   whole is not verified until every case is closed.

## Pitfalls

- Treating a design difference as automatically disqualifying --
  clause 5.2.2.3 only requires the difference to be explicitly
  assessed, not absent; an unassessed difference is the finding, not
  the difference itself.
- Accepting similarity against a reference item that was never itself
  verified -- heritage only transfers from a reference item with its
  own verification record, not from an item assumed to be fine because
  it flew before.
- Comparing only the headline environment parameter (e.g. peak
  temperature) and skipping the rest -- every parameter the new
  application is exposed to must be checked against the reference
  envelope; one unchecked parameter can exceed it while the headline
  parameter still passes.
- Reading an analysis case as verified because the numeric result
  looks right while the plan itself is incomplete -- a missing
  acceptance criterion or verifier means the case is not yet
  reviewable, independent of whether the underlying analysis is sound.

## Behavior contract (gate 3)

The technique-selection, similarity heritage-validation, environment-
envelope, plan-completeness, and case roll-up logic is exercised by
the gate 3 contract test: scripts/test_e1002_method_analysis.py
against scripts/e1002_method_analysis_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e1002_method_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
