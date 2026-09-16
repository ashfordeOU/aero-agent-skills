---
name: e2008-sca-acceptance-testing-general
description: "Use when an SCA acceptance matrix, lot traveller set or coupon allocation has to be assessed. Evaluate whether the solar cell assembly acceptance activity set of clause 6.3.1 of ECSS-E-ST-20-08C reaches both populations it owes: the assemblies being delivered and the assemblies consumed by the qualification campaign. Expand the owed activities over every article, list what each article has no record for, separate an unrun activity from a recorded failure, measure coverage per population, catch a population exempted from acceptance testing wholesale, and return one lot verdict with ranked findings. Trigger: ecss, e-st-20-08c, sca-acceptance-testing-general, sca-delivery-article-acceptance, sca-qualification-article-acceptance, sca-acceptance-population-coverage, sca-lot-acceptance-verdict, sca-article-acceptance-record."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-acceptance-testing-general, e-st-20-08c, sca-acceptance-testing-general, sca-delivery-article-acceptance, sca-qualification-article-acceptance, sca-acceptance-population-coverage, sca-lot-acceptance-verdict, sca-article-acceptance-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Acceptance Testing, General (space-systems/ecss/e2008-sca-acceptance-testing-general)

Use when the task is clause 6.3.1 of ECSS-E-ST-20-08C: acceptance tests are
applied to the cell assemblies being delivered and to the cell assemblies
used for qualification. This leaf grades a lot record on whether both
populations carry the acceptance activity set, article by article.

## Domain quick reference

- The second population is the whole point of the clause. A qualification
  article is easy to read as exempt — it is not being shipped, so acceptance
  looks like somebody else's obligation. It is the reverse: a qualification
  result only means something if the article it was produced on was itself a
  sound assembly.
- An unaccepted coupon that fails a thermal cycle has told nobody anything.
  The result cannot separate a process that does not hold from a coupon that
  was defective before the campaign touched it, and the campaign is repeated.
- Exemption is a population-level defect, not an article-level one. One
  coupon with a thin record is a traveller problem; every coupon with an
  empty record is a decision somebody made, and it is reported as its own
  finding rather than as a run of individually incomplete articles.
- Absence, non-execution and failure are three different states. No record
  at all is the worst of them, because it cannot be dispositioned: nobody
  knows whether the activity was skipped, lost or never scheduled. An
  activity recorded as not yet run is a schedule item. A recorded failure is
  known and can be dispositioned.
- Coverage is reported twice. The article share says how many assemblies are
  clear; the activity share says how much of the owed work the population
  carries at all. A population can look thinly covered on the first number
  and be wholly untested on the second.
- A dispositioned failure is a project position, not a default. Whether a
  failed article leaves the lot open is read from policy, because both
  answers are legitimate and the wrong one silently accepts hardware.

## Workflow

1. Validate each article: a unique identifier, one of the two populations,
   and acceptance records naming only activities this clause owes. Refuse an
   activity outside the acceptance set rather than counting it as coverage.
2. Grade the article against the owed activity set: what has no record, what
   is recorded as not run, what failed and what passed.
3. Rank the article verdict — absent record first, then unrun, then failed —
   so the lot report names the root cause before the consequence.
4. Summarise each population: how many articles it holds, how many are
   clear, and what share of the owed activity it carries.
5. Detect a population present in the lot whose articles carry no acceptance
   work at all, and report it as an exemption.
6. Compare each population's coverage with the policy minimum, absorbing
   floating-point representation error at the boundary with a named relative
   tolerance rather than by moving the minimum.
7. Report the lot: articles grouped by verdict, both population summaries,
   the exempted populations and every finding in rank order.

## Pitfalls

- Running the acceptance matrix over the delivery lot only. The qualification
  articles are inside the clause, and leaving them out is the single defect
  this leaf exists to catch.
- Reading an empty acceptance record as a pass. An article with no record has
  not been shown sound; it has been shown undocumented.
- Collapsing absence into failure. They are dispositioned by different people
  through different paperwork, so the verdict keeps them apart.
- Judging the lot on delivery coverage alone. A lot can be fully covered on
  the shipped assemblies and carry a qualification population nobody tested,
  which is exactly the state the clause forbids.
- Assuming a failed article closes the lot. Whether a dispositioned failure
  is carried is a project position read from policy, and assuming either
  answer produces a verdict the project did not agree to.
- Judging a coverage share that lands exactly on its policy minimum by bare
  arithmetic. The share is a ratio of two counts and the minimum is a round
  fraction, so a lot meant to sit on the minimum can land a few units in the
  last place below it; the comparison absorbs that while the minimum stays
  as declared.

## Behavior contract (gate 3)

The article validation, the owed-activity expansion, the ranked article
verdict, the per-population summaries, the wholesale-exemption detector and
the rolled-up lot verdict are exercised by the gate 3 contract test:
scripts/test_e2008_sca_acceptance_testing_general.py against
scripts/e2008_sca_acceptance_testing_general_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_acceptance_testing_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
