# Contributing to Aero Agent Skills

Aero Agent Skills is an open library of civil aerospace engineering methodology
for AI agents, published by Ashforde OÜ (Estonia) under Apache-2.0.

## Ground rules (AGENTS.md)

- ONE main branch; every change lands on main as a complete commit.
- Every commit is complete: code + docs + tests + state together.
- Clean at rest: zero uncommitted files.
- Test-first: failing test → fix → passing test.
- Evidence over claims: no finding ships without receipts.

## Contribution workflow

1. Read AGENTS.md and docs/harness-contract.md before starting.
2. For non-trivial work, open an issue or discussion first so the change
   is scoped and agreed.
3. Build the change with its tests. The harness gate suite is the
   definition of done for any skill or tooling change:

       make validate
       make attest
       bash ops/automation/test/run-tests.sh

4. Commit as ONE complete unit on main (see DCO below) and push.
5. CI (`.github/workflows/attest.yml`) re-runs `make validate` and
   `make attest` on every push.

## Contributor certification

By submitting a contribution, you certify that your submission:

(a) contains no ITAR/EAR/USML-controlled technical data (no specific
    designs, dimensions, tolerances, materials, part numbers, or
    performance parameters of USML/600-series defense articles);
(b) contains no classified content of any jurisdiction;
(c) contains no verbatim text from proprietary standards — including
    DO-178C, DO-254, ARP4754A, ARP4761A, AS9100, and similar — and no
    material from illegally hosted copies of those standards.

Standards are referenced and summarized, never reproduced. The
summary-not-copy rule is defined in research/briefs/06-legal-export-control.md
section 5.2 and enforced by the no-verbatim gate (docs/harness-contract.md
gate 4). State this certification in your pull request description, or in
the commit body for direct pushes.

## Developer Certificate of Origin (DCO)

Every commit must carry a sign-off trailer, which you add with:

    git commit -s

By signing off you attest to the Developer Certificate of Origin, version
1.1:

    Developer Certificate of Origin
    Version 1.1

    Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

    Everyone is permitted to copy and distribute verbatim copies of this
    license document, but changing it is not allowed.

    Developer's Certificate of Origin 1.1

    By making a contribution to this project, I certify that:

    (a) The contribution was created in whole or in part by me and I have
        the right to submit it under the open source license indicated in
        the file; or

    (b) The contribution is based upon previous work that, to the best of
        my knowledge, is covered under an appropriate open source license
        and I have the right under that license to submit that work with
        modifications, whether created in whole or in part by me, under
        the same open source license (unless I am permitted to submit
        under a different license), as indicated in the file; or

    (c) The contribution was provided directly to me by some other person
        who certified (a), (b) or (c) and I have not modified it.

    (d) I understand and agree that this project and the contribution are
        public and that a record of the contribution (including all
        personal information I submit with it, including my sign-off) is
        maintained indefinitely and may be redistributed consistent with
        this project or the open source license(s) involved.

The sign-off trailer looks like:

    Signed-off-by: Your Name <you@example.com>

`git commit -s` appends it automatically using your git user.name and
user.email.

## Review gate

Contributions are reviewed by the project maintainers before merge; the
review covers correctness, the harness gates, and the contributor
certification above. Standards are referenced/summarized — never
reproduced.
