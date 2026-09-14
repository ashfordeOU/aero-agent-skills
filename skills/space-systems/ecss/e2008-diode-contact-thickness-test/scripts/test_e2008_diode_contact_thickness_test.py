"""Contract tests for the clause 9.6.8 diode contact thickness record."""

import unittest

from e2008_diode_contact_thickness_test_logic import (
    ACCEPT,
    ANODE,
    CATHODE,
    DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA,
    NOT_ESTABLISHED,
    REFER_FOR_REVIEW,
    REJECT,
    assess_contact_thickness,
    assess_diode_thickness,
    assess_thickness_acceptance_lot,
    calibration_is_current,
    categorize_contact_thickness,
    gauge_resolves_the_band,
    mean_replicate_um,
    quantize_to_resolution,
    replicate_spread_um,
    specification_band_um,
    validate_gauge,
    validate_thickness_acceptance_criteria,
    validate_thickness_contact,
    validate_thickness_measurement,
    worst_disposition,
)


def _criteria(**overrides):
    criteria = dict(DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA)
    criteria.update(overrides)
    return criteria


def _gauge(**overrides):
    gauge = {
        "id": "xrf-07",
        "resolution_um": 0.1,
        "calibration_valid_to_day": 200,
    }
    gauge.update(overrides)
    return gauge


def _measurement(**overrides):
    measurement = {
        "gauge": _gauge(),
        "measured_on_day": 120,
        "replicates": [6.0, 6.1, 5.9],
    }
    measurement.update(overrides)
    return measurement


def _anode(**overrides):
    contact = {
        "id": "anode-land",
        "polarity": ANODE,
        "measurement": _measurement(),
    }
    contact.update(overrides)
    return contact


def _cathode(**overrides):
    contact = {
        "id": "cathode-land",
        "polarity": CATHODE,
        "measurement": _measurement(),
    }
    contact.update(overrides)
    return contact


def _case(**overrides):
    case = {"id": "diode-01", "contacts": [_anode(), _cathode()]}
    case.update(overrides)
    return case


def _devices(count=5):
    return [_case(id="diode-%02d" % index) for index in range(1, count + 1)]


def _lot(**overrides):
    lot = {"id": "acceptance-lot-01", "declared_sample": 5, "devices": _devices()}
    lot.update(overrides)
    return lot


def _flat(value, count=3):
    return [value] * count


def _ratio(value, expected):
    return value / expected


class CriteriaTests(unittest.TestCase):
    def test_the_default_criteria_validate(self):
        self.assertIs(
            validate_thickness_acceptance_criteria(
                DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA
            ),
            DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA,
        )

    def test_a_non_mapping_criteria_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_acceptance_criteria("four to ten microns")

    def test_a_band_that_closes_on_itself_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_acceptance_criteria(
                _criteria(min_thickness_um=6.0, max_thickness_um=6.0)
            )

    def test_a_resolution_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_acceptance_criteria(
                _criteria(max_gauge_resolution_fraction=1.6)
            )

    def test_a_single_replicate_criteria_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_acceptance_criteria(_criteria(min_replicates=1))

    def test_a_negative_acceptance_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_acceptance_criteria(_criteria(min_acceptance_sample=-2))

    def test_the_band_is_the_ceiling_less_the_floor(self):
        self.assertAlmostEqual(specification_band_um(), 6.0, places=12)


