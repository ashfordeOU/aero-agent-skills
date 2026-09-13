---
name: e2008-coverglass-conductivity-measurement-process
description: "Perform the surface conductivity measurement on the coverglasses of the designated qualification subgroup per ECSS-E-ST-20-08C clause 6.4.3.13.2: separate subgroup members from articles that only shared the bench, turn each four-point or concentric-ring site reading into a sheet resistance and its reciprocal conductivity, check every drive current sits inside the electrometer band and the ambient inside the declared humidity and temperature band, then weight each article once into a subgroup figure. Use when a coverglass conductivity run has to be made on the right population by an established method. Trigger: ecss, e-st-20-08c-clause-6-4-3-13-2, coverglass-qualification-subgroup-sampling, coverglass-surface-conductivity-measurement, four-point-collinear-probe-sheet-resistance, concentric-ring-electrode-sheet-resistance, coating-measurement-humidity-band, electrometer-probe-current-band."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-conductivity-measurement-process, coverglass-qualification-subgroup-sampling, coverglass-surface-conductivity-measurement, four-point-collinear-probe-sheet-resistance, concentric-ring-electrode-sheet-resistance, coating-measurement-humidity-band, electrometer-probe-current-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Conductivity Measurement Process (space-systems/ecss/e2008-coverglass-conductivity-measurement-process)

Use when the task is clause 6.4.3.13.2 of ECSS-E-ST-20-08C -- measuring
the surface conductivity of conductive coverglasses that belong to the
designated qualification subgroup. The clause fixes a population and it
fixes a measurement, and a run that is loose about either produces a
figure that cannot be carried into the acceptance decision.

## Domain quick reference

- The population is the designated subgroup, not the bench. A
  coverglass from another subgroup can be measured perfectly and still
  contribute nothing, because the figure being built describes that
  subgroup and no other.
- An article whose subgroup is not recorded is the harder case. Unknown
  membership is not membership, and it is not non-membership either; it
  is a record defect, and reading it as either one quietly moves the
  population.
- Surface conductivity is never read off an instrument. A voltage and a
  current are measured and a geometry factor converts them into sheet
  resistance, whose reciprocal is the wanted quantity. The collinear
  four-point probe contributes pi over ln two; a guarded concentric
  ring pair contributes two pi over the log of the radius ratio.
- The two factors are not interchangeable and neither is a fudge. At a
  two-to-one ring radius ratio the ring factor is exactly twice the
  four-point factor, which is a useful arithmetic check and not a
  reason to substitute one method for the other.
- Drive current has a floor and a ceiling. Below the floor a
  high-resistance coating returns electrometer noise; above the ceiling
  the current heats a thin coating and can change the property being
  measured, so the record has to show where inside the band each site
  sat.
- Ambient travels with the number. Adsorbed moisture conducts, so the
  same coverglass reads differently at twenty per cent relative
  humidity and at eighty, and a conductivity quoted without the ambient
  it was taken in is not comparable with the drawing value or with the
  next article.
- Sites per article matter as much as articles per subgroup. One site
  per coverglass satisfies any article count and samples almost none of
  the outer face.

## Workflow

1. Validate the sampling and conditions policy first: minimum member
   articles, minimum sites per article, the electrometer current band
   and the humidity and temperature bands. An inverted band is refused
   rather than used.
2. Read the designated subgroup from the case. An absent designation is
   a defect and is refused; a blank one closes immediately on subgroup
   not established, because there is no population to measure.
3. Split the inventory into members and non-members, rejecting a
   duplicate article identifier and any article that records no
   subgroup. Keep the non-members in the record by name so it is
   visible what was set aside and why.
4. Check the population before converting anything: member count
   against the policy minimum, and sites per member against the
   per-article minimum. Report every short article, not only the first.
5. Convert each site reading by the method its article declares, into
   sheet resistance and then into surface conductivity. A reading whose
   method is not one of the two established ones is refused.
6. Check every drive current against the electrometer band and the
   declared ambient against the humidity and temperature bands, naming
   the offending site or condition in each finding.
7. Average the sites of each article, then average the articles with
   equal weight, so an over-sampled coverglass cannot carry the
   subgroup figure on its own. Report that average even when the run is
   invalid, so the defect and the number it would have produced stay
   visible together.
8. Close on one verdict: subgroup not established, population
   incomplete, measurement conditions invalid, or subgroup conductivity
   measured.

## Pitfalls

- Averaging every site in the campaign into one number. Forty sites on
  a convenient article and five on the rest is not a subgroup mean, it
  is that article's mean with a small correction.
- Letting a non-member article into the population because it was
  measured the same day on the same rig. The measurement is fine; the
  membership is what fails.
- Applying the four-point factor to a ring measurement, or the reverse.
  The result is off by a factor that depends on the ring geometry, and
  nothing in the number shows it.
- Driving hard to get a clean reading. Raising the current until the
  electrometer is comfortable can heat and damage the coating, and the
  reading then describes an article that no longer exists.
- Omitting the ambient from the record. Without it the conductivity
  cannot be compared with the drawing value, and a later reviewer has
  no way to recover the condition it was taken in.

## Behavior contract (gate 3)

The policy validation, subgroup membership split, the four-point and
concentric-ring conversions, the reciprocal conductivity, the probe
current and ambient band checks, the per-article and equal-weight
subgroup averages, and the process verdict are exercised by the gate 3
contract test:
scripts/test_e2008_coverglass_conductivity_measurement_process.py
against
scripts/e2008_coverglass_conductivity_measurement_process_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2008_coverglass_conductivity_measurement_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
