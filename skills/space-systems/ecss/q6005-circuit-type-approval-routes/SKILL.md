---
name: q6005-circuit-type-approval-routes
description: "Determine which ECSS-Q-ST-60-05C clause 7.3 approval route a hybrid circuit type has to travel: a full new-design approval, an extension of an already approved type, a bounded delta approval, or an administrative change record. Use when a candidate hybrid design is set against a predecessor and the question is how much of that predecessor's approval still carries. Weigh each declared departure by category, force the new-design sequence on any envelope-critical departure or a predecessor approval that is lapsed or superseded, name the departure that escalated the route, and attach the evidence that route owes. Trigger: ecss, q-st-60-hybrid-scope, hybrid-circuit-type-approval-route, approved-type-extension, hybrid-delta-approval, envelope-critical-departure, predecessor-approval-currency, hybrid-departure-score."
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
  tags: [ecss, q-st-60-hybrid-scope, q6005-circuit-type-approval-routes, hybrid-circuit-type-approval-route, approved-type-extension, hybrid-delta-approval, envelope-critical-departure, predecessor-approval-currency, hybrid-departure-score]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Circuit Type Approval Routes (space-systems/ecss/q6005-circuit-type-approval-routes)

Use when the task is the routing decision of ECSS-Q-ST-60-05C clause 7.3
-- choosing, before any approval work is scheduled, which of the
alternative paths to formal approval a hybrid circuit design is actually
entitled to, given what an already approved predecessor still covers.

## Domain quick reference

- Clause 7.3 does not offer one way in. It offers several, and the route
  is not a preference: it falls out of the relationship between the
  candidate design and an approved predecessor. Picking the light route
  first and arguing the relationship afterwards is the failure this
  clause exists to prevent.
- The routes, lightest to heaviest: an administrative change record when
  nothing technical moved; a delta approval when the departure is small
  and bounded and can be evaluated against the predecessor evidence; an
  extension of the approved type when the departure is real but the
  predecessor still carries most of the case, paid for with added
  qualification; and the full new-design sequence when nothing carries
  over at all.
- The predecessor has to be current. An approval that has lapsed, or
  that was superseded by a later configuration, carries nothing forward,
  so a candidate leaning on it is a new design however small its
  departure looks on paper.
- Every declared departure carries a weight by category -- die
  technology and substrate technology at the top, a passive trim value
  at the bottom -- and the weights of the uncovered departures add up to
  a departure score that the route thresholds read.
- Some categories are envelope-critical: they leave what the predecessor
  qualification actually demonstrated. Die technology, substrate
  technology and the interconnection method are of that kind, and one of
  them alone forces the new-design sequence no matter how low the score
  lands.
- A departure can be held inside the predecessor envelope, but only
  against cited evidence. A coverage claim with no reference is not a
  coverage claim, and the score has to carry the departure in full.
- The score also names the business case: the heaviest uncovered
  departure is the one to challenge first, because withdrawing it is
  usually what drops the route a whole tier.

## Workflow

1. Declare the predecessor state -- none, current, superseded or lapsed
   -- and reject an uncategorized value rather than assuming the
   approval is live, because every downstream tier depends on it.
2. Declare each departure from the predecessor by category. A departure
   claimed as already covered needs the reference to the evidence that
   covers it; reject the claim otherwise.
3. Add the weights of the uncovered departures into a departure score,
   and list separately any uncovered departure in an envelope-critical
   category.
4. Select the route: the new-design sequence when the predecessor is not
   current, when an envelope-critical departure stands, or when the
   score passes the extension ceiling; otherwise the tier the score
   falls in.
5. Attach the evidence the selected route owes, and state the driver
   that put it there so the decision can be re-argued on the facts
   rather than re-litigated on preference.
6. Name the heaviest uncovered departure and the route that would apply
   without it, so the project can see what a design change would buy
   before it commits to the heavier path.

## Pitfalls

- Choosing the route first and fitting the departure list to it. The
  route is an output of the relationship to the predecessor, and one
  chosen ahead of the categorization has no traceable justification.
- Leaning on a lapsed or superseded predecessor approval. It reads like
  an approval in the file and carries nothing at all, so a delta
  argument built on it is a new design that has not been costed.
- Reading a low departure score as permission. An envelope-critical
  departure outranks the score entirely: a die technology change scores
  once but leaves everything the predecessor qualification demonstrated.
- Accepting a coverage claim without the evidence reference. A departure
  waved off as already qualified, with nothing cited, silently removes
  its whole weight from the score and can drop the route two tiers.
- Counting the new-design route as the top of the delta ladder. It is a
  different set of obligations, not a longer one -- there is no
  predecessor evidence to add to -- so an obligation count is not the
  way to compare the two.

## Behavior contract (gate 3)

The change validation, departure scoring, envelope-critical detection,
route selection, evidence obligations and withdrawal analysis are
exercised by the gate 3 contract test:
scripts/test_q6005_circuit_type_approval_routes.py against
scripts/q6005_circuit_type_approval_routes_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_circuit_type_approval_routes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
