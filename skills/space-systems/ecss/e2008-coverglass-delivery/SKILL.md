---
name: e2008-coverglass-delivery
description: "Evaluate whether an offered coverglass shipment may leave under ECSS-E-ST-20-08C clause 8.10. Use when a dispatch of ordered coverglasses is presented for release with the documentation set the order agreed: hold every batch whose agreed documents are absent, written to a superseded issue, unsigned or issued against another batch; fill each ordered line from its own coverglass type before any alternative the order named, and never from one it did not; reconcile every line short and every surplus piece; and apply the declared partial-delivery floor under a named tolerance. Trigger: ecss, e-st-20-08c-clause-8-10, coverglass-dispatch-release, coverglass-agreed-documentation-set, coverglass-batch-document-coverage, coverglass-type-substitution-permission, coverglass-partial-delivery-floor."
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
  tags: [ecss, e-st-20-08-coverglass-scope, e-st-20-08c-clause-8-10, e2008-coverglass-delivery, coverglass-dispatch-release, coverglass-agreed-documentation-set, coverglass-batch-document-coverage, coverglass-type-substitution-permission, coverglass-partial-delivery-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses -- Delivery (space-systems/ecss/e2008-coverglass-delivery)

Use when the task is clause 8.10 of ECSS-E-ST-20-08C: the ordered
coverglasses are ready to leave, and whether they may go is settled
against the order they answer and against the documentation set that
order agreed would travel with them.

## Domain quick reference

- Two arms have to close, not one. A shipment is not releasable because
  the pieces are counted and present; every batch also has to carry the
  documents the order agreed. A batch nobody wrote the agreed records
  for is not glass with late paperwork, it is glass no one downstream
  can tie back to a controlled process.
- Agreed is the operative word. The accompanying set is named by the
  order, not fixed once for every shipment, so the first thing read is
  which kinds this order agreed to -- grading a coverglass dispatch
  against a habitual list is how a shipment passes while the record the
  customer actually asked for is missing.
- A count is therefore the weakest possible check. The ordered quantity
  can be met in full from batches whose agreed records are absent,
  written to a superseded issue, unsigned, or issued against a different
  batch entirely, and a pure counting sweep passes all four.
- A document is read for what it covers and how it stands. A record of
  the right kind naming some other batch is not this batch's record; a
  record written to an issue the governing one has replaced describes
  glass built to a rule set nobody works to now; an unsigned record is a
  draft. Presence in the folder is not one of the three tests.
- A superseded duplicate does not hold a batch its current record
  already clears. Where several records of one kind cover a batch, the
  one that stands is the one the disposition reads, so a superseded copy
  left in the folder is not a finding in itself.
- Coverglasses are ordered by type, which raises a substitution question.
  A line may be filled from another type only where the order named that
  type as permitted for it; a type the line never named is a different
  article, whatever the count says.
- Allocation order matters as much as the rule. Exact type is spent
  first and only then a permitted alternative, or a scarce type is
  consumed by a line that had its own stock standing by and the other
  line goes short purely through allocation order.
- What is left over is not slack. A releasable piece no line asks for is
  surplus the shipment was never asked to carry, and it is reported
  rather than quietly loaded.
- A partial dispatch is a decision. The order declares the fraction of a
  line below which a partial delivery is refused outright; a line that
  clears that floor without being complete still goes, and is still
  named as partial. A line sitting exactly on its floor clears it -- the
  comparison absorbs representation error rather than moving the floor.

## Workflow

1. Validate the order: every line carries an identifier, a coverglass
   type, a positive ordered count and its permitted alternative types;
   the agreed document kinds are a non-empty set of recognized kinds;
   and the partial-delivery floor is a stated fraction between nought
   and one.
2. Validate the accompanying records: kind, issue, governing issue,
   signature state and the batches each one covers.
3. For every shipped batch, resolve each agreed kind in turn -- accepted,
   missing for this batch, superseded, or unsigned -- and disposition the
   batch releasable only when all of them are accepted.
4. Fill each order line from the releasable batches, drawing the exact
   type first and only then a permitted alternative; never draw a type
   the line did not name.
5. Reconcile each line: shipped against ordered, the short count, the
   fill fraction, and which pieces were drawn as alternatives.
6. Compare each fill fraction with the declared floor under a named
   tolerance, marking the line complete, partial within the floor, or
   refused below it.
7. Report the surplus pieces no line asked for, the held batches with
   their reasons, the lines filled by substitution, and release only
   when the finding list is empty.

## Pitfalls

- Counting to the ordered quantity and stopping. The count says nothing
  about which batches the glass came from, and the documentation arm is
  where a traceability break actually shows.
- Grading the shipment against a habitual document list. The agreed set
  is an order-level fact; reading it from custom passes a shipment that
  is missing exactly the record this customer asked for.
- Reading the folder for presence. A record of the right kind covering a
  different batch, or sitting at a superseded issue, or unsigned, is an
  entry and not coverage, and all three ship untraceable glass.
- Holding a batch for a superseded copy that a current record already
  covers. The disposition reads the record that stands, or a tidy folder
  becomes a finding and a genuine gap gets lost in the noise.
- Drawing a type the line never named. Filling an order line from other
  glass delivers an article the order did not buy, however neatly the
  quantity reconciles.
- Taking alternatives before exact stock. A permitted alternative spent
  on a line with its own stock available starves the line that had no
  other candidate, so the same pool produces a short line purely through
  allocation order.
- Loading the surplus. A releasable piece no line wants is not a free
  extra; it leaves the shipment and the order disagreeing.
- Moving the floor to pass a line that sits exactly on it. An equality at
  the limit is a representation question, handled by the tolerance inside
  the comparison; the declared fraction stays as declared.
- Reporting a bare rejection. One refused line, one held batch or one
  surplus piece each block the dispatch for a different reason, and the
  report names which.

## Behavior contract (gate 3)

The agreed document kind vocabulary, the order and line validation with
its permitted alternative types and bounded partial-delivery floor, the
per-batch resolution of each agreed kind into accepted, missing,
superseded or unsigned, the preference for the record that stands, the
exact-type-before-alternative allocation with unnamed types refused, the
per-line short and surplus reconciliation, the floor comparison under a
named tolerance and the aggregated dispatch verdict are exercised by the
gate 3 contract test: scripts/test_e2008_coverglass_delivery.py against
scripts/e2008_coverglass_delivery_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2008_coverglass_delivery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
