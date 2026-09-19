---
name: e3102-thermal-mechanical-qualification-envelopes
description: "Define the qualification temperature and mechanical envelopes and the working fluid of ECSS-E-ST-31-02 clause 4.4.2 and its merit chart for two-phase heat transport equipment: widen the predicted range by the acceptance and then the qualification margin, confirm the declared survival range contains the result, lift the acceptance vibration density and duration to qualification level, and admit only a fluid that stays liquid across the whole envelope, choosing the one whose weakest end is strongest. Use when a heat pipe or loop heat pipe qualification programme needs its envelopes and its fluid fixed. Trigger: ecss, e-st-31-02-two-phase, two-phase-qualification-temperature-envelope, heat-pipe-working-fluid-merit-number, two-phase-acceptance-margin, survival-range-containment, qualification-vibration-uplift, loop-heat-pipe-fluid-selection."
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
  tags: [ecss, e-st-31-02-two-phase, e3102-thermal-mechanical-qualification-envelopes, two-phase-qualification-temperature-envelope, heat-pipe-working-fluid-merit-number, two-phase-acceptance-margin, survival-range-containment, qualification-vibration-uplift, loop-heat-pipe-fluid-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase — Thermal and Mechanical Qualification Envelopes (space-systems/ecss/e3102-thermal-mechanical-qualification-envelopes)

Use when the task is the envelope definition of ECSS-E-ST-31-02 clause
4.4.2 and the working-fluid merit chart that goes with it -- fixing the
temperature range a heat pipe or loop heat pipe is qualified over, the
mechanical levels it is qualified to, and which fluid can carry heat
across that range at all.

## Domain quick reference

- Temperature builds outward from the prediction in two steps, not one.
  The acceptance envelope is the predicted range widened by the
  acceptance margin; the qualification envelope is that envelope widened
  again by the qualification margin. Both steps are recorded, because a
  later acceptance test is graded against the inner one.
- The declared survival range has to contain the qualification envelope.
  A unit that cannot survive the temperature it is qualified at cannot
  be qualified at it, and this is the containment check that catches a
  survival limit quoted from an earlier, narrower mission.
- Mechanical levels build the same way: an acceptance spectral density
  lifted by a decibel uplift, and an acceptance duration lifted by its
  own factor. The uplift is a ratio in decibel, so the level is the
  acceptance density times ten to the tenth of the uplift, never the
  acceptance density plus the uplift.
- The liquid transport merit of a candidate fluid groups four
  properties: surface tension times liquid density times latent heat,
  divided by liquid viscosity. It has units of watt per square metre and
  it is what the capillary transport limit scales with.
- A fluid is admissible only while it is liquid. Its freezing point has
  to sit at or below the cold end of the qualification envelope and its
  critical point at or above the hot end, each with whatever clearance
  the project declares. Water is the standard casualty of a cold end
  below the ice point.
- Among admissible fluids, the choice follows the WEAKEST end of the
  envelope, not the headline number. The transport limit is sized by the
  worst point in the range, so a fluid that is superb warm and poor cold
  loses to a flatter one across a wide envelope.

## Workflow

1. Build the acceptance envelope from the predicted range and the
   acceptance margin, and refuse a margin that drives the cold end to or
   below absolute zero rather than returning a number nobody can test.
2. Build the qualification envelope from the acceptance envelope and the
   qualification margin, keeping both pairs of limits in the result.
3. Where a survival range is declared, check containment at both ends
   and report each end that fails separately.
4. Lift the acceptance vibration density by the decibel uplift and the
   duration by the duration factor, refusing a factor that would shorten
   the test.
5. Assess each candidate fluid against the qualification envelope with
   the declared clearance, and record the reason each rejected fluid
   was rejected rather than only the survivors.
6. Rank the admitted fluids by their weakest envelope end, break ties by
   name so the choice is reproducible, and return no selection with an
   explicit finding when nothing is admissible.

## Pitfalls

- Adding the decibel uplift to the spectral density. A decibel is a
  ratio; adding it understates a three decibel uplift by about half and
  produces a qualification test weaker than the acceptance one it is
  meant to bound.
- Comparing a survival limit with an envelope end by bare arithmetic.
  The ends are sums and differences of margins, so a limit set exactly
  on the envelope can land a few units in the last place inside it; the
  containment check absorbs that representation error rather than
  raising a phantom finding.
- Choosing the fluid on its best-case merit. The capillary limit is
  sized at the weakest point of the range, and a fluid picked on its
  warm-end number can leave the cold end short of the transported power.
- Forgetting the freezing point when the qualification cold end is
  driven down by margins. The prediction may never go near the ice
  point, but the cold end after two margins often does, and the fluid
  has to be liquid there.
- Quoting a survival range from a previous mission. The envelope moved
  when the margins or the prediction moved, and the old range is exactly
  the one that silently fails containment.

## Behavior contract (gate 3)

Envelope construction, survival containment, vibration uplift and
duration, fluid property validation, merit number, envelope admission
and worst-end selection are exercised by the gate 3 contract test:
scripts/test_e3102_thermal_mechanical_qualification_envelopes.py against
scripts/e3102_thermal_mechanical_qualification_envelopes_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3102_thermal_mechanical_qualification_envelopes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
