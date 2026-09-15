---
name: q60-class-1-hybrid-procurement
description: "Evaluate a class 1 hybrid microcircuit purchase against the specifications ECSS-Q-ST-60C clause 4.6.3 lists for it: select the generic specification family from the hybrid's construction, confirm the order cites that family at an issue that has not been superseded with a detail specification behind it, test the supplier against the approval list and the week its approval lapses, and check every die, chip element and substrate inside the hybrid carries a specification of its own. Refuses a construction with no listed family and names each constituent left uncovered. Use when a hybrid is about to be ordered. Trigger: ecss, q-st-60c-clause-4-6-3, class-1-hybrid-procurement, hybrid-generic-specification-family, hybrid-detail-specification-citation, hybrid-supplier-approval-expiry, constituent-element-specification-gap."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-1-hybrid-procurement, class-1-hybrid-procurement, hybrid-generic-specification-family, hybrid-detail-specification-citation, hybrid-supplier-approval-expiry, constituent-element-specification-gap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Hybrid Procurement (space-systems/ecss/q60-class-1-hybrid-procurement)

Use when the task is the clause 4.6.3 purchase step of ECSS-Q-ST-60C: a
class 1 hybrid microcircuit is going on a purchase order, and what makes
it a class 1 part is not the order value or the supplier's reputation but
the specification the order is placed against. The question is whether
the document the order names is the one the standard lists for this
hybrid, and whether everything inside the package is bought the same way.

## Domain quick reference

- A hybrid is a component made of components. The package is procured as
  one item, and the die, the chip resistors, the chip capacitors and the
  substrate inside it are each material with a procurement history of
  their own. Buying the assembly to a specification says nothing about
  what went into it unless the constituents were bought that way too.
- The listed specifications come in two levels. A generic family fixes
  the construction, the process controls and the test flow for a whole
  class of hybrids; a detail specification fixes this part — its
  function, its pinout, its limits. Citing only the generic family
  orders a category, not a part.
- The family follows the construction. Thick film, thin film, a multichip
  module and a microwave hybrid are governed by different listed
  families, and a construction the standard lists no family for is not a
  case to approximate with the nearest one.
- A specification carries an issue. An order placed against a superseded
  issue buys parts to test conditions that were withdrawn, which is a
  finding on the purchase document rather than on the parts, and it is
  found only by comparing the cited issue with the current one.
- Supplier approval is scoped and dated. An approval is granted for named
  families and lapses in a given week, so a supplier genuinely approved
  for multichip modules is not approved for a thick-film hybrid, and an
  approval that expires before the order week is not an approval.
- Week codes carry two digits of year. An approval week and an order week
  that straddle a century rollover have no orderable relation, which is
  an input to refuse rather than an ordering to guess.

## Workflow

1. Select the generic specification family listed for the hybrid's
   construction. An unlisted construction closes the assessment; the
   applicable specification cannot be chosen by resemblance.
2. Validate the purchase package: a cited family, a positive integer
   issue, a named supplier, a well-formed order week, and a detail
   specification reference when one is present.
3. Compare the cited family with the selected one, the cited issue with
   the current one, and require a detail specification wherever the
   selected family calls for one.
4. Look the supplier up on the approval list: present at all, approved
   for this family, and with an approval week that has not passed the
   order week. Report the weeks remaining.
5. Validate the constituent elements and take the element kinds the
   selected family requires that carry no specification of their own,
   together with the coverage of the required kinds.
6. Return one verdict in precedence order: the wrong family, a superseded
   issue, a missing detail specification, an unapproved supplier, an
   uncovered constituent, otherwise a package the order may be placed
   against. Report every finding, not only the one that decided the
   verdict.

## Pitfalls

- Ordering against the generic family alone. It is the commonest defect
  on a hybrid purchase order, and it survives review because the cited
  document is genuinely the right one — it is simply not specific enough
  to describe the part being bought.
- Choosing the family from the supplier's catalogue wording rather than
  the construction. A supplier's product line naming is a marketing
  choice; the construction is what decides which listed family applies.
- Accepting a supplier approval without checking its scope. Approval
  lists are granted per family, and a supplier approved for one
  construction is routinely quoted as approved for everything it makes.
- Treating the constituent elements as covered by the assembly
  specification. The assembly specification governs how the hybrid is
  built and tested, not where its die came from; a die with no
  specification is an untraceable part inside a class 1 package.
- Letting a superseded issue stand because the parts themselves are fine.
  The order is the record of what was bought; an issue nobody can now
  retrieve leaves the acceptance evidence pointing at a withdrawn
  document.
- Reporting only the verdict. A package can fail on the family and also
  carry a lapsed approval and two uncovered constituents; fixing the
  family and re-ordering then fails again, one finding at a time.

## Behavior contract (gate 3)

The family selection, package validation, citation comparison, supplier
approval lookup with its week arithmetic, constituent coverage measure
and verdict precedence are exercised by the gate 3 contract test:
scripts/test_q60_class_1_hybrid_procurement.py against
scripts/q60_class_1_hybrid_procurement_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_hybrid_procurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
