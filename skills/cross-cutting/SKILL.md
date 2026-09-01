---
name: cross-cutting
description: "Use when a task concerns the skill delivery layer, the standard atmosphere, engineering documentation, or numerical analysis: guide the router to the cross-cutting pack. SEP-2640 skill-delivery, skill-evaluation, skill-authoring cover SKILL.md conformance, quality, authoring; isa-atmosphere, unit-conversion, and temperature-conversion cover atmosphere and units; engineering-margins and engineering-report cover margins and reports; tolerance-stackup assembly tolerancing and position-tolerance-calc GD&T position tolerance; convergence-verification Richardson, least-squares-regression OLS, uncertainty-propagation GUM, numerical-integration quadrature, finite-difference-derivatives finite differences, monte-carlo-sampling sampling. Trigger: skill delivery, SEP-2640, skill evaluation, skill authoring, SKILL.md, ISA, unit conversion, temperature conversion, margin of safety, tolerance stack-up, worst case, RSS, GD&T, position tolerance, engineering report, least squares, uncertainty, numerical integration."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: sep-2640
    reference-only: true
  - id: ecss
    reference-only: true
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; router/entry point for the cross-cutting domain pack"
metadata:
  domain: cross-cutting
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Cross-cutting domain pack (router)

Route here when the task is the skill format, packaging, or delivery
layer, the standard atmosphere, the engineering documentation layer,
or numerical analysis.

## Domain

Cross-cutting and foundational: the skill-format and delivery
specification (SEP-2640) that governs how this library packages and
serves skills over MCP, skill evaluation, the ISA standard atmosphere
for performance work, unit conversion, the documentation discipline
for engineering reports and margins, and the numerical analysis
discipline (verification, regression, uncertainty propagation,
integration) for engineering calculations.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| cross-cutting/sep2640/skill-delivery | SEP-2640 skill delivery | SKILL.md packaging, skill URIs, MCP resources, server readiness |
| cross-cutting/sep2640/skill-evaluation | Skill evaluation | SEP-2640 conformance checks, weighted quality score, acceptance verdict, coverage ratio |
| cross-cutting/sep2640/skill-authoring | Skill authoring | frontmatter template, kebab-case name rule, pre-publish conformance check, required fields |
| cross-cutting/units-atmos/isa-atmosphere | ISA atmosphere | standard atmosphere, temperature lapse, pressure altitude, density |
| cross-cutting/units-atmos/unit-conversion | Unit conversion | SI/imperial/aviation units, length, speed, temperature, pressure, density, Mach |
| cross-cutting/units-atmos/temperature-conversion | Temperature conversion | kelvin, celsius, fahrenheit, rankine, absolute zero, temperature difference |
| cross-cutting/documentation/engineering-margins | Engineering margins | margin of safety, allowable vs applied load, limit and ultimate basis, report sentence |
| cross-cutting/documentation/engineering-report | Engineering report | report anatomy, abstract length, required sections, completeness verdict |
| cross-cutting/numerics/convergence-verification | Convergence verification | Richardson extrapolation, GCI, observed order, discretization error, mesh refinement |
| cross-cutting/numerics/least-squares-regression | Least squares regression | OLS slope and intercept, residual standard deviation, R-squared, prediction |
| cross-cutting/numerics/uncertainty-propagation | Uncertainty propagation | GUM first order law, sensitivity coefficients, combined uncertainty, coverage factor |
| cross-cutting/numerics/numerical-integration | Numerical integration | trapezoid rule, Simpson rule, Gauss-Legendre quadrature, Richardson error estimate |
| cross-cutting/numerics/finite-difference-derivatives | Finite difference derivatives | forward/backward/central difference, step size, second derivative, tabulated data |
| cross-cutting/numerics/monte-carlo-sampling | Monte Carlo sampling | seeded draws, sample mean and standard deviation, percentile confidence interval, histogram |
| cross-cutting/tolerancing/tolerance-stackup | Tolerance stackup | worst case, root sum square, assembly limits, nominal dimension, dominant contributor |
| cross-cutting/tolerancing/position-tolerance-calc | GD&T position tolerance | true position, tolerance zone diameter, MMC bonus tolerance, virtual condition, hole and pin |

## Routing guidance

- Skill packaging and MCP delivery questions route to the SEP-2640
  skill-delivery sub-skill; evaluating a delivered skill's conformance
  and quality routes to the skill-evaluation sub-skill; authoring a
  new SKILL.md (template, kebab-case name, required fields) routes to
  the skill-authoring sub-skill.
- Standard atmosphere questions route to the units-atmos
  isa-atmosphere sub-skill; converting units between systems routes to
  the unit-conversion sub-skill; converting between temperature
  scales (kelvin, celsius, fahrenheit, rankine) routes to the
  temperature-conversion sub-skill.
- Margin of safety and report sentence questions route to the
  documentation engineering-margins sub-skill; report structure and
  completeness questions route to the engineering-report sub-skill.
- Mesh refinement, Richardson extrapolation, and discretization
  error questions route to the numerics convergence-verification
  sub-skill.
- Regression fitting questions (slope, intercept, R-squared,
  prediction) route to the numerics least-squares-regression
  sub-skill.
- Measurement uncertainty questions (GUM, combined and expanded
  uncertainty, coverage factor) route to the numerics
  uncertainty-propagation sub-skill.
- Quadrature and integral-estimate questions (trapezoid, Simpson,
  Gauss-Legendre) route to the numerics numerical-integration
  sub-skill.
- Numerical differentiation questions (forward, backward, central
  difference, step size, tabulated derivatives) route to the numerics
  finite-difference-derivatives sub-skill.
- Sampling and distribution questions (seeded Monte Carlo draws,
  percentiles, confidence intervals, histograms) route to the numerics
  monte-carlo-sampling sub-skill.
- Aerospace engineering questions route to their domain pack
  (avionics, space-systems, systems-engineering-safety,
  manufacturing-quality).

- Tolerance stack-up, worst case, and root sum square assembly questions route to the tolerancing tolerance-stackup sub-skill.
- True position, MMC bonus tolerance, and virtual condition questions route to the tolerancing position-tolerance-calc sub-skill.
## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
