#!/usr/bin/env python3
"""Cooper-Harper handling qualities rating logic (paraphrase).

The Cooper-Harper scale assigns a pilot rating from 1 (excellent) to
10 (uncontrollable) to the handling qualities of an aircraft flown on
a defined evaluation task. The rating is collected by walking a
decision tree (paraphrase of the standard procedure): is the aircraft
controllable, is adequate performance attainable with the required
tolerances, is the aircraft satisfactory without improvement, and how
much pilot compensation does the task demand. FAR-25 and CS-25 flight
characteristics requirements frame the assessment for transport
aeroplanes (summary reference only, standards-map.yaml); the scale
itself is the common pilot-rating methodology of Cooper and Harper
(1969), summarized here:

- Rating bands: 1-3 satisfactory without improvement, 4-6
  deficiencies warrant improvement, 7-9 deficiencies require
  improvement, 10 uncontrollable.
- Desired tolerances grade the 1-3 band by compensation: none gives
  1, negligible gives 2, minor gives 3. Compensation beyond minor
  contradicts desired tolerances (the aircraft would have been rated
  in the 4-6 band).
- Adequate tolerances grade the 4-6 band: minor gives 4, moderate
  gives 5, considerable gives 6, extensive tops the band at 6.
- When adequate performance is not attainable, the 7-9 band grades
  the compensation required to retain control: minimal gives 7,
  considerable gives 8, extensive or intense gives 9.
- Handling qualities levels (MIL-STD-1797A framing): 1-3 Level 1
  (satisfactory), 4-6 Level 2 (adequate), 7-9 Level 3 (controllable),
  10 uncontrolled.

The decision tree takes evaluation descriptors: controllability (bool),
whether adequate performance is attained (bool), the tolerance class
('desired' or 'adequate'), and the pilot compensation required
('none', 'negligible', 'minor', 'moderate', 'considerable',
'extensive', 'intense'). It returns the integer rating 1-10 and
raises ValueError on malformed descriptors or on a contradictory
combination (desired tolerances with compensation beyond minor).
"""

COMPENSATION_LEVELS = (
    "none", "negligible", "minor", "moderate", "considerable",
    "extensive", "intense",
)
TOLERANCE_CLASSES = ("desired", "adequate")

# Rating per (tolerance class, compensation) once adequate performance
# is attained and the aircraft is controllable.
_SATISFACTORY = {  # desired tolerances, 1-3 band
    "none": 1,
    "negligible": 2,
    "minor": 3,
}
_WARRANT_IMPROVEMENT = {  # adequate tolerances, 4-6 band
    "none": 4,
    "negligible": 4,
    "minor": 4,
    "moderate": 5,
    "considerable": 6,
    "extensive": 6,
}
_REQUIRE_IMPROVEMENT = {  # adequate performance not attainable, 7-9 band
    "none": 7,
    "negligible": 7,
    "minor": 7,
    "moderate": 8,
    "considerable": 8,
    "extensive": 9,
    "intense": 9,
}


def cooper_harper_rating(controllable, adequate_performance, tolerances,
                         compensation):
    """Integer Cooper-Harper rating (1-10) from evaluation descriptors.

    Decision tree: uncontrollable gives 10; adequate performance not
    attainable gives 7-9 by the compensation needed to retain control;
    desired tolerances give 1-3 by compensation; adequate tolerances
    give 4-6 by compensation. Worked anchors:
    (True, True, 'desired', 'none') = 1;
    (True, True, 'desired', 'minor') = 3;
    (True, True, 'adequate', 'considerable') = 6;
    (True, False, 'adequate', 'extensive') = 9;
    (False, True, 'desired', 'none') = 10.
    Raises ValueError on non-bool flags, unknown tolerance or
    compensation strings, or desired tolerances combined with
    compensation beyond minor.
    """
    if not isinstance(controllable, bool):
        raise ValueError("controllable must be a bool, got %r"
                         % (controllable,))
    if not isinstance(adequate_performance, bool):
        raise ValueError("adequate_performance must be a bool, got %r"
                         % (adequate_performance,))
    if tolerances not in TOLERANCE_CLASSES:
        raise ValueError(
            "tolerances must be one of %s, got %r"
            % (", ".join(TOLERANCE_CLASSES), tolerances))
    if compensation not in COMPENSATION_LEVELS:
        raise ValueError(
            "compensation must be one of %s, got %r"
            % (", ".join(COMPENSATION_LEVELS), compensation))

    if not controllable:
        return 10
    if not adequate_performance:
        return _REQUIRE_IMPROVEMENT[compensation]
    if tolerances == "desired":
        if compensation not in _SATISFACTORY:
            raise ValueError(
                "compensation %r contradicts desired tolerances; the "
                "aircraft would be rated in the 4-6 band"
                % (compensation,))
        return _SATISFACTORY[compensation]
    return _WARRANT_IMPROVEMENT[compensation]


def rating_band(rating):
    """Cooper-Harper band name for a rating in 1-10.

    Bands: 1-3 'satisfactory without improvement', 4-6 'deficiencies
    warrant improvement', 7-9 'deficiencies require improvement',
    10 'uncontrollable'. Raises ValueError outside 1-10.
    """
    if not isinstance(rating, int) or not (1 <= rating <= 10):
        raise ValueError("rating must be an integer in 1-10, got %r"
                         % (rating,))
    if rating <= 3:
        return "satisfactory without improvement"
    if rating <= 6:
        return "deficiencies warrant improvement"
    if rating <= 9:
        return "deficiencies require improvement"
    return "uncontrollable"


def handling_qualities_level(rating):
    """Handling qualities level for a rating (MIL-STD-1797A framing).

    1-3 Level 1 (satisfactory), 4-6 Level 2 (adequate), 7-9 Level 3
    (controllable), 10 uncontrolled. Raises ValueError outside 1-10.
    """
    if not isinstance(rating, int) or not (1 <= rating <= 10):
        raise ValueError("rating must be an integer in 1-10, got %r"
                         % (rating,))
    if rating <= 3:
        return "Level 1"
    if rating <= 6:
        return "Level 2"
    if rating <= 9:
        return "Level 3"
    return "uncontrolled"


def demonstrate():
    """Print a demonstration evaluation across the rating bands."""
    cases = [
        (True, True, "desired", "none"),
        (True, True, "desired", "negligible"),
        (True, True, "desired", "minor"),
        (True, True, "adequate", "minor"),
        (True, True, "adequate", "moderate"),
        (True, True, "adequate", "considerable"),
        (True, False, "adequate", "minor"),
        (True, False, "adequate", "considerable"),
        (True, False, "adequate", "extensive"),
        (False, True, "desired", "none"),
    ]
    for case in cases:
        r = cooper_harper_rating(*case)
        print("%-5s controllable=%-5s adequate=%-5s tolerances=%-8s "
              "compensation=%-12s -> rating %d (%s, %s)"
              % (case, case[0], case[1], case[2], case[3], r,
                 rating_band(r), handling_qualities_level(r)))


if __name__ == "__main__":
    demonstrate()
