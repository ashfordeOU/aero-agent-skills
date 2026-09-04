---
name: information-entropy
description: "Use when you must compute the information content of a symbol distribution: the Shannon entropy in bits per symbol of a measured count distribution or probability mass function, the binary entropy function of a two-symbol source, the uniform-distribution entropy bound log2 of the symbol count, and the minimum source-coding bit rate as entropy times symbol rate. Produces the entropy, the uniform bound, the redundancy verdict against it, and the minimum bit rate that gates data-channel and quantization assessments. Pure Python stdlib, deterministic. Trigger: information-entropy, shannon-entropy, binary-entropy-function, source-coding-bound, information-content, telemetry symbol distribution, source coding bit rate, symbol distribution entropy."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: numerics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [information-entropy, shannon-entropy, binary-entropy-function, source-coding-bound, information-content]
  version: 0.1.0
  author: AeroSkills
---

# Information Entropy (cross-cutting/numerics/information-entropy)

Use when the task is the information-theoretic content of a symbol
distribution for aerospace data-channel work: the Shannon entropy in
bits per symbol of a measured count distribution or a stated
probability mass function, the binary entropy function for a
two-symbol source, the uniform-distribution entropy bound as log2 of
the symbol count, and the minimum source-coding bit rate of a symbol
stream as entropy times symbol rate. This leaf is the pure
information-measure utility of the numerics pack: deterministic,
stdlib only, no RNG. It pairs with
flight-test-operations/planning/pcm-telemetry-decommutation, where the
recovered channel symbol stream is the stream whose entropy and
minimum bit rate this leaf sizes. It does NOT fit probability models,
estimate frequency spectra, sample or estimate densities, or build
coding trees: the numerics siblings below own those operations.

## Domain quick reference

- Shannon entropy: H = -sum(p_i * log2(p_i)) bits per symbol over the
  normalized probabilities; a zero-probability symbol contributes
  0 * log2(0) = 0. Raw counts are normalized by their total first, so
  counts and probabilities give identical results.
- Binary entropy function: b(p) = -p log2(p) - (1-p) log2(1-p) for a
  two-symbol source with symbol probability p. Endpoints give
  b(0) = b(1) = 0 (fully deterministic source) and the peak is
  b(0.5) = 1 bit. The function is symmetric, b(p) = b(1-p).
- Uniform bound: H_uniform = log2(N) for N symbols, the maximum
  entropy any distribution over N symbols can reach, so
  H <= log2(N) always. Redundancy against the bound is
  1 - H / log2(N): 0 for a uniform source, 1 for a deterministic one.
- Minimum source-coding bit rate: R_min = H * r bits per second for a
  stream of r symbols per second. Shannon source coding says the
  average code length per symbol cannot go below H, so R_min is the
  floor bit rate the data channel must carry and quantization must
  respect.
- Units: bits per symbol for entropy, symbols per second for the
  symbol rate, bits per second (bps) for the minimum bit rate.
- NACA TR-824 anchors the numerics-pack reference convention; the
  relations above are standard information-theory methodology,
  summary-only.

## Workflow

1. Assemble the symbol distribution of the data channel: raw symbol
   counts from a measurement window, or the probability mass function
   when it is known directly.
2. Run shannon_entropy on the distribution to get entropy_bits and the
   normalized probabilities; the function accepts counts or
   probabilities and normalizes internally.
3. For a two-symbol source (single bit per symbol, on-off channel),
   run binary_entropy with the probability of one symbol instead.
4. Run uniform_entropy with the symbol count to get the log2 upper
   bound for the comparison.
5. Size the channel floor: min_bit_rate with the per-symbol entropy
   and the symbol rate in symbols per second.
6. For the consolidated verdict, run entropy_summary with the
   distribution and symbol rate: entropy, symbol count, uniform bound,
   redundancy, and minimum bit rate in one dict.
7. Confirm the deterministic checks with the contract test
   scripts/test_information_entropy.py.

## Worked example

A telemetry data channel carries four symbol classes with p = [0.5,
0.25, 0.125, 0.125] at 1000 symbols per second (module outputs shown).

- shannon_entropy(p) returns entropy_bits 1.75 bits per symbol and
  normalized [0.5, 0.25, 0.125, 0.125]; the same call on counts
  [4, 2, 1, 1] returns the same 1.75 bits.
- binary_entropy(0.9) returns 0.4689955935892811, 0.4690 bits within
  the worked-example bound; binary_entropy(0.5) returns exactly 1.0.
- uniform_entropy(4) returns 2.0 bits and uniform_entropy(8) returns
  3.0 bits, the log2 upper bounds.
- min_bit_rate(1.75, 1000.0) returns 1750.0 bps.
- entropy_summary(p, 1000.0) returns entropy_bits 1.75, n_symbols 4,
  uniform_bound_bits 2.0, redundancy 0.125 (1 - 1.75/2), and
  min_bit_rate_bps 1750.0.
