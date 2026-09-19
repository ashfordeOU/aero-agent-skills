---
name: e4008-file-format-specification
description: "Validate the format declaration an exchange file carries under ECSS-E-ST-40-08C clause 5.7.2.1. Use when the task is confirming a simulator exchange file opens with a delimited declaration block, that the format identifier, two-part version, character encoding, line ending and section list are each present exactly once, that the version falls inside the range the reader supports and whether a newer minor is still forward readable, and that the required sections are all declared, unrepeated and in the order the format fixes. Grades a file against the single normative item. Trigger: ecss, e-st-40-08c, simulator-exchange-file, format-declaration-block, exchange-file-version-support, exchange-file-encoding, exchange-file-section-order, forward-readable-minor-version."
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
  tags: [ecss, e-st-40-08-simulation-scope, e4008-file-format-specification, simulator-exchange-file, format-declaration-block, exchange-file-version-support, exchange-file-section-order, forward-readable-minor-version]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Infrastructure — File Format Specification (space-systems/ecss/e4008-file-format-specification)

Use when the task is the format declaration of ECSS-E-ST-40-08C clause
5.7.2.1 -- what a simulator exchange file has to say about its own
format before a reader is allowed to interpret anything below it. The
clause carries one normative item, and it is the gate every later
validation rule stands on.

## Domain quick reference

- The declaration is the first content in the file, not a field
  somewhere inside it. A reader that has to parse the body to learn how
  to parse the body has already guessed at an encoding, and the guess
  is what corrupts the file rather than rejecting it.
- The block is delimited at both ends. An unterminated declaration is
  not a file that happens to be short; it is a file whose body may have
  been read as declaration lines, so it is refused rather than
  salvaged.
- Five things are declared: what the format is, which version of it,
  the character encoding, the line ending, and the sections that
  follow. Each exactly once -- a repeated key means two readers will
  disagree about which one wins.
- Version is two parts and the two parts carry different weight. A
  different major version is a different format and is never readable;
  a newer minor inside the same major is forward readable, meaning a
  reader may take what it recognises and skip unknown trailing content.
- Encoding and line ending come from a fixed set. They are declared
  rather than sniffed because a sniffed encoding is right most of the
  time, and the times it is wrong are silent.
- The section list fixes both membership and order. A required section
  that is present but out of order breaks a streaming reader, which is
  why the order check is separate from the presence check.
- A malformed version string is a finding about the file, not a crash
  in the reader. Only a file that cannot be delimited at all stops the
  assessment.

## Workflow

1. Take the file content as text that was handed in; locate the first
   non-blank line and require it to be the opening marker.
2. Read declaration lines until the closing marker, skipping blank and
   comment lines, and refuse a line that is not a key and value pair.
3. Refuse a block that is never closed -- that is the case where body
   content has been absorbed into the declaration.
4. Record every key, noting the ones that appear more than once rather
   than silently keeping the last value.
5. Check the five required keys are present, then grade each value: the
   format identifier against the one the reader accepts, the version
   against the supported major and the supported minor range, and the
   encoding and line ending against their declared sets.
6. Grade the section list for emptiness, repeats, missing required
   sections and the order of the required ones, keeping extra sections
   as an allowed tail.
7. Report the single normative item with every finding named, so a file
   with three problems is not re-submitted three times.

## Pitfalls

- Sniffing the encoding when the declaration is absent. The guess
  succeeds on the common case and silently mangles the file on the
  one that mattered.
- Accepting an unterminated declaration block. The body lines that got
  read as declarations set keys nobody wrote, and the resulting
  configuration looks plausible.
- Keeping the last value of a repeated key. Two readers implemented the
  other way round disagree about the same file, and neither reports
  anything.
- Comparing the version as a string. Ordering "2.10" against "2.9" as
  text puts the newer file behind the older one, so the supported-range
  check passes a file it should refuse.
- Reading a newer minor as unreadable. Inside the same major it is
  forward readable with unknown trailing content skipped, and refusing
  it strands files that are perfectly usable.
- Checking section membership and skipping the order. A streaming
  reader needs the catalogue before the assembly that references it, so
  a reordered file fails much later with an unresolved reference.
- Raising on a malformed version. That turns one reportable finding
  into an aborted assessment, and the other four problems in the same
  file never get reported.

## Behavior contract (gate 3)

Declaration-block delimiting, repeated-key detection, required-key
presence, format-identifier matching, two-part version parsing and
support-range grading, forward readability, encoding and line-ending
membership, section presence, repeat and order checks, and the
single-item grading are exercised by the gate 3 contract test:
scripts/test_e4008_file_format_specification.py against
scripts/e4008_file_format_specification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e4008_file_format_specification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
