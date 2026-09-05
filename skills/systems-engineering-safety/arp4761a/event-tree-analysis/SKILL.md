---
name: event-tree-analysis
description: "Use when you must run a forward event-tree analysis of the sequences from an initiating event: enumerate every binary branch path through an ordered list of mitigating functions, each with its success probability, roll up each end-state outcome frequency as the initiator frequency times the product of the branch probabilities along the path, rank the end-state paths by frequency, sum the frequency over the paths that reach the failure end state, and screen the ranked sequences against the ARP4761A-class per-flight-hour severity targets to flag the dominant sequences. Produces the full path enumeration with per-path probabilities and frequencies, the frequency-ranked end-state list, the failure-end-state frequency sum and the dominant-sequence flags. Trigger: event tree, initiating event, mitigating function, branch path, end state, failure end state, dominant sequence, initiator frequency."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
- id: arp4761a
  reference-only: true
gated: false
domain: systems-engineering-safety
pack: arp4761a
compatibility: agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags:
  - event-tree-analysis
  - event-sequence-rollup
  - end-state-frequency
  - dominant-sequence
  - mitigating-function
  - initiator-frequency
  - failure-end-state
  version: 0.1.0
  author: AeroSkills
---

# ARP4761A Event-Tree Analysis (systems-engineering-safety/arp4761a/event-tree-analysis)

Use when the task is forward event-tree analysis of an aircraft system
safety case per ARP4761A: starting from one initiating event, enumerate
every binary branch path through an ordered list of mitigating
functions, roll up each end-state outcome frequency, sum the frequency
of the failure end state, and screen the dominant sequences against the
per-flight-hour severity targets. This leaf is the forward dual of
fault tree analysis: FTA works backward from a top event through gates
to basic events, while this leaf works forward from an initiator
through successive mitigating-function branches. It consumes the FHA
severity class of each end state (rated by
functional-hazard-assessment, never re-derived here) and feeds end-state
frequencies into the SSA close-out work. Pairs with
systems-engineering-safety/arp4761a/fta-fmea for the backward side and
with systems-engineering-safety/arp4761a/particular-risk-analysis for
single-event forward risk that does not branch.

## Domain quick reference

- An event tree starts from one initiating event with a per-flight-hour
  frequency q0 and lets each ordered mitigating function (for example
  fire detection, extinguisher discharge, pilot action) either succeed
  with probability p or fail with probability 1 - p.
- Full binary expansion: N branch nodes give 2**N end-state paths.
  Enumeration is the ascending binary mask with node i mapped to bit i,
  so the all-failure path (mask 0) comes first and the all-success path
  (mask 2**N - 1) comes last. The cap is BRANCH_NODES_MAX = 12 nodes =
  4096 paths; 13 nodes (8192 paths) raise ValueError.
- Path probability: the product of the branch probabilities along the
  path, p for a success branch and 1 - p for a failure branch. The
  probabilities of the full expansion sum to exactly 1.0.
- End-state frequency: frequency = q0 x path probability for every
  end-state path; the frequencies of the full expansion sum to exactly
  the initiator frequency q0 (the expansion partitions the initiator).
- Failure end state: under the series-barriers reading, the path where
  no mitigating function contained the initiator (every outcome False).
  Its frequency is the top-function failure frequency, the undetected
  and uncontained end state that the mitigating chain must push below
  its severity target.
- Dominant sequence: an end-state sequence whose frequency strictly
  exceeds the severity target of its FHA class (frequency > target;
  equality is NOT dominant). Ratio = frequency / target.
- ARP4761A-class per-flight-hour severity targets, magnitude only and
  mirrored from the FHA probability-target mapping: CATASTROPHIC 1e-9,
  HAZARDOUS 1e-7, MAJOR 1e-5, MINOR 1e-3. The class of each end state is
  an analyst input from the FHA and is never derived in the module:
  screen each end state against the target of its own class.
- Deterministic binary enumeration only: no Monte Carlo, no time
  integration, no analyst weighting inside the rollup.

## Workflow

1. Fix the initiating event: state the initiator and its per-flight-hour
   frequency q0 from the prior analysis (for example an FHA or
   preliminary assessment). q0 must be non-negative;
   outcome_frequencies rejects a negative initiator frequency with
   ValueError.
2. List the ordered mitigating functions: build the branch node list of
   (name, p_success) tuples in the order the functions act; the failure
   probability of each function is 1 - p_success. At most
   BRANCH_NODES_MAX = 12 nodes keep the expansion at 4096 paths; the
   boundary probabilities 0.0 and 1.0 are legal.
