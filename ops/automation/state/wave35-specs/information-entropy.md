# Wave-35 leaf spec: information-entropy (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/information-entropy/
- Pack: numerics. Closest siblings: probability-distributions
  (distribution FITTING: normal/lognormal/Weibull/exponential
  parameter estimation, pdf/cdf/quantile, goodness of fit - no
  entropy), descriptive-statistics (location/spread summaries),
  monte-carlo-sampling (seeded random draws, histogram estimation),
  fast-fourier-transform and power-spectral-density (frequency-
  domain spectra, not information content), hypothesis-testing
  (tests/ANOVA). Repo-wide grep proves ZERO owners for Shannon
  entropy, binary entropy, information content; the only "entropy"
  hits are thermodynamic false positives (cea combustion, normal
  shock). CC numerics leaves carry naca-tr-824 reference-only as the
  numerics convention (matrix-operations, hypothesis-testing,
  descriptive-statistics precedent).
- Standards id: naca-tr-824 (reference-only; numerics convention).
  Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Compute the information-theoretic content of a symbol distribution
for aerospace data-channel analysis: the Shannon entropy of a
measured count distribution or a given probability mass function in
bits per symbol, the binary entropy function for a two-symbol
source, the entropy of the uniform distribution as the log2
cardinality upper bound, and the minimum source-coding bit rate for
a symbol stream as the entropy times the symbol rate. Produces the
entropy, the uniform-distribution bound, the redundancy verdict
against that bound, and the minimum bit rate that gate data-channel
and quantization assessments.

Does NOT do: probability distribution fitting or goodness-of-fit
(probability-distributions); spectral estimation (fast-fourier-
transform, power-spectral-density); histogram or density estimation
(monte-carlo-sampling, descriptive-statistics); compression
algorithms (Huffman, LZW etc.); KL divergence, cross-entropy or
channel capacity beyond the single-distribution entropy.

## Model (implement exactly)

Module constants: none beyond defaults.

Conventions: probabilities are normalized internally; raw counts are
accepted and normalized by their sum. 0 * log2(0) is treated as 0
(an empty symbol contributes nothing).

Functions (pure stdlib):
- shannon_entropy(symbol_probs_or_counts) -> dict {entropy_bits,
  normalized} = -sum(p_i log2 p_i) over the normalized values.
  ValueErrors: empty input; any negative value; sum <= 0.
- binary_entropy(p) -> -p log2 p - (1-p) log2(1-p) (p in [0,1];
  endpoints return 0). ValueError: p outside [0, 1].
- uniform_entropy(n_symbols) -> log2(n_symbols). ValueError:
  n_symbols < 1.
- min_bit_rate(entropy_bits, symbol_rate_per_s) ->
  entropy * symbol rate. ValueErrors: entropy < 0, rate < 0.
- entropy_summary(symbol_probs_or_counts, symbol_rate_per_s) ->
  dict {entropy_bits, n_symbols, uniform_bound_bits, redundancy
  (1 - H / log2(n)), min_bit_rate_bps}. ValueError: n_symbols < 2
  (uniform bound needs at least 2 symbols).

Identity to test: uniform distribution over N symbols gives entropy
exactly log2(N); a deterministic single-symbol distribution gives
entropy exactly 0; binary_entropy(0.5) = 1.0; H <= log2(N) always
for a valid distribution over N symbols.

## Worked example

Run your module and take the real outputs as assert targets, then
check the magnitude bounds (independently verified at prep):
- Distribution p = [0.5, 0.25, 0.125, 0.125]:
  shannon_entropy = 1.7500 bits/symbol.
- binary_entropy(0.9) = -0.9 log2 0.9 - 0.1 log2 0.1 = 0.4690 bits.
- uniform_entropy(4) = 2.0 bits; uniform_entropy(8) = 3.0 bits.
- entropy_summary for p at 1000 symbols/s: entropy 1.75, uniform
  bound 2.0, redundancy 0.125, min_bit_rate = 1750 bps (vs 3000 bps
  for a uniform 8-symbol source at the same rate, a 42 percent
  reduction bound).

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: empty input; negative probability/count; zero-sum
  input; p outside [0,1]; n_symbols < 1; negative rates.
- H >= 0 for any valid input; a deterministic [1.0] distribution ->
  0.0 bits.
- Raw counts normalize identically to their probability
  equivalents: counts [5, 5] -> entropy 1.0 bit.
- uniform_entropy(4) == 2.0 and == shannon_entropy([0.25]*4);
  uniform_entropy(2) == 1.0.
- binary_entropy(0.5) == 1.0; endpoints binary_entropy(0.0) == 0.0
  and binary_entropy(1.0) == 0.0; symmetry b(p) == b(1-p).
- Worked example anchors 1.7500 / 0.4690 / 1750 within 1e-4 /
  1e-4 / 1e-9.
- Max-entropy bound: for the worked distribution H <= log2(4); for
  a skew [0.9, 0.05, 0.03, 0.02] H < log2(4).
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-information-entropy.yaml)

Query 1 (copy verbatim):
  "compute the Shannon entropy in bits per symbol of a telemetry symbol distribution and the minimum source coding bit rate"
  intent: "cross-cutting; Shannon entropy and minimum source coding bit rate"
  expected_skill: "cross-cutting/numerics/information-entropy"
Query 2 (copy verbatim):
  "compute the binary entropy function and the uniform distribution entropy bound for an aerospace data channel assessment"
  intent: "cross-cutting; binary entropy function and uniform entropy bound"
  expected_skill: "cross-cutting/numerics/information-entropy"
Task ids: w35-information-entropy-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the information
content of a symbol distribution:" and include the outputs in the
Claim. First tag: information-entropy. Additional tags ONLY:
shannon-entropy, binary-entropy-function, source-coding-bound,
information-content. NEVER single generic words (entropy,
information, symbol, coding, channel, distribution, data). 50-150
words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): weibull, lognormal,
kolmogorov, goodness of fit, quantile (probability-distributions);
periodogram, welch, psd, fft (power-spectral-density,
fast-fourier-transform); histogram, bootstrap (monte-carlo-sampling);
huffman, compression algorithm (out of scope); channel capacity,
mutual information (out of scope).