class GaugeTests(unittest.TestCase):
    def test_a_gauge_normalises_to_step_and_calibration_day(self):
        instrument = validate_gauge(_gauge())
        self.assertEqual(instrument["id"], "xrf-07")
        self.assertAlmostEqual(instrument["resolution_um"], 0.1, places=12)
        self.assertEqual(instrument["calibration_valid_to_day"], 200)

    def test_a_blank_gauge_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_gauge(_gauge(id="   "))

    def test_a_zero_resolution_gauge_rejected(self):
        with self.assertRaises(ValueError):
            validate_gauge(_gauge(resolution_um=0.0))

    def test_a_negative_calibration_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_gauge(_gauge(calibration_valid_to_day=-3))

    def test_a_non_mapping_gauge_rejected(self):
        with self.assertRaises(ValueError):
            validate_gauge("xrf-07")

    def test_a_fine_gauge_splits_the_band(self):
        self.assertTrue(gauge_resolves_the_band(_gauge()))

    def test_a_gauge_exactly_on_the_resolution_allowance_splits_the_band(self):
        allowance = (
            specification_band_um()
            * DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA["max_gauge_resolution_fraction"]
        )
        self.assertAlmostEqual(allowance, 0.6, places=9)
        self.assertTrue(gauge_resolves_the_band(_gauge(resolution_um=0.6)))

    def test_a_coarse_gauge_cannot_split_the_band(self):
        self.assertFalse(gauge_resolves_the_band(_gauge(resolution_um=2.0)))


class MeasurementTests(unittest.TestCase):
    def test_a_measurement_with_no_replicate_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_measurement(_measurement(replicates=[]))

    def test_a_non_sequence_replicate_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_measurement(_measurement(replicates="six microns"))

    def test_a_negative_replicate_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_measurement(_measurement(replicates=[6.0, -6.0, 6.0]))

    def test_a_fractional_measurement_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_measurement(_measurement(measured_on_day=120.5))

    def test_a_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_measurement(None)

    def test_the_mean_is_the_average_of_the_replicates(self):
        self.assertAlmostEqual(mean_replicate_um([6.0, 6.1, 5.9]), 6.0, places=9)

    def test_the_spread_is_the_widest_disagreement(self):
        self.assertAlmostEqual(replicate_spread_um([6.0, 6.1, 5.9]), 0.2, places=9)

    def test_an_empty_replicate_set_has_no_mean(self):
        with self.assertRaises(ValueError):
            mean_replicate_um([])

    def test_a_calibration_still_standing_on_the_day_is_current(self):
        self.assertTrue(calibration_is_current(_measurement(measured_on_day=200)))

    def test_a_calibration_that_lapsed_before_the_day_is_not_current(self):
        self.assertFalse(calibration_is_current(_measurement(measured_on_day=201)))


class QuantisationTests(unittest.TestCase):
    def test_a_figure_is_carried_at_the_gauge_step(self):
        self.assertAlmostEqual(quantize_to_resolution(6.04, 0.1), 6.0, places=9)

    def test_a_figure_rounds_up_at_the_gauge_step(self):
        self.assertAlmostEqual(quantize_to_resolution(6.06, 0.1), 6.1, places=9)

    def test_a_coarse_gauge_writes_a_coarse_record(self):
        self.assertAlmostEqual(quantize_to_resolution(6.04, 0.5), 6.0, places=9)

    def test_a_zero_step_rejected(self):
        with self.assertRaises(ValueError):
            quantize_to_resolution(6.0, 0.0)


