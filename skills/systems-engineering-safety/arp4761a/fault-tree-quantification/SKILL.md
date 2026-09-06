---
name: fault-tree-quantification
description: "Use when you must quantify a fault-tree top event from its minimal cut sets and basic-event probabilities: compute the rare-event approximation (sum of cut-set probabilities), the Esary-Proschan min-cut upper bound, and the exact inclusion-exclusion top probability when 2^n stays tractable; truncate the cut sets below an analyst probability threshold and keep the retained probability share; rank the cut sets by per-cut-set probability share to flag dominant failure combinations. Produces the quantified top-event probability, its bound chain, and the truncated cut-set mass picture, the predicted-probability input the SSA closure comparison consumes. Trigger: fault-tree quantification, rare-event approximation, min-cut upper bound, cut-set truncation, cut-set probability share, top-event probability."
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
  tags: [fault-tree-quantification, rare-event-approximation, min-cut-upper-bound, cut-set-truncation, cut-set-probability-share, top-event-probability]
  version: 0.1.0
  author: AeroSkills
---

# Fault Tree Quantification (systems-engineering-safety/arp4761a/fault-tree-quantification)

Use when you must quantify the top-event probability of a fault tree
from its minimal cut sets and basic-event probabilities. This leaf
computes the rare-event approximation, the Esary-Proschan min-cut upper
bound, the exact inclusion-exclusion top probability when the cut-set
count keeps 2^n tractable, the probability-threshold truncation of the
cut sets with the retained probability share, and the per-cut-set
probability-share ranking that flags the dominant failure combinations.
It is the missing producer in the FTA-to-SSA chain: it pairs with
systems-engineering-safety/arp4761a/fta-fmea, which derives the minimal
cut sets and checks their sanity against a supplied top probability, and
with systems-engineering-safety/arp4761a/ssa-closure, which consumes the
quantified top number as the predicted probability per flight hour. All
logic is deterministic, offline, pure stdlib.

## Domain quick reference

- Inputs: cut_sets, a list of sets of basic-event names (one set per
  minimal cut set), and probs, a dict mapping every basic-event name to a
  probability strictly inside (0, 1). Basic events are independent; a cut
  set occurs when every basic event in it fails, at probability equal to
  the product of its member probabilities.
- Rare-event approximation: Q_re = sum of the cut-set probabilities, the
  first-order union approximation, exact only for one cut set and always
  at or above the true union probability.
- Esary-Proschan min-cut upper bound: Q_ep = 1 - product over the cut
  sets of (1 - cut-set probability), an upper bound on the exact top
  probability of a coherent tree with independent basic events. In real
  arithmetic Q_ep <= Q_re always; the float survival product near 1.0 has
  an absolute rounding floor around 1e-16, so compare with Q_ep <= Q_re
  + 1e-15.
- Exact inclusion-exclusion: Q_ie = sum over the non-empty subsets of the
  cut sets of (-1)^(k+1) times the product of the basic-event
  probabilities over the union of the k selected cuts (independent events
  make the intersection product exactly that union product). The 2^n - 1
  term count is capped at EXACT_IE_MAX_CUT_SETS = 12 (4095 terms).
- Bound chain on a tree with shared events: Q_ie < Q_ep <= Q_re, because
  the inclusion-exclusion pair terms subtract the overlap mass the
  rare-event sum counts twice.
- Truncation: retained_probability_share = sum of the retained cut-set
  probabilities divided by the sum of all cut-set probabilities; drop is
  strict below the analyst threshold (probability equal to the threshold
  is kept), threshold in (0, 1].
- Ranking: per-cut-set probability share = cut-set probability divided by
  the sum of all cut-set probabilities, sorted descending with a stable
  input-order tie-break; shares sum to 1.0.
- ARP4761A frames the quantitative safety assessment context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Gather the analysis inputs from the fta-fmea leaf: the minimal cut
   sets (list of event-name sets) and the basic-event probabilities per
   flight hour (dict), and confirm every event in every cut set has a
   probability strictly inside (0, 1); an empty list, an empty cut-set
   entry, a missing or out-of-range probability is rejected with
   ValueError before any pass runs.
2. Run the rare-event approximation pass with rare_event_probability:
   Q_re is the sum of the cut-set probabilities, the first-order
   top-event estimate.
3. Run the Esary-Proschan min-cut upper bound pass with
   min_cut_upper_bound: Q_ep = 1 - product(1 - q_i) brackets the exact
   top probability from above.
4. Run the exact inclusion-exclusion pass with exact_top_probability when
   the cut-set count is at most EXACT_IE_MAX_CUT_SETS = 12; at 13 or more
   cut sets the guard raises ValueError and the step 2 and step 3
   approximations bracket the top number instead.
