#!/usr/bin/env python3
"""Errors raised by the Duino-Coin SDK."""

from __future__ import annotations

from typing import Any


class DucoAPIError(Exception):
    """
    *DucoAPIError Base SDK error, with request and response details when available.*

    message str - Message for the caller.
    endpoint str | None - API route associated with the request or response.
    status_code int | None - HTTP status received from the server.
    server str | None - Server identifier reported by the API.
    response Any - Response that supplied the error details.
    """

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        status_code: int | None = None,
        server: str | None = None,
        response: Any = None,
    ) -> None:
        """
        *__init__ Store the message, endpoint, HTTP status, server and raw response.*

        message str - Message for the caller.
        endpoint str | None - API route associated with the request or response.
        status_code int | None - HTTP status received from the server.
        server str | None - Server identifier reported by the API.
        response Any - Response that supplied the error details.
        """
        super().__init__(message)

        self.message = message
        self.endpoint = endpoint
        self.status_code = status_code
        self.server = server
        self.response = response

    def __str__(self) -> str:
        """
        *__str__ Include the endpoint, HTTP status and server when known.*
        """
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
    """
    *DucoAPIRequestError The HTTP client could not complete the request.*

    message str - Message for the caller.
    endpoint str | None - API route associated with the request or response.
    original_error Exception | None - Underlying transport error when explicitly supplied.
    """

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        *__init__ Keep the original HTTP client exception for inspection.*

        message str - Message for the caller.
        endpoint str | None - API route associated with the request or response.
        original_error Exception | None - Underlying transport error when explicitly supplied.
        """
        super().__init__(
            message,
            endpoint=endpoint,
        )

        self.original_error = original_error


class DucoAPIHTTPError(DucoAPIError):
    """
    *DucoAPIHTTPError The server returned an HTTP error or a redirect the caller declined.*

    message str - Message for the caller.
    endpoint str | None - API route associated with the request or response.
    status_code int | None - HTTP status received from the server.
    server str | None - Server identifier reported by the API.
    response Any - Response that supplied the error details.
    """

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        status_code: int | None = None,
        server: str | None = None,
        response: Any = None,
    ) -> None:
        """
        *__init__ Record the HTTP status and any response details.*

        message str - Message for the caller.
        endpoint str | None - API route associated with the request or response.
        status_code int | None - HTTP status received from the server.
        server str | None - Server identifier reported by the API.
        response Any - Response that supplied the error details.
        """
        super().__init__(
            message,
            endpoint=endpoint,
            status_code=status_code,
            server=server,
            response=response,
        )


class DucoAPIResponseError(DucoAPIError):
    """
    *DucoAPIResponseError The response could not be decoded or did not match the API schema.*

    message str - Message for the caller.
    endpoint str | None - API route associated with the request or response.
    status_code int | None - HTTP status received from the server.
    server str | None - Server identifier reported by the API.
    response Any - Response that supplied the error details.
    """

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        status_code: int | None = None,
        server: str | None = None,
        response: Any = None,
    ) -> None:
        """
        *__init__ Record the response that could not be decoded or validated.*

        message str - Message for the caller.
        endpoint str | None - API route associated with the request or response.
        status_code int | None - HTTP status received from the server.
        server str | None - Server identifier reported by the API.
        response Any - Response that supplied the error details.
        """
        super().__init__(
            message,
            endpoint=endpoint,
            status_code=status_code,
            server=server,
            response=response,
        )


class DucoAPIOperationError(DucoAPIError):
    """
    *DucoAPIOperationError The API reported success=false, often in an HTTP 200 response.*

    message str - Message for the caller.
    endpoint str | None - API route associated with the request or response.
    server str | None - Server identifier reported by the API.
    response Any - Response that supplied the error details.
    """

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        server: str | None = None,
        response: Any = None,
    ) -> None:
        """
        *__init__ Keep the API message and the rejected response.*

        message str - Message for the caller.
        endpoint str | None - API route associated with the request or response.
        server str | None - Server identifier reported by the API.
        response Any - Response that supplied the error details.
        """
        super().__init__(
            message,
            endpoint=endpoint,
            server=server,
            response=response,
        )


class DucoAPIAuthenticationError(DucoAPIOperationError):
    """
    *DucoAPIAuthenticationError The API rejected the account credentials.*

    message str - Message for the caller.
    endpoint str | None - API route associated with the request or response.
    server str | None - Server identifier reported by the API.
    response Any - Response that supplied the error details.
    """

    pass


class DucoAPIValidationError(DucoAPIError, ValueError):
    """
    *DucoAPIValidationError Invalid SDK arguments. This is also a ValueError.*

    message str - Message for the caller.
    endpoint str | None - API route associated with the request or response.
    status_code int | None - HTTP status received from the server.
    server str | None - Server identifier reported by the API.
    response Any - Response that supplied the error details.
    """

    pass
