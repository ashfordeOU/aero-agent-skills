---
name: e2008-coverglass-humidity-test-purpose
description: "Determine what accelerated damp storage of a coated coverglass has to deliver under ECSS-E-ST-20-08C clause 8.7.11.1.1: map the declared coating degradation mechanisms onto what the exposure reveals, derive the humidity and Arrhenius acceleration of the planned chamber over the declared store, turn it into the field interval the run stands in for, and check the sample surface sits far enough above the chamber dew point that the exposure is damp heat and not liquid water. Use when scoping or reviewing a coated-coverglass humidity exposure. Trigger: ecss, e-st-20-08c-clause-8-7-11-1-1, coated-coverglass-damp-storage, coverglass-coating-stability-exposure, damp-heat-acceleration-factor, chamber-dew-point-condensation-margin, coverglass-equivalent-field-storage-hours."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-humidity-test-purpose, coated-coverglass-damp-storage, coverglass-coating-stability-exposure, damp-heat-acceleration-factor, chamber-dew-point-condensation-margin, coverglass-equivalent-field-storage-hours, coverglass-coating-degradation-mechanism]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Humidity Test Purpose (space-systems/ecss/e2008-coverglass-humidity-test-purpose)

Use when the task is to state and defend why a coated coverglass is put
through accelerated damp storage under ECSS-E-ST-20-08C clause
8.7.11.1.1 -- which coating stability problems the exposure is meant to
surface, whether this part has any of them declared against it, and
whether the planned chamber run can surface them at all.

## Domain quick reference

- A coated coverglass leaves the coater looking finished. The
  antireflection stack, the conductive layer and the ultraviolet reject
  filter are thin films on glass, and the ways they fail are slow:
  hydrolysis of the film, corrosion of a conductive layer, water
  creeping along the coating-to-glass interface until adhesion goes,
  pinholes opening and scattering.
- None of that is visible on the day of deposition. It is visible after
  months in a humid store, which is the interval a programme does not
  have before the panel is populated. The exposure exists to buy that
  interval back.
- Accelerated damp storage invents no failure mode. It runs the ones
  already present faster, so the acceleration factor is what the whole
  argument rests on: a humidity term in the chamber-to-store humidity
  ratio and an Arrhenius term in the temperature difference.
- The figure the requirement is written against is the equivalent field
  interval -- acceleration multiplied by chamber hours -- not the
  chamber hours themselves. Two chambers running the same hours at
  different conditions stand in for field intervals that differ by
  orders of magnitude.
- Condensation ends the argument. If the sample surface sits at or below
  the dew point of the chamber air, water condenses on the coverglass
  and the exposure is no longer damp heat: it is liquid water driving a
  different mechanism at an unknown rate, and the hours accumulated buy
  no field equivalence.
- A coating with no moisture-sensitive mechanism declared against it
  does not earn the exposure. That is a different outcome from a
  declared mechanism with no exposure planned, and both differ again
  from an exposure planned that cannot reach the interval it was meant
  to stand in for.

## Workflow

1. Validate the damp-storage policy first: the field temperature and
   humidity the exposure stands in for, the required equivalent
   interval, the activation energy, the humidity exponent, the
   condensation margin and the chamber-hours floor. A negative humidity
   exponent, which would make a drier chamber the harsher one, is
   refused rather than used.
2. Group the declared degradation mechanisms, rejecting an unrecognised
   one rather than ignoring it, and map each to what the exposure
   reveals. Append the shared stability objective whenever any mechanism
   is present.
3. Close early when the part is uncoated or nothing moisture-sensitive
   is declared: the exposure would run a mechanism nobody has claimed.
4. Close on a finding when a mechanism is declared and no exposure is
   planned.
5. Validate the chamber plan and derive the dew point of its air and the
   margin the sample surface holds above it.
6. Derive the humidity and Arrhenius acceleration terms, multiply them,
   and turn the planned hours into the equivalent field interval.
7. Check the condensation margin, the chamber-hours floor and the
   equivalent interval, reporting every inadequacy found rather than
   only the first.
8. Close on one verdict: exposure not required, exposure not planned,
   exposure inadequate, or coating stability evidenced.

## Pitfalls

- Quoting chamber hours as the exposure. The hours only mean something
  once multiplied by the acceleration, and the acceleration depends on
  conditions the hours do not record.
- Running a chamber whose sample surface tracks below the air
  temperature. The dew point is a property of the air; the condensation
  is a property of the surface, and only the surface decides whether the
  test is still damp heat.
- Treating an absent mechanism list as an empty one. An inventory nobody
  wrote is not a declaration that nothing is moisture-sensitive, and the
  validator refuses it.
- Accepting an unrecognised mechanism name by passing it through. A
  mechanism the model cannot map contributes no objective and silently
  shrinks what the exposure is being asked to show.
- Comparing an equivalent interval, a condensation margin or a duration
  with its bound by bare arithmetic. Each is a computed quantity built
  from an exponential or a logarithm, so a plan sitting exactly on a
  bound can evaluate a few units in the last place on the wrong side of
  it; the comparisons absorb that representation error while the bounds
  stay untouched.
- Reporting an acceleration of many hundreds without its assumptions. A
  factor that large rests on the activation energy and the humidity
  exponent, not on the chamber, and the record has to say so.

## Behavior contract (gate 3)

The policy validation, the mechanism inventory and objective mapping,
the humidity and Arrhenius acceleration terms and their product, the
equivalent field interval, the Magnus dew point and condensation margin,
the chamber plan validation and the purpose verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_coverglass_humidity_test_purpose.py against
scripts/e2008_coverglass_humidity_test_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_humidity_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
