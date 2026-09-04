# Wave-33 leaf spec: flight-vibration-survey (flight-test-operations, flutter pack)

- Path: skills/flight-test-operations/flutter/flight-vibration-survey/
- Pack: flutter. Sibling receipts: envelope/buffet-boundary-testing
  owns RMS-rise ONSET detection during high-Mach pull-ups;
  flutter/ground-vibration-testing owns the GROUND modal survey
  (structure suspended); flutter/limit-cycle-oscillation owns
  time-domain sustained-oscillation amplitude;
  envelope/structural-coupling-test is control-system loop margins.
  Zero tach/order/track-and-balance/1-per-rev content family-wide;
  whole-repo zero vibration-survey/track-and-balance hits. Rotorcraft
  leaves own hover/level-flight power reduction only. This leaf owns
  in-flight mechanical vibration survey reduction (order domain).
- Standards id: far-29 (reference-only; matching the rotorcraft
  siblings) + far-25/cs-25 25.251-context reference (paraphrase only).
  Ledger Standard: far-29.
- Family: flight-test-operations

## Claim

Reduce an in-flight mechanical vibration survey (rotorcraft main-rotor
track-and-balance and airframe vibration limits; fixed-wing vibration/
buzz survey) from measured accelerometer time histories: extract
per-order (N/rev) amplitudes with a synchronous DFT over integer-
revolution windows, compute windowed total RMS survey levels, combine
the order components by root-sum-square, and gate each survey point
against the declared vibration limit and the 1P trim limit. Produces
the per-order amplitudes, the total level, and the pass/needs-trim
verdicts.

Does NOT do: buffet onset detection (buffet-boundary-testing); ground
vibration modal survey (ground-vibration-testing); LCO sustained
oscillation (limit-cycle-oscillation); control-system loop margins
(structural-coupling-test); rotorcraft power reduction
(rotorcraft-performance-flight-test and the forward-flight sibling).

## Model (implement exactly)

Conventions: sampled accelerometer time history x (g), sample rate
rate (Hz), rotor frequency rotor_hz (Hz), survey segment length N =
m_revs * rate / rotor_hz (integer-revolution window; N must be an
integer - the builder should round to the nearest integer sample count
and document the convention; for synthetic exactness choose parameters
that make N integer).
- Synchronous order DFT at order p: A_p = (2/N) |sum_{k=0}^{N-1} x_k
  exp(-j 2 pi (p m) k / N)| where the bin index is p * m_revs (the
  p-per-rev component falls exactly on bin p*m_revs of the m-rev
  window). Exact (no leakage) for integer-rev windows.
- Total RMS over a segment: RMS = sqrt(mean(x^2)).
- RSS of orders: RMS_tot = sqrt(sum_p A_p^2 / 2) (identity: equals the
  full-record RMS over integer revolutions for a pure multi-order
  signal).
- Vibration verdict: margin = (limit - level) / limit, pass if margin
  >= 0.
- 1P trim verdict: margin on the 1P component against the trim limit.

Functions (pure stdlib):

- order_amplitude(samples, sample_rate_hz, rotor_hz, order, m_revs) ->
  A_p via the synchronous DFT formula (pure stdlib complex exp; N
  integer convention). ValueErrors on non-positive inputs, order < 1,
  m_revs < 1.
- total_rms(samples) -> sqrt(mean(x^2)). ValueError on empty.
- windowed_rms(samples, sample_rate_hz, window_s) -> list of RMS per
  window (sliding, hop = window; last partial window dropped or
  documented).
- rss_of_orders(order_amps) -> sqrt(sum(A^2)/2) over the dict values.
  ValueError on empty dict.
- vibration_verdict(level_g, limit_g) -> dict {margin, pass}.
  ValueError if limit_g <= 0.
- trim_verdict(amp_1p_g, limit_1p_g) -> dict {margin, needs_trim}.
- vibration_survey_summary(samples, sample_rate_hz, rotor_hz, orders,
  m_revs, vibration_limit_g, trim_limit_g) -> dict with the order
  amplitudes, total RMS, RSS check, and both verdicts.

## Worked example

Rotor 5.0 Hz, 1000 Hz sampling, signal = 0.15 g at 1P + 0.06 g at 2P +
0.08 g at 4P (deterministic sines), 12-rev window (N = 12 * 1000 / 5 =
2400 samples).

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- Recovered order amplitudes: 0.150000 / 0.060000 / 0.080000 g (exact
  to 1e-6).
- Full-record RMS about 0.12748 g = RSS of orders about 0.12748 g
  (identity holds).
- Survey margin vs a 0.15 g limit: +0.150 -> pass.
- 1P trim margin vs a 0.10 g limit: -0.500 -> needs-trim flag.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: non-positive sample rate/rotor Hz/order/m_revs/limit;
  empty samples.
- Exact-order recovery: single-tone segments at 1P/2P/4P recover the
  amplitudes to 1e-6.
- RSS identity: rss_of_orders equals total_rms to 1e-6 for the pure
  multi-order signal.
- Leakage check: an off-order tone (e.g. 2.5P) does not appear in the
  integer-order bins beyond the DFT sidelobe level.
- Verdict logic: level below limit -> pass with positive margin; level
  above -> fail.
- Determinism: identical outputs run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-flight-vibration-survey.yaml)

Query 1 (copy verbatim):
  "rotorcraft track and balance vibration survey order analysis of the main rotor 1 per rev amplitude from measured accelerometer time histories"
  intent: "flight-test-operations; rotorcraft track-and-balance vibration survey order analysis"
  expected_skill: "flight-test-operations/flutter/flight-vibration-survey"
Query 2 (copy verbatim):
  "reduce the in flight mechanical vibration survey point to per order amplitudes and total rms and gate it against the declared vibration limit"
  intent: "flight-test-operations; in-flight vibration survey order-domain reduction and limit gating"
  expected_skill: "flight-test-operations/flutter/flight-vibration-survey"
Task ids: w33-flight-vibration-survey-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce an in-flight vibration
survey:" and include the outputs in the Claim. First tag:
flight-vibration-survey. Additional tags ONLY: track-and-balance,
order-analysis, per-rev-amplitude, synchronous-dft, vibration-limit,
rotor-balance-survey. NEVER single generic words (vibration, survey,
order, rotor, amplitude, rms, flight test). 50-150 words, <=1000
chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): buffet onset, RMS rise,
Mach pull up (buffet-boundary-testing); ground vibration, modal,
suspended structure (ground-vibration-testing); limit cycle, sustained
oscillation (limit-cycle-oscillation); loop margin, structural
coupling (structural-coupling-test); hover power, level flight power
(rotorcraft performance flight test leaves). The tokens "track and
balance", "per-rev order", "vibration survey", "1P trim" are this
leaf's own.

Tags: [flight-vibration-survey, track-and-balance, order-analysis,
per-rev-amplitude, synchronous-dft, vibration-limit,
rotor-balance-survey]

Sibling-citation lines for Related leaves:
flight-test-operations/flutter/ground-vibration-testing (ground modal
sibling; this leaf is the in-flight survey),
flight-test-operations/performance/rotorcraft-performance-flight-test,
flight-test-operations/envelope/buffet-boundary-testing.

Ledger Standard: far-29.
