---
name: e20-inclusive-and-exclusive-category-use
description: "Use when determine which requirements of a standard apply to one product while tailoring by product type, per ECSS-E-ST-20C clause 8.2: read each requirement's applicability category, treat an exclusive requirement as applicable only to the product types it names and an inclusive requirement as applicable to every product type it does not except, resolve a product carrying several type roles by union, reject a catalogue entry whose category and product-type list contradict each other, and build the pre-tailoring-matrix column with a deletion rationale recorded against every requirement dropped and an approved deviation behind every applicable requirement deleted anyway. Trigger: ecss, e-st-20-electrical-scope, exclusive-requirement-category, inclusive-requirement-category, applicability-matrix, pre-tailoring-matrix, product-type-role, deletion-rationale, requirement-tailoring."
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
  tags: [ecss, e-st-20-electrical-scope, e20-inclusive-and-exclusive-category-use, exclusive-requirement-category, inclusive-requirement-category, pre-tailoring-matrix, product-type-role, requirement-tailoring]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical and Electromagnetic — Inclusive and Exclusive Category Use (space-systems/ecss/e20-inclusive-and-exclusive-category-use)

Use when the task is applying the two applicability categories of
ECSS-E-ST-20C clause 8.2 -- deciding, for one product and the type
roles it carries, which catalogue requirements are applicable, which
are deleted, and what has to be recorded against each deletion before
the pre-tailoring-matrix column is issued.

## Domain quick reference

- The catalogue splits requirements into two applicability categories,
  and they read in opposite directions. An exclusive requirement names
  the product types it applies to and applies to nothing else: absence
  from the list means not applicable. An inclusive requirement applies
  to every product type by default and names only the exceptions:
  absence from the exception list means applicable. Reading one with
  the other's rule inverts the answer on every row.
- The two lists are mutually exclusive by construction. An exclusive
  entry carrying an exception list, or an inclusive entry carrying a
  named product-type list, is a malformed catalogue entry -- the
  category and the list contradict each other and the row cannot be
  evaluated at all. That is a catalogue defect to raise, not a row to
  guess at.
- A real product usually carries more than one type role: an antenna
  assembly that is also a passive radio-frequency unit, a unit that is
  also part of the payload chain. Applicability is the union over the
  roles. An exclusive requirement applies when any role is named; an
  inclusive requirement is only deleted when every role it could apply
  to is excepted. Evaluating a single role silently drops
  requirements that a second role pulls back in.
- Tailoring is a recorded decision, not a filter. A requirement that
  is not applicable is deleted with a rationale pointing at the
  category logic that made it so. A requirement that is applicable
  and deleted anyway is a different act: it needs an approved
  deviation reference, because the project is stepping outside the
  standard rather than reading it.
- The pre-tailoring-matrix column is the output: one row per
  catalogue requirement, its applicability, the tailoring decision,
  and the record behind that decision.

## Workflow

1. Normalise the product's type roles against the known product-type
   vocabulary; reject an unknown role, a duplicate role, or an empty
   role set -- a product with no declared type cannot be tailored for.
2. Normalise every catalogue requirement: identifier, clause anchor,
   applicability category, named product-type list, exception list and
   relative weight. Reject an exclusive entry with an empty named list
   or a non-empty exception list, an inclusive entry with a non-empty
   named list, an unknown product type in either list, a duplicate
   entry within a list, and a duplicate requirement identifier across
   the catalogue.
3. Evaluate applicability per requirement against the union of roles:
   exclusive applies when any role is named; inclusive applies unless
   every role is excepted. Record the reason alongside the verdict so
   the matrix can be re-derived and argued.
4. Derive the expected tailoring action from the verdict: keep when
   applicable, delete when not applicable, and deviation-required when
   the project deletes something that is applicable.
5. Check the recorded decision against the expected action: a deletion
   of a non-applicable requirement needs a rationale; a deletion of an
   applicable requirement needs an approved deviation reference; a
   requirement kept although not applicable needs a rationale too,
   since it imports obligations the standard did not place there.
6. Build the matrix column, count applicable and deleted rows, and
   compare the deleted weight against the agreed deletion-ceiling.
   Treat a ratio that sits at the ceiling as within it -- a ratio is a
   quotient of two sums and can land marginally high on
   representation alone.

## Pitfalls

- Applying the exclusive rule to an inclusive requirement. Silence
  means applicable for one category and not applicable for the other,
  so the mistake never announces itself; it just quietly empties or
  fills the column.
- Tailoring against one product-type role when the product carries
  several. The union is the rule, and a second role commonly restores
  requirements the first role would have deleted.
- Treating a malformed entry as an implicit default. A catalogue entry
  whose category contradicts its lists is a defect against the
  catalogue owner, not a row to resolve locally.
- Deleting an applicable requirement with a rationale rather than an
  approved deviation. The rationale documents a reading of the
  standard; a deviation documents a departure from it, and only the
  second is a valid basis for dropping an applicable requirement.
- Issuing the column without recording why each row was dropped. A
  count of deleted requirements with no rationales cannot be reviewed
  at the next gate and puts the whole tailoring back in question.

## Behavior contract (gate 3)

The role normalisation, catalogue validation, category-driven
applicability, tailoring-action derivation, decision-record checking
and matrix-column aggregation logic is exercised by the gate 3
contract test:
scripts/test_e20_inclusive_and_exclusive_category_use.py against
scripts/e20_inclusive_and_exclusive_category_use_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_inclusive_and_exclusive_category_use.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
