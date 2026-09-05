# Wave-38 leaf spec: fault-tree-importance-measures (systems-engineering-safety, arp4761a pack)

- Path: skills/systems-engineering-safety/arp4761a/fault-tree-importance-measures/
- Pack: arp4761a. Closest siblings: fta-fmea (computes minimal cut sets,
  cut-set probability and the analysis set; its logic module exports
  analysis_set_for_level, minimal_cut_sets, cut_set_probability,
  cut_set_sanity and FMEA severity mapping - NO ranking function), markov-
  analysis (state-probability dynamics), reliability-block-diagram (RBD
  series/parallel), failure-rate-estimation (chi-square demonstration).
  Whole-tree grep: "birnbaum", "fussell", "importance measure", "risk
  achievement worth", "risk reduction worth", "RAW", "RRW" = ZERO owning
  hits in any leaf or family router. fta-fmea_logic.py verified: zero
  importance-measure functions. ZERO owners. GENUINE SES gap (fresh probe).
- Standards id: arp4761a (reference-only; the family spine - importance
  measures rank basic-event contribution to the top event, ARP4761A
  quantitative context). Ledger Standard: arp4761a.
- Family: systems-engineering-safety

## Claim

Rank the basic events of a fault tree by their contribution to the top
event probability: compute the Birnbaum measure (partial derivative of the
top event probability with respect to the event probability), the
Fussell-Vesely measure (fraction of top event probability that involves the
event), the risk achievement worth (top probability when the event is
forced true divided by the nominal top probability) and the risk reduction
worth (nominal top probability divided by the top probability when the
event is forced false), each from the minimal cut sets and the basic-event
probabilities, then sort the events by each measure and flag the dominant
contributors. Produces the per-event measure dict, the sorted rank list and
the dominance flag that gate risk-reduction prioritization. Does NOT do:
minimal cut-set generation, cut-set probability sanity or FMEA severity
mapping (fta-fmea); state-probability dynamics (markov-analysis);
reliability network math (reliability-block-diagram).

## Model (implement exactly)

Conventions: cut_sets is a list of sets of basic-event names (the minimal
cut sets, one set per cut set); probs is a dict mapping each basic-event
name to its probability in (0, 1). The top event probability Q is the
probability of the union of the cut sets computed by exact inclusion-
exclusion over the cut sets (events are independent). With three or fewer
cut sets this is a handful of product terms; implement the general mask
loop over 2**n - 1 subsets (n = number of cut sets; keep n <= 6 in tests).

Functions (pure stdlib):
- top_event_probability(cut_sets, probs) -> float: inclusion-exclusion
  union probability; ValueError on empty cut_sets or unknown event names.
- birnbaum_measure(cut_sets, probs, event) -> float: Q(q_event=1) -
  Q(q_event=0) computed by re-evaluating the union probability with the
  event probability replaced by 1.0 then 0.0.
- fussell_vesely_measure(cut_sets, probs, event) -> float:
  (Q - Q(q_event=0)) / Q.
- risk_achievement_worth(cut_sets, probs, event) -> float:
  Q(q_event=1) / Q.
- risk_reduction_worth(cut_sets, probs, event) -> float:
  Q / Q(q_event=0).
- importance_measures(cut_sets, probs) -> dict: per-event dict with keys
  birnbaum, fussell_vesely, raw, rrw.
- rank_events(cut_sets, probs, measure="fussell_vesely") -> [(event,
  value)] sorted descending by the named measure; ValueError for an
  unknown measure name.
- dominant_contributors(cut_sets, probs, threshold=0.1) -> [str]: events
  whose Fussell-Vesely measure exceeds the threshold, sorted descending.
  ValueError: probability outside (0, 1), event not in any cut set, empty
  cut_sets.

Identity to test: for an event in a single-event cut set that is the only
cut set, raw == 1/Q and rrw == 1.0; Fussell-Vesely <= 1 always;
Birnbaum of an event with probability 0.5 in the only single-event cut set
is 1.0; rank order by fussell_vesely equals rank by raw for positive
probabilities (monotone). All measures non-negative; Q(q=1) >= Q >=
Q(q=0).

## Worked example

Anchor tree: cut_sets = [{"A", "B"}, {"C"}], probs = {"A": 0.01, "B":
0.02, "C": 0.03}. Verified at prep:
- Q = 0.030194 (union of AB and C with independence: 0.0002 + 0.03 -
  0.000006).
- A: birnbaum 0.0194, fussell_vesely 0.006425, raw 1.6361, rrw 1.00647.
- B: birnbaum 0.0097, fussell_vesely 0.006425, raw 1.3148, rrw 1.00647.
- C: birnbaum 0.9998, fussell_vesely 0.9934, raw 33.1192, rrw 150.97.
- rank_events by fussell_vesely: C first (0.9934), then A and B (tied
  0.006425, order by event name for determinism).
- dominant_contributors at threshold 0.1: ["C"].
Run your module and take the real outputs as assert targets; these anchor
values are the prep-verified bounds (union math and each measure formula
independently checked).

## Validation list (contract test must include)

- Union probability on a two-cut-set tree (0.030194) and on a single cut
  set {A} (equals p_A).
- Birnbaum truth: event C in the anchor = 0.9998; event with p=0.5 in the
  only cut set gives 1.0.
- Fussell-Vesely <= 1; raw >= 1; rrw >= 1 for any event that appears.
- Rank function ordering; tie-break determinism (alphabetical by event
  name).
- Dominance threshold behavior at exactly the threshold (strict >).
- ValueErrors: empty cut_sets, probability 0 or 1, unknown event,
  unknown measure name.
- Identity: re-evaluation method reproduces closed forms (FV = 1 -
  Q0/Q; RAW = Q1/Q; RRW = Q/Q0).
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave38-fault-tree-importance-measures.yaml)

Query 1 (copy verbatim):
  "rank the basic events of the fault tree by birnbaum-importance and fussell-vesely-importance from the minimal-cut-set probabilities"
  intent: "systems-engineering-safety; basic event importance ranking from cut sets"
  expected_skill: "systems-engineering-safety/arp4761a/fault-tree-importance-measures"
Query 2 (copy verbatim):
  "compute the risk-achievement-worth and risk-reduction-worth of each basic event to prioritize the safety-relevant components"
  intent: "systems-engineering-safety; RAW and RRW importance measures"
  expected_skill: "systems-engineering-safety/arp4761a/fault-tree-importance-measures"
Task ids: w38-fault-tree-importance-measures-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must rank basic events of a fault tree
by importance:" and include the outputs in the Claim. First tag:
fault-tree-importance-measures. Additional tags ONLY:
birnbaum-importance, fussell-vesely-importance, risk-achievement-worth,
risk-reduction-worth, basic-event-ranking, top-event-sensitivity. NEVER
single generic words (importance, measure, ranking, risk, event,
probability). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): minimal cut set generation, cut
set probability sanity, analysis set, FMEA severity (fta-fmea); state
probability, transition rate, availability (markov-analysis); series
parallel reliability, k-out-of-n (reliability-block-diagram); failure
rate demonstration, chi-square bound (failure-rate-estimation).
