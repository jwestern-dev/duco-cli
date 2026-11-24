#!/usr/bin/env python3
"""The data returned by the Duino-Coin API, with amounts stored as Decimals."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TypeAlias

DUCOAmount: TypeAlias = Decimal
"""Type used for DUCO monetary amounts."""

UnixTimestamp: TypeAlias = int | float
"""Unix timestamp returned by the DUCO API."""


@dataclass(frozen=True, slots=True)
class UserBalance:
    """
    *UserBalance Wallet balance, stake and account details.*

    balance DUCOAmount - Wallet balance reported by the API.
    created str - Account creation date in the server's text format.
    last_login UnixTimestamp - Unix time of the most recent login.
    max_miners int - Account limit on active miners.
    stake_amount DUCOAmount - Amount held in staking.
    stake_date UnixTimestamp - Unix time of the stake.
    trust_score int - Trust score reported for the account.
    username str - DUCO account name.
    verified str - Account verification status as returned by the server.
    verified_by str - Identity recorded for the verification.
    verified_date UnixTimestamp - Unix time of verification.
    warnings int - Number of warnings recorded for the account.

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
    """
    *User Balance, miners and recent transactions from /users/<username>.*

    balance UserBalance - Wallet and account details.
    miners tuple['Miner', ...] - Workers active on this account.
    transactions tuple['Transaction', ...] - Recent ledger entries for the account.
    """

    balance: UserBalance
    miners: tuple["Miner", ...] = ()
    transactions: tuple["Transaction", ...] = ()


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    """
    *ExchangeRate Exchange price and the reported changes over 24 hours and seven days.*

    change_24h DUCOAmount - Price change reported over the previous 24 hours.
    change_7d DUCOAmount - Price change reported over the previous seven days.
    price DUCOAmount - Price reported by the source.
    """

    change_24h: DUCOAmount
    change_7d: DUCOAmount
    price: DUCOAmount


@dataclass(frozen=True, slots=True)
class ExchangeRates:
    """
    *ExchangeRates Exchange rates with field names from exch_rates.*

    bch ExchangeRate - Reported bch exchange rate.
    bitstorage ExchangeRate | None - Reported bitstorage exchange rate when available.
    fluffy ExchangeRate - Reported fluffy exchange rate.
    furim ExchangeRate - Reported furim exchange rate.
    max ExchangeRate - Reported max exchange rate.
    nano ExchangeRate - Reported nano exchange rate.
    nodes ExchangeRate - Reported nodes exchange rate.
    pancake ExchangeRate - Reported pancake exchange rate.
    sunswap ExchangeRate - Reported sunswap exchange rate.
    sushi ExchangeRate - Reported sushi exchange rate.
    trx ExchangeRate - Reported trx exchange rate.
    ubeswap ExchangeRate - Reported ubeswap exchange rate.
    xmg ExchangeRate - Reported xmg exchange rate.

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
    """
    *UserV3 The wallet profile returned by /v3/users/<username>.*

    achievements tuple[int, ...] - Identifiers of unlocked achievements.
    balance UserBalance - Wallet and account details.
    exchange_rates ExchangeRates - Exchange prices included with the profile.
    items tuple[object, ...] - Item identifiers from the account inventory.
    miners tuple['Miner', ...] - Workers active on this account.
    notices tuple[object, ...] - Account notices in the order returned.
    transactions tuple['Transaction', ...] - Recent ledger entries for the account.
    """

    achievements: tuple[int, ...]
    balance: UserBalance
    exchange_rates: ExchangeRates
    items: tuple[object, ...] = ()
    miners: tuple["Miner", ...] = ()
    notices: tuple[object, ...] = ()
    transactions: tuple["Transaction", ...] = ()


@dataclass(frozen=True, slots=True)
class Transaction:
    """
    *Transaction A ledger entry with a numeric ID, hash and exact DUCO amount.*

    amount DUCOAmount - Transfer amount in DUCO.
    datetime str - Date and time text from the ledger.
    hash str - Transaction hash.
    id int - Numeric ledger identifier.
    memo str - Text attached to the transfer.
    recipient str - Account receiving the transfer.
    sender str - Account sending the transfer.

    The datetime field keeps the date and time text returned by the API.
    """

    amount: DUCOAmount
    datetime: str
    hash: str
    id: int
    memo: str
    recipient: str
    sender: str


@dataclass(frozen=True, slots=True)
class Miner:
    """
    *Miner An active miner and its share counters.*

    accepted int - Shares accepted from this worker.
    algorithm str - Proof-of-work algorithm reported by the worker.
    diff int - Current worker difficulty.
    hashrate float - Worker throughput in hashes per second.
    identifier str - Rig identifier shared by the worker threads.
    it object | None - Worker telemetry field retained under the API name it.
    ki int - Worker telemetry field retained under the API name ki.
    pg int - Worker telemetry field retained under the API name pg.
    pool str - Pool serving this worker.
    rejected int - Shares rejected from this worker.
    sharerate int - Share rate reported by the worker.
    sharetime float - Share time reported by the worker.
    software str - Mining software identifier.
    threadid str - Identifier for this worker thread.
    username str - DUCO account name.
    wd str | None - Worker telemetry field retained under the API name wd.

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


