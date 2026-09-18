---
name: q7029-product-identification
description: "Identify the offgassing products a material releases into a crew-compartment atmosphere from chromatographic and mass-spectrometric evidence under ECSS-Q-ST-70-29: grade each peak on retention-index deviation and spectral match score, hold a co-eluting pair back for a second technique, demand orthogonal confirmation for products driving the toxicity total, and account for the area left unidentified. Use when a test house returns an offgassing chromatogram and the peak list must become a defensible product inventory, not a raw table. Trigger: ecss, q-st-70-29, offgassing-product-identification, offgassing-peak-library-match, offgassing-retention-index-window, offgassing-spectral-match-score, offgassing-coelution-resolution, offgassing-unidentified-area-fraction, crew-compartment-offgassing."
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
  tags: [ecss, q-st-70-materials-scope, q7029-product-identification, offgassing-product-identification, offgassing-peak-library-match, offgassing-retention-index-window, offgassing-spectral-match-score, offgassing-unidentified-area-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Offgassing — Product Identification (space-systems/ecss/q7029-product-identification)

Use when the task is the analysis step of ECSS-Q-ST-70-29 that turns the raw
output of the offgassing collection into a named inventory of products: which
chromatographic peaks correspond to which compounds, how confident each of
those assignments is, and how much of the collected material the inventory
does not account for.

## Domain quick reference

- Two independent pieces of evidence carry an assignment: where the peak
  elutes, expressed as a retention index on the column in use, and how well
  its mass spectrum matches a library entry. Either one alone is a
  coincidence; a spectral match at the wrong retention index is a different
  compound of the same class, and a retention hit with a poor spectrum is an
  unresolved shoulder.
- Assignments are therefore graded, not binary. A peak inside the retention
  window with a high match score is a confirmed product; one that satisfies
  only one of the two, or satisfies both weakly, is tentative and is reported
  as tentative. A peak satisfying neither stays unidentified and keeps its
  area in the accounting.
- Two peaks separated by less than the resolution the column can deliver are
  not two independent assignments. Their spectra are mixtures, so both are
  held back for a second technique — a different stationary phase or an
  orthogonal detector — before either is carried forward.
- Any product that will drive a toxicity total needs orthogonal confirmation,
  because a mis-assignment there propagates straight into the crew exposure
  number. Without that confirmation the assignment is downgraded rather than
  accepted on library score alone.
- The area that stays unidentified is an output, not a residue to be dropped.
  A large unidentified fraction means the inventory is incomplete regardless
  of how good the assigned peaks look, and is the finding that sends the
  sample back for rerun on a second column.

## Workflow

1. Validate the peak list: every peak needs an identifier, a positive
   retention index and a positive integrated area. A missing area is an
   input error, not a zero.
2. Validate the library: entries need a compound name, a reference retention
   index and, where relevant, the flag saying the compound drives the
   toxicity assessment.
3. For each peak, find the best library candidate, measure its retention-index
   deviation against the declared window and read its spectral match score.
4. Grade the assignment: confirmed when both the window and the confirmation
   score threshold are met, tentative when only the weaker tentative
   threshold is met, unidentified otherwise. Treat a score sitting exactly on
   a threshold as meeting it, absorbing representation error with a named
   tolerance.
5. Detect co-elution: order the peaks by retention index and mark every
   adjacent pair whose separation is below the resolution floor, downgrading
   both members to tentative pending a second technique.
6. Downgrade any toxicity-driving assignment that carries no orthogonal
   confirmation, and record why.
7. Sum the area of the peaks left unidentified, express it as a fraction of
   total integrated area, and compare it with the declared budget.
8. Report the graded inventory, the unidentified fraction, and every finding:
   co-elution held back, unconfirmed driver, budget exceeded.

## Pitfalls

- Accepting the top library hit because it is the top hit. A ranked list
  always has a first entry; the score and the retention window decide whether
  that entry is an assignment or a guess.
- Dropping unidentified peaks from the area accounting so the identified
  fraction reads as one hundred per cent. That converts an incomplete
  inventory into an apparently complete one.
- Reporting a tentative assignment with the same weight as a confirmed one.
  The grade travels with the compound into the concentration and toxicity
  steps and has to survive the trip.
- Splitting a co-eluting pair into two confident assignments. The spectra are
  mixtures; the pair is one unresolved observation until a second technique
  separates it.
- Widening the retention-index window until a stubborn peak lands inside it.
  The window is a property of the column and the reference set, not a dial to
  be turned per sample.

## Behavior contract (gate 3)

The peak and library validation, retention-window grading, match-score
thresholds, co-elution detection, orthogonal-confirmation downgrade and
unidentified-area accounting are exercised by the gate 3 contract test:
scripts/test_q7029_product_identification.py against
scripts/q7029_product_identification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7029_product_identification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
