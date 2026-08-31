# AeroSkills FAQ

Answers grounded in the repo as it stands. Where a claim points at an
artifact, the artifact is named so you can check it yourself.

## Is AeroSkills certified?

No. AeroSkills is not a certification body, and nothing here is
approved by FAA, EASA, RTCA, SAE, or IAQG for any specific program.
The skills encode methodology: the planning, DAL determination, and
verification steps that live inside certified workflows. The
standards themselves remain the authority and must be purchased from
their publishers (STANDARDS.md).

## What is the export-control status?

As published, AeroSkills is not controlled technical data; verify
before use. The library is open and unrestricted, Apache-2.0, and
contains general engineering principles and process guidance, not
design data for specific articles. Users are responsible for their
own compliance with the export-control and sanctions laws that apply
to their use. The compliance notice at the top of the README states
the legal basis.

## Do you reproduce standards text?

No. The summary-not-copy rule (STANDARDS.md) allows only name +
paraphrase + short attributed quotes under 100 words + a link to the
publisher. Gated standards (DO-178C, DO-254, ARP4754A, ARP4761A,
AS9100) never appear verbatim anywhere in this repository. A real
gate enforces it: make validate runs a no-verbatim scan over skills/
and docs/ and requires zero matches.

## What does "verified" mean?

A skill is marked verified only when make validate passes: 5 REAL
gates covering spec conformance, description quality, a behavior test
for DAL determination, the no-verbatim scan, and a Hit@1 routing
corpus. The run is deterministic and offline. You can replay it:
clone the repo and run make validate; exit 0 means the gates pass on
that commit. It means nothing more. It is not certification, not
approval, and not a guarantee of airworthiness.

## What license is it under?

Apache-2.0. The full text is in LICENSE; NOTICE names the publisher,
Ashforde OU (Estonia). Standards remain the property of their
publishers.

## Which tools work with these skills?

Any host that loads SKILL.md files per the agentskills.io format:
Claude Code, Hermes, OpenClaw, Codex, and 20+ others. Skills are
plain files, so there is no lock-in. Each skill declares its
compatibility in frontmatter.

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

No. AeroSkills is not affiliated with or endorsed by RTCA, EUROCAE,
SAE International, IAQG, EASA, FAA, or any government.
