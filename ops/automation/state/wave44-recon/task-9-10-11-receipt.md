# Extension probe receipt extract: vehicle-design (wave-44, deleg_1a37284c task-0)

Verdict: NO_CANDIDATES (saturated). 55 leaves / 6 packs (conceptual 5,
cost-estimation 3, mass-properties 3, mdo 3, sizing 39, structures-
integration 2). Router parity 55/55. Corpus 202 vehicle-design mentions.
Declines (receipts): high-lift/flap sizing (aero high-lift-systems owns),
winglet sizing (aero winglet-design owns), rotorcraft main-rotor sizing
(FM rotorcraft-main-rotor-sizing owns), trim-tab sizing (0 owners BUT 0
corpus tasks), air-induction/inlet-duct sizing (0 owners, 0 corpus,
sibling-adjacency), deep oleo/shock-strut internals (0 corpus), thrust-
reverser sizing (0 corpus), windshield/canopy aperture (partial owner),
refuel/defuel/fuel-vent (0 corpus), full APU selection (vendor-table
fabrication risk). Full receipt on file (delegation summary).

# Extension probe receipt extract: structures (wave-44, deleg_1a37284c task-1)

Verdict: 2 ranked GO candidates (both wave-43 reserves, re-verified).
1. structures/fem/statically-indeterminate - elastic redundancy analysis
   (fixed-end moments, three-moment/Clapeyron, slope-deflection, moment
   distribution, consistent deformation); 0 owners (plastic-collapse is
   LIMIT analysis only; beam-frame-analysis is stiffness-method numeric);
   Roark/Shigley/Bruhn closed forms; far-25, cs-25.
2. structures/fem/restrained-warping - non-uniform torsion of thin-walled
   open sections (bimoment, warping constant Cw = Iy*h^2/4 I-section,
   St-Venant-vs-warping torque split); 0 owners (torsion-shear-flow is
   free-warping only); Megson/Bruhn/Timoshenko-Vlasov closed forms;
   far-25, cs-25.
Declines: lateral-torsional buckling (0 demand), beam-on-elastic-
foundation (0 demand), plate bending (0 demand + coefficient tables),
grillage/ring-frame (iterative machinery), stress-concentration/hoop
(owned: notch-sensitivity, shrink-fit, pressure-bulkhead). Full receipt
on file.

# Extension probe receipt extract: cross-cutting (wave-44, deleg_1a37284c task-2)

Verdict: 1 ranked GO candidate.
1. cross-cutting/numerics/bandpass-bandstop-filter-design - Butterworth
   IIR bandpass/bandstop via the z-domain LP->BP/LP->BS frequency
   transformation; 0 owners (digital-filter-design is LP/HP only with a
   hard ftype fence; fir-filter-design FIR lowpass only); Oppenheim-
   Schafer/Proakis closed-form algebra, band edges at -3.0103 dB;
   naca-tr-824.
Declines (13): QR/Householder (SVD owns pinv deliverable), iterative
solvers (matrix-operations fence + no sparse surface), adaptive
quadrature/Romberg (numerical-integration owns Richardson), stiff ODE
(ode-solvers fence open), Shapiro-Wilk (probability-distributions ks_gof
owns), constrained opt/LP/KKT (routes to mdo), two-way ANOVA/ANCOVA
(mq gage-rr-anova + DOE), Bender/Mansoor stackup (tolerance-stackup
extension territory + no canonical anchor), QNH/QFE (no map id + FTO
adjacency), EVM/CPM/PERT (no map id, out of domain), SE/safety math
(SES owns), test/QA math (MQ owns), data/format converters (gnc/FTO/
space/avionics own). Full receipt on file.
