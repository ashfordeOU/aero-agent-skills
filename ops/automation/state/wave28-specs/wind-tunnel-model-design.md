# Wave-28 leaf spec: wind-tunnel-model-design (aerodynamics, wind-tunnel pack)

- Path: skills/aerodynamics/wind-tunnel/wind-tunnel-model-design/
- Pack: wind-tunnel (existing siblings: windtunnel-data-reduction,
  windtunnel-wall-corrections)
- Standards ids: naca-tr-824  (Ledger Standard: naca-tr-824)
- Family: aerodynamics

## Claim

Design the scale model and the test setup for a wind tunnel campaign
on an aircraft configuration: select the model scale from the test
section blockage limit and the span clearance, compute the model
reference dimensions, check the Reynolds-number capability of the
tunnel against the full-scale flight condition and report the
Reynolds mismatch, estimate the aerodynamic loads the model will put
on the balance at the maximum test dynamic pressure, rate the balance
against those loads, and size the model support sting for the bending
moment. Produces the chosen scale, the model wing area and chord, the
blockage ratio, the Reynolds ratio, the load margin verdict, and the
sting diameter that gate the wind tunnel model design.

Does NOT do: reduce balance and pressure measurements into
coefficients or apply tare and blockage corrections after the test
(windtunnel-data-reduction); apply closed-wall wall corrections to
measured coefficients (windtunnel-wall-corrections); generate a CFD
mesh (cfd-mesh-generation); plan the data-reduction campaign or the
test-point matrix (flight-test-operations planning siblings are for
flight test, not wind tunnel).

## Model (implement exactly)

Module constants:
- BLOCKAGE_MAX = 0.05 (default maximum model-to-test-section area
  ratio, documented typical),
- SPAN_CLEARANCE = 0.8 (fraction of the test section width available
  to the model span, documented typical),
- STING_ALLOWABLE_STRESS_PA = 800.0e6 (default steel sting allowable,
  input),
- MU_AIR = 1.789e-5 (kg/(m s), sea level dynamic viscosity),
- RHO_SL = 1.225, G0 = 9.80665.

Inputs:
- test_section_width_m, test_section_height_m (or area directly),
- full_span_m (full-scale wing span),
- full_wing_area_m2 (full-scale reference area),
- full_mac_m (full-scale mean aerodynamic chord),
- full_reynolds (full-scale flight Reynolds number, e.g. based on the
  MAC),
- tunnel_max_speed_m_s,
- max_test_cl (float, default 1.4; the maximum lift coefficient the
  model will reach),
- balance_capacity_N (float),
- sting_arm_m (float, model quarter chord to the sting mount
  distance),
- sting_allowable_stress_pa (float, default
  STING_ALLOWABLE_STRESS_PA),
- blockage_max (float, default BLOCKAGE_MAX).

Functions:
- test_section_area(width, height) -> float: width*height.
  ValueError on width <= 0 or height <= 0.
- scale_from_blockage(test_area, full_wing_area, blockage_max) ->
  float: sqrt(blockage_max*test_area/full_wing_area).
- scale_from_span(test_width, full_span, clearance) -> float:
  (test_width*clearance)/full_span.
- choose_scale(test_area, full_wing_area, test_width, full_span,
  blockage_max, clearance) -> dict: lambda_blockage,
  lambda_span, scale = min of the two, model_wing_area =
  full_wing_area*scale^2, model_mac = full_mac*scale, model_span =
  full_span*scale, blockage_ratio = model_wing_area/test_area,
  blocked_ok (bool). ValueError on any non-positive dimension.
- reynolds_model(tunnel_speed, model_mac, rho=RHO_SL, mu=MU_AIR) ->
  float: rho*V*model_mac/mu.
- reynolds_ratio(model_re, full_re) -> float: model_re/full_re.
- model_load_N(q, model_wing_area, cl) -> float: q*S*cl.
- balance_verdict(load_N, capacity_N) -> str: "balance-ok" when
  load <= capacity else "balance-overload".
