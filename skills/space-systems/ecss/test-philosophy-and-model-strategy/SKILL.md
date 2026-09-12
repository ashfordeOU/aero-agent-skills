---
name: test-philosophy-and-model-strategy
description: "Use when determine the structural model philosophy and test campaign
  for a space structure under ECSS-E-ST-32C clauses 4.6.3.1–4.6.3.6: categorize
  each hardware unit as a development article, qualification article, or flight
  article; select which test phases (development, qualification, acceptance) apply;
  choose the qualification strategy (prototype-plus-flight-model, proto-flight, or
  qualification-model-plus-flight-model) based on unit count and risk level; verify
  that test levels meet required margins and that proto-flight qualification test
  durations are appropriately reduced; and assess whether similarity to a qualified
  reference can substitute dedicated qualification testing. Trigger: ecss,
  e-st-32-structures-scope, model-philosophy, test-philosophy, qualification-test,
  acceptance-test, proto-flight-model, structural-model-strategy."
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
  tags: [ecss, e-st-32-structures-scope, model-philosophy, test-philosophy, qualification-test, acceptance-test, proto-flight-model, structural-model-strategy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Test Philosophy and Model Strategy (space-systems/ecss/test-philosophy-and-model-strategy)

Use when the task is to determine the structural model strategy and test campaign
philosophy for a space structure programme under ECSS-E-ST-32C clauses
4.6.3.1–4.6.3.6 — selecting which model types to build, what test phases each
article must complete, and verifying that test levels and durations are consistent
with qualification and acceptance rules.

## Domain quick reference

- E-ST-32C clauses 4.6.3.1–4.6.3.6 organise structural verification around three
  test phases. **Development testing** is performed early on non-flight articles to
  reduce design risk and establish structural margins; it is not contractually
  required at specific levels and its results inform the design rather than
  demonstrating compliance. **Qualification testing** demonstrates that the design
  meets all requirements with margin, using a dedicated article that is not
  subsequently flown. **Acceptance testing** screens each flight unit for
  workmanship defects at levels below the qualification test, ensuring the flight
  unit is not fatigue-penalised by re-qualification loading.
- Each hardware article belongs to exactly one category: a **development article**
  (Prototype Model — PTM; Structural Thermal Model — STM) supports development
  testing only and is not flown. A **qualification article** (Qualification Model —
  QM) undergoes qualification testing only. A **flight article** (Flight Model —
  FM; Proto-Flight Model — PFM) is the unit that is flown; an FM undergoes
  acceptance testing, while a PFM undergoes both a qualification test (at
  qualification levels but with reduced duration) and an acceptance test before
  being accepted for flight.
- Three qualification strategies are available depending on programme context.
  The **prototype-plus-flight-model** strategy (PTM + FM) uses a separate
  non-flight prototype to carry development risk, followed by an FM at acceptance
  levels only. The **proto-flight** strategy (PFM) is chosen when only one unit
  will be built or when schedule precludes a separate QM; the single unit is
  qualified then accepted and subsequently flown. The
  **qualification-model-plus-flight-model** strategy (QM + FM) is preferred when
  multiple flight units will be produced, amortising the qualification test cost.
- **Qualification by similarity** allows a candidate item to inherit qualification
  status from a previously qualified reference item when the design, materials,
  manufacturing process, and target environment are no more demanding than those
  of the qualified reference. Any difference in design version, material
  specification, manufacturing process, or target environment exceeding the
  reference qualification environment invalidates the similarity claim.

## Workflow

1. Identify every hardware article in the verification programme and categorize
   it as a development article (PTM or STM), a qualification article (QM), or a
   flight article (FM or PFM). Reject an unrecognized article type before it
   enters the campaign plan.
2. Determine the required test phases for each article: development articles
   require development testing only; the QM requires qualification testing only;
   an FM requires acceptance testing only; a PFM requires both a qualification
   test and a subsequent acceptance test. Flag any proposed test phase that is not
   required for the article type.
3. Select the qualification strategy for the programme based on the number of
   planned flight units and the development risk level. Use
   qualification-model-plus-flight-model for more than one flight unit. For a
   single flight unit, use proto-flight when schedule constrains the programme or
   risk is low; use prototype-plus-flight-model when risk is high and a dedicated
   development article is warranted.
4. For each qualification test record, verify that the test level is at or above
   the minimum required qualification level (which incorporates the required
   margin over the specification). For each acceptance test record, verify that
   the test level is strictly below the qualification test level applied to that
   design, ensuring the flight unit is not loaded to qualification severity.
5. For any PFM qualification test, verify that the test duration per axis is less
   than the equivalent QM reference duration (it is a reduced-duration test) and
   is not so short that it falls below a practicable minimum fraction of the QM
   duration.
6. For each item proposed for qualification by similarity, confirm that the
   reference item is already qualified, that design version, material
   specification, and manufacturing process match, and that no component of the
   target environment exceeds the reference qualification environment. Flag each
   failing criterion as a finding; all findings must be resolved before similarity
   is accepted.
7. Aggregate findings across all articles and test records. A programme test
   campaign is not compliant until every article has its required phases
   completed, every test level is valid, and every similarity claim is fully
   substantiated.

## Pitfalls

- Running an FM acceptance test at the qualification test level — this is not
  conservative; it fatigue-penalises the flight unit and voids the distinction
  between qualification and acceptance testing.
- Proposing a PFM strategy for a multi-unit programme — when multiple flight
  units are planned, the qualification-model-plus-flight-model strategy amortises
  the qualification cost and leaves each FM exposed only to acceptance loading.
- Treating a development test result as qualification evidence — development
  testing is exploratory and not conducted at contractually fixed levels or
  durations; it cannot substitute for a formal qualification test.
- Claiming similarity without checking every criterion — a match on design
  version alone is insufficient; material specification, manufacturing process,
  and environment must each be verified against the qualified reference.
- Applying the full QM duration to a PFM qualification test — the reduced
  duration is a defining characteristic of the proto-flight approach; a PFM test
  run at full QM duration is effectively a QM test and the programme model
  strategy should be reconsidered.

## Behavior contract (gate 3)

The model categorization, test-phase assignment, qualification-strategy
selection, test-level validation, PFM duration check, and similarity assessment
logic is exercised by the gate 3 contract test:
`scripts/test_test_philosophy_and_model_strategy.py` against
`scripts/test_philosophy_and_model_strategy_logic.py` (stdlib unittest,
offline). Run:

```
python3 scripts/test_test_philosophy_and_model_strategy.py
```

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
