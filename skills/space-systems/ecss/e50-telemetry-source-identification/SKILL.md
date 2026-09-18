---
name: e50-telemetry-source-identification
description: "Verify that every telemetry data unit carries an unambiguous source identification under ECSS-E-ST-50C clause 5.5.3: build the spacecraft-plus-source identifier tuple for each stream, detect two streams sharing one tuple, size the identifier fields from the number of distinct sources actually flown, reject an identifier value that overflows its declared field, and refuse a retired identifier re-issued before the ground data ambiguity window has passed. Use when defining an application-process identifier plan, reviewing a virtual-channel and source map, or tracing a mis-attributed telemetry packet. Trigger: ecss, e-st-50-communications-scope, telemetry-source-identification, application-process-identifier-plan, spacecraft-identifier-uniqueness, virtual-channel-source-map, identifier-field-width, identifier-reuse-guard-window."
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
  tags: [ecss, e-st-50-communications-scope, e50-telemetry-source-identification, telemetry-source-identifier, application-process-identifier-plan, spacecraft-identifier-uniqueness, virtual-channel-source-map, identifier-field-width, identifier-reuse-guard-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Telemetry Source Identification (space-systems/ecss/e50-telemetry-source-identification)

Use when the task is the source-identification provision of ECSS-E-ST-50C
clause 5.5.3 — showing that a receiving ground system can say, from the
data unit alone, which spacecraft and which on-board source produced it,
with no recourse to the pass plan or the time of arrival.

## Domain quick reference

- Identification is carried in the data unit, not inferred from context.
  A ground system that decides provenance from which antenna was pointed
  where, or from the schedule, loses the answer the moment two spacecraft
  are visible at once or a recorded playback is replayed out of order.
- The identifier is a tuple, not one field. The spacecraft identifier
  separates co-visible missions; the on-board source identifier — the
  application process behind the packet — separates the instrument, the
  processor and the platform services within one spacecraft. Uniqueness
  is a property of the tuple, so two spacecraft may reuse the same source
  identifier and stay unambiguous.
- Field width is set by the identifier values actually issued, not by the
  count of sources. A plan of six sources numbered 2, 5, 9, 40 and 300
  needs the width to hold 300, and the minimum width to enumerate n
  distinct sources is the bit length of n-1. Both checks are needed: a
  field wide enough to count them can still be too narrow to carry them.
- Identifier reuse is a time problem. Retiring a source and re-issuing
  its identifier to a different source is safe only once no stored or
  in-transit data from the first one can still arrive; until the ground
  ambiguity window has passed, the same tuple denotes two different
  things and the archive cannot be disambiguated after the fact.
- Virtual channel is a transport concept and does not identify a source.
  Several sources routinely share a channel and one source can move
  channels; treating the channel as the identifier gives an answer that
  is right until the routing changes.

## Workflow

1. Validate each declared stream: a name, a non-negative integer
   spacecraft identifier, a non-negative integer source identifier, and
   optionally the virtual channel it is routed on. Non-integer or
   negative identifiers are input errors.
2. Form the (spacecraft, source) tuple per stream and group the streams
   by tuple; any group holding more than one stream is an ambiguity that
   the receiving system cannot resolve.
3. Size the fields: compute the minimum bit width to enumerate the
   distinct source identifiers, and the minimum width to carry the
   largest identifier value issued. Take the larger of the two as the
   required width.
4. Compare the required widths with the declared field widths of the
   transfer-frame and packet headers, and report every identifier value
   that overflows its declared field.
5. Screen the retirement history: for each re-issued identifier, compare
   the elapsed time since retirement with the ground ambiguity window,
   which is at least the longest on-board storage retention plus the
   longest playback and archive-ingest delay.
6. Report the tuple map, the required widths, and every finding:
   duplicate tuple, field overflow, premature reuse, channel used as an
   identifier.

## Pitfalls

- Checking uniqueness of the source identifier alone. Within one
  spacecraft that is the right check; across a constellation it raises
  duplicates that are not duplicates, and hides the case where two
  spacecraft identifiers were configured the same.
- Sizing the field from the number of sources. The count sets a floor;
  the largest value issued sets the real requirement, and sparse
  identifier plans routinely exceed the floor by several bits.
- Re-issuing an identifier as soon as a source is switched off. The
  on-board mass memory can still hold days of data from the retired
  source, so the ambiguity window runs from the last possible playback,
  not from the switch-off.
- Reading the virtual channel as the source. Channel assignment is a
  bandwidth decision and changes with mission phase; a source map built
  on it silently mis-attributes packets after a re-plan.
- Treating a reserved or idle identifier value as available. Idle-frame
  and fill values are already spoken for; issuing one to a real source
  makes its data indistinguishable from filler.

## Behavior contract (gate 3)

The stream validation, identifier tuple construction, duplicate
detection, field-width sizing, overflow screening and reuse-window check
are exercised by the gate 3 contract test:
scripts/test_e50_telemetry_source_identification.py against
scripts/e50_telemetry_source_identification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e50_telemetry_source_identification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
