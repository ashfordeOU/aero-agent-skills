---
name: q20-gse-production
description: "Evaluate the production of a ground support equipment item under ECSS-Q-ST-20C clause 5.8.3: grade each bought-in lot on supplier approval state, incoming inspection, conformity evidence and lot traceability, apply the surveillance a conditionally approved supplier owes, replay the manufacturing, assembly and integration operations in sequence against process qualification and operator certification validity, check every mandatory inspection point for completion and the right witness, and return released, released-with-actions or held. Use when a GSE build is up for release. Trigger: ecss, q-st-20c-clause-5-8-3, gse-procurement-assurance, gse-supplier-surveillance, gse-mandatory-inspection-point, gse-process-qualification-validity, gse-build-release-verdict."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-gse-production, gse-procurement-assurance, gse-supplier-surveillance, gse-mandatory-inspection-point, gse-process-qualification-validity, gse-build-release-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS GSE Production Assurance (space-systems/ecss/q20-gse-production)

Use when the task is the clause 5.8.3 quality assurance of ground support
equipment production in ECSS-Q-ST-20C: parts have been bought in, the item has
been manufactured, assembled and integrated, and the question is whether it may
be released to the people who will put flight hardware on it.

## Domain quick reference

- Procurement assurance is four separate questions about one lot: the approval
  state of the supplier, the incoming inspection result, whether conformity
  evidence arrived, and whether the lot can be traced back to a manufacturing
  lot at all. Any of them can stop the lot on its own.
- A conditionally approved supplier is not a slightly worse approved supplier.
  The approval was granted against an additional measure — surveillance at
  source, or a widened incoming inspection — and a lot that skipped it was
  bought outside the approval.
- An inspection still running is different from one that rejected. Pending is
  an action the build carries; rejected is a lot that does not go into the
  item.
- The route is a sequence. An operation performed while the one ahead of it is
  still open leaves an unverified state underneath finished work, and no later
  inspection can see back into it.
- A process qualification and an operator certification are dated permissions.
  Work done after either lapsed was done without the authority the route
  assumed, whatever the result looks like.
- A mandatory inspection point is a stop, not a note. An operation signed off
  past an open point is the defect the point existed to catch, and a point
  witnessed by the wrong function is not witnessed.

## Workflow

1. Grade every procurement lot on its four questions, refusing a lot entered
   twice, and separate a pending inspection from a rejected one.
2. Raise a conditionally approved supplier with no surveillance applied as its
   own blocking finding rather than folding it into the approval state.
3. Validate the operation set: unique identifiers, unique sequence numbers, and
   an ordering taken from the sequence rather than from the order the records
   happened to arrive in.
4. Replay the operations in sequence, raising an operation completed past an
   open predecessor, a lapsed process qualification and a lapsed operator
   certification as three different findings.
5. Check each mandatory inspection point against its operation: a point on an
   operation that is not in the build, an operation completed past an open
   point, and a point witnessed by the wrong function all block; a point still
   open on an unstarted operation is an action.
6. Report the completion fraction of the inspection points, comparing it with a
   required value through a named tolerance where one is set.
7. Return the release verdict over the combined blocking and action sets.

## Pitfalls

- Reading supplier approval as the whole procurement check. An approved
  supplier still ships a lot that fails incoming inspection or arrives with no
  traceability.
- Buying from a conditionally approved supplier on the strength of the
  approval. The condition is the approval; without it applied, the lot is
  outside it.
- Sorting the route by the order the records were entered. The sequence number
  is the route, and a set sorted any other way finds sequence breaks that are
  not there and misses ones that are.
- Accepting work done on a lapsed qualification because the result looks right.
  The qualification is what makes the result evidence rather than opinion.
- Counting a witnessed inspection point without checking who witnessed it. A
  customer-mandated point signed by the supplier's own quality function is an
  unwitnessed point.
- Holding a build for an action. A lot still in incoming inspection and an
  operation not yet started are things the release carries forward; a rejected
  lot and a bypassed inspection point are not.

## Behavior contract (gate 3)

The procurement lot grading, conditional-supplier surveillance rule, operation
set validation and ordered replay, process qualification and operator
certification validity, mandatory inspection point and witness checks,
completion fraction and the release verdict are exercised by the gate 3
contract test: scripts/test_q20_gse_production.py against
scripts/q20_gse_production_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_gse_production.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
