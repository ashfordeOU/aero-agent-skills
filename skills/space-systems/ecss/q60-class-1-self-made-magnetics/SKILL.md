---
name: q60-class-1-self-made-magnetics
description: "Assess an in-house wound magnetic part built for class 1 equipment under ECSS-Q-ST-60C clause 4.6.8: refuse a part with no wire, core or qualified winding procedure behind it, test the winding current density, core flux utilisation, interwinding dielectric withstanding voltage and hot spot margin against recognised practice, derive the screening sequence the construction, potting state and flight lot call for, and return one practice-satisfied, screening-outstanding, design-nonconforming or magnetics-not-admissible disposition. Use when a magnetic part is wound in house rather than procured to a component specification. Trigger: ecss, q-st-60c, self-made-magnetics-current-density, self-made-magnetics-flux-utilisation, self-made-magnetics-screening-sequence, self-made-magnetics-hot-spot-margin."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-1-self-made-magnetics, self-made-magnetics-current-density, self-made-magnetics-flux-utilisation, self-made-magnetics-screening-sequence, self-made-magnetics-hot-spot-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 1 — Self-Made Wound Magnetic Parts (space-systems/ecss/q60-class-1-self-made-magnetics)

Use when the task is clause 4.6.8 of ECSS-Q-ST-60C: a magnetic part wound in
house for class 1 equipment rather than bought against a component
specification. This leaf checks the design against recognised practice and
derives the screening the part owes before it may be used.

## Domain quick reference

- A self-made part has no procurement history to lean on, so the evidence is
  built rather than inherited. Without a stated wire specification, a stated
  core specification, a qualified winding procedure and a certified operator
  there is nothing to assess: the part is not admissible.
- Four numbers decide the design. Winding current density, core flux
  utilisation, interwinding dielectric withstanding voltage and hot spot
  margin against the insulation rating are the recognised-practice checks, and
  a part passing three of them has not passed.
- The limits are inclusive. A current density exactly on the ceiling, a flux
  utilisation exactly on the fraction and a hot spot margin exactly on the
  derating are all compliant, and float arithmetic lands on them.
- The interwinding test voltage is derived, not chosen. It follows the working
  voltage through a fixed construction, so a winding whose working voltage
  rises owes a higher test than the one it passed last build.
- The screening sequence is derived too. Impregnation state, working voltage,
  a gapped core and the flight lot size each add their own step, and the
  sampled destructive step comes last because it consumes a part.
- A single flight part owes no destructive sample. Consuming the only unit
  built proves the build and leaves nothing to fly.
- Coverage is a fraction of the owed sequence, not of the work performed.
  Closing a step the part never owed raises the count of work done and clears
  nothing.

## Workflow

1. Test admissibility first: part identity, wire specification, core
   specification, winding procedure qualification and operator certification.
   Report every reason rather than stopping at the first.
2. Compute the four design values: current density from the winding current
   and conductor cross section, flux utilisation from peak and saturation flux
   density, the required interwinding test voltage from the working voltage,
   and the hot spot margin from the insulation rating.
3. Raise a finding for each value outside recognised practice.
4. Derive the owed screening sequence from the baseline plus the additions the
   impregnation state, working voltage, core gap and flight lot size call for,
   ordered so the sampled destructive step is last.
5. Compare the screening already closed against the owed sequence and return
   the outstanding steps plus the coverage fraction.
6. Return one disposition: practice-satisfied, screening-outstanding,
   design-nonconforming or magnetics-not-admissible. Inadmissibility overrides
   everything and a finding outranks outstanding screening.

## Pitfalls

- Treating a house winding as a qualified component. The part carries the
  build shop's process record and nothing else, and an unqualified procedure
  makes every later measurement unattributable.
- Sizing the conductor for room-temperature resistance. The current density
  ceiling is a thermal limit in vacuum, where the winding sheds heat by
  conduction alone and the margin that held on the bench is gone.
- Driving the core to its datasheet saturation. The datasheet value is a cold
  nominal, and a core sitting near it distorts and heats at the temperature
  and tolerance extremes the part actually sees.
- Reusing last build's interwinding test voltage. The required voltage tracks
  the working voltage, so a rewound part at higher voltage passes a test it
  has already outgrown.
- Reading a bound as excluded. A hot spot margin exactly on the derating, a
  flux utilisation exactly on the fraction and a current density exactly on
  the ceiling are all inside, and a strict comparison rejects a compliant
  build.
- Sampling a lot of one for the destructive step. The sample is the flight
  part, and the analysis passes on a part that can no longer be delivered.

## Behavior contract (gate 3)

The admissibility test, current density, flux utilisation, required
interwinding test voltage, hot spot margin, design findings, screening
derivation, outstanding comparison, coverage fraction and the disposition are
exercised by the gate 3 contract test:
scripts/test_q60_class_1_self_made_magnetics.py against
scripts/q60_class_1_self_made_magnetics_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q60_class_1_self_made_magnetics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
