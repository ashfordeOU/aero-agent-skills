---
name: e2001-multipactor-verification-process
description: "Use when execute the multipactor verification process of ECSS-E-ST-20-01C clause 4.1 on a radio-frequency unit: inventory every multipactor-critical gap, derive its frequency-gap-product, drop a gap outside the validated susceptibility-chart band as carrying no credible multipactor risk, look up the parallel-plate breakdown-voltage of the electrode material, convert the peak operating-power at that gap into a multipactor-margin in decibel, then select the verification route, taking analysis-only above the analysis-threshold, a seeded multipactor-test at the elevated test-level below it, and redesign below the test-threshold. Trigger: ecss, e-st-20-electrical-scope, multipactor-verification, frequency-gap-product, secondary-electron-yield, multipactor-margin, electron-seeding-source, multipactor-breakdown-voltage."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multipactor-verification-process, multipactor-verification, frequency-gap-product, secondary-electron-yield, multipactor-margin, electron-seeding-source, multipactor-breakdown-voltage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Multipactor Verification Process (space-systems/ecss/e2001-multipactor-verification-process)

Use when the task is the overall verification process of
ECSS-E-ST-20-01C clause 4.1 -- the sequence that demonstrates, before
flight, that every multipactor-critical gap of a radio-frequency unit
holds the required multipactor-margin, and that decides gap by gap
whether analysis-only suffices or a seeded multipactor-test campaign
is owed.

## Domain quick reference

- Multipactor is a vacuum resonant-electron discharge: a free electron
  released from one electrode is accelerated across the gap by the
  radio-frequency field, strikes the opposite electrode in phase, and
  is multiplied there when the surface secondary-electron-yield
  exceeds unity. It needs vacuum, a resonant transit, and a surface
  that multiplies -- remove any one and the discharge cannot build.
- The governing similarity parameter is the frequency-gap-product,
  the operating frequency times the electrode separation, expressed in
  gigahertz-millimetre. Susceptibility charts are plotted against it,
  so two gaps with the same product and the same material share the
  same breakdown-voltage regardless of their absolute size.
- The charts are valid only inside a band of the frequency-gap-product.
  A product below the band gives the electron no room to reach the
  resonant transit before the field reverses; a product far above it
  puts the transit outside the resonant orders and moves the risk to
  gas-discharge instead. Outside the band the gap carries no credible
  multipactor risk -- and, decisively, the chart fit must not be
  extrapolated there to manufacture a number.
- The breakdown-voltage of the parallel-plate reference geometry rises
  with the frequency-gap-product and depends on the electrode surface:
  a low secondary-electron-yield surface such as gold or titanium
  breaks down later than a silver or alodine-treated surface. The
  margin is the ratio of that threshold to the operating condition,
  taken in decibel; because power goes as voltage squared, the same
  margin is ten times the base-ten logarithm of the power ratio and
  twenty times the logarithm of the voltage ratio.
- The route depends on the margin, in three bands. A large margin lets
  analysis alone discharge the requirement. A smaller but still
  positive margin requires a multipactor-test at a level raised above
  the operating condition by the required test margin. Below the
  test-threshold no test can close the gap and the design has to
  change.
- A test only counts when the electron population is seeded (a
  radioactive source, an ultraviolet source, or an electron gun) and
  the discharge is watched by at least two independent detection
  methods -- a global method such as forward-reverse power nulling and
  a local one such as third-harmonic or electron-current probing. A
  single detector cannot separate a real discharge from an instrument
  artefact.

## Workflow

1. Inventory the multipactor-critical gaps: every place where the
   radio-frequency field crosses a vacuum separation -- connector
   interfaces, filter irises, coupling slots, waveguide steps, dielectric
   support boundaries. Each gap carries its separation, its electrode
   material, its local impedance and its peak operating condition.
2. Derive the frequency-gap-product per gap and categorize it against
   the validated chart band. A gap outside the band leaves the
   assessment with a stated reason; never extrapolate the chart fit to
   cover it.
3. Resolve the electrode material to its chart coefficients and
   compute the parallel-plate breakdown-voltage at that
   frequency-gap-product. An unrecognized material stops the gap --
   without a secondary-electron-yield reference there is no threshold.
4. Convert the breakdown-voltage into a threshold power at the gap's
   local impedance, and the peak operating condition into the same
   unit, then take the multipactor-margin in decibel.
5. Select the route per gap against the project thresholds: analysis-only
   above the analysis-threshold, multipactor-test between the two
   thresholds, redesign below the test-threshold. A margin landing
   exactly on a threshold takes the more favourable route -- the
   equality is the design point, so the comparison absorbs
   floating-point representation error rather than moving the limit.
6. For every gap routed to test, compute the elevated level the test
   has to reach and validate the planned setup: a recognized seeding
   source and at least two independent detection methods.
7. Aggregate. The unit is verified only when no gap needs redesign,
   every tested gap has a valid setup, and every analysis-only gap
   holds the analysis-threshold.

## Pitfalls

- Extrapolating the susceptibility chart outside its validated
  frequency-gap-product band. The fit has no physical content there,
  and a manufactured threshold reads as a comfortable margin on a gap
  nobody assessed.
- Mixing the voltage and power forms of the margin. Twenty log of a
  voltage ratio equals ten log of a power ratio; using ten log on
  voltages halves every margin in the report and using twenty on
  powers doubles it.
- Taking the average operating-power instead of the peak. Multipactor
  responds to the instantaneous field, so a pulsed or
  multi-carrier unit is assessed at its peak envelope, not its mean.
- Treating the analysis-threshold and the test-threshold as one
  number. The whole point of the two bands is that an untested gap has
  to hold a larger margin than a tested one; collapsing them either
  waives tests that are owed or orders tests that are not.
- Running a multipactor-test without seeding. An unseeded gap can stay
  quiet through the whole campaign simply because no starting electron
  appeared, and the silence is then mistaken for a pass.
- Relying on a single detection method. One detector cannot separate a
  genuine discharge from an instrument artefact; the standard's
  intent is an independent pair, global and local.
- Assessing the gap separation without its material. Two identical
  gaps in silver and in gold have different thresholds, so a
  material-free geometry check cannot produce a margin.

## Behavior contract (gate 3)

The frequency-gap-product derivation, chart-band categorization,
material resolution, breakdown-voltage and threshold-power
computation, decibel margin, three-band route selection, elevated
test-level computation, setup validation and unit-level verdict are
exercised by the gate 3 contract test:
scripts/test_e2001_multipactor_verification_process.py against
scripts/e2001_multipactor_verification_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_multipactor_verification_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
