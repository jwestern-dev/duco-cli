"""DucoCLI command implementations, discovered at startup."""

from core.commands import REGISTRY

for _CATEGORY, _DESCRIPTION in {
    "wallet": "Wallet commands",
    "network": "Network commands",
    "system": "System / CLI commands",
    "shop": "Shop commands",
    "config": "Configuration commands",
}.items():
    REGISTRY.set_category_description(_CATEGORY, _DESCRIPTION)
