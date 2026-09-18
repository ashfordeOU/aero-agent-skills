---
name: q7080-part-acceptance
description: "Derive the acceptance case for a lot of additively manufactured parts, class by class. Use when a build lot is presented for acceptance under ECSS-Q-ST-70-80C: read the density, porosity and surface limits the part class sets, confirm the mandatory screens that class owes were actually performed, size the sampling plan from the protection demanded rather than a rule of thumb -- the smallest sample whose exact hypergeometric chance of accepting a lot at the limiting quality stays under the tolerated consumer risk -- then rule on the lot against the findings observed. Trigger: ecss, q-st-70-80-additive-manufacturing-scope, am-part-acceptance, part-class-acceptance-limits, am-lot-sampling-plan, hypergeometric-consumer-risk, limiting-quality-level, mandatory-am-screening."
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
  tags: [ecss, q-st-70-80-additive-manufacturing-scope, q7080-part-acceptance, am-part-acceptance, part-class-acceptance-limits, am-lot-sampling-plan, hypergeometric-consumer-risk, limiting-quality-level, mandatory-am-screening]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Part Acceptance (space-systems/ecss/q7080-part-acceptance)

Use when the task is the acceptance step of ECSS-Q-ST-70-80C on a lot
of built parts -- reading the limits the part class sets, confirming
the screens that class owes, and deciding how much of the lot has to be
examined before the lot as a whole can be accepted.

## Domain quick reference

- Acceptance has two halves. The attribute half asks whether a part
  meets the density, porosity and surface limits of its class. The lot
  half asks how many parts are examined at all, how many findings the
  plan tolerates, and what a passing lot proves about the parts nobody
  looked at. Both have to close before the lot is accepted.
- A sampling plan is not a discount on inspection. It is a stated
  probability of accepting a lot that carries a given share of
  non-conforming parts, so the honest way to size one is backwards:
  name the limiting quality the project refuses to accept, name the
  risk it will tolerate of accepting it anyway, and take the smallest
  sample that holds that risk.
- Drawing parts from a finite lot happens without replacement, so the
  acceptance probability is hypergeometric and can be summed exactly.
  The binomial approximation that treats the lot as infinite is
  optimistic on exactly the small lots additive manufacturing produces.
- Acceptance probability falls as the sample grows, which is why the
  smallest protective sample is found by bisection rather than by
  scanning, and why a sample that protects a lot of one hundred also
  protects a lot of five hundred at barely a larger size. Protection
  tracks the share of bad parts, not the headcount.
- An acceptance number is a promise to ship a known finding. If it is
  at least the number of bad parts a limiting lot carries, no sample
  size makes the plan protective -- not even examining every part --
  and the only fix is a smaller acceptance number.
- The most demanding class is not sampled at all. Where an escape is
  not survivable, every part is examined and the acceptance number is
  zero, and the sampling machinery is simply not the instrument.
- An attribute that was never measured is open, not passed. An empty
  field carries no information about conformance in either direction,
  and a lot closed on missing data is closed on an assumption.

## Workflow

1. Declare the part class and the lot size. Reject an uncategorized
   part rather than defaulting it, because the limits, the screens and
   the plan all hang off the class.
2. Where the class is examined in full, take the whole lot and stop
   sizing; the plan is the inspection.
3. Otherwise take the limiting quality and the tolerated consumer risk
   for the class, count the bad parts a limiting lot carries, and find
   the smallest sample whose acceptance probability stays under the
   risk. Floor it at the practical class minimum.
4. Where no sample can reach the protection, say so and name the cause
   -- the acceptance number -- rather than quietly returning the lot
   size.
5. Evaluate the attributes of the examined parts against the class
   limits, and list every attribute that was not measured as open.
6. Confirm the mandatory screens for the class were performed, and
   close with an acceptance verdict that names each reason: findings
   beyond the acceptance number, a non-conforming attribute, a missing
   screen, or a plan that never was protective.

## Pitfalls

- Choosing a sample size first and computing its protection afterwards,
  if at all. A round fraction of the lot has no stated consumer risk,
  and the plans that feel generous on small lots are the least
  protective ones there.
- Using a binomial model on a small lot. It assumes sampling with
  replacement from an infinite population, so it overstates the chance
  of catching a bad part in exactly the lot sizes a build plate
  produces.
- Reading a passing lot as evidence about the parts that were never
  examined. It is evidence about the lot at a stated confidence, and
  the strength of that evidence is the consumer risk, not the pass.
- Setting an acceptance number above zero on a class whose escapes
  matter. It tolerates a known finding, and on a small lot it can make
  protection unreachable at any sample size, which shows up as a plan
  that never goes protective however much is inspected.
- Treating a mandatory screen as satisfied because a sample was taken.
  Screens apply to every part of the class, so a sampling plan does not
  reduce them, and a screen that was skipped is a gap regardless of
  what the sample found.
- Comparing an acceptance probability with the tolerated risk by bare
  arithmetic. The probability is a ratio of large integers, so a plan
  meant to sit exactly on the limit can land a few units in the last
  place above it; the comparison absorbs that representation error
  while the risk limit stays untouched.

## Behavior contract (gate 3)

The hypergeometric acceptance probability, limiting-quality count,
protective sample search, class plans, attribute limits, screening gap
and the lot verdict are exercised by the gate 3 contract test:
scripts/test_q7080_part_acceptance.py against
scripts/q7080_part_acceptance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7080_part_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
