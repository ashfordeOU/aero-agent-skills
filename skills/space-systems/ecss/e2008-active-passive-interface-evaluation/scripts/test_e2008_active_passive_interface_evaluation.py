#!/usr/bin/env python3
"""Contract test for active/passive interface evaluation, clause 7.5.18 (offline)."""

import copy
import unittest

from e2008_active_passive_interface_evaluation_logic import (
    DEFAULT_INTERFACE_POLICY,
    INTERFACE_ACTIVE,
    INTERFACE_INDETERMINATE,
    INTERFACE_PASSIVE,
    LINE_INCONCLUSIVE,
    LINE_INDICATES_ACTIVE,
    LINE_INDICATES_PASSIVE,
    LINE_LONGPASS_CURRENT,
    LINE_SUB_BANDGAP_RESPONSE,
    LINE_VOLTAGE_EXCESS,
    LOT_OPEN,
    LOT_RESOLVED,
    assess_cell,
    assess_interface_evaluation,
    categorize_interface,
    integrate_response,
    longpass_current_ratio,
    open_circuit_voltage_excess_v,
    read_evidence_line,
    sub_bandgap_response_share,
    validate_interface_policy,
    validate_spectral_response,
)


def _sweep(pairs):
    return [{"wavelength_nm": w, "response_a_per_w": r} for w, r in pairs]


ACTIVE_SWEEP = _sweep(
    [
        (400, 0.50),
        (600, 0.60),
        (800, 0.62),
        (880, 0.60),
        (890, 0.05),
        (1000, 0.12),
        (1400, 0.20),
        (1800, 0.02),
    ]
)

PASSIVE_SWEEP = _sweep(
    [
        (400, 0.50),
        (600, 0.60),
        (800, 0.62),
        (880, 0.60),
        (890, 0.002),
        (1000, 0.002),
        (1400, 0.001),
        (1800, 0.000),
    ]
)

UNDECIDED_SWEEP = _sweep(
    [
        (400, 0.50),
        (600, 0.60),
        (800, 0.62),
        (880, 0.60),
        (890, 0.010),
        (1000, 0.010),
        (1400, 0.008),
        (1800, 0.002),
    ]
)

TRUNCATED_SWEEP = _sweep(
    [(400, 0.50), (600, 0.60), (800, 0.62), (880, 0.60), (890, 0.05), (1000, 0.12)]
)


def _cell(
    cell_id="cell-a",
    voc=1.25,
    reference=1.00,
    samples=None,
    filtered=0.030,
    unfiltered=0.500,
):
    return {
        "cell_id": cell_id,
        "measured_voc_v": voc,
        "single_junction_reference_v": reference,
        "spectral_response": list(samples if samples is not None else ACTIVE_SWEEP),
        "filtered_isc_a": filtered,
        "unfiltered_isc_a": unfiltered,
    }


def _passive_cell(cell_id="cell-p"):
    return _cell(cell_id, voc=1.02, samples=PASSIVE_SWEEP, filtered=0.001)


def _reading(line, reading):
    return {"line": line, "value": 0.0, "reading": reading}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_interface_policy(DEFAULT_INTERFACE_POLICY),
            DEFAULT_INTERFACE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface_policy("look for a second junction")

    def test_sub_bandgap_band_starting_below_the_edge_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERFACE_POLICY)
        broken["sub_bandgap_start_nm"] = 700.0
        with self.assertRaises(ValueError):
            validate_interface_policy(broken)

    def test_germanium_cutoff_below_the_band_start_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERFACE_POLICY)
        broken["germanium_cutoff_nm"] = 900.0
        with self.assertRaises(ValueError):
            validate_interface_policy(broken)

    def test_thresholds_with_no_undecided_band_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERFACE_POLICY)
        broken["passive_voltage_excess_v"] = broken["active_voltage_excess_v"]
        with self.assertRaises(ValueError):
            validate_interface_policy(broken)

    def test_asking_for_more_lines_than_exist_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERFACE_POLICY)
        broken["min_conclusive_lines"] = 5
        with self.assertRaises(ValueError):
            validate_interface_policy(broken)

    def test_agreeing_lines_above_conclusive_lines_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERFACE_POLICY)
        broken["min_conclusive_lines"] = 1
        broken["min_agreeing_lines"] = 3
        with self.assertRaises(ValueError):
            validate_interface_policy(broken)


