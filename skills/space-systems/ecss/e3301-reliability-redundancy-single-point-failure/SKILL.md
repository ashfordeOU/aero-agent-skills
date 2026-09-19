---
name: e3301-reliability-redundancy-single-point-failure
description: "Evaluate the reliability and redundancy case of a mechanism against ECSS-E-ST-33-01C clause 4.2.5. Use when the task is showing both that a mission-critical mechanism reaches the reliability figure it was apportioned and that no single failure quietly carries the mission: building each functional block from its failure rate and redundancy scheme, combining simplex, active-parallel and cold-standby blocks over the mission duration, finding the blocks whose loss defeats a critical function with nothing behind them, holding every active element to the redundancy rule, and grading each single-point failure as eliminated, accepted against a written rationale, or still open. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-single-point-failure, mechanism-redundancy-scheme, active-element-redundancy, cold-standby-mechanism-reliability, mission-reliability-apportionment, spf-acceptance-rationale."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-reliability-redundancy-single-point-failure, mechanism-single-point-failure, mechanism-redundancy-scheme, active-element-redundancy, cold-standby-mechanism-reliability, mission-reliability-apportionment, spf-acceptance-rationale]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Reliability, Redundancy and Single-Point Failure (space-systems/ecss/e3301-reliability-redundancy-single-point-failure)

Use when the task is the reliability obligation of ECSS-E-ST-33-01C
clause 4.2.5 -- demonstrating the apportioned figure for a
mission-critical mechanism, and settling every failure mode that could
defeat it on its own.

## Domain quick reference

- The clause carries two obligations that are usually argued in
  different documents and have to close together. One is numerical:
  the mechanism reaches the reliability figure its function was
  apportioned. The other is structural: no single failure defeats a
  mission-critical function. A mechanism can pass the number and still
  fail the clause.
- A redundancy scheme is a modelling choice with consequences. A
  simplex block contributes the plain exponential survival of its
  failure rate. An active-parallel block survives while any one of its
  units does. A cold-standby block adds the unpowered spares brought in
  by a switch, and the switch is part of the model rather than an
  assumption -- a standby chain is only better than a parallel one
  while its switch is good.
- Failure rates arrive in FIT, one failure per billion operating hours,
  so the mission duration is what turns a rate into a probability. The
  chain is a series product: every block in the functional path has to
  survive, and adding a block can only lower the result.
- An active element -- anything that moves, latches, releases, switches
  or is commanded -- is held to a redundancy rule in its own right.
  Its dominant failure modes are wear, contamination and jamming rather
  than random electronics failure, so a low apportioned rate does not
  excuse carrying it single string.
- A single-point failure has exactly two admissible outcomes: it is
  eliminated by design, or it is formally accepted against a written
  rationale. There is no third. A ledger entry marked accepted with a
  blank or token rationale has not been accepted, and the honest
  reading is that it is still open.
- Reliability is a product of exponentials, so a case engineered to sit
  exactly on its requirement can evaluate a few units in the last place
  below it. The comparison absorbs that representation error; the
  requirement itself is never lowered to make a case close.

## Workflow

1. Write the functional chain as blocks. Each one declares a failure
   rate, a redundancy scheme with its unit count, whether it is an
   active element, and how critical its loss is. Reject an
   uncategorized block rather than defaulting it -- an unstated
   criticality is not a benign one.
2. Evaluate each block over the mission duration on its own scheme, and
   put the switch reliability into the standby blocks instead of
   assuming a perfect changeover.
3. Multiply the chain into a mechanism figure and compare it with the
   apportionment, absorbing representation error at the comparison
   only.
4. List the single-point failures: every block with one unit whose loss
   defeats a mission-critical function, plus every single-string active
   element the redundancy rule catches.
5. Resolve each entry to eliminated, accepted or open. Demand a
   rationale of substance behind an acceptance and demote a token one
   back to open.
6. Close only when the figure is met and the ledger has no open entry;
   otherwise report which of the two obligations failed, because they
   are repaired by different work.

## Pitfalls

- Closing the case on the number alone. The apportioned figure can be
  met by a chain that still has a single-string release device in it,
  and clause 4.2.5 is not satisfied by a reliability report that never
  enumerated the failure modes.
- Modelling a cold-standby chain with a perfect switch. The changeover
  is a real element with a real failure probability, and a standby pair
  modelled without it can be reported as better than an active pair
  when it is worse.
- Reading a low failure rate as a redundancy waiver for an active
  element. The rate describes random failures; jamming, wear debris and
  cold welding are not in it, which is exactly why the element rule is
  stated separately from the numerical one.
- Letting an acceptance stand on a sentence that repeats the failure
  mode instead of arguing it. An empty rationale converts a live
  single-point failure into a closed line item and removes it from
  every later review.
- Treating a mission-degrading block as harmless. It is outside the
  single-point failure list only because of its consequence, and its
  contribution to the series product is unchanged -- dropping it from
  the chain inflates the figure.
- Comparing the achieved figure with the requirement by bare
  arithmetic. A product of exponentials can land one unit in the last
  place under a requirement it was built to meet exactly, which reads
  as a failure on one platform and a pass on another.

## Behavior contract (gate 3)

Block validation, per-scheme reliability, the series chain, the
single-point failure list, the disposition ledger and the two-part
verdict are exercised by the gate 3 contract test:
scripts/test_e3301_reliability_redundancy_single_point_failure.py
against
scripts/e3301_reliability_redundancy_single_point_failure_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_reliability_redundancy_single_point_failure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
