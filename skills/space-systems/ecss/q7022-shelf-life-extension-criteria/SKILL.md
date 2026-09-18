---
name: q7022-shelf-life-extension-criteria
description: "Assess whether the shelf life of a stored material may be extended under ECSS-Q-ST-70-22 and for how long: separate the criteria that refuse an extension outright — a non-extendable family, an incomplete storage record, exposure past its allowance, no covering manufacturer statement and no passed re-test, the extension count already used — from the caps that only shorten it, then grant the smaller of the per-step increment cap and the remaining total-life headroom and name which cap cut the request. Use when an expiring lot is reviewed. Trigger: ecss, q-st-70-22, shelf-life-extension-eligibility, shelf-life-extension-evidence-basis, shelf-life-increment-cap, shelf-life-total-life-ceiling, shelf-life-extension-count."
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
  tags: [ecss, q-st-70-22-limited-shelf-life-materials, q-st-70-22, q7022-shelf-life-extension-criteria, shelf-life-extension-eligibility, shelf-life-extension-evidence-basis, shelf-life-increment-cap, shelf-life-total-life-ceiling, shelf-life-extension-count]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Limited Shelf Life — Extension Criteria (space-systems/ecss/q7022-shelf-life-extension-criteria)

Use when the task is the life-extension clause of ECSS-Q-ST-70-22: an item is
approaching its date, somebody wants more time on it, and the question is
whether the evidence supports that and how much time it supports.

## Domain quick reference

- Two different kinds of rule are in play and they must not be run together. A
  blocking criterion answers "may this be extended at all" and its failure is a
  refusal. A cap answers "by how much" and its bite is a reduced grant. Mixing
  them either refuses requests that only needed trimming, or grants requests
  that had no basis at all.
- The evidence base is the heart of it. Either the manufacturer has stated a
  longer life covering the period being asked for, or the item has been
  re-tested and passed. Qualification data on its own describes the material as
  made, not this lot as stored, so it supports neither route by itself.
- A manufacturer statement that covers less time than the request is not
  partial support; for the requested period it is no support. The honest move
  is to ask for the period the statement does cover.
- Some families are not extendable on any evidence, because the property that
  degrades is not the property the available tests measure. No amount of
  re-testing changes that, so the family check runs first.
- Extensions accumulate. A per-step cap stops one heroic extension, and a
  total-life ceiling stops a series of modest ones from doubling the life by
  instalments. The count limit stops the paperwork treadmill independently of
  either.
- An item whose storage record is incomplete has no history to extend. The
  extension presumes the item was held as declared, and an unmonitored period
  is exactly the period that would have invalidated it.

## Workflow

1. Validate the request: identity and family present, original shelf life and
   requested days positive whole numbers, prior grants and counts non-negative,
   every evidence source from the known set.
2. Resolve the evidence basis: a manufacturer statement covering at least the
   requested days, else a re-test report marked passed, else none.
3. Run the blocking criteria — family extendable, storage record complete,
   exposure within allowance, evidence basis present, extension count below its
   ceiling — and collect every failure rather than stopping at the first.
4. Compute the per-step increment cap as a fraction of the original shelf life,
   floored to whole days.
5. Compute the total-life headroom left after the original life and everything
   already granted, floored at zero.
6. Grant the smallest of the request and the two caps, recording which cap cut
   it.
7. Close: refused when any blocking criterion failed or no days remain,
   granted-reduced when a cap bit, granted otherwise.

## Pitfalls

- Treating a cap breach as a refusal. The request was too long, not
  unsupported; the reviewer wants the number that is supportable.
- Accepting a manufacturer statement without checking the period it covers. A
  statement for ninety days does not underwrite a six-month extension.
- Letting qualification data stand in for a re-test. It characterises the
  material as manufactured and says nothing about this lot after storage.
- Stopping at the first unmet criterion. The requester needs the full list, or
  the request comes back having fixed one thing at a time.
- Counting extensions but not the days. Three modest extensions can pass a
  count limit and still double the life, which is what the total-life ceiling
  exists to catch.
- Extending an item whose storage record has a hole in it. The missing period
  is the one that would have decided the question.

## Behavior contract (gate 3)

The request validation, evidence-basis resolution, blocking-criteria set,
increment and total-life caps, cap precedence and the granted / granted-reduced
/ refused disposition are exercised by the gate 3 contract test:
scripts/test_q7022_shelf_life_extension_criteria.py against
scripts/q7022_shelf_life_extension_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7022_shelf_life_extension_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