@dataclass(frozen=True, slots=True)
class Pool:
    """
    *Pool Mining pool status, resource use and time since the last sync.*

    connections int - Number of pool connections.
    cpu int - Reported processor utilisation.
    icon str - Font Awesome identifier for the pool icon.
    last_sync str - Last synchronisation reported by the server.
    name str - Pool name.
    ram int - Reported memory utilisation.
    region str | None - Pool location when supplied.
    type str - Pool type reported by the server.

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


@dataclass(frozen=True, slots=True)
class ShopItem:
    """
    *ShopItem A catalogue entry priced in DUCO.*

    item_id int - Catalogue identifier for the item.
    description str - Catalogue description, which may contain HTML.
    display bool - Whether the item can be displayed on a profile.
    icon str - Item icon URL.
    name str - Item name from the catalogue.
    price DUCOAmount - Price reported by the source.
    category tuple[str, ...] | None - Catalogue categories when available.

    Descriptions may contain HTML. Some older items have no categories.
    """

    item_id: int
    description: str
    display: bool
    icon: str
    name: str
    price: DUCOAmount
    category: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class GratkaStatistics:
    """
    *GratkaStatistics Activity, purchases and cached IP counts in the Gratka statistics.*

    active int - Activity count reported by Gratka.
    bought_items int - Number of purchases reported by Gratka.
    cached_ips int - Number of cached IP addresses.
    """

    active: int
    bought_items: int
    cached_ips: int


@dataclass(frozen=True, slots=True)
class KolkaStatistics:
    """
    *KolkaStatistics Ban and jail counts reported by Kolka.*

    banned int - Accounts reported as banned.
    jailed int - Accounts reported as jailed.
    """

    banned: int
    jailed: int


@dataclass(frozen=True, slots=True)
class MinerDistribution:
    """
    *MinerDistribution Miner counts by platform, including the network total.*

    all int - Total across all miner platforms.
    arduino int - Number of miners in the API’s arduino category.
    cpu int - Number of miners in the API’s cpu category.
    esp32 int - Number of miners in the API’s esp32 category.
    esp8266 int - Number of miners in the API’s esp8266 category.
    gpu int - Number of miners in the API’s gpu category.
    other int - Number of miners in the API’s other category.
    phone int - Number of miners in the API’s phone category.
    rpi int - Number of miners in the API’s rpi category.
    web int - Number of miners in the API’s web category.
    """

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
    """
    *Statistics Network totals, prices and server status from /statistics.*

    active_connections int - Number of active network connections.
    all_time_mined_duco DUCOAmount - Total DUCO mined since the network began.
    current_difficulty int - Network difficulty at the time of the snapshot.
    duco_s1_hashrate str - Reported DUCO-S1 throughput.
    duco_bitstorage_price DUCOAmount | None - DUCO price reported for BITSTORAGE.
    duco_fluffyswap_price DUCOAmount - DUCO price reported for FLUFFYSWAP.
    duco_furim_price DUCOAmount - DUCO price reported for FURIM.
    duco_nodes_price DUCOAmount - DUCO price reported for NODES.
    duco_pancakeswap_price DUCOAmount - DUCO price reported for PANCAKESWAP.
    duco_sunswap_price DUCOAmount - DUCO price reported for SUNSWAP.
    duco_sushiswap_price DUCOAmount - DUCO price reported for SUSHISWAP.
    duco_ubeswap_price DUCOAmount - DUCO price reported for UBESWAP.
    duco_price DUCOAmount - Reported reference price of DUCO.
    duco_price_bch DUCOAmount - DUCO price reported for BCH.
    duco_price_nano DUCOAmount - DUCO price reported for NANO.
    duco_price_trx DUCOAmount - DUCO price reported for TRX.
    duco_price_xmg DUCOAmount - DUCO price reported for XMG.
    duino_coin_server_api str - Server API identifier.
    gratka GratkaStatistics - Gratka component statistics.
    kolka KolkaStatistics - Kolka component statistics.
    last_block_hash str - Hash of the latest block.
    last_sync float - Last synchronisation reported by the server.
    last_update str - Last update text from the API.
    mined_blocks int - Total blocks mined.
    miner_distribution MinerDistribution - Worker counts grouped by platform.
    net_energy_usage str - Reported network energy usage.
    open_threads int - Number of open server threads.
    pool_hashrate str - Combined pool throughput as reported.
    registered_users int - Number of registered accounts.
    server_cpu_usage float - Server processor utilisation.
    server_ram_usage float - Server memory utilisation.
    server_version float - Server version reported by the statistics endpoint.
    top_10_richest_miners tuple[str, ...] - Ranked account entries as supplied by the API.
    xxhash_hashrate str | int | float - Reported XXHASH throughput.
    transaction_count int - Number of ledger transactions.
    fast_miners_hashrate str | None - Reported throughput of fast miners when available.

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


@dataclass(frozen=True, slots=True)
class MiningKeyStatus:
    """
    *MiningKeyStatus Whether the API reports a mining key for the account.*

    has_key bool - Whether the account has a configured mining key.
    """

    has_key: bool


@dataclass(frozen=True, slots=True)
class APIResponseMetadata:
    """
    *APIResponseMetadata The success flag and any server name or message returned by the API.*

    success bool - Application-level success flag.
    server str | None - Server identifier reported by the API.
    message str | None - Message for the caller.
    """

    success: bool
    server: str | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class APIResponse:
    """
    *APIResponse Response metadata and the raw result value from the JSON envelope.*

    metadata APIResponseMetadata - Status and server information from the response envelope.
    result object - Decoded result carried by the envelope.
    """

    metadata: APIResponseMetadata
    result: object = field(default=None)