class DispositionTests(unittest.TestCase):
    def test_a_sound_record_inside_the_band_is_accepted(self):
        disposition, reason = categorize_contact_thickness(_measurement())
        self.assertEqual(disposition, ACCEPT)
        self.assertIn("inside the", reason)

    def test_a_coarse_gauge_leaves_the_contact_unsentenced(self):
        disposition, reason = categorize_contact_thickness(
            _measurement(gauge=_gauge(resolution_um=2.0))
        )
        self.assertEqual(disposition, NOT_ESTABLISHED)
        self.assertIn("splits the band", reason)

    def test_a_lapsed_calibration_leaves_the_contact_unsentenced(self):
        disposition, reason = categorize_contact_thickness(
            _measurement(measured_on_day=205)
        )
        self.assertEqual(disposition, NOT_ESTABLISHED)
        self.assertIn("unknown bias", reason)

    def test_a_reading_on_the_last_calibrated_day_is_sentenced(self):
        disposition, _reason = categorize_contact_thickness(
            _measurement(measured_on_day=200)
        )
        self.assertEqual(disposition, ACCEPT)

    def test_too_few_replicates_leave_the_contact_unsentenced(self):
        disposition, reason = categorize_contact_thickness(
            _measurement(replicates=[6.0, 6.0])
        )
        self.assertEqual(disposition, NOT_ESTABLISHED)
        self.assertIn("replicate", reason)

    def test_replicates_that_disagree_leave_the_contact_unsentenced(self):
        disposition, reason = categorize_contact_thickness(
            _measurement(replicates=[5.0, 6.0, 7.0])
        )
        self.assertEqual(disposition, NOT_ESTABLISHED)
        self.assertIn("unrepeatable", reason)

    def test_replicates_exactly_on_the_repeatability_limit_are_used(self):
        replicates = [5.7, 6.0, 6.3]
        self.assertAlmostEqual(replicate_spread_um(replicates), 0.6, places=9)
        disposition, _reason = categorize_contact_thickness(
            _measurement(replicates=replicates)
        )
        self.assertEqual(disposition, ACCEPT)

    def test_a_contact_under_the_floor_is_rejected(self):
        disposition, reason = categorize_contact_thickness(
            _measurement(replicates=_flat(3.0))
        )
        self.assertEqual(disposition, REJECT)
        self.assertIn("not there to weld", reason)

    def test_a_contact_exactly_on_the_floor_is_accepted(self):
        floor = DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA["min_thickness_um"]
        disposition, _reason = categorize_contact_thickness(
            _measurement(replicates=_flat(floor))
        )
        self.assertEqual(disposition, ACCEPT)

    def test_a_contact_exactly_on_the_ceiling_is_accepted(self):
        ceiling = DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA["max_thickness_um"]
        disposition, _reason = categorize_contact_thickness(
            _measurement(replicates=_flat(ceiling))
        )
        self.assertEqual(disposition, ACCEPT)

    def test_a_contact_over_the_ceiling_goes_to_review_not_to_scrap(self):
        disposition, reason = categorize_contact_thickness(
            _measurement(replicates=_flat(11.0))
        )
        self.assertEqual(disposition, REFER_FOR_REVIEW)
        self.assertIn("excess metal", reason)

    def test_the_record_gates_run_before_the_figure_is_sentenced(self):
        disposition, _reason = categorize_contact_thickness(
            _measurement(gauge=_gauge(resolution_um=2.0), replicates=_flat(3.0))
        )
        self.assertEqual(disposition, NOT_ESTABLISHED)


class WorstDispositionTests(unittest.TestCase):
    def test_an_empty_set_accepts(self):
        self.assertEqual(worst_disposition([]), ACCEPT)

    def test_severity_beats_record_order(self):
        self.assertEqual(worst_disposition([ACCEPT, REJECT, REFER_FOR_REVIEW]), REJECT)

    def test_a_missing_conductor_outranks_an_unsentenced_record(self):
        self.assertEqual(worst_disposition([NOT_ESTABLISHED, REJECT]), REJECT)

    def test_an_unsentenced_record_outranks_a_review(self):
        self.assertEqual(
            worst_disposition([REFER_FOR_REVIEW, NOT_ESTABLISHED]), NOT_ESTABLISHED
        )

    def test_an_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            worst_disposition([ACCEPT, "thick enough"])


class ContactRecordTests(unittest.TestCase):
    def test_a_sound_contact_record_is_accepted_and_complete(self):
        result = assess_contact_thickness(_anode())
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["gauge_id"], "xrf-07")
        self.assertEqual(result["replicates_taken"], 3)
        self.assertTrue(result["gauge_resolves_the_band"])
        self.assertTrue(result["calibration_current"])

    def test_the_record_carries_no_more_precision_than_the_gauge(self):
        result = assess_contact_thickness(
            _anode(
                measurement=_measurement(
                    gauge=_gauge(resolution_um=0.5), replicates=[6.0, 6.06, 6.06]
                )
            )
        )
        self.assertAlmostEqual(result["mean_thickness_um"], 6.04, places=9)
        self.assertAlmostEqual(result["recorded_thickness_um"], 6.0, places=9)

    def test_a_blank_contact_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_contact(_anode(id="  "))

    def test_an_unknown_polarity_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_contact(_anode(polarity="middle"))

    def test_a_contact_with_no_measurement_rejected(self):
        with self.assertRaises(ValueError):
            validate_thickness_contact(_anode(measurement=None))


