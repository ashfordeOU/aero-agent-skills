---
name: e2001-reduced-carrier-equivalent-power-test
description: "Use when size a reduced-carrier multipaction verification in which fewer carriers, each raised to an equivalent drive, stand in for the full operational spectrum under ECSS-E-ST-20-01C clause 6.4.3.3: divide the square-root-power sum across the retained carriers so peak-envelope-voltage is preserved, hold the operational carrier-spacing so the envelope-repetition-period is unchanged, solve the main-lobe dwell above the multipaction-onset voltage, count the electron-gap-crossings that dwell supports, and refuse a reduction leaving fewer crossings than the operational spectrum or fewer than the avalanche-growth minimum. Trigger: ecss, e-st-20-01c, multipaction, reduced-carrier-verification, equivalent-drive-level, peak-envelope-voltage, envelope-dwell-time, electron-gap-crossings, carrier-spacing-retention."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-reduced-carrier-equivalent-power-test, multipaction, reduced-carrier-verification, equivalent-drive-level, envelope-dwell-time, electron-gap-crossings]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Reduced-Carrier Equivalent-Drive Verification (space-systems/ecss/e2001-reduced-carrier-equivalent-power-test)

Use when the task is the multi-frequency multipaction verification of
ECSS-E-ST-20-01C clause 6.4.3.3 -- standing in for the operational
carrier spectrum with a smaller retained set, each retained carrier
raised so the set still reaches the operational peak-envelope-voltage,
and proving the retained envelope dwells above the multipaction onset
long enough for a discharge to actually develop.

## Domain quick reference

- Peak envelope voltage scales with the sum of the individual carrier
  voltages, so a set of M retained carriers reproduces the operational
  peak when each carries `P_reduced = (sum_i sqrt(P_i) / M)**2`. The
  retained set then draws `1/M` of the average power a single
  equivalent continuous-wave carrier would demand, which is exactly why
  this route survives bench limits that defeat clause 6.4.3.2.
- Matching the peak is necessary, not sufficient. The envelope of M
  equal carriers spaced by `df` follows the Dirichlet kernel
  `|sin(M*pi*df*t) / (M*sin(pi*df*t))|`: it touches the peak only
  briefly and repeats every `1/df`. What the gap experiences is the
  time spent above the multipaction onset voltage, not the peak value.
- The onset sits below the peak by the verification margin. A power
  margin of m decibels puts the onset at `10**(-m/20)` of the peak in
  voltage, so a 6 dB campaign solves the dwell at roughly half the peak
  amplitude and a 0 dB campaign degenerates to the peak instant itself.
- Electron avalanche growth needs roughly twenty transits of the gap
  while the envelope stays above onset. Transit time at resonant order
  n and frequency f is `n / (2f)`, taken at the highest operational
  carrier frequency because that is the shortest transit in the set.
- Fewer carriers at unchanged spacing widen the main lobe, so the
  retained configuration is normally more severe on dwell than the
  operational one -- that is the physical licence for the reduction.
  Widening the spacing while reducing the count reverses it silently,
  and a retained set with fewer crossings than the operational spectrum
  is an under-test dressed as an equivalent one.
- Reducing all the way to one retained carrier is not this clause: a
  single carrier is continuous-wave, its dwell is unbounded, and the
  governing procedure becomes clause 6.4.3.2.

## Workflow

1. Validate the operational carrier set and confirm it is uniformly
   spaced; derive the operational spacing and the envelope repetition
   period from it.
2. Check the proposed retained count is a positive integer strictly
   below the operational count -- a count that does not reduce anything
   is not a clause 6.4.3.3 case, and a count of one belongs to the
   single-carrier clause.
3. Sum the square-roots of the operational carrier powers, divide by
   the retained count and square the result to get the per-carrier
   drive; confirm the retained carriers sum back to the operational
   peak-envelope-voltage within a named tolerance.
4. Convert the verification margin into an onset-to-peak voltage ratio,
   then solve the envelope main lobe for the dwell above that ratio,
   for both the operational and the retained configurations, using the
   spacing each one actually uses.
5. Divide each dwell by the electron transit time to get the
   gap-crossing count the configuration supports.
6. Flag a retained configuration whose crossing count falls below the
   avalanche-growth minimum, or below what the operational spectrum
   itself supports; flag a per-carrier drive the bench cannot deliver.
7. Categorize the outcome: acceptable when nothing is flagged, out of
   scope when the reduction collapses to a single carrier, otherwise
   not acceptable -- re-run with a larger retained count or the
   operational spacing restored.

## Pitfalls

- Dividing power rather than voltage across the retained carriers.
  Giving each retained carrier `sum(P_i)/M` matches average power and
  lands the peak-envelope-voltage far below the operational one, so the
  article is verified under a peak it never sees in flight.
- Re-spacing the retained carriers for bench convenience. Spacing sets
  the envelope repetition period and the main-lobe width; a wider
  spacing shortens the dwell at the same peak and quietly converts a
  conservative reduction into an under-test.
- Reading a matched peak as a passed criterion. Peak amplitude and
  dwell are independent conditions; a retained set can reach the exact
  operational peak and still starve the avalanche of the transits it
  needs.
- Solving the dwell at the peak amplitude instead of at the onset. The
  onset follows the verification margin, and using the peak collapses
  the dwell toward zero for every configuration, failing reductions
  that are physically sound.
- Comparing crossing counts computed at different resonant orders or
  different carrier frequencies. The comparison between operational and
  retained configurations only means something when both are evaluated
  against the same governing transit time.

## Behavior contract (gate 3)

The carrier-set validation, reduction-count checking, equivalent-drive
derivation, envelope main-lobe dwell solution and gap-crossing
comparison logic is exercised by the gate 3 contract test:
scripts/test_e2001_reduced_carrier_equivalent_power_test.py against
scripts/e2001_reduced_carrier_equivalent_power_test_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_reduced_carrier_equivalent_power_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
