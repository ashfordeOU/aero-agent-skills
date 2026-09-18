---
name: e2020-centralised-undervoltage-protection-redundancy
description: "Assess a centralised undervoltage protection that serves several current limiters for single point failure tolerance under clause 5.2.5.3.1 of ECSS-E-ST-20-20C. Use when one sensing and voting chain arms or trips the undervoltage protection of a whole distribution unit. Walk each redundancy stage as a k-of-n vote, remove one unit at a time, and test both directions: whether the surviving units still protect every limiter served, and whether one unit failing active trips the bus on its own. Report each loss path and each spurious path, and flag an architecture that serves a single limiter as outside the shared protection case. Trigger: ecss, e-st-20-20c, centralised-undervoltage-protection, undervoltage-protection-single-point-failure, undervoltage-voting-redundancy, spurious-undervoltage-trip-path, undervoltage-protection-cross-strapping, shared-undervoltage-sensing-chain."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e2020-centralised-undervoltage-protection-redundancy, centralised-undervoltage-protection, undervoltage-protection-single-point-failure, undervoltage-voting-redundancy, spurious-undervoltage-trip-path, undervoltage-protection-cross-strapping, shared-undervoltage-sensing-chain]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Centralised Undervoltage Protection Redundancy (space-systems/ecss/e2020-centralised-undervoltage-protection-redundancy)

Use when the task is clause 5.2.5.3.1 of ECSS-E-ST-20-20C: an undervoltage
protection shared by several current limiters has to survive any single point
failure. This leaf takes the architecture of the shared chain — sensing,
comparison, voting, trip distribution — and walks every unit failure through
it in both directions.

## Domain quick reference

- Centralising the protection is what creates the requirement. A limiter with
  its own undervoltage watchdog fails alone; one shared chain that arms or
  trips a whole distribution unit puts every limiter behind a single set of
  parts, so the clause asks that no one part can take the function down.
- The chain is a series of stages and the protection needs all of them. A
  limiter is protected only while every stage serving it works, so redundancy
  at the sensing stage buys nothing if the trip distribution behind it is a
  single driver.
- Each stage is a k-of-n vote and the two failure directions pull against each
  other. Losing a unit is survivable while at least k of the survivors remain,
  which pushes the vote down; a unit failing active reaches the output when a
  single active input satisfies the vote, which pushes the vote up. One of
  two, OR'd, tolerates a loss and trips spuriously on a single failure; two of
  two tolerates a spurious failure and loses the function on a single loss.
  Two of three is the smallest arrangement that clears both.
- A spurious trip is a real single point failure, not a nuisance. The
  undervoltage protection removes loads; a stuck comparator that asserts on a
  healthy bus switches off every limiter the stage serves, and the healthy
  stages downstream cannot tell that command from a genuine one.
- Cross-strapping and shared hardware are expressed by the same unit appearing
  in more than one stage, and the walk has to remove it from all of them at
  once. A unit that sits in both the sensing and the distribution stage is one
  failure, not two.
- Coverage is per limiter, not per architecture. A stage that serves a subset
  takes only that subset down, and a limiter no stage serves at all has no
  protection to make tolerant in the first place.

## Workflow

1. Validate the architecture: named limiters without duplicates, named stages
   with a non-empty unit set, a vote between one and the unit count, and a
   serves list drawn from the declared limiters.
2. Collect the distinct unit identifiers across every stage so shared hardware
   is counted once.
3. Establish the no-failure baseline: which limiters are protected when
   nothing has failed.
4. Walk the loss direction. Remove each unit from every stage it appears in,
   re-evaluate each stage's vote against its survivors, and record every
   limiter that drops out of the baseline.
5. Walk the spurious direction. For each unit, find the stages where a single
   active input satisfies the vote and record the limiters those stages serve.
6. Check scope and coverage: fewer than two served limiters is not the shared
   case the clause addresses, and a limiter no stage serves is its own
   finding.
7. Return the verdict with both point lists and the findings behind them; the
   architecture is tolerant only when both walks come back empty.

## Pitfalls

- Walking only the loss direction. Half the single point failures of a
  protection chain are spurious actuations, and an OR'd pair — the usual
  answer to "make it redundant" — is exactly the arrangement that passes the
  loss walk and fails the spurious one.
- Declaring the chain redundant because the sensing stage is triplicated. The
  weakest stage sets the answer, and the trip distribution is frequently the
  one left simplex.
- Treating a unit that appears in two stages as two independent items. It is
  one failure and it has to be removed from both stages together, otherwise a
  cross-strapped architecture grades better than it behaves.
- Reading a stage that serves a subset of limiters as harmless. It is a single
  point failure for the limiters it does serve, and the report has to name
  them rather than average them away.
- Assuming a two-of-two vote is redundancy. It is a series pair for the loss
  direction: either unit going quiet disables the protection entirely.
- Grading a dedicated protection against this clause without saying so. When
  the chain serves one limiter, the shared case does not apply, and the result
  is reported for information rather than passed off as compliance.

## Behavior contract (gate 3)

The architecture validation, distinct-unit collection, per-limiter stage
lookup, k-of-n survivor evaluation, loss walk, spurious-actuation walk,
subset-serving coverage, shared-case scope check and verdict are exercised by
the gate 3 contract test:
scripts/test_e2020_centralised_undervoltage_protection_redundancy.py against
scripts/e2020_centralised_undervoltage_protection_redundancy_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2020_centralised_undervoltage_protection_redundancy.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