class SweepTests(unittest.TestCase):
    def test_a_full_sweep_reads_back_in_order(self):
        sweep = validate_spectral_response(list(reversed(ACTIVE_SWEEP)))
        wavelengths = [s["wavelength_nm"] for s in sweep["samples"]]
        self.assertEqual(wavelengths, sorted(wavelengths))
        self.assertTrue(sweep["reaches_germanium_cutoff"])
        self.assertEqual(sweep["findings"], [])

    def test_a_sweep_stopping_short_of_germanium_is_reported(self):
        sweep = validate_spectral_response(TRUNCATED_SWEEP)
        self.assertFalse(sweep["reaches_germanium_cutoff"])
        self.assertTrue(any("partly measured" in t for t in sweep["findings"]))

    def test_a_sweep_starting_past_the_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_response(
                _sweep(
                    [
                        (900, 0.1),
                        (1000, 0.1),
                        (1100, 0.1),
                        (1200, 0.1),
                        (1400, 0.1),
                        (1800, 0.1),
                    ]
                )
            )

    def test_a_sweep_with_no_sub_bandgap_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_response(
                _sweep(
                    [
                        (400, 0.5),
                        (500, 0.5),
                        (600, 0.5),
                        (700, 0.5),
                        (800, 0.5),
                        (900, 0.5),
                    ]
                )
            )

    def test_a_repeated_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_response(list(ACTIVE_SWEEP) + [ACTIVE_SWEEP[0]])

    def test_a_sweep_below_the_sample_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_response(_sweep([(400, 0.5), (1000, 0.1)]))

    def test_a_negative_response_rejected(self):
        broken = _sweep([(w, r) for w, r in [(400, 0.5)]]) + list(ACTIVE_SWEEP[1:])
        broken[0]["response_a_per_w"] = -0.1
        with self.assertRaises(ValueError):
            validate_spectral_response(broken)

    def test_a_non_mapping_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_response(["400 nm"] + list(ACTIVE_SWEEP))


class IntegrationTests(unittest.TestCase):
    def test_a_flat_response_integrates_to_a_rectangle(self):
        flat = _sweep([(400, 0.5), (1800, 0.5)])
        self.assertAlmostEqual(integrate_response(flat, 400.0, 1800.0), 700.0, places=9)

    def test_a_sub_band_integrates_over_its_own_width(self):
        flat = _sweep([(400, 0.5), (1800, 0.5)])
        self.assertAlmostEqual(integrate_response(flat, 950.0, 1800.0), 425.0, places=9)

    def test_a_ramp_integrates_to_a_triangle(self):
        ramp = _sweep([(0.5, 0.0), (1000.5, 1.0)])
        self.assertAlmostEqual(
            integrate_response(ramp, 0.5, 1000.5), 500.0, places=9
        )

    def test_a_band_closing_below_its_opening_rejected(self):
        flat = _sweep([(400, 0.5), (1800, 0.5)])
        with self.assertRaises(ValueError):
            integrate_response(flat, 1800.0, 400.0)

    def test_a_band_outside_the_sampled_span_rejected(self):
        flat = _sweep([(400, 0.5), (1800, 0.5)])
        with self.assertRaises(ValueError):
            integrate_response(flat, 200.0, 1800.0)

    def test_a_single_sample_cannot_be_integrated(self):
        with self.assertRaises(ValueError):
            integrate_response(_sweep([(400, 0.5)]), 400.0, 1800.0)

    def test_an_active_sweep_puts_a_large_share_beyond_the_edge(self):
        share = sub_bandgap_response_share(validate_spectral_response(ACTIVE_SWEEP))
        self.assertAlmostEqual(share, 0.28202428, places=7)

    def test_a_passive_sweep_puts_almost_nothing_beyond_the_edge(self):
        share = sub_bandgap_response_share(validate_spectral_response(PASSIVE_SWEEP))
        self.assertAlmostEqual(share, 0.00315978, places=7)

    def test_a_sweep_with_no_response_at_all_rejected(self):
        dead = _sweep(
            [(400, 0.0), (600, 0.0), (800, 0.0), (1000, 0.0), (1400, 0.0), (1800, 0.0)]
        )
        with self.assertRaises(ValueError):
            sub_bandgap_response_share(validate_spectral_response(dead))

    def test_an_unvalidated_sweep_rejected(self):
        with self.assertRaises(ValueError):
            sub_bandgap_response_share(ACTIVE_SWEEP)


