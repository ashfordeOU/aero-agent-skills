# Wave-26 leaf spec: leak-testing (manufacturing-quality, ndt pack)

- Path: skills/manufacturing-quality/ndt/leak-testing/
- Pack: ndt (existing siblings: the nine method leaves plus
  ndt-method-selection)
- Standards ids: as9100  (Ledger Standard: as9100)
- Family: manufacturing-quality

## Claim

Plan and evaluate a leak test on an aerospace part or system (fuel
tank, accumulator, valve, sealed enclosure): compute the leak rate
from a pressure decay or vacuum decay measurement, size the test time
needed to detect a target leak with a stated gauge resolution, convert
a measured helium leak to the equivalent air leak and back, translate
an immersion bubble observation into a leak rate, recommend the leak
test method (pressure decay, vacuum decay, bubble, helium mass
spectrometer sniffer or hood) from the required sensitivity and access,
and disposition the part against the maximum allowable leak rate.
Produces the measured or computed leak rate, the method
recommendation, and the accept/reject verdict that gate the leak test
under an approved procedure.

Does NOT do: pick among the classic volumetric NDT methods
(ndt-method-selection owns RT/UT/ET/PT/MT screening and does not list
leak testing), detect material discontinuities inside a solid part
(method siblings), or qualify the pressure vessel design
(structures/vehicle leaves own pressure vessel sizing). This leaf is
the leak-rate measurement math and method screening.

## Model (implement exactly)

Units and conversions (module constants):
- M_HE = 4.003, M_AIR = 28.97 (g/mol) for the molecular-flow helium
  to air conversion Q_air = Q_he * sqrt(M_HE / M_AIR) (documented
  typical molecular-flow relation; viscous-flow conversion is closer
  to the viscosity ratio, documented in the SKILL body as a note).
- STD_TEMP_K = 293.15 (standard condition for scc).
- HELIUM_MS_MIN_DETECT_SCCS = 1e-9 (typical helium mass spectrometer
  sensitivity in scc/s He, documented typical).
- GAS_CONVERSION = sqrt(M_HE / M_AIR) (module computed).
Functions:
- pressure_decay_rate(volume_L, dP_bar, time_s, temp_K=293.15) ->
  scc/s at standard temperature: dP in bar converted to atm
  (1 bar = 0.986923 atm, module constant BAR_TO_ATM), volume in L
  converted to cc (*1000), q = V_cc * dP_atm / time_s * (STD_TEMP_K /
  temp_K); ValueError on volume <= 0, dP < 0, time <= 0, temp <= 0.
- vacuum_decay_rate(chamber_volume_L, dP_bar, time_s, temp_K) same
  math (one shared helper with a different name for the SKILL
  vocabulary).
- gauge_resolution_time(volume_L, gauge_res_bar, target_sccs,
  temp_K=293.15) -> seconds needed so that the target leak produces a
  pressure drop above the gauge resolution: t = V_cc * dP_atm /
  target (invert the decay equation); ValueError on target <= 0.
- helium_to_air(q_he_sccs) -> q_air = q_he * sqrt(M_HE / M_AIR)
  (molecular flow); air_to_helium(q_air) -> q_he = q_air /
  sqrt(M_HE / M_AIR); round-trip identity in the tests.
- bubble_leak_rate(bubble_diameter_mm, bubbles_per_s) -> scc/s:
  per-bubble volume = (4/3) * pi * (d/2)^3 in cc (d in cm), rate =
  volume * bubbles_per_s; ValueError on negative inputs.
- method_recommendation(required_sensitivity_sccs, access_both_sides
  (bool), need_localization (bool), part_pressure_capable (bool)) ->
  (method, rationale): helium mass spectrometer hood when
  required_sensitivity_sccs <= 1e-6 (module constant MS_THRESHOLD =
  1e-6); helium sniffer when need_localization and sensitivity <= 1e-5
  (module constant SNIFFER_THRESHOLD = 1e-5); pressure or vacuum decay
  when access_both_sides False and part_pressure_capable; bubble
  (immersion) when need_localization and sensitivity <= 1e-2 (module
  constant BUBBLE_THRESHOLD = 1e-2); else pressure decay. Deterministic
  priority order implemented in one function with the module
  thresholds.
