"""
config_manager.py - Loads, validates, and hot-reloads configuration from config.yaml.
Monitors the config file periodically and triggers a callback when changed.
"""

import os
import time
import hashlib
from typing import Any, Callable, Dict, Optional
import yaml

DEFAULT_CONFIG: Dict[str, Any] = {
    "game_windows": {
        "filter": {
            "titles": ["Hold'em", "Omaha", "Tournament", "Table", "NLH"],
            "title_pattern": "",
            "classes": [],
            "class_pattern": "",
            "exclude": [
                "Lobby",
                "Cashier",
                "Tournament Lobby",
                "File Explorer",
                "Visual Studio",
                "Explorer",
                "WhatsApp",
                "Discord",
                "PuTTY",
                "Keepass",
                "Outlook",
                "PowerShell",
                "Command Prompt",
            ],
            "exclude_titles": [
                "Lobby",
                "Cashier",
                "Tournament Lobby",
                "File Explorer",
                "Visual Studio",
                "Explorer",
                "WhatsApp",
                "Discord",
                "PuTTY",
                "Keepass",
                "Outlook",
                "PowerShell",
                "Command Prompt",
            ],
            "exclude_title_pattern": "",
            "exclude_classes": [
                "CabinetWClass",
                "Chrome_WidgetWin_1",
                "CASCADIA_HOSTING_WINDOW_C",
                "ConsoleWindowClass",
                "Progman",
                "WorkerW",
            ],
            "exclude_class_pattern": "",
            "case_sensitive": False,
            "sort_by": "hwnd",
        },
        "strategy": "default",
        "strategy_config": {
            "default": {
                "gap": 0,
                "keep_aspect_ratio": True,
                "aspect_ratio": "auto",
                "vertical_overlap": 50,
                "vertical_overlap_4_tables": 200,
                "max_spots": 6,
                "single_window_slot": "left",
            },
            "grid": {
                "columns": 2,
                "rows": 2,
                "gap": 2,
            },
            "stack": {
                "offset_x": 30,
                "offset_y": 30,
                "width_ratio": 0.8,
                "height_ratio": 0.8,
            },
        },
    },
    "other_windows": {
        "enabled": True,
        "filter": {
            "titles": ["Lobby", "Cashier", "Tournament Lobby", "Notes", "HUD"],
            "title_pattern": "",
            "classes": [],
            "class_pattern": "",
            "exclude": ["File Explorer", "Visual Studio", "WhatsApp", "Discord", "PuTTY"],
            "exclude_titles": ["File Explorer", "Visual Studio", "WhatsApp", "Discord", "PuTTY"],
            "exclude_title_pattern": "",
            "exclude_classes": ["CabinetWClass", "Chrome_WidgetWin_1"],
            "exclude_class_pattern": "",
            "case_sensitive": False,
            "sort_by": "hwnd",
        },
        "layout": {
            "resize": False,
            "gap": 2,
            "alignment": "left",
            "reserve_space_only_if_present": True,
        },
    },
    "rng": {
        "enabled": True,
        "hotkey": "F8",
        "middle_click": True,
        "auto_reroll_seconds": 10.0,
        "threshold_value": 50,
        "show_slider": True,
        "slider_min": 0,
        "slider_max": 100,
        "color_above": "#00FF41",
        "color_below": "#FF3B30",
        "font_family": "Segoe UI",
        "font_size": 28,
        "window_width": 140,
        "window_height": 90,
        "position": "center",
        "always_on_top": True,
        "click_to_reroll": True,
        "hide_on_click_outside": True,
    },
    "runtime": {
        "poll_interval_seconds": 1.0,
        "config_check_interval_seconds": 10.0,
        "compensate_invisible_borders": True,
        "restore_minimized": False,
        "bring_tables_to_front": False,
    },
}


