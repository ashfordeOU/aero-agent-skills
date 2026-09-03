# Wave-28 leaf spec: delamination-growth (structures, composites pack)

- Path: skills/structures/composites/delamination-growth/
- Pack: composites (existing siblings: laminate-stiffness,
  failure-criteria, composite-bolted-joints, adhesive-bonded-joints,
  sandwich-panels, cmh17-allowables)
- Standards ids: cmh-17  (Ledger Standard: cmh-17)
- Family: structures

## Claim

Assess delamination growth in a composite laminate with fracture
mechanics: compute the mode I strain energy release rate of a double
cantilever beam (DCB) specimen and the mode II strain energy release
rate of an end-notched flexure (ENF) specimen from the applied load,
crack length, and specimen geometry, combine mixed-mode conditions
with the Benzeggagh-Kenane criterion, and decide whether the energy
release rate exceeds the critical rate so that delamination onset and
growth are predicted. Produces G_I, G_II, the mixed-mode ratio, the
critical energy release rate G_c, the onset margin, and the growth
verdict that gate the delamination tolerance assessment.

Does NOT do: evaluate lamina failure from in-plane stresses with
Tsai-Wu or max-stress criteria (failure-criteria owns ply-level stress
failure); compute bearing/bypass stresses at a bolted joint
(composite-bolted-joints); analyze single-lap adhesive shear-lag
(adhesive-bonded-joints); predict metallic fatigue crack growth with
the Paris law (structures damage-tolerance crack-growth); residual
strength of a metallic cracked panel (residual-strength).

## Model (implement exactly)

Functions:
- dcb_g1(P_N, a_m, b_m, h_m, E_pa) -> float:
  G_I = 12*P^2*a^2/(E*b^2*h^3) where h is the half-thickness of the
  DCB arm (specimen total thickness 2h). ValueErrors on P < 0, a <= 0,
  b <= 0, h <= 0, E <= 0.
- dcb_g1_compliance(P_N, delta_m, b_m, a_m) -> float:
  G_I = 3*P*delta/(2*b*a) (compliance form using the total load-line
  opening delta of both arms). The test cross-checks the two forms
  with delta = 2*w where w = P*a^3/(3*E*I) is the one-arm tip
  deflection and I = b*h^3/12 (they must agree to 1e-6).
- enf_g2(P_N, a_m, b_m, h_m, E_pa) -> float:
  G_II = 9*P^2*a^2/(16*E*b^2*h^3), h = half-thickness.
- mixed_mode_ratio(g1, g2) -> float: g2/(g1+g2) when g1+g2 > 0 else 0.
- bk_critical(g1, g2, g1c, g2c, eta) -> float:
  G_T = g1+g2; ratio = mixed_mode_ratio(g1, g2);
  G_c = g1c + (g2c - g1c)*ratio^eta.
  ValueError on g1c <= 0, g2c <= 0, eta <= 0, g1 < 0, g2 < 0.
- onset_margin(g1, g2, g1c, g2c, eta) -> float: G_c - G_T.
- assess(inputs) -> dict: g1, g2, g_t, ratio, g_c, margin,
  growth = G_T >= G_c, verdict "delamination-growth" when growth else
  "no-delamination-growth".
ValueError on any non-physical input (negative load, zero or negative
geometry, zero or negative toughness, eta <= 0).

## Worked example

E = 135e9 Pa, b = 0.02 m.
Specimen A (DCB/ENF, arm half-thickness h = 0.0015 m, total 3 mm):
- dcb_g1(50.0, 0.05, 0.02, 0.0015, 135e9): E*b^2*h^3 = 135e9*4e-4*
  3.375e-9 = 0.18225; 12*2500*0.0025 = 75.0; G_I = 75.0/0.18225 =
  411.52 J/m2 (assert within 0.1).
- dcb_g1(30.0, 0.05, 0.02, 0.0015, 135e9) = 27.0/0.18225 = 148.15
  (assert within 0.05).