class LineTests(unittest.TestCase):
    def test_voltage_excess_is_the_difference_from_the_reference(self):
        self.assertAlmostEqual(
            open_circuit_voltage_excess_v(1.25, 1.00), 0.25, places=9
        )

    def test_a_zero_reference_voltage_rejected(self):
        with self.assertRaises(ValueError):
            open_circuit_voltage_excess_v(1.25, 0.0)

    def test_longpass_ratio_is_the_share_of_current_left(self):
        self.assertAlmostEqual(longpass_current_ratio(0.030, 0.500), 0.06, places=9)

    def test_a_filter_that_added_current_rejected(self):
        with self.assertRaises(ValueError):
            longpass_current_ratio(0.600, 0.500)

    def test_a_zero_unfiltered_current_rejected(self):
        with self.assertRaises(ValueError):
            longpass_current_ratio(0.0, 0.0)

    def test_a_value_above_the_upper_threshold_indicates_active(self):
        read = read_evidence_line(LINE_VOLTAGE_EXCESS, 0.25)
        self.assertEqual(read["reading"], LINE_INDICATES_ACTIVE)

    def test_a_value_on_the_upper_threshold_indicates_active(self):
        read = read_evidence_line(
            LINE_VOLTAGE_EXCESS, DEFAULT_INTERFACE_POLICY["active_voltage_excess_v"]
        )
        self.assertEqual(read["reading"], LINE_INDICATES_ACTIVE)

    def test_a_value_below_the_lower_threshold_indicates_passive(self):
        read = read_evidence_line(LINE_LONGPASS_CURRENT, 0.002)
        self.assertEqual(read["reading"], LINE_INDICATES_PASSIVE)

    def test_a_value_between_the_thresholds_decides_nothing(self):
        read = read_evidence_line(LINE_SUB_BANDGAP_RESPONSE, 0.021)
        self.assertEqual(read["reading"], LINE_INCONCLUSIVE)

    def test_an_unknown_evidence_line_rejected(self):
        with self.assertRaises(ValueError):
            read_evidence_line("dark-current-slope", 0.1)

    def test_a_non_numeric_line_value_rejected(self):
        with self.assertRaises(ValueError):
            read_evidence_line(LINE_VOLTAGE_EXCESS, "a quarter of a volt")


