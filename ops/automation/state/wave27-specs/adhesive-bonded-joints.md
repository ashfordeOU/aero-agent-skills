# Wave-27 leaf spec: adhesive-bonded-joints (structures, composites pack)

- Path: skills/structures/composites/adhesive-bonded-joints/
- Pack: composites (existing siblings: failure-criteria,
  composite-bolted-joints, laminate-stiffness, sandwich-panels,
  cmh17-allowables)
- Standards ids: cmh-17  (Ledger Standard: cmh-17)
- Family: structures

## Claim

Analyze an adhesively bonded joint (single-lap) between two
aerospace adherends: from the applied load, the overlap length, the
bond width, the adherend modulus and thickness, and the adhesive
thickness and shear modulus, compute the average adhesive shear
stress, the shear-lag parameter, the peak shear stress at the overlap
ends with the Volkersen-style shear-lag correction, and the joint
margin against the adhesive allowable shear stress. Produces the
average and peak stresses, the stress concentration ratio, and the
pass or fail verdict that gate bonded joint design in the CMH-17
composite context.

Does NOT do: analyze bolted joints with bearing, net-tension, and
shear-out failure modes (composite-bolted-joints owns the mechanical
fastener analysis); compute laminate stiffness or failure criteria of
the adherend plies (laminate-stiffness, failure-criteria); or select
adhesive materials (material-selection in the materials pack). This
leaf is the adhesive bondline shear analysis of a single-lap joint
only; peel stress is reported as out of scope.

## Model (implement exactly)

Geometry: single-lap joint, overlap length L, width b, two identical
adherends of thickness t and modulus E; adhesive layer thickness t_a
and shear modulus G_a.

Shear-lag parameter:
  beta = sqrt( (G_a / t_a) * (2.0 / (E * t)) )   (1/m)
(For identical adherends the 2/(E t) term is the sum 1/(E1 t1) +
1/(E2 t2) with E1=E2=E, t1=t2=t.)

Average shear stress:
  tau_avg = P / (b * L).

Peak shear stress (Volkersen-style, ends of the overlap):
  tau_max = tau_avg * (beta*L/2) / tanh(beta*L/2).
Note: (beta*L/2)/tanh(beta*L/2) -> 1 as beta*L -> 0 (uniform shear)
and grows with beta*L.

Inputs:
- load_n (float, P), width_m (b), overlap_m (L),
- adherend_E_pa (float), adherend_t_m (float),
- adhesive_G_pa (float), adhesive_t_m (float),
- allowable_shear_pa (float, adhesive allowable).

Functions:
- shear_lag_beta(adherend_E_pa, adherend_t_m, adhesive_G_pa,
  adhesive_t_m) -> float.
- avg_shear_stress(load_n, width_m, overlap_m) -> float.
- peak_shear_stress(load_n, width_m, overlap_m, beta) -> float:
  tau_avg * (beta*L/2)/tanh(beta*L/2).
- concentration_factor(beta, overlap_m) -> float: peak/avg.
- joint_margin(allowable_shear_pa, peak_shear_pa) -> float:
  allowable/peak (margin ratio, MS-style = allowable/peak - 1 also
  returned as margin_ms).
- analyze(...) -> dict {beta, tau_avg, tau_max, concentration,
  margin_ratio, margin_ms, pass (bool)}: pass when peak <= allowable.

ValueError on: load < 0, width/overlap <= 0, modulus/thickness/G_a/t_a
<= 0, allowable <= 0.

## Worked example

Aluminum adherends: E 70 GPa, t 2 mm; adhesive G 0.5 GPa, t_a 0.2 mm;
bond width 25 mm, load 10 kN.
Case 1: overlap L 25 mm, allowable 25 MPa.
- beta = sqrt((0.5e9/0.2e-3) * (2/(70e9*2e-3))) = sqrt(2.5e12 *
  1.4286e-8) = sqrt(35714) = 188.98 1/m (assert within 0.5),
- beta*L = 4.7245; tau_avg = 10000/(0.025*0.025) = 16 MPa (assert),
- tau_max = 16e6 * (4.7245/2)/tanh(2.3623) = 16e6*2.3623/0.9815 =
  16e6*2.4068 = 38.51 MPa (assert within 0.2 MPa),
- concentration = 2.407 (assert within 0.01),
- margin_ratio = 25/38.51 = 0.649 -> FAIL (assert pass False).
Case 2: overlap L 10 mm, allowable 25 MPa:
- beta*L = 1.8898; tau_avg = 10000/(0.025*0.010) = 40 MPa,
- tau_max = 40e6*(1.8898/2)/tanh(0.9449) = 40e6*0.9449/0.7372 =
  40e6*1.2817 = 51.27 MPa (assert within 0.3 MPa),
- margin_ratio = 0.488 -> FAIL (shorter overlap raises both average
  and peak stress; assert peak > the 25 mm case).
Case 3: allowable 45 MPa, L 25 mm -> margin_ratio = 45/38.51 = 1.169
-> PASS (assert pass True).
ValueErrors: load -1, overlap 0, E 0, allowable 0.
Keep at least 16 test methods.

## Corpus tasks (ids w27-adhesive-bonded-joints-1/2)

Distinctive tokens: adhesive bonded joint, single lap joint, shear lag
parameter, adhesive shear stress, overlap length, Volkersen shear
distribution, bondline peak stress, adhesive allowable. Avoid: bolted
joint bearing bypass net-tension shear-out (composite-bolted-joints);
laminate stiffness CLT (laminate-stiffness); ply failure criteria
(failure-criteria); CMH-17 allowables lookup (cmh17-allowables).

1. "analyze the single lap adhesive bonded joint in the composite
   structure: 10 kN load over a 25 mm overlap and 25 mm width with the
   shear lag correction, check the peak adhesive shear stress against
   the 25 MPa allowable"
2. "compute the shear lag parameter and the peak to average shear
   concentration for the bonded lap joint with the aluminum adherends
   and report the joint margin"

## SKILL body notes

Pair with composite-bolted-joints (fastener alternative in the same
pack), failure-criteria and laminate-stiffness (adherend design), and
cmh17-allowables (bonded joint data context). The Volkersen-style
single-lap shear model ignores peel and bending of the adherends;
document that peel-critical designs need a Goland-Reissner or FE
analysis. CMH-17 referenced, not reproduced.
