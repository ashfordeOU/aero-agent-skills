---
name: e2007-measurement-chain-integrity-check
description: "Validate the whole receiving chain of an emission measurement before its first point is recorded, anchored at ECSS-E-ST-20-07C clause 5.2.11.2: sum the transducer, cable, attenuator, amplifier and receiver contributions into an end-to-end gain, predict what a reference signal of known level should indicate, hold the deviation to its decibel allowance, and refuse an injection that bypasses part of the chain, that was performed after the run began or too long before it, or that is one record reused across several runs. Use when preparing, auditing or accepting a radiated or conducted emission run. Trigger: ecss, e-st-20-07c, measurement-chain-integrity-check, end-to-end-chain-gain, reference-signal-injection, emission-run-precheck, bypassed-chain-element, chain-check-staleness."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-07c, e2007-measurement-chain-integrity-check, end-to-end-chain-gain, reference-signal-injection, emission-run-precheck, bypassed-chain-element, chain-check-staleness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Measurement Chain Integrity Check (space-systems/ecss/e2007-measurement-chain-integrity-check)

Use when the task is the chain-check rule of ECSS-E-ST-20-07C clause
5.2.11.2 -- every emission measurement opens with a verification that
the complete receiving chain, from the sensing transducer through to the
indicating receiver, still behaves as its calibration says it does.

## Domain quick reference

- The chain is an ordered path, not a bag of instruments: a transducer
  at the head, then the cables, attenuators, amplifiers and filters
  between, and the receiver at the tail. Each element carries its
  contribution in decibels, a loss entering as a negative gain, and the
  end-to-end gain is their sum.
- The check is a prediction compared with an indication. A reference
  signal of known level applied at the head should indicate at the
  receiver as that level plus the end-to-end gain; the deviation
  between prediction and indication is what the campaign's decibel
  allowance is held against.
- Where the reference is injected decides what the check covers.
  Injecting at the amplifier input proves the back end and leaves the
  transducer and the cable ahead of it unverified -- which is exactly
  the part of the chain most likely to have changed since the last run.
- The check belongs to the run. It has to precede the first measured
  point, and a check carried over from hours earlier proves only that
  the chain was intact then. One check record cannot cover two runs:
  the clause asks for a check at the beginning of each measurement, and
  a record appearing twice is a reused record, not two checks.
- Not every deviation is a chain defect, but every deviation is a stop:
  a connector backed off, an amplifier out of compression, a mis-set
  attenuator and a wrong transducer factor all land here, and the run
  cannot be graded until the source is known.
- A deviation that exactly meets the allowance meets it. The difference
  of two decibel quantities can land a few units in the last place
  outside an exactly met allowance; absorb that in the comparison, not
  by widening the allowance.

## Workflow

1. Normalize the chain head to tail. Reject a chain shorter than a
   transducer and a receiver, a head that is not the transducer, a tail
   that is not the receiver, a second transducer or an interior
   receiver, a duplicated element identifier, an unknown key and a
   non-finite gain.
2. Sum the element gains into the end-to-end gain of the chain.
3. For each run, read its check record: the time, the injected level,
   the indicated level and the injection point.
4. Predict the indication from the injected level and the chain gain,
   take the signed deviation, and hold it to the allowance in both
   directions.
5. List the elements ahead of the injection point; any that are listed
   were not exercised and the check is partial.
6. Compare the check time with the start of the run: it must precede it
   and must sit inside the staleness window.
7. Across the campaign, detect a check record shared by more than one
   run and report it against every run it was used for.
8. Aggregate: the conforming fraction of the runs and one finding per
   defect, accepting the campaign only when none remains.

## Pitfalls

- Injecting at the receiver or the amplifier input and reporting a
  chain check. The elements ahead of the injection are exactly the ones
  the check exists to exercise.
- Adding a cable loss as a positive number. Losses enter as negative
  gains, and the sign error moves the prediction by twice the loss,
  turning an intact chain into an apparent fault.
- Reusing one morning check for a day of runs. Each measurement begins
  with its own, and a shared record is indistinguishable in the data
  from a check that was never repeated.
- Accepting a check performed after the first point was recorded. It
  cannot tell anyone whether the points already taken are trustworthy.
- Treating a deviation inside the allowance as proof the chain is
  correct when part of it was bypassed; coverage and deviation are two
  separate findings and one does not answer the other.
- Widening the allowance to absorb a deviation that lands exactly on
  it. The representation error is handled inside the comparison; the
  allowance stays as the campaign declared it.

## Behavior contract (gate 3)

The chain normalization, end-to-end gain summation, prediction and
deviation, allowance comparison, injection-coverage analysis, check
timing and campaign aggregation are exercised by the gate 3 contract
test: scripts/test_e2007_measurement_chain_integrity_check.py against
scripts/e2007_measurement_chain_integrity_check_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_measurement_chain_integrity_check.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
