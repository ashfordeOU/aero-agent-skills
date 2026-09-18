---
name: q6012-die-selection-general-requirements
description: "Assess a candidate microwave die against the baseline selection rules of ECSS-Q-ST-60-12 clause 5.1. Use when the task is deciding which bare die may enter a microwave design at all: confirm the die comes from a controlled process reached by a traceable supply route, measure how much of the application band, case-temperature range, total-dose requirement and rated life it actually covers, separate a hard exclusion from a recoverable evidence gap, then group the candidates as eligible, eligible-with-actions or not-eligible and rank the survivors on a reproducible coverage composite. Trigger: ecss, q-st-60-12, microwave-die-baseline-selection, mmic-bare-die-eligibility, die-supply-route-traceability, application-band-coverage, die-case-temperature-coverage, die-total-dose-headroom."
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
  tags: [ecss, q-st-60-microwave-die-scope, q6012-die-selection-general-requirements, microwave-die-baseline-selection, mmic-bare-die-eligibility, die-supply-route-traceability, application-band-coverage, die-total-dose-headroom]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die — Baseline Selection Rules (space-systems/ecss/q6012-die-selection-general-requirements)

Use when the task is the first, coarse step of ECSS-Q-ST-60-12 clause 5.1 —
deciding which candidate microwave dice are admissible for an application at
all, before anyone spends effort on the detailed parameter-by-parameter case.
It answers one question per candidate: is this die allowed into the design,
is it allowed in once some evidence is produced, or is it out.

## Domain quick reference

- A bare microwave die is chosen against an application envelope, not in the
  abstract. The envelope is the operating band, the case-temperature range the
  die sees in its mounted configuration, the mission total-ionising-dose, the
  life the equipment owes, and the assembly route the die has to survive.
  A die that is excellent in one envelope can be inadmissible in another.
- Two different things make a candidate fail, and conflating them wastes
  programmes. A datum that is present and insufficient — a band that does not
  span the application, a temperature range the application steps outside, dose
  capability below the mission requirement — is a hard exclusion; no amount of
  further work makes that die fit. A datum that is simply not on record yet is
  an evidence gap, recoverable by an evaluation or a data request.
- Provenance is a selection criterion in its own right. A die reached through
  a route that cannot be traced back to the manufacturer carries no usable
  process history, so its coverage numbers describe a part nobody can prove was
  the part delivered. A traceable route through an intermediary is admissible
  but owes an incoming verification plan.
- The process the die is fabricated on has to be one the programme controls.
  An uncontrolled process means the die's behaviour over life is not anchored
  to anything the project can monitor, which is why it excludes rather than
  merely flags.
- Coverage and eligibility are separate answers. Eligibility is the sign of
  each margin; coverage is how comfortable those margins are. Ranking uses
  coverage, but coverage never promotes a candidate past an exclusion.

## Workflow

1. Normalise the application envelope and refuse it if the band is inverted or
   non-positive, the temperature range is inverted, the dose or life figure is
   not positive, or the assembly route is not one the line supports.
2. Normalise every candidate record. Absent optional data stays absent; it is
   never defaulted to a convenient value. A broker route defaults to untraced
   unless traceability is explicitly asserted.
3. Confirm the fabrication process is on the controlled process list and the
   supply route is traceable. Both are exclusions when they fail.
4. Form the band-coverage fraction, the cold and hot temperature margins, the
   dose headroom against the required factor, and the life headroom. Compare
   each at its limit with a named representation tolerance rather than a bare
   inequality, so an exactly covering die is accepted.
5. Raise an action, not an exclusion, for each datum that is absent, for an
   unevaluated die, and for a traceable intermediary route.
6. Group the candidate from its findings: any exclusion makes it not-eligible,
   any remaining action makes it eligible-with-actions, otherwise eligible.
7. Score coverage as a reproducible composite of the four margins, rank by
   category first and coverage second with the part identifier breaking ties,
   and recommend only a candidate that carries no open action.

## Pitfalls

- Treating an absent datum as a pass. A die with no dose capability on record
  is not a die with adequate dose capability; it is a die owing data, and
  reporting it as eligible hides the work still to be done.
- Letting a high coverage score float a candidate above an exclusion. The
  score exists to order admissible parts, and a ranking that mixes the two
  turns an inadmissible die into a shortlist entry.
- Accepting an untraced route because the datasheet numbers look right. The
  numbers describe a part; traceability is what connects them to the die that
  will actually be mounted.
- Comparing a coverage fraction or a margin against its limit with a bare
  inequality. A die whose band exactly spans the application can land a unit in
  the last place short; absorb that in the comparison, never by widening the
  application envelope.
- Carrying a candidate forward on partial band overlap because "most of the
  band is covered". Baseline selection is pass or fail on the envelope; a
  partially covered band is an exclusion, not a percentage to negotiate.

## Behavior contract (gate 3)

The envelope validation, candidate normalisation, band and temperature
coverage arithmetic, dose and life headroom, exclusion-versus-action split,
grouping, scoring and ranking are exercised by the gate 3 contract test:
scripts/test_q6012_die_selection_general_requirements.py against
scripts/q6012_die_selection_general_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_die_selection_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
