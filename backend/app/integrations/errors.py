class IntegrationError(RuntimeError):
    """Raised when an internal integration is misconfigured or unavailable."""


class UpstreamAPIError(RuntimeError):
    """Raised when an upstream provider call fails unexpectedly."""
