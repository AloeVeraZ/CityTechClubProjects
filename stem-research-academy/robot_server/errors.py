"""Robot controller exceptions."""


class RobotError(Exception):
    """Base exception for expected controller failures."""


class ConfigurationError(RobotError):
    """A port map or setting is unsafe or invalid."""


class HardwareUnavailable(RobotError):
    """Requested hardware is missing or cannot be accessed."""
