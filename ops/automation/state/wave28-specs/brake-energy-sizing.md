# Wave-28 leaf spec: brake-energy-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/brake-energy-sizing/
- Pack: sizing (existing siblings: landing-gear-sizing, tire-sizing,
  engine-sizing, fuel-tank-sizing, fuselage-sizing, nacelle-sizing,
  propeller-sizing, battery-sizing, control-surface-sizing,
  spoiler-sizing, tail-sizing, wing-planform-sizing, ws-tw-trade,
  ice-protection-sizing, weight-estimation)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: vehicle-design

## Claim

Size the wheel brake system of an aircraft from the kinetic energy it
must absorb: compute the rejected-takeoff (RTO) brake energy at the
decision speed and the landing-stop brake energy at the touchdown
speed, divide the total energy over the number of braked wheels,
estimate the required brake heat-sink mass from the allowable
temperature rise and the heat-sink specific heat, check the
temperature rise of the selected heat sink, and estimate the
braking distance at the design deceleration. Produces the RTO and
landing energies, the per-brake energy, the required heat-sink mass,
the temperature rise and margin, the braking distance, and the pass or
fail verdict that gate the wheel-brake sizing.

Does NOT do: compute the accelerate-stop distance or the V1 decision
speed from a flight test (flight-test-operations accelerate-stop-
distance owns the rejected-takeoff distance test); size the shock
absorber stroke or the gear loads (landing-gear-sizing); select the
tire dimensions or footprint (tire-sizing); estimate landing distance
with flare and ground roll (flight-mechanics landing-performance or
flight-test-operations landing-distance-determination).

## Model (implement exactly)

Module constants:
- G0 = 9.80665.
- CP_CARBON = 1200.0 (documented typical specific heat of a carbon
  heat sink, J/(kg K)); the material is an input with this default.
- REVERSE_THRUST_CREDIT_DEFAULT = 0.0 (fraction of RTO energy removed
  by reverse thrust; conservative default 0).

Inputs:
- mtow_kg (float), v1_m_s (float),
- mlw_kg (float, maximum landing weight), touchdown_speed_m_s (float,
  e.g. 1.23*v_sr or a direct input),
- n_braked_wheels (int),
- heat_sink_cp (float, default CP_CARBON),
- delta_t_allowable_K (float, allowable heat-sink temperature rise),
- heat_sink_mass_available_kg (float, selected heat sink per brake),
- decel_g (float, braking deceleration in g, e.g. 0.35),
- reverse_credit (float, default REVERSE_THRUST_CREDIT_DEFAULT, 0..1).

Functions:
- rto_energy_J(mtow_kg, v1_m_s) -> float: 0.5*mtow*v1^2.
  ValueError on mtow <= 0 or v1 <= 0.
- landing_energy_J(mlw_kg, touchdown_speed_m_s) -> float:
  0.5*mlw*v_td^2. ValueErrors as above.
- per_brake_energy_J(total_energy_J, n_braked_wheels,
  reverse_credit) -> float: total*(1 - reverse_credit)/n.
  ValueError on n <= 0, reverse_credit outside [0, 1].
- required_heat_sink_mass_kg(energy_per_brake_J, cp, delta_t_K) ->
  float: energy/(cp*delta_t). ValueError on cp <= 0, delta_t <= 0.
- temperature_rise_K(energy_per_brake_J, mass_kg, cp) -> float:
  energy/(mass*cp). ValueError on mass <= 0.
- braking_distance_m(v_m_s, decel_g) -> float: v^2/(2*decel_g*G0).
  ValueError on v <= 0 or decel_g <= 0.
- analyze(inputs) -> dict: E_rto, E_land, per-brake energy for the RTO
  case (governing), required mass, actual temperature rise with the
  available mass, delta_t_margin = delta_t_allowable - actual rise,
  braking distance at V1, verdict = "brake-energy-pass" when
  delta_t_margin >= 0 and required_mass <= available_mass else
  "brake-energy-fail"; also list which case governs (rto or landing).
ValueError on: n_braked_wheels <= 0, heat_sink_mass_available <= 0,
any energy input <= 0.

## Worked example

Regional transport: mtow 70000 kg, V1 = 70 m/s; mlw 58000 kg,
touchdown speed 65 m/s; 4 braked wheels; cp 1200; allowable rise
300 K; available heat sink 130 kg per brake; decel 0.35 g;
reverse credit 0.
- E_rto = 0.5*70000*4900 = 171,500,000 J (171.5 MJ, assert within
  1e3).
- E_land = 0.5*58000*4225 = 122,525,000 J (122.5 MJ, assert).
- per-brake RTO = 171.5e6/4 = 42,875,000 J (assert).
- required mass = 42.875e6/(1200*300) = 42.875e6/360000 = 119.10 kg
  (assert within 0.01).
- actual rise with 130 kg = 42.875e6/(130*1200) = 42.875e6/156000 =
  274.84 K (assert within 0.01); margin 25.16 K; required mass 119.1
  <= 130 -> verdict "brake-energy-pass".
- With heat_sink_mass_available 100 kg: rise = 357.29 K > 300 ->
  "brake-energy-fail" (assert).
- Landing case per-brake = 122.525e6/4 = 30.63 MJ -> rise 196.35 K
  (assert) -> the RTO case governs.
- braking_distance(70, 0.35) = 4900/(2*0.35*9.80665) = 4900/6.86466 =
  713.8 m (assert within 0.1).
- ValueErrors on mtow 0, v1 -5, n 0, cp 0, delta_t 0, mass 0.
Keep at least 16 test methods: both energies, per-brake division with
reverse credit (credit 0.2 case), required mass, rise and margin,
pass/fail verdicts, governing case, braking distance, ValueErrors.

## Corpus tasks (ids w28-brake-energy-sizing-1/2)

Distinctive tokens: brake energy sizing, rejected takeoff energy,
wheel brake heat sink, brake temperature rise, carbon brake mass,
braking distance at V1. Avoid: accelerate stop distance, V1 decision
speed test (flight-test-operations accelerate-stop-distance); shock
absorber stroke, gear loads (landing-gear-sizing); tire footprint,
inflation pressure (tire-sizing).

1. "size the wheel brakes from the rejected takeoff kinetic energy at
   V1: compute the per brake energy and the carbon heat sink mass for
   the allowable temperature rise"
2. "check the brake temperature rise for the landing stop and the RTO
   stop and estimate the braking distance at the design deceleration"

## SKILL body notes

Pair with landing-gear-sizing and tire-sizing (the landing gear
neighbors), accelerate-stop-distance (the flight-test rejected-takeoff
neighbor). The carbon specific heat, reverse-thrust credit, and
deceleration values are documented typical design inputs; the body must
say they are program inputs. FAR/CS-25 referenced for the brake-energy
context (paraphrase only).
