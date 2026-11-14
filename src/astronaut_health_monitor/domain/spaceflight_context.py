"""How the five NASA spaceflight hazards relate to each health indicator, and how mission environments differ.

Hazard names follow NASA's Human Research Program hazards page (https://www.nasa.gov/hrp/hazards).
The environment ratings are qualitative orientation aids written for this prototype, not mission requirements.
"""

from dataclasses import dataclass
from enum import StrEnum

from astronaut_health_monitor.domain.enumerations import HealthIndicatorType

NASA_HAZARDS_TITLE = "NASA Human Research Program: Hazards of human spaceflight"
NASA_HAZARDS_URL = "https://www.nasa.gov/hrp/hazards"


class SpaceflightHazard(StrEnum):
    SPACE_RADIATION = "space_radiation"
    ISOLATION_AND_CONFINEMENT = "isolation_and_confinement"
    DISTANCE_FROM_EARTH = "distance_from_earth"
    GRAVITY_FIELDS = "gravity_fields"
    HOSTILE_CLOSED_ENVIRONMENT = "hostile_closed_environment"


HAZARD_DISPLAY_NAMES: dict[SpaceflightHazard, str] = {
    SpaceflightHazard.SPACE_RADIATION: "Space radiation",
    SpaceflightHazard.ISOLATION_AND_CONFINEMENT: "Isolation and confinement",
    SpaceflightHazard.DISTANCE_FROM_EARTH: "Distance from Earth",
    SpaceflightHazard.GRAVITY_FIELDS: "Gravity fields",
    SpaceflightHazard.HOSTILE_CLOSED_ENVIRONMENT: "Hostile and closed environments",
}


@dataclass(frozen=True)
class IndicatorSpaceContext:
    indicator_type: HealthIndicatorType
    hazards: tuple[SpaceflightHazard, ...]
    how_hazards_change_it: str
    why_it_needs_checking: str
    how_it_is_measured_on_board: str
    suggested_interval_hours: int  # a prototype suggestion; the mission protocol always decides
    source_title: str = NASA_HAZARDS_TITLE
    source_url: str = NASA_HAZARDS_URL


_GRAVITY = SpaceflightHazard.GRAVITY_FIELDS
_ISOLATION = SpaceflightHazard.ISOLATION_AND_CONFINEMENT
_DISTANCE = SpaceflightHazard.DISTANCE_FROM_EARTH
_CLOSED = SpaceflightHazard.HOSTILE_CLOSED_ENVIRONMENT

_BLOOD_PRESSURE_EFFECT = (
    "In low gravity body fluids move toward the head and the body re-tunes how it controls blood pressure. "
    "Standing up in partial gravity or after landing can make it drop."
)
_BLOOD_PRESSURE_WHY = (
    "Only a measurement shows whether this adaptation is healthy, because mild changes cause no symptoms."
)

