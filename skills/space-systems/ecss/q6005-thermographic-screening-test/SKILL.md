---
name: q6005-thermographic-screening-test
description: "Analyze an infrared image of a biased hybrid microcircuit taken before its package is sealed and decide which sites are behaving as the design predicted, under ECSS-Q-ST-60-05 clause 10.3.2. Use when a thermographic screening run has to be graded rather than glanced at: test that the detector resolves the smallest feature, correct the reading for surface emissivity and reflected background, take every rise against the recorded reference, weigh each site against the absolute surface limit and its predicted rise, catch the site that is far colder than predicted, and return one verdict. Trigger: ecss, q-st-60-05, hybrid-thermographic-screening, infrared-hot-spot-detection, hybrid-surface-emissivity-correction, thermographic-detector-resolution, predicted-temperature-rise-excursion, thermographic-screen-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-thermographic-screening-test, hybrid-thermographic-screening, infrared-hot-spot-detection, hybrid-surface-emissivity-correction, thermographic-detector-resolution, predicted-temperature-rise-excursion, thermographic-screen-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Thermographic Screening Test (space-systems/ecss/q6005-thermographic-screening-test)

Use when the task is clause 10.3.2 of ECSS-Q-ST-60-05: the infrared image of
a powered hybrid taken while the package is still open, read to find surface
temperatures the design did not predict. Where the step sits in the run is
graded under the screening sequence; the burn-in that precedes it and the
photographic record that follows have leaves of their own.

## Domain quick reference

- The image is only as good as the setup that took it. A detector that
  cannot put enough pixels across the smallest feature averages a bond-pad
  hot spot into its surroundings, and the screen then reports a clean unit
  with complete confidence.
- An infrared camera measures radiance, not temperature. Without the surface
  emissivity and the temperature of what that surface reflects, the reading
  is a number nobody can defend, so the correction runs before any
  comparison — in kelvin and in fourth powers, because that is where
  radiance lives.
- Every comparison is a rise above the recorded reference, never an absolute
  reading. A workshop five degrees warmer would otherwise turn a whole batch
  into hot spots and a cold morning would hide a real one.
- A site is judged twice. The absolute surface limit catches a site that
  will not survive; the ratio against the predicted rise catches a site that
  is not behaving like the circuit that was designed. The absolute limit is
  read first.
- A site far colder than its prediction is an anomaly too. An open bond or a
  part that never turned on dissipates nothing, and a screen that only looks
  for heat walks straight past the defect.
- The image is taken after the unit has been held biased long enough to
  settle. A frame captured on the way up reads low everywhere, which is the
  most flattering error the test can make.
- The setup gates the result rather than averaging into it. An inadequate
  setup makes the screen invalid — not a pass with reservations — because
  there is nothing to have confidence in.

## Workflow

1. Take the reference temperature the unit sat in, the bias condition, the
   dwell it was held for, and the sites the image covers.
2. Test the detector against the smallest feature that matters, using the
   pixel pitch and the required pixels across that feature.
3. Correct each reading for surface emissivity and reflected background
   before anything is compared.
4. Grade the setup conditions from met and recorded down to not met, and
   overrule a declared dwell with the measured one when they disagree.
5. Convert each corrected site reading into a rise above the reference, and
   reject a biased site that reads below it as an input error.
6. Take the ratio of each rise to the rise predicted for that site.
7. Group each site: over the absolute surface limit first, then by excursion
   ratio downward, then the cold-site case.
8. Name the verdict: invalid while the setup is short, rejected on a
   critical or major hot spot or a cold site, passed with open actions on a
   minor excursion or an unrecorded condition, passed only when nothing is
   outstanding.

## Pitfalls

- Reading the camera's number as a temperature. It is the temperature a
  perfect emitter would need to reach, and a hybrid lid is not one.
- Comparing absolute readings between units imaged on different days. The
  rise above the reference is the only quantity that travels.
- Imaging a feature the detector cannot resolve and believing the flat
  result. The averaging is invisible in the image and fatal to the screen.
- Taking the frame as soon as the bias goes on. The unit is still climbing,
  and every site reads low at once, which looks like a good unit.
- Looking only for heat. The missing bond is the site that stayed at ambient
  while everything around it warmed up.
- Letting a strong image carry a setup that never recorded the emissivity.
  The correction cannot be reconstructed afterwards, so neither can the
  result.
- Sealing the package before the anomalies are dispositioned. The whole
  value of doing this before the seal is that a repair costs nothing to
  reach.

## Behavior contract (gate 3)

The detector-resolution test, emissivity and reflected-background
correction, rise-above-reference computation, excursion ratio, absolute
surface limit precedence, cold-site rule, setup-condition grading, setup
index and screen verdict are exercised by the gate 3 contract test:
scripts/test_q6005_thermographic_screening_test.py against
scripts/q6005_thermographic_screening_test_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6005_thermographic_screening_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
