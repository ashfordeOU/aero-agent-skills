---
name: e2008-pva-hardware-delivery
description: "Use when a PVA shipment, delivery lot, dispatch note or documentation package has to be released together. Audit a photovoltaic assembly delivery against clause 5.8 of ECSS-E-ST-20-08C: reconcile the ordered quantity against the serials actually shippable, hold every delivery document to issued status and to the lot that is physically leaving, disposition each serial from its conformance state and its build standard, measure the released share of the documentation package, and return one lot verdict. Trigger: ecss, e-st-20-08c, pva-hardware-delivery, pva-delivery-documentation-package, pva-delivery-quantity-reconciliation, pva-certificate-of-conformity-release, pva-as-built-configuration-record, pva-delivery-lot-release-verdict."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-pva-hardware-delivery, e-st-20-08c, pva-hardware-delivery, pva-delivery-documentation-package, pva-delivery-quantity-reconciliation, pva-certificate-of-conformity-release, pva-as-built-configuration-record, pva-delivery-lot-release-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Hardware Delivery (space-systems/ecss/e2008-pva-hardware-delivery)

Use when the task is clause 5.8 of ECSS-E-ST-20-08C: the ordered
photovoltaic assembly hardware ships, and it ships together with the
documentation package the preceding clause already demanded. This leaf
holds the crate and the paperwork to each other and names every reason
the lot is not yet releasable.

## Domain quick reference

- A delivery has three arms and they fail differently. The quantity arm
  asks how many serials are actually shippable against the order; the
  documentation arm asks whether the required package is present,
  issued and pointed at the right lot; the hardware arm dispositions
  each serial. A full crate with a draft certificate and a complete
  document set covering last month's lot are different problems with
  different recoveries, so they are measured separately and only then
  folded into one verdict.
- A document is only released when it is at issued status AND cites the
  lot that is leaving. A draft is not a document; an issued document
  for the previous lot is worse than an absent one, because it looks
  complete to anyone counting sheets rather than reading them.
- The required package is fixed: the as-built configuration record, the
  certificate of conformity, the acceptance test report, the
  non-conformance record, the parts and materials list, and the
  handling and storage instruction. The released share is measured
  against that full set, not against what happens to be in the folder,
  so an absent document lowers the share exactly as a draft one does.
- A serial is dispositioned from its conformance state: conforming
  ships, a waived non-conformance ships on the waiver, an open
  non-conformance is held. The build standard overrides all three --
  an item built to a superseded standard is held even when it is
  otherwise conforming, because the lot ships to one standard.
- Partial delivery is declared project policy, not a physical fact. The
  default accepts a shipment down to a declared share of the order; a
  project that forbids partial delivery turns the same lot into a hold
  with no change to the hardware.
- Over-delivery is reported rather than silently accepted. More serials
  than were ordered still satisfies the quantity arm, but the receiving
  end has to know it happened.

## Workflow

1. Read the lot reference and the build standard the lot ships to.
   Reject a case that declares neither, rather than assuming the first
   item's standard applies to the rest.
2. Disposition each serial from its conformance state, then override to
   held when its build standard differs from the lot standard. Reject a
   repeated serial instead of counting it twice.
3. Assess each document against the shipping lot: issued and matching
   is released, anything else is not, and the reason is recorded.
4. Count the required documents actually released as a share of the
   full set, and list the ones absent from the package by name.
5. Reconcile the shippable count against the ordered quantity: report
   the delivered share, flag over-delivery, and apply the partial
   delivery policy only when the shipment is short.
6. Release the lot only when the quantity arm and the documentation arm
   both accept. Return the grouped serials, the held ones by name, and
   every finding from all three arms.

## Pitfalls

- Counting sheets rather than reading them. A package with all six
  documents present can have every one of them citing the previous
  lot, and a check that only tests presence reports it as complete.
- Treating a draft as a document pending signature. It is not released,
  it lowers the released share, and a lot that ships against it has no
  conformity evidence at the receiving end.
- Letting a held serial quietly shrink the order. A shipment of three
  against an order of four is a partial delivery decision, not a
  rounding detail, and it has to be tested against the declared policy.
- Assuming a conforming item is shippable. Conformance and build
  standard are independent; an item conforming to a superseded standard
  is the classic mixed-lot defect and is held on the standard alone.
- Judging a delivered share that lands exactly on the partial-delivery
  limit by bare arithmetic. The share is a ratio of two counts and the
  limit is a round percentage, so a shipment meant to sit on the limit
  can land a few units in the last place below it; the comparison
  absorbs that while the limit stays as declared.
- Silently absorbing over-delivery. It passes the quantity arm, but an
  unannounced extra serial has no acceptance evidence travelling with
  it and no place in the receiving inventory.

## Behavior contract (gate 3)

The document release test, the documentation package share, the serial
disposition, the build-standard override, the quantity reconciliation
with its partial-delivery policy and the rolled-up lot verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_pva_hardware_delivery.py against
scripts/e2008_pva_hardware_delivery_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_pva_hardware_delivery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
