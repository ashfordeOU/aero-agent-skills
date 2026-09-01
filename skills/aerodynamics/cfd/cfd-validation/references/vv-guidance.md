# V&V Guidance and Validation Case Sources

Paraphrased summary for the cfd-validation skill. Standards are cited as
guidance; no long excerpts are reproduced (standards-map.yaml policy).
NACA TR 824 is US government work and is public domain.

## Verification and validation definitions

- AIAA G-077-1998, "Guide for the Verification and Validation of
  Computational Fluid Dynamics Simulations" (AIAA, Reston VA).
  - Verification: the process of determining that a model implementation
    accurately represents the developer's conceptual description of the
    model and its solution. It answers "are we solving the equations
    right?" Verification has two parts: code verification (order-of-
    accuracy testing on manufactured solutions) and solution verification
    (grid and iterative convergence of a given calculation).
  - Validation: the process of determining the degree to which a model is
    an accurate representation of the real world from the perspective of
    the intended uses of the model. It answers "are we solving the right
    equations?" Validation compares computed results with experimental
    reference data of known, quantified uncertainty.
  - Validation is application-specific and condition-specific. A code is
    never "validated" globally, only for stated applications and condition
    ranges.
- ASME V&V 20-2009, "Standard for Verification and Validation in
  Computational Fluid Dynamics and Heat Transfer" (ASME, New York).
  - Introduces the validation comparison error E = S - D (simulation
    result minus experimental data), the validation uncertainty
    U_val, and the standard's requirement that E be compared with
    U_val: when |E| is small relative to U_val, the comparison is
    inconclusive rather than "validated".
  - U_val combines the uncertainties of the simulation result (modeling
    and numerical, including discretization) and of the experimental data
    in quadrature: U_val = sqrt(sum of u_i^2).
  - The validation result should be reported as a band, not a single
    number, and the code's range of applicability stated.

## Validation case catalog sources

- NACA TR 824, "Summary of Airfoil Data" (Abbott, von Doenhoff, Stivers,
  1945). Public domain (US government work). Classic 2D section polars
  for NACA 4/5-digit and 6-series airfoils. The NACA 0012 at M 0.30,
  Re 6e6 with Cd ~ 0.0081 is the standard airfoil validation anchor.
  Available from the NASA Technical Reports Server:
  https://ntrs.nasa.gov/citations/19930090976
- AGARD-AR-138, "Experimental Data Base for Computer Program Assessment"
  (Schmitt and Charpin, 1979). ONERA M6 wing pressure and force data at
  M 0.84, Re 11.72e6, alpha 3.06 deg; nominal CL 0.266, CD 0.0163. Widely
  used transonic wing validation case. Report of the AGARD Fluid Dynamics
  Panel, NATO.
- DLR-F6 wing-body, used by the AIAA Drag Prediction Workshop series
  (DPW-2 onwards). M 0.75, Re 3e6 (mean aerodynamic chord), CL 0.5;
  nominal CD ~ 0.0299 (participant mean). Known for sensitive shock and
  separation modeling; treat CD scatter across participants (of the order
  of a few drag counts at the workshop level) as the realistic
  comparison noise. See https://aiaa-dpw.larc.nasa.gov/
- Zero-pressure-gradient flat plate: laminar Blasius solution
  Cf = 1.328 / sqrt(Rex) (average skin friction), turbulent correlation
  Cf = 0.074 / Rex^0.2 (Schlichting, average skin friction over the plate
  length). Textbook values, no experiment needed for the laminar anchor;
  turbulent cases should state the transition location and Reynolds
  range.

## Acceptance-band guidance

- Section drag (2D airfoil): within 5% of the reference is a typical
  acceptance band for a converged, well-resolved run.
- Wing-body drag (3D transport): within 10% is more realistic given
  experimental scatter and modeling sensitivity.
- Pressure coefficient distributions: within 0.02 absolute, or 5% of the
  local magnitude, whichever is larger, is a common band on the pressure
  side; relax on strong suction peaks and shocks where probe resolution
  limits the reference.
- Report the band before running the comparison; do not tune the band to
  force a PASS.

## Uncertainty sources to list in U_val

- Discretization (grid convergence): GCI from Richardson extrapolation.
- Modeling: turbulence model, transition treatment, boundary conditions.
- Numerical: iterative (residual) convergence, round-off.
- Experimental: reference data scatter, probe position and bias.
- Combine in quadrature with validation_uncertainty(sources).
