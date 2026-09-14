---
name: e2008-reflectance-bandwidth-requirement
description: "Evaluate whether the reflectance bandwidth measured on a coverglass matches the figure declared in the coverglass source control drawing per ECSS-E-ST-20-08C clause 8.7.5.4.2: refuse a requirement carrying no drawing reference, recompute each article bandwidth from its cut-on and cut-off under the drawing centre convention, normalise a percentage declaration against a fractional one, compare against the drawing value and its tolerance with a tie admissible, report deviation and tolerance consumed, and flag band-edge drift that cancels inside the ratio. Use when a measured coverglass bandwidth has to become an acceptance verdict. Trigger: ecss, e-st-20-08c-clause-8-7-5-4-2, coverglass-reflectance-bandwidth-acceptance, coverglass-source-control-drawing-bandwidth, bandwidth-declaration-unit-normalisation, coverglass-bandwidth-tolerance-band, coverglass-band-edge-drift-advisory."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-reflectance-bandwidth-requirement, e-st-20-08c, coverglass-reflectance-bandwidth-acceptance, coverglass-source-control-drawing-bandwidth, bandwidth-declaration-unit-normalisation, coverglass-bandwidth-tolerance-band, coverglass-band-edge-drift-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Reflectance Bandwidth Requirement (space-systems/ecss/e2008-reflectance-bandwidth-requirement)

Use when the task is the clause 8.7.5.4.2 acceptance decision of
ECSS-E-ST-20-08C: a filtered coverglass has been measured, and the
reflectance bandwidth that came out of that measurement is admissible
only when it matches the figure the coverglass source control drawing
declares.

## Domain quick reference

- The figure comes from the source control drawing, not from the coating
  vendor's datasheet, not from house practice and not from the last
  build. A verdict quoted with no drawing reference behind it is not a
  verdict against this clause, so an unreferenced declaration closes the
  assessment instead of passing it.
- Two numbers can only be compared in one unit. The same quantity is
  written as a fraction in one document and as a percentage in the next,
  so both the declared value and its tolerance are normalised before any
  comparison, and a fraction large enough that it could only have been a
  percentage is refused rather than used.
- The band centre convention is part of the requirement. The arithmetic
  mean of the edges and their geometric mean are different wavelengths,
  so they give different bandwidth figures for the same filter. The
  drawing's convention governs; where the drawing is silent the policy
  default applies and says so.
- When the two conventions differ by more than the entire tolerance band,
  the verdict is an artefact of that choice. That case is reported
  outright, because a pass that would have been a fail under the other
  centre is not a result anybody should inherit silently.
- The ratio is blind to a bodily shift of the band. Scaling both edges by
  the same factor leaves the bandwidth exactly unchanged, so a filter
  whose whole band has drifted to longer wavelengths reports precisely
  the figure the drawing asks for. Where the drawing also declares a
  nominal centre, that drift is recovered and reported beside the
  verdict rather than folded into it.
- Two measurements of one filter have to agree. An article carrying both
  an edge pair and a separately reported bandwidth is refused when they
  describe different filters, because that is a transcription error and
  grading it puts a number nobody measured into the lot.
- The tolerance band is two-sided and often asymmetric, so the share of
  the allowance a deviation consumed is reported against the side it
  landed on.
- A lot verdict is not a lot description. Articles that all pass can
  still scatter across most of the tolerance band, and that scatter is an
  advisory beside the verdict rather than inside it.

## Workflow

1. Validate the acceptance policy: the default centre convention, the
   tolerance under which an edge pair and a reported figure are treated
   as the same measurement, and the advisory thresholds.
2. Resolve the drawing declaration. An absent declaration, or one whose
   drawing reference is blank, closes immediately on requirement not
   established; a tolerance that is zero on both sides, or one reaching
   zero bandwidth, is a malformed declaration and is refused.
3. Normalise the declared bandwidth and both tolerance arms into
   fractions of the centre wavelength, whichever unit the drawing used.
4. For each article, derive the bandwidth from the measured cut-on and
   cut-off under the drawing's convention, or take the reported figure
   when no edge pair exists, and refuse an article whose two records
   disagree.
5. Compare each article against the declared value and its two-sided
   tolerance, admitting a tie, and report the signed deviation with the
   share of the side-specific allowance it consumed.
6. Close on one verdict -- requirement not established, bandwidth outside
   the drawing tolerance, or bandwidth meets the drawing -- with the lot
   mean, the spread and the worst article beside it.
7. Raise the advisories the verdict cannot carry: a convention gap wider
   than the tolerance band, a mean band centre away from the declared
   one, and article-to-article scatter beyond ordinary spread.

## Pitfalls

- Comparing against a remembered figure. The drawing is the only source
  of the declared bandwidth, and a criterion applied from memory is a
  criterion nobody can audit.
- Comparing a fraction with a percentage. A measured 0.40 against a
  declared 40 fails a coverglass that is exactly on target, and the
  tolerance arms carry the same unit trap.
- Recomputing the measured bandwidth on the house convention when the
  drawing declared the other one. On a wide band that alone can move the
  figure past the tolerance.
- Reporting a pass on a wide band without saying which centre was used.
  The next reader cannot reproduce the number, and the opposite
  convention may well have failed it.
- Reading an unchanged bandwidth as an unchanged filter. A band that has
  shifted bodily keeps its ratio exactly, so the centre wavelength has to
  be carried and compared separately.
- Grading an article whose edge pair and reported bandwidth disagree.
  One of the two is a transcription error, and averaging them or picking
  one puts an unmeasured number into the lot.
- Folding an asymmetric tolerance into a single consumed figure. The
  share is only meaningful against the side the deviation landed on.
- Comparing a measurement with a band edge by bare arithmetic. The edge
  is a declared figure combined with a tolerance and the measurement
  comes from a division, so a value exactly on the bound can evaluate a
  few units in the last place outside it; the comparison absorbs that
  representation error while the tolerance stays untouched.

## Behavior contract (gate 3)

The policy validation, unit normalisation of the declaration and both
tolerance arms, the drawing convention override, the per-article
bandwidth derivation from an edge pair or a reported figure, the
edge-versus-figure consistency refusal, the two-sided tolerance
comparison with an admissible tie, the consumed-allowance share, the lot
mean, spread and worst article, and the convention-gap, centre-drift and
scatter advisories are exercised by the gate 3 contract test:
scripts/test_e2008_reflectance_bandwidth_requirement.py against
scripts/e2008_reflectance_bandwidth_requirement_logic.py (stdlib
unittest, offline, deterministic). Run:
python3 scripts/test_e2008_reflectance_bandwidth_requirement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
