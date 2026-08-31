#!/usr/bin/env python3
"""Gate 3 contract test: SysML diagram modeling.

Exercises scripts/sysml_modeling_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - each modeling purpose maps
to exactly one SysML diagram kind; a block definition diagram is valid
only when every referenced element has a definition; requirements
traceability closes only when every requirement has a satisfying design
element; a model is complete only when all four viewpoints (structure,
behavior, requirements, parametric) are covered. Unknown inputs raise
ValueError.

Hand-computed expected values (no external reference):
- sysml_diagram_for('system-composition') == 'bdd'
- sysml_diagram_for('internal-connections') == 'ibd'
- sysml_diagram_for('constraint-analysis') == 'param'
- sysml_diagram_for('requirements-traceability') == 'req'
- sysml_diagram_for('functional-flow') == 'act'
- sysml_diagram_for('message-ordering') == 'seq'
- sysml_diagram_for('state-transition') == 'stm'
- sysml_diagram_for('use-case-scoping') == 'uc'
- diagram_kind_name('bdd') == 'block definition diagram'
- block_definition_verdict(['gear', 'wheel', 'strut'], ['wheel'])
  == 'valid'  (one reference, definition present)
- block_definition_verdict(['gear', 'wheel'], ['wheel', 'strut'])
  == 'invalid'  (strut has no definition)
- block_definition_verdict([], ['wheel']) == 'invalid'  (empty parts)
- requirement_trace_closure(['R1', 'R2'], {'R1': ['gear'], 'R2': ['brake']})
  == []  (both satisfied)
- requirement_trace_closure(['R1', 'R2'], {'R1': ['gear']})
  == ['R2']  (R2 has no satisfying element)
- requirement_trace_closure(['R1'], {'R1': []}) == ['R1']
- model_viewpoint_verdict({'structure': True, 'behavior': True,
  'requirements': True, 'parametric': True}) == 'complete'
- model_viewpoint_verdict({'structure': True, 'behavior': True,
  'requirements': True, 'parametric': False}) == 'missing'
- model_viewpoint_verdict({'structure': True, 'behavior': True,
  'requirements': True}) == 'missing'  (parametric absent)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sysml_modeling_logic as sml  # noqa: E402


class DiagramSelectionTest(unittest.TestCase):
    def test_purpose_maps_to_diagram_kind(self):
        self.assertEqual(sml.sysml_diagram_for("system-composition"), "bdd")
        self.assertEqual(sml.sysml_diagram_for("internal-connections"), "ibd")
        self.assertEqual(sml.sysml_diagram_for("constraint-analysis"), "param")
        self.assertEqual(
            sml.sysml_diagram_for("requirements-traceability"), "req"
        )
        self.assertEqual(sml.sysml_diagram_for("functional-flow"), "act")
        self.assertEqual(sml.sysml_diagram_for("message-ordering"), "seq")
        self.assertEqual(sml.sysml_diagram_for("state-transition"), "stm")
        self.assertEqual(sml.sysml_diagram_for("use-case-scoping"), "uc")

    def test_unknown_purpose_raises(self):
        with self.assertRaises(ValueError):
            sml.sysml_diagram_for("cooking")

    def test_diagram_kind_name(self):
        self.assertEqual(sml.diagram_kind_name("bdd"), "block definition diagram")
        self.assertEqual(sml.diagram_kind_name("ibd"), "internal block diagram")
        self.assertEqual(sml.diagram_kind_name("param"), "parametric diagram")
        self.assertEqual(sml.diagram_kind_name("req"), "requirements diagram")
        with self.assertRaises(ValueError):
            sml.diagram_kind_name("nope")


class BlockDefinitionTest(unittest.TestCase):
    def test_all_references_defined_is_valid(self):
        self.assertEqual(
            sml.block_definition_verdict(
                ["gear", "wheel", "strut"], ["wheel"]
            ),
            "valid",
        )

    def test_missing_reference_is_invalid(self):
        self.assertEqual(
            sml.block_definition_verdict(
                ["gear", "wheel"], ["wheel", "strut"]
            ),
            "invalid",
        )

    def test_empty_parts_is_invalid(self):
        self.assertEqual(
            sml.block_definition_verdict([], ["wheel"]), "invalid"
        )

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            sml.block_definition_verdict("gear", ["wheel"])


class RequirementTraceTest(unittest.TestCase):
    def test_all_satisfied_closes(self):
        self.assertEqual(
            sml.requirement_trace_closure(
                ["R1", "R2"], {"R1": ["gear"], "R2": ["brake"]}
            ),
            [],
        )

    def test_missing_satisfaction_reported(self):
        self.assertEqual(
            sml.requirement_trace_closure(
                ["R1", "R2"], {"R1": ["gear"]}
            ),
            ["R2"],
        )

    def test_empty_satisfier_list_is_missing(self):
        self.assertEqual(
            sml.requirement_trace_closure(["R1"], {"R1": []}), ["R1"]
        )

    def test_empty_requirements_close(self):
        self.assertEqual(sml.requirement_trace_closure([], {}), [])

    def test_unknown_satisfied_by_key_raises(self):
        with self.assertRaises(ValueError):
            sml.requirement_trace_closure(["R1"], {"R9": ["gear"]})


class ViewpointTest(unittest.TestCase):
    def test_all_viewpoints_covered_is_complete(self):
        self.assertEqual(
            sml.model_viewpoint_verdict(
                {
                    "structure": True,
                    "behavior": True,
                    "requirements": True,
                    "parametric": True,
                }
            ),
            "complete",
        )

    def test_false_viewpoint_is_missing(self):
        self.assertEqual(
            sml.model_viewpoint_verdict(
                {
                    "structure": True,
                    "behavior": True,
                    "requirements": True,
                    "parametric": False,
                }
            ),
            "missing",
        )

    def test_absent_viewpoint_is_missing(self):
        self.assertEqual(
            sml.model_viewpoint_verdict(
                {"structure": True, "behavior": True, "requirements": True}
            ),
            "missing",
        )

    def test_unknown_viewpoint_raises(self):
        with self.assertRaises(ValueError):
            sml.model_viewpoint_verdict(
                {"structure": True, "cost": True}
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
