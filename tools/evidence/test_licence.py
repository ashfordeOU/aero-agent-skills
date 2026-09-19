#!/usr/bin/env python3
"""Licence record tests, written from the counterfeiter's side.

The licence is worth money only if it cannot be manufactured. These assert
that, plus the two design decisions that stop it from lying: a licence
signature cannot be replayed as an evidence attestation, and expiry is
reported separately from the signature because the clock belongs to
whoever is asking.

Run: python3 tools/evidence/test_licence.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))
from tools.evidence import canonical, licence, signing  # noqa: E402


def a_licence(licensee="Beta Aerospace GmbH", until="2027-01-01"):
    return licence.build(
        licensee=licensee,
        scope="space-systems/ecss",
        valid_from="2026-01-01",
        valid_until=until,
        terms="https://example.invalid/terms/v1",
        grants=["corpus.read", "attestation.request"],
    )


class Shape(unittest.TestCase):

    def test_a_licence_needs_a_licensee(self):
        with self.assertRaises(ValueError):
            licence.build("", "scope", "2026-01-01")

    def test_a_licence_needs_a_scope(self):
        # An entitlement to everything is not an entitlement anyone can check.
        with self.assertRaises(ValueError):
            licence.build("Someone", None, "2026-01-01")

    def test_grants_are_sorted_so_the_digest_is_stable(self):
        a = licence.build("X", "s", "2026-01-01", grants=["b", "a"])
        b = licence.build("X", "s", "2026-01-01", grants=["a", "b"])
        self.assertEqual(a["seal"]["body_digest"], b["seal"]["body_digest"])


class CannotBeManufactured(unittest.TestCase):

    def setUp(self):
        self.priv, self.pub = signing.keypair()
        self.trusted = {signing.key_id(self.pub): self.pub}
        self.forger, _ = signing.keypair()

    def test_a_signed_licence_verifies(self):
        lic = licence.attest(a_licence(), self.priv)
        ok, state, notes = licence.verify(lic, self.trusted, at="2026-06-01")
        self.assertTrue(ok, notes)
        self.assertEqual(state, licence.VALID)

    def test_an_unsigned_licence_is_refused(self):
        ok, _, notes = licence.verify(a_licence(), self.trusted, at="2026-06-01")
        self.assertFalse(ok)
        self.assertIn("anyone can write one", " ".join(notes))

    def test_a_licence_signed_by_an_untrusted_key_is_refused(self):
        lic = licence.attest(a_licence(), self.forger)
        ok, _, notes = licence.verify(lic, self.trusted, at="2026-06-01")
        self.assertFalse(ok)
        self.assertIn("trust anchor", " ".join(notes))

    def test_renaming_the_licensee_after_signing_is_refused(self):
        lic = licence.attest(a_licence("Alpha Ltd"), self.priv)
        lic["body"]["licensee"] = "Pirate Ltd"
        lic["seal"]["body_digest"] = canonical.digest(lic["body"])
        self.assertFalse(licence.verify(lic, self.trusted, at="2026-06-01")[0])

    def test_extending_the_expiry_after_signing_is_refused(self):
        # The obvious attack on any licence.
        lic = licence.attest(a_licence(until="2026-02-01"), self.priv)
        lic["body"]["validity"]["until"] = "2099-01-01"
        lic["seal"]["body_digest"] = canonical.digest(lic["body"])
        self.assertFalse(licence.verify(lic, self.trusted, at="2026-06-01")[0])

    def test_widening_the_grants_after_signing_is_refused(self):
        lic = licence.attest(a_licence(), self.priv)
        lic["body"]["grants"].append("everything")
        lic["seal"]["body_digest"] = canonical.digest(lic["body"])
        self.assertFalse(licence.verify(lic, self.trusted, at="2026-06-01")[0])

    def test_transplanting_a_signature_onto_another_licence_is_refused(self):
        good = licence.attest(a_licence("Alpha Ltd"), self.priv)
        other = a_licence("Pirate Ltd")
        other["attestation"] = dict(good["attestation"])
        self.assertFalse(licence.verify(other, self.trusted, at="2026-06-01")[0])


class ContextSeparation(unittest.TestCase):
    """A licence is not an evidence attestation and must not be mistakable."""

    def setUp(self):
        self.priv, self.pub = signing.keypair()
        self.trusted = {signing.key_id(self.pub): self.pub}

    def test_the_two_contexts_differ(self):
        self.assertNotEqual(licence.CONTEXT, signing.CONTEXT)

    def test_an_evidence_signature_is_not_accepted_as_a_licence(self):
        lic = a_licence()
        digest = lic["seal"]["body_digest"]
        # Sign with the EVIDENCE payload, present it as a licence.
        lic["attestation"] = {
            "algorithm": signing.ALGORITHM,
            "context": signing.CONTEXT,
            "key_id": signing.key_id(self.pub),
            "public_key": self.pub.hex(),
            "licensee": lic["body"]["licensee"],
            "signature": signing.ed25519.sign(
                self.priv, signing.payload(digest, "x")).hex(),
        }
        ok, _, notes = licence.verify(lic, self.trusted, at="2026-06-01")
        self.assertFalse(ok)
        self.assertIn("not a licence", " ".join(notes))

    def test_a_licence_is_not_accepted_as_an_evidence_record(self):
        lic = licence.attest(a_licence(), self.priv)
        ok, _ = signing.verify(lic, self.trusted)
        self.assertFalse(ok)


class TheClockIsSeparate(unittest.TestCase):
    """Signature is a fact; expiry is an opinion about a clock."""

    def setUp(self):
        self.priv, self.pub = signing.keypair()
        self.trusted = {signing.key_id(self.pub): self.pub}

    def test_an_expired_licence_still_has_a_valid_signature(self):
        # Collapsing these into one boolean would let an expiry read as a
        # forgery, which sends someone to entirely the wrong conversation.
        lic = licence.attest(a_licence(until="2026-02-01"), self.priv)
        ok, state, _ = licence.verify(lic, self.trusted, at="2026-06-01")
        self.assertTrue(ok)
        self.assertEqual(state, licence.EXPIRED)

    def test_a_licence_before_its_start_is_not_yet_valid(self):
        lic = licence.attest(a_licence(), self.priv)
        ok, state, _ = licence.verify(lic, self.trusted, at="2025-06-01")
        self.assertTrue(ok)
        self.assertEqual(state, licence.NOT_YET_VALID)

    def test_with_no_time_supplied_expiry_is_reported_as_unchecked(self):
        lic = licence.attest(a_licence(), self.priv)
        ok, state, notes = licence.verify(lic, self.trusted)
        self.assertTrue(ok)
        self.assertIsNone(state)
        self.assertIn("NOT checked", " ".join(notes))

    def test_a_perpetual_licence_says_so(self):
        lic = licence.attest(a_licence(until=None), self.priv)
        ok, state, notes = licence.verify(lic, self.trusted, at="2099-01-01")
        self.assertTrue(ok)
        self.assertEqual(state, licence.VALID)
        self.assertIn("perpetual", " ".join(notes))


class RoundTrip(unittest.TestCase):

    def test_save_and_load(self):
        priv, pub = signing.keypair()
        lic = licence.attest(a_licence(), priv)
        with tempfile.TemporaryDirectory() as d:
            path = licence.save(lic, d)
            back = licence.load(path)
        ok, state, _ = licence.verify(
            back, {signing.key_id(pub): pub}, at="2026-06-01")
        self.assertTrue(ok)
        self.assertEqual(state, licence.VALID)
        self.assertEqual(licence.grants(back),
                         ["attestation.request", "corpus.read"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
