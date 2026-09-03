# Wave-25 leaf spec: radio-frequency-emissions (avionics, do160 pack)

- Path: skills/avionics/do160/radio-frequency-emissions/
- Pack: do160 (existing: power-input, environmental-qualification,
  electrostatic-discharge, lightning-protection, radio-frequency-
  susceptibility). NOTE: RF susceptibility (section 20) is a SIBLING,
  not the same leaf. This leaf is DO-160 section 21 emissions.
- Standards ids: do-160  (Ledger Standard: do-160)
- Family: avionics

## Claim

Plan and check the DO-160 section 21 radio frequency emission test
(conducted emissions CE102 and radiated emissions RE102) of airborne
equipment: classify the equipment installation category and the emission
limit class, convert the measured conducted emission amplitude into the
dBuV scale and the radiated emission into dBuV/m at the antenna, apply
the limit line of the applicable category, compute the emission margin
at each frequency, and judge the equipment against the CE102 and RE102
limit curves (paraphrased reference-only, never reproduce the RTCA
tables verbatim). Produces the emission margin, the worst-case frequency,
and the pass or fail verdict that gate the DO-160 EMC qualification.

Does NOT do: immunity/susceptibility testing (section 20, the RF
susceptibility sibling owns radiated and conducted immunity levels,
amplifier power sizing, CS114 current limits), power input sag/surge
(section 16, power-input), lightning (sections 22/23, lightning-
protection), ESD (section 25), or environment test matrix mapping
(environmental-qualification). This leaf is strictly the equipment
emission side (section 21) with limit/margin computation.

## Model (implement exactly)

Reference data (paraphrased reference-only typical limits, mark them as
reference-only and NOT the normative RTCA table; the SKILL must say the
normative limits come from the current DO-160 revision):

- Conducted emissions CE102: limit roughly 60-80 dBuV over 10 kHz to
  10 MHz band with category-based curve (simplified piecewise constant
  band model in the logic with module constants; e.g. 10 kHz-100 kHz 78
  dBuV, 100 kHz-2 MHz 60 dBuV, 2-10 MHz 70 dBuV as a representative
  curve, clearly labeled reference-only typical).
- Radiated emissions RE102: limit roughly 24-54 dBuV/m over 2 MHz to
  18 GHz depending on the installation category (A: 24 dBuV/m floor,
  B: 34 dBuV/m floor, etc. representative values, reference-only).
- dBuV conversion: dBuV = 20*log10(V_uV), amplitude in volts to uV.
- dBuV/m conversion from field measurement: dBuV/m = 20*log10(E_uV/m);
  E (V/m) = sqrt(30*P_erp)/d style inverse-square sanity check when an
  antenna is characterized (same equation family as RF susceptibility
  but used to sanity-check the source, not to size an immunity amplifier).
- Margin: margin_db = limit_db - measured_db at each frequency;
  negative margin is a fail.
- Worst case: frequency of the minimum margin and its value.
- Verdict: pass if min margin >= 0 with a recommended margin band
  (>= 6 dB typical recommended, reference-only; do not encode as a hard
  RTCA requirement).
Functions:
- dbu_v_from_volts(v) and volts_from_dbu_v(dbu)
- dbu_v_per_m_from_v_per_m(vpm)
- ce102_limit_db(freq_hz, category) -> limit
- re102_limit_db(freq_hz, category) -> limit
- conducted_emission_margin(measured_dbu, limit_dbu) -> margin
- radiated_emission_margin(measured_dbu_vpm, limit_dbu_vpm) -> margin
- worst_case_frequency(freqs, margins) -> (freq, margin)
- emission_verdict(margins, freq_hz, category, kind) -> dict
  (pass/fail, worst margin, worst frequency, category)
ValueError on: negative frequency, negative measured amplitude,
category not in the supported set, empty arrays.

## Worked example

Equipment category A (representative) measured conducted emission 72 dBuV
at 150 kHz -> compare to the reference CE102 limit curve at 150 kHz,
margin = limit - 72; radiated emission 40 dBuV/m at 100 MHz vs RE102
category A limit at 100 MHz. Assert the exact margins and the pass/fail
verdict from your module.

## Corpus tasks (ids w25-radio-frequency-emissions-1/2)

Distinctive tokens: DO-160 section 21, radio frequency emissions,
conducted emissions, radiated emissions, CE102, RE102, emission limit,
emission margin, dBuV, dBuV/m, EMC qualification. Avoid: susceptibility,
immunity, RS103, CS114, amplifier power budget, sag/surge, lightning,
ESD (those belong to the susceptibility/power/lightning siblings).

1. "check the equipment radiated emission against the DO-160 RE102
   category A limit at 100 MHz and compute the emission margin in
   dBuV/m for the EMC qualification"
2. "reduce the conducted emission sweep to the CE102 limit curve and
   find the worst case frequency and margin across the band"

## SKILL body notes

Pair with radio-frequency-susceptibility (immunity counterpart),
electrostatic-discharge, lightning-protection. Worked example uses
module constants and real outputs. Compliance: DO-160 section 21
referenced by name; limits paraphrased as reference-only typical values
with an explicit statement that the normative limits come from the
current RTCA/DO-160 revision; no reproduced tables.
