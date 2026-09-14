---
name: e2008-bare-cell-delivery
description: "Use when a shipment is offered: hold every cell drawn from a lot whose data package is not released, disposition each cell as shippable, shippable on an accepted concession or held, fill each ordered grade line from that grade before any upgrade the order permits, reconcile every line short and over, and apply the declared partial-delivery floor. Evaluate whether a dispatch of ordered bare solar cells may leave under ECSS-E-ST-20-08C clause 7.8, where the hardware and its matching documentation set have to close together. Trigger: ecss, e-st-20-08c, clause-7-8, bare-cell-dispatch-release, bare-cell-lot-documentation-coverage, bare-cell-grade-line-allocation, bare-cell-upgrade-substitution-rule, bare-cell-partial-delivery-floor."
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
  tags: [ecss, e-st-20-08-bare-solar-cell-scope, e2008-bare-cell-delivery, e-st-20-08c-clause-7-8, bare-cell-dispatch-release, bare-cell-lot-documentation-coverage, bare-cell-grade-line-allocation, bare-cell-upgrade-substitution-rule, bare-cell-partial-delivery-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Solar Cells -- Delivery (space-systems/ecss/e2008-bare-cell-delivery)

Use when the task is clause 7.8 of ECSS-E-ST-20-08C: the ordered bare
cells are ready to leave, and whether they may go has to be settled
against both the order they answer and the documentation set the
preceding clause asks for.

## Domain quick reference

- Two arms have to close, not one. A shipment is not releasable because
  the cells are counted and present; every cell also has to come from a
  lot whose data package is released. A cell whose lot has no released
  package is not a cell with late paperwork, it is a cell nobody
  downstream can trace back to a qualified process.
- That is why a count is the weakest possible check. An ordered quantity
  can be met in full by cells drawn entirely from a lot whose package was
  never released, and a pure counting sweep passes it without a word.
- Release state is a state, not an entry. A lot listed in the package
  register with the release still pending is a lot without a released
  package, and reading the register for presence rather than for state is
  the quiet way this arm goes green.
- Bare cells are ordered by grade, which raises a substitution question
  an assembly-level delivery never has to answer. A line asking for a
  lower grade may be filled from a higher one when the order permits the
  upgrade -- the customer receives more than was bought. It may never be
  filled from a lower grade, which is a downgrade of the article dressed
  up as a substitution.
- Allocation order therefore matters as much as the rule. Exact grade is
  spent first and only then is a permitted upgrade drawn on, or a high
  line goes short because its cells were consumed by a low line that had
  its own stock available.
- A cell under an open nonconformance is not shippable because somebody
  wrote a concession; it is shippable when that concession is accepted,
  and those cells are named in the dispatch rather than folded into the
  clean count.
- What is left over is not slack. A shippable cell that no order line
  asks for is surplus the shipment was never asked to carry, and it is
  reported rather than quietly loaded.
- A partial dispatch is a decision. The order declares the fraction of a
  line below which a partial delivery is refused outright; a line that
  clears that floor without being complete still goes, and is still named
  as partial. A line sitting exactly on its floor clears it -- the
  comparison absorbs representation error rather than moving the floor.

## Workflow

1. Validate the order: every line carries an identifier, a grade, a
   positive ordered count and an explicit substitution permission, and
   the partial-delivery floor is a stated fraction between nought and
   one.
2. Resolve which lots have a released data package, reading the release
   state rather than the presence of a register entry.
3. Disposition every offered cell: held when its lot has no released
   package, held when an open nonconformance carries no accepted
   concession, shippable on an accepted concession when it does, and
   shippable otherwise.
4. Fill each order line from the shippable cells, taking the exact grade
   first and only then the nearest permitted upgrade; never take a lower
   grade.
5. Reconcile each line: shipped against ordered, the short count, the
   fill fraction, and which allocated cells were substitutions.
6. Compare each fill fraction with the declared floor under a named
   tolerance, marking the line complete, partial within the floor, or
   refused below it.
7. Report the surplus shippable cells no line asked for, the held cells
   with their reasons, the concession cells by name, and release only
   when the finding list is empty.

## Pitfalls

- Counting to the ordered quantity and stopping. The count says nothing
  about which lots the cells came from, and the documentation arm is
  where a traceability break actually shows.
- Reading the lot package register for presence. An entry whose release
  is still pending is an entry, and treating it as coverage puts
  untraceable cells on the shipment.
- Letting an accepted concession stand in for documentation. A concession
  disposes of a nonconformance; it does not release a lot's data package,
  and a cell can fail both arms at once.
- Allowing a downgrade as a substitution. Filling a higher-grade line
  from a lower grade delivers an article the order did not buy, whatever
  the count says.
- Taking upgrades before exact stock. A permitted upgrade spent on a low
  line can starve the high line the cell was the only candidate for, so
  the same pool produces a short line purely through allocation order.
- Loading the surplus. A shippable cell no line wants is not a free
  extra; it leaves the shipment and the order disagreeing.
- Moving the floor to pass a line that sits exactly on it. An equality at
  the limit is a representation question, handled by the tolerance inside
  the comparison; the declared fraction stays as declared.
- Reporting a bare rejection. One refused line, one held cell or one
  surplus cell each block the dispatch for a different reason, and the
  report names which.

## Behavior contract (gate 3)

The grade ladder and its rank order, the order and line validation with
the explicit substitution permission and the bounded partial-delivery
floor, the release-state reading of the lot package register, the
three-way cell disposition with its concession states, the exact-grade
-before-upgrade allocation with downgrades refused, the per-line short
and surplus reconciliation, the floor comparison under a named tolerance
and the aggregated dispatch verdict are exercised by the gate 3 contract
test: scripts/test_e2008_bare_cell_delivery.py against
scripts/e2008_bare_cell_delivery_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2008_bare_cell_delivery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
