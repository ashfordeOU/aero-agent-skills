---
name: e2008-sca-electrical-performance-acceptance
description: "Use when an SCA acceptance data sheet, flash-test record or lot power summary has to be assessed. Evaluate the electrical performance measurement of clause 6.3.3 of ECSS-E-ST-20-08C applied to cell assemblies in the acceptance sequence: hold the bench conditions to the window a correction is valid in, translate current, voltage and maximum power back to reference irradiance and temperature, test the corrected point for internal consistency, hold it against the declared minimum, then roll the lot up on sample size and reject share. Trigger: ecss, e-st-20-08c, sca-electrical-performance-acceptance, sca-acceptance-electrical-measurement, solar-cell-assembly-maximum-power-acceptance, sca-reference-condition-correction, sca-acceptance-lot-reject-share."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-electrical-performance-acceptance, e-st-20-08c, sca-electrical-performance-acceptance, sca-acceptance-electrical-measurement, solar-cell-assembly-maximum-power-acceptance, sca-reference-condition-correction, sca-acceptance-lot-reject-share]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Electrical Performance in Acceptance (space-systems/ecss/e2008-sca-electrical-performance-acceptance)

Use when the task is clause 6.3.3 of ECSS-E-ST-20-08C: the electrical
performance measurement carried out on cell assemblies inside the
acceptance test sequence. This leaf takes the bench reading, decides
whether it can be translated at all, translates it, tests the result for
internal consistency, holds it against the declared minimum, and rolls
the lot up into one acceptance verdict.

## Domain quick reference

- The number on the data sheet is not the number the decision is taken
  on. The reading belongs to the conditions the bench delivered; the
  declared minimum belongs to the reference conditions. Comparing the
  two directly accepts weak assemblies measured cold and rejects good
  ones measured hot.
- A translation is only an interpolation inside a window. Far off
  reference irradiance or reference temperature, the declared drift
  coefficients are being extrapolated and the corrected value carries an
  error nobody quantified, so the measurement is refused as a condition
  fault rather than reported as a power result.
- Current and power follow irradiance; all three quantities carry a
  temperature drift. Correcting one of them and not the others leaves a
  triple that no longer describes a single operating point.
- The corrected triple grades itself. Maximum power cannot exceed the
  product of short-circuit current and open-circuit voltage, and it
  cannot sit far under it either. A corrected point outside that band is
  an instrument, connection or transcription fault, and reporting it as
  a weak assembly sends a good part to the scrap bin and leaves the
  bench uncalibrated.
- The three arms are ranked, not merged. A condition fault is reported
  ahead of an inconsistent point, and an inconsistent point ahead of a
  power shortfall, because grading the power of a reading taken outside
  the correction window is wasted effort.
- The lot carries two separate questions. Did the measurement cover
  enough of the lot to speak for it, and did too much of what it covered
  fall out. One assembly under the minimum is a part to set aside; a
  lot with too many of them is a lot whose acceptance measurement has
  stopped being a sampling exercise.
- An assembly meant to sit exactly on its declared minimum is judged
  with the representation error absorbed. The corrected power is a
  product and a difference of declared numbers, so it can land a few
  units in the last place below a minimum it was built to meet; the
  comparison tolerates that while the minimum stays as declared.

## Workflow

1. Read the bench reading with its irradiance, temperature and the
   three measured quantities, and the declared drift coefficients of the
   assembly type. Reject an incomplete or non-physical reading rather
   than carrying it into a correction.
2. Test the bench conditions against the correction window and stop
   there if either axis is outside it.
3. Translate current, voltage and maximum power to reference irradiance
   and reference temperature.
4. Test the corrected triple against its own current-voltage envelope
   and report an implausible fill as a measurement fault.
5. Compare the corrected maximum power with the declared minimum and
   report the margin either way.
6. Rank the three arms into one assembly verdict: condition fault
   first, then inconsistent point, then power shortfall.
7. Roll the lot up: size the sample against the lot, group the
   assemblies by verdict, compute the reject share against the policy
   limit, and return a verdict that is clean only when both hold.

## Pitfalls

- Comparing a raw bench reading with a reference-condition minimum. The
  bench rarely sits at reference, so the comparison silently grades the
  bench instead of the assembly.
- Correcting for temperature and ignoring irradiance. A flash a few per
  cent low reads as a uniformly weak lot, and the lot gets rejected for
  a lamp that needed recalibrating.
- Treating an impossible corrected point as a weak assembly. A maximum
  power above its own current-voltage envelope is a fault in the
  measurement chain; scrapping the part hides the fault and the next lot
  measures the same way.
- Merging the three arms into one pass or fail. A reading taken out of
  window with a low corrected power is one root cause and one fix; a
  merged verdict sends the lot back for the wrong correction.
- Reading the reject share without the sample size. A lot sampled at
  two assemblies can show a perfect reject share and say nothing about
  the lot at all.
- Judging a corrected power that lands exactly on the declared minimum
  by bare arithmetic. The value is computed, not tabulated, so an
  assembly built to the minimum can land a few units in the last place
  under it; the comparison absorbs that while the minimum stays as
  declared.

## Behavior contract (gate 3)

The correction window, the translation to reference conditions, the
envelope consistency test, the declared minimum margin, the ranked
assembly verdict and the rolled-up lot sample size and reject share are
exercised by the gate 3 contract test:
scripts/test_e2008_sca_electrical_performance_acceptance.py against
scripts/e2008_sca_electrical_performance_acceptance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_sca_electrical_performance_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
