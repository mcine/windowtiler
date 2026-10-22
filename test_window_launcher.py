"""
test_window_launcher.py - Interactive Test Window Launcher for Window Tiler.

Features:
  - Spawns dummy poker tables (game windows) and auxiliary windows (lobbies/cashier).
  - Interactive Control Panel to dynamically ADD and REMOVE windows on the fly.
  - One-click presets: [1], [2], [3], [4], [6], [8] Tables.
  - Save named layouts to individual files in the layout directory (JSON or YAML).
  - Load saved layouts dynamically at runtime or via CLI flag (--load <layout_name>).
  - Delete saved layouts and refresh the layout catalogue.
  - Windows can be closed individually or via controller buttons.
  - Keyboard shortcuts in controller (G to add table, D to remove, 1-8 for presets).
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None  # Fallback to json only if PyYAML is unavailable

GAME_COLORS = ["#1e3d59", "#17b978", "#ff6e40", "#ffc107", "#7b1fa2", "#0288d1", "#00796b", "#e64a19"]
OTHER_COLORS = ["#2b2e4a", "#53354a", "#903749", "#4a148c"]

GAME_TEMPLATES = [
    ("Table 1 - $1/$2 NL Hold'em (Table 101)", "6-Max No Limit Hold'em"),
    ("Table 2 - $0.50/$1 PL Omaha (Table 202)", "Pot Limit Omaha Fast"),
    ("Table 3 - $5/$10 NL Hold'em High Stakes", "Deep Stack Cash Game"),
    ("Table 4 - Tournament #888321 Table #12", "Sunday Special - Level 14"),
    ("Table 5 - $2/$4 NL Hold'em Turbo", "Turbo Zoom / Fast Forward"),
    ("Table 6 - $1/$2 PL Omaha Hi/Lo", "Split Pot Omaha 6-Max"),
]

OTHER_TEMPLATES = [
    ("PokerStars Main Lobby", "Main Tournament & Cash Lobby"),
    ("Cashier - Account Balance & Banking", "Deposit & Withdrawal Window"),
    ("Tournament Lobby - Event #42 Sunday Million", "Blind Structure & Player List"),
    ("Player Notes & HUD Statistics", "Player Tendencies & Hand Histories"),
]


# ==============================================================================
# Layout File Utilities
# ==============================================================================

def get_layout_dir(custom_dir: Optional[str] = None) -> Path:
    """
    Returns the resolved layout directory path.
    Prioritizes custom_dir if provided. Otherwise looks for an existing
    'layouts' or 'layout' directory in the project root, defaulting to 'layouts'.
    """
    if custom_dir:
        p = Path(custom_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    base = Path(__file__).resolve().parent
    if (base / "layouts").is_dir():
        return base / "layouts"
    if (base / "layout").is_dir():
        return base / "layout"

    default_dir = base / "layouts"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir


def find_layout_file(name: str, layout_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Locates a layout file by name, checking with and without extensions (.json, .yaml, .yml).
    Also transparently checks alternate 'layout'/'layouts' sibling directories.
    """
    if layout_dir is None:
        layout_dir = get_layout_dir()
    else:
        layout_dir = Path(layout_dir).resolve()

    dirs_to_check = [layout_dir]
    if layout_dir.name == "layouts" and (layout_dir.parent / "layout").is_dir():
        dirs_to_check.append(layout_dir.parent / "layout")
    elif layout_dir.name == "layout" and (layout_dir.parent / "layouts").is_dir():
        dirs_to_check.append(layout_dir.parent / "layouts")

    extensions = ["", ".json", ".yaml", ".yml"]
    for d in dirs_to_check:
        for ext in extensions:
            cand = d / (name + ext if (ext and not name.endswith(ext)) else name)
            if cand.is_file():
                return cand
    return None


