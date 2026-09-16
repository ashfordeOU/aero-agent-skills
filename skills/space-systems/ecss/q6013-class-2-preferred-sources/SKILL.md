---
name: q6013-class-2-preferred-sources
description: "Use when a Class 2 build has to justify where a commercial part came from. Evaluate where a commercial EEE part is sourced from against the preferred-manufacturer and qualified-listing direction the intermediate assurance class gives under ECSS-Q-ST-60-13C clause 5.2.2.3: grade the declared source tier, test the traceability chain and let a declared incoming counterfeit-detection inspection cover one gap but never two, weigh change-notice cover, line changes since the evidence was taken and date-code age against the shelf policy, build a sourcing assurance index, pick a disposition, and list the added evaluation each step away from the preferred end buys. Trigger: ecss, q-st-60-13c-clause-5-2-2-3, class-two-preferred-sources, qualified-parts-listing-sourcing, commercial-part-traceability-chain, counterfeit-inspection-chain-substitution, lot-date-code-shelf-policy, sourcing-assurance-index, open-market-broker-refusal."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-preferred-sources, class-two-preferred-sources, qualified-parts-listing-sourcing, commercial-part-traceability-chain, counterfeit-inspection-chain-substitution, lot-date-code-shelf-policy, sourcing-assurance-index, open-market-broker-refusal]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Preferred Sources (space-systems/ecss/q6013-class-2-preferred-sources)

Use when the task is the sourcing direction of ECSS-Q-ST-60-13C clause
5.2.2.3 at the intermediate assurance class: a commercial part has been
proposed, the question is whether it comes from a preferred enough
source to be bought, and what has to be added to the part when it does
not.

## Domain quick reference

- The direction is the same one the class above gives -- source at
  preferred manufacturers and at part numbers already carried on a
  qualified listing. What the intermediate class changes is the answer
  when the direction cannot be followed: a step away from the preferred
  end is bought back with added evaluation rather than ending the
  discussion.
- Source tier, strongest to weakest: qualified-parts-listing (the part
  number sits on the listing), preferred-manufacturer (the maker is on
  the preferred list, on a line declared for space use),
  assessed-manufacturer (audited, not preferred),
  franchised-distributor (the maker's authorised channel, the maker
  itself unaudited), and independent-broker (an open-market
  intermediary with no authorised link back to the maker).
- The broker tier is still the one the ladder cannot carry on its own.
  Nothing connects the delivered date code to a line anyone has
  visibility of, so the tier is refused outright unless an incoming
  counterfeit-detection inspection is declared, and even then it never
  rises above full upscreening.
- Three records make the traceability chain: the maker's lot record,
  the distribution chain record and the project receipt record. This
  class lets a declared incoming counterfeit-detection inspection stand
  in for exactly one of them. Two gaps cannot be covered -- a
  substitution standing in for most of the chain is not a chain, and
  the fraction says so.
- Line stability carries what is left: whether the project is
  subscribed to the maker's process change notices, and how many line
  changes have landed since the evidence being relied on was taken.
  Each change loosens the tie between that evidence and this delivery.
- Lot date-code age is weighed against the project shelf policy. Age
  inside the policy costs nothing; past it the stability credit ramps
  down over a fixed window and solderability has to be re-verified on
  the delivered lot.
- The assurance index is a weighted blend of tier, chain completeness
  and line stability. It is a policy instrument rather than a physical
  constant, so it is reported next to the index fully preferred
  sourcing would have earned, and the gap is the argument.

## Workflow

1. Declare the source tier, the chain records actually held, whether an
   incoming counterfeit-detection inspection is in place, the change
   notice subscription state, the line-change count since the evidence
   was taken, and the lot date-code age against the shelf policy.
   Reject an uncategorized tier rather than defaulting it.
2. Test the chain first. Name each missing record, apply the single
   permitted substitution where one gap qualifies for it, and carry the
   completeness fraction forward; a strong tier never papers over a gap.
3. Resolve line stability from the subscription state, the line-change
   count and the shelf-policy penalty on the date code.
4. Build the sourcing assurance index from the three weighted parts and
   report it beside the index fully preferred sourcing would earn.
5. Pick the disposition: accept-as-directed, accept-with-added-
   evaluation, accept-with-full-upscreening, or reject-source. Apply
   the hard rules ahead of the index -- an unscreened broker source is
   refused at any index, a screened one is capped at upscreening, and a
   chain still broken after the substitution cannot reach directed.
6. List the added evaluation the weak parts of the source buy: raising
   the part onto the qualified listing, auditing the maker, recovering
   a missing record, recording the inspection that covered a gap,
   opening a change notice subscription, working off the line changes,
   or re-verifying solderability on an aged date code.

## Pitfalls

- Reading the intermediate class as permission to skip the ladder. The
  tier still sets half the index; the class changes what a weak tier
  costs, not whether the tier is graded.
- Letting the incoming inspection cover a second chain gap. One
  substitution is a compensating record, two are a replacement for the
  chain, and the class only allows the first.
- Accepting a qualified-listing part number on a delivery whose chain
  is broken. The listing is a statement about a part number on a known
  line; without the lot and receipt records nothing ties this box of
  parts to it.
- Treating a process change notice subscription as evidence of
  stability. The subscription only means changes will be heard about;
  changes already landed since the evidence was taken still have to be
  worked off one by one.
- Letting a date code inside the shelf policy imply a fresh lot. The
  policy sets where the penalty starts, not where ageing starts, so a
  lot near the limit deserves the solderability check it is not yet
  compelled to have.
- Comparing the index with a threshold by bare arithmetic. The index is
  a weighted sum of floats, so a case built to sit exactly on a
  threshold can land a few units in the last place below it; the
  comparison absorbs that representation error while the threshold
  stays untouched.

## Behavior contract (gate 3)

The tier grading, chain completeness and its single permitted
substitution, shelf-age penalty, line stability, assurance index,
disposition hard rules and added-evaluation list are exercised by the
gate 3 contract test:
scripts/test_q6013_class_2_preferred_sources.py against
scripts/q6013_class_2_preferred_sources_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_preferred_sources.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
