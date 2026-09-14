---
name: e2008-coverglass-clause-purpose
description: "Use when a coverglass procurement or qualification plan has to be held against the generic rules this clause opens. Scope the generic coverglass rules of ECSS-E-ST-20-08C clause 8.1.1 onto one coated coverglass item: decide first whether a space photovoltaic destination puts the item inside the clause at all, then which of the manufacture-control, test-programme and qualification-evidence families its heritage state, coating stack and declared changes pull in, derive the obligations each family owes, grade what is declared family by family, and weight those fractions into one scope coverage index with the uncovered obligations named. Trigger: ecss, e-st-20-08c-clause-8-1-1, coverglass-generic-rule-scope, coverglass-manufacture-control-coverage, coverglass-qualification-evidence-demand, coverglass-coating-stack-obligations, coverglass-scope-coverage-index."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e-st-20-08c-clause-8-1-1, e2008-coverglass-clause-purpose, coverglass-generic-rule-scope, coverglass-manufacture-control-coverage, coverglass-qualification-evidence-demand, coverglass-coating-stack-obligations, coverglass-scope-coverage-index]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Clause Purpose (space-systems/ecss/e2008-coverglass-clause-purpose)

Use when the task is to say what the generic coverglass rules of
ECSS-E-ST-20-08C clause 8.1.1 actually demand of a particular coated
coverglass -- whether the item is inside the clause, which families of
rule it pulls in, and whether the declared programme reaches them.

## Domain quick reference

- The clause opens a generic rule set rather than a single requirement,
  and the rules fall into three families: how the glass is made
  (substrate lot control, coating process control, handling and
  cleanliness), what is measured on it (transmittance, dimensions,
  coating adhesion), and the one-off evidence that the design and the
  process were qualified at all.
- The rules follow the destination, not the part number. A coverglass
  bound for a space photovoltaic assembly carries the whole set; the
  same glass cut as a ground test coupon or fitted to an unrelated
  optic is outside the clause, and saying so is a real outcome rather
  than a refusal to answer.
- Manufacture control and the measurement programme are unconditional
  for anything being made or delivered. Qualification evidence is the
  only family that can drop out, and it drops out on one narrow
  condition: a qualified heritage design running an unchanged process
  with an unchanged coating stack.
- Either declared change puts qualification evidence straight back.
  A process change and a coating change are separate drivers and both
  are recorded, because a plan that answers one and stays silent on the
  other has not answered the clause.
- A coating is the part of a coverglass most likely to be the thing
  that moved, so each declared coating adds obligations of its own: a
  spectral, conductivity or cut-off verification in the measurement
  family, and its own durability evidence in the qualification family.
- Coverage is graded per family and then weighted into one index,
  because the families are not equally expensive to leave open.
  Qualification evidence carries the heaviest weight, and the index is
  renormalised over the families that actually apply so a dropped
  family never flatters the score.
- A family that nothing declares at all is a different failure from a
  family with one gap in it, and the verdict keeps them apart however
  good the weighted index looks.

## Workflow

1. Validate the scope policy first: every family weighted above zero
   and a partial-coverage floor inside the unit interval. A policy that
   fails is refused rather than patched with a default.
2. Take the declared destination and decide whether the clause reaches
   the item at all. An item outside it closes immediately with the
   reason named and no coverage arithmetic attempted.
3. Normalise the coating stack, rejecting an unrecognised coating
   rather than dropping it, because every obligation downstream is
   derived from that stack.
4. Group the three rule families into applicable and not applicable
   from the heritage state, the process-change flag and the
   coating-change flag, recording the driver behind each decision.
5. Derive the obligations each applicable family owes, base activities
   plus one per declared coating where the family takes them.
6. Grade each family on the fraction of its obligations declared, then
   weight the applicable families into the scope coverage index.
7. Close on one verdict -- outside the clause, generic rules covered,
   partially covered, or uncovered -- reporting every missing
   obligation and every wholly untouched family, not only the first.

## Pitfalls

- Reading the clause as a checklist of tests. It opens manufacture
  rules and qualification rules alongside the measurements, so a plan
  built only from the test column leaves two thirds of the families
  with nothing declared against them.
- Treating an item as in scope because it is a coverglass. The rules
  follow a space photovoltaic destination; applying them to a ground
  coupon invents obligations, and skipping them on a flight item hides
  real ones.
- Letting qualified heritage excuse the whole clause. Heritage drops
  one family and only when the process and the coating stack are both
  unchanged; manufacture control and the measurement programme stay
  exactly where they were.
- Counting a coating as a property of the glass rather than an
  obligation. Each coating adds its own verification and its own
  durability evidence, so a stack quietly extended after the plan was
  written leaves gaps nobody re-graded.
- Averaging the families to a single percentage and stopping. A high
  weighted index can sit on top of a family that nothing covers, which
  is why the wholly untouched family is a verdict of its own.
- Comparing the index with the partial-coverage floor by bare
  arithmetic. The index is a weighted mean of ratios, so a case that
  lands exactly on the floor can fall a few units in the last place
  below it; the comparison absorbs that representation error while the
  floor stays untouched.

## Behavior contract (gate 3)

The policy validation, coating-stack normalisation, family
applicability and its drivers, obligation derivation, per-family
coverage, weighted scope coverage index and the scope verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_clause_purpose.py against
scripts/e2008_coverglass_clause_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_clause_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
