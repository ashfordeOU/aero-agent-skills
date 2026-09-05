# Wave-39 leaf spec: failure-mode-criticality (systems-engineering-safety, arp4761a pack)

- Path: skills/systems-engineering-safety/arp4761a/failure-mode-criticality/
- Pack: arp4761a. Closest siblings: fta-fmea (its entire logic module exports
  analysis_set_for_level, minimal_cut_sets, cut_set_probability,
  cut_set_sanity, fmea_severity_level; its SKILL body limits the FMEA role to
  cataloguing failure modes and mapping severity classes to development
  assurance levels - zero ranking, zero rate math), fault-tree-importance-
  measures (Birnbaum / Fussell-Vesely / RAW / RRW ranking over fault-tree
  basic events from minimal cut sets, NOT per-failure-mode criticality of an
  item), markov-analysis, reliability-block-diagram. Whole-tree greps at
  prep: "fmeca" = only fta-fmea files; "1629a" = 0 hits; "criticality" =
  only avionics DO-178C level ordering, FOD part-criticality (1-3 weighted
  score) and supplier qualitative categories - none compute a rate-based
  criticality number. The RPN trap: RPN = S x O x D (1-10 ratings) is owned
  by manufacturing-quality/as9100/risk-management (risk_priority_number);
  this leaf must NOT implement RPN. GENUINE SES gap (fresh probe).
- Standards id: arp4761a (reference-only). Ledger Standard: arp4761a.
- Family: systems-engineering-safety

## Claim

Quantify and rank the failure modes of an item by their contribution to the
item failure rate over an operating time: split the item failure rate into
per-mode rates with the mode ratios (each alpha, sum to 1), compute the
MIL-STD-1629A style quantitative criticality number C_m = beta * alpha *
lambda_p * t for every mode (beta = conditional failure-effect probability,
alpha = mode ratio, lambda_p = item failure rate, t = operating time), sum
the per-mode criticalities into the item criticality C_r, and rank the modes
by C_m with the share of item criticality and a dominant-mode flag. Produces
the per-mode rate split, the C_m values, C_r, and the sorted rank list that
gate maintenance and redesign prioritization. Does NOT do: minimal cut-set
generation, cut-set probability sanity or FMEA severity to DAL mapping
(fta-fmea); fault-tree basic-event importance ranking (fault-tree-
importance-measures); RPN rating scales (manufacturing-quality risk
management).

## Model (implement exactly)

Conventions: mode_ratios is a dict {mode_id: alpha} with every alpha in
(0, 1] and the sum within MODE_RATIO_TOLERANCE of 1.0. modes is a list of
dicts, each {id, alpha, beta} with beta in [0, 1].

Functions (pure stdlib):
- split_item_rate(item_failure_rate, mode_ratios) -> dict {mode_id:
  per-mode rate = alpha * lambda_p}; ValueError if lambda_p <= 0, empty
  mode_ratios, any alpha outside (0, 1], or |sum(alpha) - 1| >
  MODE_RATIO_TOLERANCE.
- mode_criticality(beta, alpha, item_failure_rate, operating_time) -> float
  C_m = beta * alpha * lambda_p * t; ValueError if beta outside [0, 1],
  alpha <= 0 or alpha > 1, item_failure_rate <= 0, operating_time < 0.
- item_criticality(modes, item_failure_rate, operating_time) -> float
  C_r = sum of C_m over all modes; ValueError if modes empty or any mode
  invalid.
- rank_modes(modes, item_failure_rate, operating_time) -> list of dicts,
  each {id, alpha, beta, cm, share, dominant}: sorted by cm descending with
  ties broken by mode id ascending (deterministic); share = cm / C_r;
  dominant = share >= DOMINANT_SHARE (0.5 module constant). ValueError as
  for item_criticality.
Module constants: MODE_RATIO_TOLERANCE = 1e-9, DOMINANT_SHARE = 0.5.

Identity to test: a single mode with alpha = beta = 1 gives C_m = C_r =
lambda * t; the shares over all modes sum to 1.0 (within float tolerance);
rank order by C_m is unchanged when every C_m is scaled by a positive
constant; mode_criticality is linear in beta, alpha and t separately.

## Worked example

Pump item, lambda_p = 2e-6 per hour, t = 5000 hours, three modes:
- runaway: alpha 0.2, beta 1.0 -> C_m = 1.0 * 0.2 * 2e-6 * 5000 = 2e-3.
- jammed: alpha 0.5, beta 0.05 -> C_m = 0.05 * 0.5 * 2e-6 * 5000 = 2.5e-4.
- no-output: alpha 0.3, beta 0.1 -> C_m = 0.1 * 0.3 * 2e-6 * 5000 = 3.0e-4.
C_r = 2.55e-3. rank_modes order: [runaway, no-output, jammed]; shares:
runaway 0.78431 (dominant True), no-output 0.11765, jammed 0.09804.
split_item_rate(2e-6, {runaway: 0.2, jammed: 0.5, no-output: 0.3}) ->
{runaway: 4e-7, jammed: 1e-6, no-output: 6e-7}.
Single-mode anchor: alpha = beta = 1, lambda = 3e-6, t = 4000 -> C = 1.2e-2.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (pure decimal arithmetic, independently
checked).

## Validation list (contract test must include)

- split_item_rate partition math on the pump example (4e-7 / 1e-6 / 6e-7).
- mode_criticality on the pump modes: 2e-3, 2.5e-4, 3.0e-4 within 1e-12.
- item_criticality = 2.55e-3; single-mode anchor 1.2e-2.
- rank order [runaway, no-output, jammed]; runaway share 0.78431 within
  1e-5 and dominant True; shares sum to 1.
- Mode-ratio validation: alphas summing to 0.99 or 1.01 raise ValueError;
  alpha 0 or 1.5 raises; empty dict raises.
- beta exactly 1.0 and 0.0 accepted; beta 1.01 or -0.1 raise ValueError.
- operating_time 0 returns 0.0 criticality; negative time raises.
- Tie-break determinism: two modes with equal C_m order by id ascending.
- Identity: C_r equals sum of C_m; single mode C_r = lambda * t.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-failure-mode-criticality.yaml)

Query 1 (copy verbatim):
  "compute the failure-mode-criticality number of each pump failure mode from the mode-ratio and the item failure rate over the 5000 hour operating time"
  intent: "systems-engineering-safety; rate-based FMECA criticality number C_m"
  expected_skill: "systems-engineering-safety/arp4761a/failure-mode-criticality"
Query 2 (copy verbatim):
  "rank the failure modes by the fmeca-criticality item-criticality value using the failure-effect-probability to prioritize the reliability actions"
  intent: "systems-engineering-safety; item criticality ranking with failure-effect probability"
  expected_skill: "systems-engineering-safety/arp4761a/failure-mode-criticality"
Task ids: w39-failure-mode-criticality-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must quantify and rank the failure modes
of an item by their rate-based criticality:" and include the outputs in the
Claim. First tag: failure-mode-criticality. Additional tags ONLY:
fmeca-criticality, criticality-number, mode-ratio, failure-effect-
probability, item-criticality. NEVER single generic words (failure, mode,
criticality, ranking, probability, rate). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): cut-set, minimal cut set, analysis
set, severity to DAL mapping (fta-fmea); rpn, risk-priority-number
(manufacturing-quality/as9100/risk-management); birnbaum, fussell-vesely,
risk-achievement-worth, risk-reduction-worth (fault-tree-importance-
measures); state probability, transition rate (markov-analysis).
