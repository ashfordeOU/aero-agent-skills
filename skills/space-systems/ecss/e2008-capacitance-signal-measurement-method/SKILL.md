---
name: e2008-capacitance-signal-measurement-method
description: "Use when a cell capacitance run reaches for a current transformer or a probe, or nobody sized the shunt it already has. Evaluate the signal acquisition path of a solar cell capacitance measurement against ECSS-E-ST-20-08C clause 11.1.2, which prefers the shunt: size the sensing burden against the cell reactance at the test frequency, place the sense-node corner and the shunt self-inductance corner a decade above the band, convert the sensed current into a margin over the amplifier noise floor, and hold a non-shunt pickup to a recorded justification and to the same numbers. Trigger: ecss, e-st-20-08c-clause-11-1-2, solar-cell-capacitance-signal-acquisition, shunt-technique-preference, sense-burden-fraction, acquisition-corner-headroom, shunt-self-inductance-corner, capacitance-signal-to-noise-margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-capacitance-signal-measurement-method, solar-cell-capacitance-signal-acquisition, shunt-technique-preference, sense-burden-fraction, acquisition-corner-headroom, shunt-self-inductance-corner, capacitance-signal-to-noise-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Capacitance Signal Measurement Method (space-systems/ecss/e2008-capacitance-signal-measurement-method)

Use when the task is clause 11.1.2 of ECSS-E-ST-20-08C -- how the signal
is picked up while the capacitance of a solar cell is being measured.
The clause states a preference rather than a rule: the signal is taken
across a shunt. The question a campaign actually has to answer is
therefore two-sided. Is the shunt it has good enough to be the preferred
path, and if something other than a shunt is in the return leg, what
discharges the preference.

## Domain quick reference

- A shunt is a resistor in the return path whose voltage drop is the
  current. Its transfer is one number, flat with frequency, traceable
  to a resistance standard, and it adds nothing to the loop but its own
  value. That is the whole reason the clause prefers it.
- The alternatives -- a current transformer, a Rogowski coil, a
  Hall-effect probe, a series electrometer -- each insert a transfer
  function with a gain, a phase and a bandwidth of their own, and the
  capacitance that comes out inherits every error in it.
- Burden is the first number. The cell is close to a pure reactance of
  1 / (2 pi f C) at the test frequency, and the sensing element sits in
  series with it. A sense resistance that is a few per cent of that
  reactance is measuring the instrument alongside the article.
- Sense-node bandwidth is a second, independent number. The sense
  resistance works into the cable and amplifier input capacitance, not
  into the cell, so the same shunt on a longer cable rolls off at a
  lower frequency while the article is unchanged. Burden says nothing
  about it.
- A shunt stops being a resistor above R / (2 pi L). Its own
  self-inductance has to put that zero out of the measurement band, and
  a low-value shunt reaches that limit sooner than a high-value one --
  the two conditions pull the resistance in opposite directions.
- Level closes it. The delivered voltage has to stand clear of the
  amplifier noise floor by a stated margin in dB; a small shunt keeps
  the burden down and puts the signal in the noise, which is the trade
  the sizing has to settle.
- A preference is discharged by argument plus arithmetic. An
  alternative pickup carries a written justification AND meets the same
  burden, bandwidth and level conditions the shunt would have faced.

## Workflow

1. Take the nominated technique and decide whether it is the preferred
   shunt or an alternative; refuse a technique nobody named, rather
   than assuming a shunt.
2. Pull the evidence that technique owes. A shunt owes its resistance
   and self-inductance; an alternative owes its transfer impedance, its
   bandwidth and a written justification. Absent evidence stops the
   judgement instead of defaulting.
3. Form the cell reactance at the test frequency and place the sensing
   resistance against it as a burden fraction.
4. Form the sense-node corner from the sensing resistance and the cable
   plus input capacitance, and hold it a decade above the test
   frequency.
5. For a shunt, form R / (2 pi L) and hold that corner a decade up too;
   report an inductance too small to measure as an unbounded corner
   rather than dividing by zero.
6. For an alternative, hold its declared bandwidth to the same decade
   and check the justification is text somebody wrote, not a blank.
7. Convert the sensed current into a delivered voltage and a dB margin
   over the noise floor, and compare each derived headroom with its
   limit through a tolerance that absorbs representation error while
   the limit itself stays as written.
8. Report the technique, whether it was the preferred one, every
   derived term, and a verdict that stays open while any finding
   stands.

## Pitfalls

- Reading the preference as a prohibition, or as a free choice. Both
  readings skip the work: the first rejects a justified transformer on
  a bonded return leg, the second accepts an unjustified one.
- Accepting an alternative on its justification alone. The written
  reason explains the departure; it does not exempt the path from the
  burden, bandwidth and level numbers.
- Sizing the shunt only for signal level. Raising the resistance raises
  the delivered voltage and the burden together, and the burden error
  biases every reading in the same direction where the noise only
  scatters them.
- Treating the sense-node corner as the same check as burden. They are
  independent -- one is set by the cell, the other by the cable -- and
  a path can pass either while failing the other.
- Ignoring shunt self-inductance because the resistance is small. A
  low-value shunt has the lower L / R zero, so the smallest shunt in
  the drawer is the one most likely to stop being a resistor inside the
  band.
- Comparing a headroom in decades against a limit by bare arithmetic. A
  decade count comes out of a logarithm that is not correctly rounded
  and lands either side of a whole number on different machines, so the
  comparison absorbs that error while the limit is never relaxed.
- Recovering a weak signal by averaging longer. Averaging lowers the
  random term and leaves the pickup transfer error exactly where it
  was.

## Behavior contract (gate 3)

The technique preference, per-technique evidence requirement, cell
reactance, sense burden fraction, sense-node corner headroom, shunt
self-inductance corner, pickup bandwidth, justification test and
signal-to-noise margin are exercised by the gate 3 contract test:
scripts/test_e2008_capacitance_signal_measurement_method.py against
scripts/e2008_capacitance_signal_measurement_method_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_capacitance_signal_measurement_method.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
