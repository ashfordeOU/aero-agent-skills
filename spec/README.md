# ARCS-1 is published in one place

ARCS-1, the Agent Run Conformance Specification, is the aerospace profile
of TRACE (Trust, Runtime Attestation and Compliance Evidence), the open
specification for signed evidence about what a software agent ran. ARCS-1
defers to TRACE for everything TRACE defines, and adds only what an
aerospace claim needs: the gate verdicts, the named person who signs off,
and the exact corpus and harness versions.

Its one canonical copy is published, beside the conformance suite that
grades an implementation against it, at:

<https://github.com/ashfordeOU/arcs-conformance/tree/main/spec>

This directory holds a pointer and no copy, on purpose. A second copy is a
second thing that can drift from the first.

| | |
| --- | --- |
| edition named here | 2026-09-26 |
| SHA-256 (Secure Hash Algorithm, 256-bit) of `ARCS-1.md` at that edition | `6d68f8d5d9ea2ec130dacb9c9d2af50cae67008f3a2b77911e5b66f58d05ccec` |

An edition of ARCS-1 never changes once it is published, so the line above
stays true. A later edition supersedes it at the address above, where the
file `SHA256SUMS` names the SHA-256 of the text that is current. To check a
copy you hold of the edition named here:

```sh
shasum -a 256 ARCS-1.md
```

Until 2026-09-26 the specification directory was published here. From that
edition on it is published only at the address above.
