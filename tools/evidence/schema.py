#!/usr/bin/env python3
"""The evidence record schema, and a validator for it.

aero.evidence.record/1.0.0

    {
      "kind":            "aero.evidence.record",
      "schema_version":  "1.0.0",
      "record_id":       "er_<16 hex>",           derived, not allocated
      "body":            { ... the sealed content, below ... },
      "seal":            {"algorithm","canonicalization","body_digest"},
      "amendments":      [ ... append-only, never rewrites body ... ],
      "telemetry":       { ... OUTSIDE the seal, see below ... }
    }

body
    issued          when, by whom, with which tool
    subject         what the verdict is about (a leaf, by repository-relative
                    path - never an absolute path)
    corpus          content hash of the corpus subtree in scope, with the
                    file and byte counts behind it
    leaf            content hash of the subject and of each of its files
    versions        harness_runtime and specification, as SEPARATE fields
    standards       the editions in scope, each with issue and date
    environment     the facts determinism depends on
    checker_set     every rule applied, with its parameters and their digest
    observations    the measured facts, threshold-free, one per observer
    gates           one outcome per checker, citing the observation it read
    verdict         the roll-up
    derivation      original, or a regrade naming its parent

telemetry sits outside the seal on purpose.  Wall-clock durations are not
reproducible, so sealing them would mean two runs of identical work produce
different digests; and they are not evidence, because no checker is allowed
to read them.  Diagnostics travel with the record without being part of it.

The body is sealed by digest.  Nothing ever rewrites it - see record.amend.

Validation here is structural and self-consistency checking, not a JSON
Schema document: a JSON Schema validator is not in the standard library, and
everything in this repository is stdlib-only.  The rules below are the
schema, expressed as code that runs.
"""

import re

from . import canonical

KIND = "aero.evidence.record"
SCHEMA_VERSION = "1.0.0"

_TOP_KEYS = {
    "kind",
    "schema_version",
    "record_id",
    "body",
    "seal",
    "amendments",
    "telemetry",
}
# Optional, not required. An attestation says WHO issued the record; a
# record without one is still a valid record that proves integrity only,
# and every record issued before attestation existed is in that state.
# Keeping these sets separate is what stops a new optional block from
# retroactively invalidating the archive.
_OPTIONAL_TOP_KEYS = {
    "attestation",
}
_ATTESTATION_KEYS = {
    "algorithm",
    "context",
    "key_id",
    "public_key",
    "issuer",
    "signature",
}
_BODY_KEYS = {
    "issued",
    "subject",
    "corpus",
    "leaf",
    "versions",
    "standards",
    "environment",
    "checker_set",
    "observations",
    "gates",
    "verdict",
    "derivation",
}
_AMENDMENT_KEYS = {
    "seq",
    "at",
    "author",
    "reason",
    "pointer",
    "prior_value",
    "new_value",
    "view_digest_before",
    "view_digest_after",
}

# A record travels to people who must not learn the issuer's filesystem.
_ABSOLUTE_PATH = re.compile(r"(^/[A-Za-z]|/Users/|/home/|[A-Za-z]:\\)")

VERDICTS = ("PASS", "FAIL", "INDETERMINATE", "WITHDRAWN", "NOT_APPLICABLE")


