#!/usr/bin/env python3
"""Gate test: the public-safety-audit private_ips branch discriminates real
RFC1918 addresses from BOTH ECSS clause numbers and the two-letter "ip"
inside ordinary words (VEDA-0031).

Context: the 2026-09-10 fix replaced a bare 10.x.x.x (which matched every
ECSS clause number, holding 101 leaves) with a networking-keyword context
test. That context test had no left boundary, so "ip" matched inside
"principle", "description", "recipient" - a latent re-block of the public
sync. This pins the boundary.

Hermetic: stdlib only. Patterns are compiled from the audit module's own
PATTERNS; no git, no network, no filesystem scan.
"""
import importlib.util
import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(REPO_ROOT, "scripts", "public-safety-audit.py")


def _load_audit():
    spec = importlib.util.spec_from_file_location("public_safety_audit", AUDIT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PRIVATE_IPS = _load_audit().PATTERNS["private_ips"]


class PrivateIpDiscrimination(unittest.TestCase):
    # Real RFC1918 shapes must stay caught (no over-correction).
    POSITIVES = [
        "host at 192.168.1.10 reached",
        "gateway 172.16.5.1 configured",
        "10.0.0.5:8443 listening",       # bare 10.x with a port suffix
        "subnet 10.10.2.0 in use",       # bare 10.x with a keyword before it
    ]
    # Word-embedded "ip" must NOT trip the keyword branch (VEDA-0031).
    FALSE_POSITIVES = [
        "in principle 10.2.2.1 governs the design",
        "The description 10.2.2.1 in the standard",
        "recipient 10.2.4.1 shall retain the record",
    ]
    # ECSS clause numbers with no IP context must stay clean.
    ECSS_CLAUSES = [
        "clause 10.2.2.1 applies",
        "see 10.2.4.3 for detail",
        "requirement 10.2.2.2 is met",
        "10.2.3.1 lists the controls",
    ]

    def test_real_private_ips_still_caught(self):
        for text in self.POSITIVES:
            with self.subTest(text=text):
                self.assertIsNotNone(re.search(PRIVATE_IPS, text),
                                     f"missed a real private IP: {text!r}")

    def test_word_embedded_ip_is_not_a_false_positive(self):
        for text in self.FALSE_POSITIVES:
            with self.subTest(text=text):
                self.assertIsNone(re.search(PRIVATE_IPS, text),
                                  f"false positive (VEDA-0031): {text!r}")

    def test_ecss_clause_numbers_stay_clean(self):
        for text in self.ECSS_CLAUSES:
            with self.subTest(text=text):
                self.assertIsNone(re.search(PRIVATE_IPS, text),
                                  f"ECSS clause flagged as an IP: {text!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
