---
name: e2001-level-two-multicarrier-method
description: "Use when determine the level-two multicarrier multipaction result of ECSS-E-ST-20-01C clause 5.3.2.3.4 for a radio-frequency unit: rebuild the carrier-beat envelope of a uniformly-spaced carrier comb, derive the electron gap-crossing-time and the sustaining pulse-width that the twenty-crossing rule demands, sweep every pulse-width in the pulsed susceptibility data for the envelope level held that long, drop a pulse-width the beat envelope cannot hold and one shorter than the sustaining pulse-width, then report the worst-case pulse-width, the minimum breakdown-level it governs, and the multipaction-margin in decibel against the required multipaction-margin. Trigger: ecss, e-st-20-electrical-scope, multicarrier-envelope-sweep, twenty-gap-crossing-rule, worst-case-pulse-width, minimum-breakdown-level, carrier-beat-envelope, pulsed-susceptibility-data, multipaction-margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-electrical-scope, e2001-level-two-multicarrier-method, multicarrier-envelope-sweep, twenty-gap-crossing-rule, worst-case-pulse-width, minimum-breakdown-level, carrier-beat-envelope, pulsed-susceptibility-data]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Level-Two Multicarrier Method (space-systems/ecss/e2001-level-two-multicarrier-method)

Use when the task is the level-two multicarrier method of
ECSS-E-ST-20-01C clause 5.3.2.3.4 -- the envelope sweep that replaces
the level-one peak-power assumption with a time-resolved check, walking
the candidate pulse-widths of the carrier-beat envelope to find the
worst-case pulse-width and the minimum breakdown-level that width
governs.

## Domain quick reference

- A uniformly-spaced, equal-amplitude carrier comb beats into a
  periodic envelope. The carrier voltages align once per beat period
  (the reciprocal of the carrier spacing), so the envelope peak reaches
  N-squared times the power of one carrier while the mean total power
  is only N times it. Level one stops at that peak and treats it as a
  continuous-wave level; level two asks how long the envelope actually
  stays there.
- A multipaction avalanche is not instantaneous. Free electrons have to
  complete a minimum number of gap crossings before the electron
  population grows faster than it is lost, and one crossing of a
  resonant parallel-plate gap takes half an RF period. Twenty crossings
  is the customary sustaining criterion, so the sustaining pulse-width
  is twenty half-periods of the centre frequency. An envelope excursion
  shorter than that deposits energy but never establishes a discharge.
- The envelope main lobe has a finite base width, equal to twice the
  reciprocal of the product of carrier count and carrier spacing. No
  pulse-width beyond that base width exists in the envelope at any
  positive level, so a susceptibility data point taken at a longer
  pulse-width has no counterpart in this signal and must be dropped
  rather than applied.
- The pulsed susceptibility data attaches a single-carrier
  breakdown-level to each pulse-width; short pulses break down only at
  markedly higher levels. Because that data varies with pulse-width
  while the envelope level held falls with pulse-width, the governing
  pair is found by search, not by inspection -- that search is the
  envelope sweep.
- The reported multipaction-margin is the ratio, in decibel, of the
  governing breakdown-level to the envelope power actually held for the
  worst-case pulse-width. The minimum breakdown-level is that same
  ratio applied to the envelope peak: the lowest peak envelope power at
  which the discharge starts.

## Workflow

1. Validate the carrier set: at least two carriers, distinct and
   uniformly spaced within tolerance, each with a positive power.
   Reject a non-uniform comb before any envelope is built, because the
   closed-form beat envelope does not apply to it.
2. Derive the comb geometry: carrier spacing, beat period, centre
   frequency, peak envelope power from the root-sum of carrier
   voltages, and the main-lobe base width.
3. Derive the timing criterion: electron gap-crossing-time at the
   centre frequency, then the sustaining pulse-width for the adopted
   crossing count (twenty unless a validated technique justifies
   another).
4. Normalise the pulsed susceptibility data: positive pulse-widths,
   positive breakdown-levels, no duplicated width, ordered by width.
5. Sweep every tabulated pulse-width. For each, compute the envelope
   power ratio held for that duration, mark the row unreachable when
   the width meets or exceeds the main-lobe base width, mark it
   non-sustaining when the width is shorter than the sustaining
   pulse-width, and compute the headroom ratio of its breakdown-level
   over the envelope power held.
6. Select the governing row: the reachable, sustaining row with the
   least headroom. If no row is both reachable and sustaining, the
   envelope cannot establish a discharge at any tabulated width and the
   case closes without a numeric margin -- record why.
7. Report the worst-case pulse-width, its breakdown-level, the minimum
   peak envelope power at which breakdown starts, and the
   multipaction-margin in decibel compared against the required
   multipaction-margin.

## Pitfalls

- Carrying the level-one peak straight into level two and calling it a
  result -- the whole point of clause 5.3.2.3.4 is that the peak is
  held for a vanishing time, and a sweep that never applies the
  sustaining pulse-width has simply repeated level one at greater cost.
- Reading the susceptibility data at a pulse-width the envelope cannot
  produce. Beyond the main-lobe base width the envelope level is zero,
  so the headroom is unbounded; treating that row as governing hides
  the real worst case behind a meaningless pass.
- Applying a susceptibility row measured on pulses shorter than the
  sustaining pulse-width. Those points are real measurements but they
  describe an excursion that cannot establish a discharge, so using one
  as the governing breakdown-level understates the margin and drives
  unnecessary redesign.
- Sweeping only the widest or only the narrowest tabulated width. The
  breakdown-level rises with shortening pulses while the envelope level
  held rises too; the minimum of their ratio can sit anywhere in the
  table and only a full sweep finds it.
- Comparing the margin against the requirement with a bare arithmetic
  test. The margin is a difference of logarithms and an exactly
  compliant case can land a few units in the last place on the wrong
  side, so the comparison absorbs representation error while the
  engineering limit stays untouched.

## Behavior contract (gate 3)

The comb validation, envelope reconstruction, sustaining pulse-width
criterion, pulse-width sweep and worst-case selection are exercised by
the gate 3 contract test:
scripts/test_e2001_level_two_multicarrier_method.py against
scripts/e2001_level_two_multicarrier_method_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_level_two_multicarrier_method.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