class WeighingTests(unittest.TestCase):
    def test_three_agreeing_active_lines_give_an_active_interface(self):
        grouped = categorize_interface(
            [_reading(line, LINE_INDICATES_ACTIVE) for line in
             (LINE_VOLTAGE_EXCESS, LINE_SUB_BANDGAP_RESPONSE, LINE_LONGPASS_CURRENT)]
        )
        self.assertEqual(grouped["category"], INTERFACE_ACTIVE)
        self.assertEqual(grouped["conclusive_line_count"], 3)

    def test_three_agreeing_passive_lines_give_a_passive_interface(self):
        grouped = categorize_interface(
            [_reading(line, LINE_INDICATES_PASSIVE) for line in
             (LINE_VOLTAGE_EXCESS, LINE_SUB_BANDGAP_RESPONSE, LINE_LONGPASS_CURRENT)]
        )
        self.assertEqual(grouped["category"], INTERFACE_PASSIVE)

    def test_contradicting_lines_leave_the_interface_undecided(self):
        grouped = categorize_interface(
            [
                _reading(LINE_VOLTAGE_EXCESS, LINE_INDICATES_ACTIVE),
                _reading(LINE_SUB_BANDGAP_RESPONSE, LINE_INDICATES_PASSIVE),
                _reading(LINE_LONGPASS_CURRENT, LINE_INDICATES_ACTIVE),
            ]
        )
        self.assertEqual(grouped["category"], INTERFACE_INDETERMINATE)
        self.assertTrue(any("contradict" in t for t in grouped["findings"]))

    def test_one_decided_line_is_not_enough(self):
        grouped = categorize_interface(
            [
                _reading(LINE_VOLTAGE_EXCESS, LINE_INDICATES_ACTIVE),
                _reading(LINE_SUB_BANDGAP_RESPONSE, LINE_INCONCLUSIVE),
                _reading(LINE_LONGPASS_CURRENT, LINE_INCONCLUSIVE),
            ]
        )
        self.assertEqual(grouped["category"], INTERFACE_INDETERMINATE)
        self.assertEqual(grouped["conclusive_line_count"], 1)

    def test_two_agreeing_lines_are_enough(self):
        grouped = categorize_interface(
            [
                _reading(LINE_VOLTAGE_EXCESS, LINE_INDICATES_ACTIVE),
                _reading(LINE_SUB_BANDGAP_RESPONSE, LINE_INDICATES_ACTIVE),
                _reading(LINE_LONGPASS_CURRENT, LINE_INCONCLUSIVE),
            ]
        )
        self.assertEqual(grouped["category"], INTERFACE_ACTIVE)
        self.assertEqual(grouped["inconclusive_lines"], [LINE_LONGPASS_CURRENT])

    def test_a_line_read_twice_rejected(self):
        with self.assertRaises(ValueError):
            categorize_interface(
                [
                    _reading(LINE_VOLTAGE_EXCESS, LINE_INDICATES_ACTIVE),
                    _reading(LINE_VOLTAGE_EXCESS, LINE_INDICATES_ACTIVE),
                ]
            )

    def test_an_empty_evidence_set_rejected(self):
        with self.assertRaises(ValueError):
            categorize_interface([])

    def test_an_unrecognised_reading_rejected(self):
        with self.assertRaises(ValueError):
            categorize_interface([_reading(LINE_VOLTAGE_EXCESS, "probably active")])


class CellTests(unittest.TestCase):
    def test_an_active_interface_cell_is_grouped_as_active(self):
        record = assess_cell(_cell())
        self.assertEqual(record["category"], INTERFACE_ACTIVE)
        self.assertEqual(record["findings"], [])
        self.assertEqual(len(record["active_lines"]), 3)

    def test_a_passive_interface_cell_is_grouped_as_passive(self):
        record = assess_cell(_passive_cell())
        self.assertEqual(record["category"], INTERFACE_PASSIVE)
        self.assertEqual(len(record["passive_lines"]), 3)

    def test_the_three_line_values_are_reported_with_the_outcome(self):
        record = assess_cell(_cell())
        self.assertAlmostEqual(record["voltage_excess_v"], 0.25, places=9)
        self.assertAlmostEqual(record["longpass_ratio"], 0.06, places=9)
        self.assertAlmostEqual(record["sub_bandgap_share"], 0.28202428, places=7)

    def test_a_truncated_sweep_makes_the_spectral_line_undecided(self):
        record = assess_cell(_cell(samples=TRUNCATED_SWEEP))
        self.assertIn(LINE_SUB_BANDGAP_RESPONSE, record["inconclusive_lines"])
        self.assertFalse(record["sweep_reaches_germanium_cutoff"])

    def test_a_truncated_sweep_still_resolves_on_the_other_two_lines(self):
        record = assess_cell(_cell(samples=TRUNCATED_SWEEP))
        self.assertEqual(record["category"], INTERFACE_ACTIVE)
        self.assertTrue(any("partly measured" in t for t in record["findings"]))

    def test_a_truncated_sweep_with_one_undecided_line_leaves_it_undecided(self):
        record = assess_cell(_cell(samples=TRUNCATED_SWEEP, filtered=0.005))
        self.assertEqual(record["category"], INTERFACE_INDETERMINATE)

    def test_contradicting_evidence_leaves_the_cell_undecided(self):
        record = assess_cell(_cell(samples=PASSIVE_SWEEP, filtered=0.001))
        self.assertEqual(record["category"], INTERFACE_INDETERMINATE)
        self.assertTrue(any("contradict" in t for t in record["findings"]))

    def test_an_all_undecided_cell_is_not_reported_as_passive(self):
        record = assess_cell(
            _cell(voc=1.10, samples=UNDECIDED_SWEEP, filtered=0.005)
        )
        self.assertEqual(record["category"], INTERFACE_INDETERMINATE)
        self.assertEqual(record["passive_lines"], [])

    def test_a_cell_without_an_identifier_rejected(self):
        broken = _cell()
        del broken["cell_id"]
        with self.assertRaises(ValueError):
            assess_cell(broken)

    def test_a_cell_missing_its_sweep_rejected(self):
        broken = _cell()
        del broken["spectral_response"]
        with self.assertRaises(ValueError):
            assess_cell(broken)

    def test_a_non_mapping_cell_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell("one gallium arsenide cell")


