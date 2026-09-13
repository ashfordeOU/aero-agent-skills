---
name: e2008-pva-defect-acceptability
description: "Agree and confirm the allowable defect levels of a photovoltaic assembly under ECSS-E-ST-20-08C clause 5.4.2. Use when a defect catalogue has to become an acceptance rule set before assembly hardware is presented: convert each agreed defect fraction into a whole allowable count over the declared population, categorize the agreement basis as customer-agreed, supplier-proposed or undocumented, check that a qualification article actually carried the level being claimed, compare the observed defect population against its allowance, and name the defect type that governs the assembly verdict. Trigger: ecss, e-st-20-08c, photovoltaic-assembly-defect-acceptability, allowable-defect-level-agreement, defect-catalogue-acceptance-rule, qualification-confirmed-defect-level, pva-workmanship-defect-budget, agreement-record-citation, assembly-level-defect-allowance."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-pva-defect-acceptability, photovoltaic-assembly-defect-acceptability, allowable-defect-level-agreement, defect-catalogue-acceptance-rule, qualification-confirmed-defect-level, pva-workmanship-defect-budget, assembly-level-defect-allowance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Defect Acceptability (space-systems/ecss/e2008-pva-defect-acceptability)

Use when the task is the allowable-defect question of ECSS-E-ST-20-08C
clause 5.4.2 -- fixing, before assembly hardware is offered, how many of
each defect type the assembly may carry, on whose authority that number
stands, and what evidence confirms that an assembly carrying it still
performs.

## Domain quick reference

- A photovoltaic assembly is a population, not a single item: hundreds
  of cells, interconnectors, coverglasses and bonds. Perfection is not
  purchasable, so an allowable level per defect type is fixed up front
  rather than argued once a defect appears.
- An allowable level only counts as established when three things line
  up. The level is written down, the writing down is an agreement
  rather than a supplier preference, and a qualification article
  actually carried hardware at or above the level. Any one of the three
  missing leaves the level provisional at best.
- Agreement basis, strongest to weakest: customer-agreed (the level
  sits in an agreed record that can be cited by identifier),
  supplier-proposed (documented, not yet agreed), and undocumented (the
  level exists only as shop practice and carries no acceptance
  standing).
- Qualification basis, strongest to weakest: qualification-demonstrated
  (an article carried the level through the qualification campaign),
  analysis-supported (the level is argued, never demonstrated), and
  none. A demonstrated basis is only worth the level it reached, so the
  comparison is coverage -- what was carried against what is claimed.
- A fraction is not an acceptance criterion until it is paired with a
  population. Two per cent of a 150-cell string is three whole defects,
  and the fourth is a non-conformance however close the arithmetic
  runs.
- Two questions stay separate throughout. Whether the criterion is
  established is a question about the paperwork and the qualification
  campaign; whether this article meets it is a question about the
  count on the bench. An assembly can hold a perfectly established
  criterion and still breach it, and can sit well inside an allowance
  that nobody ever agreed.

## Workflow

1. Enumerate the defect types the assembly can produce and give each
   one a declared allowable fraction. Reject a fraction of zero or a
   fraction above one; a level that permits nothing is not an allowance
   and a level above the whole population is not a level.
2. Categorize each agreement basis and demand what the basis implies.
   A customer-agreed level must cite the record it sits in; an
   undocumented level must not cite one, because a citation contradicts
   the basis.
3. Convert each fraction into whole allowable defects over the declared
   population, snapping a product that lands on an integer within
   representation error before taking the floor.
4. Resolve the qualification evidence. On a demonstrated basis compute
   the coverage of the demonstrated level over the agreed level and
   treat a coverage of one as confirmation; on an analysis basis or no
   basis at all record what is outstanding.
5. Compare the observed defect count with the allowance and carry the
   utilisation, so a type sitting on its limit is visible before it
   crosses.
6. Roll the assembly up to the weakest per-type verdict, name the
   governing defect type, and report article conformance separately
   from whether the criteria are established.

## Pitfalls

- Reading a defect fraction straight off a supplier data pack and
  calling it agreed. A documented number and an agreed number are
  different objects; only the second survives a customer review, and
  the first has to be presented as provisional until it is signed.
- Letting the qualification campaign define the allowance backwards. An
  article that carried one per cent does not confirm a two per cent
  allowance, and quoting the campaign as confirmation hides a level
  that reaches past the evidence by a factor of two.
- Taking the floor of population times fraction with bare arithmetic.
  The product is a float, so a pairing that is exactly three defects
  can evaluate a hair below three and silently drop the allowance to
  two on one platform and not another.
- Rolling the assembly up on an average. The weakest defect type
  governs, because an assembly with one unconfirmed level is an
  assembly with an unconfirmed acceptance basis regardless of how many
  other types are fully agreed.
- Collapsing the criterion question into the count question. An article
  inside every allowance still fails clause 5.4.2 when the allowances
  were never agreed, and an article over one allowance is a
  non-conformance against a criterion that is itself perfectly sound.

## Behavior contract (gate 3)

The allowable-count conversion, agreement categorization, qualification
coverage, per-type verdict, governing-defect selection and assembly
roll-up are exercised by the gate 3 contract test:
scripts/test_e2008_pva_defect_acceptability.py against
scripts/e2008_pva_defect_acceptability_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_pva_defect_acceptability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
