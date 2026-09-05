---
name: fault-tree-importance-measures
description: "Use when you must rank basic events of a fault tree by importance: compute the Birnbaum measure, the Fussell-Vesely measure, the risk achievement worth (RAW) and the risk reduction worth (RRW) of each basic event from the minimal cut sets and the basic-event probabilities, sort the events by each measure, and flag the dominant contributors above a Fussell-Vesely threshold. Produces the per-event measure dict, the sorted rank list and the dominance list that gate risk-reduction prioritization. Trigger: basic event ranking, birnbaum importance, fussell-vesely importance, risk achievement worth, risk reduction worth, top event sensitivity, dominant contributor."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: arp4761a
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [fault-tree-importance-measures, birnbaum-importance, fussell-vesely-importance, risk-achievement-worth, risk-reduction-worth, basic-event-ranking, top-event-sensitivity]
  version: 0.1.0
  author: AeroSkills
---

# Fault Tree Importance Measures (systems-engineering-safety/arp4761a/fault-tree-importance-measures)

Use when you must rank the basic events of a fault tree by their
contribution to the top event probability. This leaf computes the four
standard importance measures, Birnbaum, Fussell-Vesely, risk
achievement worth (RAW) and risk reduction worth (RRW), for every basic
event from the minimal cut sets and the basic-event probabilities, then
sorts the events by each measure and flags the dominant contributors.
It pairs with systems-engineering-safety/arp4761a/fta-fmea, which
produces the minimal cut sets and event probabilities this leaf ranks;
the outputs (rank lists, dominance flags) gate risk-reduction
prioritization inside the ARP4761A quantitative safety assessment flow.
All logic is deterministic, offline, pure stdlib.

## Domain quick reference

- Inputs: cut_sets, a list of sets of basic-event names (one set per
  minimal cut set), and probs, a dict mapping every basic-event name to
  a probability in (0, 1).
- Top event probability Q: probability of the union of the cut sets
  under event independence, Q = sum over non-empty subsets of the cut
  sets of (-1)^(k+1) times the product of the event probabilities in
  the union of that subset (exact inclusion-exclusion over 2^n - 1
  subsets, n = number of cut sets).
- Birnbaum measure of event e: B_e = Q(q_e = 1) - Q(q_e = 0), the
  change in top probability when the event probability moves from 0 to
  1, evaluated by re-computing the union with the event forced true and
  then forced false.
- Fussell-Vesely measure: FV_e = (Q - Q(q_e = 0)) / Q, the fraction of
  the top event probability that involves the event, always in [0, 1].
- Risk achievement worth: RAW_e = Q(q_e = 1) / Q, the factor by which
  the top probability grows when the event is forced true, always >= 1.
- Risk reduction worth: RRW_e = Q / Q(q_e = 0), the factor by which the
  top probability shrinks when the event is forced false, always >= 1;
  unbounded (infinity) when forcing the event false removes every
  failure path.
- Closed-form identities of the re-evaluation method: FV_e = 1 -
  1/RRW_e and RAW_e = B_e / Q + 1 / RRW_e for every contributing event;
  Q(q = 1) >= Q >= Q(q = 0).
- ARP4761A frames the quantitative safety assessment context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Take the analysis inputs from fta-fmea: the minimal cut sets (list
   of event-name sets) and the basic-event probabilities (dict), and
   confirm every event in every cut set has a probability in (0, 1).
2. Compute the top event probability with top_event_probability and
   sanity-check it against the fta-fmea cut-set result before ranking.
3. Get the full per-event picture with importance_measures, which
   returns {event: {birnbaum, fussell_vesely, raw, rrw}} for every
   event that appears in the cut sets.
4. Rank the events with rank_events(cut_sets, probs, measure), one call
   per measure; the result is sorted descending with alphabetical
   tie-break. Default measure is fussell_vesely.
5. Flag the dominant contributors with dominant_contributors(cut_sets,
   probs, threshold = 0.1): events whose Fussell-Vesely measure strictly
   exceeds the threshold, sorted descending.
6. Read the rank lists together: Fussell-Vesely and RAW/RRW order
   risk-reduction effort, Birnbaum shows raw sensitivity of the top
   event to each event probability.
7. Confirm determinism and input rejection with the contract test:
   python3 scripts/test_fault_tree_importance_measures.py.

## Worked example

Anchor tree: cut_sets = [{"A", "B"}, {"C"}], probs = {"A": 0.01, "B":
0.02, "C": 0.03}.

- Q = 0.0002 + 0.03 - 0.000006 = 0.030194 (union of the cut sets AB and
  C by inclusion-exclusion).
- Event A: birnbaum 0.0194 (Q(q=1) = 0.0494 via B or C, Q(q=0) = 0.03),
  fussell_vesely 0.006425, raw 1.6361, rrw 1.00647.
- Event B: birnbaum 0.0097 (Q(q=1) = 0.0397 via A or C), fussell_vesely
  0.006425, raw 1.3148, rrw 1.00647.
