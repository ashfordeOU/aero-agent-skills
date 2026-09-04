# Wave-37 leaf spec: electrical-wire-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/electrical-wire-sizing/
- Pack: sizing. Closest siblings: aircraft-electrical-load-analysis
  (computes the load ROLLUP - amps per bus - not conductor sizing),
  battery-sizing (pack energy/cell count with an internal branch
  voltage-drop check of the PACK circuit, not wire run sizing),
  avionics-bay-cooling-sizing (thermal), manufacturing-quality/assembly/
  ewis-installation-quality (EWIS INSTALLATION quality inspection, not
  sizing). Whole-tree grep: "ampacity", "voltage drop" wire-run context,
  "wire gauge" have no owning sizing leaf (battery-sizing's voltage drop
  is the pack branch drop; EWIS is install quality). ZERO owners of
  conductor sizing. GENUINE VD gap (fresh probe; wave-36 VD receipt did
  not cover the electrical distribution sub-piece).
- Standards id: far-25 (reference-only; EWIS certification context
  Part 25 Subpart H). Body names AS50881/SAE AS50881 derating by name
  only, no verbatim tables. Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size an aircraft electrical power feeder or wire run: select the
smallest conductor gauge whose bundled ampacity at the ambient
temperature meets the continuous load with the required derating, check
the voltage drop over the run length at the load current against the
bus tolerance, compute the percentage drop, and produce the selected
gauge, its ampacity margin, the voltage drop, and the percent-drop
verdict. Produces the gauge selection and drop verdict that close the
load-to-distribution sizing chain. Does NOT do: aircraft electrical
load rollup (aircraft-electrical-load-analysis); battery pack cell
layout (battery-sizing); EWIS installation and inspection quality
(ewis-installation-quality); avionics thermal management (avionics-bay-
cooling-sizing).

## Model (implement exactly)

Module constants (documented compact reference data, copper conductor):
- AMPACITY_TABLE = {gauge: base_ampacity_free_air_30C} for gauges
  "22".."6": {"22": 5.0, "20": 7.5, "18": 10.0, "16": 13.0, "14": 17.0,
  "12": 23.0, "10": 33.0, "8": 46.0, "6": 60.0} (A)
- AREA_MM2 = {"22": 0.324, "20": 0.519, "18": 0.823, "16": 1.31,
  "14": 2.08, "12": 3.31, "10": 5.26, "8": 8.37, "6": 13.3}
- BUNDLE_DERATE = 0.60 (bundle of 5+ wires, documented model constant)
- TEMP_DERATE = 0.94 (45 C ambient, documented model constant)
- RESISTIVITY_COPPER = 1.72e-8 (ohm m at 20 C) with
- TEMP_COEFFICIENT = 0.00393 (1/C) for the resistance at the operating
  temperature.
- MAX_PERCENT_DROP = 3.0 (percent, bus tolerance for the run)

Functions (pure stdlib):
- ampacity(gauge, ambient_c) -> A = base * BUNDLE_DERATE *
 TEMP_DERATE_at_ambient where TEMP_DERATE_at_ambient = 1.0 at 30 C and
 decreases 0.006 per C above 30 (documented linear model:
 1.0 - 0.006 * (ambient_c - 30), floored at 0.5). ValueError
  unknown gauge or ambient < 30 or ambient > 100.
- select_gauge(load_current, ambient_c) -> str: smallest gauge (from
  "22" up to "6") whose ampacity >= load_current; ValueError if load
  current exceeds the "6" gauge ampacity (beyond the table) or load <= 0.
- resistance_per_meter(gauge, temp_c) -> ohm/m = RESISTIVITY_COPPER *
  (1 + TEMP_COEFFICIENT * (temp_c - 20)) / (AREA_MM2[gauge] * 1e-6).
- voltage_drop(load_current, length_m, gauge, temp_c) -> V =
  2 * length_m * load_current * resistance_per_meter(gauge, temp_c)
  (round trip). ValueErrors: negative length/current.
- percent_drop(voltage_drop, bus_voltage) -> float. ValueError:
  bus_voltage <= 0.
- wire_size_review(load_current, length_m, bus_voltage, ambient_c,
  temp_c) -> dict {gauge, ampacity, margin_A, voltage_drop_V,
  percent_drop, verdict: "pass" if percent <= MAX_PERCENT_DROP else
  "fail"}.

Identity to test: select_gauge returns the smallest gauge with ampacity
>= load; voltage_drop doubles when the run length doubles; percent_drop
= 100 * drop / bus_voltage.

## Worked example

Load 25 A continuous, run 10 m, bus 28 V DC, ambient 45 C, conductor
temp 45 C. Ampacity(10) at 45 C = 33 * 0.60 * (1 - 0.006*15) = 33*0.60*
0.91 = 18.0 A (not enough); gauge 8: 46*0.60*0.91 = 25.1 A (enough) ->
select_gauge = "8". resistance_per_meter("8", 45) = 1.72e-8 * (1 +
0.00393*25) / (8.37e-6) = 1.72e-8 * 1.09825 / 8.37e-6 = 2.257e-3 ohm/m.
voltage_drop(25, 10, "8", 45) = 2*10*25*2.257e-3 = 1.128 V; percent_drop
= 4.03% -> fail at 3% -> try gauge 6: ampacity 60*0.60*0.91 = 32.8 A;
resistance 2.257e-3 * (8.37/13.3) = 1.420e-3; drop = 2*10*25*1.420e-3 =
0.710 V; percent 2.54% -> pass.
Run your module and take the real outputs as assert targets; the anchors
above (ampacity 18.0 / 25.1 / 32.8 A; drop 1.128 / 0.710 V) are bounds
independently verified at prep (resistance per meter for 8 AWG within
5%: 2.257e-3 ohm/m is the model anchor).

## Validation list (contract test must include)

- ValueError: unknown gauge; load <= 0 or beyond the table; negative
  length; bus_voltage <= 0; ambient outside the model band.
- select_gauge truth table: 5 A -> smallest gauge meeting 5 A at 30 C;
  25 A at 45 C -> "8" or "6" per the anchor review; > "6" capacity
  raises.
- Ampacity anchors at 45 C: 18.0 (10 AWG), 25.1 (8 AWG), 32.8 (6 AWG)
  within 0.2 A.
- Voltage-drop anchors 1.128 V / 0.710 V within 0.05 V.
- Identity: doubling length doubles drop; percent = 100*drop/bus.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave37-electrical-wire-sizing.yaml)

Query 1 (copy verbatim):
  "select the electrical-wire-sizing gauge from ampacity derating for an aircraft power feeder at the load current"
  intent: "vehicle-design; wire gauge selection by derated ampacity"
  expected_skill: "vehicle-design/sizing/electrical-wire-sizing"
Query 2 (copy verbatim):
  "check the electrical-wire-sizing voltage drop and percent drop over the run length against the bus tolerance"
  intent: "vehicle-design; wire run voltage drop verdict"
  expected_skill: "vehicle-design/sizing/electrical-wire-sizing"
Task ids: w37-electrical-wire-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size an aircraft electrical
wire run:" and include the outputs in the Claim. First tag:
electrical-wire-sizing. Additional tags ONLY: conductor-ampacity,
wire-voltage-drop, bus-tolerance-verdict, ewis-conductor-selection,
ampacity-derating. NEVER single generic words (wire, cable, electrical,
current, voltage, gauge). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): electrical load analysis,
bus load rollup (aircraft-electrical-load-analysis); pack energy,
C-rate (battery-sizing); EWIS installation inspection, fastener
(ewis-installation-quality).
