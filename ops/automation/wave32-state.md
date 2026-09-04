# Wave-32 state notes (draft, filled at close)

- 2026-09-04 WAVE-32 ... (close summary appended at close)

## Family probes and receipts (recorded during prep, ~09:30-10:00 UTC)

- BASELINE verified at start: local HEAD a024d930 (brief commit), remote
  main == 751dfb5d via ls-remote, tree clean. 427 leaves + 12 routers =
  439 SKILL.md tracked; ratings ledger 427 rows; corpus 868 tasks;
  standards-map 30 ids. make validate PASS 5/5 (868/868 Hit@1) at HEAD
  before any wave work.

- SES 33 FRESH receipt: re-enumerated all 33 leaves (arp4754a 8, arp4761a
  11, certification 4, continued-airworthiness 2, mbse 6, requirements 1,
  safety-case 1) and grepped candidate-topic ownership: safety objective
  (FHA/DAL/ELOS/in-service), hazard log and risk index (O&SHA owns the
  scored hazard register and flags critical tasks), common mode and zonal
  (CCA/ZSA/PSSA), operating and support (O&SHA). No clean non-overlapping
  gap found. SES remains saturated; slots shifted to next families.

- VD 33 FRESH receipt: re-enumerated all 33 leaves (conceptual 5,
  cost-estimation 3, mass-properties 3, mdo 3, sizing 17,
  structures-integration 2). Candidate-topic grep: propeller (propeller-
  sizing + nacelle), battery (battery-sizing), landing gear (landing-gear-
  sizing + tire-sizing + brake-energy-sizing), ice protection
  (ice-protection-sizing), fuel tank (fuel-tank-sizing + wing-planform),
  wing box (wing-box-sizing), empennage (tail-sizing + canard-sizing),
  mass budget (mass-budget). Every canonical topic owned. No clean gap.

- PROP 34 FRESH re-probe: 10 packs enumerated (axial-compressor 5,
  combustion 1, electric 3, engine-airframe 1, gas-turbine-cycle 5,
  ramjet 2, rocket 10, turbofan 3, turbomachinery 2, turboprop 2). Wave-31
  dense receipt holds; scramjet remains declined (Rayleigh/thermal-choke
  receipt). No genuine non-overlapping gap this wave.

- AERO 35: wave-31 same-morning dense receipt verified against the live
  fence (35 leaves: high-lift owns slat/Krueger, flutter owns Theodorsen,
  ground-effect owns the wing case; high-speed/wind-tunnel/aeroelasticity
  packs saturated). AERO unchanged.

- CC: airspeed-conversion chain probe (NEW this wave): no leaf owns the
  full CAS/EAS/TAS/Mach airspeed conversion set with compressibility
  corrections; unit-conversion owns unit factors and Mach from TAS only,
  isa-atmosphere owns the atmosphere at altitude, FTO leaves use
  piecewise conversions inside flight-test reductions. Genuine gap in
  cross-cutting/units-atmos: calibrated-equivalent-true-airspeed
  conversion (position error is FTO-owned; the pure air-data chain is
  not). [pending probe confirmation]

- FM rotorcraft probe: hover owns figure of merit at design point, FTO
  rotorcraft owns measured FM; NO content anywhere on rotorcraft
  autorotative descent (spin-recovery/deep-stall autorotation is
  fixed-wing post-stall), Lock number, blade flapping, coning angle,
  ground resonance, rotor tip Mach / advance ratio as outputs. Rotorcraft
  autorotation EMPIRICAL model per the wave-32 brief re-open is a genuine
  candidate if pinnable to textbook coefficients; blade dynamics and
  ground resonance have zero ownership but need deterministic stdlib
  defensibility. [pending probe confirmation]

- STRUCT: wave-31 dense receipt holds (continuous-turbulence +
  stiffener-crippling declined on empirical/spectral grounds); only a
  clean deterministic gap would be taken. [pending probe]

- AV/FTO/GNC/SPACE/MQ: probe subagents dispatched 2026-09-04 ~09:40 UTC;
  receipts appended when they return.

## Deviations / disclosures (filled at close)

## Lessons (filled at close)
