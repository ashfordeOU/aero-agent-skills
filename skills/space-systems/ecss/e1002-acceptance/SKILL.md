---
name: e1002-acceptance
description: "Use when running the acceptance stage of ECSS-E-ST-10-02C verification for a flight (or protoflight) article: gate the article on flight-standard workmanship/configuration eligibility, apply the acceptance-article rules distinguishing a dedicated acceptance test (prototype philosophy) from protoflight credit, guard against an acceptance test overstepping its qualified margin, disposition the workmanship/performance outcome, and close out the stage across a product set. Anchor: E-ST-10-02C clause 5.2.4.3. Trigger: acceptance stage, acceptance test, acceptance article, flight-standard workmanship, protoflight credit, overtest, acceptance review, e-st-10-02, ecss."
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
  tags: [ecss, e-st-10-02c, acceptance-stage, acceptance-article, workmanship, protoflight, verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification Acceptance Stage (space-systems/ecss/e1002-acceptance)

Use when the task is running the acceptance stage of ECSS-E-ST-10-02C
verification for a flight article: eligibility, test severity, and
workmanship/performance disposition, ahead of delivery or hand-over to
pre-launch verification (sibling e1002-pre-launch leaf).

## Domain quick reference

- ECSS-E-ST-10-02C clause 5.2.4.3 defines the acceptance stage: unlike
  qualification (sibling e1002-qualification leaf), which demonstrates
  design margin on a dedicated qualification model, acceptance
  verifies that the specific flight article is free of workmanship or
  manufacturing defects and meets its specified performance -- it does
  not re-prove the design.
- An acceptance article is only eligible for acceptance once it is
  built to the same flight-standard baseline (parts, materials,
  processes, configuration) that was qualified; a baseline mismatch
  blocks acceptance regardless of test result and routes to
  nonconformance or rebuild, not a waiver by test.
- The model philosophy (sibling e1002-models leaf: prototype vs
  protoflight) sets the acceptance-article rule: a prototype-philosophy
  flight model (FM) needs its own dedicated acceptance test, run at or
  below the qualification amplitude already demonstrated on the
  separate qualification model; a protoflight-philosophy article (PFM)
  is credited from its full-amplitude protoflight campaign instead of
  a second acceptance test.
- Driving a prototype-philosophy acceptance test above the qualified
  amplitude is an overtest: it demonstrates nothing new (the margin was
  already proven on the QM) and risks damaging or consuming life on the
  article that will fly, so it is flagged rather than treated as a more
  thorough pass.
- A clean acceptance disposition requires both no workmanship anomaly
  and performance within the specified acceptance criteria; either
  failure routes the article to nonconformance handling and re-test
  after rework, not a partial acceptance.

## Workflow

1. For each acceptance article, capture: model philosophy (prototype or
   protoflight), the article's as-built baseline vs the qualified
   baseline, the applied vs qualification test amplitude, and the
   workmanship/performance test result (anomaly detected, performance
   within spec).
2. Gate on flight-standard eligibility first: if the article's baseline
   does not match the qualified baseline, block acceptance and route to
   nonconformance/rebuild before considering any test result.
3. For a prototype-philosophy article, check the acceptance test
   amplitude against the qualification amplitude; flag an overtest if
   it was exceeded. A protoflight-philosophy article is exempt (its
   protoflight campaign is credited directly).
4. Disposition the workmanship/performance outcome: accepted only when
   eligible, not overtested, and free of anomaly with performance
   within spec; otherwise assign the specific blocking status
   (not-flight-standard, overtest, or failed workmanship/performance).
5. Build the disposition set for every article in the acceptance scope
   and confirm no article id from the intended set is missing --
   clause 5.2.4.3 closes the stage per article, not on a sample.
6. Close out the acceptance stage only when every article is
   dispositioned as accepted; otherwise list the open items with their
   blocking status for engineering disposition before the stage can
   close and verification proceeds to pre-launch (e1002-pre-launch).

## Pitfalls

- Accepting an article whose as-built configuration deviates from the
  qualified baseline because its test result looked clean -- the
  baseline mismatch is the actual defect.
- Driving a prototype-philosophy acceptance test to qualification-level
  amplitude "to be safe," consuming flight life for no added margin
  evidence.
- Treating a protoflight article's full-amplitude campaign as an
  overtest instead of the credited combined qualification/acceptance
  result it is by design.
- Closing the acceptance stage while one or more articles remain
  blocked or failed, instead of listing every open item.

## Behavior contract (gate 3)

The eligibility-gating, overtest-guard, disposition, and stage-closure
logic is exercised by the gate 3 contract test:
scripts/test_e1002_acceptance.py against
scripts/e1002_acceptance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
