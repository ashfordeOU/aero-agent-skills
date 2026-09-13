---
name: e20-detailed-emc-verification-requirements
description: "Use when perform an electromagnetic compatibility verification run against the detailed requirement it references under ECSS-E-ST-20C clause 6.4.3: resolve that reference and flag a run citing a requirement the applicable set does not hold, compare the swept segments with the frequency range the procedure fixes and list the sub-bands nobody swept, hold the frequency step inside the share of the measurement-bandwidth allowed, divide each segment dwell over its frequency points and accumulate the sweep total against the minimum, keep the ambient-background the demanded separation below the limit-line, and settle every level as compliant, non-compliant or inconclusive once the measurement-uncertainty is applied. Trigger: ecss, e-st-20-electrical-scope, detailed-emc-verification-requirements, referenced-verification-procedure, swept-frequency-coverage-gap, measurement-bandwidth-step-fraction, sweep-dwell-accumulation, ambient-background-separation, measurement-uncertainty-disposition."
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
  tags: [ecss, e-st-20-electrical-scope, e20-detailed-emc-verification-requirements, detailed-emc-verification-requirements, referenced-verification-procedure, swept-frequency-coverage-gap, measurement-bandwidth-step-fraction, measurement-uncertainty-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Detailed EMC Verification Requirements (space-systems/ecss/e20-detailed-emc-verification-requirements)

Use when the task is the clause 6.4.3 execution step of ECSS-E-ST-20C --
running a compatibility verification the way the detailed requirement it
references demands, and deciding whether what was run is actually the
verification that requirement asks for.

## Domain quick reference

- A verification run is graded against the detailed requirement it
  cites, not against itself. That requirement fixes six things the run
  has to honour: the frequency range to be swept, the measurement
  bandwidth and the share of it a frequency step may take, the dwell
  each frequency point owes, the detector the level is read with, the
  limit the level is held against, and how far the ambient background
  has to sit below that limit. A run reported as a single number with
  none of these attached cannot be graded at all.
- The reference itself is the first thing to resolve. A run citing a
  requirement identifier that the applicable set does not hold is a
  finding: either the procedure is not in the applicable set, or the
  identifier is wrong, and both mean nobody knows what the run was
  graded against. Skipping such a run silently produces a campaign
  that passes because its evidence was unreadable.
- Coverage is geometric, not nominal. A sweep is usually cut into
  segments with their own step and dwell, so coverage is tested by
  walking the segments in frequency order and reporting the
  sub-bands of the required range that no segment spans. Overlapping
  segments are fine and must not manufacture a gap; a sweep wider than
  the required range is fine too.
- The step is bounded by the measurement bandwidth, not by convenience:
  stepping further than the allowed share of the bandwidth walks the
  analyser past narrowband emissions that sit between the points, and
  the run then reports a quiet band that was never looked at. The
  dwell is the other half of the same trap -- a segment swept quickly
  gives each of its many points a fraction of the dwell the procedure
  demands, so the per-point value is the segment dwell divided by the
  number of points, and the accumulated sweep total is checked as
  well.
- The ambient background has to sit a stated separation below the
  limit, otherwise the limit line is being read out of the noise of
  the facility rather than out of the unit.
- A measured level only settles against the limit once the declared
  measurement uncertainty is applied. The level plus its uncertainty
  at or under the limit is compliant; the level less its uncertainty
  above the limit is non-compliant; anything between the two is
  inconclusive and owes a repeat with a tighter setup. Reporting the
  bare level as a pass hides every case that only passed because the
  instrument was imprecise.

## Workflow

1. Normalise the applicable detailed requirements: reject an empty
   identifier, an unknown verification category, an inverted frequency
   range, a non-positive bandwidth, a step share outside nought to
   one, a non-positive dwell demand, an unknown detector and a
   repeated identifier.
2. Normalise each run: reject an empty identifier, a run referencing
   nothing, an unknown detector, a negative uncertainty, a missing or
   empty segment list, an inverted segment and a non-positive segment
   step or dwell. Order the segments by start frequency so the result
   does not depend on record order.
3. Resolve the reference. An unresolved reference ends the grading of
   that run with a finding; it is never treated as a pass.
4. Walk the ordered segments across the required range and list the
   sub-bands left unswept.
5. Per segment, compare the step against the allowed share of the
   bandwidth; where the step is admissible, count the frequency points
   and check the per-point dwell against the demand.
6. Accumulate the sweep total dwell and compare it against the
   minimum, absorbing the representation error a sum of decimal
   seconds carries.
7. Check the detector against the one the procedure fixes and the
   ambient background against the demanded separation.
8. Settle the measured level as compliant, non-compliant or
   inconclusive with the uncertainty applied, and collect every
   finding. Across the campaign, also report a detailed requirement
   that no run exercised.

## Pitfalls

- Grading a run against the general limit and never opening the
  procedure it cites. The step, the dwell, the detector and the
  ambient demand all live in the referenced requirement, and a run
  that met none of them can still land under the limit.
- Dropping a run whose reference does not resolve. That is the run
  whose grading basis is unknown, which makes it a finding rather than
  a silent omission.
- Checking only the outer edges of the sweep. Two segments with a hole
  between them cover the endpoints and miss the band in the middle,
  which is exactly where a narrowband emitter hides.
- Reading the segment dwell as the per-point dwell. A segment holding
  a few thousand points gives each of them a small fraction of the
  segment total, and the procedure's demand is per point.
- Comparing an accumulated dwell or an ambient separation with a bare
  greater-or-equal test. Both are sums or differences of decimal
  values and a case that sits exactly on the demand can land a few
  units in the last place off it: 4.1 seconds three times sums to
  12.299999999999999, and 33.3 less 27.3 yields 5.9999999999999964.
  Absorb that representation error in the comparison; never shorten
  the demanded dwell or narrow the demanded separation.
- Settling a level without its uncertainty, or treating an
  inconclusive result as a pass. The inconclusive band is the whole
  reason the uncertainty is declared, and it owes a repeat rather than
  a signature.
- Closing a campaign on the runs that were performed without asking
  which applicable requirements no run touched.

## Behavior contract (gate 3)

The requirement and run normalisation, reference resolution, segment
coverage geometry, bandwidth-bounded step check, per-point and
accumulated dwell checks, detector match, ambient separation,
uncertainty-applied disposition and the campaign aggregation are
exercised by the gate 3 contract test:
scripts/test_e20_detailed_emc_verification_requirements.py against
scripts/e20_detailed_emc_verification_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_detailed_emc_verification_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
