#!/usr/bin/env python3
"""Building, sealing, amending and verifying an evidence record.

The append-only rule, concretely
--------------------------------
A post-hoc change never edits the body.  It appends an amendment naming the
author, the reason, the JSON pointer it applies to, and the value that stood
there before.  The body someone sealed on the day the verdict issued is
byte-for-byte the body a reader gets years later; the amended reading is
computed by replaying the amendments over it, in order, on demand.

That choice costs a function call at read time and buys three things: the
seal never needs re-issuing, "what did it say originally" needs no archive
to answer, and a party who disputes an amendment can point at the exact
entry that made the change and at who signed for it.

Each amendment also stores the digest of the view before and after itself, so
the chain is verifiable end to end: delete one from the middle and the next
entry's before-digest stops matching.
"""

import json
import os
import time

from . import canonical, checkers, corpus, environment, observers, schema, standards

TOOL_ID = "aero-evidence"
TOOL_VERSION = "1.0.0"
HARNESS_RUNTIME_ID = "aero-evidence-harness"
HARNESS_RUNTIME_VERSION = "1.0.0"

# The conformance specification is versioned separately from the harness that
# implements it, because they move for different reasons: a harness fix is a
# software release, a specification change is a change to what conformance
# MEANS.  No published specification document exists yet, so the version below
# is this tool's declaration of the contract it implements, bound to the
# in-tree harness contract by digest so that the document it tracks cannot
# drift without the binding changing.
SPECIFICATION_ID = "aero-conformance-spec"
SPECIFICATION_VERSION = "0.1.0-draft"
SPECIFICATION_SOURCE = "docs/harness-contract.md"


def now_iso(clock=None):
    """UTC timestamp.  SOURCE_DATE_EPOCH pins it for reproducible runs."""
    if clock is not None:
        epoch = clock
    else:
        pinned = os.environ.get("SOURCE_DATE_EPOCH")
        epoch = int(pinned) if pinned else time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


# --------------------------------------------------------------------------
# JSON pointer (RFC 6901), the subset an amendment needs
# --------------------------------------------------------------------------


def _tokens(pointer):
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError("not a JSON pointer: %r" % pointer)
    return [t.replace("~1", "/").replace("~0", "~") for t in pointer[1:].split("/")]


def pointer_get(document, pointer):
    node = document
    for token in _tokens(pointer):
        if isinstance(node, list):
            node = node[int(token)]
        else:
            node = node[token]
    return node


