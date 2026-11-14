from astronaut_health_monitor.domain.enumerations import HealthIndicatorType
from astronaut_health_monitor.domain.spaceflight_context import (
    HAZARD_DISPLAY_NAMES,
    INDICATOR_SPACE_CONTEXT,
    MISSION_ENVIRONMENTS,
    SpaceflightHazard,
)


def test_every_indicator_has_hazard_context_a_source_and_a_schedule() -> None:
    assert set(INDICATOR_SPACE_CONTEXT) == set(HealthIndicatorType)
    for context in INDICATOR_SPACE_CONTEXT.values():
        assert context.hazards, context.indicator_type
        assert context.source_url.startswith("https://www.nasa.gov/")
        assert 1 <= context.suggested_interval_hours <= 168
        for text in (context.how_hazards_change_it, context.why_it_needs_checking, context.how_it_is_measured_on_board):
            assert len(text) > 20


def test_every_environment_rates_all_five_hazards_with_a_note() -> None:
    assert {"station", "transit", "rover", "moon", "mars"} == set(MISSION_ENVIRONMENTS)
    for environment in MISSION_ENVIRONMENTS.values():
        assert set(environment.hazard_levels) == set(SpaceflightHazard) == set(environment.hazard_notes)
        assert all(level in (1, 2, 3) for level in environment.hazard_levels.values())
        assert environment.health_focus


def test_environments_differ_in_the_expected_direction() -> None:
    station, mars = MISSION_ENVIRONMENTS["station"], MISSION_ENVIRONMENTS["mars"]
    distance = SpaceflightHazard.DISTANCE_FROM_EARTH
    assert mars.hazard_levels[distance] > station.hazard_levels[distance]
    assert len(HAZARD_DISPLAY_NAMES) == 5
