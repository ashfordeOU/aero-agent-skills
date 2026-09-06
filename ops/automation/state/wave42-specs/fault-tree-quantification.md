# Wave-42 leaf spec: fault-tree-quantification (systems-engineering-safety, arp4761a pack)

- Path: skills/systems-engineering-safety/arp4761a/fault-tree-quantification/
- Pack: arp4761a (verified present at write time under
  skills/systems-engineering-safety/arp4761a/ with beta-factor-analysis,
  common-cause-analysis, event-tree-analysis, failure-mode-criticality,
  failure-rate-estimation, fault-tree-importance-measures,
  fault-tree-uncertainty-analysis, fmes-coverage-analysis, fta-fmea,
  functional-hazard-assessment, maintainability-prediction, markov-analysis,
  operating-support-hazard-analysis, particular-risk-analysis,
  preliminary-system-safety-assessment, reliability-block-diagram,
  reliability-growth-analysis, safety-assessment, ssa-closure,
  zonal-safety-analysis; leaf fault-tree-quantification absent at write
  time). GENUINE missing-producer gap in the FTA-to-SSA chain (fresh probe):
  fta_fmea_logic.py read in full (109 lines) implements minimal_cut_sets,
  cut_set_probability and cut_set_sanity(cut_sets, probs, top_prob), where
  top_prob is an INPUT; nothing in the module quantifies the tree. Whole-tree
  grep "rare[- ]event|min[- ]cut upper|cut[- ]set truncation|truncat.*cut|
  dominant cut" across all skills/**/SKILL.md = 3 hits, all unrelated
  (poisson-confidence-interval, load-spectrum-counting, particle-filter).
  fault-tree-uncertainty-analysis states it consumes "the quantified top
  probability from systems-engineering-safety/arp4761a/fta-fmea", a producer
  that module does not actually implement; ssa-closure consumes predicted
  probabilities "from updated fault tree runs" that no leaf produces. This
  leaf is that missing producer.
  Fences within the pack (quoted from the leaves at write time, read in full):
  - fta-fmea (structure + cut-set derivation + sanity): its description
    claims "compute minimal cut sets from AND/OR gate structures, check
    cut-set probability sanity against the top event probability, select the
    analysis set for an assurance level (FTA/FMEA always, CCA at levels A and
    B)"; its body states "FTA models a top event as a tree of AND/OR gates
    over basic events; a minimal cut set is a smallest set of basic events
    whose joint occurrence forces the top event"; its logic module signature
    is cut_set_sanity(cut_sets, probs, top_prob) with docstring "Flag
    (cut_set, prob) pairs whose probability exceeds the top event probability
    -- a modeling or probability error." Gate traversal and cut-set
    derivation, and sanity against a supplied top probability, stay there.
  - fault-tree-importance-measures (per-event ranking): "Use when you must
    rank basic events of a fault tree by importance: compute the Birnbaum
    measure, the Fussell-Vesely measure, the risk achievement worth (RAW) and
    the risk reduction worth (RRW) of each basic event from the minimal cut
    sets and the basic-event probabilities"; its top-event engine is "exact
    inclusion-exclusion over 2^n - 1 subsets, n = number of cut sets" and its
    pitfall is to "keep n small in quick studies". Exact IE there is the
    re-evaluation engine behind per-event measures (small-n regime only), not
    a top-number production service.
  - fault-tree-uncertainty-analysis (band around a given number): "It
    consumes the quantified top probability from systems-engineering-safety/
    arp4761a/fta-fmea and the Fussell-Vesely fractions from systems-
    engineering-safety/arp4761a/fault-tree-importance-measures; it never
    derives either input itself." A lognormal band around a top probability
    that arrives as an input; the upstream producer this leaf supplies.
  - ssa-closure (closure consumer): "the analyst-supplied predicted
    probabilities per flight hour (for example from updated fault tree runs
    on the implemented system) are compared against the quantitative
    probability target of each condition's severity class"; and "Only
    post-implementation predicted probabilities are consumed here". Margin
    and closure-gate arithmetic over the predicted number stays there; this
    leaf produces the predicted number.
  - event-tree-analysis (forward dual): enumerates binary branch paths from
    an initiating event through mitigating functions and rolls up end-state
    frequencies; no cut sets, no backward-tree union.
  - markov-analysis, reliability-block-diagram, particular-risk-analysis,
    failure-rate-estimation: time-domain state probabilities from transition
    rates, series/parallel network evaluation, single-event exposure times
    conditional probabilities, and demonstration statistics for event
    probabilities; none unions a tree of cut events into a top number.
