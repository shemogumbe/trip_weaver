class IntegrationError(Exception):
    """Base exception for integration-level failures (config, connectivity, auth)."""


class UpstreamAPIError(Exception):
    """Represents an upstream API call failure (quota, 4xx/5xx, malformed response)."""
