---
name: e2008-coverglass-breaking-strength
description: "Determine whether a coverglass lot holds the mechanical strength its control drawing fixes per ECSS-E-ST-20-08C clause 8.7.15: convert every recorded break load into a stress for the bend fixture that produced it, fit a Weibull modulus and characteristic strength over the broken set, derive the low-probability design allowable, hold that allowable rather than the arithmetic mean against the drawing value, keep the fitted modulus above its scatter floor, and record any single article that broke under the drawing limit even when the fit clears. Use when a lot is about to be accepted on an average break load that hides a weak tail. Trigger: ecss, e-st-20-08c-clause-8-7-15, coverglass-breaking-strength-acceptance, coverglass-flexural-stress-conversion, coverglass-weibull-modulus-fit, coverglass-design-allowable-stress, coverglass-control-drawing-strength-limit, ring-on-ring-coverglass-fixture."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-breaking-strength, coverglass-breaking-strength-acceptance, coverglass-flexural-stress-conversion, coverglass-weibull-modulus-fit, coverglass-design-allowable-stress, coverglass-control-drawing-strength-limit, ring-on-ring-coverglass-fixture]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Breaking Strength (space-systems/ecss/e2008-coverglass-breaking-strength)

Use when the task is clause 8.7.15 of ECSS-E-ST-20-08C -- the
mechanical strength of a coverglass held against the limits its control
drawing fixes. The drawing states a strength; the laboratory hands back
a column of break loads. Turning the second into a verdict on the first
is the whole job, and it is not an average, because a coverglass is a
brittle plate whose strength is a distribution rather than a property.

## Domain quick reference

- A coverglass has no yield point. It breaks at the largest flaw the
  stress field reaches, and the flaw population is set by the cutting,
  the edge treatment and the polish. Two lots of the same glass from
  the same melt can carry very different strengths for that reason.
- A break load is not a strength. It becomes one only through the
  geometry of the fixture that applied it: a centre-loaded bar carries
  3 F L / (2 b h squared) in its outer fibre, a four-point rig carries
  the same expression written on its offset arm, and a concentric ring
  pair carries an equibiaxial plate expression that needs Poisson's
  ratio as well.
- The thickness term is squared. A coverglass measured a few microns
  thinner than the drawing nominal reports a stress several per cent
  high, and that error never averages out across the lot.
- Ring-on-ring loads an area rather than a line, so it exposes far more
  of the flaw population and returns a lower strength for the same
  glass. That is a property of the fixture, not a defect in the lot,
  and the two fixtures' numbers are not interchangeable.
- The two-parameter Weibull fit -- least squares on the ranked set with
  median plotting positions -- returns a modulus and a characteristic
  strength. The modulus is the scatter: a high modulus means a narrow
  flaw population, a low one means the lot is not under control even
  when its mean looks comfortable.
- The number that faces the drawing is the design allowable, the stress
  at which the fitted population reaches a chosen break risk, not the
  mean and not the median. A lot whose mean clears the drawing while
  its allowable does not is precisely the lot the clause exists to
  catch.

## Workflow

1. Take the fixture and refuse to convert anything until it has brought
   the geometry that fixture owes. Missing geometry stops the
   conversion rather than defaulting to a nominal.
2. Convert each recorded break load into a stress through its own
   fixture expression, keeping the whole column rather than reducing it
   early.
3. Rank the stresses, fit the Weibull modulus and characteristic
   strength, and refuse a set too short or too flat to carry a fit.
4. Derive the design allowable at the chosen failure probability from
   the fitted pair.
5. Compare the allowable with the drawing minimum, hold the modulus
   above its floor, and record any single article that broke under the
   drawing value even when the fit clears.
6. Report the mean alongside the allowable and mark the case where the
   mean passes and the allowable does not, so the weak tail is visible
   rather than averaged away.

## Pitfalls

- Accepting on the mean. The arithmetic mean of a brittle strength
  distribution sits well above the stress at which the first per cent
  of the population breaks, and the drawing limit is about that first
  per cent.
- Comparing a bend-bar strength with a ring-on-ring strength. The two
  fixtures sample different amounts of the flaw population, so the same
  glass legitimately returns different numbers and neither converts
  into the other by a constant.
- Using the drawing nominal thickness instead of the measured one. The
  term is squared, so a small thickness error becomes a systematic
  stress error in the same direction on every article in the lot.
- Fitting a Weibull to a handful of breaks. Below about ten broken
  articles the modulus is dominated by the ranking scheme rather than
  the glass, and the allowable it produces is arithmetic rather than
  evidence.
- Ignoring a low modulus because the allowable happened to clear. A
  scattered lot passing today is a lot whose next batch has no reason
  to pass, and the modulus is the only place that shows.
- Comparing a derived allowable against the drawing value by bare
  arithmetic. The allowable is the product of a logarithm, a
  least-squares slope and a fractional power, none of them correctly
  rounded, so the comparison absorbs a few units in the last place
  while the drawing limit itself is never relaxed.
- Quietly dropping an article that broke during handling. A break below
  the drawing value is evidence about the lot whatever caused it, and
  removing it from the column moves the fit in the flattering
  direction.

## Behavior contract (gate 3)

The fixture geometry requirement, three-point, four-point and
ring-on-ring stress conversions, median plotting positions, Weibull
modulus and characteristic strength fit, design allowable at a chosen
failure probability, modulus floor, weakest-article record and the
mean-hides-the-tail flag are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_breaking_strength.py against
scripts/e2008_coverglass_breaking_strength_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_breaking_strength.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