- Standards id: arp4761a (verified present at write time in repo-root
  standards-map.yaml, SAE guidance, proprietary-sold, reference-only per
  standards-map.yaml). Ledger Standard: arp4761a.
- Family: systems-engineering-safety

## Claim

Quantify the top-event probability of a fault tree from its minimal cut sets
and basic-event probabilities when the exact union cannot always be
enumerated: compute the rare-event approximation Q = sum of the cut-set
probabilities, compute the Esary-Proschan min-cut upper bound Q = 1 - product
over the cut sets of (1 - cut-set probability), compute the exact top
probability by inclusion-exclusion over the union of the cut events when the
cut-set count keeps 2^n tractable, truncate the cut sets below an analyst
probability threshold and report the retained probability share, and rank the
cut sets by per-cut-set probability share to flag the dominant failure
combinations. Produces the quantified top-event probability, the bound chain
that brackets it, and the truncated cut-set mass picture, which together form
the predicted-probability input the SSA closure comparison consumes. Does NOT
do: AND/OR gate structure traversal, minimal-cut-set derivation from gate
structures, or cut-set probability sanity against a supplied top probability
(fta-fmea); per-event importance measures, Birnbaum, Fussell-Vesely, RAW or
RRW, or per-event ranking (fault-tree-importance-measures); lognormal error
factors, confidence bands, exceedance probabilities or variance shares around
a top number (fault-tree-uncertainty-analysis); severity-class target lookup,
per-condition margin or closure-gate verdicts (ssa-closure); forward
event-tree branch enumeration from an initiator frequency
(event-tree-analysis). Deterministic closed-form products and sums only: no
Monte Carlo, no RNG, no solver; exact inclusion-exclusion carries a
cut-set-count guard and the caller falls back to the approximations above it.

## Model (implement exactly)

Functions (pure stdlib, deterministic, no RNG). All consume cut_sets, a list
of sets (or frozensets) of basic-event names as produced by the fta-fmea
leaf's minimal_cut_sets, and probs, a dict mapping every basic-event name to
a probability strictly inside (0, 1). Basic events are independent; a cut set
occurs when every basic event in it fails, at probability equal to the
product of its member probabilities. The cut-set probability product and the
union arithmetic are shared internally; no cut set is ever derived from gate
structure here.
- rare_event_probability(cut_sets, probs) -> float, the rare-event
  approximation Q_re = sum over the cut sets of the cut-set probability
  (first-order union approximation, exact only for one cut set).
- min_cut_upper_bound(cut_sets, probs) -> float, the Esary-Proschan min-cut
  upper bound Q_ep = 1 - product over the cut sets of (1 - cut-set
  probability). Upper bound on the exact top probability of a coherent tree
  with independent basic events. In real arithmetic Q_ep <= Q_re always (the
  survival product 1 - product(1 - q_i) >= 1 - sum(q_i) = 1 - Q_re); the
  float implementation evaluates the survival product near 1.0, so its
  absolute rounding floor is about 1e-16 and the contract compares Q_ep <=
  Q_re + 1e-15.
- exact_top_probability(cut_sets, probs) -> float, the exact union
  probability by inclusion-exclusion over the cut events: iterate the
  non-empty subsets of the cut sets (mask 1 to 2^n - 1) and add (-1)^(k+1)
  times the product of the basic-event probabilities over the union of the
  k selected cuts (independent basic events make the intersection product
  exactly that union product). ValueErrors: empty cut_sets, empty cut-set
  entry, event without a probability, probability outside (0, 1), and more
  than EXACT_IE_MAX_CUT_SETS cut sets, where the error message is
  "exact inclusion-exclusion intractable at N cut sets (max 12): use
  rare_event_probability or min_cut_upper_bound".
