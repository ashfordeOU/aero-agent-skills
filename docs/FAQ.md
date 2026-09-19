# Aero Agent Skills FAQ

Answers grounded in the repo as it stands. Where a claim points at an
artifact, the artifact is named so you can check it yourself.

## Is Aero Agent Skills certified?

No. Aero Agent Skills is not a certification body, and nothing here is
approved by FAA, EASA, RTCA, SAE, or IAQG for any specific program.
The skills encode methodology: the planning, DAL determination, and
verification steps that live inside certified workflows. The
standards themselves remain the authority and must be purchased from
their publishers (STANDARDS.md).

## What is the export-control status?

As published, Aero Agent Skills is not ITAR- or EAR-controlled technical
data, and EU dual-use export authorization does not apply
(public-domain exclusion, Regulation (EU) 2021/821, Annex I General
Technology Note). Verify before use. The library is open and
unrestricted, Apache-2.0, and contains general engineering principles
and process guidance, not design data for specific articles. Users
are responsible for their own compliance with the export-control and
sanctions laws that apply to their use. The compliance notice at the
top of the README states the legal basis.

## Do you reproduce standards text?

No, and here is how far the enforcement actually goes. The
summary-not-copy rule (STANDARDS.md) allows only name + paraphrase +
short attributed quotes under 100 words + a link to the publisher, and
every skill here is written to it.

Gate 4 (make no-verbatim) enforces that rule in three parts:
publisher-boilerplate markers for every family whose publisher stamps
its documents; a source-text comparison (one-way shingle fingerprints
against the publisher's own documents) for every family whose sources
are indexed; and objective-table block detection. It scans skills/,
docs/, README.md, STANDARDS.md and NOTICE.

One family is source-compared today: ECSS, which covers most of the
library. Eight more get the marker check only, which catches a pasted
page and would not catch a retyped paragraph. Five are reported
UNCHECKED, because their sources (US Government works and an open
specification) carry no boilerplate to match and no source index exists
for them. An unchecked family is not a proven-clean family, and the
gate refuses to print PASS over one: every run names each family, the
number of leaves citing it, and the check it received.

So: no verbatim text is intended, none has been found, and for thirteen
of the fourteen families "none found" rests on the marker check or on
nothing at all rather than on a comparison against the source. The
per-family table is in docs/harness-contract.md; make no-verbatim
reproduces it on your own checkout.

## What does "verified" mean?

A skill is marked verified when the whole offline battery passes on the
commit that ships it. make validate runs spec lint, description lint,
the per-skill behavior contract, the no-verbatim scan, the Hit@1 router
corpus, verifier independence, release law, numeric portability and
corpus-fragment naming. make attest adds the number snapshot, the brief
audit and the content-policy sweep. The run is deterministic and
offline, and you can replay it: clone the repo, run both, exit 0 means
the gates pass on that commit.

It means nothing more, and two limits belong in the same breath. The
Hit@1 corpus carries queries for a minority of the leaves, so most
skills are spec-linted and behavior-tested but never router-asserted.
The no-verbatim gate compares source text for one standards family out
of fourteen; the rest are markers-only or UNCHECKED. Both figures, with
their complements and the command that produces each, are in
docs/harness-contract.md.

Verified is not certification, not approval, and not a guarantee of
airworthiness.

## What does the harness not check?

Four things, stated so that nobody has to infer them.

1. Engineering correctness. A skill's contract test and the logic module
   it exercises are authored together, so a shared misconception passes
   both. The gate proves the module behaves as its own contract says.
2. Routing for a leaf the corpus has no query for. That is most of the
   library today.
3. Verbatim reuse in a standards family with no source index. Markers
   catch a pasted page; nothing catches a retyped paragraph.
4. Anything covered only by a checker that exists in the tree but is
   wired into no make target. docs/harness-contract.md lists those by
   path, because presence is not enforcement.

## What license is it under?

Apache-2.0. The full text is in LICENSE; NOTICE names the publisher,
Ashforde OU (Estonia). Standards remain the property of their
publishers.

## Which tools work with these skills?

Any host that loads SKILL.md files per the agentskills.io format.
Claude Code, Hermes, OpenClaw, and Codex are named examples; this is
a format-level claim, not a per-host test report. Every skill is
validated against the agentskills.io spec by make validate (gate 1),
and any host that reads the format can load them. Skills are plain
files, so there is no lock-in. Each skill declares its compatibility
in frontmatter.

## How do I install?

Clone the repository, run make validate, then add the skills folder
to your host's skills directory. Full steps in the README.

## What does it cost?

Pricing is not public yet. The core library is Apache-2.0 and free.

## How do I contribute or report an issue?

Read CONTRIBUTING.md before opening a PR; every contributor certifies
their submission contains no controlled data and no verbatim
standards text. Report security issues through SECURITY.md.

## Are you affiliated with the standards bodies?

No. Aero Agent Skills is not affiliated with or endorsed by RTCA, EUROCAE,
SAE International, IAQG, EASA, FAA, or any government.