- The same channel carrying a uniform 8-symbol source at 1000 symbols
  per second needs min_bit_rate(3.0, 1000.0) = 3000 bps, so the
  four-symbol message reduces the channel floor by 42 percent
  ((3000 - 1750) / 3000 = 0.4167).
- A skew distribution [0.9, 0.05, 0.03, 0.02] gives 0.6175431233120147
  bits per symbol, well below the 2.0 bit bound for 4 symbols.

## Pitfalls

- Feeding any negative probability or count, or a zero-sum input: the
  module raises ValueError, as it does for empty input and binary p
  outside [0, 1].
- Expecting entropy above log2(N): H always lies between 0 and log2(N),
  so a uniform 4-symbol source gives exactly 2.0 bits and skew sources
  sit below (0.6175 for [0.9, 0.05, 0.03, 0.02]) — a result above the
  bound means invalid input, not a dense source.
- Misreading binary_entropy at its endpoints: b(0.0) = b(1.0) = 0.0,
  b(0.5) = 1.0 exactly, and the function is symmetric, b(p) = b(1-p).
- Treating counts and probabilities as interchangeable without the
  normalization rule: counts normalize identically to probabilities
  ([5, 5] and [0.5, 0.5] both give 1.0 bit), but every entry must be
  non-negative and the sum nonzero.
- Quoting the entropy as the channel rate: the floor is min_bit_rate =
  entropy times symbol rate (1750 bps at 1000 symbols/s), and the
  four-symbol saving over the uniform 8-symbol source (3000 bps) only
  holds at the same symbol rate.
- Calling entropy_summary on fewer than 2 symbols or with a negative
  entropy or symbol rate: it raises ValueError, and redundancy is only
  meaningful in [0, 1] for a valid distribution (0 uniform, 1
  deterministic).

## Verification

- Confirm shannon_entropy([0.5, 0.25, 0.125, 0.125]) returns entropy
  1.75 bits and that H is always between 0 and log2(N): deterministic
  inputs give exactly 0, the uniform input equals uniform_entropy(N).
- Confirm counts normalize identically to probabilities:
  [5, 5] gives 1.0 bit, the same as [0.5, 0.5].
- Confirm binary_entropy(0.5) = 1.0, endpoints binary_entropy(0.0)
  and binary_entropy(1.0) = 0.0, and the symmetry b(p) = b(1-p).
- Confirm entropy_summary redundancy is 0 for a uniform source and 1
  for a fully deterministic source, and sits in [0, 1] for every valid
  distribution.
- Confirm ValueError rejection: empty input, any negative
  probability or count, zero-sum input, binary p outside [0, 1],
  uniform n_symbols below 1, negative entropy or symbol rate in
  min_bit_rate, and entropy_summary on fewer than 2 symbols.
- Confirm determinism: identical inputs give identical outputs; the
  module never uses random numbers.
- Run the contract test offline: python3
  scripts/test_information_entropy.py (32 tests, deterministic).

## Related leaves

- cross-cutting/numerics/probability-distributions: distribution
  parameter estimation and pdf/cdf work, the model step that can feed
  this leaf its probability mass function (no entropy there).
- cross-cutting/numerics/descriptive-statistics: location and spread
  summaries of measured symbol counts before the entropy step.
- cross-cutting/numerics/monte-carlo-sampling: seeded random draws and
  empirical density estimation, not information measures.
- cross-cutting/numerics/fast-fourier-transform and
  cross-cutting/numerics/power-spectral-density: frequency-domain
  spectra, a different content view from per-symbol information.
- cross-cutting/numerics/hypothesis-testing: significance tests on
  symbol-count tables, complementary to the entropy summary.
- flight-test-operations/planning/pcm-telemetry-decommutation: recovers
  the telemetry channel symbol stream whose entropy and minimum bit
  rate this leaf computes.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_information_entropy.py

The test covers the spec worked-example anchors (Shannon entropy 1.75
bits for p = [0.5, 0.25, 0.125, 0.125], binary entropy 0.4690 at
p = 0.9, minimum bit rate 1750 bps at 1000 symbols per second, the
3000 bps uniform-8 comparison and its 42 percent reduction), the
identities (uniform distribution entropy equals log2(N), deterministic
sources give 0, b(0.5) = 1, endpoint and symmetry behavior of the
binary entropy function, counts matching probabilities), the
max-entropy bound H <= log2(N), dict key contracts, determinism, and
ValueError rejection of empty, negative, zero-sum, out-of-range and
sub-scale inputs. Runs in well under a second.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 anchors the
  numerics-pack public-domain reference convention; Shannon entropy
  and the source-coding bound are standard information-theory
  methodology (paraphrase-only) per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
