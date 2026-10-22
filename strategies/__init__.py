"""
strategies/__init__.py - Registry and auto-loader for window arrangement strategies.
"""

import importlib
import os
import pkgutil
from typing import Dict, Type
from strategies.base import ArrangementStrategy

_REGISTRY: Dict[str, Type[ArrangementStrategy]] = {}


def register_strategy(name: str):
    """Decorator to register a window arrangement strategy class."""

    def decorator(cls: Type[ArrangementStrategy]):
        cls.name = name.lower()
        _REGISTRY[cls.name] = cls
        return cls

    return decorator


def get_strategy(name: str) -> ArrangementStrategy:
    """Returns an instance of the requested strategy by name or layout file."""
    clean_name = (name or "").strip().lower()
    if clean_name in _REGISTRY:
        return _REGISTRY[clean_name]()

    # If the strategy name corresponds to a layout file in layouts/, use CustomLayout
    try:
        from test_window_launcher import find_layout_file
        if find_layout_file(name):
            return _REGISTRY["custom"]()
    except Exception:
        pass

    available = ", ".join(sorted(_REGISTRY.keys()))
    raise ValueError(f"Unknown strategy '{name}'. Available strategies: {available}")


def list_strategies() -> Dict[str, str]:
    """Returns a dictionary mapping strategy names to their descriptions."""
    return {name: cls.description or cls.__name__ for name, cls in _REGISTRY.items()}


# Auto-discover and register all strategies in this package
from strategies.side_by_side import SideBySideLayout
from strategies.grid import GridLayout
from strategies.stack import StackLayout
from strategies.other_bottom import OtherBottomLayout
from strategies.custom_layout import CustomLayout

register_strategy("default")(SideBySideLayout)
register_strategy("side_by_side")(SideBySideLayout)
register_strategy("grid")(GridLayout)
register_strategy("stack")(StackLayout)
register_strategy("other_bottom")(OtherBottomLayout)
register_strategy("custom")(CustomLayout)

# Dynamically import any other user-added .py modules in strategies/
package_dir = os.path.dirname(__file__)
for _, module_name, is_pkg in pkgutil.iter_modules([package_dir]):
    if not is_pkg and module_name not in ("base", "__init__", "side_by_side", "grid", "stack"):
        try:
            importlib.import_module(f"strategies.{module_name}")
        except Exception as e:
            print(f"[Warning] Failed to load strategy module {module_name}: {e}")