- disposition(measured_sccs, max_allowable_sccs, method) -> dict
  {verdict (accept/reject/review), margin_db}: accept when measured <=
  max_allowable; reject when measured > max_allowable and the ratio
  exceeds 1.25 (module constant REVIEW_RATIO = 1.25); review in the
  band in between; margin_db = 10 * log10(max_allowable / measured)
  (positive when accept); ValueError on non-positive allowables.
- helium_ms_verdict(detected_sccs_he, limit_sccs_air) -> converts the
  detected helium leak to air-equivalent and dispositions (uses
  helium_to_air and disposition).
- summarize(...) -> dict for the SKILL worked example.
ValueError on: volume <= 0, time <= 0, temp <= 0, negative dP,
non-positive allowables or targets, unknown method strings.

## Worked example

1. pressure_decay_rate(volume 50 L, dP 0.02 bar, time 600 s): q =
   50000 cc * 0.019738 atm / 600 = 1.645 scc/s (assert the module
   value within 1e-6, temperature 293.15 gives no correction).
2. gauge_resolution_time(50 L, gauge_res 0.001 bar, target 0.05
   scc/s): t = 50000 * 0.0009869 / 0.05 = 986.9 s (assert the module
   value within 1e-3).
3. helium_to_air(1.0) = sqrt(4.003 / 28.97) = 0.3717 scc/s air
   (assert within 1e-6); air_to_helium(helium_to_air(x)) ~ x within
   1e-12.
4. bubble_leak_rate(3.0 mm diameter, 1.0 bubble/s): per bubble
   volume = (4/3) pi (0.15 cm)^3 = 0.01414 cc -> 0.01414 scc/s
   (assert within 1e-6).
5. method_recommendation(1e-8, True, False, True) -> helium hood;
   (1e-4, True, True, True) -> helium sniffer (1e-4 <= 1e-5? no:
   1e-4 > 1e-5 so sniffer requires <= 1e-5; re-check: with 1e-4,
   need_localization True -> sniffer threshold fails, bubble threshold
   1e-2 passes -> bubble (immersion); craft the worked example to
   exercise each branch with clearly separated sensitivities).
6. disposition(1.0, 2.0, "pressure-decay") -> accept margin_db
   3.01; disposition(3.0, 2.0, "pressure-decay") -> reject;
   disposition(2.4, 2.0) -> review (ratio 1.2 within the band).
7. helium_ms_verdict(detected 1e-8 scc/s He, limit 1e-8 scc/s air):
   air-equivalent 3.7e-9 <= limit -> accept.
8. ValueError on time 0 and on volume -1.
Keep at least 18 test methods (decay rates, resolution time,
helium-air conversions and round trip, bubble geometry, method
recommendation branches, disposition bands, ValueErrors).

## Corpus tasks (ids w26-leak-testing-1/2)

Distinctive tokens: leak testing, pressure decay, vacuum decay, helium
mass spectrometer, sniffer test, bubble test, leak rate, scc per
second, helium to air conversion, gauge resolution, maximum allowable
leak. Avoid: ultrasonic / eddy current / radiography method screening
(ndt-method-selection), radiograph / penetrant method names
(siblings), structural pressure vessel design (other families).

1. "compute the leak rate of the 50 liter fuel tank from the pressure
   decay test: 0.02 bar drop in 600 seconds, then disposition the part
   against the 2 scc per second maximum allowable leak rate"
2. "recommend the leak test method for the sealed valve that needs
   1e-8 scc per second sensitivity and convert the measured helium
   mass spectrometer reading to the air equivalent leak rate for the
   acceptance check"

## SKILL body notes

Pair with ndt-method-selection (where leak testing is beyond the five
listed methods), the as9100 calibration-control leaf (gauge
resolution), and the manufacturing-quality risk-management leaf.
Helium-air conversion and sensitivity thresholds are documented as
typical values in the module constants; the approved procedure
governs the real acceptance criteria. Standards referenced not
reproduced.
