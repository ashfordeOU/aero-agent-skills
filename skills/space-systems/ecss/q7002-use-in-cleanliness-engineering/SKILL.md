---
name: q7002-use-in-cleanliness-engineering
description: "Convert ECSS-Q-ST-70-02C outgassing screening data into contributions to a molecular deposition budget under the contamination control practice of ECSS-Q-ST-70-01C. Use when a sensitive surface holds an areal allocation and each exposed material has a condensable screening figure and an exposed mass. Refuses a record that presents a screening percentage as an outgassing rate, forms a bounding source term, applies a pre-flight bakeout credit only against a bakeout on record, transports each source to the receiver through a declared fraction, sums the contributions and names the dominant one. Trigger: ecss, q-st-70-01, q-st-70-02, molecular-deposition-budget, cvcm-bounding-source-term, contamination-transport-fraction, bakeout-credit-reference, dominant-contamination-contributor."
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
  tags: [ecss, q-st-70-materials-outgassing-scope, q7002-use-in-cleanliness-engineering, molecular-deposition-budget, cvcm-bounding-source-term, contamination-transport-fraction, bakeout-credit-reference, dominant-contamination-contributor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening — Use in Cleanliness Engineering (space-systems/ecss/q7002-use-in-cleanliness-engineering)

Use when the task is carrying ECSS-Q-ST-70-02C screening results into
the contamination control work of ECSS-Q-ST-70-01C — turning condensable
percentages into deposition contributions on a sensitive surface and
grading their sum against the allocation that surface holds.

## Domain quick reference

- The condensable screening figure is a bound, not a rate. It is the
  fraction of a small specimen that condensed on a cold plate during one
  fixed bake, in one geometry, over one day. Nothing in it is per second
  and nothing in it is per steradian, so it enters a budget only as a
  bounding source term with a transport fraction declared beside it.
  A record that offers it as a rate is refused rather than converted.
- The source term is that fraction of the mass actually exposed to the
  vacuum path, not of the part. A connector backshell filled with
  potting contributes the potting it exposes; the metal around it
  contributes nothing and inflates the budget if it is weighed in.
- A pre-flight bakeout can be credited against the source term, and the
  credit needs the bakeout on record. An uncited credit is an assumption
  wearing a number, and it is the assumption that survives into the next
  programme when the budget is reused. A credit is also bounded: no
  bakeout removes everything.
- What lands on the receiver is the source times the fraction that
  reaches it — line of sight, geometry, receiver temperature and
  residence once it arrives, folded into one declared number. Keeping it
  as one declared number is what makes the budget auditable: a reviewer
  can argue with 0.01, and cannot argue with an undocumented chain of
  factors.
- Contributions add, and the sum is compared with the allocation. The
  ranking matters as much as the total, because the dominant contributor
  is the one worth re-baking, re-testing or moving, and it is rarely the
  material with the worst screening figure.
- A figure from a run that does not compare with baseline screening data
  can still be the best available, but it has to say so. A budget built
  from a mixture of bases with nothing marking which is which cannot be
  reviewed at all.

## Workflow

1. Validate each contributor: identifier, basis, condensable percentage
   between zero and a hundred, non-negative exposed mass, and a
   transport fraction in the unit interval. Refuse any basis other than
   a screening bound.
2. Form the bounding source term as the condensable percentage of the
   exposed mass.
3. Resolve the bakeout credit: apply it only when a bakeout reference
   stands behind it, raise a finding and drop the credit when it does
   not, and raise a separate finding when a bakeout is on record with no
   credit taken so the omission is deliberate rather than forgotten.
4. Raise a finding for a non-baseline screening figure used without a
   note saying what the run was.
5. Transport each source term to the receiver: the credited source times
   the declared fraction, converted to micrograms, over the receiver
   area.
6. Sum the contributions and compare with the allocation, absorbing
   representation error at the boundary with a named tolerance rather
   than by widening the allocation.
7. Rank the contributors by deposit, name the dominant one, and report
   the total, the margin, the utilization of the allocation and every
   finding.

## Pitfalls

- Multiplying a screening percentage by a mission duration. The figure
  has no time in it, so the product is an arbitrary number that grows
  with the length of the mission and means nothing at any length.
- Weighing the whole part into the source term. The exposed mass is what
  faces the vacuum path, and using part mass instead can inflate a
  contribution by an order of magnitude and send the programme re-baking
  the wrong item.
- Taking a bakeout credit on the strength of a plan. A bakeout that was
  planned and a bakeout that was performed and recorded are different
  inputs, and only one of them removed any mass.
- Hiding the transport chain inside the source term. A single combined
  number cannot be reviewed, and the next programme inherits it without
  the geometry it was derived for.
- Reporting only the total. Two budgets at the same total, one with a
  single dominant contributor and one spread evenly, need entirely
  different responses.

## Behavior contract (gate 3)

The basis refusal, source-term formation, bakeout-credit rule, transport
to an areal deposit, budget summation against an allocation with
tolerance, and contributor ranking are exercised by the gate 3 contract
test: scripts/test_q7002_use_in_cleanliness_engineering.py against
scripts/q7002_use_in_cleanliness_engineering_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7002_use_in_cleanliness_engineering.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