def pointer_set(document, pointer, value):
    tokens = _tokens(pointer)
    if not tokens:
        raise ValueError("cannot replace the whole document")
    node = document
    for token in tokens[:-1]:
        node = node[int(token)] if isinstance(node, list) else node[token]
    last = tokens[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value


# --------------------------------------------------------------------------
# building
# --------------------------------------------------------------------------


def specification_binding(root):
    path = os.path.join(root, SPECIFICATION_SOURCE.replace("/", os.sep))
    digest = canonical.digest_file(path) if os.path.isfile(path) else None
    return {
        "id": SPECIFICATION_ID,
        "version": SPECIFICATION_VERSION,
        "source_ref": SPECIFICATION_SOURCE,
        "source_digest": digest,
        "note": (
            "no separately published conformance specification exists yet; this "
            "version is the tool's declaration of the contract it implements, "
            "bound to the in-tree harness contract by digest"
        ),
    }


def harness_binding():
    return {
        "id": HARNESS_RUNTIME_ID,
        "version": HARNESS_RUNTIME_VERSION,
        "components": {
            "tool": "%s/%s" % (TOOL_ID, TOOL_VERSION),
            "observer_set": observers.OBSERVER_SET_VERSION,
            "observation_specs": dict(observers.OBSERVATION_SPECS),
            "record_schema": schema.SCHEMA_VERSION,
            "canonicalization": canonical.CANONICALIZATION,
            "corpus_digest_spec": corpus.DIGEST_SPEC,
        },
    }


def seal(body, telemetry=None):
    """Wrap a body in its seal and derive the record id from the digest."""
    body_digest = canonical.digest(body)
    return {
        "kind": schema.KIND,
        "schema_version": schema.SCHEMA_VERSION,
        "record_id": "er_" + body_digest.split(":", 1)[1][:16],
        "body": body,
        "seal": {
            "algorithm": canonical.DIGEST_ALGORITHM,
            "canonicalization": canonical.CANONICALIZATION,
            "body_digest": body_digest,
            # Integrity only.  The seal proves the body was not altered after
            # issue; it does NOT prove who issued it.  See DESIGN.md.
            "binds": "integrity",
        },
        "amendments": [],
        # Outside the seal: run diagnostics, not evidence.  No checker reads
        # them and no verdict depends on them, so sealing a wall clock would
        # only make two runs of identical work disagree.
        "telemetry": telemetry or {},
    }


def build(
    root,
    leaf_ref,
    checker_set=None,
    corpus_block=None,
    issuer="unattributed",
    at=None,
    runner=None,
):
    """Observe one leaf, check it, and seal the result."""
    checker_set = checker_set or checkers.build_set()
    corpus_block = corpus_block or corpus.corpus_binding(root)
    leaf_block = corpus.leaf_binding(root, leaf_ref)
    observations, telemetry = observers.observe_leaf(root, leaf_ref, runner=runner)
    shape = observations["spec-shape"]
    standard_ids = [entry["id"] for entry in shape.get("standards") or []]
    gates = checkers.apply_set(checker_set, observations)
    body = {
        "issued": {
            "at": now_iso(at),
            "by": issuer,
            "tool": "%s/%s" % (TOOL_ID, TOOL_VERSION),
        },
        "subject": {
            "kind": "leaf",
            "ref": leaf_ref,
            "name": shape.get("name"),
            "domain": shape.get("domain"),
            "pack": shape.get("pack"),
        },
        "corpus": corpus_block,
        "leaf": leaf_block,
        "versions": {
            "harness_runtime": harness_binding(),
            "specification": specification_binding(root),
        },
        "standards": standards.in_scope(root, standard_ids),
        "environment": environment.capture(),
        "checker_set": checker_set,
        "observations": observations,
        "gates": gates,
        "verdict": checkers.roll_up(gates),
        "derivation": {"kind": "original"},
    }
    return seal(body, telemetry=telemetry)


# --------------------------------------------------------------------------
# amending
# --------------------------------------------------------------------------


def current_view(record):
    """The body as it reads today: the original with amendments replayed."""
    view = json.loads(json.dumps(record["body"]))
    for amendment in record.get("amendments") or []:
        pointer_set(view, amendment["pointer"], amendment["new_value"])
    return view


def amend(record, author, reason, pointer, new_value, at=None):
    """Append a post-hoc change.  The body is not touched."""
    if not str(author).strip():
        raise ValueError("an amendment must name its author")
    if not str(reason).strip():
        raise ValueError("an amendment must record its reason")
    if pointer.startswith("/seal") or pointer.startswith("/amendments"):
        raise ValueError("an amendment may not target the seal or the history")
    if pointer.startswith("/body/"):
        pointer = pointer[len("/body") :]
    before = current_view(record)
    try:
        prior = pointer_get(before, pointer)
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError("pointer %s does not resolve in the record: %s" % (pointer, exc))
    if prior == new_value:
        raise ValueError("amendment would change nothing at %s" % pointer)
    after = json.loads(json.dumps(before))
    pointer_set(after, pointer, new_value)
    entry = {
        "seq": len(record.get("amendments") or []) + 1,
        "at": now_iso(at),
        "author": author,
        "reason": reason,
        "pointer": pointer,
        "prior_value": prior,
        "new_value": new_value,
        "view_digest_before": canonical.digest(before),
        "view_digest_after": canonical.digest(after),
    }
    amended = dict(record)
    amended["amendments"] = list(record.get("amendments") or []) + [entry]
    return amended


def verify_history(record):
    """Replay the amendment chain and report any break."""
    problems = []
    view = json.loads(json.dumps(record["body"]))
    for index, amendment in enumerate(record.get("amendments") or []):
        before_digest = canonical.digest(view)
        if amendment.get("view_digest_before") != before_digest:
            problems.append(
                "amendment %d claims a prior view of %s but the replayed view is %s "
                "(an entry was removed, reordered or edited)"
                % (index + 1, amendment.get("view_digest_before"), before_digest)
            )
        try:
            actual_prior = pointer_get(view, amendment["pointer"])
        except (KeyError, IndexError, ValueError):
            problems.append(
                "amendment %d points at %s, which does not resolve"
                % (index + 1, amendment.get("pointer"))
            )
            continue
        if actual_prior != amendment.get("prior_value"):
            problems.append(
                "amendment %d records a prior value that is not what stood there"
                % (index + 1)
            )
        pointer_set(view, amendment["pointer"], amendment["new_value"])
        if amendment.get("view_digest_after") != canonical.digest(view):
            problems.append("amendment %d's after-digest does not match" % (index + 1))
    return problems


def verify(record, recompute=True):
    """Full verification: structure, seal, history, and re-derived verdicts."""
    report = {
        "record_id": record.get("record_id"),
        "subject": record.get("body", {}).get("subject", {}).get("ref"),
        "schema_errors": schema.validate(record),
        "history_errors": verify_history(record),
        "rederivation": None,
    }
    if recompute and not report["schema_errors"]:
        body = record["body"]
        set_used = body["checker_set"]
        known = []
        unknown = []
        for entry in set_used["checkers"]:
            checker = checkers.REGISTRY.get(entry["id"])
            if checker is None or checker.version != entry["version"]:
                unknown.append(
                    "%s@%s" % (entry["id"], entry["version"])
                )
            else:
                known.append(entry)
        mismatches = []
        if not unknown:
            gates = checkers.apply_set(set_used, body["observations"])
            stored = {g["gate"]: g["outcome"]["verdict"] for g in body["gates"]}
            for gate in gates:
                if stored.get(gate["gate"]) != gate["outcome"]["verdict"]:
                    mismatches.append(
                        "%s: stored %s, re-derived %s"
                        % (
                            gate["gate"],
                            stored.get(gate["gate"]),
                            gate["outcome"]["verdict"],
                        )
                    )
        report["rederivation"] = {
            "possible": not unknown,
            "unavailable_checkers": unknown,
            "mismatches": mismatches,
        }
    report["ok"] = not (
        report["schema_errors"]
        or report["history_errors"]
        or (report["rederivation"] or {}).get("mismatches")
    )
    return report


# --------------------------------------------------------------------------
# storage
# --------------------------------------------------------------------------


def filename_for(record):
    ref = record["body"]["subject"]["ref"].replace("/", "__")
    return "%s.%s.json" % (ref, record["record_id"])


def save(record, directory):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename_for(record))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(canonical.dumps_pretty(record))
    return path


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_directory(directory):
    out = []
    for name in sorted(os.listdir(directory)):
        if name.endswith(".json"):
            out.append((os.path.join(directory, name), load(os.path.join(directory, name))))
    return out
