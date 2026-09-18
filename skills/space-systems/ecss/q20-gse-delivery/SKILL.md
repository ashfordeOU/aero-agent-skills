---
name: q20-gse-delivery
description: "Coordinate the delivery review and the handover of ground support equipment under ECSS-Q-ST-20C clauses 5.8.4.3 and 5.8.4.4: check that the board had the functions it needed and a chair independent of the work under review, confirm the agenda covered every subject it owes, let the open action list decide hold, reserve or deliver, derive the conformity certificates the item's own states demand, test each one against the delivery day so an expired or not-yet-issued certificate is caught, and reconcile the documentation that travels with the equipment. Use when GSE is about to be handed to its user. Trigger: ecss, q-st-20c-clause-5-8-4-3, gse-delivery-review-board, gse-board-quorum, gse-conformity-certificate-validity, gse-delivery-documentation, gse-delivery-authorisation."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-gse-delivery, gse-delivery-review-board, gse-board-quorum, gse-conformity-certificate-validity, gse-delivery-documentation, gse-delivery-authorisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS GSE Delivery Review and Handover (space-systems/ecss/q20-gse-delivery)

Use when the task is the clause 5.8.4.3 delivery review and the clause 5.8.4.4
delivery of ground support equipment in ECSS-Q-ST-20C: the board sits, the
conformity evidence is laid on the table, and the equipment either goes to its
user with its certificates and documentation or it does not go.

## Domain quick reference

- A meeting is not a review. The review owes a named set of functions in the
  room — quality, GSE engineering, the operations user who will live with the
  equipment, and configuration management — and a chair who is not the function
  whose work is being examined.
- The agenda is part of the record. A review that never reached limitations of
  use has not told the user what the equipment cannot do, whatever else it
  covered.
- The action list decides the outcome, not the mood of the room. A blocking
  action still open holds the delivery; an ordinary action still open makes it
  a delivery with a reservation; nothing open lets it go clean.
- A certificate is evidence only inside its own validity window. One that
  expired last month and one dated next month are equally worthless on the day
  the equipment moves, and both are easy to miss in a thick binder.
- The certificate set is derived from the equipment. A calibrated chain owes
  its calibration certificate, a lifting fixture its proof-load certificate, a
  pressurised system its pressure test, a mains-powered unit its electrical
  safety certificate.
- Authorisation is the conjunction of the board decision and the findings. A
  board that said deliver over an expired certificate has not authorised
  anything.

## Workflow

1. Validate the board: chair function, attending functions and the agenda
   actually covered, with the reviewed function stated rather than assumed.
2. Raise each absent mandatory function, a chair drawn from the reviewed
   function, a chair who was not in the room, and each uncovered agenda subject.
3. Validate the action list, refusing a duplicated identifier, an unknown
   severity and an unknown state.
4. Derive the board decision from the open actions: hold on a blocking action,
   reservation on any other open action, deliver otherwise.
5. Derive the mandatory certificate set from the item's own states.
6. Test each certificate against the delivery day, treating the last day of
   validity as valid, and raise the unsigned and absent ones separately.
7. Reconcile the delivery documentation, adding the limitations notice where
   limitations apply, then authorise only on a non-hold decision with no
   finding standing.

## Pitfalls

- Counting heads instead of functions. Six people from two departments is not
  a board; the operations user who was not invited is the one who will find out
  what the equipment cannot do.
- Letting the design function chair its own delivery review. The chair decides
  what the board accepts, and an author is not a reviewer.
- Reading a thick certificate binder as compliance. Validity is per certificate
  and per day, and the binder is where an expired page hides best.
- Treating the last day of validity as expiry. The certificate covers that day;
  an off-by-one here holds a delivery for no reason.
- Delivering on the board's word while a finding stands. The decision and the
  evidence are two gates, and the equipment passes both or neither.
- Leaving the limitations notice out of a reserved delivery. The user inherits
  what the equipment cannot do, and the notice is how they learn it.

## Behavior contract (gate 3)

The board validation and quorum findings, chair independence, agenda coverage,
action validation, the hold, reserve and deliver decision, the state-derived
certificate set, per-day certificate validity, delivery documentation
reconciliation and the authorisation decision are exercised by the gate 3
contract test: scripts/test_q20_gse_delivery.py against
scripts/q20_gse_delivery_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_gse_delivery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
