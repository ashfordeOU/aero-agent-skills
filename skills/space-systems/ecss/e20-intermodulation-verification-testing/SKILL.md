---
name: e20-intermodulation-verification-testing
description: "Use when verify by measurement that the intermodulation products of a unit stay inside the agreed acceptance-level under ECSS-E-ST-20C clause 7.4.4: take the lowest critical intermodulation-order as the product to measure, check the two-carrier-test-configuration (carrier-power, carrier frequencies, measurement-bandwidth, dwell) against the flight carrier-plan, confirm the measurement-system residual sits the required headroom below the acceptance-level so a reading means something, add the measurement-uncertainty to every reading, and categorize each run as pass, fail, uncertainty-limited or instrument-limited. Trigger: ecss, e-st-20-electrical-scope, passive-intermodulation, two-carrier-measurement, measurement-system-residual, lowest-intermodulation-order, pim-acceptance-level, measurement-uncertainty."
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
  tags: [ecss, e-st-20-electrical-scope, e20-intermodulation-verification-testing, passive-intermodulation, two-carrier-measurement, measurement-system-residual, lowest-intermodulation-order, pim-acceptance-level, measurement-uncertainty]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Intermodulation Verification Testing (space-systems/ecss/e20-intermodulation-verification-testing)

Use when the task is the ECSS-E-ST-20C clause 7.4.4 activity of proving by
measurement that the intermodulation products of a unit stay inside the
acceptance-level agreed with the customer -- measuring at the lowest
critical intermodulation-order, on a bench whose own residual is far enough
below the limit to make the reading mean something, with the
measurement-uncertainty carried into the verdict rather than dropped.

## Domain quick reference

- The product to measure is the lowest critical intermodulation-order
  identified for the victim band, because product amplitude falls steeply
  with order: a unit that passes at the lowest order passes at the higher
  ones, and a unit measured only at a high order has not been verified at
  all. Measuring an order that was never identified as critical proves
  nothing about the band that matters.
- The two-carrier-test-configuration must bracket flight. Per-carrier-power
  at or above the flight per-carrier-power, the same carrier count, carrier
  frequencies placed so the product under test lands in the victim band,
  and a measurement-bandwidth no wider than the victim band -- a wider
  resolution admits noise that is not the product and flatters or spoils the
  reading depending on which way it moves.
- Every passive-intermodulation bench generates products of its own. The
  measurement-system residual must sit a declared headroom below the
  acceptance-level; when it does not, no reading from that bench can
  demonstrate compliance and the run is instrument-limited, which is not a
  fail of the unit but is also not a pass.
- A reading is a level plus an uncertainty. The verdict is taken on the
  worst-case level (reading plus uncertainty): at or below the
  acceptance-level it is a pass; a reading below the limit whose worst case
  is above it is uncertainty-limited and needs a better bench or an agreed
  uncertainty allocation, not a rounded-down number.
- A reading at or under the bench residual is a residual reading: it bounds
  the unit at the residual, and it is a pass only when the residual itself
  clears the acceptance-level with the required headroom.
- Several products can fall in one victim band and they add as powers, so a
  campaign verdict for that band is taken on the power-sum of the measured
  products, not on the best single run.
- Exact equality at the limit is compliance: the comparison absorbs float
  representation error rather than moving the limit.

## Workflow

1. Take the critical-order set for the victim band and select the lowest
   order as the order to measure. Reject an empty set, a non-integer order
   and an order below three.
2. Validate the two-carrier-test-configuration: carrier count, per-carrier
   power, carrier frequencies, measurement-bandwidth, dwell time and the
   declared measurement-system residual and uncertainty. Reject a
   non-positive bandwidth, a negative dwell and a non-finite level.
3. Compare the configuration against the flight carrier-plan: flag a test
   per-carrier-power below flight, a carrier count below flight, a
   measurement-bandwidth wider than the victim band and a measured order
   that is not the lowest critical order.
4. Check bench capability: acceptance-level minus residual must be at least
   the required headroom. Below it, every run on that bench is
   instrument-limited.
5. Categorize each run: instrument-limited when the bench lacks headroom or
   the reading sits at the residual without the residual itself clearing the
   limit; pass when the reading plus its uncertainty is at or below the
   acceptance-level; uncertainty-limited when the bare reading clears but
   the worst case does not; fail otherwise.
6. Power-sum the per-run readings in a victim band and compare the aggregate
   against the acceptance-level, keeping the uncertainty in the aggregate.
7. Issue the campaign verdict: fail if any run fails or the aggregate
   exceeds the limit; inconclusive if any run is uncertainty-limited or
   instrument-limited, or the lowest critical order was never measured;
   pass only when every run passes and the configuration findings are empty.

## Pitfalls

- Measuring a convenient high order (or the bench's habitual order) instead
  of the lowest critical one, then reporting the clean result as verification
  of the band.
- Reading a bench residual as a unit level: if the residual is not the
  declared headroom below the acceptance-level, the number on the screen is
  the bench, and no verdict about the unit can be drawn from it.
- Dropping the measurement-uncertainty because the reading looks comfortable
  -- a reading 1 dB under the limit with a 2 dB uncertainty is not a pass,
  it is an uncertainty-limited result awaiting a decision.
- Testing below the flight per-carrier-power and extrapolating: product
  amplitude rises faster than the carriers, so a low-power run under-reports
  the flight level and the extrapolation is not a demonstration.
- Widening the measurement-bandwidth to find the product faster and leaving
  it wide for the graded run, so the reading contains noise that is not the
  product.
- Taking the best single run as the band verdict when several products land
  in the band -- they add as powers, and two equal products sit 3 dB above
  either one alone.
- Reporting an instrument-limited or uncertainty-limited campaign as a pass
  because nothing actually failed; neither outcome demonstrates compliance.

## Behavior contract (gate 3)

The order selection, the configuration-versus-flight comparison, the bench
headroom check, the uncertainty-carrying run categorization and the
power-summed campaign verdict are exercised by the gate 3 contract test:
`scripts/test_e20_intermodulation_verification_testing.py` against
`scripts/e20_intermodulation_verification_testing_logic.py`
(stdlib unittest, offline, deterministic). Run:
python3 scripts/test_e20_intermodulation_verification_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
