---
name: q7080-build-file-and-job-control
description: "Validate a powder-bed build file and its job before the platform is committed. Use when a nested job is released, or re-released after an engineering change, and the configuration has to be proved rather than trusted: check the build-file version, digest and parameter set are the approved ones, bind every nested part to the released design index, project each footprint through its platform rotation to prove the nest sits inside the usable envelope with its edge margin and part-to-part clearance, then compare every recorded build orientation against the approved one, treating an unrecorded orientation as a configuration break. Trigger: ecss, q-st-70-80-additive-manufacturing, am-build-file-control, am-build-job-release, am-platform-nesting-clearance, am-part-revision-binding, am-build-orientation-record."
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
  tags: [ecss, q-st-70-80-additive-manufacturing, q7080-build-file-and-job-control, am-build-file-control, am-build-job-release, am-platform-nesting-clearance, am-part-revision-binding, am-build-orientation-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Build File and Job Control (space-systems/ecss/q7080-build-file-and-job-control)

Use when the task is the process clause of ECSS-Q-ST-70-80 that controls the
build file and the build job: which file version was sliced, which design
revision each nested part came from, how the parts are laid out on the
platform and which orientation each one is built at.

## Domain quick reference

- The build file is the manufacturing configuration. Everything that
  reaches the machine passes through it, so a job without a version and
  a digest of the file that was actually sliced cannot be reconstructed
  later from the parts it produced.
- A nest is a set of independent configuration decisions sharing one
  platform. Each part carries its own design revision, and one
  superseded revision in an otherwise correct nest contaminates that
  part alone, which is why the binding is graded per part.
- Rotation on the platform changes the footprint. A part turned in plane
  presents an axis-aligned extent of dx*|cos| + dy*|sin| across and
  dx*|sin| + dy*|cos| deep, so a nest that fitted at zero rotation can
  overrun the plate or a neighbour once parts are turned.
- Clearance is not decoration. Neighbouring parts share the gas flow,
  the recoater pass and the heat of the plate, and touching footprints
  mean a recoater strike or a fused bridge rather than a tight nest.
- Orientation is a property of the part, not of the job. It is approved
  once against the part's properties and repeated on every build, so a
  recorded orientation that drifts from the approved one is a different
  part from the qualified one.
- An unrecorded orientation is a break, not a default. Reading a blank
  field as nominal invents the one parameter that determines anisotropy,
  support load and surface finish on the features that matter.
- Footprints come out of a rotation, so two parts placed at exactly the
  minimum clearance can read a few units in the last place below it. The
  comparison absorbs that; the clearance requirement is never relaxed.

## Workflow

1. Validate the platform envelope and every nested part: a part needs an
   identifier, a part number, a design revision, a bounding box and a
   position, and a non-finite or non-positive value is an input error.
2. Refuse a nest that carries the same part identifier twice; two rows
   pointing at one place on the plate cannot both be graded.
3. Check the build-file identity: a version string, a digest of the
   expected length and alphabet, and a parameter set drawn from the
   approved list rather than a machine-local experiment.
4. Bind each nested part to the released design index, separating a part
   number the index does not carry from a revision that the index
   supersedes.
5. Project every footprint through its platform rotation and check it
   against the usable platform with its edge margin, and the part height
   against the vertical envelope.
6. Grade every pair of footprints for clearance, naming an actual
   overlap differently from a gap that is merely below the minimum.
7. Compare each recorded orientation with the approved orientation for
   that part number within the stated angular tolerance, comparing
   angles the short way round, and report an unrecorded orientation and
   a missing approval separately.
8. Hold the job when anything was found; release it only when nothing
   was.

## Pitfalls

- Trusting the file name as the version. The name travels with copies
  and edits, which is what the digest of the sliced file is there to
  settle.
- Re-using a nest layout after a part grew. The footprint is recomputed
  from the bounding box and the rotation, and a nest is only valid for
  the geometry it was checked against.
- Grading the nest at zero rotation and then turning parts to fit. The
  rotation is part of the layout, so the clearance check has to run on
  the rotated footprints that will actually be built.
- Letting one superseded revision ride along because the rest of the
  nest is correct. The build produces that part too, and it is not the
  part that was released.
- Treating an orientation deviation inside the drawing tolerance band as
  equivalent to none at all without stating the tolerance. The tolerance
  is an input to the comparison, and an unstated one silently becomes
  whatever the recorded values happen to be.

## Behavior contract (gate 3)

The part validation, build-file identity checks, revision binding,
rotated-footprint platform and clearance geometry, orientation comparison
and the release-or-hold verdict are exercised by the gate 3 contract test:
scripts/test_q7080_build_file_and_job_control.py against
scripts/q7080_build_file_and_job_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_build_file_and_job_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
