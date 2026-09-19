#!/usr/bin/env python3
"""A throwaway corpus for the evidence tests.

The tests must be able to run where the real corpus is absent, and they must
be able to CHANGE a leaf to prove a digest moves.  Neither is safe to do to
the real tree, so they build a two-leaf fixture in a temporary directory that
has the same shape as the real thing: a standards map, a harness contract,
and leaves carrying SKILL.md plus a stdlib-only logic module and a unittest
suite.
"""

import os

STANDARDS_MAP = """# fixture standards map
schema_version: 1
standards:
  - id: demo-std
    name: "DEMO-100B: a fictional demonstration document"
    family: reference-data
    publisher: Example Standards Body
    status: public-domain
    domain: "demonstration"
    gated: false
  - id: demo-gated
    name: "DEMOG-7: a fictional paid document"
    family: guidance
    publisher: Example Standards Body
    status: proprietary-sold
    domain: "demonstration"
    gated: true
"""

HARNESS_CONTRACT = "# fixture harness contract\n\nNot the real one.\n"

DESCRIPTION = (
    "Use when you must compute the demonstration margin of a fixture part "
    "from its applied load and its allowable load: calculate the margin of "
    "safety as the allowable divided by the applied load minus one, decide "
    "whether the margin clears the required floor, and report the governing "
    "load case so the reviewer can see which case drove the result. Produces "
    "the margin, the pass decision and the governing case identifier for the "
    "fixture structural assessment record that the reviewer signs. "
    "Trigger: margin of safety, allowable load, applied load, governing case, "
    "fixture margin, structural reserve factor."
)

LOGIC = '''"""Fixture logic module: stdlib only, offline."""


def margin_of_safety(allowable, applied):
    if applied <= 0:
        raise ValueError("applied load must be positive")
    if allowable <= 0:
        raise ValueError("allowable load must be positive")
    return allowable / applied - 1.0


def clears(margin, floor=0.0):
    return margin >= floor
'''

TEST_MODULE = '''#!/usr/bin/env python3
"""Fixture contract test: stdlib unittest, offline."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import demo_leaf_logic as logic  # noqa: E402


class MarginTest(unittest.TestCase):
    def test_positive_margin(self):
        self.assertAlmostEqual(logic.margin_of_safety(120.0, 100.0), 0.2, places=9)

    def test_zero_margin(self):
        self.assertAlmostEqual(logic.margin_of_safety(100.0, 100.0), 0.0, places=9)

    def test_negative_applied_raises(self):
        with self.assertRaises(ValueError):
            logic.margin_of_safety(100.0, 0.0)

    def test_negative_allowable_raises(self):
        with self.assertRaises(ValueError):
            logic.margin_of_safety(-1.0, 100.0)

    def test_margin_below_bound(self):
        # A deliberate strict comparison with a relative gap near 1e-3, so the
        # near-boundary observation has something real in it.
        self.assertLess(logic.margin_of_safety(100.1, 100.0), 0.001001)

    def test_clears_floor(self):
        self.assertTrue(logic.clears(0.25, 0.0))
        self.assertFalse(logic.clears(-0.25, 0.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
'''


def skill_md(name, description=DESCRIPTION, extra=""):
    return (
        "---\n"
        "name: %s\n"
        'description: "%s"\n'
        "license: Apache-2.0\n"
        "compliance: STANDARDS-REF\n"
        "standards:\n"
        "  - id: demo-std\n"
        "    reference-only: true\n"
        "gated: false\n"
        "domain: demo-domain\n"
        "pack: demo-pack\n"
        "compatibility: \"any SKILL.md host\"\n"
        "metadata:\n"
        "  domain: demo-domain\n"
        "  subdomain: demo-pack\n"
        "  version: 0.1.0\n"
        "  author: Fixture\n"
        "---\n"
        "\n"
        "# Demonstration leaf (%s)\n"
        "\n"
        "Body text for the fixture leaf.\n"
        "%s"
    ) % (name, description, name, extra)


def write_leaf(root, name, description=DESCRIPTION):
    leaf = os.path.join(root, "skills", "demo-domain", "demo-pack", name)
    scripts = os.path.join(leaf, "scripts")
    os.makedirs(scripts, exist_ok=True)
    with open(os.path.join(leaf, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write(skill_md(name, description))
    with open(os.path.join(scripts, "demo_leaf_logic.py"), "w", encoding="utf-8") as fh:
        fh.write(LOGIC)
    with open(os.path.join(scripts, "test_demo_leaf.py"), "w", encoding="utf-8") as fh:
        fh.write(TEST_MODULE)
    return "skills/demo-domain/demo-pack/%s" % name


def build_repo(root, leaves=("demo-leaf",)):
    """Write a fixture repository under root.  Returns the leaf refs."""
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    with open(os.path.join(root, "standards-map.yaml"), "w", encoding="utf-8") as fh:
        fh.write(STANDARDS_MAP)
    with open(os.path.join(root, "docs", "harness-contract.md"), "w", encoding="utf-8") as fh:
        fh.write(HARNESS_CONTRACT)
    return [write_leaf(root, name) for name in leaves]
