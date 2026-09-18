---
name: q6005-chip-supplier-selection-criteria
description: "Evaluate whether a proposed source of bare semiconductor or passive chips is acceptable under ECSS-Q-ST-60-05C clause 8.1.2: categorize the route as the original die manufacturer, a franchised distributor or an independent reseller, count the intermediaries between the wafer line and the buyer, then test the quality-system approval, the audit currency, the wafer-lot traceability chain and the process-change-notification commitment against veto criteria that no merit score can outrank, returning acceptable, acceptable-with-conditions or refused with every failing criterion named. Use when judging a chip source, a reseller offer or an untraceable die stock. Trigger: ecss, q-st-60-05c, bare-die-source-acceptability, chip-supplier-audit-currency, wafer-lot-traceability-chain, independent-reseller-die-stock, chip-process-change-notification, chip-source-veto-criteria."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-chip-supplier-selection-criteria, bare-die-source-acceptability, chip-supplier-audit-currency, wafer-lot-traceability-chain, independent-reseller-die-stock, chip-source-veto-criteria]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Chips — Source Acceptability (space-systems/ecss/q6005-chip-supplier-selection-criteria)

Use when the task is deciding whether a proposed source of bare
semiconductor or passive chips may be bought from at all under
ECSS-Q-ST-60-05C clause 8.1.2 — the basis on which a chip source is
judged acceptable, before any purchase specification is written or any
delivered lot is inspected.

## Domain quick reference

- A bare chip carries none of the identity a packaged part carries. There
  is no body marking, no date code moulded into a case and no lead frame
  to inspect, so everything known about a die is known from its source
  and the paperwork the source keeps. Source acceptability is therefore
  not a commercial preference, it is the only evidence chain there is.
- The supply route is the first discriminator. The manufacturer that ran
  the wafer line holds the process history directly. A distributor under
  a franchise agreement with that manufacturer passes it through with an
  accountable link. An independent reseller holding stock it did not
  produce has neither, and has to make the gap up with upscreening
  evidence of its own.
- Chain depth matters separately from category. Each intermediary is a
  place where die from two wafer lots can be commingled, relabelled or
  substituted, and the buyer can only audit as far down the chain as the
  agreements reach. A chain deeper than that limit is not a weaker
  source, it is an unauditable one.
- Some criteria are vetoes, not weights. An unapproved quality system, a
  die that cannot be traced back to the wafer lot that produced it, an
  audit that has aged out of its validity window, an unauditable chain
  depth and an independent reseller with no upscreening evidence each
  refuse the source outright. Commercial merit, price and lead time do
  not trade against them.
- What is left after the vetoes is genuinely a weighted judgement: the
  route category, a process-change-notification commitment so the buyer
  learns of a die shrink or a mask revision, and the ability to deliver
  the whole quantity from one wafer lot. These move a source between
  acceptable and acceptable-with-conditions, never into acceptable from
  refused.
- A refused source is told what would change the answer. Most vetoes are
  recoverable — an audit can be re-run, a traceability record can be
  produced — and a refusal that does not name its criteria cannot be
  acted on by procurement or reviewed by the customer.

## Workflow

1. Validate the source record: a named source, the chain of
   intermediaries between the wafer line and the buyer (empty when the
   purchase is direct), the age of the source audit, and the boolean
   evidence items. A missing chain key is an input error, not an assumed
   direct purchase.
2. Categorize the route from the chain itself: no intermediary is the
   original manufacturer; an intermediary holding a franchise agreement
   is a franchised distributor; any other intermediary is an independent
   reseller. A franchise flag on a direct purchase does not demote it.
3. Evaluate the audit currency against the declared validity window,
   absorbing floating-point representation error at the boundary with a
   named tolerance rather than by shortening the window.
4. Apply the veto criteria in order and collect every one that fails,
   not merely the first. A source failing three criteria has three
   things to fix and needs to be told all three.
5. Score the remaining merit attributes only when no veto fired: the
   category weight plus the process-change-notification commitment plus
   the single-wafer-lot capability, pinned to the top of the range so a
   binary sum of decimal weights cannot report above one.
6. Dispose: any veto returns refused; a score at or above the acceptance
   threshold returns acceptable; anything else returns
   acceptable-with-conditions together with the ordered list of
   attributes the source still owes.
7. Report the category, the chain depth, the audit state, the score
   against its threshold, and the veto and condition lists, so the
   decision can be reproduced without re-reading the source file.

## Pitfalls

- Treating an approved quality system as sufficient. Approval is one
  veto criterion among five; a source with an excellent quality system
  and no wafer-lot traceability is still refused, because the die cannot
  be tied to the process history the approval covers.
- Letting a good price or a short lead time offset a veto. The weighted
  score exists only for sources that already cleared every veto;
  applying it earlier converts a hard criterion into a soft one and is
  the exact failure the clause is written to prevent.
- Reading a franchise agreement as equivalent to a direct purchase. The
  franchised route is accountable but still has an intermediary in it,
  so it scores below the direct route and still owes the manufacturer's
  own conformity evidence through the chain.
- Reporting only the first failing criterion. Procurement acts on the
  full list; a source refused for an aged audit alone will re-audit,
  come back, and be refused a second time for the traceability gap that
  was never named.
- Assuming an empty chain because the chain field was absent. A missing
  field is unknown, not zero, and defaulting it to a direct purchase
  silently promotes a reseller offer into the highest-confidence
  category.
- Judging a source once and reusing the verdict. The audit ages, the
  chain can gain an intermediary and a die can be moved to another
  wafer line, so the assessment is re-run against the window in force at
  the time of the order.

## Behavior contract (gate 3)

The source-record validation, route categorization, audit-window
evaluation, the five veto criteria, the merit score and the three-way
disposition are exercised by the gate 3 contract test:
scripts/test_q6005_chip_supplier_selection_criteria.py against
scripts/q6005_chip_supplier_selection_criteria_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_chip_supplier_selection_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
