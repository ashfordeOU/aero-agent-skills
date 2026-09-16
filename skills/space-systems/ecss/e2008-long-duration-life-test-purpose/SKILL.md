---
name: e2008-long-duration-life-test-purpose
description: "Use when justifying or reviewing the purpose of a long duration life test. Evaluate whether an accelerated long duration life test on a photovoltaic assembly delivers what ECSS-E-ST-20-08C clause 6.4.3.18.1 asks of it, evidence that the assembly stays stable under its worst case operating conditions over the whole service life: convert the elevated test temperature into an Arrhenius acceleration factor from a declared activation energy, turn the planned hours into equivalent service hours, weigh them against the mission demand, refuse a temperature past the ceiling where the degradation mechanism changes, and name every declared operating condition the plan never reproduces. Trigger: ecss, e-st-20-08c, clause-6-4-3-18-1, long-duration-life-test-purpose, arrhenius-acceleration-factor, equivalent-service-hours, worst-case-operating-condition-coverage, degradation-mechanism-ceiling."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-long-duration-life-test-purpose, long-duration-life-test-purpose, arrhenius-acceleration-factor, equivalent-service-hours, worst-case-operating-condition-coverage, degradation-mechanism-ceiling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Long Duration Life Test Purpose (space-systems/ecss/e2008-long-duration-life-test-purpose)

Use when the task is to state and defend why a long duration life test is run
on a photovoltaic assembly under ECSS-E-ST-20-08C clause 6.4.3.18.1 — what the
accelerated run is meant to demonstrate, whether the acceleration behind it
holds, and whether the planned exposure really stands for the service life it
is being offered in place of.

## Domain quick reference

- The evidence is accelerated by construction. Nobody runs fifteen years of
  geostationary service in a laboratory, so the test buys duration with
  stress: the assembly is held hotter than it ever runs in orbit and the extra
  reaction rate is converted back into service hours through an activation
  energy. That conversion is the entire argument, which is why an acceleration
  factor quoted with no activation energy behind it is not a factor, only a
  ratio somebody liked.
- The Arrhenius conversion is explicit and checkable:
  AF = exp((Ea / k) * (1/T_use - 1/T_test)) with temperatures absolute and Ea
  in electronvolts. Multiplying the planned test hours by AF gives the
  equivalent service hours, and the mission demand it is measured against is
  the service life in years times the hours in a year.
- The quantity demonstrated is stability, not survival. The assembly is not
  being taken to failure; it is being asked whether its maximum power still
  sits where it sat at the start. A plan that reports only an intact article
  at the end has answered a different question and the criteria clause has
  nothing to grade.
- Worst case means the conditions together. Hot, biased, illuminated and
  cycled at once, because the interconnects and the bonds fail at the
  interactions. A plan that reproduces the hot soak and quietly drops the bias
  has narrowed its own demonstration, so every declared condition it never
  reproduces is named instead of averaged away.
- One guard sits over the whole conversion. Acceleration is meaningful only
  while the assembly degrades the way it degrades in service. Above the
  temperature where another mechanism takes over — an encapsulant softening, a
  metallisation phase change — the extrapolation stops being conservative, so
  a test above the declared mechanism ceiling closes the justification rather
  than scoring a large factor.

## Workflow

1. Validate the service profile: a positive service life, a worst case
   operating temperature above absolute zero, and a non-empty envelope of
   recognised operating conditions. An unnamed condition is an input error,
   not a condition to be ignored.
2. Turn the service life into the hours the test has to stand for.
3. Form the Arrhenius acceleration factor from the service temperature, the
   planned test temperature and the policy activation energy. Refuse a test
   temperature below the service temperature — that decelerates the article.
4. Multiply the planned test hours by the factor to obtain equivalent service
   hours, and divide by the mission demand for the coverage ratio.
5. Apply the two guards before the arithmetic is allowed to speak: a test
   temperature above the mechanism ceiling, and a factor above the maximum the
   policy admits, both close the justification.
6. Compare the coverage ratio with the policy minimum, absorbing
   floating-point representation error at the boundary with a named tolerance
   rather than by relaxing the required ratio.
7. Report the factor, the equivalent hours, the coverage ratio, the conditions
   the plan never reproduces, and whether the plan reports power stability at
   all.

## Pitfalls

- Quoting an acceleration factor with no activation energy behind it. The
  factor is the conclusion of the argument, not its premise; without Ea there
  is nothing to review and nothing to re-run when the build changes.
- Pushing the test temperature up until the schedule fits. Above the mechanism
  ceiling the article degrades by a route it will never take in orbit, and a
  large factor earned that way is worth less than a small one earned below it.
- Treating survival as stability. An assembly that is intact but three per
  cent down has failed this test; the purpose is a stable maximum power, so a
  plan with no power measurement across the run cannot serve it.
- Reproducing the hot soak alone and calling the envelope covered. Bias,
  illumination and cycling are part of the worst case, and dropping one
  narrows the demonstration without narrowing the claim made from it.
- Accepting a coverage ratio below one because the article passed. A test
  shorter than the service life it stands for has not been extended by its own
  good result.

## Behavior contract (gate 3)

The service profile validation, Arrhenius conversion, equivalent exposure and
coverage ratio, mechanism ceiling and factor guards, and the operating
condition coverage report are exercised by the gate 3 contract test:
scripts/test_e2008_long_duration_life_test_purpose.py against
scripts/e2008_long_duration_life_test_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_long_duration_life_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
