---
name: e31-tcs-analysis-thermal-math-model-correlation
description: "Verify a thermal control subsystem by analysis under ECSS-E-ST-31C clauses 4.5.1 and 4.5.2.1. Use when the verification evidence is a thermal mathematical model rather than a test report: closing the steady-state radiative balance for a hot and a cold case, sizing the radiator area the rejected load needs at its temperature limit, integrating the lumped-capacitance transient with a step size the stability limit allows, and correlating the model against measured temperatures by forming per-sensor residuals and ranking which model parameter can account for them inside its credible range. Trigger: ecss, e-st-31-thermal-control-scope, thermal-mathematical-model-steady-state, thermal-mathematical-model-transient, radiator-area-sizing, thermal-model-correlation-residual, lumped-capacitance-time-constant, thermal-model-parameter-tuning."
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
  tags: [ecss, e-st-31-thermal-control-scope, e31-tcs-analysis-thermal-math-model-correlation, thermal-mathematical-model-steady-state, thermal-mathematical-model-transient, radiator-area-sizing, thermal-model-correlation-residual, lumped-capacitance-time-constant]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Analysis, Thermal Mathematical Model and Correlation (space-systems/ecss/e31-tcs-analysis-thermal-math-model-correlation)

Use when the task is verification by analysis under ECSS-E-ST-31C
clauses 4.5.1 and 4.5.2.1 — building the steady and transient thermal
mathematical model, sizing the radiator from the balance it has to
close, and correlating the model against the temperatures a test
actually measured. This leaf overlaps the general thermal-design
material deliberately; what is specific here is the verification chain
from model to correlated model.

## Domain quick reference

- A radiating balance is a fourth-power balance, so nothing in it
  scales linearly. Doubling the dissipation does not double the
  temperature rise, and a radiator sized for a warm sink is not a
  radiator sized for a cold one.
- Sink temperature enters as the fourth power too. A radiator looking at
  deep space and one looking at a warm neighbouring panel reject very
  different loads at the same surface temperature, so the sink is part
  of the case definition, never a default of zero.
- The transient side is governed by a radiative time constant that is
  itself temperature dependent: the linearised value is the thermal
  capacitance over four times the radiative conductance at the current
  temperature. An explicit integration step longer than that constant
  does not merely lose accuracy, it produces an oscillating and
  physically meaningless trajectory.
- Correlation is a statement about residuals, not about a plot. The
  quantities that matter are the mean residual, which exposes a
  systematic bias, and the spread, which exposes a model that is right
  on average and wrong everywhere.
- A residual is only useful when it can be attributed. Ranking the model
  parameters by the change each would need to absorb the residual, and
  comparing that change with the range the parameter is credibly known
  to, separates a genuine model correction from tuning a parameter to a
  value nobody can defend.
- Tuning a parameter outside its credible range to close a residual does
  not correlate the model; it hides the discrepancy in a number that no
  longer represents the hardware.

## Workflow

1. Validate the case: positive area, emittance in the unit interval,
   non-negative dissipation and absorbed external load, and a sink
   temperature above absolute zero.
2. Solve the steady-state balance for the surface temperature, and
   invert the same balance to size the radiator area the load needs at
   the declared temperature limit; refuse the inversion when the limit
   is at or below the sink, because no area rejects a load there.
3. Form the linearised radiative time constant and refuse an explicit
   transient step that exceeds the stability limit rather than silently
   producing an oscillation.
4. Integrate the transient from its initial temperature and report the
   trajectory and the final state.
5. Form the per-sensor residuals of predicted minus measured
   temperature, and report the mean, the spread and the largest
   magnitude.
6. Rank the model parameters by the change each would need to absorb the
   mean residual, and mark every parameter whose required change leaves
   its credible range.
7. Report the balance, the sizing, the transient, the residual
   statistics and the ranked attributions together, so the correlated
   model is traceable to the change that produced it.

## Pitfalls

- Sizing a radiator with the sink at absolute zero because no value was
  given. The missing sink is the single most common reason a radiator
  arrives undersized for the case it will actually fly.
- Scaling a radiator area linearly with dissipation. The rejection goes
  as the fourth power of temperature, so the area that rejects twice the
  load at the same limit is not twice the area of the original balance.
- Integrating the transient with a convenient step. The explicit step
  has a stability limit set by the linearised time constant; past it the
  trajectory oscillates and still terminates with a plausible number.
- Reading a small mean residual as a correlated model. A model that is
  fifteen kelvin high on one sensor and fifteen low on another has a
  mean residual of zero and no correlation at all.
- Tuning whichever parameter closes the residual fastest. The
  attribution has to stay inside what the parameter is credibly known
  to, or the correlated model has bought its agreement with a number
  that no longer describes the hardware.
- Correlating against sensors the model never claimed to predict. A
  residual at a point with no corresponding model node measures the
  mapping, not the model.

## Behavior contract (gate 3)

Radiative balance, steady-state solution, radiator sizing with its sink
guard, linearised time constant, explicit transient with its stability
refusal, residual statistics and parameter attribution with credible
range are exercised by the gate 3 contract test:
scripts/test_e31_tcs_analysis_thermal_math_model_correlation.py against
scripts/e31_tcs_analysis_thermal_math_model_correlation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e31_tcs_analysis_thermal_math_model_correlation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
