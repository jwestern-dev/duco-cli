#!/usr/bin/env python3
"""Errors raised by the Duino-Coin SDK."""

from __future__ import annotations

from typing import Any


class DucoAPIError(Exception):
    """Base SDK error, with request and response details when available."""

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        status_code: int | None = None,
        server: str | None = None,
        response: Any = None,
    ) -> None:
        """Store the message, endpoint, HTTP status, server and raw response."""
        super().__init__(message)

        self.message = message
        self.endpoint = endpoint
        self.status_code = status_code
        self.server = server
        self.response = response

    def __str__(self) -> str:
        """Include the endpoint, HTTP status and server when known."""
        details: list[str] = []

        if self.endpoint:
            details.append(f"endpoint={self.endpoint}")

        if self.status_code is not None:
            details.append(f"status={self.status_code}")

        if self.server:
            details.append(f"server={self.server}")

        if not details:
            return self.message

        return f"{self.message} ({', '.join(details)})"


class DucoAPIRequestError(DucoAPIError):
    """The HTTP client could not complete the request."""

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Keep the original HTTP client exception for inspection."""
        super().__init__(
            message,
            endpoint=endpoint,
        )

        self.original_error = original_error


class DucoAPIHTTPError(DucoAPIError):
    """The server returned an HTTP error or a redirect the caller declined."""

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        status_code: int | None = None,
        server: str | None = None,
        response: Any = None,
    ) -> None:
        """Record the HTTP status and any response details."""
        super().__init__(
            message,
            endpoint=endpoint,
            status_code=status_code,
            server=server,
            response=response,
        )


class DucoAPIResponseError(DucoAPIError):
    """The response could not be decoded or did not match the API schema."""

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        status_code: int | None = None,
        server: str | None = None,
        response: Any = None,
    ) -> None:
        """Record the response that could not be decoded or validated."""
        super().__init__(
            message,
            endpoint=endpoint,
            status_code=status_code,
            server=server,
            response=response,
        )


class DucoAPIOperationError(DucoAPIError):
    """The API reported success=false, often in an HTTP 200 response."""

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        server: str | None = None,
        response: Any = None,
    ) -> None:
        """Keep the API message and the rejected response."""
        super().__init__(
            message,
            endpoint=endpoint,
            server=server,
            response=response,
        )


class DucoAPIAuthenticationError(DucoAPIOperationError):
    """The API rejected the account credentials."""

    pass


class DucoAPIValidationError(DucoAPIError, ValueError):
    """Invalid SDK arguments. This is also a ValueError."""

    pass
