---
name: e2001-multipactor-test-sequence
description: "Use when validate the scattering-parameters of an article installed at the multipactor test site under ECSS-E-ST-20-01C clause 8.4, before any radio-frequency drive is raised: check the frequency-grid covers the declared band with enough points, convert every measured reflection-coefficient and transmission-coefficient into return-loss, voltage-standing-wave-ratio and insertion-loss, confirm each point stays passive, and compare each against the component-level reference sweep inside a decibel tolerance so a mis-mated waveguide-flange, a shifted mounting or a damaged interface is caught before the run rather than blamed on the article afterwards. Trigger: ecss, e-st-20-01c, scattering-parameters, pre-run-sweep, return-loss, insertion-loss, voltage-standing-wave-ratio, reflection-coefficient, frequency-grid-coverage, multipactor-test-sequence."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multipactor-test-sequence, scattering-parameters, pre-run-sweep, return-loss, insertion-loss, frequency-grid-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor -- Pre-Run Scattering-Parameter Sweep (space-systems/ecss/e2001-multipactor-test-sequence)

Use when the task is the gate that ECSS-E-ST-20-01C clause 8.4 places in front
of a multipactor run: with the article already mounted in the bed and the drive
still low, sweep its scattering-parameters at the test site, and compare them
against the reference sweep taken at component level before the article ever
left its own bench.

## Domain quick reference

- The pre-run sweep is an installation check, not a performance check. The
  component was already characterized; what is unknown at this point is whether
  mounting it in the bed reproduced that state. A mis-mated waveguide-flange, a
  partly engaged coaxial interface, a rotated bend, a pinched gasket or a
  cracked window all show up as a shifted reflection-coefficient long before
  they show up as an anomalous discharge.
- Two magnitudes carry the check. The reflection-coefficient at the input maps
  to return-loss (minus twenty times the base-ten logarithm of the magnitude)
  and to voltage-standing-wave-ratio (one plus the magnitude over one minus
  it). The transmission-coefficient maps to insertion-loss on the same
  logarithmic form. A perfectly matched port gives an unbounded return-loss and
  a unity standing-wave-ratio; a fully reflecting port gives zero return-loss
  and an unbounded standing-wave-ratio.
- Both magnitudes belong to the closed interval from zero to one for a passive
  article, and their squares are fractions of incident power, so their sum
  cannot exceed unity. A sum above unity means the instrument is uncalibrated
  or the port assignment is wrong, not that the article generates energy; an
  exactly lossless article sums to unity and must not be rejected because the
  binary representation of the sum of two squares lands on the last bit above.
- The comparison against the reference sweep is per frequency point and in
  decibels, because both quantities are ratios. A deviation inside the stated
  tolerance is the installation reproducing the bench; outside it, the sign
  says which way: more reflection than the reference points at the interface,
  less transmission than the reference points at a lossy or partly open joint.
- The frequency-grid itself is part of the gate. A grid that stops short of the
  declared band edges, or that is too sparse to resolve a narrow resonance,
  can return a clean verdict over a band it never actually visited.

## Workflow

1. Check the frequency-grid: strictly increasing, no repeated points, covering
   the declared band from its lower to its upper edge, and carrying at least
   the minimum number of points the procedure requires. Reject an unordered or
   duplicated grid outright; report short coverage or a sparse grid as a
   finding.
2. For each point, check the measured reflection-coefficient and
   transmission-coefficient magnitudes lie between zero and one inclusive, then
   check passivity: the sum of their squares at or below unity, absorbing
   representation error at the lossless edge rather than widening the limit.
3. Convert each point: return-loss and voltage-standing-wave-ratio from the
   reflection-coefficient, insertion-loss from the transmission-coefficient.
   A zero-magnitude reflection is an unbounded return-loss, not an error.
4. Compare each point against its reference: deviation in return-loss and in
   insertion-loss against the per-quantity tolerance, keeping the sign so the
   direction of the discrepancy is reported.
5. Screen against the absolute limits the test specification carries: a
   minimum return-loss and a maximum insertion-loss over the band. A point
   sitting exactly on a limit is compliant.
6. Aggregate per point and over the band. The run is cleared to start only when
   the grid, the passivity, the reference comparison and the absolute limits
   are all clean; otherwise report the worst point so the interface is remade
   before the drive is raised.

## Pitfalls

- Sweeping at the bench and treating that as the pre-run sweep -- the whole
  point of clause 8.4 is the state of the article as installed, with the bed
  cabling, the feed-throughs and the mounting in the path.
- Rejecting an ideal lossless point because the squares of its two magnitudes
  sum a few bits above unity -- that is binary representation error, and
  widening the passivity limit to hide it would also pass a genuinely
  non-passive measurement.
- Comparing return-loss magnitudes without their sign convention -- return-loss
  is a positive number that grows as the match improves, so a larger number is
  better and a naive worst-case comparison inverts the verdict.
- Declaring coverage from the number of points alone -- a dense grid packed
  into part of the band leaves the edges unvisited, which is where flange and
  interface effects usually appear first.
- Reading a single clean point as a clean band -- the interface defects this
  gate exists to catch are frequently narrow-band, and one point can sit
  between two resonances.

## Behavior contract (gate 3)

The frequency-grid, magnitude-range, passivity, return-loss,
standing-wave-ratio, insertion-loss, reference-comparison and absolute-limit
logic is exercised by the gate 3 contract test:
scripts/test_e2001_multipactor_test_sequence.py against
scripts/e2001_multipactor_test_sequence_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2001_multipactor_test_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
