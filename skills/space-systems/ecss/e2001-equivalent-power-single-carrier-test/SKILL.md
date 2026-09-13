---
name: e2001-equivalent-power-single-carrier-test
description: "Use when verify that a multi-carrier multipaction qualification of an RF component may be run with one carrier raised to an equivalent-power level under ECSS-E-ST-20-01C clause 6.4.3.2: sum the square-roots of the operational carrier powers to obtain the peak-envelope-voltage, square that sum to derive the equivalent continuous-wave drive, apply the multipaction-verification margin, confirm the amplifier-chain and the component peak-power-rating can deliver that drive, and quantify the thermal-over-test-ratio the substitution imposes, because an equivalent continuous-wave drive reproduces peak-envelope-voltage exactly while dissipating many times the operational average. Trigger: ecss, e-st-20-01c, multipaction, multi-carrier-verification, equivalent-power-level, peak-envelope-voltage, single-carrier-substitution, thermal-over-test-ratio, electron-gap-crossings."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-equivalent-power-single-carrier-test, multipaction, multi-carrier-verification, equivalent-power-level, peak-envelope-voltage, single-carrier-substitution]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Equivalent-Power Single-Carrier Verification (space-systems/ecss/e2001-equivalent-power-single-carrier-test)

Use when the task is the multi-frequency multipaction verification of
ECSS-E-ST-20-01C clause 6.4.3.2 -- replacing the full operational
carrier spectrum with one carrier raised to an equivalent-power level,
deriving that level from the peak-envelope-voltage, and establishing
whether the drive chain and the article under verification can carry it.

## Domain quick reference

- Multipaction onset is set by the peak voltage across the critical
  gap, never by the average power flowing through the component. For a
  set of carriers sharing one gap the envelope voltage is highest at
  the instant every carrier is momentarily in phase, so the peak
  envelope voltage scales with the sum of the individual carrier
  voltages, not with the sum of their powers.
- Because carrier voltage scales with the square-root of carrier power,
  the equivalent single-carrier drive is the square of the
  square-root-power sum: `P_equiv = (sum_i sqrt(P_i))**2`. For a set of
  N equal carriers of power P this is `N**2 * P`, which is N times the
  operational average power. The substitution is exact on
  peak-envelope-voltage and conservative on onset.
- A continuous-wave drive never leaves the onset region, so the
  electron-avalanche growth criterion (roughly twenty gap transits
  before a discharge is observable) is satisfied without a dwell
  calculation. That is the principal advantage of this substitution
  over the reduced-carrier route of clause 6.4.3.3, where the envelope
  peak is transient and the dwell has to be earned.
- The price is dissipation. The equivalent drive deposits the full
  `N**2 * P` continuously, while flight operation deposits only
  `N * P`. The over-test factor equals the carrier count for an
  equal-power set and has to be budgeted against the article's thermal
  design, the amplifier-chain capability, and the component
  peak-power-rating, any of which can make the substitution
  undeliverable or damaging.
- Electron transit time at resonant order n and frequency f is
  `n / (2f)`; it is recorded from the highest operational carrier
  frequency because that is the shortest transit in the set and the
  governing case for growth.

## Workflow

1. Validate the operational carrier set: a non-empty list of uniquely
   identified carriers, each with a finite positive power and a finite
   positive frequency. Reject a malformed set before any derivation --
   a silently dropped carrier lowers the derived drive and voids the
   verification.
2. Sum the square-roots of the carrier powers to obtain the quantity
   proportional to peak-envelope-voltage, then square that sum to get
   the equivalent continuous-wave drive level.
3. Apply the required multipaction-verification margin in decibels to
   the equivalent level; this is the drive the bench must actually
   deliver.
4. Compare the margined drive against the amplifier-chain capability
   and against the component peak-power-rating. Absorb
   representation error at an exact boundary with a relative tolerance
   -- a square-root sum squared back up lands a few units in the last
   place above an equal limit -- but never widen the limit itself.
5. Divide the equivalent level by the operational average power to get
   the over-test factor, and compare it against whatever
   over-dissipation the thermal design accepts.
6. Categorize the outcome: acceptable when nothing is flagged,
   conditional when only the over-dissipation allowance is exceeded
   (the substitution stands but needs a thermal mitigation such as a
   duty-cycled application or an auxiliary cooling case), and not
   acceptable when the drive cannot be delivered or would over-stress
   the article -- in which case the reduced-carrier route of clause
   6.4.3.3 is the fallback.

## Pitfalls

- Summing carrier powers instead of carrier voltages. Adding powers
  gives `N * P` and understates the equivalent drive by a factor of N;
  the article is then verified far below its real peak-envelope-voltage
  and passes a verification it should have failed.
- Reading the substitution as thermally representative. It is a
  voltage-equivalent drive, not a dissipation-equivalent one; treating
  a pass as evidence of thermal adequacy confuses two unrelated cases
  and leaves the operational thermal case unverified.
- Deriving the drive without checking the bench. An equivalent level
  that the amplifier-chain cannot reach yields a quiet under-drive, and
  one above the component peak-power-rating damages the article during
  the very run meant to qualify it.
- Widening the drive limit to clear a boundary comparison. When a
  square-root sum squared exceeds an equal limit by a few units in the
  last place the excess is arithmetic, not physical; absorb it in the
  comparison with a named tolerance and leave the engineering limit
  where the design put it.
- Assuming the highest-power carrier governs. The peak-envelope-voltage
  is a coherent sum over every carrier, so a set of many small carriers
  can demand a higher equivalent drive than a set of few large ones at
  the same total average power.

## Behavior contract (gate 3)

The carrier-set validation, equivalent-drive derivation, margin
application, drive-capability and over-dissipation logic is exercised by
the gate 3 contract test:
scripts/test_e2001_equivalent_power_single_carrier_test.py against
scripts/e2001_equivalent_power_single_carrier_test_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_equivalent_power_single_carrier_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