3. Enumerate the binary branch tree with build_paths: the full 2**N
   expansion from the all-failure path (mask 0, first) to the
   all-success path (mask 2**N - 1, last). Every end-state path carries
   its readable sequence string (name:S or name:F per node in node
   order), its bool path (True = the function succeeds) and the
   branch-probability product along the path.
4. Roll up and rank the end-state frequencies with
   outcome_frequencies(q0, nodes): frequency = q0 x path probability for
   every end-state path, ranked descending by frequency with ties broken
   by enumeration order (stable sort).
5. Sum the failure end-state frequency with is_failure_end_state and
   top_function_failure_frequency: the all-failure path is the failure
   end state where no mitigating function contained the initiator; the
   function returns its sequence and the sum of the frequencies of the
   paths reaching it.
6. Screen the ranked sequences with dominant_sequences: pass the
   per-flight-hour severity target of each end state's FHA class
   (CATASTROPHIC 1e-9, HAZARDOUS 1e-7, MAJOR 1e-5, MINOR 1e-3, the
   magnitude targets only). A frequency strictly above its class target
   flags the sequence dominant with ratio = frequency / target; an end
   state sitting exactly on its target is not dominant.
7. Judge the mitigating chain: any dominant sequence, or a top-function
   failure frequency above its class target, means the chain alone does
   not meet the safety objective for the initiator. Add an independent
   barrier or lower the initiator frequency and re-run steps 2 to 6.
8. Confirm deterministic behavior with the contract test:
   python3 scripts/test_event_tree_analysis.py.

## Worked example

Cargo-compartment fire. Initiating event: cargo fire ignition at
initiator_frequency q0 = 3e-5 per flight hour. Three mitigating
functions in series, branch nodes [("detect", 0.95), ("extinguish",
0.90), ("pilot", 0.80)]: fire detection, extinguisher discharge, pilot
action. Failure probabilities are 0.05, 0.10 and 0.20. Real module
outputs from the smoke run (python3, stdlib, deterministic):

Path probabilities in enumeration order (module sum exactly 1.0):
detect:F extinguish:F pilot:F 0.001, detect:S extinguish:F pilot:F
0.019, detect:F extinguish:S pilot:F 0.009, detect:S extinguish:S
pilot:F 0.171, detect:F extinguish:F pilot:S 0.004, detect:S
extinguish:F pilot:S 0.076, detect:F extinguish:S pilot:S 0.036,
detect:S extinguish:S pilot:S 0.684. Each raw float sits within 1e-15
of the products of the decimal inputs, so the displayed values are the
module outputs rounded.

outcome_frequencies(3e-5, nodes) ranked descending (module frequency sum
exactly 3e-05 = the initiator):

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
the catastrophic target 1e-9 by a factor of 30 (module ratio
30.000000000000014, within 1e-9 of 30), so this chain alone does not
meet the safety objective and the design needs an additional independent
barrier or a lower initiator frequency.

Example FHA class input for the screening (analyst rating by consequence
belongs to the FHA, not the module): extinguish success rates the end
state minor; extinguish failure with detect success rates major;
extinguish failure with detect failure rates hazardous when the pilot
action succeeds and catastrophic when it fails. Screening each end state
against the target of its own class with dominant_sequences (real module
verdicts):

- detect:F extinguish:F pilot:F vs CATASTROPHIC 1e-9: 3e-8 > 1e-9,
  DOMINANT, ratio 30.0 (mitigation required).
- detect:F extinguish:F pilot:S vs HAZARDOUS 1e-7: 1.2e-7 > 1e-7,
  DOMINANT, ratio 1.2 (module 1.200000000000001, thin margin, needs
  justification or improved detection and suppression).
- detect:S extinguish:F pilot:S and detect:S extinguish:F pilot:F vs
  MAJOR 1e-5: 2.28e-6 and 5.7e-7, not dominant.
- the four extinguish-success end states vs MINOR 1e-3: largest is the
  all-success chain at 2.052e-5, not dominant.

Global screening caution from the same run: screening the whole ranked
list against MAJOR alone flags only the all-success end state (2.052e-5
> 1e-5, module ratio 2.052), which is not the dangerous sequence; each
end state must be screened against the target of its own FHA-rated
class.

## Verification

- build_paths over the fire nodes returns 8 paths in the documented
  binary-mask order and the path probabilities sum to exactly 1.0.
- outcome_frequencies(3e-5, fire nodes) returns the ranked list above;
  the frequencies sum to exactly 3e-05 and each entry carries exactly
  the keys sequence, path, probability, frequency.
