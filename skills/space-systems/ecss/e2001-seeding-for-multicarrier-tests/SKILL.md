---
name: e2001-seeding-for-multicarrier-tests
description: "Use when determine whether a multiple-carrier multipactor-test needs an artificial electron-seed-source under ECSS-E-ST-20-01C clause 6.5.4: build the coherent carrier-envelope from the carrier set, measure the fraction of each beat-period the envelope holds above the predicted breakdown-threshold, convert that above-threshold dwell and the gap volume into the free-electron population natural-background-ionisation alone supplies, decide against the required seeding-confidence whether that population leaves a false-pass risk, size the seed-electron-generation-rate that closes the shortfall, and reject a seeding-technique whose delivered rate or RF-perturbation-current breaks the test-bed limits. Trigger: ecss, e-st-20-01c, multicarrier-seeding, electron-seed-source, carrier-envelope-dwell, natural-background-ionisation, seeding-confidence, false-pass-risk, beat-period-dwell."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-seeding-for-multicarrier-tests, multicarrier-seeding, electron-seed-source, carrier-envelope-dwell, natural-background-ionisation, seeding-confidence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor Design and Test — Seeding for Multiple-Carrier Tests (space-systems/ecss/e2001-seeding-for-multicarrier-tests)

Use when the task is the electron-seeding decision of ECSS-E-ST-20-01C
clause 6.5.4 -- establishing that a multipactor run driven by several
simultaneous carriers carries a free electron in the critical gap at the
instants the carrier-envelope rises above the breakdown-threshold, and
sizing the artificial seed-source that makes that true.

## Domain quick reference

- A multiple-carrier drive is not a steady excitation. The carriers beat
  against each other, so the instantaneous envelope sweeps from a deep
  null up to a coherent peak whose value is the square of the summed
  carrier voltage-amplitudes -- far above the sum of the individual
  carrier levels. The envelope pattern repeats once per beat-period,
  the reciprocal of the carrier spacing.
- Breakdown is only possible while the envelope sits above the
  predicted threshold, and that window is a small fraction of the
  beat-period. The physically meaningful quantity is therefore the
  above-threshold dwell per beat-period, not the average drive level.
- A discharge needs a starting electron inside the gap during that
  dwell. With no artificial source the only supply is
  natural-background-ionisation -- cosmic-ray secondaries, residual
  activity, stray field-emission -- at a rate of order one electron per
  cubic centimetre per second. Multiplying that rate by the gap volume
  and by a dwell measured in microseconds gives an expected electron
  count many orders below unity.
- Presence is a Poisson question: with an expected count of lambda the
  probability that at least one electron is available is
  1 - exp(-lambda). Turning that round, a seeding-confidence of 0,95
  demands lambda of about 3. A run that ends quiet with lambda far
  below that has demonstrated nothing -- it is a false-pass, not a pass.
- Closing the shortfall is a rate problem: the seed-source must deliver
  the deficit in expected electrons divided by the available dwell.
  Three techniques are recognised -- a beta-emitting radioactive
  source, ultraviolet-illumination driving photoemission off a gap
  surface, and an electron-gun. Each has a deliverable rate ceiling and
  each perturbs the item under test through the current it injects, so
  a technique is admissible only when it both reaches the required rate
  and stays under the test-bed perturbation-current limit.

## Workflow

1. Validate the carrier set (every carrier level strictly positive, the
   carrier spacing strictly positive) and compute the coherent peak of
   the envelope and the beat-period.
2. Sample the envelope deterministically across one beat-period and
   measure the fraction of that period spent above the predicted
   breakdown-threshold; multiply by the beat-period to get the
   above-threshold dwell. A configuration whose peak never reaches the
   threshold is flagged -- it stresses nothing and cannot serve as a
   verification point.
3. Convert the dwell into the natural expected electron count from the
   gap volume and the background ionisation rate, and report the
   corresponding presence probability.
4. Turn the required seeding-confidence into the expected electron
   count it implies, and compare. If the natural count already meets it
   no artificial source is needed; otherwise seeding is mandatory.
5. Size the shortfall as a required seed-electron-generation-rate
   (deficit in expected electrons divided by the dwell).
6. Grade the proposed technique: unknown technique rejected, delivered
   rate below the requirement flagged, delivered rate above the
   technique's physical ceiling flagged, injected perturbation-current
   above the test-bed limit flagged.
7. The run is seeding-compliant only when the finding list is empty.

## Pitfalls

- Sizing the seeding from the average multi-carrier level instead of
  the envelope. The average never triggers anything; the coherent peak
  and its short dwell govern both the breakdown risk and the electron
  supply the source has to deliver.
- Treating a quiet multiple-carrier run as a pass without checking the
  electron availability. Without a seed-source the expected electron
  count in a microsecond-scale dwell is minuscule, so silence is the
  expected outcome whether or not the hardware is multipactor-free.
- Reusing a single-carrier seeding budget unchanged. Continuous drive
  offers the whole run as the capture window, while a multiple-carrier
  drive offers only the above-threshold slice of each beat-period, so
  the rate demanded of the source is far higher for the same
  confidence.
- Choosing the source on rate alone. A source that meets the rate but
  injects more current than the test-bed tolerates changes the very
  discharge being looked for, and its result is not usable evidence.
- Reading a zero above-threshold dwell as "no seeding needed". It means
  the test point never reaches breakdown conditions at all, which is a
  finding against the test design, not a seeding conclusion.

## Behavior contract (gate 3)

The envelope, dwell, natural-population, seeding-decision, rate-sizing
and technique-grading logic is exercised by the gate 3 contract test:
scripts/test_e2001_seeding_for_multicarrier_tests.py against
scripts/e2001_seeding_for_multicarrier_tests_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_seeding_for_multicarrier_tests.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
