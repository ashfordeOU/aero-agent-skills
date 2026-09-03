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
  author: Aero Agent Skills
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
| cross-cutting/numerics/interpolation | Table interpolation | linear interpolation, piecewise linear, natural cubic spline, table lookup, tabulated data points, extrapolation |
| cross-cutting/numerics/ode-solvers | ODE solvers | explicit Euler, Heun RK2, classical RK4, initial value problem, step size convergence, closed-form comparison |
| cross-cutting/numerics/matrix-operations | Matrix operations | Gaussian elimination with partial pivoting, linear system solve Ax=b, determinant, matrix inverse, singularity detection |
| cross-cutting/numerics/fast-fourier-transform | Fast Fourier transform | DFT definition, radix-2 Cooley-Tukey FFT, magnitude and phase spectrum, inverse FFT, Parseval energy check |
| cross-cutting/tolerancing/tolerance-stackup | Tolerance stackup | worst case, root sum square, assembly limits, nominal dimension, dominant contributor |
| cross-cutting/tolerancing/position-tolerance-calc | GD&T position tolerance | true position, tolerance zone diameter, MMC bonus tolerance, virtual condition, hole and pin |
| cross-cutting/numerics/eigenvalue-decomposition | Eigenvalue decomposition | eigenvalue, eigenvector, Jacobi algorithm, power iteration, deflation, Rayleigh quotient, symmetric matrix |
| cross-cutting/numerics/root-finding | Root finding | bisection, Newton-Raphson, secant method, convergence tolerance, bracketing |
| cross-cutting/units-atmos/dimensional-analysis | Dimensional analysis | Buckingham Pi theorem, dimensional homogeneity, Pi groups, Reynolds number, unit consistency |
| cross-cutting/data-sources/aeronautical-data-sources | Aeronautical data sources | data source credibility, revision status, publisher, engineering reference, citation line, authoritative source |
| cross-cutting/tolerancing/datum-reference-frames | Datum reference frames | datum reference frames, GD&T, datum precedence, primary secondary tertiary, feature control frame, material condition, MMB LMB RMB, degrees of freedom, datum simulators, ASME Y14.5 |
| cross-cutting/tolerancing/gdandt-basics | GD&T basics | GD&T, feature control frame, datum reference frame, form tolerance, orientation tolerance, MMC, LMC, RFS, bonus tolerance |
| cross-cutting/export-control/export-control-awareness | Export Control Awareness | ITAR, EAR, USML, EAR99, 600-series, defense articles, technical data, export control, deemed export, fundamental research, public domain, compliance review, sharing data with foreign collaborators. |
| cross-cutting/numerics/optimization-algorithms | Optimization algorithms | minimize, golden section search, gradient descent, Nelder-Mead, line search, unconstrained optimum |
| cross-cutting/numerics/quaternion-algebra | Quaternion algebra | quaternion product, rotate vector by quaternion, euler to quaternion, quaternion to euler, direction cosine matrix, slerp, quaternion conjugate, unit quaternion, axis angle to quaternion |

## Routing guidance

- Skill packaging and MCP delivery questions route to the SEP-2640
  skill-delivery sub-skill; evaluating a delivered skill's conformance
  and quality routes to the skill-evaluation sub-skill; authoring a
  new SKILL.md (template, kebab-case name, required fields)- Itar questions route to the export-control export-control-awareness sub-skill.
 routes to
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
- Table lookup and interpolation questions (linear interpolation,
  piecewise linear, natural cubic spline, tabulated data points,
  extrapolation beyond the table ends) route to the numerics
  interpolation sub-skill.
- Initial-value problem and differential-equation questions (explicit
  Euler, Heun RK2, classical RK4, step size convergence, error against
  a closed-form solution) route to the numerics ode-solvers sub-skill.
- Dense linear system and matrix questions (Gaussian elimination with
  partial pivoting, Ax=b solve, determinant, matrix inverse, singular
  matrix detection) route to the numerics matrix-operations sub-skill.
- Frequency-domain and spectral questions (discrete Fourier transform,
  radix-2 Cooley-Tukey FFT, magnitude and phase spectrum, inverse FFT,
  Parseval energy check) route to the numerics fast-fourier-transform
  sub-skill.
- Aerospace engineering questions route to their domain pack
  (avionics, space-systems, systems-engineering-safety,
  manufacturing-quality).

- Tolerance stack-up, worst case, and root sum square assembly questions route to the tolerancing tolerance-stackup sub-skill.
- True position, MMC bonus tolerance, and virtual condition questions route to the tolerancing position-tolerance-calc sub-skill.
- Eigenvalue and eigenvector computation, Jacobi eigenvalue algorithm, power iteration, deflation, and Rayleigh quotient questions route to the numerics eigenvalue-decomposition sub-skill.
- Bisection, Newton-Raphson, secant method, and convergence tolerance questions route to the numerics root-finding sub-skill.
- Dimensional analysis, Buckingham Pi theorem, Pi group formation, and dimensional homogeneity checks route to the units-atmos dimensional-analysis sub-skill.
- Data source credibility, revision control, and engineering citation questions route to the data-sources aeronautical-data-sources sub-skill.
- GD&T datum reference frame establishment, datum precedence, degrees of freedom constraint, and feature control frame construction route to the tolerancing datum-reference-frames sub-skill.
- Geometric dimensioning and tolerancing fundamentals, feature control frames, datum reference frames, form and orientation tolerances, and MMC/LMC/RFS bonus tolerance questions route to the tolerancing gdandt-basics sub-skill.
- Quaternion products, vector rotation, euler and direction-cosine conversions, and slerp algebra questions route to the numerics quaternion-algebra sub-skill.
## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
- Numerical minimization (golden section, gradient descent, Nelder-Mead) questions route to the numerics optimization-algorithms sub-skill.
