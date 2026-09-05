# Wave-41 leaf spec: event-tree-analysis (systems-engineering-safety, arp4761a pack)

- Path: skills/systems-engineering-safety/arp4761a/event-tree-analysis/
- Pack: arp4761a (verified present at prep under
  skills/systems-engineering-safety/arp4761a/ with beta-factor-analysis,
  common-cause-analysis, failure-mode-criticality, failure-rate-estimation,
  fault-tree-importance-measures, fault-tree-uncertainty-analysis,
  fmes-coverage-analysis, fta-fmea, functional-hazard-assessment,
  markov-analysis, operating-support-hazard-analysis,
  particular-risk-analysis, preliminary-system-safety-assessment,
  reliability-block-diagram, safety-assessment, ssa-closure,
  zonal-safety-analysis; leaf event-tree-analysis absent at prep).
  GENUINE forward-dual gap (fresh probe): whole-tree grep
  "event tree|event-tree" = 0 hits in skills/ and 0 hits in eval/*.yaml.
  Fences within the pack (quoted from the leaves at prep, read in full):
  - fta-fmea (backward logic only): "FTA models a top event as a tree of
    AND/OR gates over basic events; a minimal cut set is a smallest set of
    basic events whose joint occurrence forces the top event"; its
    description claims "compute minimal cut sets from AND/OR gate
    structures, check cut-set probability sanity against the top event
    probability"; no forward branch or sequence enumeration exists in its
    functions or contract tests. Backward gates and cut sets stay there.
  - particular-risk-analysis (single-event, no branching): its body
    states "The analysis combines the event probability with the
    conditional probability that the hazard created by the event damages
    a system, producing the failure-condition probability contribution"
    and "PRA covers single-event risks that are not internal system
    failures: rotor burst, tire burst, bird strike, fire, and lightning";
    one event probability times one conditional probability plus
    containment verdicts, never a tree of successive mitigating-function
    branches from one initiator.
  - safety-assessment (process umbrella): "FTA (fault tree) and FMEA
    (failure modes and effects) are the standard techniques; CCA (common
    cause analysis) covers zonal, particular-risk, and common-mode risks
    (ZSA/PRA/CMA)"; it fixes the FHA-to-PSSA-to-SSA sequence and
    analysis-set scope, not any rollup arithmetic.
  - functional-hazard-assessment (severity owner): its description maps
    "severity into the categories catastrophic, hazardous, major, minor,
    and no safety effect" and maps "each severity to its quantitative
    probability target (extremely improbable below 1e-9/flight-hour,
    extremely remote below 1e-7, remote below 1e-5, probable below 1e-3)";
    rating an end-state consequence into a severity class is FHA work and
    this leaf consumes, never re-derives, the class.
  - ssa-closure (closure owner): "Quantitative probability targets per
    flight hour by severity class (severity_target): catastrophic 1e-9,
    hazardous 1e-7, major 1e-5, minor 1e-3"; closing the post-
    implementation SSA per assessed condition over predicted probabilities
    is its job, not the forward screening done here.
  - fault-tree-uncertainty-analysis (band owner): it "converts each
    basic-event lognormal error factor into a lognormal sigma" and
    "consumes the quantified top probability from
    systems-engineering-safety/arp4761a/fta-fmea"; epistemic bands around
    a backward-tree top number are out of scope here.
  - markov-analysis (time-domain neighbor): continuous-time Markov chain
    state probabilities from transition rates with time evolution and
    absorbing states; this leaf rolls up a static forward branch tree
    from one initiator and never integrates rates over time.
- Standards id: arp4761a (guidance, SAE, proprietary-sold, reference-only
  per standards-map.yaml). Ledger Standard: arp4761a.
- Family: systems-engineering-safety

## Claim

Quantify forward-branching sequences from an initiating event through
successive mitigating-function successes or failures to end states, the
forward dual of fault tree analysis: enumerate every binary branch path
over an ordered list of mitigating functions (each with its success
probability p and failure probability 1 - p), roll up each end-state
outcome frequency as initiator frequency times the product of the branch
probabilities along the path, rank the end-state paths by frequency, sum
the frequency over the paths that reach the failure end state (the
top-level safety function failing when no mitigating function succeeds),
and screen the ranked sequences against the ARP4761A-class per-flight-hour
severity targets (catastrophic 1e-9, hazardous 1e-7, major 1e-5, minor
1e-3, mirrored from the FHA probability-target mapping) to flag the
dominant sequences whose frequency exceeds the target of the FHA-rated
end-state severity class, using a strict comparison where equality is not
dominant. Produces the full path enumeration with per-path probabilities
and frequencies, the frequency-ranked end-state list, the failure-end-
state frequency sum and the dominant-sequence flags that gate whether the
mitigating chain meets the safety objective for the initiator. Does NOT
do: backward fault-tree gates, minimal cut sets or top-event probability
from basic events (fta-fmea); single-event particular-risk combination or
containment verdicts (particular-risk-analysis); the FHA-PSSA-SSA
sequence, severity classification of a failure condition or end state, or
analysis-set scoping (safety-assessment, functional-hazard-assessment);
per-condition SSA close-out margins and closure-gate verdicts
(ssa-closure); lognormal error factors, confidence bands or exceedance
bands around a tree probability (fault-tree-uncertainty-analysis);
time-dependent Markov state probabilities from transition rates
(markov-analysis). Deterministic binary enumeration only: no Monte Carlo,
no time integration, no analyst weighting inside the rollup.

## Model (implement exactly)

Functions (pure stdlib, deterministic, no RNG):
- build_paths(nodes) -> list of dicts {"sequence", "path",
  "probability"}, the full binary expansion of the ordered node list.
  nodes is a list of (name, p_success) tuples; path is a tuple of bools
  with True = the function succeeds and False = it fails; probability is
  the product of the branch probabilities along the path (p for a success
  branch, 1 - p for a failure branch); sequence is the readable string
  "name1:S name2:F ..." with S for success and F for failure in node
  order. Enumeration order is ascending binary mask with node i mapped to
  bit i, so the all-failure path (mask 0) comes first and the all-success
  path (mask 2**N - 1) comes last. ValueErrors: empty node list, more
  than BRANCH_NODES_MAX nodes, any branch probability outside [0, 1]
  (boundaries 0.0 and 1.0 are legal).
- outcome_frequencies(initiator_frequency, nodes) -> list of dicts
  {"sequence", "path", "probability", "frequency"} with frequency =
  initiator_frequency x probability for every end-state path, sorted
  descending by frequency with ties broken by enumeration order (stable).
  ValueErrors: negative initiator_frequency, empty node list, node count
  above BRANCH_NODES_MAX, branch probability outside [0, 1].
- is_failure_end_state(path) -> True exactly when every outcome on the
  path is False, the failure end state under the series-barriers reading
  where no mitigating function contained the initiator.
- top_function_failure_frequency(frequencies) -> dict {"sequences":
  list of sequence strings reaching the failure end state, "frequency":
  float sum of their frequencies}. Under the full 2**N expansion exactly
  one path (all failures) reaches the failure end state, so the sum
  equals that path's frequency; the implementation still sums over the
  flagged paths per the rollup definition.
- dominant_sequences(frequencies, severity_target) -> list of dicts
  {"sequence", "frequency", "ratio"} for the sequences whose frequency
  strictly exceeds severity_target (frequency > target; equality is NOT
  dominant, mirroring the strict target rule of the severity
  classification work), in the input frequency-descending order; ratio =
  frequency / severity_target. Empty list when nothing exceeds. ValueError
  if severity_target <= 0.
Module constants: BRANCH_NODES_MAX = 12 (2**13 = 8192 paths and above
raise ValueError; 2**12 = 4096 paths is the cap), CATASTROPHIC = 1e-9,
HAZARDOUS = 1e-7, MAJOR = 1e-5, MINOR = 1e-3 per flight hour, the
ARP4761A-class FHA severity targets paraphrased by magnitude only, the
same magnitudes the functional-hazard-assessment probability-target
mapping and the ssa-closure severity_target lookup carry. The class of
each end state is an analyst input from the FHA and is never derived
here: screen each end-state frequency against the target of its own
class by passing that target, not by inventing classes in the module.

Identity to test: the path probabilities sum to exactly 1.0 and the
outcome frequencies sum to exactly the initiator frequency (full
expansion partitions the initiator); the all-failure path probability
equals the product of the failure probabilities 1 - p over the nodes;
top_function_failure_frequency returns that path's frequency; a single
node with p = 0.5 splits the initiator evenly into two end states; an
end state sitting exactly on its target is not dominant; the all-success
path probability of a 12-node all-p = 0.5 tree is 2**-12.

## Worked example

Cargo-compartment fire. Initiating event: cargo fire ignition at
initiator_frequency q0 = 3e-5 per flight hour. Three mitigating functions
in series, branch nodes [("detect", 0.95), ("extinguish", 0.90),
("pilot", 0.80)]: fire detection, extinguisher discharge, pilot action.
Failure probabilities are 0.05, 0.10 and 0.20. Real module outputs from
the prep anchor run (/tmp/w41spec/anchor_event_tree.py, stdlib math,
verified at prep):

Path probabilities in enumeration order (sum exactly 1.0):
detect:F extinguish:F pilot:F 0.001, detect:S extinguish:F pilot:F 0.019,
detect:F extinguish:S pilot:F 0.009, detect:S extinguish:S pilot:F 0.171,
detect:F extinguish:F pilot:S 0.004, detect:S extinguish:F pilot:S 0.076,
detect:F extinguish:S pilot:S 0.036, detect:S extinguish:S pilot:S 0.684
(all within 1e-15 of the products of the decimal inputs).

outcome_frequencies(3e-5, nodes) ranked descending (frequencies sum
exactly to 3e-05 = the initiator):
- detect:S extinguish:S pilot:S probability 0.684, frequency 2.052e-5
- detect:S extinguish:S pilot:F probability 0.171, frequency 5.13e-6
- detect:S extinguish:F pilot:S probability 0.076, frequency 2.28e-6
- detect:F extinguish:S pilot:S probability 0.036, frequency 1.08e-6
- detect:S extinguish:F pilot:F probability 0.019, frequency 5.7e-7
- detect:F extinguish:S pilot:F probability 0.009, frequency 2.7e-7
- detect:F extinguish:F pilot:S probability 0.004, frequency 1.2e-7
- detect:F extinguish:F pilot:F probability 0.001, frequency 3e-8

top_function_failure_frequency returns {"sequences":
["detect:F extinguish:F pilot:F"], "frequency": 3e-8}: the undetected,
unsuppressed fire end state sits at 3e-8 per flight hour, which exceeds
the catastrophic target 1e-9 by a factor of 30, so this chain alone does
not meet the safety objective and the design needs an additional
independent barrier or a lower initiator frequency.

Example FHA class input for the screening (analyst classification by
consequence, the rule shown here is example-only and belongs to the FHA,
not the module): extinguish success rates the end state minor; extinguish
failure with detect success rates major; extinguish failure with detect
failure rates hazardous when the pilot action succeeds and catastrophic
when it fails. Screening each end state against the target of its own
class with dominant_sequences (real verdicts from the anchor run):
- detect:F extinguish:F pilot:F, catastrophic target 1e-9: 3e-8 >
  1e-9, DOMINANT, ratio 30.0000 (flagged: mitigation required).
- detect:F extinguish:F pilot:S, hazardous target 1e-7: 1.2e-7 > 1e-7,
  DOMINANT, ratio 1.2000 (flagged: thin margin, needs justification or
  improved detection and suppression).
- detect:S extinguish:F pilot:S and detect:S extinguish:F pilot:F,
  major target 1e-5: 2.28e-6 and 5.7e-7, not dominant.
- the four extinguish-success end states, minor target 1e-3: largest
  is the all-success chain at 2.052e-5, not dominant.
Global screening caution demonstrated by the same run: screening the
whole ranked list against MAJOR alone flags only the all-success end
state (2.052e-5 > 1e-5), which is not the dangerous sequence; each end
state must be screened against the target of its own FHA-rated class.

Run your module and take the real outputs as assert targets; the anchors
above are prep-verified, computed by running the prep anchor scripts
/tmp/w41spec/anchor_event_tree.py and /tmp/w41spec/classes.py
(prep-verified by stdlib math, python3.11, macOS).

## Validation list (contract test must include)

- build_paths over the fire nodes returns 8 paths in the documented
  enumeration order with the exact probabilities above (within 1e-12);
  probability sum identity = 1.0 exactly.
- outcome_frequencies(3e-5, nodes): frequency list sorted descending as
  tabulated, all 8 frequencies within 1e-12 of the table; frequency sum
  identity = 3e-05 exactly; dict keys exactly sequence, path,
  probability, frequency.
- outcome_frequencies single node: [("g", 0.5)] at initiator 1e-5 gives
  g:F 5e-6 then g:S 5e-6 (ties keep enumeration order).
- Boundary probabilities legal: nodes with p = 1.0 and p = 0.0 roll up
  without error (all-success and all-failure frequencies follow).
- is_failure_end_state: all-False tuple True; any True outcome False.
- top_function_failure_frequency on the fire rollup returns sequences
  ["detect:F extinguish:F pilot:F"] and frequency 3e-8 within 1e-15;
  identity with initiator x (0.05 x 0.10 x 0.20).
- dominant_sequences: FFF entry vs CATASTROPHIC dominant ratio 30.0
  within 1e-9; FFS entry vs HAZARDOUS dominant ratio 1.2 within 1e-9;
  SSS entry vs MINOR not dominant; equality boundary: an entry with
  frequency exactly MAJOR is NOT dominant; result order matches the
  input order.
- ValueErrors: negative initiator frequency; empty node list; 13 branch
  nodes (above BRANCH_NODES_MAX); a branch probability of 1.5 and of
  -0.1; severity target 0 and negative. 12 branch nodes at p = 0.5 all
  succeed: 4096 paths, all-success probability 2**-12 = 0.000244140625,
  max frequency 2**-12.
- Determinism: two calls return equal structures; fixed sequence strings.
- Sort identity: total order of the ranked list is descending frequency
  with enumeration-order tiebreak, no exceptions over random-free
  deterministic fixtures.

## Corpus fragment (eval/hit1-wave41-event-tree-analysis.yaml)

Query 1 (copy verbatim):
  "run the event-tree analysis from the cargo fire initiator: enumerate the binary branch paths through the detection and suppression functions and roll up the end-state frequency of every sequence"
  intent: "systems safety; forward event-tree branch enumeration and end-state frequency rollup"
  expected_skill: "systems-engineering-safety/arp4761a/event-tree-analysis"
Query 2 (copy verbatim):
  "flag the dominant event-tree sequences whose end-state frequency exceeds the severity target and sum the frequency of the paths that reach the failure end state"
  intent: "systems safety; dominant event-tree sequence screening and failure end-state frequency sum"
  expected_skill: "systems-engineering-safety/arp4761a/event-tree-analysis"
Task ids: w41-event-tree-analysis-1 and -2. Whole-corpus grep at prep:
no existing task in eval/hit1-corpus.yaml contains "event tree",
"event-tree", "branch path" or "end state", so both queries are
collision-free against the existing arp4761a tasks (sa3, sa4, xp5 route
fta-fmea on "fault tree", "minimal cut sets", "FMEA"; pra1, pra2 route
particular-risk-analysis on rotor burst, tire burst, exposure and hazard
zones; markov tasks route on Markov chains and transition rates).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must quantify the forward event-tree
sequences from an initiating event:" and include the outputs in the
Claim. First tag: event-tree-analysis. Additional tags ONLY:
event-sequence-rollup, end-state-frequency, dominant-sequence,
mitigating-function, initiator-frequency, failure-end-state. NEVER single
generic words (tree, event, branch, sequence, path, frequency, safety,
severity, target, probability, fire, risk). 50-150 words, <=1000 chars,
no em dash, no restricted content-policy wording, action verb present.

FORBIDDEN TOKENS (belong to siblings): cut-set, minimal-cut-set,
top-event, basic-event, and-gate, or-gate, gate-structure, fta, fmea,
fmeca, failure-mode (fta-fmea, failure-mode-criticality); rotor-burst,
tire-burst, bird-strike, containment, hazard-zone, conditional-
probability, exposure-probability (particular-risk-analysis);
fha-worksheet, failure-condition, severity-classification,
probability-targets, a-fha, s-fha (functional-hazard-assessment);
closure-gate, condition-margin, requirement-closure-status,
post-implementation-safety-verdict (ssa-closure); lognormal-error-factor,
lognormal-confidence-band, uncertainty-variance-share, exceedance-band,
fussell-vesely (fault-tree-uncertainty-analysis); markov-chain,
transition-rate, state-probability, absorbing-state, repair-rate,
availability (markov-analysis); beta-factor, zonal-safety-analysis,
common-mode, operating-support (pack siblings). The severity class names
catastrophic, hazardous, major, minor appear in the body only when naming
the target constants and the FHA class input; they are never used as tags
or as claims of classification work.
