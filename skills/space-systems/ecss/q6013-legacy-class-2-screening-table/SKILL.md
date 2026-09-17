---
name: q6013-legacy-class-2-screening-table
description: "Assess a legacy screening run against the ECSS-Q-ST-60-13C Table 8-13 test list. Use when an intermediate-assurance lot of legacy commercial active parts has been screened and the run has to become a screened-or-reject verdict: walk the sequence in order carrying survivors from each step into the next, refuse a declared population that does not follow from the previous step's rejects, hold a step that tested a sample instead of the whole population, take the burn-in percent defective on the devices that entered, and compare cumulative attrition and the surviving quantity with their cap and the order to be delivered. Trigger: ecss, q-st-60-13c-table-8-13, legacy-class-2-screening-sequence, screening-hundred-percent-coverage, screening-population-chain, legacy-class-2-burn-in-pda, screening-cumulative-attrition, screened-deliverable-shortfall."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-legacy-class-2-screening-table, q-st-60-13c-table-8-13, legacy-class-2-screening-sequence, screening-hundred-percent-coverage, screening-population-chain, legacy-class-2-burn-in-pda, screening-cumulative-attrition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial Parts — Legacy Class 2 Screening Table (space-systems/ecss/q6013-legacy-class-2-screening-table)

Use when the task is the legacy screening test list of ECSS-Q-ST-60-13C
Table 8-13 — taking the steps, their order and their limits as the table sets
them for an active part at the intermediate assurance class and turning an
executed screening run on one purchased lot into a screened-or-reject
verdict.

## Domain quick reference

- Screening is a hundred-percent operation, not a sampling plan. A step run
  on forty of four hundred devices has not screened the lot; the other three
  hundred and sixty ship carrying exactly the defect the step exists to find.
- Screening is a chain. The devices entering a step are the devices that
  survived the step before it, so a declared entering population that does
  not follow from the previous step's rejects is an arithmetic error in the
  record and not a number to reconcile downstream.
- Order is part of the test. Each step is placed to precipitate a failure
  mechanism the next step can then detect, so a step run out of sequence has
  not done the job the sequence was built around.
- The burn-in rate is taken on the devices that entered burn-in, not on the
  devices that came out of it. A denominator built from survivors lets a lot
  improve its rate by failing more units, which inverts the whole point.
- Attrition across the sequence is its own signal. A lot that survives every
  individual limit while losing a tenth of itself overall is reporting on the
  build rather than on the screen, and the cumulative figure catches it.
- A screened lot still has to fill the order. Screening consumes devices, so
  a run that ends clean but short of the delivered quantity is reported as a
  shortfall rather than passed and discovered at delivery.

## Workflow

1. Walk the declared steps in order from the starting lot, carrying the
   surviving population forward. Refuse a step outside the sequence, a step
   that appears twice, more rejects than devices tested, or a declared
   entering population that contradicts the previous step's survivors.
2. Compare each step's devices tested with the population entering it and
   record the untested remainder rather than accepting the run as a sample.
3. Check the sequence order and name the first step that breaks it; name the
   steps the run never performed rather than reporting a bare shortfall.
4. Take the burn-in percent defective on the entered population and compare
   it with the allowance, absorbing representation error at the boundary with
   a named tolerance rather than by relaxing the allowance.
5. Compute the cumulative attrition from the starting lot to the survivors
   and compare it with the cap.
6. Compare the surviving population with the quantity to be delivered and
   hold the run when any single check rejects, rather than averaging the
   steps into one rate that a clean step can carry.

## Pitfalls

- Reading a large sample as full coverage. Sample size is irrelevant to a
  hundred-percent step; the untested remainder is the finding.
- Restarting the population at the lot size after every step. The chain then
  hides the devices already removed, and the attrition figure comes out low
  exactly when the lot is worst.
- Dividing burn-in failures by the surviving devices. The rate falls as the
  lot gets worse, and a bad build reports cleaner than a good one.
- Accepting an out-of-order run because every step was eventually performed.
  The sequence is the test, and a step that ran before its precipitating
  stress was applied has measured nothing the stress would have exposed.
- Widening a limit to pass an exact-equality case. A rate landing exactly on
  its allowance is a representation question handled by the tolerance inside
  the comparison; the declared allowance stays as specified.

## Behavior contract (gate 3)

The step validation and hundred-percent coverage rule, the population chain
and its declared-entering check, the sequence order, the burn-in percent
defective on the entered population, cumulative attrition against its cap,
the deliverable shortfall and the overall screened-or-reject disposition are
exercised by the gate 3 contract test:
scripts/test_q6013_legacy_class_2_screening_table.py against
scripts/q6013_legacy_class_2_screening_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_legacy_class_2_screening_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
