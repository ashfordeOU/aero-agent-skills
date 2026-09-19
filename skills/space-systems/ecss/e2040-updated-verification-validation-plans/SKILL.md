---
name: e2040-updated-verification-validation-plans
description: "Verify that the verification and validation plans were genuinely refreshed once the device architecture settled, as ECSS-E-ST-20-40C clause 5.3.3 requires: compare the architecture revision each plan cites against the current one, prove the plan's own revision actually moved rather than being re-dated, reconcile entries against the current requirement and block sets in both directions, and catch an entry left pointing at the block a requirement was moved away from. Use when plan updates are reported complete after architecture close. Trigger: ecss, e-st-20-electrical-scope, updated-verification-validation-plans, plan-cites-stale-architecture, plan-revision-did-not-move, entry-not-refreshed-after-reallocation, device-plan-entry-reconciliation."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-updated-verification-validation-plans, updated-verification-validation-plans, plan-cites-stale-architecture, plan-revision-did-not-move, entry-not-refreshed-after-reallocation, device-plan-entry-reconciliation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Updated Verification and Validation Plans (space-systems/ecss/e2040-updated-verification-validation-plans)

Use when the task is the refresh duty of ECSS-E-ST-20-40C clause 5.3.3 --
saying whether the verification and validation plans written before the
architecture existed have actually been brought up to the architecture
that was settled, rather than marked as updated.

## Domain quick reference

- "Updated" is a claim, not a status. Three independent pieces of
  evidence decide it: the architecture revision the plan cites, the
  plan's own revision, and the entries themselves. Any one of them alone
  can be true while the plan is stale.
- A plan citing an architecture revision the architecture has moved past
  is stale on its face, however recently its own revision was bumped.
- A plan whose own revision did not move while the architecture did was
  re-dated, not updated. This is the commonest way the clause is
  reported closed without the work being done.
- Reconciliation runs in both directions. A requirement with no entry is
  a hole; an entry for a requirement that no longer exists is an orphan
  that keeps a retired obligation alive in the campaign.
- An entry naming a retired block points at nothing. An entry whose
  requirement was REALLOCATED but whose block field never changed is
  worse: it still names a block that exists and is simply the wrong one,
  so nothing downstream detects it.
- Validation is a separate plan from verification and both are owed.
  Refreshing one and reporting the pair leaves the validation plan a
  phase behind, and nothing in the verification plan reveals that.
- The refresh ratio is entries touched over entries owed, so a target
  met exactly is met and the comparison absorbs representation error.

## Workflow

1. Resolve the settled architecture: its revision, the current block and
   requirement sets, and any reallocation of a requirement to a new
   block. Refuse a reallocation naming an unknown block or requirement.
2. Resolve each plan, refusing a repeated requirement, an unknown key or
   a non-boolean refresh flag, and refuse two plans of the same kind.
3. Report a plan kind that was not supplied at all.
4. Compare each plan's cited architecture revision against the current
   one, and prove its own revision moved past its baseline.
5. Reconcile entries against the requirement set in both directions, and
   report entries naming a retired block.
6. Report every entry still naming the block its requirement was moved
   away from, and every entry left with no method.
7. Compute the refresh ratio per plan and compare it against any target,
   absorbing representation error at the boundary.

## Pitfalls

- Trusting the plan's own revision. It moves when anyone edits anything,
  including the date on the cover, and says nothing about whether the
  architecture reached the entries.
- Reconciling in one direction only. Checking that every requirement has
  an entry leaves the orphan entries behind, and they keep a retired
  obligation alive all the way to the test campaign.
- Missing a reallocation. The entry names a real block, the trace
  resolves, and the article is verified in the wrong place.
- Refreshing verification and reporting the pair. The validation plan
  stays a phase behind and nothing in the verification plan reveals it.
- Comparing a refresh ratio against its target with a strict inequality.
  A two-of-two division landing on 1.0 can sit a unit in the last place
  below it and red a plan that refreshed every entry it owed.

## Behavior contract (gate 3)

The architecture resolution, revision ordering, plan resolution,
stale-citation and did-not-move detection, two-way entry reconciliation,
retired-block and reallocation detection and the refresh-target
comparison are exercised by the gate 3 contract test:
scripts/test_e2040_updated_verification_validation_plans.py against
scripts/e2040_updated_verification_validation_plans_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_updated_verification_validation_plans.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