- sting_diameter_m(bending_moment_Nm, allowable_pa) -> float:
  (32*M/(pi*allowable))^(1/3). ValueError on M <= 0.
- analyze(inputs) -> dict: scale selection, model dimensions,
  blockage, model Reynolds at the max tunnel speed, Reynolds ratio to
  the full-scale flight condition, max dynamic pressure q = 0.5*rho*
  Vmax^2, model load at max_test_cl, balance verdict, sting diameter
  for the bending moment load*arm, and a reynolds_limitation string
  ("reynolds-matched" when ratio >= 0.5, "reynolds-mismatch" when
  below; engineering flag, not a pass/fail gate).
ValueError on: any dimension <= 0, full_reynolds <= 0,
tunnel_max_speed <= 0, balance_capacity <= 0, sting_arm <= 0.

## Worked example

Test section 2.44 m x 2.44 m (area 5.9536 m2). Full-scale transport:
span 34.0 m, wing area 122.6 m2, MAC 4.2 m, full Re 3.0e7. Tunnel max
speed 80 m/s. max_test_cl 1.4, balance capacity 5000 N, sting arm
0.35 m, sting allowable 800 MPa.
- scale_from_blockage = sqrt(0.05*5.9536/122.6) = sqrt(0.002428) =
  0.04927 (assert within 1e-4).
- scale_from_span = (2.44*0.8)/34.0 = 1.952/34 = 0.05741 (assert).
- scale = 0.04927; model wing area = 122.6*0.0024275 = 0.29761 m2
  (assert within 1e-4); model MAC = 4.2*0.04927 = 0.20693 m; model
  span = 34*0.04927 = 1.6752 m (assert).
- blockage_ratio = 0.29761/5.9536 = 0.04999 (assert within 1e-4),
  blocked_ok True.
- model Re at 80 m/s = 1.225*80*0.20693/1.789e-5 = 20.28/1.789e-5 =
  1.1337e6 (assert within 1e3). reynolds_ratio = 1.1337e6/3.0e7 =
  0.03779 -> "reynolds-mismatch" (assert).
- q = 0.5*1.225*6400 = 3920 Pa. load = 3920*0.29761*1.4 = 1633.3 N
  (assert within 1 N) -> balance_ok.
- sting bending moment = 1633.3*0.35 = 571.7 N m; diameter =
  (32*571.7/(pi*800e6))^(1/3) = (18293/2.5133e9)^(1/3) =
  (7.2786e-6)^(1/3) = 0.01938 m = 19.38 mm (assert within 0.01 mm).
- Balance overload case: balance_capacity 1000 N -> verdict
  "balance-overload".
- ValueErrors on zero width, zero balance capacity, zero full_re.
Keep at least 16 test methods: section area, blockage scale, span
scale, min selection, model dimensions, blockage ratio, Re model and
ratio, load, balance verdicts, sting diameter, analyze summary,
ValueErrors.

## Corpus tasks (ids w28-wind-tunnel-model-design-1/2)

Distinctive tokens: wind tunnel model design, model scale selection,
blockage ratio, Reynolds mismatch, force balance rating, sting sizing,
test section. Avoid: wall corrections, solid blockage correction,
buoyancy drag increment (windtunnel-wall-corrections); tare, wake
blockage correction, coefficient reduction (windtunnel-data-reduction);
mesh generation (cfd-mesh-generation).

1. "select the wind tunnel model scale for the transport from the test
   section blockage limit and check the Reynolds number capability
   against the full scale flight condition"
2. "size the wind tunnel test setup: rate the force balance for the
   model loads at the maximum test speed and size the model support
   sting"

## SKILL body notes

Pair with windtunnel-data-reduction and windtunnel-wall-corrections
(the post-test siblings; this leaf is the pre-test design step).
Blockage limit, span clearance, and sting allowable stress are
documented typical values; body must say they are program/test
specific inputs. NACA TR-824 referenced (name only) for the
compressible-flow data context.
