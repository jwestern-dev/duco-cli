#!/usr/bin/env python3
"""HTTP transport for the Duino-Coin SDK."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from requests import Response
import requests
from requests.adapters import HTTPAdapter

from .config import DucoAPIConfig, DucoAPIRequestConfig
from .errors import (
    DucoAPIHTTPError,
    DucoAPIRequestError,
    DucoAPIResponseError,
)


JSONValue = (
    None
    | bool
    | int
    | float
    | str
    | list["JSONValue"]
    | dict[str, "JSONValue"]
)


class DucoTransport:
    """HTTP session, URL handling and JSON decoding for the SDK.

    The client and parsers handle DUCO-specific success flags and models.
    """

    def __init__(
        self,
        config: DucoAPIConfig | None = None,
        session: requests.Session | None = None,
    ) -> None:
        """Use the supplied session or create one with the SDK defaults."""
        self._config = config or DucoAPIConfig()
        self._session = session or requests.Session()

        self._configure_session()

    @property
    def config(self) -> DucoAPIConfig:
        """Return the configuration for this transport."""
        return self._config

    @property
    def session(self) -> requests.Session:
        """Return the underlying Requests session."""
        return self._session

    def _configure_session(self) -> None:
        """Set default headers and mount adapters for connection reuse."""
        self._session.headers.setdefault("Accept", "application/json")
        self._session.headers.setdefault("User-Agent", self._config.user_agent)

        # Reuse connections across successive CLI commands.
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
        )

        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def build_url(self, endpoint: str) -> str:
        """Resolve a relative endpoint against the configured API base URL."""
        return self._config.endpoint_url(endpoint)

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        json: Any = None,
        config: DucoAPIRequestConfig | None = None,
    ) -> JSONValue:
        """Send an HTTP request and decode the response as JSON.

        Raise an SDK error for transport failures, HTTP errors or invalid JSON.
        The caller checks application-level failures in the success field.
        """
        request_config = config or DucoAPIRequestConfig()

        url = self.build_url(endpoint)
        timeout = (
            request_config.timeout
            if request_config.timeout is not None
            else self._config.timeout
        )

        headers = dict(request_config.headers)

        try:
            response = self._session.request(
                method=method.upper(),
                url=url,
                params=params,
                data=data,
                json=json,
                headers=headers or None,
                timeout=timeout,
                allow_redirects=request_config.allow_redirects,
            )
        except requests.RequestException as exc:
            raise DucoAPIRequestError(
                f"Request to the Duino-Coin API failed: {exc}",
                endpoint=endpoint,
                original_error=exc,
            ) from exc

        if not request_config.allow_redirects and 300 <= response.status_code < 400:
            raise DucoAPIHTTPError(
                "The Duino-Coin API returned a redirect.",
                endpoint=endpoint,
                status_code=response.status_code,
            )

        self._raise_for_http_error(
            response=response,
            endpoint=endpoint,
        )

        return self._decode_json(
            response=response,
            endpoint=endpoint,
        )

    def _raise_for_http_error(
        self,
        *,
        response: Response,
        endpoint: str,
    ) -> None:
        """Raise an HTTP error with any details returned by the server."""
        if response.ok:
            return

        server = self._extract_server(response)

        message = (
            f"Duino-Coin API returned HTTP "
            f"{response.status_code} for {endpoint}"
        )

        payload: Any = None

        # A proxy or gateway can return an HTML error page.
        try:
            payload = response.json()
        except ValueError:
            payload = response.text[:500]

        if isinstance(payload, Mapping):
            api_message = payload.get("message")

            if isinstance(api_message, str) and api_message.strip():
                message = api_message.strip()

            server_value = payload.get("server")

            if isinstance(server_value, str):
                server = server_value

        raise DucoAPIHTTPError(
            message,
            endpoint=endpoint,
            status_code=response.status_code,
            server=server,
            response=payload,
        )

    def _decode_json(
        self,
        *,
        response: Response,
        endpoint: str,
    ) -> JSONValue:
        """Decode the body or include a short excerpt in the response error."""
        try:
            return response.json()
        except ValueError as exc:
            body = response.text[:500]

            raise DucoAPIResponseError(
                (
                    "Duino-Coin API returned an invalid JSON response: "
                    f"{body!r}"
                ),
                endpoint=endpoint,
                status_code=response.status_code,
                response=body,
            ) from exc

    @staticmethod
    def _extract_server(response: Response) -> str | None:
        """Read the server name from a JSON response when present."""
        try:
            payload = response.json()
        except ValueError:
            return None

        if not isinstance(payload, Mapping):
            return None

        server = payload.get("server")

        if isinstance(server, str) and server.strip():
            return server

        return None

    def close(self) -> None:
        """Close the Requests session."""
        self._session.close()

    def __enter__(self) -> "DucoTransport":
        """Return the transport for use in a with block."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        """Close the session when the with block ends."""
        self.close()