- truncate_cut_sets(cut_sets, probs, threshold) -> dict with exactly the
  keys cut_sets (the retained cut sets in input order) and
  retained_probability_share (sum of retained cut-set probabilities divided
  by the sum of all cut-set probabilities, the share of the rare-event mass
  kept). A cut set whose probability equals the threshold is kept (drop is
  strict, probability < threshold); an all-dropped call returns an empty
  list and share 0.0; a threshold that drops nothing returns the full input
  and share 1.0. ValueError when threshold is outside (0, 1].
- rank_cut_sets(cut_sets, probs) -> list of dicts, each with exactly the
  keys cut_set, probability and share (share = cut-set probability divided
  by the sum of all cut-set probabilities), sorted descending by
  probability with input-order tie-break (stable), shares summing to 1.0.
Module constants: EXACT_IE_MAX_CUT_SETS = 12 (2**12 - 1 = 4095
inclusion-exclusion terms is the cap; 2**13 - 1 and above raise ValueError).
Common ValueErrors: empty cut_sets list, an empty cut-set entry, an event
name with no probability entry, a probability outside (0, 1) (0.0 and 1.0
both rejected), and for truncate_cut_sets a threshold outside (0, 1].

Identity to test: a single cut set returns its cut-set probability from all
three top formulas; two disjoint single-event cuts {A}, {B} give the
rare-event sum a + b above the exact union a + b - a*b, which the min-cut
upper bound and the inclusion-exclusion reproduce identically; Q_ep <= Q_re
holds for any probabilities; Q_ie <= Q_ep (Esary-Proschan) on the worked
tree; on trees with shared events across cuts the inclusion-exclusion pair
terms subtract overlap mass, so Q_ie < Q_re (the rare-event sum overestimates
the exact top probability); the retained probability share lies in [0, 1]
with full retention at 1.0; the ranking shares sum to 1.0.

## Worked example

Elevator actuation supply loss, dual-channel: two hydraulic pumps, a shared
reservoir, two servo-valve channels and two flight-control computers, all
feeding one actuation function. The fta-fmea leaf derived five minimal cut
sets of the top event from the OR-of-ANDs tree; several cuts share events, so
the overlap correction is non-trivial and exact IE is tractable at n = 5.
Basic-event probabilities per flight hour (all in [1e-4, 1e-6]):
C-A 1.000000e-05, C-B 1.000000e-05, P-A 1.000000e-04, P-B 1.000000e-04,
RSV 2.000000e-05, V-A 5.000000e-05, V-B 5.000000e-05 (C = flight control
computer, P = pump, RSV = shared reservoir, V = servo valve). Cut sets in
input order with their probabilities:
- {P-A, P-B} both pumps lost, q_cut 1.000000e-08
- {P-A, RSV} pump A and shared reservoir lost, q_cut 2.000000e-09
- {P-B, RSV} pump B and shared reservoir lost, q_cut 2.000000e-09
- {V-A, V-B} both servo-valve channels jammed, q_cut 2.500000e-09
- {C-A, C-B} both flight-control computers lost, q_cut 1.000000e-10

Real module outputs from the prep anchor run (/tmp/w42spec/
anchor_fault_tree_quantification.py, pure stdlib math, python3, macOS,
deterministic, exit 0, all assertions passed):

Q_re    (rare-event approximation)          = 1.66e-08
Q_ep    (Esary-Proschan min-cut upper bnd) = 1.660000015224483e-08
Q_ie    (exact inclusion-exclusion)        = 1.6599599963351046e-08

Bound chain observed at anchor precision: Q_ie < Q_ep <= Q_re. The
Esary-Proschan bound and the rare-event sum coincide at 8 significant figures
because the cut-pair corrections (sum over pairs of q_i x q_j, about 2e-16
here) sit at the float noise floor of the survival-product form 1 - product
(1 - q); the mathematically guaranteed ordering Q_ep <= Q_re is asserted with
a 1e-15 absolute tolerance. The observable exact-vs-bound gap is clean:
Q_ep - Q_ie = 4.001889e-13 and Q_re - Q_ie = 4.000366e-13, the overlap mass
the inclusion-exclusion pair terms subtract. The rare-event approximation
overestimates the exact top probability on this tree (Q_ie < Q_re), and both
upper bounds bracket the exact value from above.