def list_layouts(layout_dir: Optional[Path] = None) -> List[str]:
    """
    Returns a sorted list of layout names (without extensions) from the layout directory.
    """
    if layout_dir is None:
        layout_dir = get_layout_dir()
    else:
        layout_dir = Path(layout_dir).resolve()

    if not layout_dir.is_dir():
        return []

    names = set()
    for pattern in ("*.json", "*.yaml", "*.yml"):
        for f in layout_dir.glob(pattern):
            names.add(f.stem)

    # Check alternate dir if present
    alt_name = "layout" if layout_dir.name == "layouts" else "layouts"
    alt_dir = layout_dir.parent / alt_name
    if alt_dir.is_dir():
        for pattern in ("*.json", "*.yaml", "*.yml"):
            for f in alt_dir.glob(pattern):
                names.add(f.stem)

    return sorted(list(names))


def save_layout_file(name: str, data: Dict[str, Any], layout_dir: Optional[Path] = None) -> Path:
    """
    Saves layout dictionary data to its own file in the layout directory.
    Formats as YAML if name ends with .yaml/.yml, otherwise JSON.
    """
    if layout_dir is None:
        layout_dir = get_layout_dir()
    else:
        layout_dir = Path(layout_dir).resolve()
        layout_dir.mkdir(parents=True, exist_ok=True)

    clean_name = name.strip()
    if not clean_name:
        clean_name = f"layout_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if clean_name.endswith(".yaml") or clean_name.endswith(".yml"):
        if yaml is None:
            raise RuntimeError("PyYAML is not installed; cannot save YAML.")
        filepath = layout_dir / clean_name
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)
    else:
        if not clean_name.endswith(".json"):
            filepath = layout_dir / f"{clean_name}.json"
        else:
            filepath = layout_dir / clean_name
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    return filepath


