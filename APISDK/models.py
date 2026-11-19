#!/usr/bin/env python3
"""The data returned by the Duino-Coin API, with amounts stored as Decimals."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TypeAlias


# Shared type aliases

DUCOAmount: TypeAlias = Decimal
"""Type used for DUCO monetary amounts."""

UnixTimestamp: TypeAlias = int | float
"""Unix timestamp returned by the DUCO API."""


# User / account models


@dataclass(frozen=True, slots=True)
class UserBalance:
    """Wallet balance, stake and account details.

    The creation date keeps the API's text format. Login, stake and
    verification timestamps use the numeric values returned by the API.
    """

    balance: DUCOAmount
    created: str
    last_login: UnixTimestamp
    max_miners: int
    stake_amount: DUCOAmount
    stake_date: UnixTimestamp
    trust_score: int
    username: str
    verified: str
    verified_by: str
    verified_date: UnixTimestamp
    warnings: int


@dataclass(frozen=True, slots=True)
class User:
    """Balance, miners and recent transactions from /users/<username>."""

    balance: UserBalance
    miners: tuple["Miner", ...] = ()
    transactions: tuple["Transaction", ...] = ()


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    """Exchange price and the reported changes over 24 hours and seven days."""

    change_24h: DUCOAmount
    change_7d: DUCOAmount
    price: DUCOAmount


@dataclass(frozen=True, slots=True)
class ExchangeRates:
    """Exchange rates with field names from exch_rates.

    Bitstorage can be absent. In that case bitstorage is None.
    """

    bch: ExchangeRate
    bitstorage: ExchangeRate | None
    fluffy: ExchangeRate
    furim: ExchangeRate
    max: ExchangeRate
    nano: ExchangeRate
    nodes: ExchangeRate
    pancake: ExchangeRate
    sunswap: ExchangeRate
    sushi: ExchangeRate
    trx: ExchangeRate
    ubeswap: ExchangeRate
    xmg: ExchangeRate


@dataclass(frozen=True, slots=True)
class UserV3:
    """The wallet profile returned by /v3/users/<username>."""

    achievements: tuple[int, ...]
    balance: UserBalance
    exchange_rates: ExchangeRates
    items: tuple[object, ...] = ()
    miners: tuple["Miner", ...] = ()
    notices: tuple[object, ...] = ()
    transactions: tuple["Transaction", ...] = ()


# Transaction models


@dataclass(frozen=True, slots=True)
class Transaction:
    """A ledger entry with a numeric ID, hash and exact DUCO amount.

    The datetime field keeps the date and time text returned by the API.
    """

    amount: DUCOAmount
    datetime: str
    hash: str
    id: int
    memo: str
    recipient: str
    sender: str


# Mining models


@dataclass(frozen=True, slots=True)
class Miner:
    """An active miner and its share counters.

    Hashrate is in H/s. The fields it, ki, pg and wd retain their API names.
    The it and wd fields can be null.
    """

    accepted: int
    algorithm: str
    diff: int
    hashrate: float
    identifier: str
    it: object | None
    ki: int
    pg: int
    pool: str
    rejected: int
    sharerate: int
    sharetime: float
    software: str
    threadid: str
    username: str
    wd: str | None


# Pool models


@dataclass(frozen=True, slots=True)
class Pool:
    """Mining pool status, resource use and time since the last sync.

    The icon is a Font Awesome identifier. Region can be absent.
    """

    connections: int
    cpu: int
    icon: str
    last_sync: str
    name: str
    ram: int
    region: str | None
    type: str


# Shop models


@dataclass(frozen=True, slots=True)
class ShopItem:
    """A catalogue entry priced in DUCO.

    Descriptions may contain HTML. Some older items have no categories.
    """

    item_id: int
    description: str
    display: bool
    icon: str
    name: str
    price: DUCOAmount
    category: tuple[str, ...] | None = None


# Statistics models


@dataclass(frozen=True, slots=True)
class GratkaStatistics:
    """Activity, purchases and cached IP counts in the Gratka statistics."""

    active: int
    bought_items: int
    cached_ips: int


@dataclass(frozen=True, slots=True)
class KolkaStatistics:
    """Ban and jail counts reported by Kolka."""

    banned: int
    jailed: int


@dataclass(frozen=True, slots=True)
class MinerDistribution:
    """Miner counts by platform, including the network total."""

    all: int
    arduino: int
    cpu: int
    esp32: int
    esp8266: int
    gpu: int
    other: int
    phone: int
    rpi: int
    web: int


@dataclass(frozen=True, slots=True)
class Statistics:
    """Network totals, prices and server status from /statistics.

    The API uses human-readable keys for these fields. It can omit the
    Bitstorage price and fast-miner hashrate. The richest-miner entries
    retain the text returned by the API.
    """

    active_connections: int
    all_time_mined_duco: DUCOAmount
    current_difficulty: int
    duco_s1_hashrate: str

    duco_bitstorage_price: DUCOAmount | None
    duco_fluffyswap_price: DUCOAmount
    duco_furim_price: DUCOAmount
    duco_nodes_price: DUCOAmount
    duco_pancakeswap_price: DUCOAmount
    duco_sunswap_price: DUCOAmount
    duco_sushiswap_price: DUCOAmount
    duco_ubeswap_price: DUCOAmount
    duco_price: DUCOAmount
    duco_price_bch: DUCOAmount
    duco_price_nano: DUCOAmount
    duco_price_trx: DUCOAmount
    duco_price_xmg: DUCOAmount

    duino_coin_server_api: str

    gratka: GratkaStatistics
    kolka: KolkaStatistics

    last_block_hash: str
    last_sync: float
    last_update: str
    mined_blocks: int

    miner_distribution: MinerDistribution

    net_energy_usage: str
    open_threads: int
    pool_hashrate: str
    registered_users: int

    server_cpu_usage: float
    server_ram_usage: float
    server_version: float

    top_10_richest_miners: tuple[str, ...]

    xxhash_hashrate: str | int | float
    transaction_count: int
    fast_miners_hashrate: str | None = None


# Mining-key models


@dataclass(frozen=True, slots=True)
class MiningKeyStatus:
    """Whether the API reports a mining key for the account."""

    has_key: bool


# Generic response metadata


@dataclass(frozen=True, slots=True)
class APIResponseMetadata:
    """The success flag and any server name or message returned by the API."""

    success: bool
    server: str | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class APIResponse:
    """Response metadata and the raw result value from the JSON envelope."""

    metadata: APIResponseMetadata
    result: object = field(default=None)
