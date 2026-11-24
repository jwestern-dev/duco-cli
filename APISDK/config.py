#!/usr/bin/env python3
"""Configuration objects for the Duino-Coin API SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final
from urllib.parse import urlparse


DEFAULT_BASE_URL: Final[str] = "https://server.duinocoin.com"
DEFAULT_TIMEOUT: Final[float] = 10.0
DEFAULT_USER_AGENT: Final[str] = "ducoCLI/APISDK"


@dataclass(frozen=True, slots=True)
class DucoAPIConfig:
    """
    *DucoAPIConfig Base URL, default timeout in seconds and User-Agent for SDK requests.*

    base_url str - Root URL of the DUCO API.
    timeout float - HTTP request timeout in seconds.
    user_agent str - User-Agent header for SDK-created sessions.
    """

    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    user_agent: str = DEFAULT_USER_AGENT

    def __post_init__(self) -> None:
        """
        *__post_init__ Normalise the base URL and validate the client defaults.*
        """
        normalised_url = self.base_url.strip().rstrip("/")

        if not normalised_url:
            raise ValueError("base_url must not be empty")

        parsed = urlparse(normalised_url)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError("base_url must use the http or https scheme")

        if not parsed.netloc:
            raise ValueError("base_url must contain a valid host")

        if self.timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        if not self.user_agent.strip():
            raise ValueError("user_agent must not be empty")

        object.__setattr__(self, "base_url", normalised_url)
        object.__setattr__(self, "user_agent", self.user_agent.strip())

    def endpoint_url(self, endpoint: str) -> str:
        """
        *endpoint_url Join a relative endpoint to the base URL, preserving a trailing slash.*

        endpoint str - API route associated with the request or response.
        """
        endpoint = endpoint.strip().lstrip("/")

        if not endpoint:
            raise ValueError("endpoint must not be empty")

        if "://" in endpoint:
            raise ValueError("endpoint must be a relative path")

        return f"{self.base_url}/{endpoint}"

    def with_base_url(self, base_url: str) -> "DucoAPIConfig":
        """
        *with_base_url Copy the configuration with a different base URL.*

        base_url str - Root URL of the DUCO API.
        """
        return type(self)(
            base_url=base_url,
            timeout=self.timeout,
            user_agent=self.user_agent,
        )


@dataclass(frozen=True, slots=True)
class DucoAPIRequestConfig:
    """
    *DucoAPIRequestConfig Override the timeout, headers or redirect policy for one request.*

    timeout float | None - Maximum request wait in seconds.
    headers dict[str, str] - Extra HTTP headers for this request.
    allow_redirects bool - Whether the transport may follow HTTP redirects.

    A timeout of None uses the client's default. The default redirect
    policy follows redirects.
    """

    timeout: float | None = None
    headers: dict[str, str] = field(default_factory=dict)
    allow_redirects: bool = True

    def __post_init__(self) -> None:
        """
        *__post_init__ Check the timeout override and trim header names and values.*
        """
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        normalised_headers = {
            str(key).strip(): str(value).strip()
            for key, value in self.headers.items()
            if str(key).strip()
        }

        object.__setattr__(self, "headers", normalised_headers)
