---
name: q6013-class-2-buy-off-inspection
description: "Use when a delegated source inspection has to become a release decision. Determine whether an intermediate assurance commercial EEE lot is released for delivery at the ECSS-Q-ST-60-13C clause 5.3.6 source buy-off: validate the delegation record against the buy-off date and refuse a producer that delegated the witness of its own lot to itself, take the evidence set the declared attendance mode demands, credit an item carried by a named data pack reference below one seen directly, scale the open-minor allowance to the lot in integer arithmetic, refuse a buy-off dated before the lot conformance review closed, and return release, hold or escalate. Trigger: ecss, q-st-60-13c-clause-5-3-6, class-two-source-buy-off, buy-off-delegation-validity, documentary-buy-off-attendance-mode, evidence-carried-by-data-pack-reference, lot-scaled-minor-allowance, release-hold-or-escalate-disposition."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-2-buy-off-inspection, class-two-source-buy-off, buy-off-delegation-validity, documentary-buy-off-attendance-mode, evidence-carried-by-data-pack-reference, lot-scaled-minor-allowance, release-hold-or-escalate-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE -- Class 2 Source Buy-Off Inspection (space-systems/ecss/q6013-class-2-buy-off-inspection)

Use when the task is the clause 5.3.6 final source inspection of
ECSS-Q-ST-60-13C at the intermediate assurance class: a lot is finished
at the supplier, the buy-off may have been delegated and may have been
carried out at a distance, and the question is whether the lot is
released for delivery on the strength of it.

## Domain quick reference

- The intermediate class buys flexibility with evidence. The customer
  need not stand at the bench, so the first thing the buy-off has to
  establish is not the state of the lot but the credibility of the
  inspection: who witnessed it, under whose delegation, and whether that
  delegation was in force on the day.
- A delegation that runs out before the buy-off date is not a lapsed
  formality; it is a buy-off carried out by someone who at that moment
  held no authority to carry it out. The window is checked against the
  inspection date, not against today.
- An organisation cannot delegate to itself the witness of its own lot.
  When the delegate's organisation is the producing organisation the
  independence the delegation was meant to supply was never supplied,
  and the finding is the arrangement, not the paperwork it produced.
- The attendance mode sets the evidence set. On-site attendance needs
  the base set. A remote-witnessed buy-off owes the recording of the
  live witness. A documentary buy-off gave up presence altogether and
  owes a photographic record set and a supplier release note in its
  place, because otherwise nothing was witnessed at all.
- An item carried by a supplier data pack reference counts, but below an
  item the witness saw for himself, and only where the reference names a
  document. A reference with nothing behind it cannot be audited later,
  so it is counted absent rather than credited.
- The minor allowance scales with the lot. Two open minors on a lot of a
  hundred parts and two on a lot of sixty are different densities, and
  the allowance is computed in integer arithmetic so the same lot size
  gives the same allowance on every machine that runs it.
- Three outcomes, not two. An uncredible delegation is not a hold that
  more evidence could clear; it escalates to a witnessed buy-off. A
  credible delegation with blocking findings holds the lot where it
  stands.

## Workflow

1. Validate the delegation: named delegate, named delegating and
   producing organisations, and a validity window that covers the
   buy-off date. Flag a self-delegated witness separately from an
   expired one.
2. Resolve the evidence set from the declared attendance mode before
   looking at what was presented, so a documentary buy-off is graded
   against the documentary set.
3. Walk the set item by item as seen, carried by reference or absent.
   Demote an unsupported reference to absent and keep the weighted
   coverage alongside the list, never instead of it.
4. Scale the minor allowance to the lot size in integer arithmetic, then
   group the findings into open majors, open minors, waived and closed;
   refuse a waiver carrying no reference and a repeated identifier.
5. Check the buy-off date against the close of the lot conformance
   review and keep the signed day gap.
6. Escalate on an uncredible delegation or a documentary buy-off below
   the coverage floor; otherwise hold on any blocking finding and name
   every reason; otherwise release for delivery.
7. Report referenced items as advisories, separate from the reasons that
   actually blocked.

## Pitfalls

- Reading the delegation window against the day the record is reviewed
  rather than the day of the buy-off. The question is whether authority
  existed at the moment it was exercised.
- Grading a documentary buy-off against the on-site evidence set. The
  substitute records are the whole reason the mode is admissible, so
  omitting them from the required set makes a remote paper exercise look
  like a witnessed inspection.
- Crediting an item because someone said it is in the data pack. Without
  a named document and issue there is nothing to fetch, and the item is
  absent.
- Carrying the highest assurance minor allowance across unchanged. A
  fixed allowance is too tight on a large lot and far too loose on a
  small one, which is why it is scaled and capped.
- Treating a bad delegation as one more hold reason. Holding implies the
  lot could be released once the list is cleared; an inspection nobody
  was authorised to make has to be made again, under witness.
- Computing the allowance with a floating-point square root. Integer
  arithmetic keeps the same lot size yielding the same allowance
  everywhere the assessment is re-run.

## Behavior contract (gate 3)

The delegation validation, attendance-mode evidence set, referenced-item
credit, lot-scaled minor allowance, date-sequence check and the
three-way release, hold or escalate disposition are exercised by the
gate 3 contract test:
scripts/test_q6013_class_2_buy_off_inspection.py against
scripts/q6013_class_2_buy_off_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_buy_off_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
