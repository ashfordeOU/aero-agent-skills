---
name: e2008-sca-visual-inspection-process
description: "Evaluate whether the equipment and the viewing approach used to examine solar cell assemblies can resolve the defects the criteria name, under ECSS-E-ST-20-08C clause 6.4.3.1.2: derive the resolved feature from acuity and working distance for a visual station or from field of view and sensor sampling for an imaging one, grow it by the foreshortening an off-normal viewing angle imposes, compare that against the smallest criterion dimension with a detection margin, check illumination and the faces the approach actually reaches, and report the size every later defect call is bounded at. Use when an inspection setup must be shown adequate before its defect calls are trusted. Trigger: ecss, e-st-20-08c, clause-6-4-3-1-2, sca-inspection-resolution-adequacy, visual-station-magnification-check, imaging-sensor-sampling-limit, sca-viewing-angle-foreshortening, inspection-face-coverage."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-sca-visual-inspection-process, sca-inspection-resolution-adequacy, visual-station-magnification-check, imaging-sensor-sampling-limit, sca-viewing-angle-foreshortening, inspection-face-coverage, sca-defect-detection-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Cell Assembly Visual Inspection Process (space-systems/ecss/e2008-sca-visual-inspection-process)

Use when the task is the inspection method of ECSS-E-ST-20-08C clause
6.4.3.1.2 -- the resolution the equipment provides and the way the assembly is
looked at, turned into a statement about what the examination can and cannot
support.

## Domain quick reference

- This clause governs the instrument, not the verdict. Everything it settles is
  a bound on the defect calls that come later: an examination cannot report a
  feature it could not resolve, and a face nobody viewed contributes nothing
  however good the optics were.
- The three station kinds reach their resolution by different arithmetic. An
  unaided station is limited by the eye -- roughly one arc minute of acuity
  converted to a length at the working distance, which is about a tenth of a
  millimetre at arm's length and coarsens in direct proportion as the inspector
  stands back.
- A magnified station divides that length by its power. A station calling
  itself magnified and running at unity is an unaided station with a lens in
  front of it, and crediting it with a magnification it does not have is how a
  setup passes on paper and misses defects in the shop.
- An imaging station is limited by sampling rather than by acuity. The field of
  view spread over the sensor gives the pitch at the article, and a feature
  needs more than one sample to exist in the image, so the resolved feature is
  the pitch times the samples a feature must span. Doubling the field of view
  at a fixed sensor halves the resolution.
- The viewing approach then degrades whatever the station produced. A surface
  looked at off its normal is foreshortened, so a feature presents a shorter
  extent by the cosine of the incidence angle and the effective resolved
  feature grows as the reciprocal of that cosine. Sixty degrees off normal
  costs a factor of two, which is enough to move a comfortable station to the
  edge of its criterion without anything on the bench changing.
- Illumination is the other half of the optics. Below an illuminance floor a
  look stops being a detection activity whatever the instrument in front of it
  is capable of, so an under-lit station is not credited even when its
  resolution is ample.
- Adequacy is a margin question, not an equality. Resolving a feature at
  exactly its own size is a coincidence rather than a detection, so a station
  is credited only when it resolves the smallest criterion feature several
  times over; a station between those two points is marginal and does not carry
  a face on its own.
- Coverage closes the assessment. Every declared face needs at least one
  credited station, and the coarsest face bound is the size the whole
  inspection statement is worth.

## Workflow

1. Validate the policy: acuity, samples per feature, the detection margin, the
   illuminance floor, the incidence limit and the working distance limit.
2. Per station, take the resolved feature from the arithmetic its kind uses,
   rejecting a kind and a magnification that contradict each other.
3. Apply the foreshortening factor for the incidence angle to get the effective
   resolved feature -- the number every later comparison uses.
4. Compare it against the smallest criterion dimension divided by the detection
   margin. Inside it the station is capable; between there and the bare
   criterion it is marginal; beyond the criterion it is not capable at all.
5. Check the viewing conditions separately -- illuminance, incidence, working
   distance -- and send a station that fails one to review rather than letting
   its resolution alone carry it.
6. Map credited stations onto declared faces, keeping the finest bound per face
   and naming any face no credited station reaches.
7. Close with the process verdict, the stations that were not credited, and the
   coarsest face bound, which is what every defect call from this setup is
   worth.

## Pitfalls

- Quoting a datasheet resolution and stopping. The number on the instrument is
  the normal-incidence figure; what governs is the effective one after the
  viewing angle has had its say.
- Treating the incidence angle as a tick-box limit. It is a multiplier on the
  resolved feature, and a station inside the angle limit can still have lost
  its detection margin to it.
- Crediting a magnified station running at unity. It resolves exactly what the
  unaided eye does, and recording a magnification it does not have inflates
  the whole setup.
- Sizing an imaging station by pixel count alone. What matters is the pitch at
  the article, so the same sensor over a wider field resolves proportionally
  less.
- Letting one sample per feature count as resolving it. A feature landing on a
  single pixel is not distinguishable from noise.
- Accepting a station because it resolves the criterion exactly. That is a
  coincidence, not detection, and it leaves nothing for the variation in a real
  article.
- Reporting an adequate setup with a face nobody reached. The stations can all
  be excellent and the assembly still unexamined on one side.
- Comparing an effective resolved feature with a required one by bare
  arithmetic. The first comes from a trigonometric conversion and a cosine
  division and the second from a criterion divided by a margin, so a station
  sitting exactly on the bound can evaluate a few units in the last place above
  it; the comparison absorbs that representation error while the bound stays
  untouched.

## Behavior contract (gate 3)

The per-kind resolution derivations, the unity-magnification rejection, the
sampling limit, the incidence foreshortening factor, the capable/marginal/not
capable margin split, the viewing condition checks and the per-face coverage
rollup are exercised by the gate 3 contract test:
scripts/test_e2008_sca_visual_inspection_process.py against
scripts/e2008_sca_visual_inspection_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_visual_inspection_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