5. Truncate the cut-set list with truncate_cut_sets at the analyst
   probability threshold, drop strictly below the threshold, and record
   the retained_probability_share of the rare-event mass kept.
6. Rank the cut sets with rank_cut_sets by per-cut-set probability share,
   descending with input-order tie-break, and flag the dominant failure
   combinations where risk reduction must go first.
7. Assemble the SSA predicted-probability input: the quantified top-event
   probability, the bound chain Q_ie < Q_ep <= Q_re that brackets it, and
   the truncated cut-set mass picture, for the ssa-closure condition
   comparison.
8. Confirm determinism and input rejection with the contract test:
   python3 scripts/test_fault_tree_quantification.py.

## Worked example

Elevator actuation supply loss, dual channel: two hydraulic pumps, a
shared reservoir, two servo-valve channels and two flight-control
computers feed one actuation function. The fta-fmea leaf derived five
minimal cut sets of the top event; several cuts share events (P-A in
cuts 1 and 2, P-B in cuts 1 and 3), so the overlap correction is
non-trivial and exact IE is tractable at n = 5. Basic-event probabilities
per flight hour: C-A 1.0e-05, C-B 1.0e-05, P-A 1.0e-04, P-B 1.0e-04,
RSV 2.0e-05, V-A 5.0e-05, V-B 5.0e-05 (C = flight control computer,
P = pump, RSV = shared reservoir, V = servo valve).

- Cut sets in input order: {P-A, P-B} both pumps lost (q_cut 1.0e-08),
  {P-A, RSV} pump A and reservoir lost (2.0e-09), {P-B, RSV} pump B and
  reservoir lost (2.0e-09), {V-A, V-B} both valve channels jammed
  (2.5e-09), {C-A, C-B} both computers lost (1.0e-10).
- Q_re (rare-event approximation) = 1.66e-08.
- Q_ep (Esary-Proschan min-cut upper bound) = 1.660000015224483e-08.
- Q_ie (exact inclusion-exclusion) = 1.6599599963351046e-08.
- Bound chain: Q_ie < Q_ep <= Q_re with Q_ep - Q_ie = 4.001889e-13 and
  Q_re - Q_ie = 4.000366e-13, the overlap mass the pair terms subtract;
  the rare-event approximation overestimates the exact top probability
  on this overlapping-cut tree. The quantified top number 1.66e-08 per
  flight hour is the predicted probability the SSA closure condition
  comparison consumes.
- Cut-set truncation at threshold 1e-9 keeps the 4 cuts above 1e-10
  ({C-A, C-B} drops) with retained_probability_share 0.9939759036144578;
  at threshold 6e-9 only the dominant {P-A, P-B} cut at 1e-8 stays, share
  0.6024096385542169: the both-pumps cut alone carries 60.24 percent of
  the failure mass.
- Per-cut-set probability-share ranking (descending, input-order
  tie-break): #1 {P-A, P-B} share 0.6024096385542169, #2 {V-A, V-B}
  0.15060240963855423, #3 {P-A, RSV} 0.12048192771084339, #4 {P-B, RSV}
  0.12048192771084339 (tied pair keeps input order), #5 {C-A, C-B}
  0.00602409638554217; shares sum to 1.0. Pump independence or a second
  independent supply is the highest-leverage fix, ahead of computer
  redundancy, which holds only 0.6 percent of the mass.
- Exact-pass guard: at 13 cut sets, above EXACT_IE_MAX_CUT_SETS = 12,
  exact_top_probability raises ValueError; at the acceptance boundary, 12
  single-event disjoint cuts at 1e-6 give Q_ie = 1.1999934000219944e-05
  against the closed form 1 - (1 - 1e-6)^12 = 1.1999934000583856e-05, a
  relative gap of 3.03e-11 from alternating-sum rounding at 4095 terms.

## Verification

- Confirm rare_event_probability on the worked tree returns 1.66e-08
  within 1e-20, min_cut_upper_bound returns 1.660000015224483e-08 within
  1e-20, and exact_top_probability returns 1.6599599963351046e-08 within
  1e-20.
- Confirm the bound chain: Q_ep - Q_ie = 4.001889e-13 within 1e-18, Q_ep
  <= Q_re + 1e-15, Q_re - Q_ie = 4.000366e-13 within 1e-18.
- Confirm a single cut set {P-A} at 2.0e-4 returns 2.0e-4 from all three
  top formulas within 1e-12 relative, and disjoint single-event cuts
  {P-A} at 2e-4, {P-B} at 3e-4 give Q_re = 5.0e-4 with Q_ep = Q_ie = the
  exact union a + b - a*b = 4.9994e-4.