class DiodeRollupTests(unittest.TestCase):
    def test_a_diode_recorded_on_both_lands_is_accepted(self):
        result = assess_diode_thickness(_case())
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["contacts_recorded"], 2)
        self.assertEqual(result["polarities_without_a_record"], ())

    def test_a_diode_recorded_on_one_polarity_cannot_be_accepted(self):
        result = assess_diode_thickness(_case(contacts=[_anode()]))
        self.assertEqual(result["disposition"], NOT_ESTABLISHED)
        self.assertEqual(result["polarities_without_a_record"], (CATHODE,))

    def test_a_missing_anode_record_is_named_too(self):
        result = assess_diode_thickness(_case(contacts=[_cathode()]))
        self.assertEqual(result["polarities_without_a_record"], (ANODE,))

    def test_a_thin_land_governs_the_diode(self):
        result = assess_diode_thickness(
            _case(
                contacts=[
                    _anode(),
                    _cathode(measurement=_measurement(replicates=_flat(3.0))),
                ]
            )
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertEqual(result["contacts_not_accepted"], ("cathode-land",))

    def test_a_thin_land_outranks_a_polarity_with_no_record(self):
        result = assess_diode_thickness(
            _case(contacts=[_anode(measurement=_measurement(replicates=_flat(3.0)))])
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_the_thinnest_contact_is_carried_up(self):
        result = assess_diode_thickness(
            _case(
                contacts=[
                    _anode(),
                    _cathode(measurement=_measurement(replicates=_flat(4.5))),
                ]
            )
        )
        self.assertAlmostEqual(_ratio(result["thinnest_contact_um"], 4.5), 1.0, places=9)

    def test_a_duplicate_contact_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_thickness(_case(contacts=[_anode(), _anode()]))

    def test_a_diode_declaring_no_contact_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_thickness(_case(contacts=[]))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_thickness(["diode-01"])


class AcceptanceLotTests(unittest.TestCase):
    def test_a_complete_run_of_sound_devices_is_accepted(self):
        result = assess_thickness_acceptance_lot(_lot())
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["devices_recorded"], 5)

    def test_a_run_short_of_its_declared_sample_is_not_established(self):
        result = assess_thickness_acceptance_lot(_lot(devices=_devices(3)))
        self.assertEqual(result["disposition"], NOT_ESTABLISHED)
        self.assertTrue(
            any("unsentenced" in finding for finding in result["rollup_findings"])
        )

    def test_a_sample_under_the_acceptance_floor_is_not_established(self):
        result = assess_thickness_acceptance_lot(
            _lot(declared_sample=2, devices=_devices(2))
        )
        self.assertEqual(result["disposition"], NOT_ESTABLISHED)

    def test_one_rejected_device_governs_the_run(self):
        devices = _devices(4)
        devices.append(
            _case(
                id="diode-05",
                contacts=[
                    _anode(measurement=_measurement(replicates=_flat(3.0))),
                    _cathode(),
                ],
            )
        )
        result = assess_thickness_acceptance_lot(_lot(devices=devices))
        self.assertEqual(result["disposition"], REJECT)
        self.assertEqual(result["devices_not_accepted"], ("diode-05",))

    def test_a_duplicate_device_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_thickness_acceptance_lot(
                _lot(devices=[_case(id="diode-01"), _case(id="diode-01")])
            )

    def test_a_non_sequence_device_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_thickness_acceptance_lot(_lot(devices="diode-01"))

    def test_a_negative_declared_sample_rejected(self):
        with self.assertRaises(ValueError):
            assess_thickness_acceptance_lot(_lot(declared_sample=-1))

    def test_a_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_thickness_acceptance_lot("acceptance-lot-01")


if __name__ == "__main__":
    unittest.main()