INDICATOR_SPACE_CONTEXT: dict[HealthIndicatorType, IndicatorSpaceContext] = {
    HealthIndicatorType.HEART_RATE: IndicatorSpaceContext(
        HealthIndicatorType.HEART_RATE,
        (_GRAVITY, _ISOLATION),
        "Less load on the heart in low gravity, fluid shifts, workload and stress can all change resting heart rate.",
        "A trend in resting heart rate can reveal deconditioning, dehydration or stress before symptoms appear.",
        "A wearable sensor, or a manual pulse count at the wrist. No special equipment is needed.",
        24,
    ),
    HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE: IndicatorSpaceContext(
        HealthIndicatorType.SYSTOLIC_BLOOD_PRESSURE,
        (_GRAVITY, _CLOSED),
        _BLOOD_PRESSURE_EFFECT,
        _BLOOD_PRESSURE_WHY,
        "A cuff monitor, seated and rested for five minutes. The same cuff gives both numbers.",
        24,
    ),
    HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE: IndicatorSpaceContext(
        HealthIndicatorType.DIASTOLIC_BLOOD_PRESSURE,
        (_GRAVITY, _CLOSED),
        _BLOOD_PRESSURE_EFFECT,
        _BLOOD_PRESSURE_WHY,
        "Read from the same cuff measurement as systolic pressure.",
        24,
    ),
    HealthIndicatorType.BLOOD_GLUCOSE: IndicatorSpaceContext(
        HealthIndicatorType.BLOOD_GLUCOSE,
        (_ISOLATION, _CLOSED, _GRAVITY),
        "Limited food variety, stress and less physical load can change how the body handles sugar.",
        "Symptoms of high or low blood sugar are vague. A number settles it and shows slow drift.",
        "A finger-prick meter or sensor from the mission's approved medical supplies.",
        72,
    ),
    HealthIndicatorType.BODY_TEMPERATURE: IndicatorSpaceContext(
        HealthIndicatorType.BODY_TEMPERATURE,
        (_CLOSED, _GRAVITY),
        "Heat does not rise away from the body in microgravity, and a sealed habitat shares air between the crew.",
        "A fever can be the first sign of infection, which spreads easily in a small shared cabin.",
        "An ear or forehead thermometer. Measure at about the same time each day.",
        24,
    ),
    HealthIndicatorType.SLEEP_DURATION: IndicatorSpaceContext(
        HealthIndicatorType.SLEEP_DURATION,
        (_ISOLATION, _CLOSED),
        "Noise, unusual light cycles and shifting work schedules disturb the body clock.",
        "Sleep loss lowers alertness, mood and immune function, often before the crew notices.",
        "A wearable sensor or a simple sleep diary of hours slept.",
        24,
    ),
    HealthIndicatorType.MOOD_SCORE: IndicatorSpaceContext(
        HealthIndicatorType.MOOD_SCORE,
        (_ISOLATION, _DISTANCE),
        "A small crew, confinement and delayed contact with family and ground teams affect mood.",
        "Low mood and irritability are early signs of behavioral health risk and are easy to hide.",
        "A daily self-rating from 1 to 10. Optional questionnaires can add detail.",
        24,
    ),
    HealthIndicatorType.FATIGUE_LEVEL: IndicatorSpaceContext(
        HealthIndicatorType.FATIGUE_LEVEL,
        (_ISOLATION, _CLOSED, _GRAVITY),
        "Sleep loss, heavy workload and physical deconditioning raise fatigue.",
        "Fatigue causes errors. Tracking it helps plan workload and rest before mistakes happen.",
        "A daily self-rating from 1 (none) to 10 (exhausted).",
        24,
    ),
    HealthIndicatorType.STRESS_LEVEL: IndicatorSpaceContext(
        HealthIndicatorType.STRESS_LEVEL,
        (_ISOLATION, _DISTANCE),
        "Confinement, workload and delayed communication with Earth raise stress.",
        "Lasting stress affects sleep, mood and judgement, and help is slower to arrive far from Earth.",
        "A daily self-rating from 1 (calm) to 10 (extreme stress).",
        24,
    ),
    HealthIndicatorType.PHYSICAL_ACTIVITY: IndicatorSpaceContext(
        HealthIndicatorType.PHYSICAL_ACTIVITY,
        (_GRAVITY,),
        "Low gravity unloads muscles and bones, so daily exercise is the main countermeasure.",
        "Exercise minutes show whether the countermeasure is actually being done.",
        "An exercise log or the minutes counted by a wearable.",
        24,
    ),
}

HAZARD_NOTE_FOR_RADIATION = (
    "No indicator in this app measures radiation. Crews track exposure with dosimeters, so ask the flight surgeon "
    "about your dose."
)


@dataclass(frozen=True)
class MissionEnvironment:
    key: str
    name: str
    gravity: str
    one_way_message_delay: str
    return_to_earth: str
    hazard_levels: dict[SpaceflightHazard, int]  # 1 lower, 2 moderate, 3 high (qualitative)
    hazard_notes: dict[SpaceflightHazard, str]
    health_focus: tuple[str, ...]


