---
name: q6005-internal-circuit-photographic-record
description: "Audit the images of an assembled hybrid microcircuit interior captured before the package closes, and decide whether they hold as permanent evidence of the as-built configuration, under ECSS-Q-ST-60-05 clause 10.3.4. Use when a photographic record has to be graded rather than filed: test that the smallest feature spans enough pixels, drop unreadable frames before counting coverage, name every declared die, interconnect region and attach area no frame shows, weigh the archive format and retention, and return the record-adequacy index with one verdict. Trigger: ecss, q-st-60-05, internal-circuit-photographic-record, as-built-configuration-evidence, hybrid-interior-frame-coverage, photographic-record-resolution, photographic-record-retention, photographic-record-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-internal-circuit-photographic-record, as-built-configuration-evidence, hybrid-interior-frame-coverage, photographic-record-resolution, photographic-record-retention, photographic-record-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Internal Circuit Photographic Record (space-systems/ecss/q6005-internal-circuit-photographic-record)

Use when the task is clause 10.3.4 of ECSS-Q-ST-60-05: the images of the
assembled internal circuit, taken while the package is still open and kept
as permanent evidence of what was actually built. Where the step sits in the
run is graded under the screening sequence; the burn-in and the
thermographic image before it have leaves of their own.

## Domain quick reference

- The record exists to be read years later by somebody who cannot open the
  package. Its worth is entirely in what that reader can resolve, not in how
  many frames the shop took.
- Resolution is the first question. A feature that does not span enough
  pixels is shown to exist and nothing more, and its condition is precisely
  what a later investigation will ask about.
- Coverage is counted by subject, not by frame. Every die, interconnect
  region and attach area the assembly declares has to appear somewhere, and
  forty frames of the same corner cover one subject.
- A frame nobody can read covers nothing. Unreadable frames leave the usable
  set before coverage is counted, or the record claims evidence it does not
  hold.
- The best frame of a view decides that view's credit. A soft duplicate
  alongside a sharp frame does not dilute the evidence, and a soft frame
  alone is an open action rather than a missing view.
- The frames have to say which unit they belong to. A perfect image of an
  unidentified interior is evidence about some hybrid, which is no evidence
  at all.
- The images are taken before the seal, because afterwards the interior
  cannot be photographed without destroying the unit whose record it is.
- Storage is part of the record. A format nobody will open, a retention
  shorter than the hardware's life, or an archive that can be quietly
  replaced turns permanent evidence back into a photograph.

## Workflow

1. Take the unit, the subjects the assembly declares, the frames actually
   captured, the smallest feature that matters, and the archive retention.
2. Validate the frame set: a unique identifier, a published view, a
   published quality grade, well-formed subjects and a declared pixel
   density.
3. Drop the unreadable frames from the usable set before anything is
   counted.
4. Name every declared subject no usable frame shows.
5. Name every required view no usable frame supplies, and grade each view
   from the best frame that does.
6. Test every usable frame against the pixel floor for the smallest
   feature, and treat a frame with no declared density as unproven rather
   than adequate.
7. Grade the archive provisions, overruling a declared retention with the
   years actually held.
8. Take the weighted credit over total weight across views and provisions
   as the record-adequacy index.
9. Name the verdict: incomplete on an uncovered subject or a missing
   mandatory view, not accepted on inadequate resolution, a missing
   mandatory provision or a low index, accepted with open actions when
   findings remain, accepted only when none do.

## Pitfalls

- Counting frames instead of subjects. A hundred images of the same die
  leave the other die undocumented.
- Keeping a blurred frame in the coverage count because something is in it.
  The coverage claim is what a future reader can use, not what was aimed at.
- Photographing at the magnification that fits the whole assembly. The
  overall view is one required view, not the record.
- Filing frames with no unit identification. The archive then holds images
  of an anonymous hybrid, and no later investigation can use them.
- Leaving the pixel density out of the frame metadata. A record whose
  resolution cannot be established afterwards has to be read as unproven.
- Deciding the retention from how long the project runs. The hardware
  outlives the project, and the record has to outlive the hardware.
- Storing the archive somewhere entries can be replaced without trace.
  Evidence that can be edited is testimony, not evidence.
- Taking the images after the seal because the schedule slipped. There is no
  second chance at an interior photograph.

## Behavior contract (gate 3)

The pixel-floor resolution test, frame-set validation, unreadable-frame
exclusion, subject coverage, required-view coverage and best-frame grading,
retention floor, archive-provision grading, record-adequacy index and record
verdict are exercised by the gate 3 contract test:
scripts/test_q6005_internal_circuit_photographic_record.py against
scripts/q6005_internal_circuit_photographic_record_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_internal_circuit_photographic_record.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
