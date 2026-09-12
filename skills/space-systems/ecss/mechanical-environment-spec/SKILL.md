---
name: mechanical-environment-spec
description: "Use when define the mechanical environment for a space structure per ECSS-E-ST-32C clauses 4.2.3-4.2.4: identify each environment type (microgravity, audible noise, human-induced vibration, random vibration, shock), verify that the random vibration power spectral density spans the required 20-2000 Hz range, verify that the shock response spectrum spans 10-10 000 Hz, compute overall Grms by integrating PSD breakpoints on a log-log basis, interpolate the SRS envelope at any demanded frequency, and assess audible noise octave-band levels against allowable limits. Flag any environment type missing from the specification before structural loads analysis begins. Trigger: ecss, e-st-32-structures-scope, mechanical-environment, random-vibration, shock-response-spectrum, microgravity, audible-noise, human-induced-vibration."
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
  tags: [ecss, e-st-32-structures-scope, mechanical-environment, random-vibration, shock-response-spectrum, microgravity, audible-noise, human-induced-vibration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Mechanical Environment Specification (space-systems/ecss/mechanical-environment-spec)

Use when the task is to define the mechanical environment for a spacecraft
structure under ECSS-E-ST-32C clauses 4.2.3-4.2.4 — covering microgravity,
audible noise, human-induced vibration, and the derived random-vibration and
shock-response-spectrum environments.

## Domain quick reference

- Clause 4.2.3 of ECSS-E-ST-32C requires the project to document every
  mechanical environment the structure must survive or operate within.  The
  environment set is grouped into five types: microgravity (steady-state
  quasi-static acceleration in micro-g), audible noise (octave-band sound
  pressure levels in dB), human-induced vibration (low-frequency excitation
  from crew activity in the 1-100 Hz band), random vibration (broadband
  stochastic base excitation expressed as a power spectral density in g²/Hz
  over 20-2000 Hz), and shock (transient mechanical impulse characterised by
  the shock response spectrum in g over 10-10 000 Hz).
- Clause 4.2.4 designates random vibration and shock response spectrum
  environments as derived (D): they are not directly measured mission inputs
  but are computed by propagating upstream source data (launch vehicle
  interface loads, acoustic field, pyroshock events) through a transfer model.
  The derivation trace must be documented and the result expressed as a
  notched or enveloped PSD / SRS spectrum.
- Each environment type must appear in the specification before structural
  analysis begins.  A missing type is a gap in the load set, not a
  conservative assumption.
- Random vibration overall Grms is computed by numerical integration of the
  PSD curve on a log-log frequency axis (piecewise power-law segments between
  breakpoints).  Each segment contributes (W2·f2 - W1·f1) / (m+1) to the
  mean-square, where m is the log-log slope; the special case m = -1 gives
  W1·f1·ln(f2/f1).
- Shock response spectrum interpolation between breakpoints uses log-log
  interpolation: at a query frequency f, the acceleration is
  a1 · (a2/a1)^[log(f/f1)/log(f2/f1)] where (f1,a1) and (f2,a2) bracket
  the query.  The standard quality factor Q = 10 is assumed unless the
  project specifies otherwise.

## Workflow

1. Inventory the project's mechanical environment specification document and
   confirm that all five types are present: microgravity, audible-noise,
   human-vibration, random-vibration, and shock-response.  Raise a finding
   for each type absent before proceeding.
2. For the random vibration environment, validate the PSD breakpoint table:
   frequencies must be strictly ascending, all values positive, and the table
   must span at least 20-2000 Hz.  Compute the overall Grms from the
   breakpoints using the log-log integral and record it alongside the table.
3. For the shock response spectrum, validate the SRS breakpoint table:
   frequencies strictly ascending, all values positive, coverage at least
   10-10 000 Hz, Q factor specified (default 10).  Interpolate the SRS
   envelope at any frequency demanded by a downstream analysis using log-log
   interpolation between adjacent breakpoints.
4. For the audible noise environment, check each octave-band SPL value
   against the applicable limit and compute the overall SPL by energy
   summation.  Record any band that exceeds the limit as a finding.
5. For the human-induced vibration environment, confirm the frequency and
   amplitude of each documented event fall within the 1-100 Hz band; flag
   any event outside that range for review.
6. For the microgravity environment, confirm the steady-state acceleration
   level is documented and non-negative.  If a peak transient level is also
   specified, verify that it equals or exceeds the steady-state value; flag
   a transient that is lower, as the values may be transposed.
7. Collect all findings from steps 1-6.  The specification is complete only
   when the finding list is empty for every environment type.

## Pitfalls

- Treating a missing environment type as a zero load — clause 4.2.3 requires
  explicit documentation of each type; the absence of an entry is a gap, not
  a conservative assumption of zero.
- Integrating the PSD with a linear (not log-log) frequency axis, which
  understates the area in segments with a rising slope and overstates it in
  segments with a steep negative slope.
- Applying the log-log PSD integral formula when m = -1 without the
  special-case treatment: the (m+1) denominator goes to zero, and the correct
  form is W1·f1·ln(f2/f1).
- Treating the SRS Q factor as fixed at 10 without checking the project
  tailoring — some programs specify Q = 50 for sensitive equipment; using the
  wrong Q changes the computed response amplitude.
- Extrapolating the SRS or PSD envelope beyond its defined breakpoint range;
  only interpolation between documented breakpoints is valid unless the project
  explicitly extends the envelope.
- Reading an unset audible-noise budget as "no constraint" — an absent limit
  record means the requirement was never captured and is itself a finding.

## Behavior contract (gate 3)

The PSD integration, Grms computation, SRS interpolation, frequency-coverage
checks, audible-noise assessment, human-vibration check, microgravity
validation, and environment-completeness check are exercised by the gate 3
contract test: scripts/test_mechanical_environment_spec.py against
scripts/mechanical_environment_spec_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_mechanical_environment_spec.py

## Compliance

- ECSS standards are freely downloadable from ESA; cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
