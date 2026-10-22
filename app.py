"""
app.py - Main entry point for Window Tiler.

Features:
  - Game Windows: Arranges active poker tables using pluggable strategies (e.g. side_by_side).
    Supports 2 to 4 tables with configurable vertical overlap (default 50px) and zero margins.
  - Other Poker Windows: Positions auxiliary windows (lobbies, cashiers, HUD, notes)
    side-by-side along the bottom of the screen (preserving original size without stretching).
  - Quick Bring-to-Front: Easily view other windows via Shift+Middle Click or F9 shortcut.
  - Random Number Generator (RNG): Decision assistant popup (0-100, green/red slider)
    positioned at top-center by default, triggered via Middle Click or F8 shortcut.
  - Config Monitor: Checks config.yaml every 10 seconds and hot-reloads on change.
"""

import argparse
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import win_utils
from config_manager import ConfigManager
from window_filter import WindowFilter
from strategies import get_strategy, list_strategies
from strategies.other_bottom import OtherBottomLayout
from rng_window import RNGWindow
from input_hook import InputHookManager


class WindowTilerApp:
    """
    Core engine orchestrating game tables, auxiliary bottom windows,
    configuration hot-reloading, and the RNG decision popup.
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config_manager = ConfigManager(
            config_path=config_path,
            on_change_callback=self._on_config_changed,
            check_interval=10.0,
        )
        self.config: Dict[str, Any] = {}

        # Filters and strategies
        self.game_filter: WindowFilter = None  # type: ignore
        self.other_filter: WindowFilter = None  # type: ignore
        self.game_strategy_name: str = "default"
        self.game_strategy = None
        self.other_strategy = OtherBottomLayout()
        self.arranged_game_hwnds: List[int] = []
        self.other_windows_in_front: bool = False

        # RNG and input hook
        self.rng_app: Optional[RNGWindow] = None
        self.rng_thread = None
        self.input_hook: Optional[InputHookManager] = None

        # Enable Windows DPI awareness
        win_utils.enable_dpi_awareness()

        # Load initial configuration
        self._load_config()
        self._init_subsystems()

    def _load_config(self) -> None:
        """Loads and activates configuration."""
        self.config = self.config_manager.load()
        self._apply_config(self.config, is_initial=True)

    def _apply_config(self, cfg: Dict[str, Any], is_initial: bool = False) -> None:
        """Applies configuration settings to components."""
        # 1. Game Windows Filter & Strategy
        game_cfg = cfg.get("game_windows", {})
        self.game_filter = WindowFilter.from_config(game_cfg.get("filter", {}))

        strat_name = str(game_cfg.get("strategy", "default")).strip()
        try:
            self.game_strategy = get_strategy(strat_name)
            self.game_strategy_name = strat_name
        except Exception as e:
            print(f"[Warning] Could not load strategy '{strat_name}': {e}. Falling back to 'default'.")
            self.game_strategy = get_strategy("default")
            self.game_strategy_name = "default"

        # 2. Other Poker Windows Filter
        other_cfg = cfg.get("other_windows", {})
        self.other_filter = WindowFilter.from_config(other_cfg.get("filter", {}))

        # 3. Runtime settings
        runtime_cfg = cfg.get("runtime", {})
        self.arrange_interval = float(runtime_cfg.get("arrange_interval_seconds", 2.0))
        self.config_manager.check_interval = float(runtime_cfg.get("config_check_interval_seconds", 10.0))

        # 4. RNG settings update
        rng_cfg = cfg.get("rng", {})
        if self.rng_app:
            self.rng_app.update_config(rng_cfg)

        if self.input_hook:
            self.input_hook.update_settings(
                enable_middle_mouse=bool(rng_cfg.get("trigger_middle_mouse", True)),
                rng_shortcut=str(rng_cfg.get("shortcut", "F8")),
                other_shortcut=str(other_cfg.get("toggle_shortcut", "F9")),
                shift_middle_triggers_other=bool(other_cfg.get("shift_middle_click_to_front", True)),
                middle_triggers_both=bool(other_cfg.get("middle_mouse_triggers_both", False)),
            )

        if not is_initial:
            print(
                f"[Config Reloaded] Game Strategy: '{self.game_strategy_name}' | "
                f"Config check: {self.config_manager.check_interval}s"
            )

    def _init_subsystems(self) -> None:
        """Initializes the RNG window and input hooks."""
        rng_cfg = self.config.get("rng", {})
        other_cfg = self.config.get("other_windows", {})

        try:
            if bool(rng_cfg.get("enabled", True)):
                self.rng_app = RNGWindow(rng_cfg)
                self.rng_thread = self.rng_app.run_in_thread()

            self.input_hook = InputHookManager(
                on_rng_trigger=self._on_rng_triggered,
                on_other_trigger=self.toggle_other_windows_to_front,
                enable_middle_mouse=bool(rng_cfg.get("trigger_middle_mouse", True)),
                rng_shortcut=str(rng_cfg.get("shortcut", "F8")),
                other_shortcut=str(other_cfg.get("toggle_shortcut", "F9")),
                shift_middle_triggers_other=bool(other_cfg.get("shift_middle_click_to_front", True)),
                middle_triggers_both=bool(other_cfg.get("middle_mouse_triggers_both", False)),
            )
            self.input_hook.start()
        except Exception as e:
            print(f"[Init Error] Could not initialize subsystems: {e}")

    def _on_rng_triggered(self) -> None:
        """Invoked when middle mouse button or keyboard shortcut is pressed."""
        if self.rng_app:
            self.rng_app.trigger_from_any_thread(action="toggle")

    def toggle_other_windows_to_front(self) -> None:
        """Brings all matched auxiliary/other poker windows (lobbies, cashiers) into front view."""
        all_windows = win_utils.get_all_top_level_windows()
        matched_other = self.other_filter.filter(all_windows)
        if not matched_other:
            print("[Window Tiler] No other/lobby windows found to bring to front.")
            return

        SW_RESTORE = 9
        win_utils.reset_bottom_state()
        self.other_windows_in_front = True
        for w in matched_other:
            win_utils.user32.ShowWindow(w.hwnd, SW_RESTORE)
            win_utils.user32.SetForegroundWindow(w.hwnd)
            win_utils.user32.BringWindowToTop(w.hwnd)

        print(f"[Window Tiler] Brought {len(matched_other)} auxiliary window(s) into view.")

    def _on_config_changed(self, new_cfg: Dict[str, Any]) -> None:
        """Called automatically when config.yaml is modified and reloaded."""
        self._apply_config(new_cfg, is_initial=False)
        self.arrange_windows(verbose=True)

    def get_adjusted_work_area(self) -> win_utils.Rect:
        """Retrieves monitor work area adjusted by margin padding in config."""
        monitor_cfg = self.config.get("monitor", {})
        m_index = int(monitor_cfg.get("index", 0))
        base_work_area = win_utils.get_monitor_work_area(m_index)

        margins = monitor_cfg.get("margin", {})
        top = int(margins.get("top", 0))
        bottom = int(margins.get("bottom", 0))
        left = int(margins.get("left", 0))
        right = int(margins.get("right", 0))

        return win_utils.Rect(
            x=base_work_area.x + left,
            y=base_work_area.y + top,
            width=max(200, base_work_area.width - (left + right)),
            height=max(200, base_work_area.height - (top + bottom)),
        )

    def split_work_areas(
        self,
        work_area: win_utils.Rect,
        matched_other: List[win_utils.WindowInfo],
        game_window_count: int = 0,
    ) -> Tuple[win_utils.Rect, win_utils.Rect, bool]:
        """
        Splits screen work area into:
          - Upper work area for game tables
          - Bottom work area for other/auxiliary poker windows
        When > 2 game windows are present (configurable via reserve_space_max_tables: 2):
          - Game tables take the WHOLE screen (height = work_area.height).
          - Other windows (lobby) remain in the background (send_to_bottom=True),
            so game tables have the full display unless the lobby is explicitly called.
        When <= 2 game windows are present:
          - Game tables take the upper space above the lobby.
          - Lobby is visible at the bottom unresized.
        """
        other_cfg = self.config.get("other_windows", {})
        other_enabled = bool(other_cfg.get("enabled", True))
        layout_cfg = other_cfg.get("layout", {})
        reserve_only_if_present = bool(layout_cfg.get("reserve_space_only_if_present", True))
        max_tables_for_bottom = int(layout_cfg.get("reserve_space_max_tables", 2))

        has_other_windows = bool(matched_other)
        should_split = other_enabled and (has_other_windows or not reserve_only_if_present)

        if not should_split:
            return work_area, win_utils.Rect(0, 0, 0, 0), False

        gap = int(layout_cfg.get("gap", 0))
        should_resize = bool(layout_cfg.get("resize", False))

        if not should_resize and matched_other:
            # Measure actual visible height of auxiliary windows, bounded so they never consume more than 35% of screen
            max_other_h = int(work_area.height * 0.35)
            bottom_h = min(max_other_h, max(w.rect.height for w in matched_other))
        else:
            height_percent = max(10, min(80, int(layout_cfg.get("height_percent", 25))))
            bottom_h = int(work_area.height * (height_percent / 100.0))

        bottom_area = win_utils.Rect(
            x=work_area.x,
            y=work_area.bottom - bottom_h,
            width=work_area.width,
            height=bottom_h,
        )

        # When more than 2 game tables are active, game tables take the WHOLE screen
        if game_window_count > max_tables_for_bottom:
            game_area = work_area
            send_other_to_bottom = True
        else:
            game_h = max(100, work_area.height - bottom_h - gap)
            game_area = win_utils.Rect(
                x=work_area.x,
                y=work_area.y,
                width=work_area.width,
                height=game_h,
            )
            send_other_to_bottom = False

        return game_area, bottom_area, send_other_to_bottom

    def _get_game_tables_to_arrange(
        self,
        matched_games: List[win_utils.WindowInfo],
        max_spots: int,
        work_area: win_utils.Rect,
    ) -> List[win_utils.WindowInfo]:
        """
        Maintains the pool of arranged game tables (up to max_spots).
        Tables beyond max_spots remain strictly in MANUAL CONTROL and are NEVER arranged.
        When any of the arranged tables is closed, an extra table steps in so exactly max_spots are arranged.
        """
        current_hwnds = {w.hwnd for w in matched_games}

        # 1. Retain currently arranged tables that are still open
        self.arranged_game_hwnds = [h for h in self.arranged_game_hwnds if h in current_hwnds]

        # 2. If fewer than max_spots, promote available unarranged tables to fill vacancies
        if len(self.arranged_game_hwnds) < max_spots:
            available = [w for w in matched_games if w.hwnd not in self.arranged_game_hwnds]

            # Prefer tables that are already located inside the work area over tables on other monitors
            def _inside_score(w: win_utils.WindowInfo) -> int:
                is_inside = (
                    work_area.x <= w.rect.x < work_area.right
                    and work_area.y <= w.rect.y < work_area.bottom
                )
                return 0 if is_inside else 1

            available.sort(key=_inside_score)

            needed = max_spots - len(self.arranged_game_hwnds)
            for w in available[:needed]:
                self.arranged_game_hwnds.append(w.hwnd)

        # 3. Guard if max_spots was decreased in config
        if len(self.arranged_game_hwnds) > max_spots:
            self.arranged_game_hwnds = self.arranged_game_hwnds[:max_spots]

        arranged_set = set(self.arranged_game_hwnds)
        return [w for w in matched_games if w.hwnd in arranged_set]

    def arrange_windows(self, dry_run: bool = False, verbose: bool = False) -> int:
        """
        Executes one arrangement cycle for both game windows and other windows.
        Returns the number of windows repositioned.
        """
        all_windows = win_utils.get_all_top_level_windows()

        # 1. Match game windows
        game_sort = self.config.get("game_windows", {}).get("filter", {}).get("sort_by", "hwnd")
        matched_games = self.game_filter.filter(all_windows, sort_by=game_sort)
        game_hwnds = {w.hwnd for w in matched_games}

        # 2. Match other windows (excluding any already matched as game windows)
        other_cfg = self.config.get("other_windows", {})
        other_enabled = bool(other_cfg.get("enabled", True))
        other_sort = other_cfg.get("filter", {}).get("sort_by", "hwnd")

        remaining_candidates = [w for w in all_windows if w.hwnd not in game_hwnds]
        matched_other = self.other_filter.filter(remaining_candidates, sort_by=other_sort) if other_enabled else []

        if not matched_games and not matched_other:
            if verbose:
                print("[Window Tiler] No game or auxiliary poker windows found matching filter.")
            return 0

        # Calculate divided work areas
        base_work_area = self.get_adjusted_work_area()
        game_area, bottom_area, send_other_to_bottom = self.split_work_areas(
            base_work_area,
            matched_other=matched_other,
            game_window_count=len(matched_games),
        )

        all_placements: List[Tuple[win_utils.WindowPlacement, str, bool]] = []
        all_matched_map = {w.hwnd: w.title for w in (matched_games + matched_other)}

        # Check foreground window to detect active user interaction
        fg_hwnd = win_utils.user32.GetForegroundWindow()
        other_hwnds = {w.hwnd for w in matched_other}
        if fg_hwnd in other_hwnds:
            self.other_windows_in_front = True
        elif fg_hwnd in game_hwnds:
            self.other_windows_in_front = False

        # If user brought auxiliary windows to the front or is currently using them, don't send to bottom
        effective_send_other_to_bottom = send_other_to_bottom and not self.other_windows_in_front

        # Arrange other windows at bottom side-by-side
        # If effective_send_other_to_bottom is True, other windows stay in the background
        # Cashier windows are never sent to bottom so banking/deposits never disappear
        if matched_other and other_enabled and bottom_area.height > 0:
            other_layout_cfg = other_cfg.get("layout", {})
            other_placements = self.other_strategy.arrange(matched_other, bottom_area, other_layout_cfg)
            for op in other_placements:
                title = all_matched_map.get(op.hwnd, "")
                is_cashier = bool(re.search(r"cashier", title, re.IGNORECASE))
                send_this_to_bottom = effective_send_other_to_bottom and not is_cashier
                all_placements.append((op, "other", send_this_to_bottom))

        # Arrange game tables (tables beyond max_spots remain in manual control unless reuse_window_slots is set)
        if matched_games:
            game_cfg = self.config.get("game_windows", {})
            strat_cfgs = game_cfg.get("strategy_config", {})
            strat_cfg = dict(strat_cfgs.get(self.game_strategy_name, {}))
            if not strat_cfg and self.game_strategy_name in ("default", "side_by_side"):
                strat_cfg = dict(strat_cfgs.get("default", strat_cfgs.get("side_by_side", {})))
            if not strat_cfg and self.game_strategy_name not in ("default", "side_by_side", "grid", "stack"):
                strat_cfg = dict(strat_cfgs.get("custom", {}))
                if "layout_name" not in strat_cfg:
                    strat_cfg["layout_name"] = self.game_strategy_name

            # Inherit top-level reuse_window_slots if not overridden in strat_cfg
            for rk in ("reuse_window_slots", "reuse window slots", "reuse_slots", "reuse slots", "overflow_handling", "overflow"):
                if rk in game_cfg and rk not in strat_cfg:
                    strat_cfg[rk] = game_cfg[rk]

            reuse_mode = self.game_strategy.get_reuse_mode(strat_cfg) if hasattr(self.game_strategy, "get_reuse_mode") else ""

            if not reuse_mode:
                max_spots = self.game_strategy.get_max_spots(strat_cfg)
                tables_to_arrange = self._get_game_tables_to_arrange(matched_games, max_spots, game_area)
            else:
                tables_to_arrange = matched_games
                self.arranged_game_hwnds = [w.hwnd for w in matched_games]

            game_placements = self.game_strategy.arrange(tables_to_arrange, game_area, strat_cfg)
            for gp in game_placements:
                all_placements.append((gp, "game", False))

        runtime_cfg = self.config.get("runtime", {})
        restore_min = bool(runtime_cfg.get("restore_minimized", False))
        bring_front = bool(runtime_cfg.get("bring_to_front", False))
        compensate = bool(runtime_cfg.get("compensate_borders", True))

        # Check if any window actually needs moving or resizing (100% read-only check)
        needed_placements = [
            (p, role, send_bottom)
            for p, role, send_bottom in all_placements
            if win_utils.is_placement_needed(
                p,
                compensate_borders=compensate,
                send_to_bottom=send_bottom,
                restore_minimized=restore_min,
            )
        ]

        if not needed_placements:
            # Everything is already in place. Do absolutely nothing with windows!
            return 0

        moved_count = 0

        for p, role, send_bottom in needed_placements:
            title = all_matched_map.get(p.hwnd, f"HWND {p.hwnd}")
            tag = "Game Table" if role == "game" else "Other Window"

            if dry_run:
                bg_note = " (background)" if send_bottom else ""
                print(f"  [Dry-run] Would place {tag} '{title}' at (x={p.rect.x}, y={p.rect.y}, w={p.rect.width}, h={p.rect.height}){bg_note}")
                moved_count += 1
            else:
                applied = win_utils.apply_window_placement(
                    p,
                    restore_minimized=restore_min,
                    bring_to_front=bring_front,
                    compensate_borders=compensate,
                    send_to_bottom=send_bottom,
                )
                if applied:
                    moved_count += 1
                    bg_note = " (in background)" if send_bottom else ""
                    print(f"  [Arranged {tag}] '{title}' -> (x={p.rect.x}, y={p.rect.y}, w={p.rect.width}, h={p.rect.height}){bg_note}")

        return moved_count

    def list_all_windows(self) -> None:
        """Lists all open windows and flags which ones match game_windows and other_windows."""
        all_windows = win_utils.get_all_top_level_windows()
        matched_games = self.game_filter.filter(all_windows)
        game_hwnds = {w.hwnd for w in matched_games}

        remaining = [w for w in all_windows if w.hwnd not in game_hwnds]
        matched_other = self.other_filter.filter(remaining)
        other_hwnds = {w.hwnd for w in matched_other}

        print("\n" + "=" * 80)
        print("WINDOW TILER: CURRENTLY OPEN WINDOWS")
        print("=" * 80)
        def _fmt_titles(cfg_dict: Dict[str, Any]) -> str:
            f = cfg_dict.get("filter", {})
            val = f.get("titles")
            if val is None:
                val = f.get("title_pattern", "")
            if isinstance(val, (list, tuple)):
                return ", ".join(f"'{x}'" for x in val)
            return str(val)

        print(f"Game Filter:  {_fmt_titles(self.config.get('game_windows', {}))}")
        print(f"Other Filter: {_fmt_titles(self.config.get('other_windows', {}))}")
        print("-" * 80)

        for w in all_windows:
            if w.hwnd in game_hwnds:
                status = "[GAME] "
            elif w.hwnd in other_hwnds:
                status = "[OTHER]"
            else:
                status = "       "
            print(f"{status} HWND: {w.hwnd:<8} | Class: {w.class_name[:25]:<25} | Title: {w.title[:45]}")

        print("-" * 80)
        print(
            f"Total Windows: {len(all_windows)} | "
            f"Game Tables: {len(matched_games)} | "
            f"Other Windows: {len(matched_other)}\n"
        )

    def run(self) -> None:
        """Main monitoring loop with 10s config reload checking."""
        rng_cfg = self.config.get("rng", {})
        other_cfg = self.config.get("other_windows", {})

        rng_status = "Enabled" if rng_cfg.get("enabled", True) else "Disabled"
        rng_pos = rng_cfg.get("position", "top_center")
        rng_shortcut = rng_cfg.get("shortcut", "F8")
        other_shortcut = other_cfg.get("toggle_shortcut", "F9")

        print("=" * 70)
        print("Window Tiler started!")
        print(f"Config file:       {self.config_path}")
        print(f"Game Strategy:     {self.game_strategy_name} (2-4 tables with vertical overlap)")
        print(f"Other Windows:     Bottom of screen side-by-side (Preserves size)")
        print(f"Quick View Lobby:  Shift+MiddleClick or Key:{other_shortcut}")
        print(f"RNG Assistant:     {rng_status} [Pos: {rng_pos}] (MiddleClick or Key:{rng_shortcut})")
        print(f"Config monitoring: Every {self.config_manager.check_interval} seconds")
        print(f"Window scan:       Every {self.arrange_interval} seconds")
        print("Press Ctrl+C to stop.")
        print("=" * 70)

        # Initial arrangement pass
        self.arrange_windows(verbose=True)

        try:
            while True:
                # 1. Check if config file was modified (evaluated every 10s)
                self.config_manager.check_for_updates()

                # 2. Check and arrange windows
                self.arrange_windows(verbose=False)

                # 3. Sleep arrange_interval
                time.sleep(self.arrange_interval)

        except KeyboardInterrupt:
            print("\nWindow Tiler stopped by user.")
        finally:
            if self.input_hook:
                self.input_hook.stop()


# Backward compatibility alias
PokerTilerApp = WindowTilerApp


def main():
    parser = argparse.ArgumentParser(description="Window Tiler - Desktop Window Arranger & RNG Assistant")
    parser.add_argument(
        "--config", "-c", default="config.yaml", help="Path to config.yaml (default: config.yaml)"
    )
    parser.add_argument(
        "--once", action="store_true", help="Arrange windows once and exit immediately"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Calculate layout without actually moving windows"
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="List all open windows and show filter matches"
    )
    parser.add_argument(
        "--strategies", action="store_true", help="List all available window arrangement strategies"
    )
    parser.add_argument(
        "--rng-only", action="store_true", help="Launch only the RNG decision assistant window"
    )

    args = parser.parse_args()

    if args.strategies:
        print("\nAvailable Arrangement Strategies:")
        for name, desc in list_strategies().items():
            print(f"  - {name:<15}: {desc}")
        print()
        return

    if args.rng_only:
        cm = ConfigManager(args.config)
        cfg = cm.load().get("rng", {})
        print("Starting Window Tiler RNG Assistant...")
        rng = RNGWindow(cfg)
        root = rng.create_gui()
        root.mainloop()
        return

    app = WindowTilerApp(config_path=args.config)

    if args.list:
        app.list_all_windows()
        return

    if args.once:
        print("[Window Tiler] Performing single arrangement pass...")
        moved = app.arrange_windows(dry_run=args.dry_run, verbose=True)
        print(f"[Done] Repositioned {moved} window(s).")
        return

    app.run()


if __name__ == "__main__":
    main()
