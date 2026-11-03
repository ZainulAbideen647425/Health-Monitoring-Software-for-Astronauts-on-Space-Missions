"""Errors raised when business rules are broken. The API layer translates them to HTTP responses."""


class AstronautHealthMonitorError(Exception):
    """Base class for all errors raised by this application."""


class MissionNotFoundError(AstronautHealthMonitorError):
    """The requested mission does not exist."""


class AstronautNotFoundError(AstronautHealthMonitorError):
    """The requested astronaut does not exist."""


class DeviceNotFoundError(AstronautHealthMonitorError):
    """The requested measuring device does not exist."""


class ImplausibleMeasurementError(AstronautHealthMonitorError):
    """The measured value lies outside what a living human could show (probably a typing mistake)."""


class InvalidMeasurementTimeError(AstronautHealthMonitorError):
    """The measurement time has no timezone, or is later than the current time (beyond the clock tolerance)."""
