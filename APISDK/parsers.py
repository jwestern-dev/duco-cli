#!/usr/bin/env python3
"""Validate Duino-Coin responses and convert them to SDK models."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any, TypeVar

from .errors import DucoAPIResponseError
from .models import (
    APIResponse,
    APIResponseMetadata,
    ExchangeRate,
    ExchangeRates,
    GratkaStatistics,
    KolkaStatistics,
    Miner,
    MinerDistribution,
    MiningKeyStatus,
    Pool,
    ShopItem,
    Statistics,
    Transaction,
    User,
    UserBalance,
    UserV3,
)


T = TypeVar("T")


# Generic validation helpers


def _error(
    message: str,
    *,
    endpoint: str | None = None,
    response: Any = None,
) -> DucoAPIResponseError:
    """
    *_error Attach the endpoint and offending value to a parser error.*

    message str - Message for the caller.
    endpoint str | None - API route associated with the request or response.
    response Any - Response that supplied the error details.
    """
    return DucoAPIResponseError(
        message,
        endpoint=endpoint,
        response=response,
    )


def _require_mapping(
    value: Any,
    *,
    name: str,
    endpoint: str | None = None,
) -> Mapping[str, Any]:
    """
    *_require_mapping Accept a JSON object or raise a response error.*

    value Any - Value to validate or convert.
    name str - Field or argument name used in validation errors.
    endpoint str | None - API route associated with the request or response.
    """
    if not isinstance(value, Mapping):
        raise _error(
            f"Expected {name} to be an object, got "
            f"{type(value).__name__}",
            endpoint=endpoint,
            response=value,
        )

    return value


def _require_list(
    value: Any,
    *,
    name: str,
    endpoint: str | None = None,
) -> list[Any]:
    """
    *_require_list Accept a JSON array or raise a response error.*

    value Any - Value to validate or convert.
    name str - Field or argument name used in validation errors.
    endpoint str | None - API route associated with the request or response.
    """
    if not isinstance(value, list):
        raise _error(
            f"Expected {name} to be an array, got "
            f"{type(value).__name__}",
            endpoint=endpoint,
            response=value,
        )

    return value


def _require_string(
    value: Any,
    *,
    name: str,
    endpoint: str | None = None,
) -> str:
    """
    *_require_string Accept a string or raise a response error.*

    value Any - Value to validate or convert.
    name str - Field or argument name used in validation errors.
    endpoint str | None - API route associated with the request or response.
    """
    if not isinstance(value, str):
        raise _error(
            f"Expected {name} to be a string, got "
            f"{type(value).__name__}",
            endpoint=endpoint,
            response=value,
        )

    return value


def _require_int(
    value: Any,
    *,
    name: str,
    endpoint: str | None = None,
) -> int:
    """
    *_require_int Accept an integer. Reject booleans even though Python treats them as ints.*

    value Any - Value to validate or convert.
    name str - Field or argument name used in validation errors.
    endpoint str | None - API route associated with the request or response.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(
            f"Expected {name} to be an integer, got "
            f"{type(value).__name__}",
            endpoint=endpoint,
            response=value,
        )

    return value