- Event C: birnbaum 0.9998 (Q(q=1) = 1, Q(q=0) = 0.0002),
  fussell_vesely 0.9934, raw 33.1192, rrw 150.97.
- rank_events by fussell_vesely returns C first (0.9934), then A and B
  (tied at 0.006425, alphabetical order for determinism); rank by raw
  gives the same event order (C, A, B).
- dominant_contributors at the default threshold 0.1 returns ["C"]:
  event C dominates the top event probability, and fixing it gives the
  largest risk reduction (rrw 150.97).

## Verification

- Confirm top_event_probability([{"A", "B"}, {"C"}], {"A": 0.01, "B":
  0.02, "C": 0.03}) returns 0.030194 and that a single cut set {"A"}
  returns the event probability itself.
- Confirm the anchor measures: C birnbaum 0.9998, A 0.0194, B 0.0097;
  C fussell_vesely 0.9934, A and B 0.006425; raw 33.1192 / 1.6361 /
  1.3148; rrw 150.97 / 1.00647.
- Confirm the closed-form identities FV = 1 - 1/RRW and RAW = B/Q +
  1/RRW hold on the anchor tree, and that Q(q=1) >= Q >= Q(q=0) for
  every event.
- Confirm a lone single-event cut set {"A"} with p = 0.5 gives birnbaum
  1.0, fussell_vesely 1.0, raw 2.0 = 1/Q, and rrw infinity (the risk
  reduction is unbounded because forcing the event false eliminates the
  only failure path).
- Confirm ValueError rejection of non-physical inputs: empty cut_sets,
  an empty cut set entry, an unknown event name, a probability outside
  (0, 1), an event that appears in no cut set, and an unknown measure
  name.
- Run the contract test offline: python3
  scripts/test_fault_tree_importance_measures.py (35 tests,
  deterministic, exit 0).

## Related leaves

- systems-engineering-safety/arp4761a/fta-fmea: produces the minimal
  cut sets and the event probabilities that feed this leaf, with
  cut-set probability sanity and FMEA severity mapping on the same
  analysis set.
- systems-engineering-safety/arp4761a/markov-analysis: state-probability
  dynamics for the failure conditions this leaf ranks at the fault-tree
  level.
- systems-engineering-safety/arp4761a/reliability-block-diagram:
  series/parallel network reliability as the alternative top-event
  model.
- systems-engineering-safety/arp4761a/failure-rate-estimation: derives
  the basic-event probabilities from demonstration data before the
  importance ranking.

## Pitfalls

- Ranking on Birnbaum alone: event A has the higher Birnbaum measure
  (0.0194 vs B 0.0097) but the same Fussell-Vesely value as B
  (0.006425); Birnbaum is a raw sensitivity, not a fractional
  contribution, so risk-reduction prioritization should use FV, RAW or
  RRW as the primary order.
- Treating an unbounded RRW as an error or capping it: when the event
  sits in the only single-event cut set, Q(q=0) = 0 and the risk
  reduction worth is mathematically unbounded; the module reports
  positive infinity and the report should say so rather than inventing
  a finite value.
- Threshold semantics: dominance is strict, FV > threshold; an event
  whose Fussell-Vesely value equals the threshold is not flagged (use
  threshold 0.99 with FV 1.0 and the list comes back empty).
- Feeding redundant or non-minimal cut sets: duplicated or
  superset cut sets distort the per-event measures and inflate the
  inclusion-exclusion term count (2^n - 1 subsets), so take the minimal
  cut sets from fta-fmea and keep n small in quick studies.
- Reading significance into tie order: equal measure values are ordered
  alphabetically for determinism only, A before B in the example, so a
  tie is not a ranking statement.
- Passing degenerate event probabilities as nominal inputs: probs must
  lie strictly inside (0, 1) and cover every event in every cut set;
  forced true and forced false are internal re-evaluations, not inputs.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fault_tree_importance_measures.py

The test covers the anchor tree (Q = 0.030194, each measure inside the
spec magnitude bounds), single and four cut-set union probabilities
against closed forms, Birnbaum truth values (C 0.9998, p = 0.5 lone
event 1.0), Fussell-Vesely <= 1, RAW and RRW >= 1, rank ordering with
alphabetical tie-break, strict dominance at the threshold, closed-form
identities linking all four measures, Q(q=1) >= Q >= Q(q=0), the
unbounded RRW lone-cause case, determinism, exact dict keys, and
ValueError rejection of empty cut_sets, empty cut set entries, unknown
events, events in no cut set, probabilities outside (0, 1) and unknown
measure names. All 35 tests pass offline in under 20 seconds.

## Compliance

- Standards referenced, not reproduced: ARP4761A is proprietary (SAE,
  circa USD 180), name + paraphrase only; the importance-measure
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false. Inputs (cut sets,
  probabilities) come from the sibling fta-fmea leaf; this leaf adds
  the ranking layer only.
