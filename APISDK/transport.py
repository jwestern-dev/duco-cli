#!/usr/bin/env python3
"""HTTP transport for the Duino-Coin SDK."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
import logging
from time import perf_counter
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


LOGGER = logging.getLogger("ducocli.http")

JSONValue = (
    None
    | bool
    | int
    | float
    | Decimal
    | str
    | list["JSONValue"]
    | dict[str, "JSONValue"]
)


class DucoTransport:
    """
    *DucoTransport HTTP session, URL handling and JSON decoding for the SDK.*

    config DucoAPIConfig | None - Configuration to apply when creating the client.
    session requests.Session | None - HTTP session to reuse.

    The client and parsers handle DUCO-specific success flags and models.
    """

    def __init__(
        self,
        config: DucoAPIConfig | None = None,
        session: requests.Session | None = None,
    ) -> None:
        """
        *__init__ Use the supplied session or create one with the SDK defaults.*

        config DucoAPIConfig | None - Configuration to apply when creating the client.
        session requests.Session | None - HTTP session to reuse.
        """
        self._config = config or DucoAPIConfig()
        self._session = session if session is not None else requests.Session()
        self._configure_session(use_sdk_headers=session is None)

    @property
    def config(self) -> DucoAPIConfig:
        """
        *config Return the configuration for this transport.*
        """
        return self._config

    @property
    def session(self) -> requests.Session:
        """
        *session Return the underlying Requests session.*
        """
        return self._session

    def _configure_session(self, *, use_sdk_headers: bool) -> None:
        """
        *_configure_session Set default headers and mount adapters for connection reuse.*

        use_sdk_headers bool - Whether the SDK controls the session's default headers.
        """
        defaults = {"Accept": "application/json", "User-Agent": self._config.user_agent}
        if use_sdk_headers:
            self._session.headers.update(defaults)
        else:
            for key, value in defaults.items():
                self._session.headers.setdefault(key, value)

        # Reuse connections across successive CLI commands.
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
        )

        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def build_url(self, endpoint: str) -> str:
        """
        *build_url Resolve a relative endpoint against the configured API base URL.*

        endpoint str - API route associated with the request or response.
        """
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
        """
        *request Send an HTTP request and decode the response as JSON.*

        method str - HTTP request method.
        endpoint str - API route associated with the request or response.
        params Mapping[str, Any] | None - Query parameters to send with the request.
        data Mapping[str, Any] | None - Form fields for the request body.
        json Any - Value to encode as a JSON request body.
        config DucoAPIRequestConfig | None - Optional overrides for this HTTP request.

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

        # Endpoint paths, query strings, bodies and headers can contain wallet data.
        verb = method.upper()
        safe_method = verb if verb in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"} else "OTHER"
        started = perf_counter()
        LOGGER.debug("HTTP request: %s timeout=%s redirects=%s", safe_method, timeout,
                     request_config.allow_redirects)
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
            LOGGER.debug("HTTP request failed: %s elapsed_ms=%.1f", type(exc).__name__,
                         (perf_counter() - started) * 1000)
            # Requests exceptions may retain credential-bearing URLs and request objects.
            response = None

        if response is None:
            raise DucoAPIRequestError("Request to the Duino-Coin API failed.")

        LOGGER.debug("HTTP response: status=%d elapsed_ms=%.1f", response.status_code,
                     (perf_counter() - started) * 1000)
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
        """
        *_raise_for_http_error Raise an HTTP error with any details returned by the server.*

        response Response - HTTP response returned by the session.
        endpoint str - API route associated with the request or response.
        """
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
        """
        *_decode_json Decode the body or include a short excerpt in the response error.*

        response Response - HTTP response returned by the session.
        endpoint str - API route associated with the request or response.
        """
        try:
            return response.json(parse_float=Decimal)
        except (ValueError, InvalidOperation) as exc:
            LOGGER.debug("HTTP response decoding failed: invalid JSON")
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
        """
        *_extract_server Read the server name from a JSON response when present.*

        response Response - HTTP response returned by the session.
        """
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
        """
        *close Close the Requests session.*
        """
        self._session.close()

    def __enter__(self) -> "DucoTransport":
        """
        *__enter__ Return the transport for use in a with block.*
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        """
        *__exit__ Close the session when the with block ends.*

        exc_type type[BaseException] | None - Exception type supplied by the context manager.
        exc_value BaseException | None - Exception raised inside the context, if any.
        traceback Any - Traceback supplied when leaving the context.
        """
        self.close()
