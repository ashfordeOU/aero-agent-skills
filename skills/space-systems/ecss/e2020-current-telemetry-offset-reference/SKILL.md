---
name: e2020-current-telemetry-offset-reference
description: "Determine whether the offset of a reported output current is expressed against the class current of the device, as clause 5.2.8.5.1 of ECSS-E-ST-20-20C fixes it, and whether it stays inside its allowance. Use when a datasheet or a test report states a telemetry zero offset on some other basis and the number has to be made comparable: normalise the declared basis, refuse a percentage of reading outright because an offset lives at zero applied current, restate a full-scale or absolute figure against the class current, report the factor a full-scale basis hid, settle the measured offset from zero-current readings and compare the two. Trigger: ecss, e-st-20-20c-clause-5-2-8-5-1, current-telemetry-offset, class-current-reference-basis, telemetry-zero-offset-basis, full-scale-referenced-offset, offset-basis-restatement, zero-current-reading-spread."
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
  tags: [ecss, e-st-20-20-power-supply-interface-scope, e-st-20-20c-clause-5-2-8-5-1, e2020-current-telemetry-offset-reference, e-st-20-20c, current-telemetry-offset, class-current-reference-basis, telemetry-zero-offset-basis, full-scale-referenced-offset, offset-basis-restatement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Interface — Current Telemetry Offset Reference (space-systems/ecss/e2020-current-telemetry-offset-reference)

Use when the task is clause 5.2.8.5.1 of ECSS-E-ST-20-20C: the offset of
the current a telemetry reports is stated relative to the class current
of the device. This leaf reads one declaration, and the zero-current
readings behind it when there are any, and returns the offset on the
basis the clause fixes together with whatever the restatement exposed.

## Domain quick reference

- The offset is what the telemetry reports with no current flowing. It
  is a fixed current in amperes, set by amplifier input offset, bias
  currents and converter zero error, and it does not shrink as the load
  falls; it is the whole of the error at the bottom of the range.
- Fixing the class current as the reference makes offsets comparable
  across a power distribution. Two outputs whose offsets are each thirty
  milliamps are not equally good if one is a 1.5 A class output and the
  other a 10 A class output, and the ratio is what says so.
- A percentage of reading cannot express an offset at all. At zero
  applied current the reading is the offset, so the ratio is either
  undefined or unity, and neither states anything about the device.
- A percentage of full scale is the substitution that does real damage,
  because it is arithmetically valid and quietly flattering. The
  telemetry full scale on a protected output is sized to reach the
  limitation current of the protection ahead of it, so it sits well
  above the class current; a declaration on that basis understates the
  offset by exactly the ratio of full scale to class current.
- A declared offset and a measured one are different claims. Readings
  taken at zero applied current settle the offset actually present, and
  a set of readings too scattered to agree is noise rather than an
  offset, so the spread is checked before the mean is trusted.

## Workflow

1. Normalise the basis the declaration was written against, accepting
   the spellings a datasheet uses — spaced, underscored, percent-signed,
   abbreviated — and mapping them onto the absolute, class-current and
   full-scale bases.
2. Refuse a reading basis before any arithmetic. It is not a tighter or
   looser statement of the same thing; it is undefined at the point the
   offset is measured.
3. Convert the declared figure into an absolute current, requiring the
   telemetry full-scale current before a full-scale declaration can be
   converted at all rather than assuming one.
4. Re-express the absolute offset against the class current, and, for a
   full-scale declaration, report the factor by which that basis
   understated it: the full scale over the class current.
5. Settle the measured offset from the zero-applied-current readings
   when they are supplied, refusing a set whose spread passes the band
   it was expected to sit inside.
6. Let the measurement govern the verdict when there is one, and report
   a declaration that sits further from it than the two were expected to
   agree.
7. Compare the governing class-referenced magnitude with its allowance,
   absorbing floating-point representation error at an exact match with
   a named tolerance rather than by widening the allowance, and return
   every finding: a basis that had to be restated, a disagreement with
   the measurement, and an offset past its allowance.

## Pitfalls

- Quoting the offset in milliamps and stopping there. An absolute
  current is the right physical quantity but the wrong statement; it
  cannot be compared across outputs of different class and it is not
  what this clause asks to be declared.
- Quoting it as a percentage of full scale. It is the substitution that
  looks most like compliance and understates the offset by the ratio of
  full scale to class current, which on a protected output is rarely
  less than two.
- Quoting it as a percentage of reading. The offset is measured where
  there is no reading; a percentage of reading is undefined there and
  tends to zero exactly where the offset stops mattering.
- Converting a full-scale declaration by assuming a full scale. Without
  the telemetry full-scale current the figure cannot be moved onto the
  class basis, and inventing a plausible one turns a missing input into
  a wrong answer.
- Averaging zero-current readings without looking at their spread. A set
  that disagrees by more than the offset itself is measuring noise, and
  its mean is not an offset however many readings went into it.
- Reporting the declared offset when a measurement exists. The
  declaration is the claim; the readings are the evidence, and where
  they disagree the verdict follows the readings and the gap is named.

## Behavior contract (gate 3)

The basis normalisation, the refusal of a reading basis, the absolute
conversion, the restatement against class current, the full-scale
understatement factor, the zero-reading spread check and the allowance
comparison are exercised by the gate 3 contract test:
scripts/test_e2020_current_telemetry_offset_reference.py against
scripts/e2020_current_telemetry_offset_reference_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_current_telemetry_offset_reference.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
