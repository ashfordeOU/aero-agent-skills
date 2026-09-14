---
name: q6013-class-1-preferred-sources
description: "Assess where a commercial EEE part is sourced from against the preferred-manufacturer and preferred-parts-listing tiers a Class 1 highest-assurance build demands under ECSS-Q-ST-60-13C clause 4.2.2.3: grade the declared source tier, test the traceability chain from maker through authorised distributor to project receipt, weigh process-change-notice cover, line changes since the evidence was taken and lot date-code age against the shelf policy, then build a sourcing assurance index, pick a disposition, and list the added evaluation each step away from the preferred end buys. Use when a Class 1 build has to justify where a commercial part came from. Trigger: ecss, q-st-60-13-commercial-eee-scope, class-1-preferred-sources, preferred-manufacturer-tier, preferred-parts-listing-sourcing, commercial-part-traceability-chain, lot-date-code-age, sourcing-assurance-index, broker-sourced-part-rejection."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-preferred-sources, class-1-commercial-part-sourcing, preferred-manufacturer-tier, preferred-parts-listing-sourcing, commercial-part-traceability-chain, lot-date-code-age, sourcing-assurance-index, broker-sourced-part-rejection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 1 Preferred Sources (space-systems/ecss/q6013-class-1-preferred-sources)

Use when the task is the sourcing direction of ECSS-Q-ST-60-13C clause
4.2.2.3 -- deciding, for the highest-assurance Class 1 case, whether a
candidate commercial part comes from a preferred enough source to be
used at all, and what has to be added when it does not.

## Domain quick reference

- On a Class 1 build, where the part came from is a design decision
  rather than a purchasing detail. Sourcing is directed at the
  preferred end of a tier ladder, and every step away from that end is
  bought back with added evaluation rather than waved through.
- Source tier, strongest to weakest: preferred-parts-listing (the part
  number sits on the project or agency listing), preferred-manufacturer
  (the maker is on the preferred list, on a line declared for space
  use), assessed-manufacturer (audited, not preferred),
  franchised-distributor (the maker's authorised channel, the maker
  itself unassessed), and independent-broker (an open-market
  intermediary with no authorised link back to the maker).
- The broker tier is not a weak source, it is an absent one. Nothing
  connects the delivered date code to a line the project has any
  visibility of, so no index and no amount of screening turns it into a
  Class 1 source; the answer is to re-source.
- Three records make the traceability chain: the maker's lot record,
  the distribution chain record, and the project receipt record. A
  Class 1 build needs all three. A gap in any one caps the disposition
  below preferred however strong the tier is, because a preferred tier
  that cannot be tied to this delivery is a claim about someone else's
  parts.
- Line stability carries what is left: whether the project is
  subscribed to the maker's process change notices, and how many line
  changes have landed since the evidence being relied on was taken.
  Each change loosens the tie between the evidence and the delivery.
- Lot date-code age is weighed against the project shelf policy. Age
  inside the policy costs nothing; past it the stability credit ramps
  down and solderability has to be re-verified on the delivered lot.
- The assurance index is a weighted blend of tier, chain completeness
  and line stability. It is a policy instrument, not a physical
  constant, so it is reported with the thresholds that read it.

## Workflow

1. Declare the source tier, the chain records actually held, the change
   notice subscription state, the line-change count since the evidence
   was taken, and the lot date-code age. Reject an uncategorized tier
   rather than defaulting it -- every downstream number depends on it.
2. Test the chain first. Name each missing record as a finding and
   carry the completeness fraction forward; do not let a strong tier
   paper over a gap.
3. Resolve line stability from the subscription state, the line-change
   count and the shelf-policy penalty on the date code.
4. Build the sourcing assurance index from the three weighted parts and
   report it alongside the index the same part would earn from fully
   preferred sourcing, so the gap is visible as a number.
5. Pick the disposition: accept-as-preferred, accept-with-added-
   evaluation, accept-with-full-upscreening, or reject-source. Apply
   the hard rules before the index -- a banned tier is rejected at any
   index, and a broken chain cannot reach preferred.
6. List the added evaluation the weak parts of the source buy: raising
   the part onto the listing, auditing the maker, construction
   analysis, lot acceptance, recovering a missing record, opening a
   change notice subscription, re-taking evidence against the current
   line, or re-verifying solderability on an aged date code.

## Pitfalls

- Reading a franchised distributor as an assessed maker. The authorised
  channel proves the route, not the line: the maker behind it may never
  have been audited, so the tier credit stops at the channel.
- Accepting a preferred-listing part number on a delivery whose chain
  is broken. The listing is a statement about a part number on a known
  line; without the lot and chain records nothing ties this box of
  parts to it.
- Treating a process change notice subscription as evidence of
  stability. The subscription only means changes will be heard about.
  Changes that have already landed since the evidence was taken still
  have to be worked off one by one.
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

The tier grading, chain completeness, shelf-age penalty, line stability,
assurance index, disposition rules and added-evaluation list are
exercised by the gate 3 contract test:
scripts/test_q6013_class_1_preferred_sources.py against
scripts/q6013_class_1_preferred_sources_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_preferred_sources.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