Reading for the aircraft case: the quantified top-event probability of
1.66e-08 per flight hour for elevator actuation supply loss is the predicted
probability that the ssa-closure condition comparison consumes; the
per-cut-set ranking below shows where risk reduction must go first.

Cut-set truncation (real anchor outputs):
- truncate_cut_sets at threshold 1e-9 keeps 4 of 5 cuts (all except the
  {C-A, C-B} cut at 1e-10), retained_probability_share 0.9939759036144578.
- truncate_cut_sets at threshold 6e-9 keeps only the dominant {P-A, P-B}
  cut at 1e-8, retained_probability_share 0.6024096385542169: the dominant
  cut alone carries 60.24% of the failure mass.

Per-cut-set probability-share ranking (real anchor output, descending with
input-order tie-break):
#1 {P-A, P-B}  probability 1.000000e-08  share 0.6024096386
#2 {V-A, V-B}  probability 2.500000e-09  share 0.1506024096
#3 {P-A, RSV}  probability 2.000000e-09  share 0.1204819277
#4 {P-B, RSV}  probability 2.000000e-09  share 0.1204819277
#5 {C-A, C-B}  probability 1.000000e-10  share 0.0060240964
(shares sum to 1.0; the tied pair keeps input order). The both-pumps cut
dominates: pump independence or a second independent supply is the
highest-leverage fix, ahead of computer redundancy, which holds only 0.6% of
the mass.

exact_top_probability guard (real anchor output): at 13 cut sets, above
EXACT_IE_MAX_CUT_SETS = 12, it raises ValueError "exact inclusion-exclusion
intractable at 13 cut sets (max 12): use rare_event_probability or
min_cut_upper_bound"; the fallbacks return the approximations. At the
acceptance boundary, 12 single-event disjoint cuts at 1e-6 each give
Q_ie = 1.199993400022e-05 against the closed form 1 - (1 - 1e-6)^12 =
1.199993400058e-05, a relative gap of 3.03e-11 from alternating-sum rounding
at 4095 terms, so the contract tolerance there is 1e-9 relative.

Run your module and take the real outputs as assert targets; the anchors
above are prep-verified, computed by running /tmp/w42spec/
anchor_fault_tree_quantification.py (pure stdlib math, python3, macOS,
deterministic, exit 0).

## Validation list (contract test must include)

- rare_event_probability on the worked tree returns 1.66e-08 (the double
  nearest the sum of the five cut-set probabilities) within 1e-20;
  min_cut_upper_bound returns 1.660000015224483e-08 within 1e-20; and
  exact_top_probability returns 1.6599599963351046e-08 within 1e-20.
- Bound chain on the worked tree: Q_ie < Q_ep (gap 4.001889e-13 within
  1e-18); Q_ep <= Q_re + 1e-15; Q_ie < Q_re (gap 4.000366e-13 within
  1e-18), the rare-event overestimate on an overlapping-cut tree.
- Single cut set {P-A} at 2.0e-4: all three formulas return 2.0e-4 within
  1e-12 relative.
- Disjoint single-event cuts {P-A} at 2e-4 and {P-B} at 3e-4:
  rare_event_probability = 5.0e-4; min_cut_upper_bound and
  exact_top_probability both equal the exact union 4.9994e-4 within 1e-12
  relative; the union identity IE = EP = a + b - a*b holds.
- truncate_cut_sets on the worked tree: threshold 1e-9 returns the 4 cuts
  {P-A, P-B}, {P-A, RSV}, {P-B, RSV}, {V-A, V-B} in input order with
  retained_probability_share 0.9939759036144578 within 1e-15; threshold
  6e-9 returns only {P-A, P-B} with share 0.6024096385542169 within 1e-15;
  a threshold equal to a cut probability (2e-9) keeps that cut (>= keeps,
  strict drop); threshold 1.0 drops everything (empty list, share 0.0);
  threshold 1e-12 drops nothing (share 1.0); dict keys exactly cut_sets and
  retained_probability_share.
- rank_cut_sets on the worked tree: order and shares exactly as tabulated
  (#1 {P-A, P-B} 0.6024096386, #2 {V-A, V-B} 0.1506024096, #3 and #4 the
  tied 2e-9 cuts in input order at 0.1204819277 each, #5 {C-A, C-B}
  0.0060240964), shares summing to 1.0 within 1e-12, dict keys exactly
  cut_set, probability, share.