def load_layout_file(name_or_path: str, layout_dir: Optional[Path] = None) -> Tuple[Dict[str, Any], Path]:
    """
    Loads layout data from a layout name or direct file path.
    Returns (data_dict, resolved_path).
    """
    target = Path(name_or_path)
    if not target.is_file():
        resolved = find_layout_file(name_or_path, layout_dir)
        if resolved is None or not resolved.is_file():
            raise FileNotFoundError(f"Layout '{name_or_path}' not found in layout directory.")
        target = resolved

    if target.suffix in (".yaml", ".yml"):
        if yaml is None:
            raise RuntimeError("PyYAML is not installed; cannot parse YAML layout.")
        with open(target, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid layout format in {target}: expected dictionary root.")

    return data, target


def delete_layout_file(name: str, layout_dir: Optional[Path] = None) -> bool:
    """
    Deletes the specified layout file from disk if it exists.
    """
    file_path = find_layout_file(name, layout_dir)
    if file_path and file_path.is_file():
        file_path.unlink()
        return True
    return False


# ==============================================================================
# Test Window Launcher Class
# ==============================================================================

class TestWindowLauncher:
    """
    Interactive test window controller and manager.
    """

    __test__ = False

    def __init__(
        self,
        initial_games: int = 2,
        initial_others: int = 1,
        initial_layout: Optional[str] = None,
        layout_dir: Optional[str] = None,
    ):
        self.game_windows: List[tk.Toplevel] = []
        self.other_windows: List[tk.Toplevel] = []
        self.game_counter = 0
        self.other_counter = 0
        self.layout_dir = get_layout_dir(layout_dir)

        self.root = tk.Tk()
        self.root.title("Window Tiler - Window Launcher Controller")
        self.root.geometry("400x520+20+20")
        self.root.configure(bg="#181a20")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        self._build_gui()

        # Load initial layout or spawn requested windows
        if initial_layout:
            try:
                self.load_layout(initial_layout)
            except Exception as e:
                print(f"[Launcher] Error loading initial layout '{initial_layout}': {e}")
                self._spawn_defaults(initial_games, initial_others)
        else:
            self._spawn_defaults(initial_games, initial_others)

        self._bind_keys()

    def _spawn_defaults(self, games: int, others: int):
        for _ in range(games):
            self.add_game_window()
        for _ in range(others):
            self.add_other_window()

    def _build_gui(self):
        # Header
        header = tk.Frame(self.root, bg="#181a20")
        header.pack(fill="x", padx=15, pady=(10, 4))

        lbl_title = tk.Label(
            header,
            text="Window Tiler Test Launcher",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#181a20",
        )
        lbl_title.pack(anchor="w")

        lbl_subtitle = tk.Label(
            header,
            text="Add/remove windows or save/load custom layouts",
            font=("Segoe UI", 8),
            fg="#9da5b4",
            bg="#181a20",
        )
        lbl_subtitle.pack(anchor="w")

        # Status Bar
        self.lbl_status = tk.Label(
            self.root,
            text="Game Tables: 0   |   Other Windows: 0",
            font=("Segoe UI", 10, "bold"),
            fg="#00E676",
            bg="#23272e",
            padx=10,
            pady=5,
            relief="groove",
        )
        self.lbl_status.pack(fill="x", padx=15, pady=6)

        # -------------------------------------------------------------
        # 1. Game Tables Controls Card
        # -------------------------------------------------------------
        card_games = tk.LabelFrame(
            self.root,
            text=" Game Tables ([GAME]) ",
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg="#23272e",
            bd=1,
            relief="solid",
        )
        card_games.pack(fill="x", padx=15, pady=4)

        btn_row1 = tk.Frame(card_games, bg="#23272e")
        btn_row1.pack(fill="x", padx=10, pady=6)

        btn_add_game = tk.Button(
            btn_row1,
            text="+ Add Table (G)",
            bg="#17b978",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=3,
            command=self.add_game_window,
        )
        btn_add_game.pack(side="left", expand=True, fill="x", padx=(0, 4))

        btn_rem_game = tk.Button(
            btn_row1,
            text="- Remove Table (D)",
            bg="#e74c3c",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=3,
            command=self.remove_game_window,
        )
        btn_rem_game.pack(side="right", expand=True, fill="x", padx=(4, 0))

        # Presets Row
        preset_frame = tk.Frame(card_games, bg="#23272e")
        preset_frame.pack(fill="x", padx=10, pady=(0, 6))

        lbl_preset = tk.Label(
            preset_frame,
            text="Presets:",
            font=("Segoe UI", 8),
            fg="#9da5b4",
            bg="#23272e",
        )
        lbl_preset.pack(side="left", padx=(0, 4))

        for count in (1, 2, 3, 4, 6, 8):
            btn_p = tk.Button(
                preset_frame,
                text=f"{count}",
                font=("Segoe UI", 8, "bold"),
                bg="#343a40",
                fg="white",
                relief="flat",
                cursor="hand2",
                padx=4,
                pady=1,
                command=lambda c=count: self.set_game_count(c),
            )
            btn_p.pack(side="left", expand=True, fill="x", padx=1)

        # -------------------------------------------------------------
        # 2. Other Windows Controls Card
        # -------------------------------------------------------------
        card_other = tk.LabelFrame(
            self.root,
            text=" Other Windows ([OTHER] Lobby/Cashier) ",
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg="#23272e",
            bd=1,
            relief="solid",
        )
        card_other.pack(fill="x", padx=15, pady=4)

        btn_row2 = tk.Frame(card_other, bg="#23272e")
        btn_row2.pack(fill="x", padx=10, pady=6)

        btn_add_other = tk.Button(
            btn_row2,
            text="+ Add Lobby (L)",
            bg="#8e44ad",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=3,
            command=self.add_other_window,
        )
        btn_add_other.pack(side="left", expand=True, fill="x", padx=(0, 4))

        btn_rem_other = tk.Button(
            btn_row2,
            text="- Remove Lobby (K)",
            bg="#c0392b",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=3,
            command=self.remove_other_window,
        )
        btn_rem_other.pack(side="right", expand=True, fill="x", padx=(4, 0))

        # -------------------------------------------------------------
        # 3. Layout Management Card (Save / Load / Delete)
        # -------------------------------------------------------------
        card_layout = tk.LabelFrame(
            self.root,
            text=" Layout Management (Save / Load) ",
            font=("Segoe UI", 9, "bold"),
            fg="#ffffff",
            bg="#23272e",
            bd=1,
            relief="solid",
        )
        card_layout.pack(fill="x", padx=15, pady=4)

        # Layout name entry & combobox
        row_layout_top = tk.Frame(card_layout, bg="#23272e")
        row_layout_top.pack(fill="x", padx=10, pady=(6, 3))

        lbl_lname = tk.Label(
            row_layout_top,
            text="Layout:",
            font=("Segoe UI", 8, "bold"),
            fg="#9da5b4",
            bg="#23272e",
        )
        lbl_lname.pack(side="left", padx=(0, 5))

        self.layout_var = tk.StringVar(value="my_layout")
        self.combo_layout = ttk.Combobox(
            row_layout_top,
            textvariable=self.layout_var,
            font=("Segoe UI", 9),
        )
        self.combo_layout.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.combo_layout.bind("<Return>", lambda e: self.load_layout())

        btn_refresh = tk.Button(
            row_layout_top,
            text="🔄",
            bg="#343a40",
            fg="white",
            font=("Segoe UI", 8),
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=1,
            command=self.refresh_layout_list,
        )
        btn_refresh.pack(side="right")

        # Action Buttons Row
        row_actions = tk.Frame(card_layout, bg="#23272e")
        row_actions.pack(fill="x", padx=10, pady=4)

        btn_save = tk.Button(
            row_actions,
            text="💾 Save Layout",
            bg="#2e7d32",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=4,
            command=self.save_layout,
        )
        btn_save.pack(side="left", expand=True, fill="x", padx=(0, 3))

        btn_load = tk.Button(
            row_actions,
            text="📂 Load Layout",
            bg="#1565c0",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=4,
            command=self.load_layout,
        )
        btn_load.pack(side="left", expand=True, fill="x", padx=3)

        btn_delete = tk.Button(
            row_actions,
            text="🗑 Delete",
            bg="#c62828",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=4,
            command=self.delete_layout,
        )
        btn_delete.pack(side="right", padx=(3, 0))

        # Status text for layout operations
        self.lbl_layout_status = tk.Label(
            card_layout,
            text=f"Layout dir: {self.layout_dir.name}/",
            font=("Segoe UI", 8),
            fg="#9da5b4",
            bg="#23272e",
            anchor="w",
        )
        self.lbl_layout_status.pack(fill="x", padx=10, pady=(2, 6))

        # Refresh combobox with available layouts
        self.refresh_layout_list()

        # -------------------------------------------------------------
        # Footer
        # -------------------------------------------------------------
        lbl_hint = tk.Label(
            self.root,
            text="Shortcuts: [G] Add Table | [D] Remove Table | [1-8] Presets\nSaved layouts persist as separate files in the layout directory.",
            font=("Segoe UI", 8),
            fg="#6c757d",
            bg="#181a20",
            justify="center",
        )
        lbl_hint.pack(side="bottom", pady=6)

    def _bind_keys(self):
        self.root.bind("<g>", lambda e: self.add_game_window())
        self.root.bind("<G>", lambda e: self.add_game_window())
        self.root.bind("<d>", lambda e: self.remove_game_window())
        self.root.bind("<D>", lambda e: self.remove_game_window())
        self.root.bind("<l>", lambda e: self.add_other_window())
        self.root.bind("<L>", lambda e: self.add_other_window())
        self.root.bind("<k>", lambda e: self.remove_other_window())
        self.root.bind("<K>", lambda e: self.remove_other_window())
        self.root.bind("1", lambda e: self.set_game_count(1))
        self.root.bind("2", lambda e: self.set_game_count(2))
        self.root.bind("3", lambda e: self.set_game_count(3))
        self.root.bind("4", lambda e: self.set_game_count(4))
        self.root.bind("6", lambda e: self.set_game_count(6))
        self.root.bind("8", lambda e: self.set_game_count(8))

    def _update_status(self):
        g_count = len(self.game_windows)
        o_count = len(self.other_windows)
        self.lbl_status.config(text=f"Game Tables: {g_count}   |   Other Windows: {o_count}")

    # ==========================================================================
    # Window Spawning and Removal Methods
    # ==========================================================================

    def create_game_window(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        color: Optional[str] = None,
        geometry: Optional[str] = None,
    ) -> tk.Toplevel:
        idx = self.game_counter
        self.game_counter += 1

        tmpl = GAME_TEMPLATES[idx % len(GAME_TEMPLATES)]
        if title is None:
            title = f"{tmpl[0]} #{idx + 1}"
        if subtitle is None:
            subtitle = tmpl[1]
        if color is None:
            color = GAME_COLORS[idx % len(GAME_COLORS)]

        top = tk.Toplevel(self.root)
        top.title(title)
        if geometry:
            top.geometry(geometry)
        else:
            offset = 50 + (idx % 8) * 35
            top.geometry(f"420x300+{offset}+{offset}")
        top.configure(bg=color)

        lbl = tk.Label(
            top,
            text=f"[GAME TABLE]\n\n{title}\n{subtitle}\n\nArranged by Window Tiler",
            font=("Segoe UI", 11, "bold"),
            fg="white",
            bg=color,
            padx=15,
            pady=15,
        )
        lbl.pack(expand=True)

        top._meta = {
            "type": "game",
            "title": title,
            "subtitle": subtitle,
            "color": color,
            "index": idx,
        }

        def _on_close():
            if top in self.game_windows:
                self.game_windows.remove(top)
            top.destroy()
            self._update_status()

        top.protocol("WM_DELETE_WINDOW", _on_close)
        self.game_windows.append(top)
        self._update_status()
        return top

    def add_game_window(self) -> tk.Toplevel:
        win = self.create_game_window()
        print(f"[Launcher] Added Game Table: '{win.title()}' (Total: {len(self.game_windows)})")
        return win

    def remove_game_window(self):
        if not self.game_windows:
            print("[Launcher] No game tables to remove.")
            return
        last_win = self.game_windows.pop()
        title = last_win.title()
        last_win.destroy()
        self._update_status()
        print(f"[Launcher] Removed Game Table: '{title}' (Remaining: {len(self.game_windows)})")

    def set_game_count(self, target_count: int):
        """Sets the exact number of game tables."""
        while len(self.game_windows) < target_count:
            self.add_game_window()
        while len(self.game_windows) > target_count:
            self.remove_game_window()

    def create_other_window(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        color: Optional[str] = None,
        geometry: Optional[str] = None,
    ) -> tk.Toplevel:
        idx = self.other_counter
        self.other_counter += 1

        tmpl = OTHER_TEMPLATES[idx % len(OTHER_TEMPLATES)]
        if title is None:
            title = f"{tmpl[0]} #{idx + 1}" if idx >= len(OTHER_TEMPLATES) else tmpl[0]
        if subtitle is None:
            subtitle = tmpl[1]
        if color is None:
            color = OTHER_COLORS[idx % len(OTHER_COLORS)]

        top = tk.Toplevel(self.root)
        top.title(title)
        if geometry:
            top.geometry(geometry)
        else:
            offset = 80 + (idx % 6) * 40
            top.geometry(f"460x220+{offset}+{450 + offset // 2}")
        top.configure(bg=color)

        lbl = tk.Label(
            top,
            text=f"[AUXILIARY POKER WINDOW]\n\n{title}\n{subtitle}\n\nPlaced at bottom (size preserved)",
            font=("Segoe UI", 10, "bold"),
            fg="white",
            bg=color,
            padx=10,
            pady=10,
        )
        lbl.pack(expand=True)

        top._meta = {
            "type": "other",
            "title": title,
            "subtitle": subtitle,
            "color": color,
            "index": idx,
        }

        def _on_close():
            if top in self.other_windows:
                self.other_windows.remove(top)
            top.destroy()
            self._update_status()

        top.protocol("WM_DELETE_WINDOW", _on_close)
        self.other_windows.append(top)
        self._update_status()
        return top

    def add_other_window(self) -> tk.Toplevel:
        win = self.create_other_window()
        print(f"[Launcher] Added Auxiliary Window: '{win.title()}' (Total: {len(self.other_windows)})")
        return win

    def remove_other_window(self):
        if not self.other_windows:
            print("[Launcher] No auxiliary windows to remove.")
            return
        last_win = self.other_windows.pop()
        title = last_win.title()
        last_win.destroy()
        self._update_status()
        print(f"[Launcher] Removed Auxiliary Window: '{title}' (Remaining: {len(self.other_windows)})")

    def close_all_windows(self):
        """Closes all currently open test windows."""
        while self.game_windows:
            win = self.game_windows.pop()
            try:
                win.destroy()
            except Exception:
                pass
        while self.other_windows:
            win = self.other_windows.pop()
            try:
                win.destroy()
            except Exception:
                pass
        self._update_status()

    # ==========================================================================
    # Layout Save / Load / Delete / Refresh
    # ==========================================================================

    def refresh_layout_list(self):
        """Refreshes the combobox dropdown values with all layout files found."""
        layouts = list_layouts(self.layout_dir)
        self.combo_layout["values"] = layouts
        if layouts and not self.layout_var.get():
            self.layout_var.set(layouts[0])
        return layouts

    def _extract_slot_info(self, win: tk.Toplevel) -> Dict[str, Any]:
        """Extracts slot position and dimensions (x, y, width, height) only."""
        win.update_idletasks()
        info: Dict[str, Any] = {
            "x": win.winfo_x(),
            "y": win.winfo_y(),
            "width": win.winfo_width(),
            "height": win.winfo_height(),
        }
        meta = getattr(win, "_meta", {})
        if "monitor" in meta:
            info["monitor"] = meta["monitor"]
        return info

    def save_layout(self, layout_name: Optional[str] = None) -> Optional[Path]:
        """
        Saves current open test windows into a layout file in layout directory.
        Only stores slot coordinates (x, y, width, height) - titles, subtitles,
        geometry strings, and colors are generated dynamically by the tool when loaded.
        """
        name = (layout_name or self.layout_var.get()).strip()
        if not name:
            self.lbl_layout_status.config(text="⚠ Please enter a layout name first", fg="#ffca28")
            return None

        # Build data dictionary containing only slots
        slots = [self._extract_slot_info(w) for w in self.game_windows]
        other_slots = [self._extract_slot_info(w) for w in self.other_windows]

        layout_data = {
            "name": name,
            "slots": slots,
            "other_slots": other_slots,
        }

        try:
            saved_path = save_layout_file(name, layout_data, self.layout_dir)
            self.refresh_layout_list()
            self.layout_var.set(saved_path.stem)
            msg = f"✓ Saved '{saved_path.name}' ({len(self.game_windows)} tables, {len(self.other_windows)} other)"
            self.lbl_layout_status.config(text=msg, fg="#00E676")
            print(f"[Launcher] {msg} -> {saved_path}")
            return saved_path
        except Exception as e:
            err_msg = f"⚠ Save failed: {e}"
            self.lbl_layout_status.config(text=err_msg, fg="#ff5252")
            print(f"[Launcher] {err_msg}")
            return None

    def load_layout(self, layout_name: Optional[str] = None) -> bool:
        """
        Loads layout by name or path, recreating all game and other windows.
        Titles, subtitles, and colors are generated automatically by the tool in detection order.
        """
        name = (layout_name or self.layout_var.get()).strip()
        if not name:
            self.lbl_layout_status.config(text="⚠ Select or enter a layout name to load", fg="#ffca28")
            return False

        try:
            data, resolved_path = load_layout_file(name, self.layout_dir)
            self.close_all_windows()

            # Recreate game windows from slots (tool generates title, subtitle, color)
            gw_slots = (
                data.get("slots")
                or data.get("boxes")
                or data.get("game_windows")
                or data.get("tables")
                or []
            )
            if gw_slots:
                for slot in gw_slots:
                    if isinstance(slot, dict):
                        x = slot.get("x")
                        y = slot.get("y")
                        w = slot.get("width")
                        h = slot.get("height")
                        geom = (
                            f"{w}x{h}+{x}+{y}"
                            if (w and h and x is not None and y is not None)
                            else slot.get("geometry")
                        )
                        self.create_game_window(geometry=geom)
            elif data.get("game_count", 0) > 0:
                for _ in range(data["game_count"]):
                    self.add_game_window()

            # Recreate auxiliary windows from other_slots (tool generates title, subtitle, color)
            ow_slots = (
                data.get("other_slots")
                or data.get("other_windows")
                or []
            )
            if ow_slots:
                for slot in ow_slots:
                    if isinstance(slot, dict):
                        x = slot.get("x")
                        y = slot.get("y")
                        w = slot.get("width")
                        h = slot.get("height")
                        geom = (
                            f"{w}x{h}+{x}+{y}"
                            if (w and h and x is not None and y is not None)
                            else slot.get("geometry")
                        )
                        self.create_other_window(geometry=geom)
            elif data.get("other_count", 0) > 0:
                for _ in range(data["other_count"]):
                    self.add_other_window()

            self.layout_var.set(resolved_path.stem)
            msg = f"✓ Loaded '{resolved_path.name}' ({len(self.game_windows)} tables, {len(self.other_windows)} other)"
            self.lbl_layout_status.config(text=msg, fg="#00E676")
            print(f"[Launcher] {msg}")
            return True
        except FileNotFoundError:
            err_msg = f"⚠ Layout '{name}' not found in {self.layout_dir.name}/"
            self.lbl_layout_status.config(text=err_msg, fg="#ff5252")
            print(f"[Launcher] {err_msg}")
            return False
        except Exception as e:
            err_msg = f"⚠ Load failed: {e}"
            self.lbl_layout_status.config(text=err_msg, fg="#ff5252")
            print(f"[Launcher] {err_msg}")
            return False

    def delete_layout(self, layout_name: Optional[str] = None) -> bool:
        """
        Deletes the selected layout file from disk.
        """
        name = (layout_name or self.layout_var.get()).strip()
        if not name:
            self.lbl_layout_status.config(text="⚠ Select a layout name to delete", fg="#ffca28")
            return False

        success = delete_layout_file(name, self.layout_dir)
        if success:
            self.refresh_layout_list()
            msg = f"✓ Deleted layout '{name}'"
            self.lbl_layout_status.config(text=msg, fg="#00E676")
            print(f"[Launcher] {msg}")
            return True
        else:
            msg = f"⚠ Layout '{name}' does not exist to delete"
            self.lbl_layout_status.config(text=msg, fg="#ffca28")
            return False

    def run(self):
        print("Window Tiler Interactive Test Launcher running.")
        print("Use the controller window to Add/Remove tables or Save/Load layouts.")
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description="Interactive Window Tiler Test Window Launcher")
    parser.add_argument("--games", "-g", type=int, default=2, help="Initial number of game tables (default: 2)")
    parser.add_argument("--others", "-o", type=int, default=1, help="Initial number of auxiliary windows (default: 1)")
    parser.add_argument("--load", "-l", type=str, default="", help="Name or path of layout to load on startup")
    parser.add_argument("--layout-dir", type=str, default="", help="Custom layout directory path")
    args = parser.parse_args()

    launcher = TestWindowLauncher(
        initial_games=args.games,
        initial_others=args.others,
        initial_layout=args.load if args.load else None,
        layout_dir=args.layout_dir if args.layout_dir else None,
    )
    launcher.run()


if __name__ == "__main__":
    main()
