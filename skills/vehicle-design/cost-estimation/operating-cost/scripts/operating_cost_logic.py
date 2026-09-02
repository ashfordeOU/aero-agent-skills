#!/usr/bin/env python3
"""Direct operating cost estimation logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): direct operating cost (DOC) per flight decomposes into fuel,
crew, maintenance (labor plus material), insurance, and landing and
navigation fees, a standard airline operating economics breakdown.
Fuel cost per flight is block fuel in kg times the fuel price per kg.
Crew cost per flight is flight hours times the crew size times the
cost per crew hour. Maintenance cost per flight is flight hours times
the man-hours per flight hour times the labor rate times (1 + material
factor), where the material factor is the ratio of material cost to
labor cost. Insurance cost per flight is the aircraft price times the
annual insurance rate times the flown fraction of the year, flight
hours divided by the utilization hours per year. Landing and
navigation fees are fixed per flight. DOC per flight is the sum of the
five elements; DOC per flight hour divides the sum by the flight
hours.

Units: costs in the same currency unit throughout (for example USD),
block fuel in kg, fuel price per kg, rates as unitless fractions,
times in hours. Invalid inputs raise ValueError throughout.
"""


def fuel_cost_per_flight(block_fuel_kg, fuel_price_per_kg):
    """Fuel cost for one flight.

    Returns block_fuel_kg * fuel_price_per_kg. Raises ValueError if
    either input is not positive.
    """
    if block_fuel_kg <= 0:
        raise ValueError("block fuel must be positive, got %r" % (block_fuel_kg,))
    if fuel_price_per_kg <= 0:
        raise ValueError(
            "fuel price per kg must be positive, got %r" % (fuel_price_per_kg,)
        )
    return block_fuel_kg * fuel_price_per_kg


def crew_cost_per_flight(flight_hours, crew_size, cost_per_crew_hour):
    """Crew cost for one flight.

    Returns flight_hours * crew_size * cost_per_crew_hour. Raises
    ValueError if any input is not positive.
    """
    if flight_hours <= 0:
        raise ValueError("flight hours must be positive, got %r" % (flight_hours,))
    if crew_size <= 0:
        raise ValueError("crew size must be positive, got %r" % (crew_size,))
    if cost_per_crew_hour <= 0:
        raise ValueError(
            "cost per crew hour must be positive, got %r" % (cost_per_crew_hour,)
        )
    return flight_hours * crew_size * cost_per_crew_hour


def maintenance_cost_per_flight(
    flight_hours, mmh_fh, labor_rate_per_hour, material_factor
):
    """Maintenance cost for one flight, labor plus material.

    Returns flight_hours * mmh_fh * labor_rate_per_hour *
    (1 + material_factor), with mmh_fh the man-hours per flight hour
    and material_factor the material-to-labor cost ratio. Raises
    ValueError if any input is not positive or material_factor is
    negative.
    """
    if flight_hours <= 0:
        raise ValueError("flight hours must be positive, got %r" % (flight_hours,))
    if mmh_fh <= 0:
        raise ValueError(
            "man-hours per flight hour must be positive, got %r" % (mmh_fh,)
        )
    if labor_rate_per_hour <= 0:
        raise ValueError(
            "labor rate per hour must be positive, got %r" % (labor_rate_per_hour,)
        )
    if material_factor < 0:
        raise ValueError(
            "material factor must be non-negative, got %r" % (material_factor,)
        )
    return flight_hours * mmh_fh * labor_rate_per_hour * (1.0 + material_factor)


def insurance_cost_per_flight(
    aircraft_price, annual_insurance_rate, utilization_hours_per_year, flight_hours
):
    """Insurance cost for one flight.

    Returns aircraft_price * annual_insurance_rate *
    (flight_hours / utilization_hours_per_year): the annual premium
    prorated by the flown fraction of the year. Raises ValueError if
    any input is not positive.
    """
    if aircraft_price <= 0:
        raise ValueError("aircraft price must be positive, got %r" % (aircraft_price,))
    if annual_insurance_rate <= 0:
        raise ValueError(
            "annual insurance rate must be positive, got %r"
            % (annual_insurance_rate,)
        )
    if utilization_hours_per_year <= 0:
        raise ValueError(
            "utilization hours per year must be positive, got %r"
            % (utilization_hours_per_year,)
        )
    if flight_hours <= 0:
        raise ValueError("flight hours must be positive, got %r" % (flight_hours,))
    return (
        aircraft_price
        * annual_insurance_rate
        * (flight_hours / utilization_hours_per_year)
    )


def landing_fees_per_flight(landing_fee, navigation_fee):
    """Landing and navigation fees for one flight.

    Returns the sum of the two fees. Raises ValueError if either fee
    is negative.
    """
    if landing_fee < 0:
        raise ValueError("landing fee must be non-negative, got %r" % (landing_fee,))
    if navigation_fee < 0:
        raise ValueError(
            "navigation fee must be non-negative, got %r" % (navigation_fee,)
        )
    return landing_fee + navigation_fee


def doc_per_flight(fuel, crew, maintenance, insurance, fees):
    """Direct operating cost for one flight.

    Returns the sum of the five element costs. Raises ValueError if
    any element is negative.
    """
    elements = [fuel, crew, maintenance, insurance, fees]
    for name, value in zip(
        ("fuel", "crew", "maintenance", "insurance", "fees"), elements
    ):
        if value < 0:
            raise ValueError("%s cost must be non-negative, got %r" % (name, value))
    return sum(elements)


def doc_per_flight_hour(total_doc, flight_hours):
    """Direct operating cost per flight hour.

    Returns total_doc / flight_hours. Raises ValueError if total_doc
    is negative or flight_hours is not positive.
    """
    if total_doc < 0:
        raise ValueError("total DOC must be non-negative, got %r" % (total_doc,))
    if flight_hours <= 0:
        raise ValueError("flight hours must be positive, got %r" % (flight_hours,))
    return total_doc / flight_hours
