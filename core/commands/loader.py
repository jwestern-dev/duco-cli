"""Discover command modules from the root commands package."""

from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType


def load_commands(package: str = "commands") -> list[ModuleType]:
    """
    *load_commands Import public command modules in alphabetical order.*

    package str - Package containing the command modules.

    Imports register commands through their decorators. Python's module
    cache makes repeated calls safe, and import errors reach the caller.
    """
    root = import_module(package)
    modules = [root]

    def discover(parent: ModuleType) -> None:
        """
        *discover Visit this package's public modules and subpackages.*

        parent ModuleType - Package whose direct children are being discovered.
        """
        for info in sorted(
            iter_modules(parent.__path__, parent.__name__ + "."),
            key=lambda item: item.name,
        ):
            if info.name.rsplit(".", 1)[-1].startswith("_"):
                continue
            module = import_module(info.name)
            modules.append(module)
            if info.ispkg:
                discover(module)

    discover(root)
    return modules
