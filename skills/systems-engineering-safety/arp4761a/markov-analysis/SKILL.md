---
name: markov-analysis
description: "Use when you must run a quantitative Markov analysis for an aircraft system safety model per ARP4761A: compute continuous time Markov chain state probabilities from the transition rate matrix, evaluate two-state failure and repair availability with steady state limits, derive the non-repairable failure probability and the mean time to failure, sum series failure rates, and estimate redundant configuration reliability with k-out-of-n combinations. Produces the state probability vector, the availability, and the MTTF that gate the quantitative safety case for the failed state. Trigger: Markov analysis, Markov chain, state probability, transition rate, failure rate, repair rate, availability, MTTF, absorbing state, k-out-of-n."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [markov-analysis, markov-chain, state-probability, transition-rate, absorbing-state, mission-reliability, mean-time-to-failure, availability-analysis, k-out-of-n-reliability]
  version: 0.1.0
  author: AeroSkills
---

# ARP4761A Markov Analysis (systems-engineering-safety/arp4761a/markov-analysis)

Use when the task is quantitative safety or reliability modeling of a
system with Markov analysis per ARP4761A: state probabilities from
transition rates, two-state failure and repair availability, MTTF,
and redundant configuration reliability.

## Domain quick reference

- A continuous time Markov chain (CTMC) models system states (for
  example fully operational, degraded, failed) with transitions at
  constant rates: failure rate lambda and repair rate mu, per hour.
- The state probability vector evolves by dP/dt = P Q, where Q is the
  transition rate matrix with the row sums zeroed on the diagonal, so
  P(t) = P(0) exp(Q t) conserves total probability.
- Two-state failure and repair model: P_failed(t) = lam/(lam+mu) *
  (1 - exp(-(lam+mu) t)); steady state unavailability is lam/(lam+mu)
  and availability is mu/(lam+mu).
- Non-repairable model (absorbing failed state): R(t) = exp(-lam t),
  failure probability 1 - exp(-lam t), mean time to failure 1/lam.
- Series chain total failure rate is the sum of the rates; an n-unit
  active redundancy without repair has MTTF (1/lam) * (1/n + 1/(n-1)
  + ... + 1), so two units give 3/(2 lam).
- At least k of n identical units surviving: sum over i from k to n of
  C(n,i) R^i (1-R)^(n-i) with R the per-unit reliability.
- Markov analysis quantifies failure conditions whose probability is
  then compared against the severity-based requirement in the SSA.

## Workflow

1. Define the states of the system (operational, degraded, failed)
   and the constant transition rates between them.
2. Build the transition rate matrix; diagonal entries are the negative
   row sums.
3. Compute the state probability vector at the mission time with
   state_probabilities.
4. For a two-state model, check availability with
   two_state_availability and the steady state limit.
5. For a non-repairable unit, compute the failure probability and MTTF
   with nonrepairable_probabilities and mttf_exponential.
6. Combine independent units with series_failure_rate and estimate
   redundant configurations with redundancy_mttf and
   k_of_n_reliability.
7. Compare the resulting failure probability against the safety
   requirement for the failure condition.

## Pitfalls

- Using the transition rate matrix with the diagonal filled instead of
  rebuilt as the negative row sum, which breaks probability
  conservation.
- Treating a repairable model as non-repairable and quoting 1/lam as
  the MTTF when repair restores the state.
- Summing failure rates for a redundant parallel pair as if the pair
  were in series, which understates the true reliability.
- Forgetting that k-of-n reliability needs the per-unit reliability
  at the mission time, not the steady state availability.
- Reporting a state probability vector that does not sum to 1 as
  evidence of a modeling error, when the chain conserves probability
  by construction.

## Behavior contract (gate 3)

The Markov logic is exercised by the gate 3 contract test:
scripts/test_markov_analysis.py against
scripts/markov_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_markov_analysis.py

## Compliance

- Standards referenced, not reproduced: ARP4761A text is proprietary
  (SAE); summary-only per standards-map.yaml and brief 06.
- Markov analysis is common reliability methodology (Annex L of
  ARP4761A), paraphrased; no verbatim standard text.
- compliance: STANDARDS-REF, gated: false.