- A single node at p = 0.5 and initiator 1e-5 splits evenly into g:F
  5e-6 then g:S 5e-6 (ties keep enumeration order).
- Boundary probabilities are legal: p = 1.0 puts the whole initiator on
  the success end state, p = 0.0 on the failure end state.
- The 12-node all p = 0.5 tree enumerates 4096 paths with all-success
  probability exactly 2**-12 = 0.000244140625 and max frequency
  2**-12.
- The failure end-state frequency 3e-8 matches the initiator x (0.05 x
  0.10 x 0.20) identity within 1e-15; the dominant ratios 30.0 and 1.2
  hold within 1e-9.
- ValueError rejection of non-physical inputs: negative initiator
  frequency, empty node list, 13 branch nodes, branch probability 1.5
  or -0.1, and severity target 0 or negative all raise ValueError.
- Run the contract test offline: python3
  scripts/test_event_tree_analysis.py (33 tests, deterministic, all
  pass in under a second).

## Related leaves

- systems-engineering-safety/arp4761a/fta-fmea: the backward dual,
  top-event probability and cut sets from AND/OR gate structures over
  basic events.
- systems-engineering-safety/arp4761a/functional-hazard-assessment:
  the FHA severity classes that each end state consumes as input.
- systems-engineering-safety/arp4761a/ssa-closure: closes the SSA over
  the assessed conditions using the per-flight-hour severity targets.
- systems-engineering-safety/arp4761a/particular-risk-analysis:
  single-event forward risk combination without branch trees.
- systems-engineering-safety/arp4761a/markov-analysis: time-domain
  state probabilities from transition rates, the neighbor this leaf
  does not overlap.

## Pitfalls

- Screening the whole ranked list against one target: in the worked
  example a single MAJOR screen flags only the all-success end state
  (2.052e-5 > 1e-5), which is not the dangerous sequence, while the
  catastrophic failure end state at 3e-8 sails under that screen. Each
  end state must be screened against the target of its own FHA class.
- Reading equality with the target as dominant: the comparison is
  strict, frequency > target, so an end state sitting exactly on its
  severity target is not flagged and still needs a margin argument.
- Re-ordering or dropping a mitigating function after the rollup: the
  failure end state is the all-failure path of the exact node list in
  force; every barrier added multiplies the failure end-state frequency
  by its own 1 - p and every re-order changes the sequence strings, so
  re-run the enumeration after any chain change.
- Misreading the mask order: node i maps to bit i of an ascending
  binary mask, so mask 0 (all failure) is the FIRST path and mask
  2**N - 1 (all success) is the LAST; a reversed reading swaps the
  failure and success end states.
- Letting the module invent severity classes: the class of each end
  state is an analyst input from the FHA (extinguish failure with
  detect failure rates hazardous or catastrophic by consequence); the
  module only screens against the target it is handed.
- Reaching for this leaf outside its scope: backward fault-tree gates,
  cut sets and top-event logic from basic events, lognormal uncertainty
  bands, and Markov time evolution belong to the sibling leaves listed
  above, not to the forward branch rollup.

## Contract test

The contract test scripts/test_event_tree_analysis.py (stdlib unittest,
offline, deterministic) exercises the whole workflow: the binary
branch-tree enumeration and probability table of step 3, the ranked
end-state frequency rollup and exact partition identities of step 4,
the failure end-state frequency sum of step 5, the dominant-sequence
screening with ratios and the strict-equality rule of step 6, every
ValueError rejection of the validation list, the 12-node expansion cap,
and determinism. Run it from the repo root:

    python3 skills/systems-engineering-safety/arp4761a/event-tree-analysis/scripts/test_event_tree_analysis.py

## Behavior contract (gate 3)

The event-tree logic is exercised by the gate 3 contract test:
scripts/test_event_tree_analysis.py against
scripts/event_tree_analysis_logic.py (stdlib unittest, offline). Run:

    python3 scripts/test_event_tree_analysis.py

from the leaf directory, or the full path from the repo root as shown
in the Contract test section. Exit 0 with 33 tests passing satisfies
the behavior contract gate.

## Compliance

- Standards referenced, not reproduced: ARP4761A is proprietary SAE
  guidance (reference-only per standards-map.yaml); this leaf states
  engineering methodology in its own words, summary-only, and the
  severity targets appear by magnitude only as module constants.
- The event-tree method is the forward dual of fault tree analysis as
  practiced in system safety assessments; no verbatim standard text is
  included.
- compliance: STANDARDS-REF, gated: false.