class BatchTests(unittest.TestCase):
    def test_a_uniform_active_batch_resolves(self):
        case = {"cells": [_cell("cell-a"), _cell("cell-b"), _cell("cell-c")]}
        result = assess_interface_evaluation(case)
        self.assertEqual(result["verdict"], LOT_RESOLVED)
        self.assertEqual(result["cells_by_category"][INTERFACE_ACTIVE],
                         ["cell-a", "cell-b", "cell-c"])
        self.assertTrue(result["batch_is_uniform"])

    def test_a_uniform_passive_batch_resolves(self):
        case = {
            "cells": [
                _passive_cell("cell-a"),
                _passive_cell("cell-b"),
                _passive_cell("cell-c"),
            ]
        }
        result = assess_interface_evaluation(case)
        self.assertEqual(result["verdict"], LOT_RESOLVED)
        self.assertEqual(result["findings"], [])

    def test_a_mixed_batch_opens_the_lot(self):
        case = {"cells": [_cell("cell-a"), _cell("cell-b"), _passive_cell("cell-c")]}
        result = assess_interface_evaluation(case)
        self.assertEqual(result["verdict"], LOT_OPEN)
        self.assertFalse(result["batch_is_uniform"])
        self.assertTrue(any("one substrate process" in t for t in result["findings"]))

    def test_an_undecided_cell_opens_the_lot(self):
        case = {
            "cells": [
                _cell("cell-a"),
                _cell("cell-b"),
                _cell("cell-c", voc=1.10, samples=UNDECIDED_SWEEP, filtered=0.005),
            ]
        }
        result = assess_interface_evaluation(case)
        self.assertEqual(result["verdict"], LOT_OPEN)
        self.assertEqual(result["undecided_cell_ids"], ["cell-c"])
        self.assertTrue(any("not a passive one" in t for t in result["findings"]))

    def test_records_come_back_in_identifier_order(self):
        case = {"cells": [_cell("cell-c"), _cell("cell-a"), _cell("cell-b")]}
        result = assess_interface_evaluation(case)
        self.assertEqual(
            [r["cell_id"] for r in result["cell_records"]],
            ["cell-a", "cell-b", "cell-c"],
        )

    def test_the_batch_counts_its_cells(self):
        case = {"cells": [_cell("cell-a"), _cell("cell-b")]}
        self.assertEqual(assess_interface_evaluation(case)["cell_count"], 2)

    def test_a_repeated_cell_identifier_rejected(self):
        case = {"cells": [_cell("cell-a"), _cell("cell-a")]}
        with self.assertRaises(ValueError):
            assess_interface_evaluation(case)

    def test_an_empty_batch_rejected(self):
        with self.assertRaises(ValueError):
            assess_interface_evaluation({"cells": []})

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_interface_evaluation([_cell()])

    def test_the_batch_carries_every_cell_finding(self):
        case = {
            "cells": [
                _cell("cell-a"),
                _cell("cell-b"),
                _cell("cell-c", samples=PASSIVE_SWEEP, filtered=0.001),
            ]
        }
        result = assess_interface_evaluation(case)
        self.assertTrue(any("cell-c" in t for t in result["findings"]))


if __name__ == "__main__":
    unittest.main()
