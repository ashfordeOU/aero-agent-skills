---
name: e20-antenna-guided-wave-interfaces
description: "Use when verify the guided-wave interfaces on an antenna port under ECSS-E-ST-20C clause 7.2.3.1: categorize each port as a coaxial-connector or a waveguide-flange, convert the declared voltage-standing-wave-ratio into reflection-coefficient, return-loss and mismatch-loss, check the operating-frequency against the rectangular-waveguide cutoff-frequency and single-mode-band or against the coaxial higher-order-mode-onset and characteristic-impedance tolerance, derate the interface rf-power-rating for vacuum and hot-case-temperature, raise the applied peak rf-power by the standing-wave-enhancement, and confirm the power-handling-margin reaches the required value. Trigger: ecss, e-st-20-electrical-scope, antenna-port-interface, waveguide-flange, coaxial-connector, impedance-match, voltage-standing-wave-ratio, rf-power-handling, higher-order-mode-onset, waveguide-cutoff-frequency."
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
  tags: [ecss, e-st-20-electrical-scope, e20-antenna-guided-wave-interfaces, antenna-port-interface, waveguide-flange, coaxial-connector, impedance-match, voltage-standing-wave-ratio, rf-power-handling, higher-order-mode-onset]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical and Optical Engineering — Antenna Guided-Wave Interfaces (space-systems/ecss/e20-antenna-guided-wave-interfaces)

Use when the task is the guided-wave-interface demonstration of
ECSS-E-ST-20C clause 7.2.3.1 -- showing that the connector or waveguide
flange terminating an antenna port both matches its transmission line and
survives the peak rf-power it carries in orbit.

## Domain quick reference

- A port is either a coaxial-connector or a waveguide-flange, and the
  category decides which moding checks apply. A declared interface name
  that maps to neither is rejected rather than silently treated as one of
  them; the two categories have nothing in common numerically.
- Mismatch is one measurement expressed four ways. From the
  voltage-standing-wave-ratio s: the reflection-coefficient magnitude is
  (s-1)/(s+1), the return-loss is -20*log10 of that magnitude, the
  mismatch-loss is -10*log10(1 - magnitude squared), and the peak field at
  the standing-wave maximum raises the local peak rf-power by
  (1 + magnitude) squared. The last of the four is the one that couples
  impedance-match to power-handling: a port that is merely "within the
  return-loss specification" still concentrates more peak rf-power in the
  interface than the forward wave alone suggests.
- A rectangular waveguide of broad wall a and narrow wall b carries the
  dominant mode above c/(2a) and the first higher-order mode above c/a.
  The usable single-mode-band sits between 1.25 and 1.90 times the
  dominant cutoff-frequency: below that the guide is strongly dispersive
  and close to cutoff, above it a second mode is on the point of
  propagating.
- A coaxial line of inner radius a, outer radius b and relative
  permittivity e has characteristic impedance (59.9585/sqrt(e))*ln(b/a)
  and its first higher-order mode starts near c/(sqrt(e)*pi*(a+b)). Both
  figures move with the dielectric fill, so a connector qualified as an
  air line and flown with a filled interface can drift out of its
  impedance tolerance and mode at a lower frequency than assumed.
- Power-handling is a margin, not a pass/fail reading of a datasheet.
  The ground rating is derated for vacuum and for the hot-case
  temperature, the applied peak rf-power is raised by the
  standing-wave-enhancement, and the margin is
  10*log10(derated rating / effective peak). The port is acceptable only
  when that margin reaches the value the programme requires.
- An allowable that is absent from the record is a finding in its own
  right: a port with no allowable voltage-standing-wave-ratio has not been
  specified, and "no violation" is not a demonstration.

## Workflow

1. Collect every antenna port with its interface name, operating
   frequency, measured or specified voltage-standing-wave-ratio, applied
   peak rf-power, interface rf-power rating and the derating factors that
   apply in orbit. Give each port a unique id.
2. Categorize the interface. Reject an interface that is neither a
   coaxial-connector nor a waveguide-flange before any number is computed.
3. Run the moding check for that category. For a waveguide-flange:
   compute the dominant cutoff-frequency from the broad wall, flag an
   operating frequency at or below it as non-propagating, and flag an
   operating frequency outside the 1.25 to 1.90 single-mode-band. For a
   coaxial-connector: compute the higher-order-mode-onset and the
   characteristic impedance from the radii and the dielectric fill, flag
   an operating frequency above the onset, and flag an impedance outside
   its declared tolerance around the nominal value.
4. Convert the voltage-standing-wave-ratio into reflection-coefficient,
   return-loss, mismatch-loss and standing-wave-enhancement, and compare
   the ratio against the allowable. Record a finding when no allowable is
   on file.
5. Derate the rf-power rating by the vacuum and temperature factors,
   raise the applied peak rf-power by the standing-wave-enhancement, and
   compute the power-handling-margin. Flag a margin that falls short of
   the required value; a margin that meets it exactly is acceptable.
6. Aggregate across the port set: report the worst power-handling-margin
   and every non-compliant port. The antenna interface set is
   demonstrated only when no port carries a finding.

## Pitfalls

- Demonstrating power-handling with the forward peak rf-power alone --
  the standing wave raises the peak at the interface by (1 + reflection
  coefficient) squared, and at a 1.5 voltage-standing-wave-ratio that is
  already 1.6 dB of hidden stress on the connector.
- Accepting a flange because the operating frequency is above the
  dominant cutoff-frequency -- just above cutoff the guide is dispersive
  and lossy, which is why the usable band starts well above it, and just
  below the first higher-order cutoff a second mode is ready to
  propagate.
- Carrying an air-line impedance and mode onset into a dielectric-filled
  connector -- both scale with the square root of the relative
  permittivity, so a PTFE fill moves a nominal 50 ohm geometry well
  outside its tolerance and lowers the mode onset by about 45 percent.
- Reusing a ground rf-power rating in vacuum without derating -- the
  ambient breakdown path that set the rating does not exist in orbit, and
  the hot-case interface temperature reduces the rating further.
- Reading "no violation" as a demonstration when no allowable
  voltage-standing-wave-ratio was ever declared -- the absent allowable is
  the finding.

## Behavior contract (gate 3)

The interface categorisation, mismatch conversions, waveguide
cutoff-frequency and single-mode-band check, coaxial impedance and
higher-order-mode-onset check, rf-power derating and
power-handling-margin, and the port-set aggregation are exercised by the
gate 3 contract test:
scripts/test_e20_antenna_guided_wave_interfaces.py against
scripts/e20_antenna_guided_wave_interfaces_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_antenna_guided_wave_interfaces.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