class ConfigManager:
    """
    Manages loading, validating, and hot-reloading application configuration.
    Monitors config file mtime and hash every check_interval seconds.
    """

    def __init__(
        self,
        config_path: str = "config.yaml",
        on_change_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        check_interval: float = 10.0,
    ):
        self.config_path = config_path
        self.on_change_callback = on_change_callback
        self.check_interval = check_interval

        self._last_mtime: float = 0.0
        self._last_hash: str = ""
        self._last_check_time: float = 0.0
        self._current_config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """Loads and returns config. Creates default file if it doesn't exist."""
        if not os.path.exists(self.config_path):
            self._create_default_config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()

            self._last_mtime = os.path.getmtime(self.config_path)
            self._last_hash = self._calc_hash(content)
            self._last_check_time = time.time()

            parsed = yaml.safe_load(content) or {}
            merged = self._merge_with_defaults(parsed)
            self._current_config = merged

            runtime_cfg = merged.get("runtime", {})
            self.check_interval = float(runtime_cfg.get("config_check_interval_seconds", 10.0))

            return merged

        except Exception as e:
            print(f"[Config Error] Failed to load {self.config_path}: {e}. Using defaults.")
            self._current_config = DEFAULT_CONFIG.copy()
            return self._current_config

    def check_for_changes(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Checks if config file has been modified.
        Only performs the actual disk check if check_interval seconds have passed (or if force=True).
        Returns the new configuration dictionary if reloaded, None otherwise.
        """
        now = time.time()
        if not force and (now - self._last_check_time < self.check_interval):
            return None

        self._last_check_time = now

        if not os.path.exists(self.config_path):
            return None

        try:
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime == self._last_mtime:
                return None

            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()

            content_hash = self._calc_hash(content)
            if content_hash == self._last_hash:
                self._last_mtime = current_mtime
                return None

            new_parsed = yaml.safe_load(content)
            if not isinstance(new_parsed, dict):
                print(f"[Config Warning] {self.config_path} is not a valid YAML dictionary; keeping current configuration.")
                return None

            merged = self._merge_with_defaults(new_parsed)
            self._current_config = merged
            self._last_mtime = current_mtime
            self._last_hash = content_hash

            runtime_cfg = merged.get("runtime", {})
            self.check_interval = float(runtime_cfg.get("config_check_interval_seconds", 10.0))

            if self.on_change_callback:
                try:
                    self.on_change_callback(merged)
                except Exception as cb_err:
                    print(f"[Config Callback Error] {cb_err}")

            return merged

        except yaml.YAMLError as ye:
            print(f"[Config Syntax Error] File modified with invalid YAML syntax; keeping current settings:\n  {ye}")
            return None
        except Exception as e:
            print(f"[Config Error] Error checking config: {e}")
            return None

    @property
    def current(self) -> Dict[str, Any]:
        """Returns the current configuration dictionary."""
        return self._current_config

    def check_for_updates(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """Alias for check_for_changes."""
        return self.check_for_changes(force=force)

    def _calc_hash(self, content: str) -> str:
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _merge_with_defaults(self, custom: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge custom configuration with defaults and handle backward compatibility."""
        result = DEFAULT_CONFIG.copy()

        if "filter" in custom and "game_windows" not in custom:
            custom["game_windows"] = {
                "filter": custom.get("filter", {}),
                "strategy": custom.get("strategy", "side_by_side"),
                "strategy_config": custom.get("strategy_config", {}),
            }

        def _merge_dict(base: dict, override: dict) -> dict:
            out = base.copy()
            for k, v in override.items():
                if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                    out[k] = _merge_dict(out[k], v)
                else:
                    out[k] = v
            return out

        return _merge_dict(result, custom)


DEFAULT_CONFIG_TEMPLATE = """# ==============================================================================
# Window Tiler Configuration
# This file is monitored every 10 seconds for changes and hot-reloaded automatically.
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. GAME WINDOWS (Active Poker Tables)
# Arranges 2 to 4 tables to utilize full screen with configurable vertical overlap.
# ------------------------------------------------------------------------------
game_windows:
  filter:
    # Strings to identify poker table windows:
    # If any of these strings is part of a window title, it is counted as a game window
    titles:
      - "Hold'em"
      - "Omaha"
      - "Tournament"
      - "Table"
      - "NLH"

    # Exclude strings: If any of these strings is part of a title, the window is ignored
    exclude:
      - "Lobby"
      - "Cashier"
      - "Tournament Lobby"
      - "File Explorer"
      - "Visual Studio"
      - "Explorer"
      - "WhatsApp"
      - "Discord"
      - "PuTTY"
      - "Keepass"
      - "Outlook"
      - "PowerShell"
      - "Command Prompt"

    # Win32 Class Name strings (optional list):
    # If specified, window class must contain any of these strings
    classes: []

    # Exclude Win32 Class Names:
    # If any of these strings is part of the class name, the window is ignored
    exclude_classes:
      - "CabinetWClass"
      - "Chrome_WidgetWin_1"
      - "CASCADIA_HOSTING_WINDOW_C"
      - "ConsoleWindowClass"
      - "Progman"
      - "WorkerW"

    case_sensitive: false
    sort_by: "hwnd"

  # Arranging strategy class for game windows:
  #   - 'default':      Default layout (2 tables fill screen width, 4 tables with overlap, 6 tables)
  #   - 'custom':       Custom slot layout from layouts/ directory
  #   - 'grid':         NxM grid (2x2, 3x2, etc.)
  #   - 'stack':        Stacked / cascaded windows
  strategy: "default"

  strategy_config:
    default:
      gap: 0
      keep_aspect_ratio: true
      aspect_ratio: "auto"
      vertical_overlap: 50
      vertical_overlap_4_tables: 200
      max_spots: 6
      single_window_slot: "left"
    grid:
      columns: 2
      rows: 2
      gap: 2
    stack:
      offset_x: 30
      offset_y: 30
      width_ratio: 0.8
      height_ratio: 0.8

# ------------------------------------------------------------------------------
# 2. OTHER POKER WINDOWS (Lobbies, Cashiers, Notes, HUD)
# Positioned side-by-side along the bottom of the screen.
# ------------------------------------------------------------------------------
other_windows:
  # Enable/disable arranging other windows
  enabled: true

  filter:
    # Strings to identify auxiliary poker windows (lobbies, cashier, tournament lobby, notes, hud)
    # If any of these strings is part of a window title, it is positioned at the bottom
    titles:
      - "Lobby"
      - "Cashier"
      - "Tournament Lobby"
      - "Notes"
      - "HUD"

    # Exclude strings: If any of these strings is part of a title, the window is ignored
    exclude:
      - "File Explorer"
      - "Visual Studio"
      - "WhatsApp"
      - "Discord"
      - "PuTTY"

    # Win32 Class Name strings (optional list)
    classes: []

    # Exclude Win32 Class Names
    exclude_classes:
      - "CabinetWClass"
      - "Chrome_WidgetWin_1"

    case_sensitive: false
    sort_by: "hwnd"

  layout:
    # resize: false -> Preserves the natural window size of the lobby (do not stretch or resize)
    resize: false
    gap: 2
    alignment: "left"  # 'left', 'center', or 'right'
    reserve_space_only_if_present: true

  toggle_shortcut: "F9"
  shift_middle_click_to_front: true
  middle_click_to_front: false

# ------------------------------------------------------------------------------
# 3. RANDOM NUMBER GENERATOR (RNG) DECISION ASSISTANT
# ------------------------------------------------------------------------------
rng:
  enabled: true
  hotkey: "F8"
  middle_click: true
  auto_reroll_seconds: 10.0
  threshold_value: 50
  show_slider: true
  slider_min: 0
  slider_max: 100
  color_above: "#00FF41"
  color_below: "#FF3B30"
  font_family: "Segoe UI"
  font_size: 28
  window_width: 140
  window_height: 90
  position: "center"
  always_on_top: true
  click_to_reroll: true
  hide_on_click_outside: true

# ------------------------------------------------------------------------------
# 4. RUNTIME SETTINGS
# ------------------------------------------------------------------------------
runtime:
  poll_interval_seconds: 1.0
  config_check_interval_seconds: 10.0
  compensate_invisible_borders: true
  restore_minimized: false
  bring_tables_to_front: false
"""


def _create_default_config(self: ConfigManager) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
    with open(self.config_path, "w", encoding="utf-8") as f:
        f.write(DEFAULT_CONFIG_TEMPLATE)


ConfigManager._create_default_config = _create_default_config  # type: ignore
