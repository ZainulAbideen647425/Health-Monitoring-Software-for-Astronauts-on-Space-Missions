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


class MeasurementNotFoundError(AstronautHealthMonitorError):
    """The requested measurement does not exist."""


class DuplicateMeasurementReferenceError(AstronautHealthMonitorError):
    """A measurement with the same client reference is already stored."""


class AuthenticationRequiredError(AstronautHealthMonitorError):
    """The request has no valid signed-in session."""


class AuthenticationFailedError(AstronautHealthMonitorError):
    """The username or password is wrong. The message never says which one."""


class AccountLockedError(AstronautHealthMonitorError):
    """Too many wrong passwords were entered; the account is locked for a while."""


class PermissionDeniedError(AstronautHealthMonitorError):
    """The signed-in user's role does not allow this action."""


class UserAlreadyExistsError(AstronautHealthMonitorError):
    """A user with this username already exists."""


class InvalidUserDetailsError(AstronautHealthMonitorError):
    """The username, password or role link of a new user is not acceptable."""


class EncryptionNotConfiguredError(AstronautHealthMonitorError):
    """Encrypted fields were used before an encryption key was configured."""


class FieldDecryptionError(AstronautHealthMonitorError):
    """Stored encrypted data could not be decrypted (wrong key, or the data was altered)."""


class DemoModeDisabledError(AstronautHealthMonitorError):
    """Demo features were requested but demo mode is switched off."""


class RegistrationDisabledError(AstronautHealthMonitorError):
    """Self-registration was requested but is switched off. Accounts must then be created by mission control."""