def _require_float(
    value: Any,
    *,
    name: str,
    endpoint: str | None = None,
) -> float:
    """
    *_require_float Read a finite numeric field as a float, rejecting booleans.*

    value Any - Value to validate or convert.
    name str - Field or argument name used in validation errors.
    endpoint str | None - API route associated with the request or response.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise _error(
            f"Expected {name} to be numeric, got "
            f"{type(value).__name__}",
            endpoint=endpoint,
            response=value,
        )

    number = float(value)
    if not isfinite(number):
        raise _error(f"Expected a finite number for {name}", endpoint=endpoint)
    return number


def _require_bool(
    value: Any,
    *,
    name: str,
    endpoint: str | None = None,
) -> bool:
    """
    *_require_bool Require a boolean field without coercing truthy values.*

    value Any - Value to validate or convert.
    name str - Field or argument name used in validation errors.
    endpoint str | None - API route associated with the request or response.
    """
    if not isinstance(value, bool):
        raise _error(
            f"Expected {name} to be a boolean, got "
            f"{type(value).__name__}",
            endpoint=endpoint,
            response=value,
        )

    return value


def _require_field(
    mapping: Mapping[str, Any],
    key: str,
    *,
    endpoint: str | None = None,
) -> Any:
    """
    *_require_field Read a required key and name it in the error if missing.*

    mapping Mapping[str, Any] - Object containing the required field.
    key str - Field name to look up.
    endpoint str | None - API route associated with the request or response.
    """
    if key not in mapping:
        raise _error(
            f"Required response field {key!r} is missing",
            endpoint=endpoint,
            response=mapping,
        )

    return mapping[key]


def _to_decimal(
    value: Any,
    *,
    name: str,
    endpoint: str | None = None,
) -> Decimal:
    """
    *_to_decimal Read a monetary or numeric field as a Decimal.*

    value Any - Value to validate or convert.
    name str - Field or argument name used in validation errors.
    endpoint str | None - API route associated with the request or response.

    Convert through text to avoid carrying float representation noise into
    the Decimal.
    """
    if isinstance(value, bool):
        raise _error(
            f"Expected {name} to be numeric, got boolean",
            endpoint=endpoint,
            response=value,
        )

    if not isinstance(value, (int, float, str, Decimal)):
        raise _error(
            f"Expected {name} to be numeric, got "
            f"{type(value).__name__}",
            endpoint=endpoint,
            response=value,
        )

    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise _error(
            f"Invalid numeric value for {name}: {value!r}",
            endpoint=endpoint,
            response=value,
        ) from exc
    if not number.is_finite():
        raise _error(f"Expected a finite number for {name}", endpoint=endpoint)
    return number


# Common API envelope


def parse_response_metadata(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> APIResponseMetadata:
    """
    *parse_response_metadata Read success, server and message from a response envelope.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.

    Error responses can omit the result field.
    """
    mapping = _require_mapping(
        payload,
        name="API response",
        endpoint=endpoint,
    )

    success = _require_bool(
        _require_field(mapping, "success", endpoint=endpoint),
        name="success",
        endpoint=endpoint,
    )

    server_value = mapping.get("server")

    if server_value is not None and not isinstance(server_value, str):
        raise _error(
            "Expected server to be a string or null",
            endpoint=endpoint,
            response=payload,
        )

    message_value = mapping.get("message")

    if message_value is not None and not isinstance(message_value, str):
        raise _error(
            "Expected message to be a string or null",
            endpoint=endpoint,
            response=payload,
        )

    return APIResponseMetadata(
        success=success,
        server=server_value,
        message=message_value,
    )


def parse_api_response(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> APIResponse:
    """
    *parse_api_response Read the common envelope and leave result in its original JSON shape.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    mapping = _require_mapping(
        payload,
        name="API response",
        endpoint=endpoint,
    )

    metadata = parse_response_metadata(
        mapping,
        endpoint=endpoint,
    )

    return APIResponse(
        metadata=metadata,
        result=mapping.get("result"),
    )