- exact_top_probability guard: 13 cut sets raises ValueError with a message
  containing "max 12"; 12 cut sets of single events at 1e-6 are accepted and
  match 1 - (1 - 1e-6)^12 within 1e-9 relative (alternating-sum rounding
  grows with the 4095-term count, anchored at 3.03e-11).
- ValueErrors: empty cut_sets; an empty cut-set entry; an event with no
  probability entry; a probability of 1.5 and of 0.0; a threshold of 1.5 and
  of 0.0. All seven raise ValueError (verified by the anchor rejection
  sweep).
- Determinism: two calls return equal structures; the ranking tie-break is
  input order, stable across calls.

## Corpus fragment (eval/hit1-wave42-fault-tree-quantification.yaml)

Query 1 (copy verbatim):
  "quantify the elevator actuation fault tree: given the minimal cut sets and the per-flight-hour basic-event probabilities, compute the rare-event approximation, the Esary-Proschan min-cut upper bound and the exact inclusion-exclusion probability of the top event"
  intent: "systems safety; fault-tree top-event probability quantification from minimal cut sets by rare-event, min-cut upper bound and exact inclusion-exclusion"
  expected_skill: "systems-engineering-safety/arp4761a/fault-tree-quantification"
Query 2 (copy verbatim):
  "truncate the quantified fault tree's cut sets below a probability threshold, report the retained probability share and rank the retained cut sets by probability share to find the dominant failure combinations feeding the SSA predicted probability"
  intent: "systems safety; cut-set truncation and per-cut-set probability-share ranking of a quantified fault tree"
  expected_skill: "systems-engineering-safety/arp4761a/fault-tree-quantification"
Task ids: w42-fault-tree-quantification-1 and -2. Whole-corpus grep at write
time: no existing task in eval/ contains "rare-event", "inclusion-exclusion",
"cut-set truncation", "min-cut upper" or "esary" (zero hits), so both queries
are collision-free against the existing arp4761a tasks (sa3, sa4, xp5 route
fta-fmea on fault-tree and minimal-cut-set derivation phrasing; markov and
reliability-block-diagram tasks route on transition rates and series/parallel
networks; the event-tree-analysis tasks route on branch paths and end-state
frequencies).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must quantify a fault-tree top event from
its minimal cut sets and basic-event probabilities:" and include the outputs
in the Claim (the quantified top-event probability, the rare-event
approximation, the min-cut upper bound, the exact inclusion-exclusion result
when tractable, the truncated cut-set list with its retained probability
share, and the per-cut-set probability-share ranking) plus the SSA
predicted-probability feed. First tag: fault-tree-quantification. Additional
tags ONLY: rare-event-approximation, min-cut-upper-bound, cut-set-truncation,
cut-set-probability-share, top-event-probability. NEVER single generic words
(fault, tree, cut, bound, probability, quantification, share, ranking,
event, risk, safety). 50-150 words, <=1000 chars, no em dash, no restricted
content-policy wording, action verb present.

FORBIDDEN TOKENS (belong to siblings): and-gate, or-gate, gate-structure,
gate-traversal, derive-the-cut-sets, minimal-cut-set-derivation,
cut-set-sanity, top-prob-input, fta, fmea, fmeca, failure-mode (fta-fmea);
birnbaum, fussell-vesely, risk-achievement-worth, risk-reduction-worth,
importance-measure, event-ranking, raw, rrw (fault-tree-importance-measures);
lognormal, error-factor, confidence-band, exceedance-probability,
variance-share, sigma (fault-tree-uncertainty-analysis); closure-gate,
condition-margin, meets-verdict, severity-target, requirement-closure-status
(ssa-closure); markov-chain, transition-rate, state-probability,
absorbing-state, availability (markov-analysis); branch-path, end-state-
frequency, initiator-frequency, mitigating-function (event-tree-analysis);
exposure-probability, containment, hazard-zone (particular-risk-analysis).
The leaf consumes minimal cut sets and basic-event probabilities as inputs
and never claims to derive either; the words "predicted probability" appear
only to name the ssa-closure consumption, never to run its margin or gate
arithmetic.
