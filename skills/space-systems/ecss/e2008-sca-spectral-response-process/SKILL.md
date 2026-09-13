---
name: e2008-sca-spectral-response-process
description: "Evaluate the pre-irradiation short circuit current baseline that clause 6.4.3.5.2 of ECSS-E-ST-20-08C asks for on solar cell assemblies: confirm the reference device is traceable and inside its calibration interval, hold the bench irradiance and temperature to the window a correction stays valid in, translate every sample reading back to reference conditions, express it as a ratio against the corrected reference reading, and hold that ratio inside the declared band before any exposure starts. Use when a pre-irradiation data sheet, reference cell comparison record or irradiation campaign baseline has to be assessed. Trigger: ecss, e-st-20-08c, sca-spectral-response-process, sca-pre-irradiation-short-circuit-current-baseline, solar-cell-assembly-reference-cell-comparison, sca-reference-condition-current-correction, sca-irradiation-baseline-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-spectral-response-process, e-st-20-08c, sca-spectral-response-process, sca-pre-irradiation-short-circuit-current-baseline, solar-cell-assembly-reference-cell-comparison, sca-reference-condition-current-correction, sca-irradiation-baseline-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Pre-Irradiation Current Baseline (space-systems/ecss/e2008-sca-spectral-response-process)

Use when the task is clause 6.4.3.5.2 of ECSS-E-ST-20-08C: the short circuit
current of the test samples measured and held against a reference device
before an irradiation campaign begins. This leaf decides whether the
reference can be leaned on at all, translates every reading to reference
conditions, expresses each sample against the reference, and names the
sample that is about to be exposed with no baseline behind it.

## Domain quick reference

- The baseline is the whole point. Post-irradiation data means nothing on
  its own; the campaign reports degradation, which is a ratio against a
  reading taken before exposure. A sample irradiated without that reading
  is unusable for the rest of the campaign no matter how it later behaves.
- A reference device out of calibration does not produce a slightly wrong
  answer, it produces an unsupported one. Every sample ratio shares the
  same reference reading, so one lapsed calibration moves the whole
  sample set together and no amount of scatter analysis reveals it.
- The reading belongs to the bench, not to the sample. Short circuit
  current tracks irradiance almost linearly and drifts with temperature,
  so two samples read on different days are only comparable after both are
  translated back to reference irradiance and reference temperature.
- The translation is an interpolation inside a window. Far off reference
  irradiance or far off reference temperature it becomes an extrapolation
  of the declared coefficients, and the corrected value then carries an
  error nobody quantified; the reading is refused as a condition failure
  rather than corrected and reported.
- The comparison is a ratio, not a difference. Sample and reference are
  different devices with different areas, so only the ratio against the
  corrected reference reading carries meaning, and only inside the band
  the campaign declared for it.

## Workflow

1. Validate the reference device: a traceable identifier, a calibration
   still inside its declared interval, and a reading taken inside the
   correction window. Each failure is a finding against the whole set.
2. Translate the reference reading to reference irradiance and reference
   temperature, and keep that one corrected current as the denominator for
   every sample in the set.
3. For each sample, decide first whether its bench conditions are
   correctable at all, then translate its reading back to reference
   conditions.
4. Express the corrected sample current as a ratio against the corrected
   reference current and hold that ratio inside the declared band,
   absorbing floating-point representation error at the band edges with a
   named tolerance rather than by widening the band.
5. Flag any sample read after exposure started; it is a post-irradiation
   number sitting in a pre-irradiation column.
6. Reject a sample identifier that appears twice; two readings under one
   name make the set ambiguous rather than redundant.
7. Reconcile the samples read against the samples the campaign plans to
   expose, and report every identifier planned for exposure that never
   got a baseline.

## Pitfalls

- Comparing raw bench currents. A sample read on a brighter day outreads a
  better sample read on a dimmer one, and the band then rejects the wrong
  article.
- Treating the reference reading as a constant of the laboratory. It is a
  measurement like any other, taken at a particular irradiance and
  temperature, and it needs the same translation the samples get before it
  can serve as a denominator.
- Reading the ratio band as the only verdict. A set where every ratio sits
  inside the band but one planned sample was never read is not a clean
  baseline; it is a campaign about to lose a sample.
- Judging a ratio that lands exactly on a band edge by bare arithmetic.
  The ratio is computed from corrected currents, so an assembly built to
  the edge can land a few units in the last place outside it; the
  comparison absorbs that while the declared band stays as declared.
- Carrying on after a lapsed reference calibration because the scatter
  looks tight. Tight scatter around a wrong denominator is exactly what a
  common-mode reference error produces.

## Behavior contract (gate 3)

The reference device validation, the correction window, the translation to
reference conditions, the response ratio and its band, the post-exposure
and duplicate-identifier rejections and the planned-versus-read
reconciliation are exercised by the gate 3 contract test:
scripts/test_e2008_sca_spectral_response_process.py against
scripts/e2008_sca_spectral_response_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_spectral_response_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
