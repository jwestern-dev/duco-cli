#!/usr/bin/env python3
"""Public client interface for the Duino-Coin REST API SDK."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .config import (
    DucoAPIConfig,
    DucoAPIRequestConfig,
)
from .models import (
    APIResponse,
    DUCOAmount,
    Miner,
    MiningKeyStatus,
    Pool,
    ShopItem,
    Statistics,
    Transaction,
    User,
    UserBalance,
    UserV3,
)
from .parsers import (
    parse_balance,
    parse_balances,
    parse_mining_key_status,
    parse_miners,
    parse_pools,
    parse_shop_items,
    parse_statistics,
    parse_transaction_response,
    parse_transactions,
    parse_user,
    parse_user_miners,
    parse_user_transactions,
    parse_user_v3,
)
from .transport import DucoTransport


class DucoAPI:
    """Typed client for the Duino-Coin REST API.

    Pass a transport to reuse a session or to test against canned responses.
    Client methods raise DucoAPIValidationError for invalid arguments and
    DucoAPIError subclasses for network failures or rejected responses.
    """

    def __init__(
        self,
        config: DucoAPIConfig | None = None,
        transport: DucoTransport | None = None,
    ) -> None:
        """Create a client, using config only when building a new transport."""
        if transport is not None:
            self._transport = transport
            return

        self._transport = DucoTransport(
            config=config,
        )

    @property
    def config(self) -> DucoAPIConfig:
        """Return the transport's configuration."""
        return self._transport.config

    @property
    def transport(self) -> DucoTransport:
        """Return the transport used by this client."""
        return self._transport

    # User endpoints

    def get_user(
        self,
        username: str,
    ) -> User:
        """Fetch the balance, miners and recent transactions from /users/<username>."""
        username = self._validate_username(username)

        endpoint = f"users/{username}"
        payload = self._transport.request("GET", endpoint)

        return parse_user(payload, endpoint=endpoint)

    def get_user_v3(
        self,
        username: str,
    ) -> UserV3:
        """Fetch the v3 user profile, including rates, achievements and shop items."""
        username = self._validate_username(username)

        endpoint = f"v3/users/{username}"
        payload = self._transport.request("GET", endpoint)

        return parse_user_v3(payload, endpoint=endpoint)

    # Balance endpoints

    def get_balances(self) -> dict[str, DUCOAmount]:
        """Fetch current DUCO balances keyed by username."""
        endpoint = "balances"

        payload = self._transport.request("GET", endpoint)

        return parse_balances(payload, endpoint=endpoint)

    def get_balance(
        self,
        username: str,
    ) -> UserBalance:
        """Fetch one user's balance, stake and account details."""
        username = self._validate_username(username)

        endpoint = f"balances/{username}"
        payload = self._transport.request("GET", endpoint)

        return parse_balance(payload, endpoint=endpoint)

    # Miner endpoints

    def get_miners(self) -> dict[str, list[Miner]]:
        """Fetch active miners grouped by username."""
        endpoint = "miners"

        payload = self._transport.request("GET", endpoint)

        return parse_miners(payload, endpoint=endpoint)

    def get_user_miners(
        self,
        username: str,
    ) -> list[Miner]:
        """Fetch the active miners listed by /miners/<username>."""
        username = self._validate_username(username)

        endpoint = f"miners/{username}"
        payload = self._transport.request("GET", endpoint)

        response = self._require_success_payload(
            payload,
            endpoint=endpoint,
        )

        result = response.result

        if not isinstance(result, list):
            from .errors import DucoAPIResponseError

            raise DucoAPIResponseError(
                "Expected miners result to be an array",
                endpoint=endpoint,
                response=payload,
            )

        from .parsers import parse_miner_list

        return parse_miner_list(result, endpoint=endpoint)

    # Transaction endpoints

    def get_transactions(self) -> dict[str, Transaction]:
        """Fetch recent network transactions keyed by hash."""
        endpoint = "transactions"

        payload = self._transport.request("GET", endpoint)

        return parse_transactions(payload, endpoint=endpoint)

    def get_transaction(
        self,
        transaction_hash: str,
    ) -> Transaction:
        """Look up a transaction by hash through /transactions/<hash>."""
        transaction_hash = self._validate_identifier(
            transaction_hash,
            name="transaction_hash",
        )

        endpoint = f"transactions/{transaction_hash}"
        payload = self._transport.request("GET", endpoint)

        response = self._require_success_payload(
            payload,
            endpoint=endpoint,
        )

        from .parsers import parse_transaction

        return parse_transaction(response.result, endpoint=endpoint)

    def get_transaction_by_id(
        self,
        transaction_id: int,
    ) -> Transaction:
        """Look up a transaction by its positive numeric ID."""
        transaction_id = self._validate_positive_int(
            transaction_id,
            name="transaction_id",
        )

        endpoint = f"id_transactions/{transaction_id}"
        payload = self._transport.request("GET", endpoint)

        response = self._require_success_payload(
            payload,
            endpoint=endpoint,
        )

        from .parsers import parse_transaction

        return parse_transaction(response.result, endpoint=endpoint)

    def get_user_transactions(
        self,
        username: str,
        *,
        limit: int = 10,
    ) -> list[Transaction]:
        """Fetch up to limit recent transactions for a user."""
        username = self._validate_username(username)
        limit = self._validate_positive_int(
            limit,
            name="limit",
        )

        endpoint = f"user_transactions/{username}"
        payload = self._transport.request(
            "GET",
            endpoint,
            params={"limit": limit},
        )

        response = self._require_success_payload(
            payload,
            endpoint=endpoint,
        )

        from .parsers import parse_transaction_list

        return parse_transaction_list(response.result, endpoint=endpoint)

    # Pool endpoint

    def get_pools(self) -> list[Pool]:
        """Fetch the visible mining pools from /all_pools."""
        endpoint = "all_pools"

        payload = self._transport.request("GET", endpoint)

        return parse_pools(payload, endpoint=endpoint)

    # Shop endpoint

    def get_shop_items(self) -> list[ShopItem]:
        """Fetch the current shop catalogue."""
        endpoint = "shop_items"

        payload = self._transport.request("GET", endpoint)

        return parse_shop_items(payload, endpoint=endpoint)

    # Mining-key endpoint

    def check_mining_key(
        self,
        username: str,
        mining_key: str,
    ) -> MiningKeyStatus:
        """Check whether a user has a configured mining key."""
        username = self._validate_username(username)
        mining_key = self._validate_identifier(
            mining_key,
            name="mining_key",
        )

        endpoint = "mining_key"
        payload = self._transport.request(
            "GET",
            endpoint,
            params={
                "u": username,
                "k": mining_key,
            },
        )

        return parse_mining_key_status(payload, endpoint=endpoint)

    # Statistics endpoint

    def get_statistics(self) -> Statistics:
        """Fetch network statistics, prices and miner counts from /statistics."""
        endpoint = "statistics"

        payload = self._transport.request("GET", endpoint)

        return parse_statistics(payload, endpoint=endpoint)

    # Request-level API

    def request_raw(
        self,
        method: str,
        endpoint: str,
        *,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        json: Any = None,
        config: DucoAPIRequestConfig | None = None,
    ) -> Any:
        """Send a request and return the decoded JSON.

        Use params for query parameters, data for a form, and json for a JSON
        body. A request config can override the timeout, headers and redirects.
        Callers are responsible for checking the API's success field.
        """
        return self._transport.request(
            method,
            endpoint,
            params=params,
            data=data,
            json=json,
            config=config,
        )

    # Lifecycle

    def close(self) -> None:
        """Close the transport and its HTTP session."""
        self._transport.close()

    def __enter__(self) -> "DucoAPI":
        """Return the client for use in a with block."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        """Close the client when the with block ends."""
        self.close()

    # Validation helpers

    @staticmethod
    def _validate_username(username: str) -> str:
        """Strip surrounding whitespace and reject empty names or path separators."""
        from .errors import DucoAPIValidationError

        if not isinstance(username, str):
            raise DucoAPIValidationError(
                "username must be a string",
            )

        username = username.strip()

        if not username:
            raise DucoAPIValidationError(
                "username must not be empty",
            )

        if "/" in username or "\\" in username:
            raise DucoAPIValidationError(
                "username must not contain path separators",
            )

        return username

    @staticmethod
    def _validate_identifier(
        value: str,
        *,
        name: str,
    ) -> str:
        """Strip surrounding whitespace from a non-empty string identifier."""
        from .errors import DucoAPIValidationError

        if not isinstance(value, str):
            raise DucoAPIValidationError(
                f"{name} must be a string",
            )

        value = value.strip()

        if not value:
            raise DucoAPIValidationError(
                f"{name} must not be empty",
            )

        return value

    @staticmethod
    def _validate_positive_int(
        value: int,
        *,
        name: str,
    ) -> int:
        """Require an integer greater than zero. Booleans are invalid."""
        from .errors import DucoAPIValidationError

        if isinstance(value, bool) or not isinstance(value, int):
            raise DucoAPIValidationError(
                f"{name} must be an integer",
            )

        if value <= 0:
            raise DucoAPIValidationError(
                f"{name} must be greater than zero",
            )

        return value

    @staticmethod
    def _require_success_payload(
        payload: Any,
        *,
        endpoint: str,
    ) -> APIResponse:
        """Unwrap the response or raise the server's reported failure."""
        from .parsers import require_success

        return require_success(
            payload,
            endpoint=endpoint,
        )