- enf_g2(500.0, 0.03, 0.02, 0.0015, 135e9): 16*0.18225 = 2.916;
  9*250000*0.0009 = 2025; G_II = 2025/2.916 = 694.44 J/m2 (assert
  within 0.1).
- Compliance cross-check (use h = 0.003 m so the numbers are clean):
  I = b*h^3/12 = 0.02*2.7e-8/12 = 4.5e-11; one-arm tip deflection w =
  P*a^3/(3*E*I) = 50*1.25e-4/(3*135e9*4.5e-11) = 0.00625/18.225 =
  3.429e-4 m; load-line opening delta = 2*w = 6.859e-4 m.
  dcb_g1(50.0, 0.05, 0.02, 0.003, 135e9) = 12*2500*0.0025/(135e9*
  4e-4*2.7e-8) = 75/1.458 = 51.44 J/m2.
  dcb_g1_compliance(50.0, 6.859e-4, 0.02, 0.05) = 3*50*6.859e-4/
  (2*0.02*0.05) = 0.1029/0.002 = 51.44 (assert the two forms agree
  within 0.01).
- Mixed-mode assess case (g1 = 51.44, g2 = 694.44): g_t = 745.89,
  ratio = 0.9310; B-K with g1c = 250, g2c = 800, eta = 1.5: ratio^1.5
  = e^(1.5*ln 0.9310) = e^(1.5*(-0.07146)) = e^-0.10719 = 0.89837;
  G_c = 250 + 550*0.89837 = 250 + 494.1 = 744.1 (assert within 1.0);
  margin = 744.1 - 745.89 = -1.76 -> growth True -> verdict
  "delamination-growth" (assert margin negative within 0.5).
- No-growth case: DCB P = 30 N with h = 0.003: G_I = 27/1.458 =
  18.52; ENF P = 350: G_II = 9*122500*0.0009/2.916 = 992.25/2.916 =
  340.28; g_t = 358.80, ratio = 0.94841; ratio^1.5 = e^(1.5*
  ln 0.94841) = e^(1.5*(-0.05299)) = e^-0.07948 = 0.92361; G_c = 250 +
  550*0.92361 = 757.98; margin = +399.18 -> "no-delamination-growth"
  (assert within 2.0).
- ValueErrors on P negative, a 0, E 0, g1c 0, eta 0.
Keep at least 16 test methods: DCB value, DCB compliance consistency
(with delta = 2*P*a^3/(3*E*I), I = b*h^3/12), ENF value, ratio,
B-K G_c monotonicity in ratio (higher G_II share raises G_c toward
G_IIc), growth and no-growth verdicts, margin values, ValueErrors.

## Corpus tasks (ids w28-delamination-growth-1/2)

Distinctive tokens: delamination growth, strain energy release rate,
DCB double cantilever beam, ENF end notched flexure, mixed mode
fracture, Benzeggagh Kenane criterion, mode I mode II. Avoid: Tsai-Wu
failure index, ply stresses (failure-criteria); bearing bypass bolt
(composite-bolted-joints); Paris law crack growth (crack-growth);
shear lag adhesive (adhesive-bonded-joints).

1. "assess delamination growth in the composite laminate: compute the
   mode I strain energy release rate of the DCB specimen and the mode
   II rate of the ENF specimen at the crack length"
2. "check mixed mode delamination onset with the Benzeggagh Kenane
   criterion: compare the total energy release rate against the
   critical rate and return the growth verdict"

## SKILL body notes

Pair with failure-criteria (stress-based ply failure at the lamina
level; this leaf is fracture-mechanics delamination at the laminate
level) and crack-growth (the metallic Paris-law sibling). The DCB and
ENF beam-theory formulas are standard textbook results; the body must
state the small-deflection, isotropic-equivalent assumptions and that
the test values are engineering examples. CMH-17 referenced
reference-only (name only).
