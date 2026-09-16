---
name: q6013-class-1-buy-off-inspection
description: "Use when a source inspection has to become a ship-or-hold decision. Evaluate whether a highest-assurance commercial parts lot may leave the manufacturer at the source buy-off of ECSS-Q-ST-60-13C clause 4.3.6: confirm an independent inspector whose qualification is still current, check the mandatory evidence pack item by item instead of scoring it as a percentage, refuse a buy-off dated before lot acceptance testing finished, group the nonconformances so an open major holds the lot and a waiver closes one only with its reference, and authorize shipment only when every gate holds. Trigger: ecss, q-st-60-13c-clause-4-3-6, commercial-eee-source-buy-off, buy-off-evidence-pack, inspector-independence-check, open-major-nonconformance-hold, waiver-reference-closure, ship-or-hold-at-source."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-buy-off-inspection, commercial-eee-source-buy-off, buy-off-evidence-pack, inspector-independence-check, open-major-nonconformance-hold, waiver-reference-closure, ship-or-hold-at-source]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Parts -- Source Buy-Off Inspection (space-systems/ecss/q6013-class-1-buy-off-inspection)

Use when the task is the clause 4.3.6 final source inspection of
ECSS-Q-ST-60-13C: a lot of the highest assurance category is finished at
the manufacturer, and the buy-off decides whether it ships or is held
where it still sits.

## Domain quick reference

- A buy-off is the last point at which the lot and the people who built
  it are in the same room. Everything the inspection does not catch here
  is caught, if at all, after the parts have shipped, been kitted and in
  some cases already mounted.
- The inspector is part of the evidence. A qualification that lapsed
  before the inspection date, or an inspector drawn from the production
  organisation that built the lot, makes the record of the buy-off worth
  no more than the production record it was meant to witness.
- The mandatory evidence pack is a list of items, not a score.
  Traceability records, the lot acceptance report, the screening report,
  the packaging and marking evidence and the certificate of conformity
  each answer a different question, so a pack at five of six is a hold
  on the missing one, never a pass at eighty-three percent.
- Sequence carries information. A buy-off dated before lot acceptance
  testing finished inspected a lot the tests had not yet judged; the
  dates are checked against each other rather than each being checked
  for plausibility alone.
- Nonconformances are grouped by severity and by state. An open major
  holds the lot. A major is closed by an approved waiver only when the
  waiver reference is on the record -- a waiver asserted without one is
  an open major wearing a different word. Minors are tolerated up to a
  declared allowance, and that allowance is declared, not assumed.
- Optional evidence, the die photographs and the analysis reports that
  were offered rather than required, does not block a shipment; a thin
  showing is reported so the receiving side knows what it is getting.

## Workflow

1. Validate the inspection event: named inspector, named organisation,
   qualification expiry on or after the inspection date, and the
   independence flag that says whether the witness built the lot.
2. Check the buy-off date against the completion of lot acceptance
   testing and keep the signed day gap; a negative gap is a finding, not
   a rounding.
3. Walk the mandatory evidence pack and list every item absent or marked
   not-seen. Report the completeness share alongside the list, never
   instead of it.
4. Group the nonconformances into open majors, open minors, waived and
   closed; refuse a waived item carrying no waiver reference, and refuse
   a repeated identifier that would let one finding be counted twice.
5. Authorise shipment only when the evidence pack is whole, the
   inspector is independent and current, the sequence holds and no
   grouping is blocking. Otherwise hold at source and name every reason.
6. Add the thin-optional-evidence advisory where it applies, keeping it
   separate from the reasons that actually blocked.

## Pitfalls

- Turning the mandatory pack into a percentage. A percentage lets a
  missing certificate of conformity average away against five items that
  were present; the missing item is the finding.
- Accepting the production organisation's own inspector because the
  paperwork is in order. The paperwork is what the independent witness
  is there to test, so the witness cannot come from the organisation
  that produced it.
- Treating a claimed waiver as a closure. Without the approved waiver
  reference on the record there is nothing to audit later, and the
  nonconformance is still open.
- Checking each date for plausibility but never against the other. Both
  dates can be valid and still be in the wrong order, which is the case
  that matters.
- Letting a thin optional-evidence showing block the shipment, or
  letting it disappear. It is an advisory: reported, listed separately,
  and not mixed into the blocking reasons.

## Behavior contract (gate 3)

The inspector validation, evidence-pack walk, date-sequence check,
nonconformance grouping, waiver-reference refusal and the overall
ship-or-hold disposition are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_buy_off_inspection.py against
scripts/q6013_class_1_buy_off_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_buy_off_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
