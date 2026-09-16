---
name: e2008-blocking-diode-qualification-samples
description: "Use when the samples submitted to a blocking diode qualification campaign have to be shown to match the declared process. Verify that every sample entering blocking diode qualification was built by the process identification document ECSS-E-ST-20-08C clause 12.5.4 declares: refuse a description carrying no reference, no issue or no parameter band, hold each sample to the issue that was in force, catch one whose build predates that issue, take every declared build parameter against its own band with a value on the limit admissible, keep a parameter nobody recorded apart from one that drifted, and name each sample rather than the first. Trigger: ecss, e-st-20-08c, blocking-diode-qualification-sample-conformance, blocking-diode-process-identification-document, blocking-diode-sample-build-parameter-band, blocking-diode-sample-issue-match, blocking-diode-sample-build-chronology."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-qualification-samples, blocking-diode-qualification-sample-conformance, blocking-diode-process-identification-document, blocking-diode-sample-build-parameter-band, blocking-diode-sample-issue-match, blocking-diode-sample-build-chronology]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Blocking Diode Qualification Samples (space-systems/ecss/e2008-blocking-diode-qualification-samples)

Use when the task is clause 12.5.4 of ECSS-E-ST-20-08C: diodes are about to
be committed to a qualification campaign, and each one is admissible only if
it was built by the process the supplier has identified in writing. This leaf
grades the submitted set on document identity, on issue, on build
chronology, on construction and on every declared build parameter.

## Domain quick reference

- The baseline is a named, issued document. A process description with no
  reference and no issue cannot be a qualification baseline, because nobody
  can say afterwards which text the samples were built to. An unreferenced or
  unissued description closes the assessment instead of passing it.
- The issue is as load-bearing as the reference. A sample built to issue B,
  against a qualification being claimed for issue C, was built by a different
  process however familiar the reference on its traveller looks.
- Chronology carries the same argument. A sample whose build predates the day
  its cited issue took effect cannot have been built by that issue, and that
  is a record defect worth catching before the data pack is presented rather
  than after.
- Construction is part of the document's scope, not a detail. A mesa part
  submitted against a planar process description is outside what the document
  describes, and qualifying it establishes nothing about the planar build.
- Build parameters are judged against the bands the document declares, not
  against what the shop can reliably hold. A value exactly on a declared limit
  is inside the band; the comparison tolerance absorbs representation error
  rather than widening the document.
- Band utilisation is worth as much as the verdict. A sample conforming at
  five per cent of band and one conforming at ninety-eight per cent carry the
  same word and say completely different things about whether the delivered
  lot will conform too.
- A declared parameter with nothing recorded against it is not a pass. It is
  unestablished, and it is reported apart from a measured value that drifted,
  because the two are repaired by different actions.

## Workflow

1. Validate the conformance policy first: the largest nonconforming share the
   submitted set may carry, and the band utilisation at which a conforming
   sample is called marginal. A share above one, or a marginal point above
   one, is refused rather than used.
2. Validate the process identification document: a non-blank reference and
   issue, a non-negative effective day, a declared construction, and at least
   one build parameter band with a positive tolerance. A parameter declared
   twice is a transcription defect and is refused.
3. Validate every submitted sample record: a non-blank identifier, no
   duplicate identifier, a cited reference and issue, a non-negative build
   day, a declared construction and a mapping of measured build parameters.
   An empty submitted set is refused rather than reported as clean.
4. Judge each sample on identity, issue, construction and chronology, and
   then on every parameter the document declares. Record the band utilisation
   for each and keep the deepest one as the sample's worst.
5. Name every reason a sample failed, not only the first, and hold an
   unrecorded parameter apart from one outside its band.
6. Take the nonconforming share of the submitted set against the declared
   allowance, a share landing exactly on the allowance being admissible.
7. Report the worst sample and its band utilisation beside the verdict, and
   raise a marginal advisory for every conforming sample at or past the policy
   utilisation. Advisories are reported with the verdict and do not move it.
8. Close on one verdict: process identification not established, samples do
   not conform to process identification, or samples conform.

## Pitfalls

- Matching the document reference and stopping there. The issue is what fixes
  the process, and a correct reference at the wrong issue is the commonest way
  a campaign qualifies a build nobody will deliver.
- Reading the build date as decoration. A sample built before its cited issue
  took effect was built by whatever preceded it, and the traveller citation is
  then simply wrong.
- Treating a missing parameter value as a pass because nothing contradicts the
  document. Nothing establishes it either, and the two states are repaired by
  different actions.
- Judging parameters against shop capability rather than the declared band.
  Capability describes what the line does; the document describes what the
  qualification is being claimed for.
- Reporting a pass with no band utilisation. A set that conforms against its
  process limits will not conform again after any drift, and the word alone
  hides that from the next lot review.

## Behavior contract (gate 3)

The policy validation, the process identification validation, the per-sample
judgement on reference, issue, construction and chronology, the band
utilisation of every declared parameter with a value on the limit admitted,
the unrecorded-parameter state, the nonconforming share against its
allowance, the worst sample, the marginal advisories and the conformance
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_qualification_samples.py against
scripts/e2008_blocking_diode_qualification_samples_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_qualification_samples.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
