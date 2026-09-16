---
name: q6013-class-3-preferred-sources
description: "Use when a Class 3 buy has more than one offer and the preferred-source order has to be shown. Determine which commercial manufacturer or distributor a Class 3 procurement should buy a part from under ECSS-Q-ST-60-13C clause 6.2.2.3: score each candidate source on its supply tier, the chain of traceability back to the maker, its quality-system evidence, date-code age, single-lot delivery and counterfeit screening, order them, and state the conditions a non-preferred source has to meet. Trigger: ecss, q-st-60-13-commercial-eee-scope, class-3-preferred-source-order, franchised-distributor-preference, open-market-broker-last-resort, commercial-part-supply-chain-traceability, commercial-part-counterfeit-screening, commercial-part-date-code-age-limit."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-3-preferred-sources, class-3-preferred-source-order, franchised-distributor-preference, open-market-broker-last-resort, commercial-part-supply-chain-traceability, commercial-part-counterfeit-screening, commercial-part-date-code-age-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 3 Preferred Sources (space-systems/ecss/q6013-class-3-preferred-sources)

Use when the task is the sourcing preference of ECSS-Q-ST-60-13C
clause 6.2.2.3 -- choosing which of several offered commercial
manufacturers or distributors a Class 3 part is actually bought from,
and what a source further down the order still has to bring.

## Domain quick reference

- A Class 3 part carries the least assurance of any category, so most
  of the confidence a project has in it comes from where it was bought
  rather than from anything done to it afterwards. That is why the
  clause sets an order over sources at all.
- The order runs outwards from the maker: the maker itself, then a
  franchised distributor drawing stock from the maker, then a
  subcontractor building to the maker's flow, then an independent
  distributor, and last an open-market broker. Each step adds a
  handling link that can substitute, relabel or mix lots.
- Distance from the maker is not the whole answer, only the starting
  point. A franchised distributor with an unbroken chain, a certified
  quality system, a single lot and a young date code can beat a
  nearer source that brings none of those, and the scoring has to let
  it.
- Two conditions are a floor rather than a deduction. A source with no
  traceability at all cannot tie the delivered population to a line,
  and an open-market broker with no counterfeit screening is the
  textbook counterfeit route. Neither is admissible at any score.
- Date-code age matters because a commercial part was never stored for
  a space programme. Beyond the limit the project sets, solderability
  is the first thing to go, and the condition is a verification rather
  than a rejection.
- The buy has to show it worked down the order. The useful output is
  therefore the ordered list with the preferred source named, the
  margin over the runner-up, and the conditions each other offer
  carries -- not a single winner with no working shown.

## Workflow

1. Declare every offer: source tier, traceability chain, quality
   system, single-lot delivery, counterfeit screening, and date-code
   age. Reject an incompletely declared offer rather than scoring the
   gaps as zero silently.
2. Set the date-code age limit the project works to. It is a project
   parameter, not a constant, and it belongs in the record.
3. Score each offer in whole points -- a tier base plus the evidence it
   brings -- so the ordering is exact and reproducible rather than a
   float comparison between near-equal offers.
4. Apply the two floors before the ordering matters: no traceability,
   or open-market supply with no counterfeit screening, is not
   admissible whatever else the offer carries.
5. Order the offers by points, breaking a tie towards the tier nearer
   the maker and then by name, and take the highest-scoring admissible
   one as preferred.
6. Report the margin over the runner-up and the conditions every other
   offer would have to meet, so a later change of supply can be judged
   against the same scale.

## Pitfalls

- Buying on tier alone. The tier is the starting point, and a nearer
  source with no chain, no quality system and a five-year-old date
  code is worse than a franchised one that brings all three.
- Treating the counterfeit screen as a deduction on a broker offer. For
  open-market supply it is the floor: without it the offer is not in
  the comparison at all.
- Scoring a missing declaration as zero. A gap in the offer is an
  unanswered question about the supply chain, and folding it into the
  arithmetic hides it behind a number.
- Reporting only the winner. The clause asks for the order to be
  worked down, so the runner-up, the margin and the conditions are the
  evidence; the winning name alone is a conclusion with no working.
- Ordering by a normalized float. Two offers that differ by one point
  can compare equal after division, so the ordering is done on the
  whole-point total and the normalized value is reported, never used
  to decide.
- Comparing a date-code age with its limit by bare arithmetic. The age
  is a difference of two dates in months while the limit is a single
  declared number, so an age built to land exactly on the limit can sit
  a few units in the last place above it; the comparison absorbs that
  representation error while the limit stays untouched.

## Behavior contract (gate 3)

The candidate validation, the tier ordering, the whole-point scoring of
tier, traceability chain, quality system, single-lot delivery,
counterfeit screening and date-code age, the two admissibility floors,
the ordering with its tie break, and the preferred-source, runner-up
and margin reporting are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_preferred_sources.py against
scripts/q6013_class_3_preferred_sources_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_preferred_sources.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
