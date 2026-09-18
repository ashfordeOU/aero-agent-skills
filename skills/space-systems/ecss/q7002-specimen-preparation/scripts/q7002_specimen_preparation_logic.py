"""Specimen preparation for the thermal-vacuum outgassing screening test.

Anchor: ECSS-Q-ST-70-02C, test-item clause -- how many specimens the screening
needs, what each one has to weigh, how bulk material is cut so that it sits in
the sample holder, and the conditioning the specimens see before the test.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Size one specimen: a target mass inside the working window, and the number
   of cut pieces needed to reach it from the geometry and density of the stock.
2. Check that a cut piece actually fits the sample holder, comparing the piece
   and the holder on their sorted dimensions rather than axis by axis, since a
   piece may be turned to fit.
3. Count the specimens: a replicate minimum, extra replicates for a material
   that is not homogeneous, and a matching set of carrier blanks for anything
   supplied as a liquid, a paste or a freshly mixed two-part system.
4. Account for the carrier: the figure the screening is computed on is the net
   material mass, not the mass of the boat plus what is in it.
5. Grade the conditioning actually achieved -- duration, temperature and
   relative humidity -- against the specified windows before the specimens go
   into the chamber.
6. Return the plan and every finding that would make its results unusable.
"""

import math

__all__ = [
    "SPECIMEN_MASS_WINDOW_MG",
    "NOMINAL_SPECIMEN_MASS_MG",
    "MINIMUM_SPECIMENS",
    "EXTRA_SPECIMENS_INHOMOGENEOUS",
    "CARRIER_FORMS",
    "BOAT_INNER_MM",
    "CONDITIONING_HOURS",
    "CONDITIONING_TEMPERATURE_C",
    "CONDITIONING_TEMPERATURE_TOLERANCE_C",
    "CONDITIONING_HUMIDITY_PCT",
    "CONDITIONING_HUMIDITY_TOLERANCE_PCT",
    "GEOMETRY_TOLERANCE_MM",
    "MASS_TOLERANCE_MG",
    "CONDITIONING_TOLERANCE",
    "piece_volume_mm3",
    "piece_mass_mg",
    "piece_fits_holder",
    "pieces_per_specimen",
    "specimen_count",
    "net_specimen_mass_mg",
    "specimen_mass_findings",
    "conditioning_findings",
    "plan_specimens",
]

# Working mass window for one specimen, in milligrams, and the mass a plan aims
# at when nothing else constrains it.
SPECIMEN_MASS_WINDOW_MG = (100.0, 300.0)
NOMINAL_SPECIMEN_MASS_MG = 200.0

# Replicates: the screening is read across specimens, not off a single one.
MINIMUM_SPECIMENS = 3
EXTRA_SPECIMENS_INHOMOGENEOUS = 2

# Forms that cannot stand on their own in the holder and need a carrier, plus a
# matching blank so the carrier's own loss is subtracted.
CARRIER_FORMS = ("liquid", "paste", "two-part-mixed", "grease", "slurry")

# Usable inner dimensions of the sample holder, in millimetres.
BOAT_INNER_MM = (30.0, 12.0, 5.0)

# Conditioning window the specimens are held in before the test.
CONDITIONING_HOURS = 24.0
CONDITIONING_TEMPERATURE_C = 23.0
CONDITIONING_TEMPERATURE_TOLERANCE_C = 2.0
CONDITIONING_HUMIDITY_PCT = 50.0
CONDITIONING_HUMIDITY_TOLERANCE_PCT = 5.0

