"""
rng_window.py - Decision Assistant / Random Number Generator window for Window Tiler.

Features:
  - Frameless (NO OS title bar) for a sleek, modern HUD appearance.
  - Displays a random number (0-100) in a large bold font.
  - Automatically updates every 10 seconds.
  - Re-rolls immediately when clicked or when the window gains focus/activation.
  - Interactive slider (0-100) with configurable default threshold (default 50).
  - Dynamic color:
      * GREEN if random_number > slider_value
      * RED if random_number <= slider_value
  - Configurable position (default: 'top_center', also supports 'center', 'top_left', etc.).
  - Draggable: click and drag anywhere on the card to move it.
  - Toggle visibility with middle mouse button or configurable shortcut.
  - Stays on top of poker tables (topmost).
"""

import queue
import random
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, Optional, Tuple


class RNGWindow:
    """
    Manages the frameless Random Number Generator HUD popup window.
    Designed to run seamlessly within a background thread or main loop.
    """

    COLOR_BG = "#181a20"
    COLOR_CARD = "#23272e"
    COLOR_GREEN = "#00E676"  # Bright vibrant green
    COLOR_RED = "#FF1744"    # Bright vibrant red
    COLOR_TEXT_DIM = "#9da5b4"
    COLOR_WHITE = "#ffffff"
    COLOR_BORDER = "#3b4252"

    def __init__(self, config: Dict[str, Any], on_close_callback: Optional[Callable[[], None]] = None):
        self.config = config
        self.on_close_callback = on_close_callback

        self.threshold: int = int(config.get("default_threshold", 50))
        self.auto_interval: float = float(config.get("auto_update_seconds", 10.0))
        self.stay_on_top: bool = bool(config.get("stay_on_top", True))
        self.position: str = str(config.get("position", "top_center")).lower()
        self.current_number: int = random.randint(0, 100)

        self._root: Optional[tk.Tk] = None
        self._lbl_number: Optional[tk.Label] = None
        self._lbl_status: Optional[tk.Label] = None
        self._slider: Optional[tk.Scale] = None
        self._lbl_threshold_val: Optional[tk.Label] = None
        self._timer_id: Optional[str] = None
        self._is_visible: bool = False
        self._drag_start_x: int = 0
        self._drag_start_y: int = 0

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Hot-reloads configuration settings (interval, stay_on_top, position, default threshold)."""
        self.config = new_config
        self.auto_interval = float(new_config.get("auto_update_seconds", 10.0))
        self.stay_on_top = bool(new_config.get("stay_on_top", True))
        self.position = str(new_config.get("position", "top_center")).lower()
        if self._root:
            self._root.after(0, self._apply_hot_config)

    def _apply_hot_config(self) -> None:
        if self._root:
            self._root.attributes("-topmost", self.stay_on_top)
            w = int(self.config.get("window_width", 240))
            h = int(self.config.get("window_height", 240))
            pos_x, pos_y = self.calculate_position(self._root, w, h)
            self._root.geometry(f"{w}x{h}+{pos_x}+{pos_y}")

    def calculate_position(self, root: tk.Tk, w: int, h: int) -> Tuple[int, int]:
        """Calculates window (x, y) coordinates on the screen based on config."""
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()

        pos = str(self.config.get("position", "top_center")).lower().strip()
        offset_x = int(self.config.get("offset_x", 0))
        offset_y = int(self.config.get("offset_y", 0))

        if pos == "top_center":
            pos_x = (screen_w - w) // 2 + offset_x
            pos_y = offset_y
        elif pos == "center":
            pos_x = (screen_w - w) // 2 + offset_x
            pos_y = (screen_h - h) // 2 + offset_y
        elif pos == "top_left":
            pos_x = max(0, offset_x)
            pos_y = max(0, offset_y)
        elif pos == "top_right":
            pos_x = max(0, screen_w - w - offset_x)
            pos_y = max(0, offset_y)
        elif pos == "bottom_center":
            pos_x = (screen_w - w) // 2 + offset_x
            pos_y = max(0, screen_h - h - offset_y)
        elif pos == "custom":
            pos_x = int(self.config.get("custom_x", 0))
            pos_y = int(self.config.get("custom_y", 0))
        else:  # default top_center
            pos_x = (screen_w - w) // 2 + offset_x
            pos_y = offset_y

        return max(0, pos_x), max(0, pos_y)

    def roll_number(self, event=None) -> int:
        """Generates a new random number and updates display."""
        self.current_number = random.randint(0, 100)
        self._update_display()
        self._reset_timer()
        return self.current_number

    def _update_display(self) -> None:
        if not self._lbl_number:
            return

        is_green = self.current_number > self.threshold
        color = self.COLOR_GREEN if is_green else self.COLOR_RED

        self._lbl_number.config(text=str(self.current_number), fg=color)

        if self._lbl_status:
            status_text = f"{self.current_number} > {self.threshold} (PASS/CALL)" if is_green else f"{self.current_number} <= {self.threshold} (FOLD/CHECK)"
            self._lbl_status.config(text=status_text, fg=color)

    def _on_slider_change(self, val_str: str) -> None:
        try:
            self.threshold = int(val_str)
            if self._lbl_threshold_val:
                self._lbl_threshold_val.config(text=f"Threshold: {self.threshold}%")
            self._update_display()
        except ValueError:
            pass

    def _on_window_activated(self, event=None) -> None:
        """Re-rolls when the window gains focus/activation."""
        self.roll_number()

    def _on_window_clicked(self, event=None) -> None:
        """Re-rolls immediately when clicked."""
        self.roll_number()

    def _on_timer_tick(self) -> None:
        """Auto-updates the random number every 10 seconds."""
        self.roll_number()

    def _reset_timer(self) -> None:
        """Resets the periodic update countdown timer."""
        if self._root and self._timer_id:
            try:
                self._root.after_cancel(self._timer_id)
            except Exception:
                pass
        if self._root and self.auto_interval > 0:
            ms = int(self.auto_interval * 1000)
            self._timer_id = self._root.after(ms, self._on_timer_tick)

    def show(self) -> None:
        """Brings the window to front, visible and un-minimized."""
        if not self._root:
            return
        self._root.deiconify()
        self._root.attributes("-topmost", self.stay_on_top)
        self._root.lift()
        self._is_visible = True
        self.roll_number()

    def hide(self) -> None:
        """Hides the window."""
        if not self._root:
            return
        self._root.withdraw()
        self._is_visible = False

    def toggle(self) -> None:
        """Toggles window visibility."""
        if self._is_visible:
            self.hide()
        else:
            self.show()

    def trigger_from_any_thread(self, action: str = "toggle") -> None:
        """Thread-safe trigger method called by mouse or keyboard hooks."""
        if self._root:
            if action == "toggle":
                self._root.after(0, self.toggle)
            elif action == "show":
                self._root.after(0, self.show)
            elif action == "hide":
                self._root.after(0, self.hide)
            elif action == "roll":
                self._root.after(0, self.roll_number)

    # --------------------------------------------------------------------------
    # Smooth Window Dragging Handlers (for frameless window)
    # --------------------------------------------------------------------------
    def _start_drag(self, event):
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root

    def _on_drag(self, event):
        if not self._root:
            return
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        cur_x = self._root.winfo_x()
        cur_y = self._root.winfo_y()
        self._root.geometry(f"+{cur_x + dx}+{cur_y + dy}")

    def create_gui(self) -> tk.Tk:
        """Constructs the frameless Tkinter interface."""
        root = tk.Tk()
        self._root = root

        # REMOVE OS TITLEBAR completely
        root.overrideredirect(True)

        w = int(self.config.get("window_width", 240))
        h = int(self.config.get("window_height", 240))

        # Position (default: top_center)
        pos_x, pos_y = self.calculate_position(root, w, h)
        root.geometry(f"{w}x{h}+{pos_x}+{pos_y}")
        root.configure(bg=self.COLOR_BG)
        root.attributes("-topmost", self.stay_on_top)
        root.resizable(False, False)

        # Outer border frame for crisp definition
        outer_frame = tk.Frame(root, bg=self.COLOR_BORDER, bd=1)
        outer_frame.pack(fill="both", expand=True)

        # Card container
        card = tk.Frame(outer_frame, bg=self.COLOR_CARD)
        card.pack(fill="both", expand=True, padx=1, pady=1)

        # Mini Top Drag Bar
        top_bar = tk.Frame(card, bg=self.COLOR_CARD, height=22)
        top_bar.pack(fill="x", padx=6, pady=(4, 0))

        lbl_drag = tk.Label(
            top_bar,
            text=":: RNG HUD",
            font=("Segoe UI", 8, "bold"),
            fg=self.COLOR_TEXT_DIM,
            bg=self.COLOR_CARD,
            cursor="fleur",
        )
        lbl_drag.pack(side="left")

        # Sleek Close Button
        btn_close = tk.Label(
            top_bar,
            text="✕",
            font=("Segoe UI", 9, "bold"),
            fg=self.COLOR_TEXT_DIM,
            bg=self.COLOR_CARD,
            cursor="hand2",
            padx=4,
        )
        btn_close.pack(side="right")
        btn_close.bind("<Button-1>", lambda e: self.hide())
        btn_close.bind("<Enter>", lambda e: btn_close.config(fg="#ff5555"))
        btn_close.bind("<Leave>", lambda e: btn_close.config(fg=self.COLOR_TEXT_DIM))

        # Drag bindings
        top_bar.bind("<Button-1>", self._start_drag)
        top_bar.bind("<B1-Motion>", self._on_drag)
        lbl_drag.bind("<Button-1>", self._start_drag)
        lbl_drag.bind("<B1-Motion>", self._on_drag)

        # Main large font random number display
        lbl_num = tk.Label(
            card,
            text=str(self.current_number),
            font=("Segoe UI", 52, "bold"),
            bg=self.COLOR_CARD,
            cursor="hand2",
        )
        lbl_num.pack(pady=(0, 0))
        self._lbl_number = lbl_num

        # Result badge / status
        lbl_status = tk.Label(
            card,
            text="",
            font=("Segoe UI", 8, "bold"),
            bg=self.COLOR_CARD,
        )
        lbl_status.pack(pady=(0, 6))
        self._lbl_status = lbl_status

        # Threshold value label
        lbl_thresh = tk.Label(
            card,
            text=f"Threshold: {self.threshold}%",
            font=("Segoe UI", 8, "bold"),
            fg=self.COLOR_WHITE,
            bg=self.COLOR_CARD,
        )
        lbl_thresh.pack()
        self._lbl_threshold_val = lbl_thresh

        # Threshold slider (0 to 100)
        slider = tk.Scale(
            card,
            from_=0,
            to=100,
            orient="horizontal",
            showvalue=False,
            bg=self.COLOR_CARD,
            fg=self.COLOR_WHITE,
            troughcolor=self.COLOR_BG,
            highlightthickness=0,
            activebackground=self.COLOR_GREEN,
            command=self._on_slider_change,
            cursor="hand2",
            length=180,
        )
        slider.set(self.threshold)
        slider.pack(pady=(2, 6))
        self._slider = slider

        # Event bindings
        # Click anywhere on number or card to re-roll
        lbl_num.bind("<Button-1>", self._on_window_clicked)
        card.bind("<Button-1>", self._on_window_clicked)

        # Allow dragging from card background with right button or shift
        card.bind("<Button-3>", self._start_drag)
        card.bind("<B3-Motion>", self._on_drag)

        # Window activated / focus gained -> re-roll
        root.bind("<FocusIn>", self._on_window_activated)

        # Press Esc to close/hide
        root.bind("<Escape>", lambda e: self.hide())

        # Initial display and timer
        self._is_visible = True
        self._update_display()
        self._reset_timer()

        return root

    def run_in_thread(self) -> threading.Thread:
        """Starts the RNG window in a background thread."""
        def _thread_target():
            root = self.create_gui()
            root.mainloop()

        t = threading.Thread(target=_thread_target, daemon=True, name="WindowTiler-RNG")
        t.start()
        return t
