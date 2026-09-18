---
name: q6005-chip-procurement-specification-requirements
description: "Assess whether the purchasing documents for bare semiconductor and passive chips define everything an order needs under ECSS-Q-ST-60-05C clause 8.1.3: separate the always-mandatory content from the conditional content that applies only when the project declares a radiation, screening, single-wafer-lot or serialization context, treat a placeholder such as TBD as undefined rather than declared, compute the completeness ratio over the applicable set alone so a surplus item cannot inflate it, and refuse release-to-order while any applicable item stays undefined. Use when drafting or reviewing a bare-die purchase specification. Trigger: ecss, q-st-60-05c, bare-die-purchase-specification, chip-procurement-mandatory-content, die-revision-identification, bond-pad-metallization-definition, conditional-procurement-item, chip-release-to-order."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-chip-procurement-specification-requirements, bare-die-purchase-specification, chip-procurement-mandatory-content, die-revision-identification, conditional-procurement-item, chip-release-to-order]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Chips — Purchase Specification Content (space-systems/ecss/q6005-chip-procurement-specification-requirements)

Use when the task is establishing what the purchasing documents for bare
semiconductor or passive chips have to define under ECSS-Q-ST-60-05C
clause 8.1.3 — the content that has to be settled before the order is
placed, not after a delivered lot turns out to disagree with an
assumption nobody wrote down.

## Domain quick reference

- A bare chip has no package to carry its identity and no datasheet
  entry that fixes its mechanical form, so the purchase specification is
  the entire definition of what is being bought. Anything it leaves
  unsaid is decided by the supplier, silently, and discovered at
  incoming inspection or at wire bonding.
- The content divides into two kinds. Always-mandatory items are settled
  for every bare-chip purchase whatever the mission: the chip type, the
  die revision and mask set, wafer-lot traceability, electrical
  parameters at probe, visual inspection criteria, die dimensions with
  tolerances, bond-pad metallization, backside finish, passivation,
  packaging and storage, the ESD sensitivity category, the content of
  the certificate of conformity, and the delivery documentation.
- Conditional items are owed only when the project declares the context
  that calls for them — a radiation hardness level when the mission
  environment demands one, an additional screening plan when screening
  beyond the supplier's flow is imposed, a single-wafer-lot quantity
  when lot homogeneity is a design assumption, serialization and
  container marking when individual die identity is tracked. An
  undeclared context does not make the item optional; it makes it
  inapplicable, which is a different statement.
- A field that exists but says nothing has defined nothing. "TBD", "to
  be advised", a dash or an empty string are the commonest way a
  specification passes a completeness count while leaving the decision
  open, so they are read as undefined at the point of the check.
- The completeness ratio is computed over the applicable set alone.
  Measuring against the full catalogue would let a project with no
  radiation requirement look incomplete, and measuring against the
  declared keys would let a surplus item raise the score, so the
  denominator is what this order actually owes.
- Completeness and readiness are not the same test. A partial ratio can
  be a useful progress view mid-draft, but release-to-order needs every
  applicable item defined; a ratio threshold is never a substitute for
  the last undefined field.

## Workflow

1. Validate the declared project context. Only the known conditional
   flags are accepted, each as a boolean; an unrecognised flag is an
   input error rather than an ignored key, because a misspelt flag
   silently drops the item it was meant to switch on.
2. Build the applicable content set: every always-mandatory item, plus
   each conditional item whose context flag is declared true.
3. Normalise the declared specification's keys to one canonical form so
   an underscore, a capital or a stray space cannot present the same
   item twice; a genuine duplicate after normalisation is an input
   error.
4. Test each applicable item for definedness, reading placeholders,
   empty strings, empty collections and absent keys alike as undefined.
5. Report the undefined applicable items in applicable order, and
   separately the declared items that sit outside the applicable set.
6. Compute the completeness ratio over the applicable set only, and
   compare any declared threshold with a named tolerance rather than by
   lowering the threshold.
7. Return ready-to-order only when nothing applicable is undefined, with
   the findings naming the undefined and surplus items so the draft can
   be closed out without re-deriving the set.

## Pitfalls

- Counting declared keys instead of defined values. A specification with
  every key present and half of them reading "TBD" scores full marks on
  a key count and defines nothing that binds the supplier.
- Treating an undeclared context as an optional item. Radiation hardness
  is not an item the buyer may skip; it is either applicable, in which
  case it is mandatory, or inapplicable, in which case declaring it is a
  surplus finding worth reviewing.
- Letting a surplus item raise the completeness ratio. A denominator
  taken from the declared keys rewards adding inapplicable content, so
  the applicable set is the denominator and the surplus is reported
  separately.
- Releasing an order on a ratio threshold. Ninety-two per cent complete
  means one applicable item is still undefined, and the item left last
  is usually the contentious one.
- Leaving bond-pad metallization or backside finish to the supplier's
  standard. Both are assembly-process inputs: the wrong pad metal or an
  unexpected backside finish makes the die unbondable or unattachable
  long after the lot has been paid for.
- Deriving the applicable set once and reusing it across orders. The
  context flags belong to the order, and a project that adds a screening
  requirement between two buys owes a different set the second time.

## Behavior contract (gate 3)

The context validation, applicable-set construction, key normalisation,
placeholder detection, the completeness ratio over the applicable set
and the release-to-order decision are exercised by the gate 3 contract
test: scripts/test_q6005_chip_procurement_specification_requirements.py
against
scripts/q6005_chip_procurement_specification_requirements_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q6005_chip_procurement_specification_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