MISSION_ENVIRONMENTS: dict[str, MissionEnvironment] = {
    "station": MissionEnvironment(
        "station",
        "Space station (low Earth orbit)",
        "Microgravity",
        "A second or two",
        "Hours to days",
        {
            SpaceflightHazard.SPACE_RADIATION: 2,
            SpaceflightHazard.ISOLATION_AND_CONFINEMENT: 2,
            SpaceflightHazard.DISTANCE_FROM_EARTH: 1,
            SpaceflightHazard.GRAVITY_FIELDS: 3,
            SpaceflightHazard.HOSTILE_CLOSED_ENVIRONMENT: 3,
        },
        {
            SpaceflightHazard.SPACE_RADIATION: "Earth's magnetic field shields part of the radiation.",
            SpaceflightHazard.ISOLATION_AND_CONFINEMENT: "Contact with family and ground teams is frequent.",
            SpaceflightHazard.DISTANCE_FROM_EARTH: "Real-time contact and a return within hours to days.",
            SpaceflightHazard.GRAVITY_FIELDS: "Continuous microgravity: exercise protects bones and muscles.",
            SpaceflightHazard.HOSTILE_CLOSED_ENVIRONMENT: "Shared air, noise and microbes in a sealed habitat.",
        },
        ("Daily exercise for bones and muscles", "Sleep and light schedule", "Cabin air and hygiene"),
    ),
    "transit": MissionEnvironment(
        "transit",
        "Deep-space transit vehicle",
        "Microgravity",
        "Seconds growing to minutes",
        "Weeks to months",
        {
            SpaceflightHazard.SPACE_RADIATION: 3,
            SpaceflightHazard.ISOLATION_AND_CONFINEMENT: 3,
            SpaceflightHazard.DISTANCE_FROM_EARTH: 3,
            SpaceflightHazard.GRAVITY_FIELDS: 3,
            SpaceflightHazard.HOSTILE_CLOSED_ENVIRONMENT: 3,
        },
        {
            SpaceflightHazard.SPACE_RADIATION: "Far outside Earth's magnetic field, so exposure is higher.",
            SpaceflightHazard.ISOLATION_AND_CONFINEMENT: "A small crew in a small vehicle for a long time.",
            SpaceflightHazard.DISTANCE_FROM_EARTH: "Delayed contact and no quick return: the crew must act on its own.",
            SpaceflightHazard.GRAVITY_FIELDS: "Long microgravity exposure before any landing.",
            SpaceflightHazard.HOSTILE_CLOSED_ENVIRONMENT: "No outside help with air, water or supplies.",
        },
        ("Self-reliance: act early on trends", "Behavioral health and sleep", "Exercise discipline"),
    ),
    "rover": MissionEnvironment(
        "rover",
        "Pressurized rover (surface)",
        "Partial gravity (Moon or Mars)",
        "Depends on location",
        "Depends on distance from the base",
        {
            SpaceflightHazard.SPACE_RADIATION: 3,
            SpaceflightHazard.ISOLATION_AND_CONFINEMENT: 2,
            SpaceflightHazard.DISTANCE_FROM_EARTH: 2,
            SpaceflightHazard.GRAVITY_FIELDS: 2,
            SpaceflightHazard.HOSTILE_CLOSED_ENVIRONMENT: 3,
        },
        {
            SpaceflightHazard.SPACE_RADIATION: "Thin shielding when travelling away from the base.",
            SpaceflightHazard.ISOLATION_AND_CONFINEMENT: "Very small cabin, but trips are shorter.",
            SpaceflightHazard.DISTANCE_FROM_EARTH: "Often also far from the base's medical help.",
            SpaceflightHazard.GRAVITY_FIELDS: "Partial gravity: the body must re-adapt on every move.",
            SpaceflightHazard.HOSTILE_CLOSED_ENVIRONMENT: "Dust, heat control and limited space in a tiny cabin.",
        },
        ("Hydration and heat", "Balance and bruising risk", "Dust exposure"),
    ),
    "moon": MissionEnvironment(
        "moon",
        "Lunar base",
        "About one-sixth of Earth's gravity",
        "About 1.3 seconds",
        "Days",
        {
            SpaceflightHazard.SPACE_RADIATION: 3,
            SpaceflightHazard.ISOLATION_AND_CONFINEMENT: 2,
            SpaceflightHazard.DISTANCE_FROM_EARTH: 2,
            SpaceflightHazard.GRAVITY_FIELDS: 2,
            SpaceflightHazard.HOSTILE_CLOSED_ENVIRONMENT: 2,
        },
        {
            SpaceflightHazard.SPACE_RADIATION: "No magnetic field or thick atmosphere; habitat shielding matters.",
            SpaceflightHazard.ISOLATION_AND_CONFINEMENT: "Near enough for real-time chat, but far from home.",
            SpaceflightHazard.DISTANCE_FROM_EARTH: "A short message delay and a return in days.",
            SpaceflightHazard.GRAVITY_FIELDS: "Partial gravity gives some bone and muscle load.",
            SpaceflightHazard.HOSTILE_CLOSED_ENVIRONMENT: "Fine, sharp lunar dust can irritate eyes and lungs.",
        },
        ("Radiation awareness", "Dust control", "Exercise that adds load"),
    ),
    "mars": MissionEnvironment(
        "mars",
        "Mars base",
        "About 38 percent of Earth's gravity",
        "About 3 to 22 minutes",
        "Months",
        {
            SpaceflightHazard.SPACE_RADIATION: 3,
            SpaceflightHazard.ISOLATION_AND_CONFINEMENT: 3,
            SpaceflightHazard.DISTANCE_FROM_EARTH: 3,
            SpaceflightHazard.GRAVITY_FIELDS: 2,
            SpaceflightHazard.HOSTILE_CLOSED_ENVIRONMENT: 2,
        },
        {
            SpaceflightHazard.SPACE_RADIATION: "A thin atmosphere gives only limited protection.",
            SpaceflightHazard.ISOLATION_AND_CONFINEMENT: "The longest, most isolated mission type.",
            SpaceflightHazard.DISTANCE_FROM_EARTH: "A message takes minutes each way and a return takes months.",
            SpaceflightHazard.GRAVITY_FIELDS: "Partial gravity, but a long time spent in microgravity first.",
            SpaceflightHazard.HOSTILE_CLOSED_ENVIRONMENT: "Dust and a sealed habitat with limited resupply.",
        },
        ("Autonomy: ground answers arrive late", "Behavioral health over many months", "Bone and muscle protection"),
    ),
}

LEVEL_WORDS = {1: "Lower", 2: "Moderate", 3: "High"}
