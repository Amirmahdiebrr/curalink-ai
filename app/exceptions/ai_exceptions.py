"""
AI related exceptions.
"""


class AIException(Exception):
    """
    Base AI exception.
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
    ):

        self.message = message
        self.provider = provider

        super().__init__(message)


class AIProviderException(AIException):
    """
    Provider communication error.
    """

    pass


class AIAuthenticationException(AIException):
    """
    API key or authentication error.
    """

    pass


class AIRateLimitException(AIException):
    """
    Rate limit exceeded.
    """

    pass


class AITimeoutException(AIException):
    """
    Provider timeout.
    """

    pass


class AIResponseException(AIException):
    """
    Invalid AI response.
    """

    pass