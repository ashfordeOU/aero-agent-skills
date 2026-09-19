---
name: q7046-procurement-requirements
description: "Evaluate a threaded-fastener procurement package against the ECSS procurement clause: qualified source, purchase data, certificates. Use when an ECSS-Q-ST-70-46C fastener order has to be judged fit to place or a delivered lot fit to accept: confirm the manufacturer holds a qualification live on the delivery date whose scope covers the ordered category, score the purchase-data items the order carries against the required set and name the omissions, match every certificate to the order lot and check it was issued no later than delivery and signed, then return one goods-in disposition of release, hold or reject with the reasons behind it. Trigger: ecss, q-st-70-46-threaded-fastener-scope, fastener-procurement-requirements, fastener-qualified-source-check, fastener-purchase-data-completeness, fastener-lot-certificate-match, fastener-goods-in-disposition."
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
  tags: [ecss, q-st-70-46-threaded-fastener-scope, q7046-procurement-requirements, fastener-procurement-requirements, fastener-qualified-source-check, fastener-purchase-data-completeness, fastener-lot-certificate-match, fastener-goods-in-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Procurement Requirements (space-systems/ecss/q7046-procurement-requirements)

Use when the task is the procurement clause of ECSS-Q-ST-70-46C — deciding
whether a fastener order may be placed with a given manufacturer, whether the
order carries the data the lot has to be reproducible by, and whether the
delivered lot arrived with certificates that actually tie back to it.

## Domain quick reference

- Procurement of a flight fastener is three separate gates, not one. The
  source has to be qualified, the purchase data has to be complete, and the
  certificates have to match the lot. A package can pass any two and still be
  unusable, so the three are scored separately and only then combined.
- A qualification is not a badge, it is a scope with an expiry. A
  manufacturer qualified for one fastener category is not thereby qualified
  for another, and a qualification that lapses between order and delivery
  leaves the delivered lot unsupported even though the order was placed
  correctly. Both the scope and the delivery-date validity are checked.
- The purchase data is what makes the lot reproducible: designation,
  governing standard, material and condition, property class, surface
  treatment, lot identification, the certificates demanded, and the incoming
  inspection level. An omitted item is a named finding, never a default the
  buyer quietly supplies.
- A certificate that cites a different lot is not a paperwork slip, it is
  evidence about other hardware. Likewise a certificate dated after delivery
  documents something the receiving inspection could not have relied on.
- The three gates produce different dispositions. An unqualified or
  out-of-scope source is a reject: no amount of paperwork repairs it.
  Incomplete data or a certificate mismatch is a hold: the lot stays in
  quarantine while the omission is closed.

## Workflow

1. Validate the order itself — category, lot identifier, quantity, delivery
   date — before any judgement is made about the package around it.
2. Check the manufacturer: qualification status, scope coverage of the
   ordered category, and days of validity remaining on the delivery date.
   Keep the sign of that remainder, because it says how far the lapse ran.
3. Score the purchase data against the required item set and return both the
   completeness ratio and the named omissions, so a package one item short is
   distinguishable from one that was never written.
4. Check each certificate against the order: right kind, right lot, issued no
   later than delivery, signed by a named authority. Collect the kinds that
   have no acceptable certificate behind them.
5. Combine the three into a single disposition and carry every reason
   forward, so the quarantine note says what has to be closed.

## Pitfalls

- Reading a qualification as valid because the order date fell inside it. The
  lot is accepted at delivery, so the validity is tested there; an order
  placed inside the window and delivered outside it is still unsupported.
- Accepting a source qualified for a neighbouring category. Thread form,
  material condition and head style all change the process that was audited,
  so scope coverage is an explicit check and not an inference from the name.
- Treating purchase-data completeness as a percentage to negotiate. The
  ratio is a reporting aid; the disposition turns on whether anything at all
  is missing, and a blank field counts as missing just as an absent key does.
- Letting a certificate with the wrong lot identifier through because the
  part number matches. The lot is the traceable unit, and a mismatch means
  the evidence belongs to hardware that was not delivered.
- Collapsing hold and reject into one failure. A hold is closable by the
  supplier; a reject is not, and merging them loses the only information the
  goods-in note carried.
- Comparing the completeness ratio for exact equality with one. It is a
  float built from a division, so the whole-ratio comparison absorbs
  representation error while the required item set stays untouched.

## Behavior contract (gate 3)

The order validation, source qualification and scope check, purchase-data
completeness scoring, per-certificate and pack-level certificate matching,
and the combined goods-in disposition are exercised by the gate 3 contract
test: scripts/test_q7046_procurement_requirements.py against
scripts/q7046_procurement_requirements_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7046_procurement_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
