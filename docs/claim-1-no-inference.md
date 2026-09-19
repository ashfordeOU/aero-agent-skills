# Claim 1 — No model inference in the graded path

Status: normative text for `claim@1`. Machine-enforced by
`scripts/gate_no_inference.py` from 2026-09-19. Not advisory: the build fails
when the invariant is broken.

---

## 1. The invariant

> **Nothing reachable from a verdict performs, or arranges for, model
> inference.** Every verdict this product issues is computed by a rule base
> that is fixed at design time, fully specified in the repository, and
> verified by ordinary software-engineering methods — deterministically,
> offline, and reproducibly from the inputs alone.

A *verdict* is any pass/fail, score, ranking or conformance statement the
product emits: a gate result, a router selection, a leaf logic module's
finding, or an attestation derived from those.

The *graded path* is everything that can be reached while computing a
verdict — the shipped corpus, the verification harness, and the distribution
that carries them to a user.

## 2. What this claim does **not** say

This matters as much as what it does say, and an auditor should read it
first.

- It does **not** say no model is involved anywhere near the product. The
  corpus is a library of agent skills; the thing that *reads* a skill and
  applies it to a user's problem is, normally, a large language model running
  in the user's own harness. That is the intended use.
- The claim is about the **other side** of that boundary: the corpus itself,
  the router that selects within it, the logic each leaf executes, and the
  gates that grade all of it contain no inference. What the product asserts
  about a skill is computed, not generated — so it can be re-run by a third
  party and land on the same answer.
- It does **not** restrict what the documentation may discuss. A skill, a
  design note or a README may name model vendors, describe model behaviour
  and quote model identifiers freely. The claim constrains what the code
  **does**, never what the corpus is allowed to talk about.
- It does **not** forbid model-assisted authoring off the graded path.
  Authoring tools may use models, provided they are named in the gate's
  exemption list with a reason, are not invoked by any gate, the router or a
  leaf, and their output is reviewed and then subjected to the full gate
  battery like any other human edit.

## 3. Why the line is drawn exactly here

Two independent reasons, either of which would be sufficient.

**Regulatory (paraphrased; no source text is reproduced here).** Current
European aviation-safety guidance for AI scopes itself deliberately. A
non-learning expert system — one whose rule or knowledge base is frozen at
design time, completely specified, and verified with established
software-engineering methods — sits outside that guidance and is treated as
ordinary software, with all the assurance routes that implies. The same
guidance places a hard ceiling on large general-purpose models taken off the
shelf, admitting them only at the weakest level of assurance it recognises.
The distinction is structural and binary. It is not a matter of how much
inference is used, how carefully it is prompted, or how the output is
post-checked: a single model call on the path that produces a verdict moves
the whole product to the far side of the line, and no amount of documentation
moves it back.

**Evidential.** A model call is not reproducible. It is served by a weight
set the caller does not hold, does not version, and cannot pin; the same
input can yield a different output tomorrow. A verdict that depends on one
cannot be re-derived by an auditor, cannot be replayed against an archived
build, and cannot support a conformance mark that is supposed to mean the
same thing in two years' time. Determinism is the asset being sold.

The cost of holding this line is near zero today and rises monotonically.
Removing an inference call from a product with no users is an afternoon.
Removing one from a product whose customers hold attestations issued under
this claim is a recall.

## 4. What is forbidden

Within the graded path, code MUST NOT:

1. **Import a model SDK or client** — hosted-model vendor SDKs, local-model
   bindings and runners, aggregation layers, and model-orchestration
   frameworks.
2. **Import a trained-model runtime.** A learned model is still a model even
   when it is not a language model. The "fixed at design time" half of the
   claim fails the moment a verdict depends on fitted weights.
3. **Open network egress**, by any primitive or client library. Egress is
   forbidden both because it is the generic route to a hosted model and
   because an offline build is independently required: a verdict must be
   reproducible on a disconnected machine.
4. **Start a local model runner**, by subprocess, exec, spawn or shell.
5. **Open a client against a managed inference service.** This route needs no
   model-named import at all — a general cloud SDK plus a service-name string
   is enough — so the service names are enumerated explicitly.
