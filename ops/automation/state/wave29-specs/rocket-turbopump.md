# Wave-29 leaf spec: rocket-turbopump (propulsion, turbomachinery pack)

- Path: skills/propulsion/turbomachinery/rocket-turbopump/
- Pack: turbomachinery (existing sibling: centrifugal-compressor)
- Standards ids: ecss (reference-only; propulsion rocket-payload
  leaves carry ecss). Ledger Standard: ecss.
- Family: propulsion

## Claim

Size a liquid rocket engine turbopump at the pump level: convert the
required discharge pressure rise and propellant flow into the pump
head, compute the dimensionless specific speed from the shaft speed,
flow, and head, estimate the impeller tip speed and diameter from the
head coefficient, compute the pump power from the flow and pressure
rise at the pump efficiency, assess the suction performance with the
available net positive suction head and the suction specific speed,
and judge the cavitation margin. Produces the head, specific speed,
tip speed, impeller diameter, pump power, NPSH, suction specific
speed, and the cavitation verdict that gate a turbopump design review.

Does NOT do: compare rocket engine feed cycles or compute cycle-level
pump discharge pressure and pump power (rocket-engine-cycle owns the
cycle power balance and chooses the pump-fed architecture); analyze
axial or centrifugal air compressor stages (axial-compressor and
centrifugal-compressor leaves own air compressor velocity triangles
and maps); design turbine stages (turbine-stage and turbine-blade-
cooling own turbine aerodynamics and cooling). This leaf sizes the
pump inside a rocket engine turbopump: head, geometry, power,
cavitation.

## Model (implement exactly)

Module constants:
- G0 = 9.80665 (m/s2).
- PSI_DESIGN = 0.55 (design head coefficient for a centrifugal pump
  impeller, module constant).
- S_CRIT = 3.0 (dimensionless suction specific speed limit for the
  cavitation verdict).

Functions (pure stdlib, floats):
- omega_from_rpm(rpm) -> float: omega = 2 pi rpm / 60. ValueError on
  rpm <= 0.
- head_rise_m(pressure_rise, density) -> float:
  H = pressure_rise / (density * G0). ValueError on pressure_rise <= 0
  or density <= 0.
- specific_speed(omega, volume_flow, head_m) -> float:
  N_s = omega * sqrt(volume_flow) / (G0 * head_m)**0.75
  (dimensionless). ValueError on volume_flow <= 0 or head_m <= 0.
- impeller_tip_speed(head_m, psi=PSI_DESIGN) -> float:
  u2 = sqrt(G0 * head_m / psi). ValueError on psi <= 0.
- impeller_diameter(tip_speed, omega) -> float:
  D = 2 * tip_speed / omega. ValueError on omega <= 0.
- pump_power(volume_flow, pressure_rise, efficiency) -> float:
  P = volume_flow * pressure_rise / efficiency. ValueError on
  efficiency not in (0, 1].
- npsh_available(inlet_pressure, vapor_pressure, density) -> float:
  NPSH = (inlet_pressure - vapor_pressure) / (density * G0). ValueError
  if inlet_pressure <= vapor_pressure.
- suction_specific_speed(omega, volume_flow, npsh_m) -> float:
  S = omega * sqrt(volume_flow) / (G0 * npsh_m)**0.75. ValueError on
  npsh_m <= 0.
- cavitation_verdict(suction_specific_speed_value,
  s_crit=S_CRIT) -> str: "acceptable" if >= s_crit else
  "cavitation-risk".
- size_pump(rpm, volume_flow, pressure_rise, density, efficiency,
  inlet_pressure, vapor_pressure) -> dict: convenience chain returning
  {omega, head_m, specific_speed, tip_speed_ms, diameter_m,
  power_W, npsh_m, suction_specific_speed, verdict}. ValueErrors
  propagate.

## Worked example

LOX pump: rpm 18000, volume flow 0.04 m3/s, pressure rise 10 MPa,
density 1141 kg/m3, efficiency 0.68, inlet pressure 0.5 MPa, vapor
pressure 0.03 MPa.

Deterministic anchors (compute with the exact formulas; assert within
the stated tolerances):
- omega = 1884.96 rad/s (within 0.1).
- head_rise_m(10e6, 1141) = 893.70 m (within 0.1).
- specific_speed(1884.96, 0.04, 893.70) = 0.4162 (within 0.001).
- impeller_tip_speed(893.70, 0.55) = 126.23 m/s (within 0.1).
- impeller_diameter(126.23, 1884.96) = 0.1339 m (within 0.001).
- pump_power(0.04, 10e6, 0.68) = 588235 W (within 10), about 588 kW.
- npsh_available(0.5e6, 0.03e6, 1141) = 42.00 m (within 0.01).
- suction_specific_speed(1884.96, 0.04, 42.00) = 4.123 (within
  0.01), verdict "acceptable" (>= 3.0).
- A second case: raise vapor pressure to 0.2 MPa (warmer fluid),
  NPSH = 26.35 m, S = 3.00 (compute exact value; assert the verdict
  flips to "cavitation-risk" when S drops below 3.0, e.g. inlet 0.35
  MPa gives NPSH 11.74 m, S around 1.9).
- Round-trip: head_rise_m and npsh_available are linear in their
  pressure differences.
- ValueErrors: rpm 0, flow 0, pressure_rise 0, density 0, efficiency
  0/1.2, inlet below vapor pressure.

Keep at least 16 test methods: omega conversion, head anchor, specific
speed anchor, tip speed anchor, diameter anchor, power anchor, NPSH
anchor, suction specific speed anchor, verdict flip, round-trip
linearity, ValueErrors.

## Corpus tasks (ids w29-rocket-turbopump-1/2)

Distinctive tokens: rocket turbopump, pump specific speed, suction
specific speed, net positive suction head, impeller tip speed, LOX
pump sizing, cavitation margin. Avoid: feed cycle selection,
gas-generator cycle, staged combustion, pump discharge pressure at
cycle level (rocket-engine-cycle); compressor velocity triangles,
slip factor, de Haller (centrifugal-compressor); turbine stage
design (turbine-stage).

1. "size the LOX turbopump impeller for a liquid rocket engine: head
   893 m at 18000 rpm and 0.04 m3/s, compute specific speed, tip
   speed, diameter, and pump power at 68 percent efficiency"
2. "check the cavitation margin of a rocket turbopump from the
   available net positive suction head and the suction specific speed
   limit"

## SKILL body notes

Pair with rocket-engine-cycle (defines the discharge pressure and flow
this pump must deliver), centrifugal-compressor (the sibling
turbomachinery design method for air), turbine-stage (the drive
turbine on the same shaft). State the boundary: the cycle leaf owns
power balance and architecture; this leaf owns pump geometry,
efficiency bookkeeping, and cavitation. ecss is reference-only. Mirror
the turbomachinery pack SKILL body style (SI units, stdlib only,
deterministic offline).
