#!/usr/bin/env python3
"""Signed licence records: who is entitled to what, provably.

Same trust root as the evidence record, different statement. An evidence
record says "this is what we measured". A licence record says "this party
holds this entitlement, and we issued that claim".

What this IS
------------
Evidence of entitlement. Signed by the issuing key, verifiable by anyone
against the published trust anchor, and therefore useful in exactly the
places a claim gets tested: a procurement review, an audit, a renewal
dispute, a customer proving to their own regulator that they are entitled
to the corpus they built on.

What this is NOT, stated plainly
--------------------------------
It is NOT technical enforcement, and nothing here should be sold as DRM.
The corpus is Apache-2.0 and public; a licence record does not and cannot
gate access to it. Any offline check can be patched out by whoever runs the
binary, and pretending otherwise builds a product on a promise it cannot
keep. What cannot be patched out is the SIGNATURE: a party without a valid
licence record cannot manufacture one, and that is what makes the record
worth holding and worth buying.

Expiry, and the clock problem
-----------------------------
`valid_until` is checked against a time the CALLER supplies. A verifier's
own clock is under the control of whoever runs it, so an expiry check is
advisory by construction. `verify()` therefore reports expiry as a distinct
state rather than folding it into the signature verdict: the signature is a
fact, the expiry is an opinion about the clock. A caller who wants them
combined must say so.
"""

import json
import os
import sys

if __package__:
    from . import canonical, signing
else:
    _ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from tools.evidence import canonical, signing

KIND = "aeroskills-licence-record"
SCHEMA_VERSION = "1.0"
CONTEXT = "aeroskills-licence-attestation/v1"

VALID = "valid"
EXPIRED = "expired"
NOT_YET_VALID = "not-yet-valid"


def payload(body_digest, licensee):
    """The signed bytes. Distinct context from an evidence attestation, so
    a licence signature can never be replayed as an evidence one."""
    return canonical.canonical_bytes({
        "context": CONTEXT,
        "body_digest": body_digest,
        "licensee": licensee,
    })


def build(licensee, scope, valid_from, valid_until=None, terms=None,
          issuer="ashforde-conformance", grants=None):
    """A licence body and its seal. Unsigned until `attest` is called."""
    if not licensee or not str(licensee).strip():
        raise ValueError("a licence needs a licensee")
    if not scope:
        raise ValueError("a licence needs a scope: an entitlement to "
                         "everything is not an entitlement anyone can check")
    body = {
        "issued": {"by": issuer, "tool": "aero-licence/1.0.0"},
        "licensee": licensee,
        "scope": scope,
        "grants": sorted(grants or []),
        "validity": {"from": valid_from, "until": valid_until},
        # A pointer, not the text. Terms change; the licence should not
        # silently carry a stale copy of them.
        "terms": terms,
    }
    body_digest = canonical.digest(body)
    return {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "licence_id": "lic_" + body_digest.split(":", 1)[1][:16],
        "body": body,
        "seal": {
            "algorithm": canonical.DIGEST_ALGORITHM,
            "canonicalization": canonical.CANONICALIZATION,
            "body_digest": body_digest,
            "binds": signing.BINDS_INTEGRITY,
        },
    }


def attest(lic, private):
    """Sign a licence. Returns it, mutated in place."""
    body_digest = (lic.get("seal") or {}).get("body_digest")
    if not body_digest:
        raise ValueError("licence has no seal.body_digest to attest")
    licensee = lic.get("body", {}).get("licensee")
    public = signing.ed25519.public_key(private)
    lic["attestation"] = {
        "algorithm": signing.ALGORITHM,
        "context": CONTEXT,
        "key_id": signing.key_id(public),
        "public_key": public.hex(),
        "licensee": licensee,
        "signature": signing.ed25519.sign(
            private, payload(body_digest, licensee)).hex(),
    }
    lic["seal"]["binds"] = signing.BINDS_BOTH
    return lic


def verify(lic, trusted=None, at=None):
    """(signature_ok, validity_state, notes).

    Three values on purpose. The signature is a fact about bytes; the
    validity window is an opinion about a clock the verifier controls.
    Returning one boolean would let a moved clock read as a forged licence,
    or a forgery read as an expiry.
    """
    notes = []
    if lic.get("kind") != KIND:
        return False, None, ["not a licence record: kind is %r" % lic.get("kind")]

    att = lic.get("attestation")
    if not att:
        return False, None, ["unsigned licence: anyone can write one of these"]
    if att.get("context") != CONTEXT:
        return False, None, ["wrong signing context %r -- an evidence "
                             "attestation is not a licence" % att.get("context")]

    body = lic.get("body") or {}
    body_digest = (lic.get("seal") or {}).get("body_digest")
    actual = canonical.digest(body)
    if actual != body_digest:
        return False, None, ["the body does not hash to the sealed digest: "
                             "the licence was edited after signing"]

    trusted = {} if trusted is None else trusted
    kid = att.get("key_id")
    anchor = trusted.get(kid)
    if anchor is None:
        return False, None, ["key %s is not in the trust anchor: signed, but "
                             "not by anyone you trust" % kid]
    try:
        embedded = bytes.fromhex(att.get("public_key") or "")
    except ValueError:
        embedded = b""
    if embedded and embedded != anchor:
        return False, None, ["the embedded key does not match the trusted key"]
    try:
        sig = bytes.fromhex(att.get("signature") or "")
    except ValueError:
        return False, None, ["signature is not hex"]

    licensee = att.get("licensee")
    if not signing.ed25519.verify(anchor, payload(body_digest, licensee), sig):
        return False, None, ["signature does not verify under %s" % kid]
    if licensee != body.get("licensee"):
        return False, None, ["the attestation names licensee %r, the sealed "
                             "body says %r" % (licensee, body.get("licensee"))]

    notes.append("licence for %s, issued to key %s, signature verified"
                 % (licensee, kid))

    validity = body.get("validity") or {}
    state = VALID
    if at is None:
        notes.append("validity window NOT checked: no time supplied. The "
                     "signature is verified; whether the licence is current "
                     "is a separate question.")
        return True, None, notes
    start, end = validity.get("from"), validity.get("until")
    if start and at < start:
        state = NOT_YET_VALID
        notes.append("not yet valid: begins %s, asked about %s" % (start, at))
    elif end and at > end:
        state = EXPIRED
        notes.append("expired: ended %s, asked about %s" % (end, at))
    else:
        notes.append("within its validity window%s"
                     % ("" if end else " (no end date: perpetual)"))
    return True, state, notes


def grants(lic):
    """What this licence actually entitles the holder to."""
    return list((lic.get("body") or {}).get("grants") or [])


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(lic, directory):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, lic["licence_id"] + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(lic, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return path