6. **Read a credential that only an inference call would need** — a vendor
   API key, auth token, base URL or endpoint override. Presence of such a
   read is treated as intent, whether or not a call is visible in the same
   file.
7. **Indirect around any of the above** — a computed or dynamic import, a
   wrapper binary, a shell string assembled at run time. Indirection is
   enumerated as its own prohibited class so that evading the gate requires
   evading a named rule, not merely finding a spelling it missed.

## 5. Where it is enforced

`scripts/gate_no_inference.py`. Stdlib only, offline, deterministic; exits
non-zero on any finding and names every offending file and line.

- **Python is matched on parsed structure** (`ast`), never on raw source
  text. Text matching over code fails in both directions: it fires on a
  vendor name inside a comment and it misses an import assembled from
  fragments. This estate has a recorded incident in which a regex word
  boundary matched inside a number and the repair script then corrupted every
  figure it touched; the same class of mistake is not acceptable in the file
  that carries the product's central claim.
- **Regex is used only for the non-Python graded files** (JavaScript,
  TypeScript, shell, Kotlin), because the standard library ships no parser
  for them. Those patterns anchor on syntactic delimiters — a quote, a paren,
  a command separator — and never on a bare word boundary. Environment
  variable names are matched by whole underscore-separated segments, so a
  vendor token cannot match inside a longer identifier.
- **Both front ends share one policy.** The module, binary, service, host and
  credential tables are single definitions consumed by the parser path and
  the regex path alike, so the two cannot drift apart.
- **Scope is positive and explicit.** A file is graded when it lives under a
  declared graded tree *and* carries an executable-code suffix. Prose and
  data files are never scanned. Development-only tooling is out of scope only
  by name, in a table where each entry carries a reason — and every exemption
  is printed on every green run, because a silent allowlist is how an
  invariant like this rots.
- **It extends, rather than duplicates, the existing corpus import check.**
  `scripts/check_stdlib_imports.py` (gate 3) is an allowlist of standard
  library module names applied only to contract test files, and its allowlist
  admits `socket`. So the leaf logic module that actually computes an answer
  was never covered by it, and its most direct route to egress was permitted.
  This gate reuses that check's role for test files and extends the
  network-egress rule, by parse, across every graded file.

Wiring into the make targets is done centrally; the intended target name is
`no-inference`, added to the `validate` chain.

## 6. What a conformant implementation must demonstrate

An implementation claiming `claim@1` must be able to show, on demand:

1. **The gate exists and runs in the build**, and a failing gate fails the
   build. Evidence: the gate invoked from the verification target, with its
   exit status honoured.
2. **A green run over the whole graded path**, with the file counts it
   scanned. A pass with no denominator is not evidence.
3. **A negative control.** The gate must be shown to *fail* — a deliberately
   planted inference call inside the graded path, detected and named. A gate
   that has only ever been seen green has not been shown to work.
4. **The exemption list, with reasons**, and an argument that no exempt file
   is reachable from a verdict: not imported by a gate, the router or a leaf,
   and not invoked by any build target.
5. **Reproducibility.** The same inputs produce the same verdict on a second
   machine with no network access.
6. **Version binding.** The policy tables ship with the claim version, so
   "conformant to `claim@1`" names a specific set of prohibitions, not a
   moving one.

## 7. Changing this is a breaking change

The invariant is the product. Admitting any exception — a "small" model call,
a cached model result, an optional online mode, a learned ranker in the
router — is a **major version change to the claim specification**, not a
configuration option and not a minor release. It requires, at minimum:

- a new claim version (`claim@2` or later); `claim@1` conformance does not
  carry over, and cannot be granted to a build that contains the exception;
- every attestation and conformance mark to state the claim version it was
  issued under, so previously issued marks remain meaningful and are not
  retroactively weakened;
- a public changelog entry stating what became permitted and why;
- re-attestation of the corpus under the new claim version;
- an updated scope statement for the mark, since the argument that the graded
  path is ordinary deterministic software no longer holds unmodified.

There is no path by which the invariant is relaxed quietly. That is the
point of writing it down here and enforcing it in the build rather than
asserting it in marketing copy.