def require_success(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> APIResponse:
    """
    *require_success Read a successful API envelope or raise DucoAPIOperationError.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    from .errors import DucoAPIOperationError

    response = parse_api_response(
        payload,
        endpoint=endpoint,
    )

    if response.metadata.success:
        return response

    message = response.metadata.message or "Duino-Coin API operation failed"

    raise DucoAPIOperationError(
        message,
        endpoint=endpoint,
        server=response.metadata.server,
        response=payload,
    )


# User / account parsing


def parse_user_balance(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> UserBalance:
    """
    *parse_user_balance Parse the balance object shared by the balance and user endpoints.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    mapping = _require_mapping(
        payload,
        name="balance",
        endpoint=endpoint,
    )

    return UserBalance(
        balance=_to_decimal(
            _require_field(mapping, "balance", endpoint=endpoint),
            name="balance",
            endpoint=endpoint,
        ),
        created=_require_string(
            _require_field(mapping, "created", endpoint=endpoint),
            name="created",
            endpoint=endpoint,
        ),
        last_login=_require_int(
            _require_field(mapping, "last_login", endpoint=endpoint),
            name="last_login",
            endpoint=endpoint,
        ),
        max_miners=_require_int(
            _require_field(mapping, "max_miners", endpoint=endpoint),
            name="max_miners",
            endpoint=endpoint,
        ),
        stake_amount=_to_decimal(
            _require_field(mapping, "stake_amount", endpoint=endpoint),
            name="stake_amount",
            endpoint=endpoint,
        ),
        stake_date=_require_int(
            _require_field(mapping, "stake_date", endpoint=endpoint),
            name="stake_date",
            endpoint=endpoint,
        ),
        trust_score=_require_int(
            _require_field(mapping, "trust_score", endpoint=endpoint),
            name="trust_score",
            endpoint=endpoint,
        ),
        username=_require_string(
            _require_field(mapping, "username", endpoint=endpoint),
            name="username",
            endpoint=endpoint,
        ),
        verified=_require_string(
            _require_field(mapping, "verified", endpoint=endpoint),
            name="verified",
            endpoint=endpoint,
        ),
        verified_by=_require_string(
            _require_field(mapping, "verified_by", endpoint=endpoint),
            name="verified_by",
            endpoint=endpoint,
        ),
        verified_date=_require_int(
            _require_field(mapping, "verified_date", endpoint=endpoint),
            name="verified_date",
            endpoint=endpoint,
        ),
        warnings=_require_int(
            _require_field(mapping, "warnings", endpoint=endpoint),
            name="warnings",
            endpoint=endpoint,
        ),
    )


def parse_user(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> User:
    """
    *parse_user Unpack the profile from /users/<username>.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    response = require_success(
        payload,
        endpoint=endpoint,
    )

    result = _require_mapping(
        response.result,
        name="user result",
        endpoint=endpoint,
    )

    balance = parse_user_balance(
        _require_field(result, "balance", endpoint=endpoint),
        endpoint=endpoint,
    )

    miners = parse_miner_list(
        _require_field(result, "miners", endpoint=endpoint),
        endpoint=endpoint,
    )

    transactions = parse_transaction_list(
        _require_field(result, "transactions", endpoint=endpoint),
        endpoint=endpoint,
    )

    return User(
        balance=balance,
        miners=tuple(miners),
        transactions=tuple(transactions),
    )


def parse_user_v3(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> UserV3:
    """
    *parse_user_v3 Unpack the profile from /v3/users/<username>.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    response = require_success(
        payload,
        endpoint=endpoint,
    )

    result = _require_mapping(
        response.result,
        name="v3 user result",
        endpoint=endpoint,
    )

    achievements_raw = _require_list(
        _require_field(result, "achievements", endpoint=endpoint),
        name="achievements",
        endpoint=endpoint,
    )

    achievements = tuple(
        _require_int(
            value,
            name="achievement",
            endpoint=endpoint,
        )
        for value in achievements_raw
    )

    balance = parse_user_balance(
        _require_field(result, "balance", endpoint=endpoint),
        endpoint=endpoint,
    )

    exchange_rates = parse_exchange_rates(
        _require_field(result, "exch_rates", endpoint=endpoint),
        endpoint=endpoint,
    )

    items = _require_list(
        _require_field(result, "items", endpoint=endpoint),
        name="items",
        endpoint=endpoint,
    )

    miners = parse_miner_list(
        _require_field(result, "miners", endpoint=endpoint),
        endpoint=endpoint,
    )

    notices = _require_list(
        _require_field(result, "notices", endpoint=endpoint),
        name="notices",
        endpoint=endpoint,
    )

    transactions = parse_transaction_list(
        _require_field(result, "transactions", endpoint=endpoint),
        endpoint=endpoint,
    )

    return UserV3(
        achievements=achievements,
        balance=balance,
        exchange_rates=exchange_rates,
        items=tuple(items),
        miners=tuple(miners),
        notices=tuple(notices),
        transactions=tuple(transactions),
    )


# Exchange-rate parsing


def parse_exchange_rate(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> ExchangeRate:
    """
    *parse_exchange_rate Read an exchange price and its change fields.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    mapping = _require_mapping(
        payload,
        name="exchange rate",
        endpoint=endpoint,
    )

    return ExchangeRate(
        change_24h=_to_decimal(
            _require_field(mapping, "change_24h", endpoint=endpoint),
            name="change_24h",
            endpoint=endpoint,
        ),
        change_7d=_to_decimal(
            _require_field(mapping, "change_7d", endpoint=endpoint),
            name="change_7d",
            endpoint=endpoint,
        ),
        price=_to_decimal(
            _require_field(mapping, "price", endpoint=endpoint),
            name="price",
            endpoint=endpoint,
        ),
    )


def parse_exchange_rates(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> ExchangeRates:
    """
    *parse_exchange_rates Read rates from exch_rates. Older responses can omit Bitstorage.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    mapping = _require_mapping(
        payload,
        name="exchange rates",
        endpoint=endpoint,
    )

    def rate(name: str) -> ExchangeRate:
        """
        *rate Read a required exchange rate by name.*

        name str - Field or argument name used in validation errors.
        """
        return parse_exchange_rate(
            _require_field(mapping, name, endpoint=endpoint),
            endpoint=endpoint,
        )

    return ExchangeRates(
        bch=rate("bch"),
        bitstorage=rate("bitstorage") if "bitstorage" in mapping else None,
        fluffy=rate("fluffy"),
        furim=rate("furim"),
        max=rate("max"),
        nano=rate("nano"),
        nodes=rate("nodes"),
        pancake=rate("pancake"),
        sunswap=rate("sunswap"),
        sushi=rate("sushi"),
        trx=rate("trx"),
        ubeswap=rate("ubeswap"),
        xmg=rate("xmg"),
    )


# Transaction parsing


def parse_transaction(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> Transaction:
    """
    *parse_transaction Read one ledger entry from an API object.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    mapping = _require_mapping(
        payload,
        name="transaction",
        endpoint=endpoint,
    )

    return Transaction(
        amount=_to_decimal(
            _require_field(mapping, "amount", endpoint=endpoint),
            name="amount",
            endpoint=endpoint,
        ),
        datetime=_require_string(
            _require_field(mapping, "datetime", endpoint=endpoint),
            name="datetime",
            endpoint=endpoint,
        ),
        hash=_require_string(
            _require_field(mapping, "hash", endpoint=endpoint),
            name="hash",
            endpoint=endpoint,
        ),
        id=_require_int(
            _require_field(mapping, "id", endpoint=endpoint),
            name="id",
            endpoint=endpoint,
        ),
        memo=_require_string(
            _require_field(mapping, "memo", endpoint=endpoint),
            name="memo",
            endpoint=endpoint,
        ),
        recipient=_require_string(
            _require_field(mapping, "recipient", endpoint=endpoint),
            name="recipient",
            endpoint=endpoint,
        ),
        sender=_require_string(
            _require_field(mapping, "sender", endpoint=endpoint),
            name="sender",
            endpoint=endpoint,
        ),
    )


def parse_transaction_list(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> list[Transaction]:
    """
    *parse_transaction_list Read an array of ledger entries in the order returned by the API.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    values = _require_list(
        payload,
        name="transactions",
        endpoint=endpoint,
    )

    return [
        parse_transaction(
            transaction,
            endpoint=endpoint,
        )
        for transaction in values
    ]


def parse_transactions(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> dict[str, Transaction]:
    """
    *parse_transactions Read the /transactions response, whose keys are transaction hashes.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    response = require_success(
        payload,
        endpoint=endpoint,
    )

    result = _require_mapping(
        response.result,
        name="transactions result",
        endpoint=endpoint,
    )

    transactions: dict[str, Transaction] = {}

    for key, value in result.items():
        transaction_hash = _require_string(
            key,
            name="transaction hash",
            endpoint=endpoint,
        )

        transaction = parse_transaction(
            value,
            endpoint=endpoint,
        )

        transactions[transaction_hash] = transaction

    return transactions


# Miner parsing


def parse_miner(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> Miner:
    """
    *parse_miner Read one active worker, including its share counts and hashrate.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    mapping = _require_mapping(
        payload,
        name="miner",
        endpoint=endpoint,
    )

    it_value = _require_field(
        mapping,
        "it",
        endpoint=endpoint,
    )

    if it_value is not None and not isinstance(it_value, str):
        raise _error(
            "Expected miner.it to be a string or null",
            endpoint=endpoint,
            response=payload,
        )

    wd_value = _require_field(
        mapping,
        "wd",
        endpoint=endpoint,
    )

    if wd_value is not None and not isinstance(wd_value, str):
        raise _error(
            "Expected miner.wd to be a string or null",
            endpoint=endpoint,
            response=payload,
        )

    return Miner(
        accepted=_require_int(
            _require_field(mapping, "accepted", endpoint=endpoint),
            name="accepted",
            endpoint=endpoint,
        ),
        algorithm=_require_string(
            _require_field(mapping, "algorithm", endpoint=endpoint),
            name="algorithm",
            endpoint=endpoint,
        ),
        diff=_require_int(
            _require_field(mapping, "diff", endpoint=endpoint),
            name="diff",
            endpoint=endpoint,
        ),
        hashrate=_require_float(
            _require_field(mapping, "hashrate", endpoint=endpoint),
            name="hashrate",
            endpoint=endpoint,
        ),
        identifier=_require_string(
            _require_field(mapping, "identifier", endpoint=endpoint),
            name="identifier",
            endpoint=endpoint,
        ),
        it=it_value,
        ki=_require_int(
            _require_field(mapping, "ki", endpoint=endpoint),
            name="ki",
            endpoint=endpoint,
        ),
        pg=_require_int(
            _require_field(mapping, "pg", endpoint=endpoint),
            name="pg",
            endpoint=endpoint,
        ),
        pool=_require_string(
            _require_field(mapping, "pool", endpoint=endpoint),
            name="pool",
            endpoint=endpoint,
        ),
        rejected=_require_int(
            _require_field(mapping, "rejected", endpoint=endpoint),
            name="rejected",
            endpoint=endpoint,
        ),
        sharerate=_require_int(
            _require_field(mapping, "sharerate", endpoint=endpoint),
            name="sharerate",
            endpoint=endpoint,
        ),
        sharetime=_require_float(
            _require_field(mapping, "sharetime", endpoint=endpoint),
            name="sharetime",
            endpoint=endpoint,
        ),
        software=_require_string(
            _require_field(mapping, "software", endpoint=endpoint),
            name="software",
            endpoint=endpoint,
        ),
        threadid=_require_string(
            _require_field(mapping, "threadid", endpoint=endpoint),
            name="threadid",
            endpoint=endpoint,
        ),
        username=_require_string(
            _require_field(mapping, "username", endpoint=endpoint),
            name="username",
            endpoint=endpoint,
        ),
        wd=wd_value,
    )


def parse_miner_list(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> list[Miner]:
    """
    *parse_miner_list Read the miners array for an account.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    values = _require_list(
        payload,
        name="miners",
        endpoint=endpoint,
    )

    return [
        parse_miner(
            miner,
            endpoint=endpoint,
        )
        for miner in values
    ]


def parse_miners(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> dict[str, list[Miner]]:
    """
    *parse_miners Read the /miners response, grouped by username.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    response = require_success(
        payload,
        endpoint=endpoint,
    )

    result = _require_mapping(
        response.result,
        name="miners result",
        endpoint=endpoint,
    )

    miners: dict[str, list[Miner]] = {}

    for username, value in result.items():
        username_key = _require_string(
            username,
            name="miner username",
            endpoint=endpoint,
        )

        miners[username_key] = parse_miner_list(
            value,
            endpoint=endpoint,
        )

    return miners


# Pool parsing


def parse_pool(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> Pool:
    """
    *parse_pool Read one mining pool, including its optional region.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    mapping = _require_mapping(
        payload,
        name="pool",
        endpoint=endpoint,
    )

    region = mapping.get("region")

    if region is not None and not isinstance(region, str):
        raise _error(
            "Expected pool.region to be a string or null",
            endpoint=endpoint,
            response=payload,
        )

    return Pool(
        connections=_require_int(
            _require_field(mapping, "connections", endpoint=endpoint),
            name="connections",
            endpoint=endpoint,
        ),
        cpu=_require_int(
            _require_field(mapping, "cpu", endpoint=endpoint),
            name="cpu",
            endpoint=endpoint,
        ),
        icon=_require_string(
            _require_field(mapping, "icon", endpoint=endpoint),
            name="icon",
            endpoint=endpoint,
        ),
        last_sync=_require_string(
            _require_field(mapping, "lastsync", endpoint=endpoint),
            name="lastsync",
            endpoint=endpoint,
        ),
        name=_require_string(
            _require_field(mapping, "name", endpoint=endpoint),
            name="name",
            endpoint=endpoint,
        ),
        ram=_require_int(
            _require_field(mapping, "ram", endpoint=endpoint),
            name="ram",
            endpoint=endpoint,
        ),
        region=region,
        type=_require_string(
            _require_field(mapping, "type", endpoint=endpoint),
            name="type",
            endpoint=endpoint,
        ),
    )


def parse_pools(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> list[Pool]:
    """
    *parse_pools Read the pool list returned by /all_pools.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    response = require_success(
        payload,
        endpoint=endpoint,
    )

    values = _require_list(
        response.result,
        name="pools result",
        endpoint=endpoint,
    )

    return [
        parse_pool(
            pool,
            endpoint=endpoint,
        )
        for pool in values
    ]


# Shop parsing


def parse_shop_item(
    item_id: str,
    payload: Any,
    *,
    endpoint: str | None = None,
) -> ShopItem:
    """
    *parse_shop_item Read one catalogue item, using its mapping key as the item ID.*

    item_id str - Catalogue identifier for the item.
    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    mapping = _require_mapping(
        payload,
        name=f"shop item {item_id}",
        endpoint=endpoint,
    )

    try:
        numeric_id = int(item_id)
    except ValueError as exc:
        raise _error(
            f"Shop item ID is not numeric: {item_id!r}",
            endpoint=endpoint,
            response=payload,
        ) from exc

    category_value = mapping.get("category")

    if category_value is None:
        category: tuple[str, ...] | None = None
    else:
        category_values = _require_list(
            category_value,
            name=f"shop item {item_id} category",
            endpoint=endpoint,
        )

        category = tuple(
            _require_string(
                value,
                name=f"shop item {item_id} category entry",
                endpoint=endpoint,
            )
            for value in category_values
        )

    return ShopItem(
        item_id=numeric_id,
        description=_require_string(
            _require_field(mapping, "description", endpoint=endpoint),
            name="description",
            endpoint=endpoint,
        ),
        display=_require_bool(
            _require_field(mapping, "display", endpoint=endpoint),
            name="display",
            endpoint=endpoint,
        ),
        icon=_require_string(
            _require_field(mapping, "icon", endpoint=endpoint),
            name="icon",
            endpoint=endpoint,
        ),
        name=_require_string(
            _require_field(mapping, "name", endpoint=endpoint),
            name="name",
            endpoint=endpoint,
        ),
        price=_to_decimal(
            _require_field(mapping, "price", endpoint=endpoint),
            name="price",
            endpoint=endpoint,
        ),
        category=category,
    )


def parse_shop_items(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> list[ShopItem]:
    """
    *parse_shop_items Read items from a mapping keyed by numeric IDs stored as strings.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    response = require_success(
        payload,
        endpoint=endpoint,
    )

    result = _require_mapping(
        response.result,
        name="shop items result",
        endpoint=endpoint,
    )

    items: list[ShopItem] = []

    for item_id, value in result.items():
        item_id_string = _require_string(
            item_id,
            name="shop item ID",
            endpoint=endpoint,
        )

        items.append(
            parse_shop_item(
                item_id_string,
                value,
                endpoint=endpoint,
            )
        )

    items.sort(key=lambda item: item.item_id)

    return items


# Balance parsing


def parse_balance(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> UserBalance:
    """
    *parse_balance Unpack the /balances/<username> response.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    response = require_success(
        payload,
        endpoint=endpoint,
    )

    return parse_user_balance(
        response.result,
        endpoint=endpoint,
    )


def parse_balances(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> dict[str, Decimal]:
    """
    *parse_balances Read the balances returned by /balances, keyed by username.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    response = require_success(
        payload,
        endpoint=endpoint,
    )

    result = _require_mapping(
        response.result,
        name="balances result",
        endpoint=endpoint,
    )

    balances: dict[str, Decimal] = {}

    for username, balance in result.items():
        username_key = _require_string(
            username,
            name="balance username",
            endpoint=endpoint,
        )

        balances[username_key] = _to_decimal(
            balance,
            name=f"balance for {username_key}",
            endpoint=endpoint,
        )

    return balances


# Mining-key parsing


def parse_mining_key_status(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> MiningKeyStatus:
    """
    *parse_mining_key_status Read has_key from the envelope itself. The API puts it beside success.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    response = require_success(
        payload,
        endpoint=endpoint,
    )

    raw = _require_mapping(
        payload,
        name="mining key response",
        endpoint=endpoint,
    )

    has_key = _require_bool(
        _require_field(raw, "has_key", endpoint=endpoint),
        name="has_key",
        endpoint=endpoint,
    )

    # Only the envelope needs validation here. has_key lives at the root.
    _ = response

    return MiningKeyStatus(
        has_key=has_key,
    )


# Statistics parsing


def parse_gratka_statistics(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> GratkaStatistics:
    """
    *parse_gratka_statistics Read the Gratka counters from network statistics.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    mapping = _require_mapping(
        payload,
        name="Gratka statistics",
        endpoint=endpoint,
    )

    return GratkaStatistics(
        active=_require_int(
            _require_field(mapping, "active", endpoint=endpoint),
            name="Gratka.active",
            endpoint=endpoint,
        ),
        bought_items=_require_int(
            _require_field(mapping, "bought_items", endpoint=endpoint),
            name="Gratka.bought_items",
            endpoint=endpoint,
        ),
        cached_ips=_require_int(
            _require_field(mapping, "cached_ips", endpoint=endpoint),
            name="Gratka.cached_ips",
            endpoint=endpoint,
        ),
    )


def parse_kolka_statistics(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> KolkaStatistics:
    """
    *parse_kolka_statistics Read the Kolka counters from network statistics.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    mapping = _require_mapping(
        payload,
        name="Kolka statistics",
        endpoint=endpoint,
    )

    return KolkaStatistics(
        banned=_require_int(
            _require_field(mapping, "Banned", endpoint=endpoint),
            name="Kolka.Banned",
            endpoint=endpoint,
        ),
        jailed=_require_int(
            _require_field(mapping, "Jailed", endpoint=endpoint),
            name="Kolka.Jailed",
            endpoint=endpoint,
        ),
    )


def parse_miner_distribution(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> MinerDistribution:
    """
    *parse_miner_distribution Read the miner counts by platform.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    mapping = _require_mapping(
        payload,
        name="miner distribution",
        endpoint=endpoint,
    )

    def integer(key: str) -> int:
        """
        *integer Read one required miner count.*

        key str - Field name to look up.
        """
        return _require_int(
            _require_field(mapping, key, endpoint=endpoint),
            name=f"Miner distribution.{key}",
            endpoint=endpoint,
        )

    return MinerDistribution(
        all=integer("All"),
        arduino=integer("Arduino"),
        cpu=integer("CPU"),
        esp32=integer("ESP32"),
        esp8266=integer("ESP8266"),
        gpu=integer("GPU"),
        other=integer("Other"),
        phone=integer("Phone"),
        rpi=integer("RPi"),
        web=integer("Web"),
    )


def parse_statistics(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> Statistics:
    """
    *parse_statistics Read /statistics directly from the response body.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.

    This endpoint returns the statistics fields at the root, with no
    success or result wrapper.
    """
    mapping = _require_mapping(
        payload,
        name="statistics response",
        endpoint=endpoint,
    )

    def string(key: str) -> str:
        """
        *string Read a required text field from the statistics payload.*

        key str - Field name to look up.
        """
        return _require_string(
            _require_field(mapping, key, endpoint=endpoint),
            name=key,
            endpoint=endpoint,
        )

    def integer(key: str) -> int:
        """
        *integer Read a required integer from the statistics payload.*

        key str - Field name to look up.
        """
        return _require_int(
            _require_field(mapping, key, endpoint=endpoint),
            name=key,
            endpoint=endpoint,
        )

    def numeric(key: str) -> Decimal:
        """
        *numeric Read a required numeric field as a Decimal.*

        key str - Field name to look up.
        """
        return _to_decimal(
            _require_field(mapping, key, endpoint=endpoint),
            name=key,
            endpoint=endpoint,
        )

    xxhash_hashrate = _require_field(mapping, "XXHASH hashrate", endpoint=endpoint)
    if isinstance(xxhash_hashrate, Decimal):
        xxhash_hashrate = _require_float(xxhash_hashrate, name="XXHASH hashrate", endpoint=endpoint)
    if isinstance(xxhash_hashrate, bool) or not isinstance(
        xxhash_hashrate, (str, int, float)
    ):
        raise _error(
            "Expected XXHASH hashrate to be a string or number",
            endpoint=endpoint,
            response=xxhash_hashrate,
        )

    return Statistics(
        active_connections=integer("Active connections"),
        all_time_mined_duco=numeric("All-time mined DUCO"),
        current_difficulty=integer("Current difficulty"),
        duco_s1_hashrate=string("DUCO-S1 hashrate"),
        duco_bitstorage_price=(
            numeric("Duco Bitstorage price")
            if "Duco Bitstorage price" in mapping else None
        ),
        duco_fluffyswap_price=numeric("Duco FluffySwap price"),
        duco_furim_price=numeric("Duco Furim price"),
        duco_nodes_price=numeric("Duco Node-S price"),
        duco_pancakeswap_price=numeric("Duco PancakeSwap price"),
        duco_sunswap_price=numeric("Duco SunSwap price"),
        duco_sushiswap_price=numeric("Duco SushiSwap price"),
        duco_ubeswap_price=numeric("Duco UbeSwap price"),
        duco_price=numeric("Duco price"),
        duco_price_bch=numeric("Duco price BCH"),
        duco_price_nano=numeric("Duco price NANO"),
        duco_price_trx=numeric("Duco price TRX"),
        duco_price_xmg=numeric("Duco price XMG"),
        duino_coin_server_api=string("Duino-Coin Server API"),
        gratka=parse_gratka_statistics(
            _require_field(mapping, "Gratka", endpoint=endpoint),
            endpoint=endpoint,
        ),
        kolka=parse_kolka_statistics(
            _require_field(mapping, "Kolka", endpoint=endpoint),
            endpoint=endpoint,
        ),
        last_block_hash=string("Last block hash"),
        last_sync=_require_float(
            _require_field(mapping, "Last sync", endpoint=endpoint),
            name="Last sync",
            endpoint=endpoint,
        ),
        last_update=string("Last update"),
        mined_blocks=integer("Mined blocks"),
        miner_distribution=parse_miner_distribution(
            _require_field(
                mapping,
                "Miner distribution",
                endpoint=endpoint,
            ),
            endpoint=endpoint,
        ),
        net_energy_usage=string("Net energy usage"),
        open_threads=integer("Open threads"),
        pool_hashrate=string("Pool hashrate"),
        registered_users=integer("Registered users"),
        server_cpu_usage=_require_float(
            _require_field(mapping, "Server CPU usage", endpoint=endpoint),
            name="Server CPU usage",
            endpoint=endpoint,
        ),
        server_ram_usage=_require_float(
            _require_field(mapping, "Server RAM usage", endpoint=endpoint),
            name="Server RAM usage",
            endpoint=endpoint,
        ),
        server_version=_require_float(
            _require_field(mapping, "Server version", endpoint=endpoint),
            name="Server version",
            endpoint=endpoint,
        ),
        top_10_richest_miners=_parse_string_sequence(
            _require_field(
                mapping,
                "Top 10 richest miners",
                endpoint=endpoint,
            ),
            name="Top 10 richest miners",
            endpoint=endpoint,
        ),
        xxhash_hashrate=xxhash_hashrate,
        fast_miners_hashrate=(
            string("Fast miners hashrate")
            if "Fast miners hashrate" in mapping else None
        ),
        transaction_count=integer("transaction_count"),
    )


def _parse_string_sequence(
    payload: Any,
    *,
    name: str,
    endpoint: str | None = None,
) -> tuple[str, ...]:
    """
    *_parse_string_sequence Read a JSON array as a tuple of strings.*

    payload Any - Decoded API data to validate.
    name str - Field or argument name used in validation errors.
    endpoint str | None - API route associated with the request or response.
    """
    values = _require_list(
        payload,
        name=name,
        endpoint=endpoint,
    )

    return tuple(
        _require_string(
            value,
            name=f"{name} entry",
            endpoint=endpoint,
        )
        for value in values
    )


def parse_user_miners(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> list[Miner]:
    """
    *parse_user_miners Unpack the worker list from /miners/<username>.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    response = require_success(
        payload,
        endpoint=endpoint,
    )

    return parse_miner_list(
        response.result,
        endpoint=endpoint,
    )


def parse_transaction_response(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> Transaction:
    """
    *parse_transaction_response Unpack a single transaction found by ID or hash.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    response = require_success(
        payload,
        endpoint=endpoint,
    )

    return parse_transaction(
        response.result,
        endpoint=endpoint,
    )


def parse_user_transactions(
    payload: Any,
    *,
    endpoint: str | None = None,
) -> list[Transaction]:
    """
    *parse_user_transactions Unpack the list returned by /user_transactions/<username>.*

    payload Any - Decoded API data to validate.
    endpoint str | None - API route associated with the request or response.
    """
    response = require_success(
        payload,
        endpoint=endpoint,
    )

    return parse_transaction_list(
        response.result,
        endpoint=endpoint,
    )


def get_user_miners(
    self,
    username: str,
) -> list[Miner]:
    """
    *get_user_miners Fetch and parse the worker list for a user.*

    self DucoAPI - Client supplying the transport and request validation.
    username str - DUCO account name.
    """
    username = self._validate_username(username)

    endpoint = f"miners/{username}"

    payload = self._transport.request(
        "GET",
        endpoint,
    )

    return parse_user_miners(
        payload,
        endpoint=endpoint,
    )


def get_transaction(
    self,
    transaction_hash: str,
) -> Transaction:
    """
    *get_transaction Fetch and parse one transaction by its hash.*

    self DucoAPI - Client supplying the transport and request validation.
    transaction_hash str - Hash identifying the ledger entry.
    """
    transaction_hash = self._validate_identifier(
        transaction_hash,
        name="transaction_hash",
    )

    endpoint = f"transactions/{transaction_hash}"

    payload = self._transport.request(
        "GET",
        endpoint,
    )

    return parse_transaction_response(
        payload,
        endpoint=endpoint,
    )


def get_transaction_by_id(
    self,
    transaction_id: int,
) -> Transaction:
    """
    *get_transaction_by_id Fetch and parse one transaction by ID.*

    self DucoAPI - Client supplying the transport and request validation.
    transaction_id int - Positive numeric ledger ID.
    """
    transaction_id = self._validate_positive_int(
        transaction_id,
        name="transaction_id",
    )

    endpoint = f"id_transactions/{transaction_id}"

    payload = self._transport.request(
        "GET",
        endpoint,
    )

    return parse_transaction_response(
        payload,
        endpoint=endpoint,
    )


def get_user_transactions(
    self,
    username: str,
    *,
    limit: int = 10,
) -> list[Transaction]:
    """
    *get_user_transactions Fetch and parse recent transactions for a user.*

    self DucoAPI - Client supplying the transport and request validation.
    username str - DUCO account name.
    limit int - Maximum number of recent transactions to retrieve.
    """
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

    return parse_user_transactions(
        payload,
        endpoint=endpoint,
    )
