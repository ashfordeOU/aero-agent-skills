---
name: e20-product-type-pre-tailoring-matrix
description: "Use when determine which ECSS-E-ST-20C electrical engineering provision groups reach a deliverable before any project-specific tailoring runs, under the clause 8.3 pre-tailoring matrix: categorize each item as an equipment-unit, a subsystem, a payload or a launcher-stage, resolve its declared feature set (solar-array-generator, electrochemical-energy-store, radio-frequency-transmitter, electro-explosive-device, high-voltage-assembly, harness-and-cable-network, magnetically-quiet-item), derive the disposition each provision group holds for that pairing, admit a downgrade only against a written justification and a named approval authority, and prove no matrix cell is left undeclared. Trigger: ecss, e-st-20-electrical-scope, e20-product-type-pre-tailoring-matrix, product-type-pre-tailoring, pre-tailoring-disposition-matrix, provision-group-applicability, launcher-stage-product-type, feature-driven-applicability, tailoring-downgrade-justification."
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
  tags: [ecss, e-st-20-electrical-scope, e20-product-type-pre-tailoring-matrix, product-type-pre-tailoring, pre-tailoring-disposition-matrix, provision-group-applicability, launcher-stage-product-type, feature-driven-applicability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Product-Type Pre-Tailoring Matrix (space-systems/ecss/e20-product-type-pre-tailoring-matrix)

Use when the task is the pre-tailoring matrix of ECSS-E-ST-20C clause 8.3 --
stating, for each product type a programme delivers and for each feature that
product carries, which electrical engineering provision groups bind as
written, which the project may reduce, and which have no object at all. The
matrix is built before project tailoring, so it is the baseline the tailoring
record is later measured against, not its result.

## Domain quick reference

- Four product types carry their own default column: the equipment-unit (a
  single deliverable box), the subsystem (a functional chain of units), the
  payload (an instrument chain with its own electrical interface) and the
  launcher-stage (a stage with its own on-board electrical architecture). A
  declared product type outside that set is not a clause 8.3 column and is
  rejected before the matrix is built, rather than silently mapped onto the
  nearest neighbour.
- Feature types cut across the columns: a solar-array-generator, an
  electrochemical-energy-store, a radio-frequency-transmitter, an
  antenna-subassembly, an electro-explosive-device, a high-voltage-assembly,
  a harness-and-cable-network, a magnetically-quiet-item. A feature is
  hardware the item actually carries, and it can only raise a disposition,
  never lower it -- if the hardware is on board, the group that governs it
  binds whatever the bare product-type column said.
- Each cell holds one of three dispositions: applicable (the group binds as
  written), tailorable (the group binds but the project may reduce its
  depth against a record), not-applicable (the group has no object on this
  item). A missing cell is a fourth state and is a finding, not a default:
  an undeclared cell means the pairing was never assessed.
- The disposition-setting driver is recorded with the cell. A cell reading
  "applicable / product-type-default" and a cell reading "applicable /
  electro-explosive-device" carry the same disposition but different
  evidence, and only the second survives if the feature is later dropped
  from the design baseline.
- A downgrade -- applicable to tailorable, or either to not-applicable --
  is admissible only with a written justification and a named approval
  authority on the same record. A raise needs neither, because raising a
  disposition never removes a requirement from the deliverable.

## Workflow

1. Inventory the deliverables the programme will produce and give each one a
   name, a product type and its declared feature set. Reject an unknown
   product type or an unrecognised feature before the matrix is built.
2. For every deliverable and every provision group, read the product-type
   default, then let each declared feature raise it. Record the disposition
   together with the driver that set it (product-type-default, or the
   feature token).
3. Assemble the cells into a matrix ordered by item then group, so two runs
   over the same inventory produce byte-identical output and a diff between
   design baselines is readable.
4. Apply the project's tailoring requests one at a time. Admit a raise
   unconditionally; admit a downgrade only when both a justification text
   and a named approval authority are present, and otherwise keep the
   derived disposition and record the request as rejected.
5. Audit the tailored matrix for completeness: every deliverable must carry
   a cell for every provision group in the catalogue. Report each missing
   pairing as an undeclared cell.
6. Summarise the matrix -- the count per disposition and the share of cells
   that bind (applicable plus tailorable) -- and compare that share against
   any floor the programme declared. Absorb float representation error at an
   exactly met floor rather than widening the floor itself.
7. The pre-tailoring pass is complete only when no cell is undeclared, no
   tailoring request was rejected, and the binding share reaches its floor.

## Pitfalls

- Reading a blank cell as not-applicable. An undeclared pairing means the
  assessment never ran; treating it as an exclusion quietly removes the
  provision group from the deliverable with no record at all.
- Letting a feature lower a disposition. Features exist to catch hardware
  the product-type column did not anticipate; a group that already binds on
  the bare product type keeps binding whatever the feature list says.
- Recording a downgrade with a justification but no approval authority (or
  the reverse) and counting it as tailored. Half a record is a rejected
  request -- the cell keeps its derived disposition until both halves exist.
- Building the matrix after project tailoring instead of before. The clause
  8.3 matrix is the baseline the tailoring record is measured against; if it
  is regenerated from the tailored set, every reduction becomes invisible.
- Collapsing the payload column onto the subsystem column because both are
  "not a unit". The two differ on the groups that follow an own electrical
  interface, and collapsing them overstates the generation and distribution
  scope of a payload while understating its radio-frequency scope.
- Dropping the driver field once the disposition is known. When a feature is
  removed from the design baseline, only the driver tells which cells must
  be re-derived and which were never feature-driven.

## Behavior contract (gate 3)

The product-type and feature resolution, the per-cell disposition rule, the
tailoring-request admission rule, the completeness audit and the binding-share
summary are exercised by the gate 3 contract test:
scripts/test_e20_product_type_pre_tailoring_matrix.py against
scripts/e20_product_type_pre_tailoring_matrix_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e20_product_type_pre_tailoring_matrix.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