- Confirm truncation at 1e-9 keeps the 4 cuts above 1e-10 in input order
  with share 0.9939759036144578, at 6e-9 keeps only {P-A, P-B} with share
  0.6024096385542169, a threshold equal to a cut probability (2e-9) keeps
  that cut, threshold 1.0 drops everything (share 0.0), and threshold
  1e-12 drops nothing (share 1.0).
- Confirm the ranking order and shares match the tabulated worked example
  and the shares sum to 1.0 within 1e-12.
- Confirm exact_top_probability raises ValueError at 13 cut sets with a
  message containing "max 12" and matches 1 - (1 - 1e-6)^12 within 1e-9
  relative at 12 single-event cuts.
- Confirm ValueError rejection of non-physical inputs: empty cut_sets, an
  empty cut-set entry, an event with no probability entry, a probability
  of 1.5 and of 0.0, and a threshold of 1.5 and of 0.0.
- Run the contract test offline: python3
  scripts/test_fault_tree_quantification.py (33 tests, deterministic,
  exit 0).

## Related leaves

- systems-engineering-safety/arp4761a/fta-fmea: derives the minimal cut
  sets from AND/OR gate structures and sanity-checks cut-set
  probabilities; the producer of this leaf's two inputs.
- systems-engineering-safety/arp4761a/fault-tree-importance-measures:
  per-event Birnbaum, Fussell-Vesely, RAW and RRW ranking on top of the
  quantified tree, where exact inclusion-exclusion is the small-n
  re-evaluation engine behind each measure.
- systems-engineering-safety/arp4761a/fault-tree-uncertainty-analysis:
  lognormal band around the quantified top probability this leaf
  produces.
- systems-engineering-safety/arp4761a/ssa-closure: consumes the
  quantified top-event probability as the predicted probability per
  flight hour in the condition comparison.
- systems-engineering-safety/arp4761a/event-tree-analysis: the forward
  dual that enumerates branch paths from an initiating event frequency
  instead of unioning cut events into a top number.
- systems-engineering-safety/arp4761a/failure-rate-estimation: derives
  the basic-event probabilities from demonstration data before this leaf
  quantifies the tree.

## Pitfalls

- Attempting exact inclusion-exclusion past the guard: the 2^n - 1 term
  count doubles with every cut set, so above EXACT_IE_MAX_CUT_SETS = 12
  the module raises ValueError; the report should fall back to the
  rare-event approximation and the min-cut upper bound as the bracket.
- Reading the rare-event approximation as exact: on trees with shared
  events across cuts Q_re overestimates the true top probability (Q_ie <
  Q_re by 4.000366e-13 on the worked tree), so the bound chain, not the
  bare sum, is the honest top-number statement.
- Treating Q_ep <= Q_re as a float-guaranteed comparison: the
  Esary-Proschan bound evaluates a survival product near 1.0 whose
  absolute rounding floor is around 1e-16, so the contract asserts the
  ordering with a 1e-15 tolerance.
- Misreading the truncation boundary: drop is strict below the analyst
  threshold, so a cut set whose probability equals the threshold is kept,
  and the threshold itself must lie in (0, 1].
- Re-deriving cut sets or ranking events here: gate traversal and
  minimal-cut-set derivation stay in the fta-fmea leaf and per-event
  importance ranking in fault-tree-importance-measures; this leaf only
  unions the cut events it is given into a top number.
- Quoting per-cut-set shares without their sum check: the ranking shares
  must sum to 1.0, and the tied cuts keep input order, so a tie in the
  ranking is not a dominance statement.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fault_tree_quantification.py

The test covers the worked tree anchors (Q_re 1.66e-08, Q_ep
1.660000015224483e-08, Q_ie 1.6599599963351046e-08, each within the spec
magnitude bounds), the bound chain with its two overlap gaps, the single
cut set and disjoint-pair union identities, probability-threshold
truncation with the retained share, per-cut-set probability-share ranking
with input-order tie-break, the 12-cut-set exact inclusion-exclusion
guard and its closed-form boundary, determinism, exact dict keys, and
ValueError rejection of empty cut sets, empty cut-set entries, missing
event probabilities, out-of-range probabilities and out-of-range
thresholds. All 33 tests pass offline in under 20 seconds.

## Compliance

- Standards referenced, not reproduced: ARP4761A is proprietary (SAE);
  name + paraphrase only, summary-only per standards-map.yaml. The
  rare-event, Esary-Proschan and inclusion-exclusion relations are
  standard engineering methodology.
- compliance: STANDARDS-REF, gated: false. Inputs (minimal cut sets,
  basic-event probabilities) come from the sibling fta-fmea leaf; this
  leaf adds the top-number production only.