def _walk_strings(node, path="body"):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from _walk_strings(value, "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            yield from _walk_strings(value, "%s[%d]" % (path, index))


def absolute_path_strings(body):
    """Every string in the body that looks like a filesystem path."""
    return [
        (path, text)
        for path, text in _walk_strings(body)
        if _ABSOLUTE_PATH.search(text)
    ]


def validate(record):
    """Structural validation.  Returns a list of error strings; empty is good."""
    errors = []
    if not isinstance(record, dict):
        return ["record is not an object"]
    missing = _TOP_KEYS - set(record)
    if missing:
        errors.append("missing top-level key(s): %s" % ", ".join(sorted(missing)))
    extra = set(record) - _TOP_KEYS - _OPTIONAL_TOP_KEYS
    if extra:
        errors.append("unexpected top-level key(s): %s" % ", ".join(sorted(extra)))
    attestation = record.get("attestation")
    if attestation is not None:
        if not isinstance(attestation, dict):
            errors.append("attestation must be an object")
        else:
            att_missing = _ATTESTATION_KEYS - set(attestation)
            if att_missing:
                errors.append("attestation missing key(s): %s"
                              % ", ".join(sorted(att_missing)))
            att_extra = set(attestation) - _ATTESTATION_KEYS
            if att_extra:
                errors.append("unexpected attestation key(s): %s"
                              % ", ".join(sorted(att_extra)))
            # Shape only. Whether the signature is VALID, and whether the
            # key is one anybody trusts, is signing.verify()'s question --
            # the schema must not imply an answer it did not compute.
            for field, width in (("signature", 128), ("public_key", 64)):
                value = attestation.get(field)
                if isinstance(value, str) and len(value) != width:
                    errors.append("attestation.%s is %d hex chars, expected %d"
                                  % (field, len(value), width))
    if record.get("kind") != KIND:
        errors.append("kind is %r, expected %r" % (record.get("kind"), KIND))
    version = str(record.get("schema_version", ""))
    if not version.startswith("1."):
        errors.append("schema_version %r is not a 1.x record" % version)
    if not re.fullmatch(r"er_[0-9a-f]{16}", str(record.get("record_id", ""))):
        errors.append("record_id %r is not er_<16 hex>" % record.get("record_id"))

    body = record.get("body")
    if not isinstance(body, dict):
        errors.append("body is not an object")
        return errors
    body_missing = _BODY_KEYS - set(body)
    if body_missing:
        errors.append("body is missing %s" % ", ".join(sorted(body_missing)))
    body_extra = set(body) - _BODY_KEYS
    if body_extra:
        errors.append("body has unexpected key(s): %s" % ", ".join(sorted(body_extra)))

    for path, text in absolute_path_strings(body):
        errors.append("absolute path leaked into the record at %s: %r" % (path, text))

    seal = record.get("seal")
    if not isinstance(seal, dict):
        errors.append("seal is not an object")
    else:
        if seal.get("canonicalization") != canonical.CANONICALIZATION:
            errors.append(
                "seal canonicalization is %r, expected %r"
                % (seal.get("canonicalization"), canonical.CANONICALIZATION)
            )
        try:
            actual = canonical.digest(body)
        except canonical.CanonicalError as exc:
            actual = None
            errors.append("body is not canonically encodable: %s" % exc)
        if actual is not None and seal.get("body_digest") != actual:
            errors.append(
                "seal is broken: body digest is %s, seal says %s"
                % (actual, seal.get("body_digest"))
            )

    gates = body.get("gates")
    if not isinstance(gates, list):
        errors.append("body.gates is not a list")
    else:
        observations = body.get("observations") or {}
        for gate in gates:
            gate_id = gate.get("gate")
            verdict = gate.get("outcome", {}).get("verdict")
            if verdict not in VERDICTS:
                errors.append("gate %s has verdict %r" % (gate_id, verdict))
            name = gate.get("observation")
            stored = observations.get(name)
            if stored is None:
                if gate.get("observation_digest") is not None:
                    errors.append(
                        "gate %s cites observation %r that the record does not carry"
                        % (gate_id, name)
                    )
            else:
                expected = canonical.digest(stored)
                if gate.get("observation_digest") != expected:
                    errors.append(
                        "gate %s cites observation digest %s but %r digests to %s"
                        % (gate_id, gate.get("observation_digest"), name, expected)
                    )

    amendments = record.get("amendments")
    if not isinstance(amendments, list):
        errors.append("amendments is not a list")
    else:
        for index, amendment in enumerate(amendments):
            if not isinstance(amendment, dict):
                errors.append("amendment %d is not an object" % index)
                continue
            gap = _AMENDMENT_KEYS - set(amendment)
            if gap:
                errors.append(
                    "amendment %d is missing %s" % (index, ", ".join(sorted(gap)))
                )
            if amendment.get("seq") != index + 1:
                errors.append(
                    "amendment %d has seq %r; amendments are numbered from 1 in order"
                    % (index, amendment.get("seq"))
                )
            if not str(amendment.get("pointer", "")).startswith("/"):
                errors.append("amendment %d pointer is not a JSON pointer" % index)
            if not str(amendment.get("reason", "")).strip():
                errors.append("amendment %d records no reason" % index)
            if not str(amendment.get("author", "")).strip():
                errors.append("amendment %d records no author" % index)
    return errors