# Dimensions and masses are measured quantities; a piece exactly the size of the
# holder fits, and a mass exactly on a window bound is inside it.
GEOMETRY_TOLERANCE_MM = 1e-9
MASS_TOLERANCE_MG = 1e-9
CONDITIONING_TOLERANCE = 1e-9


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _dimensions(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("%s must be a (length, width, thickness) triple in mm" % label)
    return tuple(_positive(v, "%s component" % label) for v in value)


def piece_volume_mm3(dimensions_mm):
    """Return the volume of one cut piece in cubic millimetres."""
    length, width, thickness = _dimensions(dimensions_mm, "dimensions_mm")
    return length * width * thickness


def piece_mass_mg(dimensions_mm, density_g_cm3):
    """Return the mass of one cut piece in milligrams."""
    density = _positive(density_g_cm3, "density_g_cm3")
    volume_cm3 = piece_volume_mm3(dimensions_mm) / 1000.0
    return volume_cm3 * density * 1000.0


def piece_fits_holder(dimensions_mm, holder_inner_mm=BOAT_INNER_MM):
    """Return True when a piece fits the holder in some orientation."""
    piece = sorted(_dimensions(dimensions_mm, "dimensions_mm"))
    holder = sorted(_dimensions(holder_inner_mm, "holder_inner_mm"))
    return all(p <= h + GEOMETRY_TOLERANCE_MM for p, h in zip(piece, holder))


def pieces_per_specimen(target_mass_mg, one_piece_mass_mg):
    """Return how many cut pieces are needed to reach the target specimen mass."""
    target = _positive(target_mass_mg, "target_mass_mg")
    piece = _positive(one_piece_mass_mg, "one_piece_mass_mg")
    count = int(math.ceil(target / piece - MASS_TOLERANCE_MG))
    return max(1, count)


def specimen_count(material_form, homogeneous=True, requested=None):
    """Return the number of specimens and carrier blanks the plan needs."""
    if not isinstance(material_form, str) or not material_form.strip():
        raise ValueError("material_form must be a non-empty string")
    if not isinstance(homogeneous, bool):
        raise ValueError("homogeneous must be a boolean")
    form = material_form.strip().lower()
    required = MINIMUM_SPECIMENS
    if not homogeneous:
        required += EXTRA_SPECIMENS_INHOMOGENEOUS
    if requested is not None:
        if not isinstance(requested, int) or isinstance(requested, bool):
            raise ValueError("requested must be an integer number of specimens")
        if requested < required:
            raise ValueError(
                "%d specimens were requested but this material needs at least %d"
                % (requested, required)
            )
        required = requested
    blanks = required if form in CARRIER_FORMS else 0
    return {
        "form": form,
        "specimens": required,
        "carrier_blanks": blanks,
        "carrier_required": form in CARRIER_FORMS,
    }


def net_specimen_mass_mg(gross_mass_mg, carrier_mass_mg=0.0):
    """Return the material mass the screening is computed on."""
    gross = _positive(gross_mass_mg, "gross_mass_mg")
    if not isinstance(carrier_mass_mg, (int, float)) or isinstance(carrier_mass_mg, bool):
        raise ValueError("carrier_mass_mg must be a real number")
    carrier = float(carrier_mass_mg)
    if not math.isfinite(carrier) or carrier < 0.0:
        raise ValueError("carrier_mass_mg must be non-negative and finite, got %r"
                         % (carrier_mass_mg,))
    net = gross - carrier
    if net <= MASS_TOLERANCE_MG:
        raise ValueError(
            "carrier mass %g mg leaves no material mass against a gross of %g mg"
            % (carrier, gross)
        )
    return net


def specimen_mass_findings(mass_mg):
    """Grade one specimen mass against the working window."""
    mass = _positive(mass_mg, "mass_mg")
    low, high = SPECIMEN_MASS_WINDOW_MG
    findings = []
    if mass < low - MASS_TOLERANCE_MG:
        findings.append(
            "specimen mass of %g mg is below the %g mg working minimum; the measured "
            "loss would sit too close to the balance resolution" % (mass, low)
        )
    if mass > high + MASS_TOLERANCE_MG:
        findings.append(
            "specimen mass of %g mg is above the %g mg working maximum" % (mass, high)
        )
    return findings


def conditioning_findings(achieved):
    """Grade the conditioning actually achieved against the specified windows."""
    _require_mapping(achieved, "achieved")
    for key in ("hours", "temperature_c", "humidity_pct"):
        if key not in achieved:
            raise ValueError("achieved conditioning missing required key '%s'" % key)
    hours = achieved["hours"]
    if not isinstance(hours, (int, float)) or isinstance(hours, bool):
        raise ValueError("conditioning hours must be a real number")
    hours = float(hours)
    if not math.isfinite(hours) or hours < 0.0:
        raise ValueError("conditioning hours must be non-negative and finite")
    findings = []
    if hours < CONDITIONING_HOURS - CONDITIONING_TOLERANCE:
        findings.append(
            "conditioning ran %g h, short of the %g h specified" % (hours, CONDITIONING_HOURS)
        )
    pairs = (
        (
            "temperature",
            achieved["temperature_c"],
            CONDITIONING_TEMPERATURE_C,
            CONDITIONING_TEMPERATURE_TOLERANCE_C,
            "degC",
        ),
        (
            "relative humidity",
            achieved["humidity_pct"],
            CONDITIONING_HUMIDITY_PCT,
            CONDITIONING_HUMIDITY_TOLERANCE_PCT,
            "%RH",
        ),
    )
    for label, value, nominal, tolerance, unit in pairs:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("conditioning %s must be a real number" % label)
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("conditioning %s must be finite" % label)
        deviation = abs(value - nominal)
        if deviation > tolerance + CONDITIONING_TOLERANCE:
            findings.append(
                "conditioning %s of %g %s is outside %g +/- %g %s"
                % (label, value, unit, nominal, tolerance, unit)
            )
    return findings


def plan_specimens(material):
    """Build the specimen plan for one material and return it with its findings.

    material keys: form, density_g_cm3, piece_dimensions_mm, optional
    homogeneous, requested_specimens, target_specimen_mass_mg, carrier_mass_mg
    and achieved_conditioning.
    """
    _require_mapping(material, "material")
    for key in ("form", "density_g_cm3", "piece_dimensions_mm"):
        if key not in material:
            raise ValueError("material missing required key '%s'" % key)
    counts = specimen_count(
        material["form"],
        material.get("homogeneous", True),
        material.get("requested_specimens"),
    )
    target = material.get("target_specimen_mass_mg", NOMINAL_SPECIMEN_MASS_MG)
    target = _positive(target, "target_specimen_mass_mg")
    findings = list(specimen_mass_findings(target))

    dimensions = _dimensions(material["piece_dimensions_mm"], "piece_dimensions_mm")
    fits = piece_fits_holder(dimensions)
    if not fits:
        findings.append(
            "a cut piece of %g x %g x %g mm does not fit the sample holder in any "
            "orientation; cut it smaller" % dimensions
        )
    one_piece = piece_mass_mg(dimensions, material["density_g_cm3"])
    pieces = pieces_per_specimen(target, one_piece)

    carrier = float(material.get("carrier_mass_mg") or 0.0)
    if counts["carrier_required"] and carrier <= 0.0:
        findings.append(
            "form '%s' needs a carrier and a matching blank, but no carrier mass was "
            "declared" % counts["form"]
        )
    # The target is the material mass the screening is computed on; the balance
    # sees that plus the carrier it was applied to.
    gross = target + carrier
    net = net_specimen_mass_mg(gross, carrier)

    conditioning = material.get("achieved_conditioning")
    if conditioning is not None:
        findings.extend(conditioning_findings(conditioning))

    total_material_mg = target * counts["specimens"]
    return {
        "form": counts["form"],
        "specimens": counts["specimens"],
        "carrier_blanks": counts["carrier_blanks"],
        "target_specimen_mass_mg": target,
        "gross_specimen_mass_mg": gross,
        "carrier_mass_mg": carrier,
        "net_specimen_mass_mg": net,
        "piece_mass_mg": one_piece,
        "pieces_per_specimen": pieces,
        "piece_fits_holder": fits,
        "total_material_mg": total_material_mg,
        "findings": findings,
        "ready": not findings,
    }
